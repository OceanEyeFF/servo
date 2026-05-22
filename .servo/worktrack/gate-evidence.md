---
title: "Gate Evidence: WT-20260521-aw-upgrade-contract"
artifact_type: gate-evidence
worktrack_id: WT-20260521-aw-upgrade-contract
updated: 2026-05-22T11:32:33+08:00
---

# Gate Evidence

## implementation-gate

- Verdict: pass
- Evidence:
  - Added `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md`.
  - Synchronized `docs/servo-installer/README.md`, `docs/book.md`, `docs/servo-installer/runbooks/skill-deployment-maintenance.md`, `docs/servo-installer/reference/managed-files-ownership.md`, `docs/project-maintenance/usage-help/README.md`, and `docs/project-maintenance/deploy/README.md`.
  - Contract defines explicit opt-in command shape, dry-run/JSON/exit semantics, state matrix, copy/retention rules, fail-closed conflict handling, reinstall/update coupling, TUI health behavior, and test surface.
  - Read-only SubAgent inspection confirmed no existing `.aw` migration CLI is implemented and verified current `aw.marker`, `legacy_target_dirs`, payload fingerprint, update, conflict, and `.servo` health behavior against source.

## validation-gate

- Verdict: pass-with-retained-warning
- Evidence:
  - `git diff --check`: passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`: passed.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`: passed with retained plan-task-queue alignment warnings.
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`: failed on existing tracked `.servo/` runtime layer governance conflict; failure is retained and not introduced by the new docs contract.

## policy-gate

- Verdict: pass
- Evidence:
  - No package version, npm dist-tag, release tag, publish state, or release channel mutation.
  - No `.aw/` deletion or `.servo/` overwrite behavior implemented.
  - No deploy target changes under `.agents/` or `.claude/`.
  - Contract explicitly keeps `aw.marker` as installer-managed payload marker, not `.aw/` runtime evidence.
  - Contract keeps migrator implementation out of WT-1 and assigns implementation/test execution to later worktracks.

## Deferred Items

- Implementation of the migrator belongs to WT-20260521-aw-to-servo-runtime-migrator unless the programmer explicitly changes scope.
- Full `folder_logic_check.py` remains blocked by existing tracked `.servo/` runtime artifacts and should be handled by a separate governance/state cleanup decision, not by this docs contract slice.
