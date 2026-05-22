---
title: "Closeout Record - WT-20260521-skill-marker-reinstall-upgrade-flow"
artifact_type: worktrack-closeout-record
worktrack_id: WT-20260521-skill-marker-reinstall-upgrade-flow
milestone_id: MS-20260521-001
generated_from: init-worktrack-skill
updated: 2026-05-22T15:17:06+08:00
---

# Closeout Record

## Worktrack Summary

- worktrack_id: WT-20260521-skill-marker-reinstall-upgrade-flow
- milestone_id: MS-20260521-001
- node_type: feature
- baseline_ref: develop-aw@11a61134d6ac73bea790ac34f2a76a437ec6afc2
- closeout_checkpoint: pending

## Gate

- verdict: pass_with_retained_repo_warning
- implementation-gate: pass
- validation-gate: pass
- policy-gate: pass_with_retained_repo_warning

## Changes

- Added real `--reinstall` behavior to `migrate-runtime --from aw --to servo`.
- Added preflight blocking so update conflicts stop before `.aw` is copied into `.servo`.
- Reused existing update composition for agents, claude, and bundle backends instead of reimplementing marker refresh.
- Added `/tmp` target repository tests for managed marker refresh, payload fingerprint convergence, preflight conflict blocking before runtime copy, and bundle two-backend reinstall behavior.

## Verification

- PASS: `node --test --test-name-pattern 'migrate-runtime|parseNodeMigrateRuntimeArgs' toolchain/scripts/deploy/test_servo_installer.js`
- PASS: `node --test toolchain/scripts/deploy/test_servo_installer.js` (145/145)
- PASS: `git diff --check`
- PASS: `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- PASS: `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- RETAINED FAILURE: `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` reports pre-existing tracked `.servo/` runtime-layer content (`FL001`, `FL007`).

## Closeout Status

- execution_started: true
- closeout_ready: true
