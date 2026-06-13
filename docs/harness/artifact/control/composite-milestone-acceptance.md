---
title: "Composite Milestone Acceptance"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-06-13
---

# Composite Milestone Acceptance

Composite Milestone Acceptance is the evidence contract for goal-driven milestone final acceptance readiness. It refines the existing `Milestone Gate`; it does not create a third scope and does not transfer final acceptance authority away from the programmer.

## Position

- Scope: `RepoScope`.
- Function: milestone-level evidence collection before `purpose_achieved`.
- Consumer: `milestone-status-skill`.
- Authority boundary: a passing composite report means the milestone is ready for programmer final acceptance; it is not final acceptance itself.

## Required Lanes

| Lane | Purpose | Required for deep |
| --- | --- | --- |
| `code-review` | Check implementation correctness, integration boundaries, regression risk, and maintainability across closed worktracks. | yes |
| `feature-completeness` | Compare delivered behavior against milestone completion signals and acceptance criteria. | yes |
| `related-influence` | Check adjacent docs, tests, installer/deploy/release boundaries, and operator-facing effects that could be affected by the milestone. | yes |
| `intent-completeness` | Verify the implemented result still matches the original user intent, appended issues, non-goals, and developer decision boundaries. | yes |
| `operator-simulation` | Simulate a realistic operator path using the delivered workflow and evidence, including failure/recovery surfaces when relevant. | yes |
| `professional-review` | Provide a senior engineering synthesis: residual risks, quality bar, release readiness, and whether follow-up worktracks are required. | yes |

Standard composite review may collapse multiple lanes into a single reviewer report only when the milestone is low-risk and does not touch release, deploy, migration, authority, destructive operations, path governance, or cross-worktrack integration. The report must still explicitly cover every lane.

## Review Depth

| Depth | When to use | Minimum carrier requirement |
| --- | --- | --- |
| `standard` | Docs-only or narrow milestones with no cross-worktrack runtime integration risk. | Current carrier may produce all lanes if it records why delegation is unnecessary. |
| `deep` | Milestones touching release, installer/deploy, migration, authority, destructive operations, path governance, security/privacy, or composite acceptance itself. | Attempt SubAgent or independent lane dispatch where available; if unavailable, record fallback per lane. |

Deep review is mandatory when any of these are true:

- milestone acceptance criteria include release readiness, installer behavior, migration, publish, package, registry, or version facts;
- a required worktrack changed Harness control rules, dispatch, gate, handback, path safety, or destructive behavior;
- the milestone contains appended issues whose impact spans more than one worktrack;
- the milestone will be used to justify a release-prep or final handback decision.

## Lane Output Schema

Each lane must produce an evidence envelope:

```yaml
lane_id: code-review
lane_depth: standard | deep
carrier: subagent | current-carrier | human
delegation_attempted: true | false
fallback_reason: null | "subagent dispatch unavailable"
inputs_reviewed:
  - ".servo/milestone/MS-YYYYMMDD-NNN.md"
  - ".servo/repo/worktrack-backlog.md"
freshness:
  git_checkpoint: "<commit>"
  evidence_current: true
verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
severity: none | low | medium | high
findings:
  - severity: low
    summary: "..."
    evidence_ref: "..."
residual_risks:
  - "..."
required_followups:
  - worktrack_title: "..."
    blocking: true | false
```

## Verdict Model

Composite lane verdicts map into Milestone Gate as follows:

| Lane verdict | Meaning | Milestone effect |
| --- | --- | --- |
| `accepted` | Lane found no blocking issue and no material residual risk. | Contributes pass. |
| `accepted_with_residual_risk` | Lane found low-severity or explicitly bounded residual risk. | Contributes pass only if risk is recorded in handback evidence. |
| `needs_followup_worktrack` | Lane found a non-trivial gap that can be isolated into a follow-up worktrack. | Blocks final acceptance unless programmer explicitly accepts deferral or adds the follow-up. |
| `blocked` | Lane found high-severity or unbounded risk, missing required evidence, or contradiction with milestone intent. | Blocks Milestone Gate. |

Overall composite verdict:

- `accepted`: every required lane is `accepted` or `accepted_with_residual_risk`, and no medium/high issue remains.
- `accepted_with_residual_risk`: every lane is non-blocking, but at least one lane has recorded residual risk.
- `needs_followup_worktrack`: at least one lane requires follow-up and no lane is `blocked`.
- `blocked`: any lane is `blocked`, required evidence is missing, or fallback evidence is insufficient for a mandatory deep lane.

## Fallback Rules

SubAgent dispatch is preferred for deep review lanes, but availability is runtime-dependent. When dispatch is unavailable:

- keep the lane; do not silently drop it;
- set `carrier: current-carrier` or `human`;
- record `delegation_attempted`, `attempted_carrier` if applicable, and `fallback_reason`;
- include a stricter self-review note describing what independence was lost;
- do not mark a mandatory deep lane `accepted` if the current carrier lacks enough evidence to inspect it.

Fallback can preserve progress, but it cannot erase evidence requirements.

## Handback Boundary

For goal-driven milestones:

1. Worktrack gates must already be closed.
2. Composite lanes must be available or explicitly fall back with sufficient evidence.
3. `milestone-status-skill` consumes the composite report as part of `Milestone Gate`.
4. If the composite verdict is `accepted` or `accepted_with_residual_risk`, `purpose_achieved` may be evaluated.
5. If `milestone_acceptance_verdict == achieved`, Harness must hand back to the programmer for final acceptance.

Only the programmer can accept final milestone completion. Harness may report readiness; it must not mark final acceptance solely because worktracks are done.
