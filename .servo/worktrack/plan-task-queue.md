---
title: "Plan / Task Queue: WT-20260521-aw-to-servo-runtime-migrator"
artifact_type: plan-task-queue
worktrack_id: WT-20260521-aw-to-servo-runtime-migrator
baseline_ref: develop-aw@e8e501d7ccb3ef3abadc2c9e8120990e4c8ac2ab
updated: 2026-05-22T12:39:03+08:00
---

# Plan / Task Queue

## Queue

- [x] **T1**: Inspect current CLI parser/dispatcher and choose the smallest explicit command integration point.
- [x] **T2**: Implement dry-run and JSON state classification for `.aw` to `.servo` runtime migration.
- [x] **T3**: Implement `--yes` copy-not-move mutation with conflict blocking and idempotence.
- [x] **T4**: Add focused `/tmp` target repository tests for state matrix and no source-tree runtime pollution.
- [x] **T5**: Run Node tests and governance checks; record evidence.

## Scheduling Seed

- next_recommended_task: closeout
- dispatch_package_required: true
- current_blockers: none
- execution_not_started: false
