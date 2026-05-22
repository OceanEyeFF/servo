---
title: "Worktrack Contract: WT-20260521-aw-upgrade-docs-and-smoke"
artifact_type: worktrack-contract
worktrack_id: WT-20260521-aw-upgrade-docs-and-smoke
milestone_id: MS-20260521-001
baseline_branch: develop-aw
baseline_ref: develop-aw@2a8fbba8a71214a21b0626d1609cc0b1957926fa
node_type: docs
merge_required: yes
baseline_form: commit-on-docs-branch
gate_criteria: review + policy
if_interrupted_strategy: checkpoint-or-recover
runtime_dispatch_mode: auto
derived_from_milestone: true
created: 2026-05-22T15:20:35+08:00
---

# Worktrack Contract

## Task Goal

Synchronize operator-facing documentation, command contract details, and smoke evidence for the explicit `.aw/` to `.servo/` upgrade path now implemented in `servo-installer`.

## Milestone Binding

- milestone_id: MS-20260521-001
- milestone_title: .aw Runtime Seamless Upgrade
- derived_from_milestone: true
- worktrack_sequence_position: 4 / 4

## Worktrack Intake Review

- repo_fundamentals:
  - active_milestone: MS-20260521-001
  - active_worktrack: WT-20260521-aw-upgrade-docs-and-smoke
  - baseline_branch: develop-aw
  - baseline_ref: develop-aw@2a8fbba8a71214a21b0626d1609cc0b1957926fa
  - latest_closed_worktrack: WT-20260521-skill-marker-reinstall-upgrade-flow
  - release/package mutation: out of scope
- snapshot_freshness:
  - control_state_latest_observed_checkpoint: 2a8fbba8a71214a21b0626d1609cc0b1957926fa
  - repo_snapshot_checkpoint: 2a8fbba8a71214a21b0626d1609cc0b1957926fa
  - milestone_backlog: MS-20260521-001 active, 3/4 complete
  - worktrack_backlog: WT-20260521-aw-upgrade-docs-and-smoke active
  - verdict: fresh enough for WorktrackScope.Init
- milestone_purpose_alignment:
  - This final worktrack syncs operator docs and smoke evidence for the implemented migration and reinstall behavior.
- historical_conflict_risk:
  - Docs must not promise `.aw` deletion, silent `.servo` overwrite, or implicit migration from ordinary installer commands.
  - Contract JSON field names must match implemented output closely enough for operator/CI use.
- worktrack_adjustment_recommendations: keep docs and smoke evidence focused; milestone acceptance remains programmer-owned.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true

## Scope In

- Update `.aw` runtime upgrade contract to match implemented command output and reinstall semantics.
- Add or update operator runbook/usage docs for legacy `.aw` users.
- Record smoke evidence from implemented `/tmp` target tests and full installer suite.
- Update entrypoint navigation if new docs are added.

## Scope Out

- Do not change package version, npm dist-tag, release tag, publish state, or release channel policy.
- Do not delete `.aw/` by default or add cleanup commands.
- Do not add new migration behavior beyond documentation/clarification unless a small mismatch fix is required.
- Do not modify `.agents/` or `.claude/` deploy targets in the source repo.
- Do not modify `.autoworkflow/` or `.spec-workflow/` directories.

## Affected Surfaces

- `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md`
- `docs/servo-installer/runbooks/`
- `docs/project-maintenance/usage-help/`
- `docs/book.md` and relevant README entrypoints if needed
- `toolchain/scripts/deploy/bin/servo-installer.js` only for small doc/field mismatch fixes if needed

## Acceptance Criteria

- Docs explain default dry-run, `--json`, `--yes`, `--reinstall`, conflict blocking, idempotence, `.aw` retention, and recovery boundaries.
- Smoke evidence documents the implemented `/tmp` target matrix and full installer test result.
- Contract stable fields align with actual implementation or explicitly document compatibility aliases.
- Governance checks pass except the retained tracked `.servo/` runtime warning.

## Validation Requirements

- `node --test toolchain/scripts/deploy/test_servo_installer.js`
- `git diff --check`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` with retained `.servo/` tracked runtime warning if still present

## Rollback / Recovery

- If docs reveal an implementation/contract mismatch that cannot be fixed narrowly, append a follow-up worktrack instead of broadening this docs/smoke closeout.
