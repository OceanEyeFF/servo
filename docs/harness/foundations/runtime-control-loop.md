---
title: Harness Runtime Control Loop
status: active
updated: 2026-05-20
owner: servo-kernel
last_verified: 2026-05-20
---

# Harness Runtime Control Loop

> 目的：固定 Harness 从状态估计到下一合法算子的运行主循环。WorktrackScope 状态矩阵细节见 [scope/worktrack-scope.md](../scope/worktrack-scope.md)；RepoScope 管理文档见 [scope/repo-scope.md](../scope/repo-scope.md)；正式对象字段见 [artifact/](../artifact/README.md)。

## Control Chain

Harness 的最小控制链：

```text
state estimate
-> choose operator
-> bind skill or execution carrier
-> package task/info
-> dispatch
-> collect evidence
-> judge
-> update control state
```

单个 skill 的 bounded round 只限制本轮局部动作。未命中正式 stop condition 时，控制器继续推进到下一合法状态转移。

## Scope Owners

`RepoScope` 管 repo 长期参考信号与慢变量；`WorktrackScope` 管局部状态转移。RepoScope 管理文档见 [scope/repo-scope.md](../scope/repo-scope.md)；WorktrackScope 的状态定义、状态矩阵和异常路径由 [scope/worktrack-scope.md](../scope/worktrack-scope.md) 承接。本页只保留 runtime 主循环和连续推进规则。

Milestone Pipeline 是 RepoScope 下的中短期目标队列：多个 milestone 可处于 `planned`，同一时刻仅一个 `active`。goal-driven milestone 完成采用 `worktrack_list_finished AND purpose_achieved`，其中 `purpose_achieved` 前置独立 Milestone Gate。详细字段见 [milestone.md](../artifact/control/milestone.md) 和 [milestone-backlog.md](../artifact/repo/milestone-backlog.md)。

## Normal Loop

```text
RepoScope.Observe
-> RepoScope.Decide
-> Worktrack Intake Review
-> WorktrackScope.Init
-> WorktrackScope.Observe
-> WorktrackScope.Decide
-> WorktrackScope.Dispatch
-> WorktrackScope.Implement
-> WorktrackScope.Verify
-> WorktrackScope.Judge
-> WorktrackScope.Close 或 WorktrackScope.Recover
-> RepoScope.Refresh
-> RepoScope.Observe
```

有 active milestone 时，每个 current worktrack 都走自己的完整闭环；milestone 通过这些独立闭环的累计结果形成聚合进度、Milestone Gate 输入和最终完成判定。

`Worktrack Intake Review` 是 RepoScope.Decide 输出的一部分，不是 WorktrackScope 内部执行步骤。从 active milestone 派生 current worktrack 前，必须形成 `worktrack_intake_review`，并覆盖：

- `repo_fundamentals`
- `snapshot_freshness`
- `milestone_purpose_alignment`
- `historical_conflict_risk`
- `worktrack_adjustment_recommendations`
- `add_remove_worktrack_recommendations`
- `intake_review_verdict`
- `ready_for_worktrack_init`

只有 `intake_review_verdict = ready_for_worktrack_init` 且 `ready_for_worktrack_init = true` 时，才允许进入 `WorktrackScope.Init`。`refresh_required` 回到 RepoScope 观察/刷新；`adjust_worktracks` 回到 milestone/worktrack backlog 调整或 programmer 审批；`blocked` 停止并暴露继续阻塞项。

当请求命中 complex-project trigger 时，还必须先消费 `complex_project_entry_gate`。这是 Milestone-side blocking gate，不是固定 heavy mode；canonical guard term: not fixed heavy mode。scanner output is evidence, not verdict。gate handoff 必须携带 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与 `reinforcement_milestone_recommendation`。`milestone_blocking_decision` 中存在 `block_create`、`block_upsert`、`block_activate` 或 `block_derive_worktrack` 时，监督器不得绑定对应 initializer。弱文档命中且理解不足时，默认路由到 reinforcement documentation / project-understanding milestone。Worktrack execution modes `normal`、`autoreview`、`yolo` 不替代该阻断。

## Continuous Execution

默认语义是连续推进，而不是每完成一个 skill round 就自动 handback。

当 programmer 明确指示连续执行时，`Worktrack Close` 只是 repo refresh 或 milestone progress update 的状态刷新点，不默认触发 handback。连续推进仍受当前 `Worktrack Contract`、authority boundary、autonomy budget 和 stop conditions 约束。

`autonomy_budget` 每开启一个 autonomous slice 消费 1 个单位。budget 耗尽后不得自动开启新 slice，必须 handback。

## Stop Conditions

最小 stop conditions：

- 需要 programmer 批准的 goal change、scope expansion、destructive action 或 authority boundary
- goal-driven milestone 激活前的结构化 brief 需要 programmer 确认
- complex-project entry gate 对 create / upsert / activate / derive-worktrack 给出 Milestone-side blocker
- `worktrack_intake_review` 缺失、过时、字段不全，或 `intake_review_verdict` 为 `refresh_required` / `adjust_worktracks` / `blocked`
- 必需 artifact / evidence 缺失、过时或互相冲突
- `Gate` 给出 `soft-fail`、`hard-fail` 或 `blocked`
- host runtime 没有合法 execution carrier / dispatch shell
- 下一动作越过已批准输入、`Worktrack Contract` 或 repo baseline
- 同一交接边界在连续无变化轮次中再次被确认
- Milestone 验收边界命中：`milestone_acceptance_verdict == achieved` 或 `blocked`

"skill 已返回结构化结果"不构成 stop condition。无专门 skill 时进入 fallback execution carrier；runtime dispatch shell 缺位报告为 `runtime gap`。
