---
title: "Code Review Feedback Round 2 Triage"
artifact_type: "repo-review-feedback-triage"
generated_from: "harness-skill"
updated: "2026-05-03"
owner: "servo-kernel"
---
# Code Review Feedback Round 2 Triage

## Control Signal

- source_review: external Code Review issue confirmation report for `develop-aw -> develop-main`, received 2026-05-03
- recommended_backlog_item: `P0-056/code-review-feedback-round2-adjudication`
- recommended_route: `harness-skill -> init-worktrack-skill -> focused verification/adjudication -> split implementation routing if confirmed -> review/test/rule evidence -> gate-skill`
- approval_required: false for local read-only verification, prioritization and backlog decomposition
- implementation_approval_boundary:
  - no package metadata, version, packlist, npm, tag, GitHub Release, remote push, PR/merge, branch deletion, default backend promotion, Python file deletion or runtime retirement
  - GitHub-source changes are no longer assumed to be required migration work; expansion, mandatory SHA policy, default repo policy changes, deprecation, warning, or removal all require explicit trust-contract adjudication
  - broad module decomposition must be split into separate worktracks, not bundled with security fixes

## Incoming Findings

| ID | Incoming claim | Initial harness triage |
|---|---|---|
| CR-001 | CLI update parser logic is heavily duplicated and marked blocking. | Real likely debt, but "blocking" severity needs independent adjudication. Candidate refactor slice: shared update parser helper with regression parity tests. |
| CR-002 | `servo-installer.js` single file is too large. | Real long-term maintainability debt. Not a single merge-blocking fix; split by command/helper area in future slices. |
| CR-003 | Error propagation mixes issue arrays and thrown errors. | Real architectural debt. Needs design decision because current split maps read-only observation vs mutating operations. |
| CR-004 | GitHub archive SHA256 is optional. | Real behavior, but GitHub source is now treated as optional/possibly-retirable surface rather than a required migration gap. Do not make SHA mandatory unless a later product decision keeps and hardens this surface. |
| CR-005 | ZIP extraction lacks uncompressed-size cap. | Real security hardening candidate. Highest priority implementation candidate if verified. |
| CR-006 | ZIP magic numbers/offsets lack named constants/comments. | Real maintainability debt; should be paired with ZIP hardening or module extraction. |
| CR-007 | GitHub source only supports `agents` backend. | Real current boundary and now intentionally not a must-fill gap. Do not expand to Claude unless a later product decision keeps GitHub source as supported surface. |
| CR-008 | `defaultGithubRepo` hardcodes upstream repo. | Real behavior documented in trust boundary. Since GitHub source may be frozen or retired, default repo policy should be handled only inside that product decision, not as a standalone fix. |
| CR-009 | `targetRootForBackend` uses backend-specific if/else. | Real small extensibility debt; low-risk refactor if backend table is introduced. |
| CR-010 | `main()` migration comment is stale. | Real docs/comment cleanup; safe small fix. |
| CR-011 | `safeExtractZipBuffer` theoretical TOCTOU window. | Low practical risk; consider during ZIP module hardening. |
| CR-012 | ZIP extraction repeats `mkdirSync(dirname)` for same directories. | Low-priority performance cleanup; not merge-blocking. |
| CR-013 | Naming can be improved. | Low-priority readability cleanup. |
| CR-014 | Node test file is flat. | Real test maintainability debt; broad test reorganization should be separate. |
| CR-015 | `captureConsoleLog` monkey-patches global `console.log`. | Real concurrency risk only if parallel tests are enabled; candidate focused test-helper hardening. |

## Proposed P0-056 Scope

- Independently verify the 15 reported findings against current `develop-aw@2c6377c`.
- Separate true defects from intentional/currently documented migration boundaries.
- Produce a split plan with at most one small implementation slice selected for immediate follow-up.
- Recommended first implementation candidate, if verified: CR-005 uncompressed ZIP size cap plus CR-006 constants/comments because both touch the same security-sensitive ZIP reader area.
- Recommended non-implementation adjudication items: CR-004 optional SHA, CR-007 Claude GitHub-source and CR-008 default GitHub repo are reclassified after programmer confirmation as `freeze-or-retire-github-source` candidates, not required fixes.

## Programmer Direction Update - 2026-05-03

- decision_signal: GitHub source is not considered necessary for the core Python-runtime replacement path.
- routing:
  - do not expand GitHub source to Claude as a migration requirement.
  - do not make SHA256 mandatory as an isolated follow-up.
  - do not tune default GitHub repo behavior as an isolated follow-up.
  - keep existing GitHub source behavior maintenance-only unless/until a separate product decision chooses retention, warning/deprecation, or removal.
- impact_on_findings:
  - CR-004: `freeze-or-retire-github-source`, not fix-now.
  - CR-007: `freeze-or-retire-github-source`, not fix-now.
  - CR-008: `freeze-or-retire-github-source`, not fix-now.

## Acceptance Criteria

- Every CR-001 through CR-015 has one of: `fix-now`, `split-later`, `intentional-boundary`, `needs-approval`, or `reject/duplicate`.
- Any `fix-now` item has a bounded file list and validation plan.
- Any trust-contract change is explicitly marked approval-gated before code work.
- P0-052 package/runtime retirement remains blocked and is not consumed by this task.
