---
title: "Worktrack Dispatch Evidence Records"
status: active
updated: 2026-06-29
owner: servo-kernel
last_verified: 2026-06-29
---
# Worktrack Dispatch Evidence Records

`dispatch_evidence_records` define the linked records that make runtime dispatch decisions and delegated carrier executions auditable without prose reconstruction. A closeout bundle links to these records through `dispatch_provenance`; consumers preserve the refs, `dispatch_provenance_status`, raw parent `dispatch_result_status`, and propagated `resolved_runtime_dispatch_status` instead of synthesizing missing dispatch evidence.

This contract covers two record types:

- `runtime_dispatch_record`: the parent control-plane decision record for one dispatch attempt.
- `subagent_dispatch_record`: the child execution-plane record for one real delegated carrier run created from that decision.

One `runtime_dispatch_record` may have zero or more `subagent_dispatch_record` children. Zero child records is valid only when the parent records a non-delegated final carrier, permission block, runtime gap, dispatch package unsafe result, or historical gap.

## Record References

Record refs must be stable enough for closeout and milestone consumers to re-open the original structured evidence:

```yaml
runtime_dispatch_record_ref: ".servo/...#runtime-dispatch-WT-..."
subagent_dispatch_record_refs:
  - ".servo/...#subagent-dispatch-WT-...-implement"
```

The exact storage location is runtime-owned. A ref may point into a dispatch result, a closeout report, a repo-refresh handoff, a milestone evidence record, or another stable structured artifact. The ref must identify a structured record, not a paragraph summary.

## runtime_dispatch_record Schema

Every future runtime dispatch record must contain these fields:

```yaml
runtime_dispatch_record:
  schema_version: "worktrack-runtime-dispatch-record/v1"
  record_id: "runtime-dispatch-WT-..."
  record_ref: string
  worktrack_id: "WT-..."
  milestone_id: "MS-..." | N/A
  dispatch_step_id: string
  created_at: string
  dispatch_owner: harness | worktrack-dispatch-skill | top_level_harness | N/A
  dispatch_policy_ref: string | N/A
  dispatch_packet_ref: string | N/A
  task_package_ref: string | N/A
  worktrack_contract_ref: string | N/A
  runtime_dispatch_mode: auto | delegated | current-carrier
  subagent_dispatch_mode: auto | delegated | current-carrier | N/A
  subagent_dispatch_mode_override_scope: worktrack-contract-primary | global-override | N/A
  override_source: worktrack_contract | control_state | programmer | policy_default | N/A
  decision_inputs:
    task_coupling: low | medium | high | unknown
    state_sharing_need: low | medium | high | unknown
    parallel_value: low | medium | high | unknown
    risk_profile: low | medium | high | unknown
    context_budget_fit: fits | tight | over_budget | unknown
    runtime_supports_subagent: yes | no | unknown
    permission_allows_delegation: yes | no | unknown
    dispatch_package_safety: safe | unsafe | unknown
  deterministic_recommendation:
    recommended_carrier: SubAgent | worktrack-generic-worker-skill | worktrack-doc-catch-up-skill | current-carrier | none
    recommendation_reason: string
  runtime_dispatch_profile:
    backend_runtime: codex-cli | claude-code-cli | unknown | string
    model_family: gpt | claude | deepseek | unknown | string
    subagent_dispatch_shell: available | unavailable | unknown
    runtime_supports_subagent: yes | no | unknown
    subagent_permission_state: allowed | blocked | unknown
    permission_allows_delegation: yes | no | unknown
    dispatch_package_safety: safe | unsafe | unknown
    delegation_attempted: yes | no
    attempted_carrier: SubAgent | worktrack-generic-worker-skill | worktrack-doc-catch-up-skill | current-carrier | none
    carrier_decision: delegated_subagent | delegated_skill | current_carrier_fallback | current_carrier_policy | blocked | historical_gap
    fallback_reason: runtime fallback | permission blocked | dispatch package unsafe | current-carrier policy | no matching dedicated skill | historical_gap | N/A
  profile_validation:
    status: pass | failed | missing | historical_gap
    validator_ref: string | N/A
    missing_fields: []
  final_carrier: SubAgent | worktrack-generic-worker-skill | worktrack-doc-catch-up-skill | current-carrier | none
  final_carrier_type: delegated_subagent | delegated_skill | current_carrier | none
  carrier_decision: delegated_subagent | delegated_skill | current_carrier_fallback | current_carrier_policy | blocked | historical_gap
  selection_reason: string
  delegation_attempted: yes | no
  attempted_carrier: SubAgent | worktrack-generic-worker-skill | worktrack-doc-catch-up-skill | current-carrier | none
  fallback_reason: runtime fallback | permission blocked | dispatch package unsafe | current-carrier policy | no matching dedicated skill | historical_gap | N/A
  dispatch_result_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap
  subagent_dispatch_record_refs: []
  closeout_evidence_bundle_ref: string | N/A
  evidence_state: captured | linked | missing | historical_gap | contaminated
  residual_risks: []
```

