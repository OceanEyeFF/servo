# Worktrack Contract

> 这是 `.servo/worktrack/contract.md` 的模板来源，用来填写单个 worktrack 的局部状态转移合同。最终内容应与 `docs/harness/artifact/worktrack/contract.md` 的定义一致。

## Metadata

- worktrack_id:
- branch:
- baseline_branch:
- baseline_ref:
- owner:
- updated:
- contract_status:

## Node Type

> 从 Goal Charter 的 Engineering Node Map 绑定，决定本 worktrack 的基线策略与判定标准。

- type:
- source_from_goal_charter:
- baseline_form:
- merge_required:
- gate_criteria:
- if_interrupted_strategy:

## Worktrack Intake Review

> Milestone 派生 worktrack 必须引用 RepoScope.Decide 的 pre-init intake review。

- worktrack_intake_review:
- repo_fundamentals:
- snapshot_freshness:
- milestone_purpose_alignment:
- historical_conflict_risk:
- worktrack_adjustment_recommendations:
- add_remove_worktrack_recommendations:
- intake_review_verdict:
- ready_for_worktrack_init:

## Execution Policy

> Execution Policy canonical semantics are not repeated here. Use `execution_policy_contract_ref` as the authority reference.

- execution_policy_contract_ref: docs/harness/artifact/worktrack/contract.md#execution-policy
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes

## Task Goal

- 

## Scope

- 

## Non-Goals

- 

## Impacted Modules

- 

## Planned Next State

- 

## Acceptance Criteria

- 

## Constraints

- 

## Verification Requirements

- 

## Rollback Conditions

- 

## Notes

- 
