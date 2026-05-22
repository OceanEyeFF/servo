---
title: "Legacy .aw Runtime Upgrade Runbook"
status: active
updated: 2026-05-22
owner: servo-kernel
last_verified: 2026-05-22
---
# Legacy .aw Runtime Upgrade Runbook

> Purpose: give operators a concrete path for explicitly migrating legacy `.aw/` Harness runtime state into `.servo/` without deleting `.aw/` or silently overwriting existing `.servo/`.

Normative behavior is defined by [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md). This runbook is the procedural operator path.

## When To Use

Use this runbook when a target repository has `.aw/` runtime state from an older Harness install and you want to move that runtime state to `.servo/`.

Do not use ordinary `install`, `update`, `verify`, `diagnose`, `check_paths_exist`, or `prune --all` to migrate runtime state. Those commands manage installed skill payloads, not root runtime directories.

## Read-Only Preview

Start with a dry-run preview:

```bash
servo-installer migrate-runtime --from aw --to servo
```

For CI or structured logs:

```bash
servo-installer migrate-runtime --from aw --to servo --json
```

Both forms are read-only. `--json` is mutually exclusive with `--yes`.

## Apply Runtime Migration

When the preview reports `.aw/` only and no blocking issues, apply the copy:

```bash
servo-installer migrate-runtime --from aw --to servo --yes
```

The command copies `.aw/` to `.servo/` and writes a migration sentinel under `.servo/`. It preserves `.aw/` in place. Cleanup of `.aw/` is a separate operator decision and is not part of this runbook.

Re-running after a successful migration is safe: the sentinel lets the command report `already-migrated` instead of overwriting `.servo/`.

## Apply Migration And Refresh Installed Skills

If you also want installed skill payloads to converge on the current source metadata, run:

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents
```

For Claude:

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend claude
```

For both backends:

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
```

`--reinstall` first computes the existing update plan. If update preflight has blocking conflicts, the command stops before copying `.aw/` to `.servo/`. If runtime migration is safe and update preflight is clear, it reuses the existing `update --yes` chain: `prune --all -> check_paths_exist -> install -> verify`.

For `agents`, the reinstall/update chain also replaces installer-managed legacy `aw-*` skill target dirs with current `servo-*` target dirs. `diagnose` and `update` surface this as upgrade guidance before the mutating run.

`aw.marker` remains installer-managed payload identity. It is not evidence of `.aw/` runtime state.

## State Matrix

| Target state | Result |
| --- | --- |
| no `.aw/`, no `.servo/` | no-op; nothing is created |
| `.aw/` only | ready; `--yes` can copy runtime state |
| `.servo/` only | no-op; already on `.servo/` |
| both `.aw/` and `.servo/` without migration sentinel | blocked; no merge or overwrite |
| `.aw/` is a file, symlink, unreadable, or malformed | blocked |
| `.servo/` is a file, symlink, unreadable, or malformed | blocked |
| previous migration sentinel exists | idempotent no-op |

## Recovery

If the command blocks:

- preserve `.aw/`
- inspect the reported path and issue code
- relocate or repair existing `.servo/` only after deciding which runtime state should win
- rerun dry-run before applying mutation
- after reinstall/update issues, run backend-specific `diagnose` and `verify`

Do not delete `.aw/` as a default cleanup step.

## Smoke Evidence

The installer test suite verifies the upgrade path using `/tmp` target repositories, not this source repository. Current covered cases:

- no `.aw/` and no `.servo/`
- `.aw/` only dry-run
- `.aw/` only `--yes`
- successful rerun idempotence
- both `.aw/` and `.servo/` present
- malformed `.aw` path
- `.servo/` only
- agents `--reinstall` marker refresh and payload fingerprint convergence
- update conflict blocks before runtime copy
- bundle `--reinstall` installs both backend payloads

The latest closeout evidence for this milestone recorded the full installer suite passing with 145 tests.