## runtime_dispatch_record Status Semantics

| Status | Meaning |
| --- | --- |
| `delegated` | A real delegated carrier was created and must have at least one linked `subagent_dispatch_record`. |
| `current_carrier_fallback` | The task ran on the current carrier after an allowed `auto` fallback or explicit current-carrier policy. No SubAgent execution may be inferred. |
| `permission_blocked` | Delegation was required or preferred but blocked by the permission boundary. |
| `runtime_gap` | Delegation was required or preferred but the host runtime did not expose a real dispatch shell or support. |
| `dispatch_package_unsafe` | Delegation did not proceed because the package was too broad, unsafe, stale, or missing required boundaries. |
| `blocked` | Dispatch could not produce a legal execution carrier. |
| `historical_gap` | Older work predates this record contract. It cannot be rewritten into positive dispatch evidence. |

`current_carrier_fallback`, `permission_blocked`, `runtime_gap`, `dispatch_package_unsafe`, `blocked`, and `historical_gap` are distinct evidence states. Consumers must preserve the distinction.

## Consumer Propagation Schema

Any closeout bundle, milestone status input, milestone gate input, or milestone gate output that summarizes dispatch evidence must carry this shape or an equivalent lossless representation:

```yaml
dispatch_provenance_summary:
  runtime_dispatch_record_ref: string | N/A
  subagent_dispatch_record_refs: []
  dispatch_provenance_status: captured | linked | incomplete | missing | historical_gap | contaminated
  dispatch_result_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | N/A
  resolved_runtime_dispatch_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | incomplete | missing | contaminated
```

`dispatch_result_status` is the raw parent `runtime_dispatch_record.dispatch_result_status` when the parent record is readable and structurally complete enough to expose it. `resolved_runtime_dispatch_status` is the consumer-facing propagation field. It must equal the raw parent status when available; otherwise it records `missing`, `incomplete`, `historical_gap`, or `contaminated` according to the evidence condition.

Consumers that receive only `runtime_dispatch_record_ref` must dereference the parent record before aggregation when the ref is readable. If dereference is impossible, they must set `dispatch_provenance_status: missing` or `incomplete` and set `resolved_runtime_dispatch_status` accordingly. Consumers must not collapse `current_carrier_fallback`, `runtime_gap`, `permission_blocked`, `dispatch_package_unsafe`, `blocked`, `historical_gap`, and `delegated` into a generic fallback, failure, or missing state.

## subagent_dispatch_record Schema

Every real delegated carrier execution must create one child record:

