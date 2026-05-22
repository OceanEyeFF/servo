---
title: "Plan / Task Queue: WT-20260521-aw-upgrade-contract"
artifact_type: plan-task-queue
worktrack_id: WT-20260521-aw-upgrade-contract
baseline_ref: develop-aw@5335b7ecee76f9e1a001424f7865e3ab1a96c408
updated: 2026-05-22T11:32:33+08:00
---

# Plan / Task Queue

## Queue

- [x] **T1**: Map existing installer ownership, marker, legacy cleanup, payload fingerprint, and runtime `.servo/` boundaries.
- [x] **T2**: Draft `.aw` runtime upgrade contract with explicit states: `.aw` only, `.servo` exists, both present, foreign marker, malformed marker, already migrated, and dry-run.
- [x] **T3**: Define fail-closed conflict and recovery rules, including default retention or backup for `.aw/` and no default deletion.
- [x] **T4**: Define reinstall/update marker refresh requirements that reuse `aw.marker`, legacy target cleanup, and payload fingerprint mechanisms.
- [x] **T5**: Sync operator-facing docs/runbook entrypoints only where they own upgrade-path routing.
- [x] **T6**: Run focused docs/governance validation and record evidence in gate-evidence.

## Scheduling Seed

- next_recommended_task: closeout
- dispatch_package_required: false
- current_blockers: none
- execution_not_started: false
