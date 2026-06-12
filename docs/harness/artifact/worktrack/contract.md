---
title: "Worktrack Contract"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
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
- `Branch Policy`
  - `baseline_branch`
  - `branch_source_ref`
  - `worktrack_branch`
  - `integration_target_ref`
  - `closeout_target_ref`
  - `final_baseline_branch`
  - `checkpoint_base_ref`
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

## Branch Policy

`baseline_branch` 仍是 servo-managed baseline / final checkpoint 的根基准，不得从当前 checkout 或写死默认分支名推断。Milestone branch 模型引入后，Worktrack Contract 还必须显式区分“从哪里开分支”和“收尾合到哪里”：

- `baseline_branch`: servo-managed baseline branch。用于最终 Milestone acceptance、baseline freshness、protected branch policy 和 repo-level checkpoint 比较。
- `branch_source_ref`: 创建本 Worktrack branch 的来源 ref。普通非 Milestone worktrack 通常等于 `baseline_branch@HEAD`；Milestone-derived worktrack 通常等于 active Milestone branch head。
- `worktrack_branch`: 本 Worktrack 的执行分支。
- `integration_target_ref`: 本 Worktrack closeout 的直接集成目标。Milestone-derived worktrack 默认是 active Milestone branch；非 Milestone worktrack 可为 `baseline_branch`。
- `closeout_target_ref`: close-worktrack-skill 实际用于 PR/merge/checkpoint 的目标 ref。默认等于 `integration_target_ref`。
- `final_baseline_branch`: Milestone final acceptance 后的最终主线目标；通常等于 `baseline_branch`。
- `checkpoint_base_ref`: closeout/refreshed checkpoint 与哪一个 ref 比较；Worktrack closeout 默认比较 `closeout_target_ref`，Repo/Milestone final acceptance 再比较 `baseline_branch`。

典型 Milestone-derived worktrack：

```yaml
branch_policy:
  baseline_branch: "develop"
  branch_source_ref: "ms/MS-20260605-004-branch-model@<hash>"
  worktrack_branch: "wt-20260605-worktrack-branch-source-contract"
  integration_target_ref: "ms/MS-20260605-004-branch-model"
  closeout_target_ref: "ms/MS-20260605-004-branch-model"
  final_baseline_branch: "develop"
  checkpoint_base_ref: "ms/MS-20260605-004-branch-model@<hash>"
```

若 active Milestone 尚未创建 `milestone_branch`，`init-worktrack-skill` 必须按当前批准的 Milestone branch policy 创建或同步它，或返回 blocked；不得静默从另一个 Milestone branch、随机当前分支或 stale branch 创建 Worktrack。

`branch_source_ref`、`integration_target_ref` 与 `closeout_target_ref` 都是 contract-controlled 字段。调度、分派、验证、closeout 和 repo-refresh 只能消费这些字段，不得从当前分支名反推。若实际分支来源、PR target、merge target 或 checkpoint target 与合同不一致，必须标记 `checkpoint_policy_match: no` 并进入审批或 Recover。

## Execution Policy

本节是 Worktrack Contract 的 Execution Policy canonical text。模板文件只能引用本节并保留字段清单，不应复制本节语义正文。

Execution Policy 控制本 worktrack 的执行载体选择，不替代 `ControlState` 或任务目标/范围/验收标准。

- `runtime_dispatch_mode`: 默认 `auto`（支持 `auto`/`delegated`/`current-carrier`，与 `control-state` 的 `subagent_dispatch_mode` 同组值）。
- `dispatch_mode_source`: 默认 `worktrack-contract`。
- `fallback_reason_required`: 默认 `yes`。

语义：`auto` 按 [Dispatch Decision Policy](../../foundations/dispatch-decision-policy.md) 选择 SubAgent、专用 skill、generic worker 或 current-carrier；它不表示"能分派就分派"。`delegated` 必须分派否则返回 gap/block。`current-carrier` 关闭分派。优先级：`worktrack-contract-primary` 下 `runtime_dispatch_mode` 优先；仅 `global-override` 时 `control-state` 覆盖。contract 未声明时使用 `control-state` 的 repo 默认值。`subagent_dispatch_mode_override_scope` 决定是否允许 repo 级覆盖本合同（默认不得跨过 worktrack 合同权限边界）。若因权限边界、运行时缺口或 `dispatch package unsafe` 不能分派，须记录 fallback reason，并使用 `runtime fallback` 标记运行时回退。

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
