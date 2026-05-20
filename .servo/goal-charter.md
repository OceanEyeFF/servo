---
title: "Repo Goal / Charter"
artifact_type: "goal-charter"
generated_from: "repo-change-goal-skill"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Goal / Charter

## Metadata

- repo: servo
- owner: servo-kernel
- updated: 2026-04-26
- status: active

## Project Vision

Build a Codex-first AI coding harness platform and distribute it as a reusable repo-side contract layer across projects. The platform should make AI coding work controllable through explicit goals, bounded context, execution contracts, verification evidence, gate decisions, and verified writeback.

## Core Product Goals

- Establish Harness as the primary control-plane domain for repo evolution, with stable doctrine, scope, artifact, workflow family, and adjacent-system contracts.
- Maintain canonical executable Harness skills under `product/harness/skills/`, derived from `docs/harness/` rather than from deploy targets or backend-specific prompts.
- Maintain backend adapter source under `product/harness/adapters/`, with the current `agents` backend as the first concrete distribution target and near-term P0 consumer for the Node/npx distribution lane.
- Make Node/npm/npx the primary near-term distribution shape for Harness deploy tooling, with the user-facing entrypoint converging on `npx servo-installer` for install, update, verify, and diagnostic workflows.
- Design `servo-installer` as a dual-mode TUI + CLI tool: CLI remains the stable scriptable contract, while TUI provides the operator-facing interactive path for guided install, diagnosis, update planning, and backend selection.
- Treat Claude skills distribution as a slower compatibility lane: keep docs, smoke/runbook evidence, and future adapter room, but do not let Claude-specific packaging block the Node/npx mainline.
- Keep `Memory Side` and `Task Interface` as Harness adjacent systems that provide context, writeback, and task-contract boundaries without becoming Harness itself.
- Keep `docs/`, `product/`, and `toolchain/` boundaries stable so documentation truth, executable source, deployment targets, and runtime state do not collapse into one layer.
- Provide lightweight governance checks, adapter contract tests, scaffold validation, and gate tooling that allow narrow changes to be verified before writeback.

## Technical Direction

- `docs/harness/` is the upstream truth for Harness ontology, artifacts, workflow families, skills catalog, and adjacent-system contracts.
- `product/harness/skills/` is the canonical executable source root for Harness skills.
- `product/harness/adapters/` owns backend adapter payload source and backend-specific distribution metadata.
- `toolchain/scripts/deploy/` owns deploy, install, update, verify, and distribution helper behavior; deploy scripts should remain diagnosable, contract-driven, and evolve toward a Node/npm-packaged `servo-installer` command surface.
- The current local `servo-harness-deploy` package scaffold is an interim proof and package-facing wrapper for deploy semantics, not the final user-facing product name.
- `servo-installer` should preserve CLI-first automation semantics and add TUI flows only as an interactive layer over the same verified contracts.
- Claude-specific skill packaging remains a compatibility target behind the Node/npx `servo-installer` mainline.
- `toolchain/scripts/test/` owns lightweight governance, folder, path, semantic, gate, scaffold, and adapter contract checks.
- `.servo/` is a runtime control-plane artifact directory for the local Harness loop; it is not a long-term truth layer.
- Repo evolution should proceed through bounded worktracks with contract, plan, evidence, gate, closeout, and repo snapshot refresh.
- Backend differences may affect adapter metadata, install paths, and CLI wrapping, but must not redefine shared Harness truth.

## Engineering Node Map

This Goal defines the engineering node types that future worktracks may bind to. It is not a worktrack split.

### Node Type Registry

| type | merge_required | baseline_form | gate_criteria | if_interrupted_strategy | Description |
|------|---------------|---------------|---------------|-------------------------|-------------|
| `feature` | yes | commit-on-feature-branch | implementation + validation + policy | checkpoint-or-recover | New Harness, adapter, scaffold, or distribution capability |
| `refactor` | yes | commit-on-refactor-branch | validation + policy | checkpoint-or-rollback | Structural cleanup without intentional behavior change |
| `research` | no | annotated-tag-or-report | review-only | preserve-report-and-stop | Investigation before admitting a new truth or implementation direction |
| `bugfix` | yes | commit-on-bugfix-branch | implementation + validation + policy | checkpoint-or-rollback | Defect fix in skills, deploy, governance, gate, or docs behavior |
| `docs` | yes | commit-on-docs-branch | review + policy | checkpoint-or-recover | Truth-layer, runbook, governance, or artifact documentation update |
| `config` | yes | commit-on-config-branch | validation + policy | checkpoint-or-rollback | Adapter payload, deploy mapping, hook, package, or backend configuration change |
| `test` | yes | commit-on-test-branch | validation + policy | checkpoint-or-recover | Focused tests for governance, deploy, scaffold, adapter, or gate behavior |

### This Goal's Node Types

