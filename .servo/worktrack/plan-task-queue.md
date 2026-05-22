---
title: "Plan / Task Queue: WT-20260521-skill-marker-reinstall-upgrade-flow"
artifact_type: plan-task-queue
worktrack_id: WT-20260521-skill-marker-reinstall-upgrade-flow
baseline_ref: develop-aw@11a61134d6ac73bea790ac34f2a76a437ec6afc2
updated: 2026-05-22T15:17:06+08:00
---

# Plan / Task Queue

## Queue

- [x] **T1**: Inspect current `migrate-runtime`, `update --yes`, bundle update, marker, legacy cleanup, and payload fingerprint paths.
- [x] **T2**: Implement `--reinstall` preflight so blocking update conflicts stop before runtime migration.
- [x] **T3**: Implement `--yes --reinstall` execution by reusing existing update/reinstall chain after successful or idempotent runtime migration.
- [x] **T4**: Add `/tmp` tests for marker refresh, legacy target cleanup, payload fingerprint convergence, conflict blocking, and relevant bundle behavior.
- [x] **T5**: Run full installer tests and governance checks; record gate evidence.

## Scheduling Seed

- next_recommended_task: closeout
- dispatch_package_required: true
- current_blockers: none
- execution_not_started: false
