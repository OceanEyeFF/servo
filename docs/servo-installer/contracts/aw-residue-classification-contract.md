---
title: ".aw Residue Classification Contract"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-05-27
---
# .aw Residue Classification Contract

> Purpose: define how current distribution paths classify `.aw`, `aw-*`, and `aw.marker` residues after the Servo rename and `.servo/` runtime migration. This contract decides what may remain, what is test-only or historical, and what must be remediated by later worktracks.

This contract does not remove compatibility behavior. It is the allowlist and classification source for later remediation and governance checks.

## Inputs

The current baseline inventory is `.servo/worktrack/research-deliverables/distribution-aw-residue-inventory.md`, produced by `WT-20260527-distribution-aw-residue-inventory`.

The inventory found the important residue families in:

- adapter payload descriptors under `product/harness/adapters/{agents,claude}/skills/*/payload.json`
- installer migration implementation under `toolchain/scripts/deploy/bin/servo-installer.js`
- deploy tests and packaged/TUI smoke tests
- servo-installer contracts, runbooks, references, and project-maintenance navigation docs
- one canonical source marker file: `product/harness/skills/init-milestone-skill/aw.marker`

## Classification Categories

Every `.aw`, `aw-*`, or `aw.marker` occurrence in distribution-relevant paths must belong to exactly one category.

| Category | Meaning | May Ship | Required Evidence |
| --- | --- | --- | --- |
| `compatibility-allowed` | Required for supported legacy behavior or operator-visible compatibility. | yes | Contract or runbook explains the compatibility behavior. |
| `runtime-migration-contract` | Required for explicit `.aw -> .servo` runtime migration semantics. | yes | Covered by `.aw Runtime Upgrade Contract` and migration tests. |
| `marker-identity-contract` | Required for installer-managed payload identity through runtime-generated `aw.marker`. | yes | Docs state marker is deploy identity metadata, not root `.aw/` runtime state. |
| `legacy-target-dir-contract` | Required for recognizing and converging old `aw-*` managed target dirs. | yes | Deploy mapping or migration contract states the convergence path. |
| `test-fixture-only` | Exists only to prove compatibility, migration, blocking, or old-output handling. | no package payload unless the test file itself ships by design | Test name or surrounding assertions show fixture purpose. |
| `historical-doc-only` | Historical note, repro record, or temporary compatibility documentation. | yes while documented compatibility window remains open | Document labels the history or removal horizon. |
| `navigation-only` | Link text or filename reference to an allowed compatibility document. | yes | Target document is allowed by this contract. |
| `remediation-required` | Current source, template, payload, or operator instruction that can mislead new installs back to `.aw`, or lacks an allowed compatibility basis. | no | Must be removed, renamed, moved, or explicitly reclassified. |

## Allowlist Matrix

