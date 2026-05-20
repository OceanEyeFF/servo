---
title: "SubAgent Dispatch Config Evidence"
artifact_type: "worktrack-review-evidence"
generated_from: "worktrack-control-notes"
updated: "2026-04-27"
owner: "servo-kernel"
---
# SubAgent Dispatch Config Evidence

## Metadata

- worktrack_id: WT-20260427-docs-folder-reorg
- work_item: WT-20260427-RR-004
- reviewer: control-loop
- updated: 2026-04-27

## Scope

- Target path set: `docs/`, `product/`, `toolchain/scripts/`, `.servo/worktrack/`
- Updated control artifacts: dispatch policy precedence and control-plane wiring

## Diff Highlights

- `worktrack/contract.md` added `Execution Policy` and `runtime_dispatch_mode` precedence.
- `docs/harness/foundations/Harness运行协议.md` added explicit dispatch-mode priority and fallback semantics.
- `docs/harness/catalog/worktrack.md` documented `dispatch-skills` runtime dispatch mode reading order and supported modes.
- `product/harness/skills/dispatch-skills/SKILL.md` added runtime mode lookup rules:
  - control-state override > contract default > host auto-delegate.
- `product/harness/skills/README.md` and `docs/harness/README.md` migrated docs pointers to the new `docs/harness/catalog` path.

## Control Evidence

- `.servo/control-state.md` now records current explicit mode via `subagent_dispatch_mode: auto`.
- `.servo/worktrack/plan-task-queue.md` has transitioned to `WT-20260427-RR-004` with scoped scope and explicit completion criteria.

## Compliance Check

- RR-004 acceptance criteria alignment:
  - runtime dispatch mode precedence is documented explicitly.
  - per-worktrack precedence source is contract-level with runtime-state override.
  - conversation-driven override is no longer presented as mandatory in canonical dispatch contract.

## Decision

- `RR-004` status: **evidence-recorded**
- Recommendation: include in `WT-20260427-docs-folder-reorg` gate-evidence pack and transition to closeout handoff.
