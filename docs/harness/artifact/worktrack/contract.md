---
title: "Worktrack Contract"
status: active
updated: 2026-05-20
owner: aw-kernel
last_verified: 2026-05-20
---
# Worktrack Contract

定义单个 `Worktrack` 的局部状态转移合同。

## 上游输入

`WorktrackContract` 是执行前边界对象：用户讨论、已批准需求、append request、repo goal、恢复路径或人工授权均须先收束进本合同，再展开为 `PlanTaskQueue`，不得直接变为执行计划。收束时至少明确已批准目标、工作范围、非目标、验收标准、约束条件、风险与依赖、验证要求。未确认事实应作为风险/阻塞/待审批项暴露，不得猜测补全。

最少应包含：

- `Node Type`（从 Goal Charter 的 Engineering Node Map 绑定）
  - `type`
  - `source_from_goal_charter`
  - `baseline_form`
  - `merge_required`
  - `gate_criteria`
  - `if_interrupted_strategy`
- `Execution Policy`
  - `runtime_dispatch_mode`
  - `dispatch_mode_source`
  - `allowed_values`
  - `fallback_reason_required`
- `Worktrack Intake Review`
  - `worktrack_intake_review`
  - `repo_fundamentals`
  - `snapshot_freshness`
  - `milestone_purpose_alignment`
  - `historical_conflict_risk`
  - `worktrack_adjustment_recommendations`
  - `add_remove_worktrack_recommendations`
  - `intake_review_verdict`
  - `ready_for_worktrack_init`
- 任务目标
- 工作范围
- 非目标
- 影响模块
- 计划中的 next state
- 验收条件
- 约束条件
- 验证要求
- 回滚条件

## Execution Policy

本节是 Worktrack Contract 的 Execution Policy canonical text。模板文件只能引用本节并保留字段清单，不应复制本节语义正文。

Execution Policy 控制本 worktrack 的执行载体选择，不替代 `ControlState` 或任务目标/范围/验收标准。

- `runtime_dispatch_mode`: 默认 `auto`（支持 `auto`/`delegated`/`current-carrier`，与 `control-state` 的 `subagent_dispatch_mode` 同组值）。
- `dispatch_mode_source`: 默认 `worktrack-contract`。
- `fallback_reason_required`: 默认 `yes`。

语义：`auto` 按 [Dispatch Decision Policy](../../foundations/dispatch-decision-policy.md) 选择 SubAgent、专用 skill、generic worker 或 current-carrier；它不表示"能委派就委派"。`delegated` 必须委派否则返回 gap/block。`current-carrier` 关闭委派。优先级：`worktrack-contract-primary` 下 `runtime_dispatch_mode` 优先；仅 `global-override` 时 `control-state` 覆盖。contract 未声明时使用 `control-state` 的 repo 默认值。`subagent_dispatch_mode_override_scope` 决定是否允许 repo 级覆盖本合同（默认不得跨过 worktrack 合同权限边界）。若因权限边界、运行时缺口或 `dispatch package unsafe` 不能委派，须记录 fallback reason，并使用 `runtime fallback` 标记运行时回退。

## Worktrack Intake Review

本节记录 RepoScope.Decide 在进入 WorktrackScope.Init 前形成的 intake gate 结论。它回答“这条 worktrack 现在是否仍应初始化并执行”，不替代 Worktrack Contract 的目标、范围或验收标准。

当 worktrack 来自 active milestone（`derived_from_milestone: true`）时，本节为必填；非 milestone 派生的修复/恢复路径若无该输入，必须在合同中写明原因。

必填字段：

- `worktrack_intake_review`: intake review 记录标识或摘要。
- `repo_fundamentals`: 当前 active milestone、baseline、已关闭 worktrack、目标/非目标和禁止项的基本面检查。
- `snapshot_freshness`: Repo Snapshot/Status、Harness Control State、milestone-backlog、worktrack-backlog 与 git HEAD 是否足够新鲜。
- `milestone_purpose_alignment`: 候选 worktrack 与 active milestone 的 purpose、completion signals、acceptance criteria 的一致性。
- `historical_conflict_risk`: 与刚关闭 worktrack、历史决策、文档真相、未解决阻塞项或 handback 边界的冲突风险。
- `worktrack_adjustment_recommendations`: 保持、拆分、合并、改写、推迟或阻塞当前 worktrack 的建议。
- `add_remove_worktrack_recommendations`: 新增、移除或重排 worktrack 的建议；无变化时写 `none`。
- `intake_review_verdict`: `ready_for_worktrack_init` / `refresh_required` / `adjust_worktracks` / `blocked`。
- `ready_for_worktrack_init`: 布尔值，只能在 verdict 为 `ready_for_worktrack_init` 且无阻塞时为 true。

若 verdict 不是 `ready_for_worktrack_init`，`init-worktrack-skill` 不得创建分支、播种队列或交给执行载体；必须把控制权路由回 RepoScope 的观察、刷新、worktrack 调整或 handback 路径。
