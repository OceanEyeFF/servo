---
title: Harness Runtime Closeout Refresh
status: active
updated: 2026-07-01
owner: servo-kernel
last_verified: 2026-07-01
---

# Harness Runtime Closeout Refresh

> 目的：固定 Worktrack closeout、repo refresh、milestone progress 写回和 pipeline advancement。Worktrack backlog 字段见 [worktrack-backlog.md](../artifact/repo/worktrack-backlog.md)，milestone 字段见 [milestone.md](../artifact/control/milestone.md)。

## Closeout Boundary

`PR` 不是闭环终点。完整 closeout：

```text
merge -> refresh repo snapshot -> update milestone progress -> cleanup -> return RepoScope
```

`closed` 进入条件：

- PR 或等效 merge 完成
- PR target、merge target 与 checkpoint target 均来自 Worktrack Contract 的 `closeout_target_ref` / `checkpoint_base_ref`，而不是当前 checkout 或默认分支名
- repo snapshot / worktrack backlog 已刷新
- milestone progress 已按 closeout 结果更新
- 临时分支或 runtime handoff 已清理或明确保留理由
- residual risks 和 next repo action 已记录

## Closeout Record

Worktrack `closeout_record` 不单独新增长期 artifact。它折叠在 `worktrack-close-skill` 的关闭报告与 `repo-refresh-skill` 的刷新交接中，并由 repo refresh 写入 repo 级 backlog / snapshot。

Closeout record 字段词汇由 [worktrack artifact entry](../artifact/worktrack/README.md#closeout-boundary) 和对应 skill 输出合同承接。本页只固定 closeout 运行语义，不复制字段清单。

## Repo Refresh

Worktrack closeout 后必须进入 `RepoScope.Refresh`，刷新 repo 慢变量：

- current branch / baseline facts
- Worktrack Branch Policy facts: `branch_source_ref`、`worktrack_branch`、`integration_target_ref`、`closeout_target_ref`、`checkpoint_base_ref`
- latest closed worktrack
- repo snapshot status
- worktrack backlog entry
- milestone progress counter
- next legal route

刷新完成后，Harness 记录当前 `git rev-parse HEAD` 到 `.servo/control-state.md` 的 `Baseline Traceability.latest_observed_checkpoint`，作为下轮跳过重复 refresh 的幂等性锚点。Milestone-derived Worktrack 的本轮 checkpoint 可以落在 Milestone integration branch；servo-managed baseline branch 只在 Milestone final acceptance 后更新。

## Runtime Artifact Maintenance

Worktrack closeout 与 Milestone final acceptance 都可能留下 stale、superseded 或滚动 runtime artifact。维护周期必须是 report-first：先盘点 `.servo` runtime artifact 和引用链，再分类 preserve / promote / archive / stale / superseded / expired 候选；只有确有必要长期呈现的内容才整理成正式文档。删除或破坏性 cleanup 需要单独批准。

Worktrack Evidence / Findings / Discovery 的清理分三段处理：Worktrack closeout 先 snapshot 或 bundle 证据并分流 finding / discovery；Milestone 结束清理聚合已关闭 Worktrack 的证据和遗留发现；Repo cleanup 再处理跨 Milestone 的 stale、orphan、superseded、expired 候选。

runtime artifact 生命周期策略由 [../artifact/runtime-artifact-lifecycle.md](../artifact/runtime-artifact-lifecycle.md) 定义。Closeout 与 refresh 必须保留 Gate verdict、closeout record、manual exception record、dispatch record，以及任何被 milestone history 或 docs truth 引用的 evidence。

## Milestone Progress

单个 worktrack 的 gate pass 只是 milestone 完成的必要条件之一。Milestone progress 只由已关闭 worktrack 的 closeout record、gate evidence、repo refresh 结果聚合而来。

goal-driven milestone 需要：

- `worktrack_list_finished`
- `milestone_gate_verdict == pass`
- `purpose_achieved`
- programmer-owned final acceptance boundary

work-collection milestone 只要求 worktrack list finished，验收下沉到各 worktrack gate。

## Pipeline Advancement

goal-driven milestone achieved 后触发 programmer handback，不自动推进 pipeline。

programmer final acceptance 发生后，`harness-skill` 执行 final acceptance writeback。该写回必须作为 milestone artifact、milestone-backlog、control-state、handback guard 与 baseline traceability 的逻辑事务处理；完成后还必须校验 backlog 不含 completed/accepted milestone 的 `(planned)` / `(active)` worktrack marker，且 control-state pipeline summary 与 backlog 计数一致。事务失败时返回 `writeback_incomplete` / `milestone_pipeline_stale`，不允许继续推进。

work-collection milestone achieved 后可自动标记 superseded，并按 pipeline priority 激活下一 planned milestone；若没有下一 planned milestone，则清空 active milestone。

任何 milestone gate `soft-fail`、`hard-fail`、`blocked` 或反作弊信号，均不得把 milestone 标记为 completed，也不得自动推进 pipeline。

## Post-Acceptance Managed-Branch Merge

goal-driven milestone 被 programmer final acceptance 后，验收事实写回不等同于已经把结果合回 `develop-servo` 或其他 managed branch。Harness 必须把 post-acceptance managed-branch merge 视为 final acceptance writeback 之后的独立受控路线。

final acceptance writeback 成功后，`harness-skill` 必须向 programmer 明示 post-acceptance merge 选择，而不是静默结束在 accepted-but-not-merged 状态。提示内容至少包含 accepted source ref、默认 managed branch（通常是 `develop-servo`）、可选的 user-specified managed branch、跳过合回的选项，以及 release/publish/tag/push/protected/deploy/destructive 边界不会被授权的说明。

该路线只在满足以下条件时可进入：

- programmer 在 post-acceptance merge prompt 中明确要求合回，或 milestone / repo operator config 明确声明已接受结果需要合回的 managed branch。
- source ref 指向已接受的 milestone branch 或等价已验收 checkpoint，且 final acceptance record、Milestone Gate verdict、manual exception record 保持可追溯。
- target branch 是 servo-managed baseline branch（如 `develop-servo`）或 programmer 指定并被 branch policy 允许的 managed branch。
- preflight 已记录 target branch、source ref、当前 worktree 状态、branch context、最终验收记录引用、Gate verdict 保留策略、checkpoint / writeback plan 和失败恢复路径。

preflight 失败时必须 stop before merge，并返回明确 blocker；不得用“已验收”绕过分支策略、受保护分支策略或未满足的证据要求。若 merge 已经发生但 post-merge writeback 未完成，Harness 必须进入 recovery / refresh 路径，记录 post-merge checkpoint、实际 merge target、恢复动作和残留风险，而不是静默继续推进 pipeline。

post-acceptance managed-branch merge 不授权 release、publish、package version、tag、dist-tag、remote push、protected branch mutation、deploy、database migration、secrets access、destructive cleanup 或跨 repo 副作用。并行 Worktrack 的 git commit 编排与 git worktree 支持不是该路线的前置能力；相关问题必须保留为独立后续范围。
