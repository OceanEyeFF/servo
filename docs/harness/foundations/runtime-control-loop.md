---
title: Harness Runtime Control Loop
status: active
updated: 2026-06-04
owner: servo-kernel
last_verified: 2026-06-04
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

Milestone Review Gate route guard 是从 active goal-driven milestone 派生 Worktrack 的硬前置。`worktrack_intake_review` 必须携带 `milestone_review_gate_ready`、`latest_review_status`、`milestone_review_count`、`latest_review_checkpoint`、`effective_review_pass` 与 `review_invalidated_by`。只有 `latest_review_status = effective_pass`、`milestone_review_count >= 1`、`effective_review_pass = true`、`latest_review_checkpoint` 非空且无失效项时，才允许进入 `WorktrackScope.Init`。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全必须阻断 Worktrack Init/Dispatch，并暴露 `milestone_review_gate_not_ready`。

当请求命中 complex-project trigger 时，还必须先消费 `complex_project_entry_gate`。这是 Milestone-side blocking gate，不是固定 heavy mode；canonical guard term: not fixed heavy mode。scanner output is evidence, not verdict。gate handoff 必须携带 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与结构化 `reinforcement_milestone_recommendation`。`milestone_blocking_decision` 中存在 `block_create`、`block_upsert`、`block_activate` 或 `block_derive_worktrack` 时，监督器不得绑定对应 initializer。unresolved gate blocking default: missing, blank, placeholder, pending, or incomplete gate 不能解释为 `clear` 或 `not_applicable`。弱文档命中且理解不足时，默认路由到 reinforcement documentation / project-understanding milestone；`needed = true` 或 `blocks_implementation_until_resolved = true` 阻断实现型 Worktrack 派生。Worktrack execution modes `normal`、`autoreview`、`yolo` 不替代该阻断。

## Single-Entry Routing

`harness-skill` 是唯一闭环 supervisor。Operator 可以从同一个入口提出“查看状态”“讨论候选方向”“打开 Milestone”“继续当前 Worktrack”“验证收口”或“准备 release”等不同意图；入口不得因此拆出第二个 controller、第三个 Scope 或新的并行状态机。

启动后，supervisor 先 hydration 当前 `.servo/control-state.md`，再读取最小必要的 repo、milestone、worktrack 和 risk signals，形成 route estimate：

- `user_input`: operator 当前意图、是否包含创建/激活/继续/验证/release 等信号。
- `repo_state`: `.servo` 是否存在、baseline 是否新鲜、handback 是否锁定、分支守卫是否通过。
- `milestone_state`: 是否有 active milestone、是否已达到 final acceptance handback、是否存在 planned candidates。
- `worktrack_state`: 是否有 active worktrack、queue 是否可继续、gate/closeout 是否待处理。
- `risk_signals`: 是否涉及 release/publish/tag、破坏性操作、长期 truth 写回、跨目录治理、权限升级或高不确定调研。
- `approval_signals`: programmer 是否明确批准目标变更、milestone 创建/激活、worktrack 初始化、连续推进、委派或外部副作用。

这些信号只能选择 workflow path 和 stop/approval semantics；最终仍由 Harness 正常控制链选择 Scope、Function、Skill 或 execution carrier。Profile / operator-facing mode 只是 route hint，例如 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive。它不拥有独立 gate，不写长期 truth，不绕过 Worktrack Contract，不把 candidate milestone 或 candidate worktrack 解释成已批准执行范围。

当 route hint 与正式 artifact 或审批边界冲突时，以正式 artifact、Gate evidence、Control State authority 和 programmer approval 为准；route hint 必须降级为 handback 或 blocked observation。

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
