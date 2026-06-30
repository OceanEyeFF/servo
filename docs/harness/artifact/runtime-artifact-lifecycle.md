---
title: "Runtime Artifact Lifecycle"
status: active
updated: 2026-06-30
owner: servo-kernel
last_verified: 2026-06-30
---
# Runtime Artifact Lifecycle

This document defines the lifecycle policy for `.servo/` runtime artifacts. It is a Harness artifact contract, not a cleanup runbook. It defines what may be archived, preserved, promoted, reported, or later deleted with separate approval.

## Position

`.servo/` is the runtime control and evidence layer for the current repository. It stores control state, milestone and worktrack runtime records, temporary discoveries, execution evidence, dispatch records, and closeout traces.

Long-term project truth does not live only in `.servo/`:

- Harness doctrine, workflow policy, and artifact contracts are promoted to `docs/harness/`.
- Project maintenance, deploy, governance, and usage-help truth are promoted to `docs/project-maintenance/`.
- Executable implementation contracts live in `product/` or `toolchain/`.

## Artifact Classes

| class | examples | lifecycle |
| --- | --- | --- |
| control-state | `.servo/control-state.md`, `.servo/control-state-repo.md`, `.servo/control-state-wt.md`, `.servo/operator-config.md` | active runtime state; compact forward, do not archive while referenced by current route |
| milestone runtime record | `.servo/milestone/MS-*.md`, gate verdicts, closeout records, axis reports | preserve while referenced by backlog, history, manual exception, or gate evidence |
| worktrack runtime record | `.servo/worktrack/contract.md`, `plan-task-queue.md`, `gate-evidence.md` | rolling current worktrack files; snapshot or closeout bundle before historical references rely on them |
| repo runtime record | `.servo/repo/milestone-backlog.md`, `worktrack-backlog.md`, `snapshot-status.md`, intake reviews | preserve active pipeline records; compact stale entries only through report-first maintenance |
| temporary discovery | temporary understanding, exploratory notes, command summaries, scratch intake material | archive or expire after promotion, supersession, or explicit stale finding |
| execution output | SubAgent raw outputs, command logs, diagnostic outputs | preserve if used as evidence; archive if useful but not canonical; expire only after report and approval |

## Lifecycle States

| state | meaning | allowed transition |
| --- | --- | --- |
| active | consumed by the current control route or current Worktrack | preserve in place |
| preserved | needed for audit, gate, closeout, manual exception, or history traceability | keep stable path or archive with redirect/reference update |
| promoted | verified fact has been moved to `docs/`, `product/`, or `toolchain/` truth | runtime source may be archived, not silently deleted |
| superseded | replaced by newer runtime artifact and no longer authoritative | report as archive candidate |
| stale | conflicts with current control state, git checkpoint, or canonical docs | report as maintenance candidate before action |
| expired | temporary record past retention and not referenced by evidence | deletion still requires explicit cleanup approval |

## Archive Paths

Archive paths should preserve enough identity to keep references understandable:

```text
.servo/archive/
  milestone/<milestone_id>/
  worktrack/<worktrack_id>/
  discovery/<YYYYMMDD>/<slug>/
  subagent/<worktrack_id>/<carrier_id>/
  command-output/<YYYYMMDD>/<slug>/
```

Moving an artifact to archive is a state transition. It must record the source path, destination path, reason, timestamp, and references updated or intentionally left unchanged.

## Preservation Rules

The following artifacts must not be deleted by default:

- Milestone Gate verdicts, axis reports, closeout records, manual exception records, and final acceptance records.
- Worktrack contracts, gate evidence, closeout evidence bundles, dispatch records, and SubAgent records used by Gate or closeout.
- Repo backlog/history entries that are still referenced by current milestone status, milestone history, or control state.
- Evidence cited by docs truth, governance checks, release notes, or manual exception follow-up records.

Rolling files such as `.servo/worktrack/gate-evidence.md` must not be used as historical proof unless a closeout record, bundle, or archive snapshot preserves the version used by that worktrack.

## Maintenance Cycle

The maintenance cycle runs after verified closeout or during an explicit repo maintenance pass:

1. Observe runtime artifact inventory and references.
2. Classify candidates as preserve, promote, archive, stale, superseded, expired, or unknown.
3. Produce a maintenance sweep report before making changes.
4. Promote verified long-term facts to the correct docs or implementation owner.
5. Archive only when traceability is retained.
6. Request separate approval before deletion or destructive cleanup.

Report-first maintenance may identify deletion candidates, but it does not execute deletion. Cleanup execution is a separate approval boundary.

## Checks

Maintenance checks should detect:

- rolling evidence reuse without snapshot or closeout bundle
- stale references to missing milestone/worktrack artifacts
- orphan artifacts not reachable from backlog/history/control-state
- temporary discovery records that were never promoted or retired
- SubAgent or command-output evidence referenced only by prose summaries
- archived artifacts whose source references were not updated or explicitly preserved

These checks provide evidence for cleanup decisions. They do not by themselves authorize cleanup.

## Boundaries

This policy does not authorize release, publish, tag, remote push, deploy, protected branch mutation, secret handling, database migration, external side effects, or destructive cleanup.

When a runtime artifact contains a verified long-term fact, promote the fact to the appropriate truth owner before treating the runtime artifact as stale or expired.
