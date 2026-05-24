---
title: "Legacy Version Handling"
status: active
updated: 2026-05-23
owner: servo-kernel
last_verified: 2026-05-23
---
# Legacy Version Handling

> Temporary compatibility note for old target repositories that still carry `.aw/` runtime state or old installer-managed skill target dirs. This document is expected to be removed in the `0.7.x` series after the legacy migration window closes.

## Scope

This page documents the current compatibility behavior for legacy targets produced before the current `servo-*` agents target-dir convention stabilized.

It covers:

- root `.aw/` Harness runtime state
- old `.agents/skills/aw-*` managed skill target dirs
- existing `.claude/skills/*` targets when agents and claude are both installed
- packaged installer upgrade smoke expectations for the `0.5.x` and `0.6.x` compatibility window

It does not define release policy, npm dist-tags, package version approval, or future removal mechanics. Release governance remains in `docs/project-maintenance/governance/servo-installer/`.

## Removal Window

This is a transitional support document.

- Keep this page during the `0.5.x` and `0.6.x` compatibility window.
- Expect to remove this page in `0.7.x`.
- Before removing it, verify that operator-facing runbooks no longer need dedicated old-version handling for `.aw/` runtime state or old `aw-*` agents target dirs.
- Removing this page must not silently remove runtime migration code; code removal, if any, needs its own worktrack and verification.

## Legacy States

| Legacy state | Current handling |
|---|---|
| `.aw/` exists and `.servo/` is absent | `servo-installer migrate-runtime --from aw --to servo --json` reports a ready copy plan. `--yes` creates `.servo/` and retains `.aw/`. |
| `.aw/` and `.servo/` both exist | Migration is blocked by default unless a prior migration sentinel proves the target is already migrated. |
| `.agents/skills/aw-*` managed dirs exist | `servo-installer update --backend agents --yes` replaces managed old target dirs with current `servo-*` target dirs. |
| `.agents/skills/servo-*` exists | Current agents target shape; normal verify/update applies. |
| `.claude/skills/<skill-id>` exists | Current claude target shape; normal verify/update applies. |
| `.agents` and `.claude` both exist | Use `--backend bundle` for aggregate verify/update/reinstall when both should converge together. |

## Operator Path

For a legacy target with `.aw/` runtime state:

```bash
servo-installer migrate-runtime --from aw --to servo --json
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents
servo-installer verify --backend agents
servo-installer diagnose --backend agents
```

For a target that has both agents and claude deploy targets:

```bash
servo-installer migrate-runtime --from aw --to servo --json
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
servo-installer verify --backend bundle
servo-installer diagnose --backend bundle
```

For a target that has already migrated runtime state but still has old agents target dirs:

```bash
servo-installer update --backend agents --yes
servo-installer verify --backend agents
```

## Safety Rules

- Ordinary `install`, `update`, `verify`, `diagnose`, `check_paths_exist`, and `prune --all` do not silently migrate `.aw/` to `.servo/`.
- `.aw/` is retained by default after a successful migration.
- Cleanup of `.aw/` is an explicit operator decision and is not part of the default upgrade path.
- `aw.marker` inside managed skill target dirs is deploy identity metadata; it is not the same thing as root `.aw/` runtime state.
- Agents and claude deploy targets have different canonical target naming:
  - agents: `.agents/skills/servo-<skill-id>`
  - claude: `.claude/skills/<skill-id>`
- Bundle mode must refresh each backend inside its own target root; it must not rename claude targets to agents naming, or agents targets to claude naming.

## Verified Compatibility Evidence

The following evidence was collected on 2026-05-23 using a packaged `servo-installer-0.5.3.tgz` generated from the source tree.

| Scenario | Result |
|---|---|
| `/tmp/repo-rating-function` with `.aw/` and old `.agents/skills/aw-*` dirs | Packaged `migrate-runtime --yes --reinstall --backend agents` copied `.aw` to `.servo`, replaced old managed agents dirs with 21 `servo-*` dirs, and passed verify/diagnose. |
| Repeat migration on `/tmp/repo-rating-function` | Packaged JSON returned `state=already-migrated`, `verdict=already-migrated`, and `sentinel_present=true`. |
| `/tmp/servo-dual-backend-smoke.OZuLrQ` with `.aw/`, `.agents/skills/servo-*`, and `.claude/skills/<skill-id>` | Packaged `migrate-runtime --yes --reinstall --backend bundle` refreshed both backends independently and passed bundle verify/diagnose. |
| Runtime equivalence checks | `.aw/` and `.servo/` matched in both smoke targets when excluding `.servo-installer-aw-migration.json`. |

## Related Documents

- [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md)
- [Legacy `.aw` Runtime Upgrade Runbook](../runbooks/aw-runtime-upgrade-runbook.md)
- [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)
- [Managed Files Ownership](./managed-files-ownership.md)
