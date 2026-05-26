---
title: "Model Runtime Support Boundary"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# Model Runtime Support Boundary

> Purpose: record the tested model/runtime support boundary for Servo without turning observed compatibility into a permanent certification claim.

Servo is designed as a repo-side contract layer. The stable contract is the artifact/skill protocol in this repository; model runtimes are execution carriers that may differ in tool shells, SubAgent support, context handling, and permission behavior.

## Tested Support

As of 2026-05-26, Servo workflows have been exercised with generally good support on these model/runtime families:

| Runtime family | Observed support | Notes |
| --- | --- | --- |
| Deepseek V4 Pro | Good | Suitable for Harness control-loop work when the surrounding CLI/tool shell exposes the required filesystem and git operations. |
| Deepseek V4 Lite | Good | Suitable for lighter Harness and documentation work; use stricter verification for broad implementation changes. |
| Claude | Good | Supported through the `claude` backend compatibility lane and repo-local `.claude/skills/` payload. |
| Pi | Good | Treated as an execution carrier compatibility observation; require the same artifact and gate evidence as other carriers. |
| GPT-5.5 | Good | Suitable for complex control, implementation, review, and recovery work when available through Codex-compatible tooling. |
| GPT-5.4 / CodeX | Good | Current primary Codex-facing lane for `agents` backend workflows and repo-local `.agents/skills/` payload. |

These observations mean the model/runtime family has been used successfully with Servo workflows. They do not bypass Worktrack contracts, gate evidence, or repo governance checks.

## Boundary

Model support is not a substitute for:

- `servo-installer verify` proving deploy target alignment
- Worktrack Contract scope, non-goals, and acceptance criteria
- test/review/rule evidence
- Milestone final acceptance by the programmer
- release-channel approval for npm publication

When a runtime cannot prove SubAgent dispatch support, Harness should use the dispatch decision policy and record a current-carrier fallback rather than claiming delegated execution.

## Where To Look Next

- Codex / agents usage: [../../project-maintenance/usage-help/codex.md](../../project-maintenance/usage-help/codex.md)
- Claude backend usage: [../../project-maintenance/usage-help/claude.md](../../project-maintenance/usage-help/claude.md)
- Dispatch carrier policy: [dispatch-decision-policy.md](./dispatch-decision-policy.md)
- Runtime dispatch contract: [runtime-dispatch-contract.md](./runtime-dispatch-contract.md)
