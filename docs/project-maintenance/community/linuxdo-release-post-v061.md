---
title: "Linux Do v0.6.1 发布推广帖"
status: active
updated: 2026-06-18
owner: servo-kernel
last_verified: 2026-06-18
---
# Linux Do v0.6.1 发布推广帖

> 仓内维护说明：本文保留 Linux Do 社区发布语境和原帖表达。技术侧、架构侧和能力边界的整理版见 [Servo 对外技术与架构叙事](./external-technical-architecture.md)。

#### 本帖使用社区开源推广，符合推广要求。我申明并遵循社区要求的以下内容：

*   **我的帖子已经打上 [开源推广](https://linux.do/tag/2234-tag/2234) 标签：** 是
*   **我的开源项目完整开源，无未开源部分：** 是
*   **我的开源项目已链接认可 LINUX DO 社区：** 是
*   **我帖子内的项目介绍，AI生成、润色内容部分已截图发出：** 是
*   **以上选择我承诺是永久有效的，接受社区和佬友监督：** 是

_以下为项目介绍正文内容，AI生成、润色内容已使用截图方式发出_

* * *

## 项目链接

GitHub： [https://github.com/OceanEyeFF/servo](https://github.com/OceanEyeFF/servo)

npm： [servo-installer](https://www.npmjs.com/package/servo-installer) `v0.6.1`

## VibeCoding 的痛点

- 模型写了一堆代码，意识到要检查一下的时候，已经偏到不知道哪里去了。面对屎山代码捏着鼻子慢慢改吧。
- “帮我做一个 XXX”，模型很听话，猛猛干。但是结束之后不管你怎么喊他干活，他都很关心你想让你早点睡觉。只能被迫新开一个窗口。*可以休息了主人~已经可以休息了~已经很很晚了我们明天再来吧~*
- 追加需求的时候，需求还没说清楚，模型自己有自己的想法，马上开干。*反应过来Deepseek已经写了三四个文件的我：尖锐爆鸣。*
- 又想享受自动工作的，又怕它删库跑路;不自动推进，又得一直盯着。*真是不好意思我把库删了给你的工作造成了困扰，你还想做什么?我会稳稳地接住你的。*
- 上下文污染。*Claude开始蹦韩文和乱码：完蛋了*
- ......

现在模型还需要一套额外的**控制系统和行为逻辑**——基于项目状态，让他能够自主分析“现在应该做什么、不该做什么、做完下一步是什么、什么时候该把控制权交还给程序员”。

## 为什么写了 Servo ?

Servo 是一套**基于控制论的 AI coding harness**。它不替你写代码，它帮你管“AI 写代码的过程”。

本Skills包兼容 Codex、Pi、Claude Code，几乎不需要改变工作习惯。 Servo 主要负责 **状态估计、目标拆分、任务分派、证据收集、准入门控** 这些细细碎碎的工作细节，大方向和细节验收还是要自己来负责。

实际体验上大概是这样：

> 你对仓库设一个长期目标(或者直接给需求描述)。Servo 分析现状，推荐候选 Milestone。你确认一个 Milestone brief(目的、范围、验收标准)后，Servo 把它拆成 Worktrack 逐个推进。每完成一个 Worktrack 自动收集证据、Gate 裁决、合入分支。全做完后交还--你来决定这个 Milestone 过还是不过。

你有想法的时候，直接描述交给 Servo 拆解推进;没想法的时候，一句 `$harness-skill` 让 Servo 自己嗅探现状，推荐下一步该做什么。

## 技术思路

### 为什么需要控制论

LLM 本身是不stable的工作组件--根据不同的输入可能会会跑偏、长上下文会产生遗忘、部分模型会有幻觉。任何一个单一提示词、任何一次单次生成，都可能出错。这不是模型不够好，而是大模型的工作模式导致的：Transformer模拟的贝叶斯学习决定了它不可能每次都得到相同的结果。

系统工程和控制论的核心思想是**设计冗余、反馈和恢复路径，让系统整体变得可靠**。一个部件出错了，另一个机制能兜底圈回来。

Servo 把 AI coding 建模成一个闭环控制系统。目标是让每次犯错都有机制接住：每一层有观察(Observe)、有验证(Verify)、有验收判断(Judge)，验证不通过就回滚重试或换路径。多层冗余协作，系统才能稳定跑下去。

### 三层控制对象

不同粒度的决策应该在不同层上做。把“新加的代码怎么补测试任务”和“项目上微服务需要分几步改造”放在同一个上下文里讨论，是非常的不合理的。

Servo 定义了三层：

| 层 | 变量速度 | 关注什么 |
|---|---|---|
| **Repo** | 慢 | 长期目标、架构地图、系统不变量、治理状况。这一层不关心具体代码。 |
| **Milestone** | 中 | 把长期目标拆成多个MileStone或者手动指定MileStone。每个MS有明确的目标、完成信号和验收标准。需要使用者的批准验收来完成交付。 |
| **Worktrack** | 快 | 把单个 Milestone 落地成受控执行单元。独立 Git 分支、独立验收流程。这里会写代码和写文档。 |

我的做法是，对总的任务目标，先讨论+规划拆分到多个MileStone，确认MileStone清单写入到 `.servo` 的管理文档中，然后开新的窗口，逐个MileStone做推进工作。
如果使用连续推进就对Worktrack级别的工作无感，如果每个Worktrack都要求使用者手动验收的话，也可以作为WT层级的观察验收角色来参与流程工作。

### 三层模型

每一层控制器的行为由三个层级的Tick确定：

```
Scope(在哪层控制)× Function(此刻做什么)× Artifact(依赖什么正式对象)
```

- **Scope**：RepoScope / WorktrackScope，决定了操作的粒度和权限面
- **Function**：Observe → Decide → Init → Dispatch → Verify → Judge → Recover → Close，八个状态转移算子。
- **Artifact**：Goal Charter、Contract、Plan/Task Queue、Evidence、Control State 等文档，用于管理项目状态、项目进度、过去未来工作决策等信息。

观测层 `Scope` 决定了哪些算子 `Function` 合法，`Function` 决定了需要更新、使用哪些 `Artifact`。
比如MileStone层的Judge算子是更严格的验收模式，要通过更多的测试;Dispatch是Worktrack层级的特有的分派器。

### 何时Handback与如何继续推进工作

Servo 在每轮 Worktrack 或 Milestone 闭环后主动交还控制权--这叫 Handback。

设计思路很简单：AI 完成了一个受控执行单元，它需要你确认“这个结果对不对”，或者“下一步往哪走”。你给的信息会形成新的误差信号，控制器拿到之后才知道该干什么。你不给新信息，状态机就没有新的输入，自然不应该有新的动作。

**所以“继续工作”“继续推进”在 Handback 后是无效的。** 这不是在为难你，是系统设计上就没有“盲继续”这个状态转移路径。你要么说“这个 Milestone 过”，要么说“不对，补一个 Worktrack”，要么说“调整目标，因为……”。

AI 交还控制权时会给你他的工作思路，你只需要说“好”、“不好”、“我的意见是……”——这就够了，这就是有效的信息输入。

### 完整循环

```
RepoScope.Observe(看现状)
  → RepoScope.Decide(选 Milestone)
  → WorktrackScope.Init(建分支、设 Contract)
  → WorktrackScope.Observe(看当前 Worktrack 状态)
  → WorktrackScope.Decide(选下一任务)
  → WorktrackScope.Dispatch(分派给 SubAgent 执行)
  → WorktrackScope.Verify(收集 review/test/rule 证据)
  → WorktrackScope.Judge(Gate 裁决)
  → WorktrackScope.Close or Recover(合入 or 回滚)
  → RepoScope.Refresh(刷新 repo 快照)
  → RepoScope.Observe(循环)
```

这个闭环里，Worktrack自动验收之后，还要刷 repo 状态、更新 Milestone 进度、清理工作分支，才算真正闭环。实际使用中这个流程是自动推进的，你只在 Handback 节点介入。

## v0.6.1 已经有什么

上面讲的设计思路(分层控制、闭环回路、Handback 交接)大部分都已经实装。这里列一些更接近日常使用的功能：

-   **TUI 引导安装**：六阶段流程 diagnose → preview → confirm → install → verify → summary，不用记 CLI 参数
-   **Milestone Intake 审批**：初始化 Milestone 前做信息确认和使用者准入审批，防止方向性偏差在源头
-   **追加需求自动路由**：`repo-append-request-skill` ，把你的需求自动分流为 new worktrack / scope expansion / design-only / goal change
-   **Worktrack 额度机制**：允许连续推进，但是连续推进仅有一定的预算数额，耗尽需要重新申请
-   23 个 Skills，完整覆盖 Supervisor → Repo → Milestone → Worktrack 四层控制回路

## 怎么上手

```bash
# 需要 Node.js >= 18，在你的项目根目录(不做全局分发)

npx servo-installer          # TUI 引导安装(推荐)
# 或者 CLI：
npx servo-installer install --backend agents
npx servo-installer verify --backend agents
# 或者交给 CodeX | Claude
# Chat with ...
```

然后在你的 Coding CLI 里：

```txt
$set-harness-goal-skill 当前仓库期望最终实现一个 [目标描述]。
$repo-whats-next-skill    # 分析候选 Milestone
$harness-skill            # 开始推进
```

注意，不通过 `harness-skill` 技能调用的工作，不一定会走完整的harness流程。个人的建议是，开始MileStone和中间的重要Worktrack要使用 `harness-skill` 来执行你的Prompt。

完整教程见 GitHub README 和项目内 `docs/`。

## 写在最后

从 v0.5 到 v0.6.1，Servo 走过了好几轮 Milestone 自开发(用 Servo 开发 Servo)。控制论那套理论在工程中能不能跑通、LLM 能不能吃住三层状态切换的复杂度、SubAgent 分派会不会把上下文炸飞--这些问题都在 dogfood 过程中一个个验证过来了。

目前实测 CodeX + GPT-5.5 和 Pi + DeepSeek 都可以丝滑跑通完整闭环，Claude没测(不咋用了)。如果你测出了更好的模型配置，或者有新的想法，欢迎来提 issue 和 PR。

用得顺手的话点个 ⭐，也欢迎来交流 VibeCoding 心得经验，帮助一起改进这个还不是很完善的 .servo 项目~

* * *

 碎碎念
260508： 大概 VibeCoding 也有差不多一年了，用过国产小垃圾也用过中转 Claude 和 GPT，这个项目算是个人 VibeCoding 的经验加上之前看了很多的工程控制论的一个整合产品。
260618： 时隔一个月的更新，补了一个`MileStoneIntake`，也就是初始化MileStone之前需要做一些信息确认和使用者的准入审批;还做了很多的bugfix。总的来说都是细细碎碎的东西，大致思路没有做很大的修改。