| Area | Token Family | Category | Rule |
| --- | --- | --- | --- |
| `toolchain/scripts/deploy/bin/servo-installer.js` migration state detection and copy/rewrite code | `.aw` | `runtime-migration-contract` | Allowed only for explicit `migrate-runtime --from aw --to servo` behavior, TUI migration prompt, state reports, retention policy, and path-reference rewriting. |
| `toolchain/scripts/deploy/bin/servo-installer.js` managed marker code | `aw.marker` | `marker-identity-contract` | Allowed as managed payload identity for live install dirs. It must not be described as root runtime state. |
| `product/harness/adapters/{agents,claude}/skills/*/payload.json` `required_payload_files` | `aw.marker` | `marker-identity-contract` | Allowed only when runtime-generated at install target and documented as not stored as adapter source payload. |
| `product/harness/adapters/{agents,claude}/skills/*/payload.json` legacy target dirs | `aw-*` | `legacy-target-dir-contract` | Allowed only for `legacy_target_dirs` / `legacy_skill_ids` convergence from old agents target dirs to current `servo-*` dirs. |
| `docs/servo-installer/contracts/aw-runtime-upgrade-contract.md` | `.aw`, `aw-*`, `aw.marker` | `runtime-migration-contract` / `marker-identity-contract` / `legacy-target-dir-contract` | Allowed as normative compatibility contract. |
| `docs/servo-installer/contracts/deploy-mapping-spec.md` | `aw-*` | `legacy-target-dir-contract` | Allowed only to define recognition and convergence of legacy target dirs. |
| `docs/servo-installer/contracts/payload-provenance-trust-boundary.md` | `aw.marker` | `marker-identity-contract` | Allowed to define trust boundary and non-source-truth semantics. |
| `docs/servo-installer/runbooks/*` and `docs/servo-installer/reference/managed-files-ownership.md` | `.aw`, `aw-*`, `aw.marker` | `compatibility-allowed` | Allowed when giving operator guidance that preserves explicit migration and marker boundaries. |
| `docs/servo-installer/reference/legacy-version-handling.md` | `.aw`, `aw-*`, `aw.marker` | `historical-doc-only` | Allowed during the stated 0.5.x / 0.6.x compatibility window; must be reviewed before or during the planned 0.7.x cleanup. |
| `docs/servo-installer/reference/tui-aw-runtime-migration-repro.md` | `.aw`, `aw.marker` | `historical-doc-only` | Allowed as v0.5.7 repro and residual-risk evidence; must not describe current behavior as still broken after the fix. |
| `docs/book.md`, `docs/servo-installer/README.md`, and project-maintenance navigation docs | `.aw`, `aw-*` | `navigation-only` | Allowed only when linking to an allowed compatibility, runbook, reference, or contract document. |
| deploy tests and smoke tests | `.aw`, `aw-*`, `aw.marker` | `test-fixture-only` | Allowed when asserting migration, compatibility, marker identity, conflict blocking, legacy convergence, or historical output handling. |
| `product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js` marker exclusion | `aw.marker` | `marker-identity-contract` | Allowed when excluding runtime marker files from canonical skill packaging. |

## Remediation-Required Rules

An occurrence is `remediation-required` when any of the following is true:

- It is a source or template file that would install, copy, or instruct creation of `.aw/` as current runtime state for new Servo installs.
- It is a source or template file that tells operators or agents to write, synchronize, or verify current control-plane truth under `.aw/`.
- It is an `aw.marker` file stored as canonical source payload instead of runtime-generated target metadata, unless a local contract explicitly proves why it must exist in source.
- It is a legacy `aw-*` target-dir reference outside `legacy_target_dirs`, migration tests, historical docs, or explicit cleanup/convergence guidance.
- It appears in package payload or generated install content without a documented compatibility category from this contract.
- It is a stale historical statement that contradicts current verified behavior, for example saying the fixed TUI path still does not run migration.

The current inventory marked `product/harness/skills/init-milestone-skill/aw.marker` as a candidate `remediation-required` item because it was a zero-byte marker file in canonical skill source and appeared in the npm packlist. `WT-20260527-distribution-template-remediation` removed that source marker. Future occurrences of the same shape remain `remediation-required` unless a specific contract proves why the marker must exist in canonical source.

## Evidence Requirements

Future governance checks should report each finding with:

- `path`
- `line` or file-level marker
- `token_family`: `.aw` / `aw-*` / `aw.marker`
- `category`
- `category_source`: this contract section, related contract, or test fixture rationale
- `distribution_relevance`: packlist / deploy payload / operator docs / tests / historical reference
- `required_action`: keep / monitor / remediate / remove-after-window

Findings that cannot be mapped to a category must fail as `unclassified-aw-residue`.

## Non-Goals

- Do not rename `aw.marker` in this contract.
- Do not remove legacy `.aw -> .servo` migration behavior.
- Do not remove legacy `aw-*` target-dir convergence.
- Do not change package version, npm dist-tag, release tag, GitHub Release, publish workflow, or release channel.

## Related Documents

- [`.aw` Runtime Upgrade Contract](./aw-runtime-upgrade-contract.md)
- [Deploy Mapping Spec](./deploy-mapping-spec.md)
- [Payload Provenance Trust Boundary](./payload-provenance-trust-boundary.md)
- [Legacy `.aw` Runtime Upgrade Runbook](../runbooks/aw-runtime-upgrade-runbook.md)
- [Legacy Version Handling](../reference/legacy-version-handling.md)
