---
title: "Gate Evidence: WT-20260521-skill-marker-reinstall-upgrade-flow"
artifact_type: gate-evidence
worktrack_id: WT-20260521-skill-marker-reinstall-upgrade-flow
updated: 2026-05-22T15:17:06+08:00
---

# Gate Evidence

## implementation-gate

- Verdict: pass
- Evidence:
  - `migrate-runtime --from aw --to servo --yes --reinstall` now preflights the existing update plan before runtime mutation.
  - Agents/Claude reinstall uses the existing `applyUpdateContext(buildNodeBackendContext(...))` path.
  - Bundle reinstall uses the existing `runBundleUpdateYes(...)` composition.
  - The implementation preserves `aw.marker` as payload identity and reuses existing `legacy_target_dirs`, `legacy_skill_ids`, and `payload_fingerprint` mechanics.

## validation-gate

- Verdict: pass
- Evidence:
  - `node --test --test-name-pattern 'migrate-runtime|parseNodeMigrateRuntimeArgs' toolchain/scripts/deploy/test_servo_installer.js` passed.
  - `node --test toolchain/scripts/deploy/test_servo_installer.js` passed: 145/145 tests.
  - `git diff --check` passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py` passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py` passed with retained plan-task-queue alignment warnings.

## policy-gate

- Verdict: pass_with_retained_repo_warning
- Evidence:
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py` failed only on retained tracked `.servo/` runtime-layer content (`FL001`, `FL007`), matching prior worktrack evidence.
  - Tests use `/tmp` target repositories and do not create source-tree `.aw/`, `.servo/`, `.agents/`, or `.claude/` runtime state.

## Deferred Items

- WT-4 owns operator docs/runbook and broader upgrade smoke documentation.
