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

## Evidence Contract

WT3 defines the evidence packet shapes that later work may collect for the existing L0-L6 taxonomy and WT2 side-effect boundaries. These packet shapes do not rename layers, loosen side-effect rules, or authorize any release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply.

Evidence must identify whether it is automated sandbox evidence for L0-L4 or manual real-environment evidence for L5/L6. A manual packet may be recorded and checked by Harness, but it is not Harness-executed automated evidence.

### Automated Sandbox Evidence Packet (L0-L4)

Each L0-L4 automated packet must include these fields:

- `layer_id`: one of `L0`, `L1`, `L2`, `L3`, or `L4`.
- `package_selector`: requested package selector, such as `servo-installer@next`, exact version, tag, or local selector used by the bounded test.
- `resolved_package_facts`: resolved package name, version, dist-tag or selector resolution, tarball or package metadata where observed, `gitHead` when available, and source of those facts.
- `run_root`: unique temp run root for the automated run, or an explicit not-applicable reason for metadata-only L0 evidence that has no filesystem target.
- `target_path_allowlist_result`: allowlist decision for every target path, including target path, allowed/blocked result, and reason. L0/L1 packets that have no target path must record that no target path was selected.
- `copy_source_path`: original fixture, source, repo, or manifest path used for copy-on-write. L3/L4 packets must record the source path. L0/L1/L2 packets may record `not_applicable` when no copied source is used, with the layer-specific reason.
- `copied_target_path`: copied fixture, projection, repo, or disposable target path used for write-capable/copy-layer execution. L3/L4 packets must record the copied target path under the run root. L0/L1/L2 packets may record `not_applicable` when no copied source is used; L2 packets that use a fresh disposable target must still identify that target through `target_path_allowlist_result` and `write_manifest`.
- `command_list`: ordered commands or API invocations executed by Harness.
- `log_refs`: durable references to command output, diagnostic logs, or captured stdout/stderr summaries.
- `write_manifest`: files created, changed, or deleted inside the allowed disposable/copy target, or an explicit empty manifest for read-only layers.
- `original_manifest_before_after`: original fixture, source, repo, or manifest snapshot before and after the run, or an explicit not-applicable reason when no original source is involved.
- `original_unchanged_result`: pass/fail result proving the original fixture, source, repo, or manifest remained unchanged, or an explicit not-applicable result tied to the previous field.
- `second_dry_run_convergence_result`: convergence result for the second dry-run, including `changes=[]` or equivalent when it converged, or a clear non-convergence reason when it did not. Metadata-only or read-only layers must record why this check is not applicable.
- `packet_result`: aggregate result for this automated packet, one of `pass`, `fail`, `blocked`, `stale`, or `not_applicable`, with the reason and the field or check that determined the result.
- `cleanup_state`: temp run root and target cleanup result, retained artifact location, or reason cleanup was intentionally deferred.

Automated packets must stay inside the WT2 side-effect envelope for their layer. For L2-L4, writes are valid only under the unique temp run root and allowlisted target root. For L3/L4 copy-on-write lanes, `copy_source_path` must identify the original read-only source and `copied_target_path` must identify the mutable copy. For L0/L1, write manifests must be empty and the packet must show that no mutation-capable target operation was invoked.

### Manual Real-Environment Evidence Packet (L5/L6)

Each L5/L6 manual packet must include these fields:

- `layer_id`: `L5` for real-environment readonly/smoke evidence or `L6` for real-environment apply, repair, cleanup, or destructive-risk evidence.
- `mode`: one of `readonly`, `smoke`, `apply`, `repair`, or `destructive-risk`.
- `environment`: OS, shell, Node version, and npm version.
- `package_selector`: requested package selector, such as `servo-installer@next`, exact version, or tag.
- `resolved_package_facts`: resolved package name, version, dist-tag or selector resolution, tarball or package metadata where observed, `gitHead` when available, and source of those facts.
- `target_type`: target class, such as Windows workspace, WSL workspace, daily repo, disposable local repo, or other operator environment.
- `actions`: ordered operator-run actions and commands, with enough detail to distinguish readonly, smoke, apply, repair, or destructive-risk behavior.
- `write_locations`: paths written, if any; otherwise an explicit statement that no writes were observed or intended.
- `operator_conclusion`: programmer/operator conclusion, including pass/fail/blocked and the reason.
- `cleanup_state`: cleanup performed, retained artifacts, rollback state, or reason cleanup was not performed.
- `harness_execution_statement`: explicit statement that Harness recorded and checked this evidence but did not execute the real-environment test.
- `authorization_ref`: required for L6; the separate explicit authorization that named target, backup, rollback, evidence, and stop conditions. L5 may record not applicable when no L6 authority is involved.
- `packet_result`: aggregate result for this manual packet, one of `pass`, `fail`, `blocked`, `stale`, or `not_applicable`, with the reason and the field, authorization state, or operator conclusion that determined the result.

