---
title: "Code Review Feedback Round 3 Triage"
artifact_type: "repo-review-feedback-triage"
generated_from: "harness-skill"
updated: "2026-05-04"
owner: "servo-kernel"
---
# Code Review Feedback Round 3 Triage

## Control Signal

- source_review: external Code Review report for `feature-remove-python-deploy-code -> develop-main`, received 2026-05-04
- recommended_backlog_item: `P0-067/code-review-feedback-round3-check`
- append_classification: new worktrack
- recommended_route: `harness-skill -> init-worktrack-skill -> focused feedback verification -> bounded implementation only for confirmed low-risk items -> review/test/rule evidence -> gate-skill`
- approval_required: false for local read-only verification and bounded code/docs/test cleanup inside the listed feedback items
- implementation_approval_boundary:
  - no npm publish, dist-tag mutation, tag push, GitHub Release, remote push, PR/merge, branch deletion, version bump, release-channel mutation, package metadata change, default backend promotion, or repository-wide Python deletion.
  - no broad `servo-installer.js` modularization in this task.
  - no mandatory SHA256 policy, GitHub-source product policy change, or Claude GitHub-source expansion.
  - no blanket removal of `python` / `.py` documentation references; retained repo-local reference, parity, governance, and test Python references must be distinguished from stale package/runtime claims.

## Incoming Findings

| ID | Incoming claim | Initial harness triage |
|---|---|---|
| CR3-S1 | Minimal ZIP parser checks entry size but does not validate CRC32. | Real likely gap. `servo-installer.js` reads ZIP headers and sizes but no current `CRC32` / `crc` validation was found. Candidate `fix-now` or explicit trust-boundary limitation after focused verification. |
| CR3-S2 | GitHub archive buffer is loaded fully into memory with 500 MiB cap. | Known and already partially mitigated by P0-055 archive download cap and P0-056 extraction cap. Classify as `acceptable-current-boundary` unless new evidence shows CI/container risk. |
| CR3-S3 | `writeDeployedTextFile` always calls `chmodSync`. | Needs verification. Candidate low-risk cleanup only if mode checks are portable and tests stay focused. |
| CR3-A1 | `servo-installer.js` is too large and should be split. | Real long-term maintainability debt, but too broad for this check task. Classify as `split-later`; do not bundle with round3 verification. |
| CR3-A2 | `copyAssetSpec(spec) { return spec; }` in Node `deploy_aw.js` is an empty hook. | Real small readability issue. Candidate low-risk `fix-now`: remove the hook or add a concise intent comment. |
| CR3-P1 | EOCD search is linear over the ZIP comment window. | Not actionable. Current search window is bounded and tiny for CLI usage. Classify as `reject/no-fix`. |
| CR3-P2 | Template parsing runs regex checks per line. | Already uses module-level regex constants in `deploy_aw.js`; file size is small. Classify as `reject/no-fix` unless verification finds repeated construction elsewhere. |
| CR3-Q1 | `closeout_acceptance_gate.py` no-Python sentinel uses POSIX `#!/bin/sh`, weak on Windows. | Real cross-platform test portability gap. Candidate `split-later` or docs limitation; implementation needs a Windows-specific sentinel contract and should not be bundled with ZIP integrity unless selected deliberately. |
| CR3-Q2 | `runNodeOwnedOrWrapper` name retains stale wrapper semantics. | Real readability cleanup after P0-052 removed package/runtime Python fallback. Candidate low-risk `fix-now` if exported test API and callers are updated together. |
| CR3-Q3 | Docs may retain stale Python references. | Needs targeted verification. Search must distinguish legitimate repo-local Python reference/governance docs from stale package/runtime fallback claims. Candidate docs-only cleanup if stale claims are confirmed. |

## Proposed P0-067 Scope

- Verify every CR3 finding against the current branch and existing P0-055/P0-056/P0-052 evidence.
- Produce a finding-by-finding classification: `fix-now`, `split-later`, `acceptable-current-boundary`, `reject/no-fix`, or `needs-approval`.
- Recommended first implementation candidates if confirmed:
  - add CRC32 verification to the minimal ZIP parser, or document the exact limitation if implementation risk is too high for this slice.
  - rename `runNodeOwnedOrWrapper` to current Node-only semantics and update focused tests/exports.
  - remove or explain `copyAssetSpec`.
  - clean only verified stale package/runtime Python doc references.
- Keep Windows sentinel compatibility as a separate candidate unless this task explicitly selects it and adds platform-aware validation.

## Acceptance Criteria

- CR3-S1 through CR3-Q3 each has an explicit classification and rationale.
- Any `fix-now` item has a bounded file list, focused regression coverage, and no release/remote/package metadata impact.
- If CRC32 is implemented, tests cover at least one mismatched-entry-CRC ZIP fixture.
- If docs are changed, stale package/runtime Python claims are removed while legitimate repo-local Python reference/governance/test references remain intact.
- Gate evidence states which Code Review recommendations were satisfied, deferred, rejected, or left approval-gated.

## Suggested Validation

- `node --check toolchain/scripts/deploy/bin/servo-installer.js`
- `node --check toolchain/scripts/deploy/test_servo_installer.js`
- `node --test toolchain/scripts/deploy/test_servo_installer.js`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_set_harness_goal_deploy_aw_node.py -q` if `deploy_aw.js` changes
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py` if docs/governance paths change
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py` if docs/governance text changes
- `git diff --check`
