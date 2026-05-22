---
title: "Worktrack Contract: WT-20260521-aw-upgrade-contract"
artifact_type: worktrack-contract
worktrack_id: WT-20260521-aw-upgrade-contract
milestone_id: MS-20260521-001
baseline_branch: develop-aw
baseline_ref: develop-aw@5335b7ecee76f9e1a001424f7865e3ab1a96c408
node_type: feature
merge_required: yes
baseline_form: commit-on-feature-branch
gate_criteria: implementation + validation + policy
if_interrupted_strategy: checkpoint-or-recover
runtime_dispatch_mode: auto
derived_from_milestone: true
created: 2026-05-22T10:11:07+08:00
---

# Worktrack Contract

## Task Goal

Define the explicit `.aw/` runtime seamless upgrade contract for legacy target repositories so later implementation can add a safe migrator without re-deciding policy. The contract must cover detection, `.servo/` conflict blocking, backup or retention, dry-run reporting, idempotence, recovery guidance, and the reinstall/update path that refreshes managed skills markers and payload fingerprints.

## Milestone Binding

- milestone_id: MS-20260521-001
- milestone_title: .aw Runtime Seamless Upgrade
- derived_from_milestone: true
- worktrack_sequence_position: 1 / 4

## Worktrack Intake Review

- repo_fundamentals:
  - active_milestone: MS-20260521-001
  - active_worktrack: WT-20260521-aw-upgrade-contract
  - baseline_branch: develop-aw
  - baseline_ref: develop-aw@5335b7ecee76f9e1a001424f7865e3ab1a96c408
  - latest_accepted_milestone: MS-20260520-002
  - release/package mutation: out of scope
- snapshot_freshness:
  - control_state_latest_observed_checkpoint: 5335b7ecee76f9e1a001424f7865e3ab1a96c408
  - repo_snapshot_checkpoint: 5335b7ecee76f9e1a001424f7865e3ab1a96c408
  - milestone_backlog: MS-20260521-001 active
  - worktrack_backlog: WT-20260521-aw-upgrade-contract active
  - verdict: fresh enough for WorktrackScope.Init
- milestone_purpose_alignment:
  - This worktrack establishes the upgrade policy and acceptance contract required before implementing migration behavior.
  - It directly supports the milestone completion signals for explicit migration, conflict blocking, retention/backup, dry-run, and reinstall marker refresh.
- historical_conflict_risk:
  - Existing rename milestone preserved `.autoworkflow/` and `.spec-workflow/`; this worktrack must not reinterpret those directories as upgrade targets.
  - Existing installer marker remains named `aw.marker`; this worktrack may define compatibility semantics but must not force a marker rename.
  - Existing release policy forbids package version, npm dist-tag, release tag, publish state, or release channel mutation.
- worktrack_adjustment_recommendations: keep current worktrack as contract-first slice before migrator implementation.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true

## Scope In

- Define operator-facing and implementation-facing `.aw` upgrade contract.
- Specify how the installer detects `.aw/`, existing `.servo/`, both-present state, foreign marker, malformed marker, and previously migrated state.
- Specify dry-run output requirements for copy, backup, block, recovery, and reinstall/update actions.
- Specify idempotence and safe rerun requirements.
- Specify default retention/backup behavior for user-owned `.aw/` runtime state.
- Specify that `.servo/` conflicts block by default unless an explicit recovery path is selected.
- Specify how existing `aw.marker`, legacy target cleanup, and payload fingerprint mechanisms participate in reinstall/update after migration.
- Identify implementation and smoke-test surfaces for later worktracks.

## Scope Out

- Do not implement the migrator in this worktrack.
- Do not delete user-owned `.aw/` contents by default.
- Do not silently overwrite existing `.servo/`.
- Do not modify package version, npm dist-tag, release tag, publish state, or release channel policy.
- Do not treat `.agents/` or `.claude/` deploy targets as source truth.
- Do not modify `.autoworkflow/` or `.spec-workflow/` directories.

## Affected Surfaces

- `docs/servo-installer/contracts/`
- `docs/servo-installer/runbooks/`
- `docs/project-maintenance/usage-help/`
- `toolchain/scripts/deploy/bin/servo-installer.js`
- `toolchain/scripts/deploy/test_servo_installer.js`
- `product/harness/adapters/*/skills/*/payload.json` only if contract references for marker or legacy target semantics require synchronization

## Acceptance Criteria

- A stable upgrade contract exists and distinguishes `.aw/` runtime state from installer-managed skill payload.
- Ordinary init/install/update does not silently mutate `.aw/` into `.servo/`.
- Dry-run requirements include planned copy, backup/retention, block, recovery, and reinstall/update actions.
- `.servo/` conflict handling is fail-closed by default.
- `.aw/` deletion remains explicit and outside default behavior.
- Contract explains reuse of `aw.marker`, legacy target cleanup, and payload fingerprint mechanisms.
- Later implementation worktracks have clear test cases for `.aw` only, `.servo` exists, both present, foreign marker, malformed marker, dry-run, idempotence, and backup recovery.

## Validation Requirements

- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- Focused Node tests only if executable installer behavior is changed.
- `git diff --check`

## Rollback / Recovery

- If the contract conflicts with existing installer ownership or marker semantics, stop and route to WorktrackScope.Recover for split or scope correction.
- If implementation is needed to make the contract meaningful, defer implementation to WT-20260521-aw-to-servo-runtime-migrator rather than expanding this slice.
