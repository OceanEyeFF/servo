---
name: milestone-gate
description: 当顶层 Harness 已取得四份互相独立的 Milestone axis reports，需要按 target-type 与 aggregation rules 做唯一聚合裁决时，使用这个技能。
---

# Milestone Gate

## Role

This Skill is the only Milestone axis-report aggregator. It runs after every
declared Worktrack contribution is complete and after the upper Harness has
separately dispatched blackbox, whitebox, anticheat, and composite carriers.

It does not create or invoke an axis carrier, inspect a Worktrack round chain,
repeat Worktrack Review, or revalidate Close. It consumes independent reports
and returns one Milestone Gate verdict.

## Input

```yaml
milestone_gate_input:
  milestone_id: string
  milestone_objective: object
  target_type_rules: object
  aggregation_rules: object
  closed_worktrack_facts:
    - worktrack_id: string
      node_type: string | null
      initial_requirement_ref: string
      finished_handback_ref: string
      accepted_checkpoint: string
      closeout_checkpoint_commit: string
      stable_evidence_refs: [string]
  axis_reports:
    blackbox: object
    whitebox: object
    anticheat: object
    composite: object
  axis_dispatch_profile: object
```

The Worktrack facts are contribution references, not a second Worktrack
acceptance interface. Candidate input contains no Worktrack Gate record,
closeout bundle, dispatch packet/provenance, composite lane record, Contract,
or `.servo/tmp` round data.

Each axis report must include:

- `axis`, `verdict`, `severity`, and concrete `evidence_refs`;
- `axis_applicability_state` and `expected_method`;
- `missing_evidence` and conditional substitution evidence;
- its own `runtime_dispatch_profile` and isolation result;
- target type/scenario interpretation when relevant.

## Input Guards

Block before aggregation when:

- any required axis report is missing, malformed, stale, or for another
  Milestone;
- a report or its package contains a sibling report, verdict, finding, or
  conclusion;
- `axis_dispatch_profile` shows same-carrier cross-axis execution, broken
  isolation, ambiguous carrier identity, or nested dispatch;
- target type/applicability cannot be resolved with high-confidence evidence;
- required substitution evidence or mixed-slice coverage is missing;
- aggregation rules are missing or internally contradictory;
- a stable evidence ref resolves only into disposable `.servo/tmp` content.

Gate does not repair these inputs and does not infer a missing report from a
Milestone summary.

## Aggregation

Apply the configured rules in this order:

1. Resolve target type, target scenario, per-axis applicability, and any mixed
   delivery slices.
2. Preserve each report's raw verdict and evidence. Compute whether each
   applicable or substituted axis is satisfied.
3. Apply Worktrack weights and explicit overrides from `aggregation_rules`.
4. Detect contradictions among high-weight contribution claims and axis
   findings.
5. Apply veto rules. Blackbox, whitebox, and anticheat are veto-capable by
   default; composite follows the configured rule.
6. Apply a degenerate all-pass rule only when applicability is fully resolved,
   all mandatory axes are satisfied, no veto or contradiction exists, and no
   weight override hides a failure.

`not_applicable` is not a pass. `substituted` is satisfied only when its method,
evidence ref, pass result, and completion-signal coverage are concrete.

## Verdict

Allowed values are:

- `pass`: every mandatory axis is satisfied and no veto/contradiction remains;
- `soft-fail`: non-veto concerns require Programmer judgment or follow-up;
- `hard-fail`: a critical implementation or evidence claim failed;
- `blocked`: required input, isolation, applicability, or evidence is missing or
  contaminated.

Any non-pass verdict blocks Milestone closeout. A Programmer manual exception
may be recorded by the upper acceptance layer, but it must not rewrite this
Gate verdict. Preserve the original verdict, anticheat findings, affected refs,
and follow-up decision as `anti_cheat_findings_preserved` and related exception
facts.

## Output

```yaml
milestone_gate_result:
  milestone_id: string
  milestone_gate_verdict: pass | soft-fail | hard-fail | blocked
  milestone_gate_summary: string
  milestone_gate_execution_model: axis_report_aggregation
  axis_reports: object
  axis_report_status: complete | missing | contaminated | isolation_broken | blocked_axis
  axis_dispatch_profile: object
  axis_satisfaction: object
  aggregation_rules_applied: boolean
  aggregation_rules_missing: boolean
  per_worktrack_weights: [object]
  contradiction_findings: [object]
  contradiction_blocked: boolean
  degenerate_and_applied: boolean
  blockers: [string]
  evidence_refs: [string]
  manual_exception: object | null
  accepted_gate_verdict_preserved_as: string | null
  anti_cheat_findings_preserved: boolean | null
  manual_exception_followup_ref: string | null
```

The output references all four original reports. It does not copy Worktrack
round data or create a new persistent Worktrack artifact.

## Boundaries

- Read-only: do not modify source, evidence, handbacks, backlog, Milestone, or
  control state.
- Do not create, invoke, retry, or simulate axis carriers. The upper Harness is
  the dispatch owner.
- Do not allow an axis carrier or consumer Skill to create descendants.
- Do not read sibling inputs beyond the four reports explicitly supplied for
  aggregation.
- Do not inspect `initial-requirement.yaml`, `finished-handback.yaml`, Git diffs,
  or Worktrack validation to redo technical judgment. Axis carriers own fresh
  technical checks.
- Do not accept Candidate/legacy fallback, Worktrack Gate authority, or a
  legacy closeout transport.
- Stop immediately after returning the structured result. The upper Harness
  owns direct canonical observation, purpose evaluation, and authorized writeback.

## Resources

Use only the approved Milestone objective/configuration, minimal completed
contribution facts, explicit target-type and aggregation rules, four independent
axis reports, and their dispatch profile. This Skill has no runtime dependency
on source-repo Harness docs.
