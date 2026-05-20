---
title: "Repo Snapshot Status"
artifact_type: "repo-snapshot-status"
generated_from: "repo-refresh-skill"
updated: "2026-05-20"
owner: "servo-kernel"
---

# Repo Snapshot Status

## Baseline

- branch: develop-aw
- checkpoint: 94a570044eb651fa2f1aa9ecef3cdb119bc2f537
- checkpoint_type: milestone-acceptance
- verified_at: 2026-05-20

## Current Repo State

- active_milestone: none
- active_worktrack: none
- latest_closed_worktrack: WT-20260520-runtime-dispatch-profile-claude-deepseek
- latest_accepted_milestone: MS-20260520-001

## Recent Milestones Completed

- [completed] MS-20260520-001 (Harness Runtime State Freshness & Worktrack Intake Governance)
  - milestone_kind: goal-driven
  - priority: 0
  - progress: 3 / 3 worktracks complete
  - completed:
    - WT-20260520-milestone-acceptance-writeback-transaction
    - WT-20260520-worktrack-intake-review-gate
    - WT-20260520-runtime-dispatch-profile-claude-deepseek
  - purpose: 修复 Harness 在 milestone 验收写回、.aw 基本面刷新、Worktrack 初始化前审查，以及 Claude/Deepseek 环境 SubAgent 分派倾向上的控制缺口
  - accepted_by: programmer
  - accepted_at: 2026-05-20

- [completed] MS-20260519-004 (TUI Full-Flow Implementation)
  - milestone_kind: goal-driven
  - priority: 12
  - progress: 4 / 4 worktracks + 7 refinement commits
  - accepted_by: programmer
  - accepted_at: 2026-05-20

- [completed] MS-20260519-003 (Human-First TUI Contract)
  - milestone_kind: goal-driven
  - priority: 11
  - progress: 3 / 3 worktracks
  - accepted_by: programmer
  - accepted_at: 2026-05-19

- [completed] MS-20260519-005 (servo-installer Documentation System)
  - milestone_kind: goal-driven
  - priority: 10.5
  - progress: 3 / 3 worktracks
  - accepted_by: programmer
  - accepted_at: 2026-05-19

- [completed] MS-20260519-002 (Distribution Safety & Version Traceability)
  - milestone_kind: goal-driven
  - priority: 10
  - progress: 3 / 3 worktracks
  - accepted_by: programmer
  - accepted_at: 2026-05-19

## Branch And Release Baseline Observations

- harness_baseline_branch: develop-aw
- harness_baseline_head: 94a570044eb651fa2f1aa9ecef3cdb119bc2f537
- develop_main_head: 2c4fab873fedd786f38a6de5cd3e6591f0d2c7f5
- local_master_head: 9a98815627f06285132077ab9675e7fceafb557a
- origin_master_head: 2c4fab873fedd786f38a6de5cd3e6591f0d2c7f5
- origin_develop_main_head: 2c4fab873fedd786f38a6de5cd3e6591f0d2c7f5
- origin_develop_aw: deleted (2026-05-20) — confirmed erroneously pushed, programmer authorized deletion from GitHub + Gitee
- remote_branches: origin/develop-main (only remote branch; origin/develop-aw no longer exists)
- branch_role_note: develop-aw is the Harness-managed baseline for development. develop-main is the release branch (v0.5.2-rc.3). No remote tracking for develop-aw.

## Release Fact Observations

- current_harness_baseline_source_tuple:
  - root_package_version: 0.5.1-rc.1
  - deploy_scaffold_version: 0.5.1-rc.1
  - note: develop-aw release docs still describe 0.5.1-rc.1 facts
- release_branch_source_tuple (develop-main):
  - root_package_version: 0.5.2-rc.3
  - latest_publish: v0.5.2-rc.3 (commit 0d9c6e2)
  - publish_workflow: PR #54 merged
- npm_registry:
  - latest: 0.5.1
  - next: 0.5.2-rc.1 (may be out of date — not rechecked)
- pending_decision:
  - Whether and when to resynchronize develop-aw with develop-main release facts is a programmer-owned branch-role decision.
  - Dedicated deployment repository design and repo rename are preserved as later planning topics.

## Governance Signals

- branch_environment_guard: satisfied — current checkout develop-aw matches baseline_branch
- docs_freshness:
  - develop-aw release docs still describe 0.5.1-rc.1 facts
  - develop-main contains 0.5.2-rc.3 release fact docs
  - last_doc_catch_up_checkpoint: 052ad0dd (stale — 93 commits behind HEAD)

## Pipeline Summary

- completed: 15 milestones
- active: 0
- planned: 1
  - MS-20260520-002 (Repo Rename to servo): 3 worktracks, priority 0, awaiting activation

## Recommended Next Route

- RepoScope.Observe: no active milestone; await programmer direction for next milestone planning