Manual packets remain programmer-run or separately authorized real-environment lanes. They must not be counted as Harness automated execution, and L6 is blocked unless the packet includes a separate explicit authorization reference for that specific route.

### Freshness and Pass/Fail Rules

- Missing required fields block the packet. A field may be `not_applicable` only when the packet records the layer-specific reason.
- A packet with a missing required field, missing required authorization, or invalid `not_applicable` claim must set `packet_result` to `blocked` and must not be counted as pass evidence.
- Evidence from an earlier package selector, resolved version, source commit, target snapshot, or environment state must be labeled `stale` and must not be counted as fresh pass evidence.
- A stale packet must set `packet_result` to `stale`; stale evidence cannot be upgraded into a fresh `pass` without rerunning or recollecting the affected evidence for the current selector, version, source, target snapshot, and environment state.
- Stale evidence may remain as historical context only when its stale reason is explicit.
- Manual L5/L6 evidence cannot satisfy an automated L0-L4 execution requirement.
- Automated L0-L4 evidence cannot claim real-environment coverage beyond the disposable or copy workspace that it actually executed.
- L6 evidence requires separate explicit authorization for each route. Without that authorization, the result is blocked, even if an operator already performed an action.
- Any packet that relies on release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply is invalid for this Milestone.

## Next npx Test Plan Handoff

This planning Milestone defines the downstream `npx servo-installer@next` test-plan handoff shape only. It does not run real `npx servo-installer@next`; real execution belongs to later `MS-20260705-002` or an equivalent future authorized Milestone.

The default automated plan lanes are L0-L4. L5 and L6 are optional manual evidence lanes only: manual evidence may be recorded and checked, but must not be counted as Harness automated execution. L6 requires separate explicit authorization for the specific route, target, backup, rollback, evidence, and stop conditions.

Forbidden authority remains unchanged for the handoff: no release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply.

### L0 Registry / Release-Channel Facts

Objective: establish read-only selector, registry, package, GitHub, and release-channel facts for the future `servo-installer@next` test without package execution or target selection.

Side-effect boundary: metadata observation only. The lane must not execute the package, create a target workspace, mutate registry or release state, or invoke any mutation-capable operation.

Expected evidence packet: an L0 automated sandbox packet using WT3 fields with `package_selector`, `resolved_package_facts`, `command_list` or API observation list, `log_refs`, `run_root` marked not applicable with reason, `target_path_allowlist_result` stating no target path was selected, empty `write_manifest`, original-manifest fields marked not applicable with reason, second dry-run convergence marked not applicable with reason, `packet_result`, and `cleanup_state`.

### L1 Read-Only Invocation

Objective: prove the selected package can be resolved and invoked only in non-target-writing modes for later validation.

Side-effect boundary: read-only package invocation only. The lane must not select a target path, generate `.servo`, `.agents`, `.claude`, deploy output, package output, installer apply output, or perform target writes.

Expected evidence packet: an L1 automated sandbox packet using WT3 fields with `package_selector`, `resolved_package_facts`, `run_root` when used or not-applicable reason when no filesystem run root exists, `target_path_allowlist_result` stating no target path was selected, `command_list` limited to read-only invocation modes selected by the future Milestone, `log_refs`, empty `write_manifest`, original-manifest fields marked not applicable with reason, second dry-run convergence marked not applicable with reason, `packet_result`, and `cleanup_state`.

### L2 Fresh Disposable Target

Objective: exercise installer behavior against a fresh disposable target created for the future run.

Side-effect boundary: writes may occur only inside a unique temp run root and the allowlisted fresh target root. No current repo, daily repo, non-allowlisted path, release authority, or onsite apply is allowed.

Expected evidence packet: an L2 automated sandbox packet using WT3 fields with `package_selector`, `resolved_package_facts`, `run_root`, `target_path_allowlist_result`, `copy_source_path` marked not applicable with reason, `copied_target_path` marked not applicable when no copy source is used, `command_list` chosen by the future Milestone, `log_refs`, `write_manifest`, `original_manifest_before_after` and `original_unchanged_result` marked not applicable when no original source exists, `second_dry_run_convergence_result`, `packet_result`, and `cleanup_state`.

