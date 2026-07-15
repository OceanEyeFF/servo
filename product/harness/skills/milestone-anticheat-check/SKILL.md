---
name: milestone-anticheat-check
description: 当 Milestone Gate 需要一个独立只读轴检查完成声明与稳定证据是否可信、未伪造、未复用或未绕过边界时，使用这个技能。
---

# Milestone Anticheat Check

## Role

This Skill is the independent evidence-credibility axis for Milestone Gate. It
checks whether completed Worktrack contribution claims are supported by stable,
specific, fresh evidence. It does not decide implementation correctness, repeat
Worktrack Review, aggregate sibling axes, or create another SubAgent.

The upper Harness runs this Skill in an isolated carrier. The input must not
contain blackbox, whitebox, or composite reports, verdicts, findings, or
conclusions.

## Input

```yaml
anticheat_input:
  milestone_id: string
  milestone_objective: object
  target_type: string
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

The Skill may read the referenced immutable initial requirements, finished
handbacks, checkpoints, diffs, source, validation output, and stable evidence.
It must not require legacy Self-Review, Single-Acceptance, Worktrack Gate,
closeout bundle, dispatch provenance, per-Worktrack lane records, or
`.servo/tmp` runtime content.

## Checks

Run every applicable check independently and attach concrete evidence refs:

### A1 Evidence existence and specificity

Resolve each claimed stable ref. Flag missing paths, placeholders, vague prose,
or evidence that cannot identify what was checked.

### A2 Cross-contribution evidence reuse

Detect the same evidence ref or validation result being used for materially
different Worktrack claims without an explicit shared-scope reason and fresh
applicability check.

### A3 Claim-to-check coverage

Map initial acceptance checks and final acceptance summary entries to concrete
implementation/validation/governance/runtime/artifact evidence. Missing mapping
is non-positive evidence, not an inferred pass.

### A4 Boundary-bypass signals

Detect completion claims that omit the immutable initial requirement, finished
handback, `accepted_checkpoint`, `closeout_checkpoint_commit`, or stable evidence, or that depend only on
disposable `.servo/tmp` material. Do not replay the Close Git transaction.

### A5 Freshness

Confirm that evidence identifies the checkpoint it supports and is not stale
relative to `accepted_checkpoint` and `closeout_checkpoint_commit`. Git refs and recorded checkpoints
are primary; filesystem timestamps are never sole hard-fail evidence.

### A6 Circular or self-asserted evidence

Detect evidence whose only support is the same completion summary or an
unverified assertion, without an observable implementation, validation, or
artifact fact. Do not request Human/LLM/carrier identity or provenance.

### A7 Contamination and omission

Detect sibling-axis content in the input, suppressed negative results,
contradictory refs, unexplained evidence gaps, or a summary that omits known
residuals. Sibling contamination blocks this axis.

## Severity And Verdict

Use measured facts where possible: missing/ref counts, reuse counts, checkpoint
relations, acceptance coverage, and contradiction counts. Scenario judgment is
allowed when the evidence cannot be reduced to a count, but must state the
reason and uncertainty.

Per finding severity is `low | medium | high`. The axis verdict is:

- `pass`: all mandatory checks have credible evidence and no material issue;
- `soft_fail`: bounded credibility risk remains but no completion claim is
  disproved;
- `hard_fail`: fabricated, knowingly misleading, materially stale, or bypassed
  evidence undermines a completion claim;
- `blocked`: required evidence is absent, unreadable, contaminated, or too
  ambiguous to judge.

High-severity and hard-fail findings retain veto power at Milestone Gate.
`historical_gap` is visible non-positive evidence, distinct from missing,
incomplete, and contaminated. It is not a waiver, not a pass, and cannot become
synthetic pass evidence. A manual exception belongs to final Programmer
acceptance; the original gap and finding remain preserved.

## Output

```yaml
anticheat_report:
  axis: anticheat
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  checklist_results:
    - check_id: A1 | A2 | A3 | A4 | A5 | A6 | A7
      verdict: pass | soft_fail | hard_fail | blocked
      finding: string
      evidence_refs: [string]
      quantitative_indicators: object | null
      scenario_judgment: string | null
  affected_worktracks: [string]
  missing_evidence: [string]
  residual_risks: [string]
  evidence_refs: [string]
  axis_applicability_state: applicable | substituted | not_applicable | blocked
  expected_method: string
  runtime_dispatch_profile: object
  isolation_guarantee: boolean
  historical_gap_preserved: boolean
```

## Boundaries

- Read-only. Do not modify source, artifacts, control state, or evidence.
- Do not consume sibling reports or infer their conclusions.
- Do not spawn a descendant SubAgent. Return input gaps to the upper Harness.
- Do not repeat blackbox behavior testing, whitebox implementation review, or
  composite intent assessment.
- Do not aggregate the four axes or alter Worktrack/Milestone state.
- Do not require or synthesize legacy Worktrack artifacts.

## Resources

Use only the common factual base supplied by the upper Harness and the explicit
repo/source/evidence reads allowed for this axis. This Skill has no runtime
dependency on source-repo Harness documentation.
