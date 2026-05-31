---
title: "Large Undocumented Repo Onboarding"
status: active
updated: 2026-05-31
owner: servo-kernel
last_verified: 2026-05-31
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

It should include:

- `observed_facts`: cited facts from the repo;
- `inferred_purpose`: likely purpose with confidence;
- `operational_purpose`: safe initial operating goal;
- `known_risks`: high-impact areas and stale or missing docs;
- `unknowns`: questions that block confident long-term purpose;
- `confirmation_questions`: a short list for the programmer;
- `promotion_plan`: what must be confirmed before writing long-lived truth.

Do not hide uncertainty by rewriting it as confident project intent.

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

- `set-harness-goal-skill`: should emit a temporary inferred charter when documentation is weak, instead of pretending to know long-lived purpose.
- `repo-status-skill`: should flag weak-doc initialization risk and stale or missing purpose evidence.
- `repo-whats-next-skill`: should prefer discovery or intake clarification before implementation when unknowns affect scope.
- `init-worktrack-skill`: should record unconfirmed assumptions as risks or blockers, not as accepted scope.

Mandatory enforcement requires explicit artifact fields rather than overloading free-form notes.
