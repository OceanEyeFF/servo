---
title: "全局语言风格"
status: active
updated: 2026-04-19
owner: servo-kernel
last_verified: 2026-06-13
---
# 全局语言风格

> 目的：固定跨任务的人读输出默认口径，优先服务判断、执行和收口，而不是背景铺垫。

## 一、默认原则

先给结论；前 20% 明确最终判断与可执行性；推理与背景若非决策必需、无独立价值，可省略。

## 二、默认结构

默认按下面结构组织：

```text
【TL;DR】
一句话结论 + 是否可执行

【Key Points】
- 最多 3 条关键点

【Action】
- 最多 3 条可执行动作

【Optional Reasoning】
- 可选；不影响理解与执行
```

## 三、使用约束

`TL;DR` 必须独立可判；`Key Points` 只留决策信息；`Action` 只写当前动作，无动作时写明不可执行；`Optional Reasoning` 只含推理与证据。

## 四、判断标准

读者开头即知结论与可执行性，无需先读背景。推理后置，主结论仍完整。

## 五、肯定优先写作规则

> 背景：LLM 处理否定句时先激活被否定概念的语义关联，再附加弱否定信号。Compaction 后否定修饰符容易丢失，导致语义反转（"PR 不是闭环终点" → "PR = 闭环终点"）。

### 5.1 核心原则

优先用肯定句式直接陈述"是什么"，避免以"不是A，而是B"的否定优先形式引入被排除的概念 A。

### 5.2 改写范例

| 否定优先（避免） | 肯定优先（推荐） |
|---|---|
| 当当前问题不是"如何修复"，而是"如何收尾"时 | 当需要完成收尾路径时 |
| Harness 关注的不是"把任务做完"本身 | Harness 关注的是：系统输入、状态观测、目标对比、持续判断 |
| PR 不是闭环终点 | PR 只是中间步骤；完整的 closeout 是 merge → refresh → cleanup |
| 它不是代码仓库的规划器 | 它专注于观察层，不承担代码仓库规划的职责 |

### 5.3 适用范围

- **必须遵守**：Skill 文件的"何时使用"段、关键约束声明、与其他 skill 的边界区分
- **建议遵守**：文档正文中用于界定边界和排除场景的描述
- **不适用**："它不是什么"等显式否定列表段（有意为之的 scope boundary 保留不改）；治理性硬约束中的 `不得`/`禁止`/`必须返回 blocked`

### 5.4 判断标准

改写后：核心语义等价，不丢失边界定义，不引入新概念。若肯定改写后语义模糊或边界不清，保留原句并在此段记录理由。

## 六、相关文档

- [Review / Verify 治理入口](./review-verify-handbook.md)
- [Branch / PR 治理规则](./branch-pr-governance.md)

## 七、中英混排文档去机翻味润色模式（附录）

> 来源：WT-20260614-doc-language-polish 工作追踪的逐条对校 pass。以下 8 类模式来自实际润色案例，供后续文档作者参考。

### A. 去除节标题中的英文注释 / 双语括号

将 `中文标题（English Parenthetical）` 改为纯中文标题。英文注释若有必要保留，放入正文首句。

| Before | After |
|--------|-------|
| `## 测试分层（Test Lane Taxonomy）` | `## 测试分层` |
| `### In-Gate Lanes（在 closeout gate 内运行）` | `### 关内通道（纳入 closeout 关）` |

### B. 英文表头/概念标签中文化

表格表头、概念标签从中英混排替换为纯中文，消解拼接感。

| Before | After |
|--------|-------|
| `| Lane \| 用途 \| Gate |` | `| 通道 \| 用途 \| 所属 Gate |` |
| `| Profile \| 运行 Gates \| 适用场景 |` | `| 策略 \| 执行关卡 \| 适用场景 |` |

### C. 英文术语系统性中文化

散布在正文中的英文专有名词消化为中文自然表达，用中文读者的概念习惯重新命名，而非逐词翻译。

| Before | After |
|--------|-------|
| `dogfood` | `真机验证` |
| `package-smoke` | `包体冒烟` |
| `canonical skill source` | `技能源码` |
| `operator-facing installer behavior` | `运维侧安装器行为` |

### D. 拆解英文缩写/中英混成词

将 `in-gate`、`dry-run/apply/idempotency` 等英文名词串消化为完整中文短语。

| Before | After |
|--------|-------|
| `5 个 in-gate lane + 5 个 independent lane 分层` | `5 个关内通道 + 5 个独立通道分层组织` |
| `补 dry-run/apply/idempotency 证据` | `补上预览/执行/幂等性证据` |

### E. 英式语序/句式调整为中文自然语序

将受英文 SVO 结构或从句影响的句子重写为流畅中文。

| Before | After |
|--------|-------|
| `Pre-release，Human 触发或规范化脚本` | `发布前，由人工触发或用规范化脚本执行` |
| `声明式调和。它封装 ...` | `做声明式同步。它封装 ...` |

### F. 直译/机翻句式修正

将"英文逐词翻译塞进中文句子"的痕迹重写为地道中文。

| Before | After |
|--------|-------|
| `docs-only、配置修改、小范围 analysis WT` | `纯文档、配置修改、小范围分析任务` |
| `已有 runtime field 的值保持不变` | `已有运行时字段的值保持不变` |
| `仅基于 section/field 名称匹配` | `仅基于节/字段名称匹配，不依赖版本号` |

### G. 导航链接/引用文字中文化

文档底部的导航链接文字从英文替换为中文描述。

| Before | After |
|--------|-------|
| `[Mapping Spec]` | `[映射规格]` |
| `[Legacy .aw Runtime Upgrade Runbook]` | `[旧版 .aw 运行时升级手册]` |
| `drift/conflict/unrecognized 见...` | `漂移/冲突/未识别项见...` |

### H. 运行时输出中文化

面向终端用户的 stderr/stdout 提示从英文改写为中文。

| Before | After |
|--------|-------|
| `WARNING: lightweight gate profile skips test_gate and smoke_gate.` | `WARNING: 轻量关卡策略跳过了 test_gate 和 smoke_gate。` |

### 使用优先级

- **文档正文**：所有 8 类均适用
- **代码注释/README**：A、B、C、D、G 优先
- **Python stderr/stdout**：H 适用
- **不适用**：代码标识符、API 名称、git 命令、YAML 键名等技术符号（保留原文）
