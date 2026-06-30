---
title: "Composite Lane Evidence Records"
status: active
updated: 2026-06-29
owner: servo-kernel
last_verified: 2026-06-29
---
# Composite Lane Evidence Records

`composite_lane_record` is the per-lane evidence record for Worktrack closeout and Milestone composite acceptance. It makes each composite acceptance lane a linked evidence object instead of a prose paragraph inside a closeout or milestone summary.

The record is Worktrack-scoped and milestone-addressable. A closeout bundle links one record per lane when available, and preserves missing, incomplete, historical gap, contaminated, or not applicable states when a record cannot be used as positive evidence.

## Required Lanes

Every goal-driven Worktrack closeout that participates in Milestone composite acceptance must address these lane ids:

- `code-review`
- `feature-completeness`
- `related-influence`
- `intent-completeness`
- `operator-simulation`
- `professional-review`

## Record Schema

Each lane record must use this envelope:

```yaml
composite_lane_record:
  schema_version: "worktrack-composite-lane-record/v1"
  record_ref: string
  lane_id: code-review | feature-completeness | related-influence | intent-completeness | operator-simulation | professional-review
  check_id: C1 | C2 | C3 | C4 | C5 | C6
  worktrack_id: "WT-..."
  milestone_id: "MS-..." | N/A
  producer_ref: string
  produced_at: string | N/A
  validation_ref: string | N/A
  lane_status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
  lane_depth: standard | deep | N/A
  mandatory: true | false
  carrier: subagent | current-carrier | human | N/A
  delegation_attempted: true | false | unknown | N/A
  fallback_reason: string | N/A
  verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked | N/A
  severity: none | low | medium | high | N/A
  evidence_refs: []
  findings:
    - finding_id: string
      severity: low | medium | high
      summary: string
      evidence_refs: []
      absorbed_issue_refs: []
  absorbed_issue_refs: []
  residual_risks: []
  required_followups:
    - worktrack_title: string
      blocking: true | false
      evidence_ref: string | N/A
  missing_required_fields: []
  contaminated_reason: string | N/A
  not_applicable_reason: string | N/A
  freshness:
    git_checkpoint: string | N/A
    evidence_current: true | false | unknown
```

`record_ref` must be stable enough for later Milestone Gate preparation to dereference or report as missing. It may point to a section inside a closeout report, a repo-refresh handoff, a milestone closeout record, or another durable evidence artifact. It must not point only to an unstructured prose summary.

## Lane Status Semantics

| Status | Meaning | Consumer Treatment |
| --- | --- | --- |
| `captured` | The structured lane record was produced during the relevant Worktrack closeout or verification step. | May count as lane evidence if required fields and refs are present. |
| `linked` | The closeout bundle carries a stable reference to a structured lane record stored elsewhere. | May count as lane evidence after dereference or freshness validation. |
| `incomplete` | A lane record or expected ref exists, but required fields, evidence refs, producer refs, validation refs, or status fields are absent or unreadable. | Non-pass evidence. Preserve `missing_required_fields`; do not synthesize the lane from surrounding prose. |
| `missing` | The lane is required or expected for this Worktrack, but no structured record/ref was captured. | Non-pass evidence. Preserve as missing in closeout, milestone-status, composite-check, and gate outputs. |
| `historical_gap` | The Worktrack predates this contract or was closed before lane records were required. | Visible non-positive evidence. Do not rewrite historical summaries into lane records. |
| `contaminated` | The lane record is stale, reused, cross-axis polluted, same-carrier without disclosure, contradicts its producer/validation refs, or is otherwise unreliable. | Non-pass evidence. Preserve reason and affected refs for anti-cheat and final handback. |
| `not_applicable` | The lane is not required for the Worktrack or milestone path, and the reason is explicit. | Does not contribute positive evidence. Preserve reason; do not treat as pass. |

## Closeout Bundle Link Shape

`closeout_evidence_bundle.composite_lane_records` must use one entry per lane:

```yaml
composite_lane_records:
  code_review:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: code-review
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
  feature_completeness:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: feature-completeness
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
  related_influence:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: related-influence
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
  intent_completeness:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: intent-completeness
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
  operator_simulation:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: operator-simulation
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
  professional_review:
    status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    record_ref: string | N/A
    lane_id: professional-review
    validation_ref: string | N/A
    producer_ref: string | N/A
    missing_required_fields: []
    contaminated_reason: string | N/A
    not_applicable_reason: string | N/A
```

The closeout bundle records link state; the lane record holds findings, absorbed issue refs, residual risks, verdict, carrier, and freshness. If the bundle only has old scalar `*_ref` values, consumers must treat that as `incomplete` unless they can dereference a complete `worktrack-composite-lane-record/v1`.

## Consumer Rules

- `worktrack-close-skill` produces or links lane records in the closeout report and repo-refresh handoff. It may mark lanes `missing`, `incomplete`, `historical_gap`, `contaminated`, or `not_applicable`; it must not create pass evidence from prose.
- `milestone-status-skill` preserves lane record refs and statuses in the closed Worktrack input package and input checkpoint. It does not infer lane records from closeout summaries.
- `milestone-composite-check` consumes `composite_lane_record` refs/statuses for C1-C6. If a mandatory lane is `missing`, `incomplete`, `historical_gap`, `contaminated`, or unreasoned `not_applicable`, that lane cannot pass.
- `milestone-gate` aggregates the composite axis output and preserves per-Worktrack lane refs/statuses in the final Gate output. It must not turn lane prose summaries into structured records.