```yaml
subagent_dispatch_record:
  schema_version: "worktrack-subagent-dispatch-record/v1"
  record_id: "subagent-dispatch-WT-..."
  record_ref: string
  parent_runtime_dispatch_record_ref: string
  worktrack_id: "WT-..."
  milestone_id: "MS-..." | N/A
  dispatch_step_id: string
  created_at: string
  carrier_identity:
    carrier: SubAgent | worktrack-generic-worker-skill | worktrack-doc-catch-up-skill | dedicated_skill | string
    carrier_type: delegated_subagent | delegated_skill
    model_family: gpt | claude | deepseek | unknown | string
    backend_runtime: codex-cli | claude-code-cli | unknown | string
    session_ref: string | N/A
  task_package:
    dispatch_packet_ref: string
    task_package_ref: string
    worktrack_contract_ref: string | N/A
    task_id: string
    scope_ref: string | N/A
    acceptance_ref: string | N/A
    context_budget_ref: string | N/A
  isolation_boundary:
    independent_carrier: true | false
    sibling_axis: blackbox | whitebox | anticheat | composite | N/A
    context_visibility: bounded | polluted | unknown
    prohibited_context_read: true | false | unknown
    same_carrier_as: [] | N/A
    isolation_guarantee: true | false | unknown
    carrier_isolation_broken: true | false | unknown
  execution:
    started_at: string | N/A
    completed_at: string | N/A
    completion_status: completed | blocked | failed | cancelled | timed_out | historical_gap
    touched_paths: []
    validation_refs: []
    evidence_refs: []
    returned_payload_ref: string | N/A
    returned_payload_status: captured | missing | contaminated | historical_gap
  cleanup_close_status:
    status: open | closed | cleanup_pending | failed | not_applicable | historical_gap
    cleanup_ref: string | N/A
    close_ref: string | N/A
  closeout_evidence_bundle_ref: string | N/A
  evidence_state: captured | linked | missing | historical_gap | contaminated
  residual_risks: []
```

## subagent_dispatch_record Status Semantics

| Status | Meaning |
| --- | --- |
| `completed` | Delegated carrier returned a structured payload and the parent can continue to Verify / Judge. |
| `blocked` | Delegated carrier could not proceed because required context, permissions, or acceptance boundaries were missing. |
| `failed` | Carrier ran but failed the delegated task. |
| `cancelled` | Carrier was stopped before a usable result. |
| `timed_out` | Carrier did not return in the allowed runtime window. |
| `historical_gap` | A historical delegated execution is known to exist but was not captured under this contract. |

A `subagent_dispatch_record` is only valid for real delegated execution. Current-carrier fallback must not create a synthetic child record.

## Lifecycle

1. Dispatch creates or links one `runtime_dispatch_record` before execution begins.
2. If the final carrier is delegated, each created carrier writes one `subagent_dispatch_record` linked through `parent_runtime_dispatch_record_ref`.
3. The delegated carrier returns a structured payload and evidence refs; the child record records `returned_payload_ref`, `completion_status`, and cleanup/close status.
4. Verify, Judge, and Close consume the refs. They may append status refs but must not rewrite missing fields from prose summaries.
5. Closeout writes `dispatch_provenance.runtime_dispatch_record_ref` and `dispatch_provenance.subagent_dispatch_record_refs` into the `closeout_evidence_bundle`.
6. Milestone Status and Milestone Gate preserve the linked refs, `dispatch_provenance_status`, raw `dispatch_result_status`, and `resolved_runtime_dispatch_status` when preparing closed worktrack inputs.

## Consumer Rules

- If a linked record is expected but absent, record `missing`.
- If the Worktrack predates this contract, record `historical_gap`.
- If the record exists but lacks required fields, record `incomplete` or `contaminated` in the consuming bundle/report.
- Do not infer delegated execution from `implementer_carrier`, a model name, or a prose statement. Delegated execution requires a linked `subagent_dispatch_record`.
- Do not infer runtime fallback from silence. Runtime fallback requires an explicit `runtime_dispatch_record.dispatch_result_status`.
- Do not collapse `delegated`, `permission_blocked`, `runtime_gap`, `dispatch_package_unsafe`, `current_carrier_fallback`, `blocked`, and `historical_gap` into a generic failure summary.
