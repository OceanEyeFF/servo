---
title: "Harness Artifact / Worktrack"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Harness Artifact / Worktrack

`docs/harness/artifact/worktrack/` 承接 `WorktrackScope` 的局部状态转移对象字段和结构化 artifact 合同。

当前入口：

- [contract.md](./contract.md)
- [self-review-contract.md](./self-review-contract.md)
- [single-acceptance-contract.md](./single-acceptance-contract.md)
- [closeout-evidence-bundle.md](./closeout-evidence-bundle.md)
- [dispatch-evidence-records.md](./dispatch-evidence-records.md)
- [composite-lane-records.md](./composite-lane-records.md)
- [plan-task-queue.md](./plan-task-queue.md)
- [dispatch-packet.md](./dispatch-packet.md)
- [gate-evidence.md](./gate-evidence.md)
- [debug-evidence.md](./debug-evidence.md)

## Closeout Boundary

Worktrack `closeout_record` 不单独新增长期 artifact。Closeout 的运行语义由 [runtime-closeout-refresh.md](../../foundations/runtime-closeout-refresh.md) 承接；稳定字段若需要长期合同，落到本目录的对应 artifact 或相关 skill 输出合同。

Closeout record 词汇至少覆盖：`worktrack_id`、`branch`、`base_ref`、`head_ref`、`merge_commit`、`pr`、`files_changed`、`acceptance_result`、`gate_verdict`、`evidence_refs`、`decision_refs`、`docs_updated`、`snapshot_refreshed`、`backlog_updated`、`cleanup_done`、`remaining_risks`、`next_repo_scope_action`。

Closeout evidence bundle 的稳定字段由 [closeout-evidence-bundle.md](./closeout-evidence-bundle.md) 承接。Dispatch provenance 的 linked record 字段由 [dispatch-evidence-records.md](./dispatch-evidence-records.md) 承接。Composite acceptance lane evidence 的 linked record 字段由 [composite-lane-records.md](./composite-lane-records.md) 承接。Milestone Gate 准备输入时应优先消费 `closeout_evidence_bundle_ref`，并保留 `complete / incomplete / contaminated / historical_gap` 状态；不得从 prose summary 合成 dispatch record 或 composite lane record。
