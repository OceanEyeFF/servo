# Closeout Record Real-Shape Regression Fixtures

Minimal tracked closeout-shaped excerpts for milestone gate aggregation tests.
They preserve legacy/runtime-shaped failure modes without depending on ignored
`.servo` runtime state.

## WT-deploy-sync-and-dogfood-evidence

```yaml
closeout_evidence_bundle:
  schema_version: worktrack-closeout-evidence-bundle/v1
  worktrack_id: WT-deploy-sync-and-dogfood-evidence
  milestone_id: MS-20260628-001
  node_type: test
  branch_policy:
    baseline_branch: develop-servo
    branch_source_ref: abc1234
    worktrack_branch: wt/WT-deploy-sync-and-dogfood-evidence
    integration_target_ref: ms/MS-20260628-001
    closeout_target_ref: ms/MS-20260628-001
    checkpoint_base_ref: abc1234
    final_baseline_branch: develop-servo
  self_review_record:
    status: linked
    record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#self-review
    verdict: pass
  single_acceptance_verdict:
    status: linked
    verdict_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#single-acceptance
    verdict: accepted
    critical_failure: false
  worktrack_gate_evidence:
    status: linked
    evidence_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#gate-evidence
    gate_verdict: pass
    implementation_gate: pass
    validation_gate: pass
    policy_gate: pass
  closeout_gate_evidence:
    status: linked
    evidence_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#closeout-gate
    verdict: pass
  dispatch_provenance:
    status: linked
    runtime_dispatch_record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#runtime-dispatch
    subagent_dispatch_record_refs:
      - .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#subagent-dispatch
    missing_dispatch_record_refs: []
    dispatch_result_status: delegated
    resolved_runtime_dispatch_status: delegated
    implementer_carrier: SubAgent
    reviewer_carrier_refs:
      - .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#reviewer-carrier
    gate_judge_carrier_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#gate-judge
    independence_summary: "SubAgent implementer with reviewer and gate judge described in prose"
  composite_lane_records:
    code_review:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#code-review
      lane_id: code-review
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#code-review-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#code-review-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
    feature_completeness:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#feature-completeness
      lane_id: feature-completeness
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#feature-completeness-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#feature-completeness-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
    related_influence:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#related-influence
      lane_id: related-influence
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#related-influence-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#related-influence-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
    intent_completeness:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#intent-completeness
      lane_id: intent-completeness
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#intent-completeness-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#intent-completeness-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
    operator_simulation:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#operator-simulation
      lane_id: operator-simulation
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#operator-simulation-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#operator-simulation-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
    professional_review:
      status: linked
      record_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#professional-review
      lane_id: professional-review
      validation_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#professional-review-validation
      producer_ref: .servo/worktrack/WT-deploy-sync-and-dogfood-evidence.md#professional-review-producer
      missing_required_fields: []
      contaminated_reason: N/A
      not_applicable_reason: N/A
  repo_refresh_checkpoint:
    status: linked
    checkpoint_ref: .servo/repo/refresh.md#WT-deploy-sync-and-dogfood-evidence
    latest_observed_checkpoint: abc1234
  bundle_completeness:
    status: complete
    missing_required_fields: []
    historical_gap_fields: []
    contaminated_fields: []
    residual_risks: []
```

## WT-closeout-evidence-bundle-contract

```yaml
closeout_evidence_bundle:
  schema_version: worktrack-closeout-evidence-bundle/v1
  worktrack_id: WT-closeout-evidence-bundle-contract
  milestone_id: MS-20260628-001
  node_type: test
  branch_policy:
    baseline_branch: develop-servo
    branch_source_ref: def5678
    worktrack_branch: wt/WT-closeout-evidence-bundle-contract
    integration_target_ref: ms/MS-20260628-001
    closeout_target_ref: ms/MS-20260628-001
    checkpoint_base_ref: def5678
    final_baseline_branch: develop-servo
  self_review_record:
    status: linked
    record_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#self-review
    verdict: pass
  single_acceptance_verdict:
    status: linked
    verdict_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#single-acceptance
    verdict: accepted
    critical_failure: false
  worktrack_gate_evidence:
    status: linked
    evidence_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#gate-evidence
    gate_verdict: pass
    implementation_gate: pass
    validation_gate: pass
    policy_gate: pass
  closeout_gate_evidence:
    status: linked
    evidence_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#closeout-gate
    verdict: pass
  dispatch_provenance:
    runtime_dispatch_record_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#runtime-dispatch
    subagent_dispatch_record_refs: []
    missing_dispatch_record_refs: []
    resolved_runtime_dispatch_status: incomplete
    implementer_carrier: current_carrier
    reviewer_carrier_refs: []
    gate_judge_carrier_ref: .servo/worktrack/WT-closeout-evidence-bundle-contract.md#gate-judge
    independence_summary: unknown
  composite_lane_records:
    code_review: linked
  repo_refresh_checkpoint:
    status: linked
    checkpoint_ref: .servo/repo/refresh.md#WT-closeout-evidence-bundle-contract
    latest_observed_checkpoint: def5678
  bundle_completeness:
    status: incomplete
    missing_required_fields:
      - dispatch_provenance.status
      - dispatch_provenance.dispatch_result_status
      - composite_lane_records
    historical_gap_fields: []
    contaminated_fields: []
    residual_risks: []
```
