---
title: Harness Runtime Closeout Refresh
status: active
updated: 2026-05-20
owner: servo-kernel
last_verified: 2026-05-20
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
- repo snapshot / worktrack backlog 已刷新
- milestone progress 已按 closeout 结果更新
- 临时分支或 runtime handoff 已清理或明确保留理由
- residual risks 和 next repo action 已记录

## Closeout Record

Worktrack `closeout_record` 不单独新增长期 artifact。它折叠在 `close-worktrack-skill` 的关闭报告与 `repo-refresh-skill` 的刷新交接中，并由 repo refresh 写入 repo 级 backlog / snapshot。

Closeout record 字段词汇由 [worktrack artifact entry](../artifact/worktrack/README.md#closeout-boundary) 和对应 skill 输出合同承接。本页只固定 closeout 运行语义，不复制字段清单。

## Repo Refresh

Worktrack closeout 后必须进入 `RepoScope.Refresh`，刷新 repo 慢变量：

- current branch / baseline facts
- latest closed worktrack
- repo snapshot status
- worktrack backlog entry
- milestone progress counter
- next legal route

刷新完成后，Harness 记录当前 `git rev-parse HEAD` 到 `.servo/control-state.md` 的 `Baseline Traceability.latest_observed_checkpoint`，作为下轮跳过重复 refresh 的幂等性锚点。

## Milestone Progress

Milestone progress 只由已关闭 worktrack 的 closeout record、gate evidence、repo refresh 结果聚合而来。单个 worktrack 的 gate pass 不等于 milestone 完成。

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
