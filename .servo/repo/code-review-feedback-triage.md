---
title: "Code Review Feedback Triage"
artifact_type: "repo-review-feedback-triage"
generated_from: "harness-skill"
updated: "2026-05-03"
owner: "servo-kernel"
---
# Code Review Feedback Triage

## Control Signal

- source_review: external Code Review report for `develop-aw -> develop-main`, received 2026-05-03
- recommended_backlog_item: `P0-055/code-review-feedback-hardening`
- recommended_route: `harness-skill -> init-worktrack-skill -> focused review/inventory -> bounded implementation if confirmed -> review/test/rule evidence -> gate-skill -> close-worktrack-skill -> repo-refresh-skill`
- approval_required: false for local code-quality/security/test maintainability work that stays inside the listed files and does not alter release/package/runtime-retirement boundaries
- blocked_boundaries:
  - no package metadata, version, packlist, npm, tag, GitHub Release, remote push, PR/merge, branch deletion, default promotion, Python file deletion or runtime retirement
  - no broad `servo-installer.js` command-module split unless separately scoped
  - no repository-wide Python deletion

## Finding Triage

| ID | Review claim | Local observation | Triage |
|---|---|---|---|
| CR-001 | `run_test_gate` is very large and should be split. | `toolchain/scripts/test/closeout_acceptance_gate.py` has `run_test_gate` from line 311 to line 1107. Explorer confirmed about 795 lines. | Real maintainability debt. Track as P2/deferred; not a current merge blocker by itself. |
| CR-002 | ZIP parser is inline in `servo-installer.js`. | `findZipEndOfCentralDirectory`, `zipEntries`, `zipEntryData`, and `safeExtractZipBuffer` are inline around lines 799-880. | Real maintainability/testability debt. Track as P1/P2; only implement as a bounded module-extraction slice if package files/packlist impact is explicitly handled. |
| CR-003 | `downloadGithubArchive` lacks archive size cap and retry. | Current implementation collects all chunks and `Buffer.concat(chunks)` without byte cap or retry. | Real security/stability hardening. Treat as the highest-priority actionable item for P0-055. |
| CR-004 | Claude mutating lifecycle test combines install/update/prune. | `test_servo_installer_claude_mutating_lifecycle_is_node_owned_without_python` covers all three operations in one test. | Real test-diagnostics debt. Track as low-risk test-only cleanup in P0-055 if time permits. |
| CR-005 | `servo-installer.js` is very large. | File is 3793 lines. | Real long-term debt, but too broad for a small review-feedback task. Defer to separate P2 worktrack. |
| CR-006 | GitHub repo/SHA constants are duplicated across JS/Python. | Patterns exist in `servo-installer.js` and `adapter_deploy.py`; Explorer also noted broader duplicated deploy constants. | Real during dual-track migration, but shared-schema extraction is architectural. Defer until retirement/package boundary planning unless a focused constant is touched by CR-003. |
| CR-007 | Test archive fixture traverses file tree twice. | `createGithubArchiveFromSource` calls separate `listDirectories` and `listFiles`. | Real minor test-only inefficiency. Optional cleanup only if touched by ZIP module/test work. |

## Proposed P0-055 Scope

- Verify the seven Code Review findings against current `develop-aw`.
- Implement only bounded fixes that reduce near-term risk before `develop-aw -> develop-main` review:
  - add GitHub archive download size limit and retry/backoff behavior with deterministic tests
  - split the Claude mutating lifecycle no-Python sentinel test into independent install, update and prune tests if it remains low-risk
  - optionally extract inline ZIP parsing helpers from `servo-installer.js` only if package/packlist impact remains controlled
- Record deferred findings explicitly as P1/P2/P3 debt instead of treating them as merge blockers.

## Acceptance Criteria

- Finding-by-finding review evidence is recorded.
- Any changed deploy behavior has targeted Node tests and no-Python sentinel coverage where applicable.
- Existing deploy parity tests still pass for touched surfaces.
- Docs are updated only if verified operator-facing behavior changes.
- Gate evidence explicitly states whether the original Code Review recommendations are satisfied, deferred, or downgraded.

## Suggested Validation

- `node --check toolchain/scripts/deploy/bin/servo-installer.js`
- `node --test toolchain/scripts/deploy/test_servo_installer.js`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest toolchain.scripts.deploy.test_adapter_deploy`
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- `git diff --check`
