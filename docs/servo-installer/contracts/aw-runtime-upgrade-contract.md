---
title: ".aw Runtime Upgrade Contract"
status: active
updated: 2026-05-22
owner: servo-kernel
last_verified: 2026-05-22
---
# .aw Runtime Upgrade Contract

> Purpose: define the safe upgrade boundary for target repositories that still have legacy `.aw/` Harness runtime state and need to converge on `.servo/`.

This contract owns the operator-visible and implementation-facing rules for `.aw/` runtime state migration. It does not define skill payload install semantics, release policy, or package versioning.

## Ownership Boundary

`.aw/` and `.servo/` are Harness runtime state directories in the target repository. They are not servo-installer skill payload and are not deploy targets.

The installer may offer an explicit upgrade command or flow that copies or migrates runtime state from `.aw/` to `.servo/`, but ordinary `install`, `update`, `verify`, `diagnose`, `check_paths_exist`, and `prune --all` must not silently mutate `.aw/` into `.servo/`.

Installer-managed skill payload remains under backend target roots:

- `agents`: `<targetRepoRoot>/.agents/skills/aw-{skill_id}/`
- `claude`: `<targetRepoRoot>/.claude/skills/{skill_id}/`

Those directories continue to use runtime-generated `aw.marker` files for managed payload identity. The marker name is a compatibility contract and must not be treated as evidence that `.aw/` runtime state is current.

## Explicit Entry

The upgrade path must be opt-in. A valid entrypoint must make the target state, planned actions, and destructive or overwrite risks visible before mutation.

Canonical command shape:

```text
servo-installer migrate-runtime --from aw --to servo [--json] [--yes] [--backend agents|claude|bundle] [--reinstall]
```

The exact command name may be revised during implementation only if the replacement keeps the same explicit `from aw` / `to servo` semantics and updates this contract in the same worktrack.

Minimum command semantics:

- default mode: dry-run or preview only
- mutating mode: requires an explicit confirmation flag such as `--yes`
- `--json` is read-only and mutually exclusive with `--yes`
- target root: uses the same target root resolution rules as the existing installer commands
- backend: may be `agents`, `claude`, or `bundle` only for the reinstall/update portion; runtime state migration itself is backend-neutral
- `--reinstall` controls whether the existing reinstall/update chain is planned after runtime state migration; without it, the command only handles runtime state

The entrypoint must report at least:

- detected `.aw/` state
- detected `.servo/` state
- whether migration is blocked
- planned copy or restore source
- backup or retention path for legacy `.aw/`
- whether reinstall/update will run after state migration
- recovery guidance when blocked

Exit semantics:

- `0`: dry-run/JSON completed with no blocking issue, or `--yes` completed all planned mutation and post-checks
- `1`: blocked, validation failed, partial copy failed, reinstall/update failed, or arguments are unsafe
- no partial-success exit code: partial completion is represented in structured output and stderr

JSON output must include stable top-level fields: `target_root`, `source_runtime_path`, `destination_runtime_path`, `state`, `verdict`, `planned_actions`, `backup_policy`, `reinstall_plan`, `blocking_issues`, `recovery_hints`, and `mutation_performed`. The implementation may also expose compatibility/detail fields such as `target_repo_root`, `action`, `mutation_allowed`, `sentinel_path`, `sentinel_present`, `issue_count`, and `issues`.

## State Matrix

| Target State | Default Verdict | Required Behavior |
| --- | --- | --- |
| no `.aw/`, no `.servo/` | no-op | Report that no legacy runtime state exists. Do not create `.servo/` as part of this upgrade. |
| `.aw/` only | ready | Dry-run reports planned `.aw/` to `.servo/` copy and retention behavior. Mutating mode may create `.servo/`. |
| `.servo/` only | no-op | Report already on `.servo/`. Do not touch `.aw/`. |
| both `.aw/` and `.servo/` | blocked | Fail closed by default. Provide recovery options; do not merge or overwrite automatically. |
| `.aw/` unreadable or malformed | blocked | Do not guess. Report the unreadable path and preserve contents. |
| `.servo/` unreadable or malformed | blocked | Do not overwrite. Report recovery options. |
| previous successful migration marker exists | idempotent | Re-running must be safe and must not duplicate backups or degrade `.servo/`. |

The implementation may use additional sentinel metadata to make idempotence observable, but the sentinel must not become the source of truth for Harness state.

For this contract, malformed includes: path exists but is not a directory, symlink where a real directory is required, unreadable directory, broken symlink, missing expected baseline files when the command is asked to preserve equivalent runtime state, or invalid artifact text that prevents a faithful copy. Malformed does not authorize repair by guessing.

## Copy And Retention Rules

The default mutating action is copy, not move.

Required behavior:

