---
title: "servo-installer Dogfood Layering"
status: active
updated: 2026-07-06
owner: servo-kernel
last_verified: 2026-07-06
---
# servo-installer Dogfood Layering

This document defines the stable dogfood layer taxonomy used before concrete `npx servo-installer@next` validation work.

Dogfood layers are defined by three axes together: execution environment, side-effect boundary, and executor. The model separates Harness automation from programmer-run real-environment testing. It does not authorize release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply.

## Control Signal

- layer_range: L0-L6
- automated_harness_layers: L0-L4
- manual_real_environment_layers: L5-L6
- automation_boundary: Harness automation only covers reproducible, disposable, copy-on-write environments
- manual_evidence_boundary: Harness may record and check manual real-environment evidence, but must not claim it executed that test
- current_planning_authority: taxonomy, boundary, evidence, and test-plan design only

## Layer Model

| Layer | Executor | Automation Posture | Environment / Side-Effect Boundary |
| --- | --- | --- | --- |
| L0 | Harness | Automatic | Registry, GitHub, and release-channel facts; read-only metadata observation |
| L1 | Harness | Automatic | Installer read-only invocation such as help, version, or diagnose; no target writes |
| L2 | Harness | Automatic | Fresh disposable target; real installer execution in a newly created temp directory or temp repo |
| L3 | Harness | Automatic | Fixture clone or projection; dry-run, reconcile projection, or apply observation in a fixture copy |
| L4 | Harness | Automatic | Existing-work disposable copy; copy a sample repo with existing work, run against the copy, verify original unchanged |
| L5 | Programmer | Manual or human-triggered | Real environment readonly or smoke, such as Windows, WSL, or a daily repo; Harness only receives evidence |
| L6 | Programmer | Manual | Real environment apply, repair, or destructive-risk operation; explicit separate authorization required |

## WT2 Side-Effect Boundary Matrix

WT1 defines layer identity. WT2 only defines the side-effect envelope for those same L0-L6 layers.

| Layer | Automated Side-Effect Envelope | Write Boundary | Required Evidence Boundary |
| --- | --- | --- | --- |
| L0 | Metadata observation only | No target workspace and no package execution | Record selector, registry/GitHub/release facts, and proof that no mutation-capable operation was invoked |
| L1 | Read-only package invocation only | No target writes; generated `.servo`, `.agents`, `.claude`, deploy output, package output, and installer apply output are forbidden | Record command mode and logs proving it was help, version, diagnose, or equivalent read-only behavior |
| L2 | Disposable fresh target under automation | Writes may occur only inside a unique temp run root and allowlisted target root; source/current-repo manifests must remain unchanged or be marked not applicable when no source is read | Record target allowlist result, write manifest, original manifest unchanged result, and second dry-run convergence or non-convergence reason |
| L3 | Disposable fixture copy, clone, or projection under automation | Writes may occur only in the copied target under the run root; original fixture is read-only | Record copy-on-write source and target paths, write manifest, original fixture manifest unchanged result, and second dry-run convergence or non-convergence reason |
| L4 | Disposable copy of an existing-work repo or fixture under automation | Writes may occur only in the copied target under the run root; original repo/fixture is read-only | Record copy-on-write source and target paths, write manifest, original repo/fixture manifest unchanged result, and second dry-run convergence or non-convergence reason |
| L5 | Manual real-environment readonly or smoke lane | Not default Harness automation; any real-environment write must be operator-run and explicitly recorded | Harness may record/check evidence, but must not claim it executed the real-environment test |
| L6 | Manual real-environment apply, repair, cleanup, or destructive-risk lane | Not default Harness automation; every route requires separate explicit authorization with target, backup, rollback, evidence, and stop conditions | Harness may record/check evidence, but must not claim it executed the real-environment operation |

Forbidden authority applies to every layer: no release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply.

## Core Principles

- Harness automatic dogfood only covers environments that are reproducible, disposable, and safe to rerun.
- Automatic layers L0-L4 are limited to metadata/read-only invocation or disposable/copy workspaces under a unique temp run root and allowlisted target root.
- Automated execution requires copy-on-write when any existing source, fixture, repo, or manifest is involved.
- Every automated run creates a unique temp run root before any target path is selected.
- All write paths must stay under the unique temp run root and the allowlisted target root for that run.
- Targets must not point to the current repo, a daily real repo, or any non-allowlisted path.
- Existing-repo scenarios must copy or clone into temp first, then run only against the copy.
- Write-capable automation must record a write manifest for the copied or disposable target.
- Write-capable automation must verify the original repo, fixture, source, or manifest remains unchanged. If no original source is used, the evidence must explicitly record why original-manifest comparison is not applicable.
- Write-capable automation must verify second dry-run convergence or record the non-convergence reason.
- L5 and L6 are outside default automation. Real environments are tested by the programmer, then handed to Harness as manual real-environment evidence.
- Harness may record and check manual evidence, but must not claim it executed real-environment testing.

