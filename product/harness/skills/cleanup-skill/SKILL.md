---
name: servo-cleanup-skill
description: 当需要对 repo 执行限定范围的清理操作（stale backlog 条目归档、已完成 milestone/worktrack 的本地分支清理）时，使用这个技能。它是 repo 维护层面的清理 worker，不执行破坏性操作，不修改 remote，不删除未确认的 artifact。
---

# Servo Cleanup 技能

## 概览

本技能是 Harness 执行平面的 repo 清理 worker。它负责执行两类安全的清理操作：

1. **backlog 过期引用清理**：将 worktrack-backlog 中已完成条目归档到 worktrack-history，保持 backlog 精简。
2. **已完成 milestone/worktrack 的本地分支清理**：删除已闭环的 `ms/*` 和 `wt/*` 本地分支。

本技能设计为低风险、可复核的清理操作；不执行 `git push --delete`、不修改 remote、不删除 `.servo/` artifact 文件、不触碰 protected 分支。

## 何时使用

当满足以下任一条件时使用：

- Worktrack-backlog 体量过大（如超过 100 条已完成条目），需要归档清理
- 本地分支过多（如超过 50 个 stale 分支），需要清理已完成 milestone/worktrack 的分支
- Milestone closeout 后，对应 `ms/*` 分支可安全删除
- 周期性 repo 维护

不适用于：

- 删除未完成或 active 状态的 worktrack 分支
- 删除 develop/master/main 等 protected 分支
- 删除 remote 分支（`git push --delete`）
- 删除 `.servo/milestone/` 或 `.servo/worktrack/` artifact 文件

## 工作流

### 1. Backlog 清理

1. 读取 `.servo/repo/worktrack-backlog.md` 和 `.servo/repo/worktrack-history.md`。
2. 识别 backlog 中所有 `[done]`、`[resolved]` 状态的条目。
3. 对于 history 中已存在的条目（按 worktrack_id 匹配），从 backlog 中移除。
4. 对于 history 中不存在的条目，先在 history 中追加，再从 backlog 移除。
5. 清理后，backlog 中仅保留 `[active]`、`[blocked]`、`[deferred]` 条目及当前 active milestone 的 pending worktrack。
6. 若 backlog 清理后条目数为 0，active_worktrack 标记为 `N/A`。

### 2. 本地分支清理

1. 列出所有本地 `ms/*` 分支。
   - 检查对应 milestone 是否在 `.servo/repo/milestone-history.md` 中且状态为 `completed`。
   - 若已完成：删除本地分支（`git branch -d`）。
   - 若当前 active milestone（从 `.servo/control-state.md` 读取），跳过。

2. 列出所有本地 `wt/*` 分支。
   - 检查对应 worktrack 是否在 `.servo/repo/worktrack-history.md` 或清理后的 backlog 中标记为 `done`。
   - 若已完成：删除本地分支（`git branch -d`）。
   - 若当前 active worktrack，跳过。

3. 白名单保护：
   - `develop`、`master`、`main`、`develop-aw`、`develop-servo`、`develop-main` 永不可删除。
   - 当前 active milestone branch（从 control-state 读取）永不可删除。
   - 当前检出的分支永不可删除。
   - 所有 `origin/*` remote-tracking 分支不参与清理。

### 3. 生成清理报告

输出结构化清理报告，至少包含：

- 清理前 backlog 条目数 / 清理后条目数
- 已归档到 history 的条目列表
- 已删除的本地分支列表
- 被白名单保护的跳过分支列表
- 未处理的条目（如有）

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。

- **不删除 remote 分支**：本技能只操作本地分支（`git branch -d`），不执行 `git push --delete`。
- **不删除 artifact 文件**：`.servo/milestone/` 和 `.servo/worktrack/` 下的文件永不删除。
- **不删除 protected 分支**：develop、master、main 及 active milestone branch 永不可删除。
- **不删除未确认条目**：backlog 中 `active`、`blocked`、`deferred` 条目不参与清理。
- **`git branch -d` 而非 `-D`**：使用 safe delete，如果分支未完全合并则跳过并报告。
- **操作前必须 dry-run**：先输出将要执行的操作列表，等待确认后再执行。在非交互模式下，low-risk 清理（仅 backlog 清理）可自动执行。
- **操作后必须验证**：执行后重新读取 backlog 和 branch list，确认清理结果与预期一致。

## 预期输出

- `cleanup_type`：backlog_only / branches_only / full
- `backlog_before_count` / `backlog_after_count`
- `archived_entries`：已归档的 worktrack_id 列表
- `deleted_branches`：已删除的本地分支列表
- `skipped_branches`：被白名单保护的跳过分支
- `errors`：清理过程中的错误
- `recommendations`：建议的后续动作
