---
title: "Recommended Harness Usage"
status: active
updated: 2026-05-17
owner: aw-kernel
last_verified: 2026-05-17
---
# Recommended Harness Usage

> 本文档是 Harness 使用场景的路由入口。先判断你的场景，再跳转到对应的细化文档。

## 场景速查

| 场景 | 适用条件 | 细化文档 |
|------|---------|---------|
| **新用户快速入门** | 第一次使用 Harness，需要 10 分钟上手指南 | [quickstart.md](./quickstart.md) |
| 新仓库，从零初始化 Harness | 空项目，无 `.aw/` 目录 | [init-greenfield.md](./init-greenfield.md) |
| 已有代码，接入 Harness | 已有代码库，需要初始化 `.aw/` | [init-with-code.md](./init-with-code.md) |
| 已有目标，需要追加功能或调整方向 | 现有 Goal Charter 需要修改 | [goal-change-guide.md](./goal-change-guide.md) |
| 已有授权的工作项，需要完整走一个 Worktrack | 已有明确的请求，需要 contract → plan → 执行 → closeout | 通过 `$harness-skill` 进入 Harness 控制回路 |
| 确认 backend 差异（Codex vs Claude） | Coding CLI 内切换 backend | [codex.md](./codex.md)、[claude.md](./claude.md) |

## 场景摘要

### 新仓库从零初始化
1. 安装 Harness Skills（`npx aw-installer install --backend agents`）
2. 调用 `$set-harness-goal-skill` 初始化 `.aw/` 并生成 Goal Charter
3. 验证 `.aw/` 目录就绪
→ 完整步骤见 [init-greenfield.md](./init-greenfield.md)

### 已有代码接入 Harness
1. 诊断当前仓库状态
2. 生成 `.aw/repo/discovery-input.md`
3. 初始化 Harness 控制面
→ 完整步骤见 [init-with-code.md](./init-with-code.md)

### 变更仓库目标
1. 判断变更类型（追加目标 / 调整方向 / 修改验收标准）
2. 调用 `$repo-append-request-skill` 或创建新 Goal Charter
→ 完整步骤见 [goal-change-guide.md](./goal-change-guide.md)

### 完整 Worktrack 闭环
1. Harness 自动执行 Init → Dispatch → Verify → Judge → Close
2. 程序员在 handback 点验收 Milestone
→ 详细流程见 [../../harness/scope/repo-scope.md](../../harness/scope/repo-scope.md)

## 通用提示

- 目标描述应包含：最终结果、非目标范围、验收标准、约束
- 安装或重装前先跑 `aw-installer diagnose --backend agents --json`
- 每个 Worktrack 在独立 Git 分支上执行，完成后合并回基线
- Milestone 最终验收由程序员做决定
