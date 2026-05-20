---
title: "Harness Quickstart Tutorial"
status: active
updated: 2026-05-18
owner: aw-kernel
last_verified: 2026-05-18
---

# Harness Quickstart Tutorial

> 目标：让新 operator 在 10 分钟内完成 Harness 安装、初始化、第一个 Worktrack 闭环，并理解 handback 和显式 unlock 的边界。

## 前置条件

- Node.js >= 18（用于 `npx servo-installer`）
- 一个 Git 仓库（已有代码或空项目均可）
- 一个支持 slash command 的 Coding CLI（Codex 或 Claude Code）

## 第零步：诊断当前仓库状态

在安装前，先诊断目标仓库是否已安装过 Harness：

```bash
npx servo-installer diagnose --backend agents --json
```

输出示例：
```json
{"status":"not-installed","backend":"agents","target_root":"/path/to/repo"}
```

如果已安装，`diagnose` 会报告当前版本和 skill 清单。使用 `--backend claude` 检查 Claude Code 兼容路径。

## 第一步：安装 Harness Skills

**人类 operator 推荐使用 TUI 引导流程：**

```bash
npx servo-installer
```

不带参数启动 TUI，默认使用 `bundle` backend（同时部署 agents + claude）。TUI 提供六阶段引导：diagnose → preview → confirm → install → verify → summary。详见 [TUI/CLI 合同](../../servo-installer/tui/human-cli-contract.md)。

**AI agent、CI 或脚本使用 CLI：**

```bash
npx servo-installer install --backend agents
```

验证安装：

```bash
npx servo-installer verify --backend agents
```

`agents` 是当前主路径 backend。Claude Code 用户将 `--backend agents` 替换为 `--backend claude`。CLI 必须显式指定 `--backend`。

## 第二步：初始化 Harness 控制面

在 Coding CLI 中调用：

```
/set-harness-goal-skill
```

这一步会创建 `.aw/` 目录并生成 Goal Charter（`repo goal/charter`），定义仓库的长期目标、工程节点类型和系统不变量。

初始化完成后，`.aw/` 下会生成：
- `control-state.md` — Harness 控制面状态
- `goal-charter.md` — 仓库目标与约束
- `repo/` — Repo 级快照和 backlog

## 第二步补充：理解 Milestone 和 Worktrack

在启动 Harness 之前，需要理解两个核心概念：

- **Milestone（里程碑）**：一组相关 Worktrack 的集合，有明确的 `purpose`、`completion_signals` 和 `acceptance_criteria`。Milestone 不是凭空出现的 —— 它来自对仓库目标的分析和手动编排。
- **Worktrack（工作追踪）**：单个受约束的执行单元，有独立的 Git 分支、Contract、Plan/Task Queue 和 Gate Evidence。

**典型流程：**

```
1. 用 /repo-whats-next-skill 分析当前有哪些候选 Milestone
2. 手动确认 Milestone brief（目的、范围、Worktrack 列表）
3. Harness 逐个推进 Worktrack：Init → Dispatch → Verify → Judge → Close
4. 所有 Worktrack 完成后，Harness handback 等待 programmer 验收 Milestone
```

每个 Worktrack 闭环后，Milestone 进度计数器更新；所有 Worktrack 关闭后触发 Milestone 验收边界。

## 第三步：启动 Harness 执行 Worktrack

确认 Milestone 和 Worktrack 列表后，用以下标准模板调用 Harness：

```
/harness-skill
请逐项推进MileStone的既定内容。
请逐项完成已经确定的Worktrack列表的任务。
这一轮执行周期中我会给你批准30个连续执行任务的行动额度（Worktrack额度）。
你有下列的权限：
1. 开启SubAgent（AgentTeams）
2. 低危险Worktrack审批可以自行通过
3. 连续工作
4. 按需增加Worktrack任务

---

你需要额外注意下列的情形需要通知我处理：
1. 大量文件删除、系统配置修改等危险操作
2. 上下文噪声明显，提示词明显遗忘
3. 你觉得有必要由我来做决定的内容

---

如果评估到改动不完善任务明显没有完成，你可以添加Worktrack到backlog并且继续执行。
特别的，针对这个任务，MileStone的验收必须由我来做决定

---

可以开始了！谢谢你
```