- preserve user-owned `.aw/` contents by default
- never delete `.aw/` unless the operator explicitly asks for cleanup
- if backup is used, place it under a clearly named path outside active `.servo/`
- preserve file content and relative paths as faithfully as the local filesystem permits
- preserve normal file modes where supported by the platform
- copy symlinks only when they remain inside the source runtime tree after resolution; otherwise block with a recovery hint
- fail before partial overwrite when `.servo/` already exists
- if a partial copy fails, report both source and destination state and leave recovery guidance
- never clean up partial destination data silently

Cleanup of `.aw/` is a separate operator decision. It must not be bundled into the default successful migration path.

If an idempotence sentinel is introduced, it should live under `.servo/` and record only migration metadata such as source path, timestamp, source hash summary, and installer version. It must not replace `control-state.md`, `goal-charter.md`, or other Harness runtime artifacts as truth.

## Reinstall / Update Coupling

After runtime state migration, the installer may run the existing destructive reinstall/update chain so installed skills converge on current naming and payload descriptors.

Implemented command shape:

```text
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents|claude|bundle
```

`--reinstall` is not an independent migration mode. It adds an update preflight to `migrate-runtime`; when the update plan has blocking issues, the command must stop before copying `.aw/` to `.servo/`. When the runtime migration is safe and the update plan is clear, the command runs the existing `update --yes` chain for the selected backend. Bundle mode uses the same aggregate update composition as `servo-installer update --backend bundle --yes`.

The reinstall/update portion must reuse existing mechanisms:

- `aw.marker` identifies installer-managed payload directories
- `legacy_target_dirs` and `legacy_skill_ids` drive managed cleanup of old skill target names
- `payload_fingerprint` proves live target payload alignment with current source
- `update --yes` keeps the existing `prune -> check_paths_exist -> install -> verify` shape

The runtime migration step must not reinterpret `aw.marker` as a `.aw/` runtime marker. `aw.marker` belongs to skill payload target directories only.

## Conflict And Recovery Rules

The upgrade path is fail-closed. It must block before mutation when it cannot prove the target state is safe.

Blocking cases include:

- existing `.servo/` when `.aw/` also exists
- unreadable source or destination runtime directories
- destination path is a file or symlink where a directory is required
- target root safety validation fails
- requested cleanup would delete `.aw/` without explicit cleanup approval
- reinstall/update preflight reports blocking target path conflicts

Recovery guidance must distinguish:

- keep `.servo/` and abandon `.aw/`
- archive `.aw/` manually, then rerun
- remove or relocate broken destination state, then rerun
- run backend-specific `verify` / `diagnose` after reinstall/update issues

Root `.aw/` remains an allowed compatibility state until an explicit successful migration and any separate cleanup approval. Governance checks must not treat merely existing `.aw/` as a deletion mandate. Once cleanup is explicitly requested, cleanup must still preserve backup or operator-confirmed deletion evidence.

## Dry-Run Requirements

Dry-run output must be specific enough for an operator or CI log to audit.

Minimum fields:

- target root
- source runtime path
- destination runtime path
- state classification from the state matrix
- planned filesystem actions
- backup or retention policy
- reinstall/update plan, if enabled
- blocking issues
- recovery hints

Dry-run must not create, modify, move, delete, or chmod target repository files.

`--json` is always read-only and mutually exclusive with `--yes`. Human output may include a concise `reinstall status` and `reinstall blocking issues` summary; JSON exposes the same information under `reinstall_plan.status` and `reinstall_plan.blocking_issue_count`.

TUI may surface legacy `.aw/` as a warning or upgrade prompt, but it must route mutating behavior back to the explicit CLI-equivalent command shape. TUI `.servo` health checks must not auto-migrate `.aw/`, and missing `.servo/` plus present `.aw/` should be reported as "legacy runtime state present" rather than as a generic uninitialized state.

## Test Surface

The implementation worktracks must include `/tmp` target repository smoke tests for at least:

- `.aw/` only
- `.servo/` exists
- both `.aw/` and `.servo/` present
- `.aw/` path is malformed
- `.servo/` path is malformed
- dry-run reports planned actions without mutation
- successful migration is idempotent
- failed copy exposes recovery guidance
- reinstall/update refreshes managed skill markers and payload fingerprints through the existing installer path

Current verified test coverage also includes update preflight blocking before runtime copy and bundle reinstall installing both backend payloads.

Tests must not create runtime state under this source repository.

## Non-Goals

- no package version, npm dist-tag, release tag, publish state, or release channel mutation
- no default deletion of `.aw/`
- no silent overwrite of `.servo/`
- no use of `.agents/` or `.claude/` deploy targets as source truth
- no migration of `.autoworkflow/` or `.spec-workflow/`
- no change to the `aw.marker` filename in this contract

## Related Documents

- [Deploy Mapping Spec](./deploy-mapping-spec.md)
- [Distribution Entrypoint Contract](./distribution-entrypoint-contract.md)
- [Payload Provenance Trust Boundary](./payload-provenance-trust-boundary.md)
- [Managed Files Ownership](../reference/managed-files-ownership.md)
- [Skill Deployment Maintenance](../runbooks/skill-deployment-maintenance.md)
