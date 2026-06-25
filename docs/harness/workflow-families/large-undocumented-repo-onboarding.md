---
title: "Large Undocumented Repo Onboarding"
status: active
updated: 2026-05-31
owner: servo-kernel
last_verified: 2026-06-13
---
# Large Undocumented Repo Onboarding

> Purpose: define the Harness workflow policy for onboarding large codebases that lack reliable initialization docs, maintenance docs, or confirmed project purpose.

This page belongs to [Workflow Families](./README.md). It defines discovery and truth-promotion policy only. It does not replace Goal Charter, Repo Snapshot, or Worktrack Contract artifact definitions.

## Core Rule

Do not promote code inference directly into long-lived project truth.

For a large undocumented repo, Servo should first create a temporary inferred charter and an operational safety model. Long-lived purpose, owner boundaries, and maintenance rules require programmer confirmation or verified evidence before they can be written into the Goal Charter or documentation truth layer.

## When This Applies

Use this workflow when at least one condition is true:

- the repo is large enough that full manual review is unrealistic in one session;
- there is no `README`, onboarding guide, architecture note, maintenance doc, or reliable Goal Charter;
- existing docs are stale, contradictory, or only describe installation, not purpose;
- the repo contains many domains, generated code, legacy modules, or unclear ownership;
- the programmer asks Servo to initialize or work in a codebase whose purpose is not already confirmed.

## Evidence Classes

Separate onboarding output into these classes:

| Class | Meaning | May be promoted to long-lived truth? |
| --- | --- | --- |
| Observed facts | Directly observed files, commands, modules, routes, schemas, tests, CI, deployment config, package metadata | Yes, if evidence is cited and current |
| Inferred purpose | Model-derived interpretation of what the system likely does | No, not without confirmation |
| Unknowns | Questions that materially affect scope, risk, or acceptance | No |
| Operational purpose | Minimal safe-working objective, such as "make small verified changes without breaking known commands" | Yes, as a temporary operating constraint |
| Programmer-confirmed truth | Purpose, owner boundary, constraints, or acceptance criteria explicitly confirmed by the programmer | Yes |

The temporary inferred charter should keep these classes visibly separate.

## Discovery Pass

The first pass is read-only unless the programmer explicitly authorizes otherwise.

Minimum discovery checks:

- top-level directory and package layout;
- app entrypoints and framework signals;
- build, test, lint, and deploy commands;
- CI/CD and container configuration;
- API routes, schemas, migrations, generated clients, or service boundaries;
- domain vocabulary from module names and data models;
- docs presence, staleness, and contradiction signals;
- high-risk paths such as auth, billing, migrations, secrets, infra, or release scripts.

The output should state what was inspected and what was intentionally not inspected.

## Temporary Inferred Charter

For weakly documented large repos, the initial charter is temporary and must say so.

Use `product/harness/skills/harness-set-goal-skill/assets/repo/temporary-understanding.md` as the reusable template when `harness-set-goal-skill` initializes or adopts a weak-doc repo. The generated runtime artifact should be `.servo/repo/temporary-understanding.md`, and structured handoff may refer to it as `temporary_understanding`. When using `deploy_servo.js`, automatic generation requires `--adoption-mode existing-code-adoption --weak-doc-onboarding`; plain existing-code adoption should only emit discovery input.

It should include:

- `observed_facts`: cited facts from the repo;
- `inferred_purpose`: likely purpose with confidence;
- `operational_purpose`: safe initial operating goal;
- `known_risks`: high-impact areas and stale or missing docs;
- `unknowns`: questions that block confident long-term purpose;
- `confirmation_questions`: a short list for the programmer;
- `programmer_decisions_required`: decisions that cannot be inferred from repo evidence;
- `promotion_plan`: what must be confirmed before writing long-lived truth;
- `truth_boundary`: where temporary runtime evidence may live, and where it must not be promoted;
- `token_budget_note`: the token-cost tradeoff behind the selected discovery mode.

Do not hide uncertainty by rewriting it as confident project intent. The temporary understanding is runtime evidence, not Goal Charter truth.

## Complex Project Entry Gate

Weak-doc onboarding can trigger [Complex Project Entry Gate](../artifact/repo/complex-project-entry-gate.md). The gate is a Milestone-side blocking gate, not fixed heavy mode. If the requested Milestone is implementation-oriented and repo purpose, core directories, verification authority, service workflow boundary, or high-risk operation policy is still weak, Servo should block Milestone activation or Worktrack derivation instead of guessing.

unresolved gate blocking default: missing, blank, placeholder, pending, or incomplete `complex_project_entry_gate` fields must not be treated as `clear` or `not_applicable`; they keep create / upsert / activate / derive-worktrack blocked until programmer confirmation or verified evidence exists.

`complex_project_entry_gate` must preserve:

- `scanner_evidence_ref`: scanner output is evidence, not verdict;
- `complexity_signals`: thresholds, confidence, and rationale used for LLM judgment;
- `operator_safety_policy`: programmer-owned required safety fields;
- `dialog_review_questions`: highest-leverage questions and recommended answers;
- `milestone_blocking_decision`: whether create / upsert / activate / derive-worktrack is allowed;
- `reinforcement_milestone_recommendation`: structured reinforcement documentation / project-understanding Milestone recommendation when evidence is weak.
- Worktrack execution modes `normal`, `autoreview`, and `yolo`: user-owned policy choices that do not bypass the gate.

