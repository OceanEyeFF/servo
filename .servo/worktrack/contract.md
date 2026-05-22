---
title: "Worktrack Contract: WT-20260521-skill-marker-reinstall-upgrade-flow"
artifact_type: worktrack-contract
worktrack_id: WT-20260521-skill-marker-reinstall-upgrade-flow
milestone_id: MS-20260521-001
baseline_branch: develop-aw
baseline_ref: develop-aw@11a61134d6ac73bea790ac34f2a76a437ec6afc2
node_type: feature
merge_required: yes
baseline_form: commit-on-feature-branch
gate_criteria: implementation + validation + policy
if_interrupted_strategy: checkpoint-or-recover
runtime_dispatch_mode: auto
derived_from_milestone: true
created: 2026-05-22T12:42:35+08:00
---

# Worktrack Contract

## Task Goal

Make the explicit `.aw/` to `.servo/` migration path converge installed skill payloads after runtime migration by reusing the existing installer update/reinstall chain. The worktrack must keep `aw.marker` as managed payload identity only, refresh markers and payload fingerprints through current install/update mechanics, and verify legacy target cleanup without adding silent runtime migration to ordinary installer commands.

## Milestone Binding

- milestone_id: MS-20260521-001
- milestone_title: .aw Runtime Seamless Upgrade
- derived_from_milestone: true
- worktrack_sequence_position: 3 / 4

## Worktrack Intake Review

- repo_fundamentals:
  - active_milestone: MS-20260521-001
  - active_worktrack: WT-20260521-skill-marker-reinstall-upgrade-flow
  - baseline_branch: develop-aw
  - baseline_ref: develop-aw@11a61134d6ac73bea790ac34f2a76a437ec6afc2
  - latest_closed_worktrack: WT-20260521-aw-to-servo-runtime-migrator
  - release/package mutation: out of scope
- snapshot_freshness:
  - control_state_latest_observed_checkpoint: 11a61134d6ac73bea790ac34f2a76a437ec6afc2
  - repo_snapshot_checkpoint: 11a61134d6ac73bea790ac34f2a76a437ec6afc2
  - milestone_backlog: MS-20260521-001 active, 2/4 complete
  - worktrack_backlog: WT-20260521-skill-marker-reinstall-upgrade-flow active
  - verdict: fresh enough for WorktrackScope.Init
- milestone_purpose_alignment:
  - This worktrack implements the reinstall/update coupling required after the explicit runtime migration entry.
  - It follows the WT-1 contract and builds on the WT-2 `migrate-runtime` command.
- historical_conflict_risk:
  - `aw.marker` must remain deploy payload identity and must not be treated as `.aw/` runtime evidence.
  - Existing update conflict blocking and bundle partial-completion semantics must not regress.
  - Runtime migration must not happen implicitly through ordinary `install`, `update`, `verify`, `diagnose`, `check_paths_exist`, or `prune --all`.
- worktrack_adjustment_recommendations: keep implementation focused on explicit `--reinstall` behavior and tests; defer operator docs and broad smoke runbook to WT-4.
- add_remove_worktrack_recommendations: none.
- intake_review_verdict: ready_for_worktrack_init
- ready_for_worktrack_init: true

## Scope In

- Extend explicit `migrate-runtime --from aw --to servo` behavior so `--yes --reinstall --backend agents|claude|bundle` runs or applies the existing update/reinstall chain after safe runtime migration.
- Ensure reinstall preflight can block before runtime mutation when update conflicts would prevent convergence.
- Preserve `aw.marker`, `legacy_target_dirs`, `legacy_skill_ids`, and `payload_fingerprint` as existing installer mechanisms.
- Add `/tmp` target repository tests for marker refresh, legacy target cleanup, payload fingerprint convergence, reinstall conflict blocking, and bundle backend behavior where feasible.
- Keep JSON/human output explicit about runtime migration result and reinstall/update result.

## Scope Out

- Do not delete `.aw/` by default.
- Do not change `aw.marker` filename or reinterpret it as runtime state.
- Do not modify package version, npm dist-tag, release tag, publish state, or release channel policy.
- Do not modify `.agents/` or `.claude/` deploy targets in the source repo.
- Do not modify `.autoworkflow/` or `.spec-workflow/` directories.
- Do not write operator docs/runbook beyond contract clarifications required by implementation; WT-4 owns docs and smoke runbook.

## Affected Surfaces

- `toolchain/scripts/deploy/bin/servo-installer.js`
- `toolchain/scripts/deploy/test_servo_installer.js`
- `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md` only if implementation reveals required clarification

## Acceptance Criteria

- `migrate-runtime --from aw --to servo --yes --reinstall --backend agents` refreshes installed managed skill payloads through the existing update chain after safe runtime migration.
- Existing update preflight conflicts block before runtime migration when `--reinstall` is requested.
- Legacy target cleanup and payload fingerprint convergence are verified with `/tmp` target repository tests.
- Bundle reinstall behavior either works via existing bundle update composition or is explicitly blocked/planned with contract-consistent evidence.
- Ordinary installer commands still do not silently migrate `.aw/` runtime state.

## Validation Requirements

- `node --test toolchain/scripts/deploy/test_servo_installer.js`
- `git diff --check`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` with retained `.servo/` tracked runtime warning if still present

## Rollback / Recovery

- If `--reinstall` cannot safely reuse the existing update chain without broad rewrite, split a follow-up worktrack instead of reimplementing marker refresh.
- If bundle semantics require a separate recovery model, preserve agents/claude behavior and record bundle as deferred or explicitly blocked with evidence.
