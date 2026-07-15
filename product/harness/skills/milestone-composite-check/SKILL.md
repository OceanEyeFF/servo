---
name: milestone-composite-check
description: 当 Milestone Gate 需要独立检查多个已完成 Worktrack contribution 组合后是否覆盖 Milestone 意图、交互与专业完成度时，使用这个技能。
---

# Milestone Composite Check

## Role

This Skill is the independent composite axis for Milestone Gate. It checks how
the completed Worktrack contributions compose against the Milestone objective,
acceptance criteria, cross-contribution interactions, operator path, and
professional completeness.

It does not aggregate blackbox, whitebox, or anticheat results. It receives no
sibling report, verdict, finding, or conclusion. Only `milestone-gate`
aggregates the four axis reports.

## Input

```yaml
composite_input:
  milestone_id: string
  milestone_objective: object
  completion_signals: [object]
  acceptance_criteria: [object]
  target_type: string
  target_scenario: string
  completed_contributions:
    - worktrack_id: string
      initial_requirement_ref: string
      finished_handback_ref: string
      accepted_checkpoint: string
      closeout_checkpoint_commit: string
      acceptance_summary: object
      residuals: [object]
      stable_evidence_refs: [string]
  allowed_repo_reads: [string]
```

The common factual base may be supplemented by bounded reads of source,
artifacts, runbooks, validation, and operator-facing surfaces allowed in the
input. It must not include per-Worktrack composite lane records, legacy
closeout bundles, Worktrack Gate records, or sibling axis output.

## Assessment

Perform one fresh composite assessment across these dimensions:

### C1 Contribution coverage

Map every Milestone completion signal and acceptance criterion to one or more
completed contributions and concrete evidence. Identify gaps, duplicate claims,
and contributions that do not support the Milestone objective.

### C2 Feature and artifact completeness

Check that the assembled deliverables include the required implementation,
validation, governance, runtime, and artifact surfaces for this target type.
Do not treat mere Worktrack completion as proof of Milestone completeness.

### C3 Related influence and integration

Inspect cross-contribution interfaces, ordering assumptions, shared files,
configuration, migrations, and compatibility boundaries. Record unresolved
interaction risks without rerunning Worktrack Close.

### C4 Intent completeness

Compare the assembled result with the original Milestone objective and accepted
scope. Flag mission drift, omitted intent, accidental expansion, or a set of
individually valid contributions that does not achieve the combined purpose.

### C5 Operator path

For operator-facing targets, inspect the complete workflow/runbook/CLI/config
path and available stable evidence. This is a composite completeness assessment,
not a replacement for blackbox execution.

### C6 Professional readiness

Assess whether residuals, follow-up requirements, documentation/maintenance
impact, and release/deploy boundaries are explicit enough for Programmer final
acceptance. This dimension does not consume another axis's professional-review
verdict.

## Applicability

Use `target_type` and `target_scenario` to select depth. For mixed delivery,
produce slice coverage so a non-program slice cannot hide a missing program
slice and vice versa. Unknown or contradictory target classification without a
high-confidence, evidence-backed resolution blocks the axis.

Each dimension returns `pass | soft_fail | hard_fail | blocked |
not_applicable`. `not_applicable` requires a concrete target-type reason and
does not count as positive evidence.

The overall verdict is:

- `pass`: every mandatory dimension is covered and no material composition gap
  remains;
- `soft_fail`: bounded residual composition risk requires explicit acceptance;
- `hard_fail`: the assembled contributions materially fail Milestone intent or
  conflict with each other;
- `blocked`: required common input or evidence is missing, contaminated, or
  cannot support a conclusion.

## Output

```yaml
composite_report:
  axis: composite
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  axis_applicability_state: applicable | substituted | not_applicable | split | blocked
  expected_method: string
  checklist_results:
    - check_id: C1 | C2 | C3 | C4 | C5 | C6
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      finding: string
      affected_worktracks: [string]
      evidence_refs: [string]
      residual_risks: [string]
  completion_signal_coverage: [object]
  acceptance_criteria_coverage: [object]
  slice_coverage: [object] | null
  missing_evidence: [string]
  residual_risks: [string]
  evidence_refs: [string]
  runtime_dispatch_profile: object
  isolation_guarantee: boolean
```

## Isolation And Boundaries

- Run read-only in an independent carrier selected by the upper Harness.
- Reject an input package that contains any blackbox, whitebox, or anticheat
  report, verdict, finding, or conclusion.
- Do not spawn a descendant SubAgent or request another axis to run.
- Do not aggregate sibling reports; `milestone-gate` is the only aggregator.
- Do not recreate fixed per-Worktrack lane artifacts or a shared axis-evidence
  interface.
- Do not inspect `.servo/tmp` round chains or redo Worktrack Review/Close.
- Do not write source, artifacts, backlog, Milestone, or control state.

## Resources

Use only the Milestone objective/configuration, immutable initial requirements,
finished handbacks, checkpoint refs, stable evidence refs, and bounded
repo/source reads supplied in this axis's clean input package. This Skill has no
runtime dependency on source-repo Harness docs.
