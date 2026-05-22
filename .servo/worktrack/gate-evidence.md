---
title: "Gate Evidence: WT-20260521-aw-upgrade-docs-and-smoke"
artifact_type: gate-evidence
worktrack_id: WT-20260521-aw-upgrade-docs-and-smoke
updated: 2026-05-22T15:59:04+08:00
---

# Gate Evidence

## implementation-gate

- Verdict: pass
- Evidence:
  - Added `target_root`, `verdict`, `planned_actions`, `backup_policy`, `blocking_issues`, and `recovery_hints` to `migrate-runtime` JSON summaries while preserving existing implementation detail fields.
  - Updated `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md` to describe implemented dry-run, `--json`, `--yes`, `--reinstall`, conflict blocking, idempotence, and retention semantics.
  - Added `docs/servo-installer/runbooks/aw-runtime-upgrade-runbook.md` and linked it from `docs/servo-installer/README.md`, project maintenance deploy/usage entrypoints, and `docs/book.md`.

## validation-gate

- Verdict: pass
- Evidence:
  - `node --check toolchain/scripts/deploy/bin/servo-installer.js` passed.
  - `git diff --check` passed before governance verification.
  - `node --test --test-name-pattern 'migrate-runtime|parseNodeMigrateRuntimeArgs' toolchain/scripts/deploy/test_servo_installer.js` passed: 11 pass, 134 skipped.
  - `node --test toolchain/scripts/deploy/test_servo_installer.js` passed: 145 pass.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py` passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py` passed with retained artifact-alignment warnings.

## policy-gate

- Verdict: pass-with-retained-repo-warning
- Evidence:
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` failed only on the retained tracked `.servo/` runtime/install/mount conflict (`FL001`, `FL007`), which predates this worktrack and was already recorded in earlier MS-20260521-001 closeouts.
  - No package version, release tag, npm dist-tag, publish state, `.aw` deletion behavior, deploy target source rewrite, or `.autoworkflow` / `.spec-workflow` mutation was introduced.

## Deferred Items

- Milestone final acceptance remains programmer-owned.
- Repository-level snapshot refresh and final checkpoint update are deferred until after the worktrack is merged to `develop-aw`.
