# Worktrack Contract

> 这是 `.servo/worktrack/contract.md` 的模板来源，用来填写单个 worktrack 的局部状态转移合同。
> 按 `Control Signal` / `Supporting Detail` 双层输出：`Control Signal` 只放影响下一动作决策的关键结论；`Supporting Detail` 放完整上下文。

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

> Execution Policy runtime defaults are embedded below so installed skill packages do not need source-repo docs.

- execution_policy_contract_ref: bundled-runtime-semantics
- runtime_dispatch_mode: auto
- dispatch_mode_source: worktrack-contract
- allowed_values: auto / delegated / current-carrier
- fallback_reason_required: yes

## SubAgent Role / Mode Provenance

> Distinguish task_producing_subagent from review_acceptance_subagent; do not reuse producer evidence as independent review or acceptance evidence. If current-carrier fallback is used, record a machine-checkable fallback_reason_code.

- task_producing_subagent:
- review_acceptance_subagent:
- producer_carrier_ref:
- review_carrier_ref:
- acceptance_carrier_ref:
- evidence_provenance:
- current-carrier fallback:
- fallback_reason_code: runtime_gap | permission_blocked | coupling_or_shared_state | dispatch_package_unsafe | not_applicable
- fallback_reason:

## Post-Feedback Update Revalidation

> If post-review/post-gate updates occur, final acceptance evidence is not reusable until validation and acceptance rerun after the updated files or artifacts below.

- updated_files_or_artifacts:
- post_update_validation_timestamp:

## Task Goal

-

## Scope

### Control Signal
- 范围摘要（一句话）：

### Supporting Detail
- 详细范围项：

## Non-Goals

-

## Impacted Modules

-

## Planned Next State

-

## Acceptance Criteria

### Control Signal
- 核心验收项：

### Supporting Detail
- 完整验收标准：

## Constraints

### Control Signal
- 关键约束：

### Supporting Detail
- 详细约束条件：

## Verification Requirements

-

## Rollback Conditions

### Control Signal
- 回滚触发条件：

### Supporting Detail
- 回滚步骤与回退路径：

## Notes

-
