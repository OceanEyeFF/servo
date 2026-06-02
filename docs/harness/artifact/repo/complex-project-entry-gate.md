---
title: "Complex Project Entry Gate"
status: active
updated: 2026-06-02
owner: servo-kernel
last_verified: 2026-06-02
---

# Complex Project Entry Gate

> Purpose: define the RepoScope runtime artifact and handoff contract that blocks complex or weakly understood implementation milestones before they create or activate unsafe worktracks.

`complex_project_entry_gate` is a Milestone-side blocking gate for complex project entry. It is evaluated before an implementation-oriented goal-driven milestone is created, updated, activated, or allowed to derive its first Worktrack. It does not replace Worktrack Gate, Worktrack risk judgment, or the execution mode chosen inside WorktrackScope.

This contract is not fixed heavy mode. Small, low-risk, well-understood requests may record that the gate is not applicable after a light signal check. Complex, weak-doc, multi-system, deploy, migration, security, data, destructive, or authority-sensitive requests must keep the gate explicit.

## Scope

`complex_project_entry_gate` belongs to RepoScope and is consumed by Milestone initialization and RepoScope decision logic.

Runtime storage may be either:

- `.servo/repo/complex-project-entry-gate.md`, when the gate needs persistent runtime evidence;
- a structured handoff object named `complex_project_entry_gate`, when the current intake round can carry the evidence directly.

The gate blocks Milestone entry when the project or requested milestone is not understood enough to safely derive Worktracks. WorktrackScope remains responsible for local implementation gating, review strategy, and risk execution modes such as `normal`, `autoreview`, and `yolo`.

## Required Fields

| Field | Meaning |
| --- | --- |
| `gate_id` | Stable identifier for this gate evaluation. |
| `target_repo` | Repo or worktree being evaluated. |
| `target_milestone_id` | Milestone being created, updated, activated, or used to derive Worktracks. |
| `trigger_source` | One of `repo-init`, `pre-milestone-intake`, `init-milestone`, `repo-whats-next`, `manual`. |
| `complexity_signals` | Observed signals that made the gate applicable, with thresholds and confidence. |
| `scanner_evidence_ref` | Reference to scanner output; scanner output is evidence, not verdict. |
| `project_understanding` | Current understanding of purpose, core directories, service boundaries, and verification authority. |
| `service_workflow_boundary` | Known service topology, external systems, deploy surface, migration surface, and workflow boundaries. |
| `operator_safety_policy` | Programmer-owned safety settings required before high-risk work. |
| `dialog_review_questions` | Highest-leverage questions asked or still required before Milestone entry. |
| `allowed_before_confirmation` | Low-risk operations allowed while the gate is unresolved. |
| `forbidden_before_confirmation` | Operations forbidden until programmer confirmation or reinforcement evidence exists. |
| `entry_verdict` | `clear`, `needs_reinforcement_milestone`, `blocked`, or `not_applicable`. |
| `milestone_blocking_decision` | Whether create / upsert / activate / derive-worktrack is allowed. |
| `reinforcement_milestone_recommendation` | Recommended reinforcement documentation or project-understanding Milestone when evidence is weak. |
| `evidence_refs` | Runtime artifacts, docs, commands, scanner outputs, or user confirmations supporting the verdict. |
| `updated` | Last update timestamp. |

## Operator Safety Policy

`operator_safety_policy` is owned by the programmer. Harness records and enforces the confirmed policy; it does not invent one from repo inference.

Minimum required fields:

- `docker_compose_permission`
- `database_migration_permission`
- `deploy_network_permission`
- `destructive_cleanup_permission`
- `secrets_policy`
- `protected_paths`
- `protected_branches`
- `allowed_high_risk_command_modes`

`allowed_high_risk_command_modes` may include `normal`, `autoreview`, or `yolo`, but these modes are user-owned execution policy choices. They do not make scanner output authoritative and do not bypass Milestone-side blocking when required understanding is missing.

## Dialog Review Questions

`dialog_review_questions` should stay short and high leverage. Common questions include:

1. What is the system purpose and the current Milestone purpose?
2. Which directories are core, legacy, generated, vendored, or low-trust?
3. Which tests, checks, or smoke commands are authoritative?
4. What service topology and workflow boundaries matter for this Milestone?
5. Are data migration, deploy, secrets, destructive cleanup, or external contract surfaces in scope?
6. Which high-risk command modes are allowed: `normal`, `autoreview`, `yolo`, or none?
7. What must be confirmed before the first implementation Worktrack may start?

Each question should carry `why_it_matters`, `recommended_answer`, `tradeoff`, and `blocks_ready`.

## Scanner Evidence

Scanner output is evidence, not verdict. A scanner may report thresholds, counts, patterns, confidence, or risk signals, but the gate verdict remains a structured Harness decision over observed facts, programmer confirmation, and runtime context.

`complexity_signals` should preserve scanner thresholds and rationale so an LLM or review carrier can judge:

- why the gate is applicable;
- which signals are weak or contradictory;
- which signals are only heuristics;
- what evidence would clear the block.

## Verdict Semantics

`entry_verdict` values:

- `clear`: Required understanding and safety policy are sufficient for Milestone entry.
- `needs_reinforcement_milestone`: The request appears worthwhile, but weak docs or missing understanding should first become a reinforcement documentation / project-understanding Milestone.
- `blocked`: A required programmer decision, safety policy, or authority boundary is missing.
- `not_applicable`: Light signal evaluation found no complex-project trigger for this request.

`milestone_blocking_decision` values:

- `allow_create`
- `allow_upsert`
- `allow_activate`
- `allow_derive_worktrack`
- `block_create`
- `block_upsert`
- `block_activate`
- `block_derive_worktrack`

For implementation-oriented goal-driven milestones, `needs_reinforcement_milestone` and `blocked` must block activation and Worktrack derivation unless the programmer explicitly accepts a narrower safe slice whose safety boundary is documented.

## Weak-Doc Routing

When weak docs prevent safe implementation, Harness should recommend a reinforcement documentation or project-understanding Milestone. The recommendation is represented by `reinforcement_milestone_recommendation`.

Weak-doc findings may use `.servo/repo/temporary-understanding.md` as runtime evidence, but unconfirmed inference must not be promoted into Goal Charter, docs truth, Milestone truth, or Worktrack acceptance criteria.

## Consumers

- `set-harness-goal-skill` may create or reference the gate during existing-code adoption when weak-doc or complex-project signals are found.
- `pre-milestone-intake-skill` produces or updates `complex_project_entry_gate`, `operator_safety_policy`, and `dialog_review_questions` for high-risk Milestone requests.
- `init-milestone-skill` consumes the gate and blocks create / upsert / activate when `milestone_blocking_decision` says to block.
- `repo-whats-next-skill` checks the gate before deriving a Worktrack from an active Milestone.
- `harness-skill` must not bind the next initializer when the gate has an unresolved Milestone-side blocker.

## Relationship To Other Gates

This gate is a Milestone-entry blocker. It is distinct from:

- Worktrack Gate, which judges a single Worktrack closeout inside WorktrackScope.
- Milestone Gate, which validates a goal-driven Milestone after its declared Worktracks close.

The gates are layered. `complex_project_entry_gate` prevents unsafe Milestone entry; Worktrack Gate handles local execution quality; final Milestone Gate handles cross-worktrack integration and purpose achievement.
