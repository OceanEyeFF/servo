---
title: "CodingAgent Skills Usage Guide"
status: active
updated: 2026-05-18
owner: servo-kernel
last_verified: 2026-06-13
---

# CodingAgent Skills 使用教程

> 本文档是当前 operator 主入口，介绍 Harness Skills 在 CodingAgent 中的调用方式、backend 差异和常见工作流。

## Skill 调用方式

Harness Skills 在 CodingAgent 中通过 slash command 调用：

| Skill | 用途 | 调用方式 |
|-------|------|---------|
| `repo-init-goal-skill` | 初始化 `.servo/` 并生成 Goal Charter | `/repo-init-goal-skill` |
| `harness-skill` | 启动 Harness 控制回路，逐项推进 Milestone | `/harness-skill` + 参数 |
| `repo-whats-next-skill` | 分析仓库当前状态，列出候选 Milestone | `/repo-whats-next-skill` |
| `repo-change-goal-skill` | 修改仓库目标（Goal Charter 变更） | `/repo-change-goal-skill` |
| `repo-append-request-skill` | 追加临时任务或补充需求 | `/repo-append-request-skill` |

`harness-skill` 先读取最小仓库入口，再按当前 scope 选择对应 canonical Skill。

## Backend 差异

Harness 支持两个 backend，共享同一套合同和验证标准，差异仅在部署目标目录。

| Backend | 安装命令 | 部署路径 | 定位 |
|---------|---------|---------|------|
| `agents` | `npx servo-installer install --backend agents` | `.agents/skills/` | 主路径，Codex 默认 |
| `claude` | `npx servo-installer install --backend claude` | `.claude/skills/` | Claude Code 兼容路径 |

详细 backend 差异和 runtime 配置见：
- [codex.md](./codex.md) — Codex / agents backend 专属
- [claude.md](./claude.md) — Claude Code backend 专属

## 常见工作流

### 工作流一：初始化全新仓库

```
npx servo-installer diagnose --backend agents --json
npx servo-installer install --backend agents
npx servo-installer verify --backend agents
/repo-init-goal-skill
```
→ 初始化完成后由 Repo/Milestone Orchestrator 形成第一个 approved Worktrack entry

### 工作流二：已有代码接入 Harness

```
npx servo-installer diagnose --backend agents --json
/repo-init-goal-skill
```
→ 完整步骤见 [init-with-code.md](./init-with-code.md)

### 工作流三：Milestone 编排与执行

```
/repo-whats-next-skill                    # 分析候选 Milestone
（手动确认 Milestone brief 和 Worktrack 列表）
/harness-skill                            # 启动 Harness 逐项推进
  （Harness 路由 PlanWork → 独立 Review → Close）
（Milestone 验收边界：programmer 做最终决定）
```
→ 跨模块原则见 [Harness指导思想.md](../../harness/foundations/Harness指导思想.md)，具体运行合同见对应 `SKILL.md`

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
| 新仓库从零初始化 | 本页的初始化与 approved Worktrack entry 流程 |
| 已有代码接入 Harness | [init-with-code.md](./init-with-code.md) |
| 调整目标 / 追加需求 | [goal-change-guide.md](./goal-change-guide.md) |
| Codex backend 细节 | [codex.md](./codex.md) |
| Claude Code backend 细节 | [claude.md](./claude.md) |

## 通用提示

- 安装或重装前先跑 `npx servo-installer diagnose --backend agents --json`
- 每个 Worktrack 在独立 Git 分支上执行，完成后合并回基线
- Milestone 最终验收由 programmer 做决定；handback 需要显式 unlock（不是裸"继续"）
- 目标描述应包含：最终结果、非目标范围、验收标准、约束
