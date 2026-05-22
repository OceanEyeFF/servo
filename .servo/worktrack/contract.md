---
title: "Worktrack Contract: WT-20260521-aw-to-servo-runtime-migrator"
artifact_type: worktrack-contract
worktrack_id: WT-20260521-aw-to-servo-runtime-migrator
milestone_id: MS-20260521-001
baseline_branch: develop-aw
baseline_ref: develop-aw@e8e501d7ccb3ef3abadc2c9e8120990e4c8ac2ab
node_type: feature
merge_required: yes
baseline_form: commit-on-feature-branch
gate_criteria: implementation + validation + policy
if_interrupted_strategy: checkpoint-or-recover
runtime_dispatch_mode: auto
derived_from_milestone: true
created: 2026-05-22T11:35:19+08:00
---

# Worktrack Contract

## Task Goal

Implement the explicit `.aw/` to `.servo/` runtime migrator entry for `servo-installer`, following [docs/servo-installer/contracts/aw-runtime-upgrade-contract.md]. The migrator must be opt-in, dry-run by default, fail closed on `.servo/` conflicts, preserve `.aw/` by default, support explicit mutation with `--yes`, and include `/tmp` target repository tests for the key state matrix.

## Milestone Binding

- milestone_id: MS-20260521-001
- milestone_title: .aw Runtime Seamless Upgrade
- derived_from_milestone: true
- worktrack_sequence_position: 2 / 4

## Worktrack Intake Review

- repo_fundamentals:
  - active_milestone: MS-20260521-001
  - active_worktrack: WT-20260521-aw-to-servo-runtime-migrator
  - baseline_branch: develop-aw
  - baseline_ref: develop-aw@e8e501d7ccb3ef3abadc2c9e8120990e4c8ac2ab
  - latest_closed_worktrack: WT-20260521-aw-upgrade-contract
  - release/package mutation: out of scope
- snapshot_freshness:
  - control_state_latest_observed_checkpoint: e8e501d7ccb3ef3abadc2c9e8120990e4c8ac2ab
  - repo_snapshot_checkpoint: e8e501d7ccb3ef3abadc2c9e8120990e4c8ac2ab
  - milestone_backlog: MS-20260521-001 active, 1/4 complete
  - worktrack_backlog: WT-20260521-aw-to-servo-runtime-migrator active
  - verdict: fresh enough for WorktrackScope.Init
- milestone_purpose_alignment:
  - This worktrack implements the explicit migration entry required by milestone completion signals.
  - It follows the contract slice completed in WT-20260521-aw-upgrade-contract.
- historical_conflict_risk:
  - Existing `aw.marker` is payload identity and must not be reinterpreted as `.aw/` runtime evidence.
  - Existing ordinary install/update behavior must not silently migrate runtime state.
  - Existing release policy forbids package version, npm dist-tag, release tag, publish state, or release channel mutation.
- worktrack_adjustment_recommendations: keep implementation focused on runtime migration and tests; defer marker reinstall refinement to WT-3.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true

## Scope In

- Add explicit CLI entry for `.aw/` to `.servo/` runtime migration.
- Implement dry-run/default preview and `--json` read-only output.
- Implement `--yes` mutation path with copy-not-move semantics.
- Preserve `.aw/` by default; do not delete it.
- Block when `.servo/` exists or when source/destination state is unsafe.
- Add idempotence handling for already migrated state.
- Add `/tmp` target repository tests for `.aw` only, `.servo` exists, both present, malformed path, dry-run, successful mutation, and rerun behavior.

## Scope Out

- Do not implement default `.aw/` cleanup.
- Do not modify package version, npm dist-tag, release tag, publish state, or release channel policy.
- Do not modify `.agents/` or `.claude/` deploy targets.
- Do not modify `.autoworkflow/` or `.spec-workflow/` directories.
- Do not implement WT-3 reinstall marker refresh beyond preserving existing update/install behavior.

## Affected Surfaces

- `toolchain/scripts/deploy/bin/servo-installer.js`
- `toolchain/scripts/deploy/test_servo_installer.js`
- `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md` only if implementation reveals required clarification

## Acceptance Criteria

- `servo-installer migrate-runtime --from aw --to servo` or equivalent explicit command exists.
- Default and `--json` modes are read-only.
- `--yes` copies `.aw/` to `.servo/` only when safe.
- Existing `.servo/` blocks by default.
- Re-running after successful migration is safe.
- Tests cover state matrix without creating runtime state under the source repo.

## Validation Requirements

- `node --test toolchain/scripts/deploy/test_servo_installer.js`
- `git diff --check`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` with retained `.servo/` tracked runtime warning if still present

## Rollback / Recovery

- If the migration command would need destructive `.aw/` deletion, stop and split a cleanup worktrack.
- If test coverage requires broad TUI behavior changes, defer TUI prompt integration to WT-4 unless it is necessary to keep CLI/TUI safety equivalent.