### L3 Fixture Clone / Projection

Objective: evaluate dry-run, projection, reconcile intent, or bounded apply observation against a copied fixture or projection in the future run.

Side-effect boundary: copy-on-write only. The original fixture or projection source is read-only, and all writes must stay inside the copied target under the unique temp run root and allowlisted target root.

Expected evidence packet: an L3 automated sandbox packet using WT3 fields with `package_selector`, `resolved_package_facts`, `run_root`, `target_path_allowlist_result`, `copy_source_path`, `copied_target_path`, `command_list` chosen by the future Milestone, `log_refs`, `write_manifest`, `original_manifest_before_after`, `original_unchanged_result`, `second_dry_run_convergence_result`, `packet_result`, and `cleanup_state`.

### L4 Existing-Work Disposable Copy

Objective: evaluate behavior around existing files, user edits, managed and unmanaged state, and preservation expectations against a disposable copy in the future run.

Side-effect boundary: copy-on-write only. The original existing-work repo or fixture is read-only, and all writes must stay inside the copied target under the unique temp run root and allowlisted target root.

Expected evidence packet: an L4 automated sandbox packet using WT3 fields with `package_selector`, `resolved_package_facts`, `run_root`, `target_path_allowlist_result`, `copy_source_path`, `copied_target_path`, `command_list` chosen by the future Milestone, `log_refs`, `write_manifest`, `original_manifest_before_after`, `original_unchanged_result`, `second_dry_run_convergence_result`, `packet_result`, and `cleanup_state`.

### Go / No-Go Conditions

The future execution Milestone may proceed only while each selected lane remains inside its layer boundary and packet contract. Stop or mark the packet blocked when any of these conditions occur:

- Target path is outside the allowlist, points at the current repo, points at a daily real repo, or otherwise bypasses the approved disposable/copy target boundary.
- A run writes outside the unique temp run root or outside the allowlisted target root.
- The original fixture, repo, source, or manifest changes when copy-on-write or original-unchanged proof is required.
- A second dry-run fails to converge and no clear non-convergence reason is recorded.
- Any required WT3 packet field is missing, uses an invalid `not_applicable` claim, or omits the layer-specific reason.
- Evidence is stale for the current selector, resolved version, source commit, target snapshot, or environment state.
- The lane depends on forbidden authority: release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply.
- L5/L6 manual evidence is counted as Harness automated execution, or L6 lacks separate explicit authorization.

## Final Milestone Handoff

MS-20260705-001 is ready for Milestone Gate as a planning and contract closeout. WT1 established the L0-L6 dogfood taxonomy, WT2 bound each layer to its side-effect envelope, WT3 defined automated sandbox and manual real-environment evidence packets, and WT4 converted those contracts into the next `npx servo-installer@next` test-plan handoff without running the real command.

The closed scope remains limited to taxonomy, boundary, evidence, and handoff design. Harness automation covers only L0-L4 metadata, read-only invocation, disposable target, fixture copy/projection, and existing-work disposable-copy lanes. L5/L6 remain programmer-run or separately authorized manual evidence lanes that Harness may record and check without claiming automated execution.

Activation of MS-20260705-002, or any equivalent future registry dogfood Milestone, requires a separate explicit authorization before real `npx servo-installer@next` execution. This handoff grants no release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply authority.

## Downstream Use

- Side-effect boundary work must state that L0-L4 automated side effects are limited to disposable/copy workspaces, and that L5-L6 real-environment side effects are not default-automated.
- WT3 evidence contract work defines automated sandbox evidence and manual real-environment evidence as separate packet shapes without redesigning the L0-L6 taxonomy or WT2 side-effect boundaries.
- WT4 `npx servo-installer@next` test-plan work may consume these packet shapes as evidence requirements and the handoff shape above, but this document does not select concrete commands, targets, target repositories, or run sequence.
- WT4 `npx servo-installer@next` test-plan work should default to L0-L4 automation and select commands only inside the WT2 side-effect envelope. It should not add release, publish, package version mutation, tag, dist-tag, GitHub Release, push, PR, deploy, force, destructive cleanup, current-repo installer apply, or default onsite apply authority.
- L5/L6 may be optional manual evidence lanes for the later test plan, but must remain programmer-run or separately authorized real-environment lanes.
- A manually completed Windows test belongs to L5 or L6 manual evidence, depending on whether it was readonly/smoke or apply/repair/destructive-risk. It must not be mixed into automated L2-L4 evidence.