## Automated Harness Layers

### L0 Registry, GitHub, and Release-Channel Facts

Purpose: establish selector and package facts before package execution.

Allowed automated actions include reading npm dist-tags, package version, `gitHead`, tarball metadata, GitHub Release metadata, and workflow provenance.

Boundary: metadata only. No package execution, filesystem target, registry mutation, release action, or write side effect.

### L1 Installer Read-Only Invocation

Purpose: prove the selected package can be resolved and invoked in non-target-writing modes.

Allowed automated actions include help, version, diagnose, or equivalent read-only command behavior where no target write is possible.

Boundary: no target writes and no generated `.servo`, `.agents`, `.claude`, or deploy output.

### L2 Fresh Disposable Target

Purpose: run installer behavior in a new disposable target.

Allowed automated actions include creating a unique temp run root, creating a fresh temp directory or temp git repo under it, and running installer commands whose writes remain inside that root.

Boundary: writes are allowed only under the run root and allowlisted target root, and only to disposable targets. Evidence must include a write manifest, an original-manifest unchanged result or explicit not-applicable reason, and a second dry-run convergence result or recorded non-convergence reason. The current repo and real daily repos are forbidden targets.

### L3 Fixture Clone / Projection

Purpose: evaluate projection, dry-run, reconcile intent, or apply observation against a copied fixture.

Allowed automated actions include cloning or copying an allowlisted fixture into the temp run root and running dry-run, projection, or bounded apply observation against that copy.

Boundary: the original fixture is read-only. Automation must use copy-on-write, write only inside the copied target under the run root and allowlisted target root, record a write manifest, verify the original fixture manifest is unchanged, and verify second dry-run convergence or record the non-convergence reason.

### L4 Existing-Work Disposable Copy

Purpose: verify behavior around existing files, user edits, managed/unmanaged state, and preservation expectations.

Allowed automated actions include copying a representative existing-work repo or fixture into the temp run root, running installer behavior against the copy, checking write manifests, and verifying the original remains unchanged.

Boundary: writes are allowed only to the copied target under the run root and allowlisted target root. Automation must use copy-on-write, record a write manifest, verify the original repo/fixture manifest is unchanged, and verify second dry-run convergence or record the non-convergence reason.

## Manual Real-Environment Layers

### L5 Real Environment Readonly / Smoke

Purpose: capture real Windows, WSL, shell, Node/npm, daily-repo, or operator-environment behavior without default Harness automation.

Executor: programmer or human-triggered process. Harness receives an evidence packet afterward.

Boundary: L5 is a manual real-environment evidence lane, not default Harness automation. Harness may record and check evidence, but must not claim it executed the real-environment test. Any write-producing action must either be absent or be explicitly recorded with target type, path, cleanup state, and operator conclusion.

### L6 Real Environment Apply / Repair / Destructive-Risk

Purpose: cover real target mutation, repair, backup, apply, cleanup, or destructive-risk operations.

Executor: programmer, or a separately authorized route with explicit target, backup, rollback, evidence, and stop conditions.

Boundary: L6 is a manual real-environment evidence lane, never part of default automated dogfood. Harness may record and check evidence, but must not claim it executed the real-environment operation. L6 requires explicit authorization for each route.

## Evidence Families

### Automated Sandbox Evidence

Automated L0-L4 evidence should record:

- run root
- package selector and resolved facts
- target path allowlist result
- command list and logs
- write manifest
- original fixture or repo manifest before and after
- original manifest unchanged result
- second dry-run result, or non-convergence reason
- cleanup state for the temp run root

### Manual Real-Environment Evidence

Manual L5-L6 evidence should record:

- OS, shell, Node, and npm versions
- package selector and resolved package facts
- target type
- executed actions
- write locations, if any
- operator conclusion
- cleanup state
- whether the run was readonly, smoke, apply, repair, or destructive-risk
- whether Harness only recorded evidence rather than executing the test

## Downstream Use

- Side-effect boundary work must state that L0-L4 automated side effects are limited to disposable/copy workspaces, and that L5-L6 real-environment side effects are not default-automated.
- WT3 evidence contract work must encode automated sandbox evidence and manual real-environment evidence as separate evidence families. It should include fields for run root, target allowlist result, copy-on-write source/target, write manifest, original manifest unchanged result, second dry-run convergence result, and non-convergence reason without redesigning the L0-L6 taxonomy.
- WT4 `npx servo-installer@next` test-plan work should default to L0-L4 automation and select commands only inside the WT2 side-effect envelope. It should not add release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply authority.
- L5/L6 may be optional manual evidence lanes for the later test plan, but must remain programmer-run or separately authorized real-environment lanes.
- A manually completed Windows test belongs to L5 or L6 manual evidence, depending on whether it was readonly/smoke or apply/repair/destructive-risk. It must not be mixed into automated L2-L4 evidence.