**模板关键要素：**
- `Worktrack额度`：本轮允许连续执行的 Worktrack 数量（如 30、15）
- 权限声明：SubAgent 开关、低危险自动审批、连续工作、按需追加 Worktrack
- 危险操作通知：文件删除、配置修改等需要 programmer 介入
- Milestone 验收边界：明确最终验收由 programmer 做决定

Harness 收到指令后会按控制回路逐项推进每个 Worktrack（Init → Dispatch → Verify → Judge → Close）。验证方式由仓库治理文档决定；默认走 gate 验证（implementation + validation + policy 三个正交校验面）。

详细的控制回路说明见 [docs/harness/README.md](../../harness/README.md)；Worktrack 生命周期见 [docs/harness/scope/worktrack-scope.md](../../harness/scope/worktrack-scope.md)。

## 第四步：理解 Handback 和显式 Unlock 边界

### 什么是 Handback

Harness 在以下情况会停止并将控制权交还给 programmer：

- **Milestone 验收边界**：一个 Milestone 的所有 Worktrack 完成闭环后，Harness 停止等待 programmer 验收
- **审批门控**：目标变更、范围扩张或其他需要 programmer 决策的动作
- **证据门控**：所需证据缺失或矛盾，无法安全继续
- **路由阻塞**：Gate 裁决为失败或阻塞

### 什么是显式 Unlock

Handback 后，**裸"继续工作"或"继续"不构成有效的 unlock 信号**。Harness 要求 programmer 提供实质性新输入：

**有效的 unlock 信号示例：**
- 对 Milestone 的明确验收决定（"接受 MS-xxx"或"拒绝，原因：..."）
- 新的 Milestone brief 确认（"确认 Quickstart Tutorial 的 Milestone brief，请写入 pipeline"）
- 新指令加具体范围（"请初始化 WT-xxx，范围是..."）
- 权限变更声明（"批准 30 个 Worktrack 额度，允许 SubAgent"）

**无效的 unlock 信号（会被 Harness 拒绝）：**
- "继续工作"
- "继续"
- "重试"
- 对上一轮输出的纯文字摘要

### Handback 后的正确操作

```
程序员审阅 Milestone 完成状态
    ↓
验收通过？
    ├─ 是 → "接受 MS-xxx，激活下一个 Milestone"
    └─ 否 → "拒绝 MS-xxx，原因：xxx。追加 Worktrack：WT-xxx"
```

## 常见问题

### Q: Worktrack 额度用完了怎么办？

Harness 会在额度耗尽时停止并交还控制权。你可以用新的 `/harness-skill` 调用授予更多额度。

### Q: 如何查看当前 Milestone 进度？

Harness 在每轮控制回路中会自动报告 Milestone 进度。你也可以直接查看 `.aw/milestone/` 目录下的 Milestone artifact。

### Q: agents 和 claude backend 有什么区别？

`agents` 是主路径，部署到 `.agents/skills/`；`claude` 是兼容路径，部署到 `.claude/skills/`。两者共享同一套 Harness 合同和验证标准。

### Q: 如何修改仓库目标？

使用 `/repo-change-goal-skill` 或 `/repo-append-request-skill` 发起目标变更请求。目标变更需要 programmer 显式审批。

## 下一步

- 深入了解 Harness 控制回路：[docs/harness/README.md](../../harness/README.md)
- Skills 使用教程（backend 差异、调用方式、常见工作流）：[recommended-usage.md](./recommended-usage.md)
- 按 backend 查看详细差异：[codex.md](./codex.md) | [claude.md](./claude.md)
- 部署与安装详情：[deploy/README.md](../deploy/README.md)