- type: docs
  - expected_count: recurring
  - merge_required: yes
  - baseline_form: commit-on-docs-branch
  - gate_criteria: review + policy
  - if_interrupted_strategy: checkpoint-or-recover
- type: feature
  - expected_count: recurring
  - merge_required: yes
  - baseline_form: commit-on-feature-branch
  - gate_criteria: implementation + validation + policy
  - if_interrupted_strategy: checkpoint-or-recover
- type: config
  - expected_count: recurring
  - merge_required: yes
  - baseline_form: commit-on-config-branch
  - gate_criteria: validation + policy
  - if_interrupted_strategy: checkpoint-or-rollback
- type: test
  - expected_count: recurring
  - merge_required: yes
  - baseline_form: commit-on-test-branch
  - gate_criteria: validation + policy
  - if_interrupted_strategy: checkpoint-or-recover
- type: refactor
  - expected_count: as-needed
  - merge_required: yes
  - baseline_form: commit-on-refactor-branch
  - gate_criteria: validation + policy
  - if_interrupted_strategy: checkpoint-or-rollback
- type: bugfix
  - expected_count: as-needed
  - merge_required: yes
  - baseline_form: commit-on-bugfix-branch
  - gate_criteria: implementation + validation + policy
  - if_interrupted_strategy: checkpoint-or-rollback
- type: research
  - expected_count: as-needed
  - merge_required: no
  - baseline_form: annotated-tag-or-report
  - gate_criteria: review-only
  - if_interrupted_strategy: preserve-report-and-stop

### Node Dependency Graph

- research -> docs (when an investigation is admitted into the truth layer)
- docs -> feature (when doctrine or artifact contracts define executable behavior)
- feature -> test (new behavior requires focused verification)
- config -> test (deploy, adapter, hook, or package changes require contract validation)
- bugfix -> test (regression fixes require local coverage)
- refactor -> test (structural cleanup requires no-regression evidence)
- feature -> config (distribution features may require adapter or package metadata)

### Default Baseline Policy

- if_worktrack_interrupted: preserve current evidence, checkpoint if useful, then route to `recover-worktrack-skill` for retry, rollback, split, or baseline refresh decision.
- if_no_merge: do not update the verified baseline; preserve gate evidence and alternative traceability, then return to `RepoScope.Observe`.

## Success Criteria

- Harness can start from a repo goal, create a bounded worktrack, collect evidence, judge a gate, close or recover, and return to an updated repo snapshot.
- `docs/harness/` remains the upstream truth for Harness doctrine, artifacts, workflow families, and adjacent-system contracts.
- `product/harness/skills/` and `product/harness/adapters/` remain canonical executable and adapter source, not deploy-result mirrors.
- Deploy tooling can install, verify, diagnose, and update through a Node/npm/npx distribution path centered on `npx servo-installer`, without requiring target repositories to understand this repository's internal source layout.
- `servo-installer` supports a dual working mode: machine-readable CLI commands for scripts/CI and an interactive TUI for human operators, with both modes sharing the same deploy contracts and verification semantics.
- Claude skills distribution can lag the Node/npx mainline as long as Claude-facing docs and smoke/runbook evidence stay coherent with the shared Harness contracts.
- Governance checks cover root layering, path and document integrity, semantic drift, adapter contracts, scaffold templates, and closeout/gate behavior at the scale of each change.
- Backend-specific prompts, payloads, and install paths do not redefine shared project truth.
- Verified changes are written back to the correct truth layer, while runtime state and deploy targets remain outside the canonical source of truth.

## System Invariants

- `product/` is the only business source root.
- `docs/` is the truth layer for project maintenance, Harness doctrine, and adjacent-system contracts.
- `toolchain/` only contains scripts, tests, evaluation, deployment, packaging, and governance tooling.
- `.agents/`, `.claude/`, and `.opencode/` are repo-local deploy targets, not source or truth layers.
- `.servo/`, `.autoworkflow/`, and `.spec-workflow/` are runtime or state layers, not long-term truth layers.
- `.nav/` is only a compatibility navigation layer.
- Harness is a layered closed-loop control system, not the coding executor itself.
- Goal changes are reference-signal changes and must be handled through explicit change control, not by ordinary loop decisions.
- Evidence and Gate remain separate: evidence proves state, gate decides whether the state may advance.
- Only verified facts may be written into long-term truth documents.

## Notes

- This charter was derived from local repository analysis and user confirmation on 2026-04-26.
- The current tracked worktree was clean before this `.aw` runtime control-plane update.
- Local governance observation before this update: `path_governance_check.py` and `governance_semantic_check.py` passed; `folder_logic_check.py` failed because `.servo/` is not registered in the root allowlist and an ignored Python `__pycache__` exists under a product skill script directory.
- 2026-04-26: Goal clarified by user confirmation: Node/npm/npx distribution via `npx servo-installer` is the primary near-term distribution shape, `servo-installer` should support TUI + CLI dual working modes, and Claude skills distribution is a slower compatibility lane.
