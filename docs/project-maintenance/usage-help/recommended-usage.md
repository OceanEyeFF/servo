---
title: "CodingAgent Skills Usage Guide"
status: active
updated: 2026-05-18
owner: aw-kernel
last_verified: 2026-05-18
---

# CodingAgent Skills 使用教程

> 本文档面向已读过 [quickstart.md](./quickstart.md) 的 operator，深入介绍 Harness Skills 在 CodingAgent 中的调用方式、backend 差异和常见工作流。
> **新用户先读 [quickstart.md](./quickstart.md) 10 分钟快速入门。**

## Skill 调用方式

Harness Skills 在 CodingAgent 中通过 slash command 调用：

| Skill | 用途 | 调用方式 |
|-------|------|---------|
| `set-harness-goal-skill` | 初始化 `.aw/` 并生成 Goal Charter | `/set-harness-goal-skill` |
| `harness-skill` | 启动 Harness 控制回路，逐项推进 Milestone | `/harness-skill` + 参数 |
| `repo-whats-next-skill` | 分析仓库当前状态，列出候选 Milestone | `/repo-whats-next-skill` |
| `repo-change-goal-skill` | 修改仓库目标（Goal Charter 变更） | `/repo-change-goal-skill` |
| `repo-append-request-skill` | 追加临时任务或补充需求 | `/repo-append-request-skill` |

`harness-skill` 的标准调用模板见 [quickstart.md 第三步](./quickstart.md#第三步启动-harness-执行-worktrack)。

## Backend 差异

Harness 支持两个 backend，共享同一套合同和验证标准，差异仅在部署目标目录。

| Backend | 安装命令 | 部署路径 | 定位 |
|---------|---------|---------|------|
| `agents` | `npx aw-installer install --backend agents` | `.agents/skills/` | 主路径，Codex 默认 |
| `claude` | `npx aw-installer install --backend claude` | `.claude/skills/` | Claude Code 兼容路径 |

详细 backend 差异和 runtime 配置见：
- [codex.md](./codex.md) — Codex / agents backend 专属
- [claude.md](./claude.md) — Claude Code backend 专属

## 常见工作流

### 工作流一：初始化全新仓库

```
npx aw-installer diagnose --backend agents --json
npx aw-installer install --backend agents
npx aw-installer verify --backend agents
/set-harness-goal-skill
```
→ 完整步骤见 [init-greenfield.md](./init-greenfield.md)

### 工作流二：已有代码接入 Harness

```
npx aw-installer diagnose --backend agents --json
/set-harness-goal-skill
```
→ 完整步骤见 [init-with-code.md](./init-with-code.md)

### 工作流三：Milestone 编排与执行

```
/repo-whats-next-skill                    # 分析候选 Milestone
（手动确认 Milestone brief 和 Worktrack 列表）
/harness-skill                            # 启动 Harness 逐项推进
  （Harness 自动执行 Init → Dispatch → Verify → Judge → Close）
（Milestone 验收边界：programmer 做最终决定）
```
→ Harness 控制回路详解见 [docs/harness/README.md](../../harness/README.md)

### 工作流四：追加需求或调整方向

```
/repo-append-request-skill               # 追加临时任务
/repo-change-goal-skill                  # 调整仓库目标
```
→ 完整步骤见 [goal-change-guide.md](./goal-change-guide.md)

## 场景速查

以下场景表用于快速定位细化文档：

| 场景 | 文档 |
|------|------|
| 新仓库从零初始化 | [init-greenfield.md](./init-greenfield.md) |
| 已有代码接入 Harness | [init-with-code.md](./init-with-code.md) |
| 调整目标 / 追加需求 | [goal-change-guide.md](./goal-change-guide.md) |
| Codex backend 细节 | [codex.md](./codex.md) |
| Claude Code backend 细节 | [claude.md](./claude.md) |

## 通用提示

- 安装或重装前先跑 `npx aw-installer diagnose --backend agents --json`
- 每个 Worktrack 在独立 Git 分支上执行，完成后合并回基线
- Milestone 最终验收由 programmer 做决定；handback 需要显式 unlock（不是裸"继续"）
- 目标描述应包含：最终结果、非目标范围、验收标准、约束
