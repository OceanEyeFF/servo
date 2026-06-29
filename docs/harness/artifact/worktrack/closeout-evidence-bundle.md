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
    runtime_dispatch_record_ref: string | N/A
    subagent_dispatch_record_refs: []
    implementer_carrier: string | N/A
    reviewer_carrier_refs: []
    gate_judge_carrier_ref: string | N/A
    independence_summary: independent | same_carrier | unknown | historical_gap
  composite_lane_records:
    code_review_ref: string | N/A
    feature_completeness_ref: string | N/A
    related_influence_ref: string | N/A
    intent_completeness_ref: string | N/A
    operator_simulation_ref: string | N/A
    professional_review_ref: string | N/A
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
| `missing` | Required evidence should exist for this Worktrack but was not captured. | Non-pass evidence; Milestone Gate preparation must report the missing field. |
| `historical_gap` | Older Worktrack did not capture this evidence because the contract did not exist yet. | Must remain visible; cannot be converted into synthetic pass evidence. |
| `contaminated` | Evidence is stale, reused, cross-axis polluted, same-carrier without disclosure, or otherwise unreliable. | Non-pass evidence; anti-cheat/composite axes must preserve the finding. |
| `not_applicable` | Evidence is not required for this node type or closeout path, with a reason. | Does not contribute positive evidence. |

`historical_gap` is not a waiver. It is an honest marker that lets future gates distinguish old missing evidence from current process failure.

## Linked Record Boundary

The bundle may require evidence produced by other records. It must link to those records instead of inlining or summarizing them:

- `runtime_dispatch_record_ref` records the parent dispatch decision: inputs, deterministic recommendation, override source, final carrier, fallback reason, and profile validation.
- `subagent_dispatch_record_refs` record delegated carrier execution facts: carrier identity, task package, isolation boundary, returned payload, completion status, and cleanup/close status.
- composite lane refs point to explicit lane records, not a single prose review bucket.

If a linked record is expected but absent, the bundle records `missing`. If the Worktrack predates the contract, it records `historical_gap`.

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
  closeout_bundle_status: complete | incomplete | contaminated | historical_gap
```

Rules:

- `complete` may be consumed by axis checks and aggregation.
- `incomplete`, `contaminated`, and unaccepted `historical_gap` must be visible to blackbox / whitebox / anticheat / composite axes.
- A missing bundle must not be reconstructed from summaries.
- Programmer manual exception can accept residual risk at final acceptance, but it must preserve the original bundle status and anti-cheat findings.

## Producer Responsibilities

`worktrack-close-skill` is responsible for producing the bundle in its closeout report and repo-refresh handoff. `repo-refresh-skill` may write the stable reference into repo-level backlog or milestone closeout records. `milestone-status-skill` prepares closed Worktrack inputs using the bundle reference; `milestone-gate` consumes the prepared status but does not create missing bundle evidence.