The distributable read-only scanner is installed with `harness-set-goal-skill` at `.agents/skills/harness-set-goal-skill/scripts/complexity_signal_scanner.py` or `.claude/skills/harness-set-goal-skill/scripts/complexity_signal_scanner.py`; this repository also keeps a local governance wrapper at `toolchain/scripts/test/complexity_signal_scanner.py`. Its JSON should expose scanner thresholds and observations for compose files, service hints, package managers, CI/deploy workflow hints, migration/data hints, debt proxy markers, and code size. The scanner must not access network, start services, execute docker/database/deploy actions, perform destructive writes, or emit file contents. It skips secret-like paths, but still performs bounded reads of non-secret-like text/code files for aggregate signals.

When weak docs are the blocking factor, the preferred route is a reinforcement documentation / project-understanding Milestone. Temporary understanding may support that recommendation, but it must not be promoted into long-lived truth before programmer confirmation or verified evidence.

The recommendation must be structured enough for downstream routing: `needed`, `recommendation_status`, `recommendation_type`, `suggested_title` or `suggested_purpose`, `reason` or `recommendation_reason`, `temporary_understanding_ref`, `evidence_refs`, `confirmation_required`, and `blocks_implementation_until_resolved`. `recommendation_status` should distinguish `not_needed`, `recommended`, `required`, and `pending_operator_review`. `needed = true` or `blocks_implementation_until_resolved = true` blocks implementation-oriented Worktrack derivation. `needed = false` does not block a low-risk `clear` / `not_applicable` gate by itself.

## Discovery Modes

Use a `lightweight` mode when the repo only needs low-token orientation for a narrow safe first slice. This mode should record coverage limits and keep assumptions visible.

Use a `full` mode when purpose, ownership, verification authority, or high-risk boundaries are unclear and materially affect the requested work. Full mode has higher token and time cost; if it cannot fit the current round, Servo should recommend a separate discovery milestone or worktrack instead of guessing.

## Programmer Confirmation

Ask only the highest-leverage questions first. The usual first questions are:

1. Who is the system for?
2. What business or product capability is most important right now?
3. Which directories are core, and which are legacy, generated, or low-trust?
4. Which commands or tests are authoritative?
5. Which areas should not be touched without explicit approval?

Each question should include the current recommended answer when the repo evidence supports one, plus the impact if the recommendation is wrong.

## Truth Promotion

Only promote facts after one of these events:

- programmer confirms the claim;
- a test, build, smoke, or contract check verifies the claim;
- source/config evidence is direct and unambiguous, such as package name or CI command.

Promotion targets:

- confirmed project purpose and operating boundaries -> Goal Charter;
- maintenance rules and onboarding notes -> project maintenance docs;
- Harness workflow policy -> `docs/harness/`;
- implementation contract -> `product/` or `toolchain/`.

Unconfirmed inferred purpose remains in runtime evidence or a temporary charter, not in long-lived docs.

## Stop Conditions

Stop before implementation when:

- the requested change depends on unknown business purpose;
- test authority is unknown and failure impact is high;
- the repo contains obvious high-risk areas but no owner boundary;
- the model cannot distinguish core modules from generated, vendored, or legacy code;
- inferred purpose conflicts with programmer input or existing docs;
- the first safe slice cannot be expressed without guessing.

In these cases, route to intake clarification, discovery worktrack, or programmer handback rather than implementation.

## Safe First Slice

If business purpose remains unclear, Servo may still proceed with an operationally safe slice when all are true:

- the change is narrow;
- affected files are well localized;
- verification commands are known or the lack of verification is explicitly accepted;
- no release, data migration, permission, security, or external contract boundary is touched;
- assumptions are recorded in the Worktrack Contract.

This is an operational purpose, not a substitute for understanding the product.

## Skill Impact

Current policy is docs-first.

Current skill policy implications:

- `harness-set-goal-skill`: should emit `.servo/repo/temporary-understanding.md` from `assets/repo/temporary-understanding.md` when documentation is weak, and may emit or reference `complex_project_entry_gate` when weak-doc or complex-project signals affect safe Milestone entry.
- `repo-status-skill`: should flag weak-doc initialization risk and stale or missing purpose evidence.
- `milestone-pre-intake-skill`: should ask `dialog_review_questions`, capture `operator_safety_policy`, and return `milestone_blocking_decision` before initialization.
- `milestone-init-skill`: should consume `complex_project_entry_gate` and block implementation Milestone activation when the gate says `needs_reinforcement_milestone` or `blocked`.
- `repo-whats-next-skill`: should prefer discovery, reinforcement documentation / project-understanding Milestone, or intake clarification before implementation when unknowns affect scope.
- `worktrack-init-skill`: should record unconfirmed assumptions as risks or blockers, not as accepted scope.

Mandatory enforcement requires explicit artifact fields rather than overloading free-form notes.
