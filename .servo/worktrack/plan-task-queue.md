---
title: "Plan / Task Queue: WT-20260521-aw-upgrade-docs-and-smoke"
artifact_type: plan-task-queue
worktrack_id: WT-20260521-aw-upgrade-docs-and-smoke
baseline_ref: develop-aw@2a8fbba8a71214a21b0626d1609cc0b1957926fa
updated: 2026-05-22T15:59:04+08:00
---

# Plan / Task Queue

## Queue

- [x] **T1**: Compared implemented `migrate-runtime` output/semantics against the upgrade contract and fixed the stable JSON field mismatch with compatibility aliases.
- [x] **T2**: Updated operator runbook/usage docs and navigation for `.aw` to `.servo` upgrade.
- [x] **T3**: Recorded smoke evidence for the target-state matrix and reinstall refresh path through the installer test suite.
- [x] **T4**: Ran full installer tests and governance checks; recorded gate evidence.
- [x] **T5**: Prepared worktrack closeout and programmer-owned milestone acceptance handback.

## Scheduling Seed

- next_recommended_task: closeout to `develop-aw`, then RepoScope refresh and programmer milestone acceptance handback
- dispatch_package_required: false
- current_blockers: none
- execution_not_started: false
- worktrack_tasks_complete: true
