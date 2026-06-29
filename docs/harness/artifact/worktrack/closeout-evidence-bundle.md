---
title: "Worktrack Closeout Evidence Bundle"
status: active
updated: 2026-06-29
owner: servo-kernel
last_verified: 2026-06-29
---
# Worktrack Closeout Evidence Bundle

`closeout_evidence_bundle` is the structured evidence envelope emitted during Worktrack closeout and consumed by Milestone Gate preparation. It is not a separate long-lived `.servo/worktrack/` artifact by default; it may live as a structured section inside the `worktrack-close-skill` closeout report, the repo-refresh handoff, or a milestone closeout record. Consumers must reference it with a stable `closeout_evidence_bundle_ref`.

The bundle exists to prevent Milestone Gate axes from reconstructing evidence from prose summaries. It records what was captured, what is linked elsewhere, what is missing, and what is a historical gap.

## Required Fields

Every future closeout bundle must contain these fields:

```yaml
closeout_evidence_bundle:
  schema_version: "worktrack-closeout-evidence-bundle/v1"
  worktrack_id: "WT-..."
  milestone_id: "MS-..." | N/A
  node_type: docs | feature | refactor | bugfix | config | test | research
  branch_policy:
    baseline_branch: string
    branch_source_ref: string
    worktrack_branch: string
    integration_target_ref: string
    closeout_target_ref: string
    checkpoint_base_ref: string
    final_baseline_branch: string
  self_review_record:
    status: captured | linked | missing | historical_gap | not_applicable
    record_ref: string | N/A
    verdict: pass | soft-fail | hard-fail | blocked | N/A
  single_acceptance_verdict:
    status: captured | linked | missing | historical_gap | not_applicable
    verdict_ref: string | N/A
    verdict: accepted | accepted_with_notes | blocked | N/A
    critical_failure: true | false | N/A
  worktrack_gate_evidence:
    status: captured | linked | missing | historical_gap
    evidence_ref: string | N/A
    gate_verdict: pass | soft-fail | hard-fail | blocked | N/A
    implementation_gate: pass | soft-fail | hard-fail | blocked | N/A
    validation_gate: pass | soft-fail | hard-fail | blocked | N/A
    policy_gate: pass | soft-fail | hard-fail | blocked | N/A
  closeout_gate_evidence:
    status: captured | linked | missing | historical_gap | not_applicable
    evidence_ref: string | N/A
    verdict: pass | soft-fail | hard-fail | blocked | N/A
  dispatch_provenance:
    status: captured | linked | incomplete | missing | historical_gap | contaminated
    runtime_dispatch_record_ref: string | N/A
    subagent_dispatch_record_refs: []
    missing_dispatch_record_refs: []
    dispatch_result_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | N/A
    resolved_runtime_dispatch_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | incomplete | missing | contaminated
    implementer_carrier: string | N/A
    reviewer_carrier_refs: []
    gate_judge_carrier_ref: string | N/A
    independence_summary: independent | same_carrier | unknown | historical_gap
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
  repo_refresh_checkpoint:
    status: captured | linked | missing | historical_gap | not_applicable
    checkpoint_ref: string | N/A
    latest_observed_checkpoint: string | N/A
  bundle_completeness:
    status: complete | incomplete | contaminated | historical_gap
    missing_required_fields: []
    historical_gap_fields: []
    contaminated_fields: []
    residual_risks: []
```

## Evidence State Semantics

Use these state values consistently:

| State | Meaning | Gate Treatment |
| --- | --- | --- |
| `captured` | Evidence was generated during the relevant control step and is present in the bundle. | May satisfy the corresponding evidence requirement. |
| `linked` | Evidence exists in another stable record and the bundle carries a reference. | May satisfy the requirement if the linked record is readable and fresh. |
| `incomplete` | A linked structured record exists but required fields are absent, unreadable, or internally incomplete. | Non-pass evidence; consumers must preserve the incomplete field list or status. |
| `missing` | Required evidence should exist for this Worktrack but was not captured. | Non-pass evidence; Milestone Gate preparation must report the missing field. |
| `historical_gap` | Older Worktrack did not capture this evidence because the contract did not exist yet. | Must remain visible; cannot be converted into synthetic pass evidence. |
| `contaminated` | Evidence is stale, reused, cross-axis polluted, same-carrier without disclosure, or otherwise unreliable. | Non-pass evidence; anti-cheat/composite axes must preserve the finding. |
| `not_applicable` | Evidence is not required for this node type or closeout path, with a reason. | Does not contribute positive evidence. |

`historical_gap` is not a waiver. It is an honest marker that lets future gates distinguish old missing evidence from current process failure.

## Linked Record Boundary

The bundle may require evidence produced by other records. It must link to those records instead of inlining or summarizing them:

- `runtime_dispatch_record_ref` points to a `runtime_dispatch_record` defined in [dispatch-evidence-records.md](./dispatch-evidence-records.md). It records the parent dispatch decision: inputs, deterministic recommendation, override source, final carrier, fallback reason, `dispatch_result_status`, and profile validation.
- `subagent_dispatch_record_refs` point to `subagent_dispatch_record` children defined in [dispatch-evidence-records.md](./dispatch-evidence-records.md). They record delegated carrier execution facts: carrier identity, task package, isolation boundary, returned payload, completion status, and cleanup/close status.
- `composite_lane_records.*.record_ref` points to `composite_lane_record` entries defined in [composite-lane-records.md](./composite-lane-records.md). The bundle carries link state for all six lanes: `code-review`, `feature-completeness`, `related-influence`, `intent-completeness`, `operator-simulation`, and `professional-review`. The linked lane records carry lane verdicts, findings, absorbed issue refs, residual risks, producer refs, validation refs, carrier/fallback facts, and freshness.

`dispatch_provenance.dispatch_result_status` preserves the raw parent `runtime_dispatch_record.dispatch_result_status` when the parent record is readable. `dispatch_provenance.resolved_runtime_dispatch_status` is the propagated consumer field: it must equal the parent status when available, or `missing` / `incomplete` / `historical_gap` / `contaminated` when the parent record cannot be trusted as complete evidence. Consumers must not collapse `current_carrier_fallback`, `runtime_gap`, `permission_blocked`, `dispatch_package_unsafe`, `blocked`, `historical_gap`, or `delegated`.

If a linked record is expected but absent, `dispatch_provenance.status` records `missing`, `resolved_runtime_dispatch_status` records `missing`, and `missing_dispatch_record_refs` lists the absent refs or expected roles. If the Worktrack predates the contract, both fields record `historical_gap`. If only prose describes dispatch, the bundle must not reconstruct the record; it records `missing` or `historical_gap`.

## Milestone Gate Consumption

Milestone Gate preparation must prefer `closeout_evidence_bundle_ref` over prose closeout summaries. For each closed Worktrack, the prepared input should include:

```yaml
closed_worktrack:
  id: "WT-..."
  node_type: docs
  verdict: pass | soft-fail | hard-fail | blocked
  critical_failure: true | false
  closeout_record_ref: string
  closeout_evidence_bundle_ref: string
  closeout_bundle_status: complete | incomplete | contaminated | historical_gap | missing
  runtime_dispatch_record_ref: string | N/A
  subagent_dispatch_record_refs: []
  dispatch_provenance_status: captured | linked | incomplete | missing | historical_gap | contaminated
  dispatch_result_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | N/A
  resolved_runtime_dispatch_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | incomplete | missing | contaminated
  composite_lane_records:
    code_review:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    feature_completeness:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    related_influence:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    intent_completeness:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    operator_simulation:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
    professional_review:
      record_ref: string | N/A
      status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
```

Rules:

- `complete` may be consumed by axis checks and aggregation.
- `incomplete`, `contaminated`, `missing`, and unaccepted `historical_gap` must be visible to blackbox / whitebox / anticheat / composite axes.
- A missing bundle must not be reconstructed from summaries.
- Dispatch provenance fields must be copied from the bundle or dereferenced linked dispatch records. Milestone Gate preparation must preserve both `dispatch_result_status` and `resolved_runtime_dispatch_status`; it must not downgrade distinct parent statuses into a generic missing/failed bucket.
- Composite lane record refs and statuses must be copied from the bundle or dereferenced linked lane records. Milestone Gate preparation must preserve lane statuses including `incomplete`, `missing`, `historical_gap`, `contaminated`, and `not_applicable`; it must not infer lane verdicts, findings, absorbed issue refs, or residual risks from prose closeout summaries.
- Programmer manual exception can accept residual risk at final acceptance, but it must preserve the original bundle status and anti-cheat findings.

## Producer Responsibilities

`worktrack-close-skill` is responsible for producing the bundle in its closeout report and repo-refresh handoff. The handoff must carry `dispatch_provenance.status`, `runtime_dispatch_record_ref`, `subagent_dispatch_record_refs`, `missing_dispatch_record_refs`, raw `dispatch_result_status`, and `resolved_runtime_dispatch_status` as structured fields, not as prose. It must also carry all six `composite_lane_records` entries with status, `record_ref`, `lane_id`, `producer_ref`, `validation_ref`, missing field lists, contamination reason, and not-applicable reason. If only a prose composite review exists, Close marks the lane `missing`, `historical_gap`, or `incomplete`; it does not rewrite the prose into a passable lane record.

`repo-refresh-skill` and `repo-writeback-skill` may preserve stable references in repo-level backlog or milestone closeout records, but they must treat dispatch provenance as passthrough evidence. If they cannot dereference an expected record, they mark the field `missing`, `incomplete`, `historical_gap`, or `contaminated`; they do not synthesize `delegated`, fallback, blocked, or historical states from summaries.

`milestone-status-skill` prepares closed Worktrack inputs using the bundle reference; `milestone-gate` consumes the prepared status but does not create missing bundle evidence. Both consumers preserve composite lane record refs/statuses and do not synthesize lane evidence from closeout prose.
