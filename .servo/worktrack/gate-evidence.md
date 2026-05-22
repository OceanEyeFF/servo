---
title: "Gate Evidence: WT-20260521-aw-to-servo-runtime-migrator"
artifact_type: gate-evidence
worktrack_id: WT-20260521-aw-to-servo-runtime-migrator
updated: 2026-05-22T12:39:03+08:00
---

# Gate Evidence

## implementation-gate

- Verdict: pass
- Evidence:
  - Added Node-owned `migrate-runtime --from aw --to servo` CLI path in `toolchain/scripts/deploy/bin/servo-installer.js`.
  - Default and `--json` paths are read-only; `--yes` performs copy-not-move into `.servo`.
  - Existing `.servo` without the migration sentinel blocks; successful migration writes `.servo/.servo-installer-aw-migration.json` for safe rerun idempotence.
  - Runtime migration target root validation no longer requires the target repository to also be a harness payload source.

## validation-gate

- Verdict: pass
- Evidence:
  - `node --test --test-name-pattern 'migrate-runtime|parseNodeMigrateRuntimeArgs' toolchain/scripts/deploy/test_servo_installer.js` passed.
  - `node --test toolchain/scripts/deploy/test_servo_installer.js` passed: 142/142 tests.
  - `git diff --check` passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py` passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py` passed with retained plan-task-queue alignment warnings.

## policy-gate

- Verdict: pass_with_retained_repo_warning
- Evidence:
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` failed only on retained tracked `.servo/` runtime-layer content (`FL001`, `FL007`), matching the pre-existing repository warning from the prior worktrack.
  - No `.aw`, `.servo`, `.agents`, `.claude`, `.autoworkflow`, or `.spec-workflow` runtime target was mutated by tests; runtime migration tests use `/tmp` target repositories.

## Deferred Items

- WT-3 owns reinstall marker refresh refinements beyond preserving existing update/install behavior.
