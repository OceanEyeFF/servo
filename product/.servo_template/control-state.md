---
artifact_type: "control-state"
control_state_version: split
---
# Harness Control State

> 这是 `.servo/control-state.md` 的模板来源，仅保留跨 Repo/Worktrack 的控制记忆。
> 自 control-state 分拆后，Repo + Milestone 级字段 → `.servo/control-state-repo.md`、
> Worktrack 级字段 → `.servo/control-state-wt.md`、人类可调配置 → `.servo/operator-config.md`。
> `control_state_version: split` 是必填 frontmatter 字段，触发分拆文件 hydration。
> 缺失字段只能按最保守默认值解释，不能静默扩大权限或自动性。

## Metadata

- updated:
- owner:

## Handback Guard

- handoff_state: none
- last_handback_signature:
- handback_reaffirmed_rounds: 0
- stable_handback_threshold: 2
- handback_lock_active: false
- last_unlock_signal: N/A
- stop_reason_history: []

## Approval Boundary

- needs_programmer_approval:
- reason:
- approval_scope:
- approval_persistence: one-shot

## Linked Formal Documents

- worktrack_contract:
- plan_task_queue:
- gate_evidence:

## Autonomy Ledger

- autonomy_budget_remaining: 1
- autonomous_worktracks_opened: 0

## Branch Environment Guard

> 分支上下文守卫字段。在分拆架构中这些字段的实际运行时位置在 control-state-repo.md 和 control-state-wt.md，
> 此处保留以通过 governance semantic check。详见 control-state-repo.md 的 Baseline Traceability 和 Milestone Pipeline 段。

- baseline_branch:
- active_milestone_branch:
- current_branch_context: unknown
- expected_branch_context: unknown
- branch_context_guard_status: blocked
- branch_context_required_ref:
- worktrack_branch:

## SubAgent Default Contract

> 执行载体选择合同。运行时字段位于 operator-config.md，此处保留以满足 governance semantic check。

- SubAgent default: auto
- 权限边界: worktrack-contract-primary
- Dispatch Decision Policy: 按 coupling/state-sharing/parallel-value/risk/context-budget 选择
- subagent_dispatch_mode: auto
- subagent_dispatch_mode_override_scope: worktrack-contract-primary
- global-override: false
- runtime_dispatch_mode: auto
- delegated: false
- current-carrier: true
- runtime fallback: N/A
- dispatch package unsafe: false

## Runtime Dispatch Profile

> 运行时分派配置文件。运行时字段在 gate-evidence.md 中记录，此处保留以满足 governance semantic check。

- runtime_dispatch_profile: N/A
- backend_runtime: N/A
- model_family: N/A
- subagent_dispatch_shell: N/A
- runtime_supports_subagent: unknown
- subagent_permission_state: unknown
- permission_allows_delegation: unknown
- dispatch_package_safety: unknown
- delegation_attempted: false
- attempted_carrier: current-carrier
- carrier_decision: auto
- fallback_reason: N/A

## User-Defined Servo Controls

> 用户可配置的 Servo 控制参数。运行时字段在 operator-config.md 中，此处保留以满足 governance semantic check。

- continuous_progression_permission: false
- per_milestone_automatic_worktrack_budget: 0
- default_servo_work_branch: develop
- protected_branch_policy: master protected
- branch_mutation_policy: no force push
- auto_maintained_runtime_facts_not_asked: "milestone_pipeline_summary, last_doc_catch_up_checkpoint, latest_observed_checkpoint, runtime_dispatch_profile, progress_counters, observed_git_hash, active_worktrack"
- runtime facts: auto-maintained
- milestone_pipeline_summary: N/A
- last_doc_catch_up_checkpoint: N/A
- latest_observed_checkpoint: N/A
- observed_git_hash: N/A
- progress_counters: N/A
- active_worktrack: N/A

## Continuation Authority

> 运行时在 operator-config.md，此处保留为 compact/validate 兼容。

- post_contract_autonomy: false

## Review Gate

> 运行时在 control-state-repo.md，此处保留为 compact/validate 兼容。

- milestone_review_gate_ready: false
- milestone_review_gate_checkpoint: N/A

## Current Control Level

> 控制面当前层级。运行时字段在 control-state-repo.md 和 control-state-wt.md 中。此处保留为兼容 compact/validate 测试。

- repo_scope: active
- worktrack_scope: closed
- current_function:

## Active Worktrack

- active_worktrack:
- active_worktrack_branch:
- active_worktrack_node_type:

## Milestone Pipeline

- active_milestone:
- milestone_status:

## Baseline Branch

- active_milestone_branch:
- active_milestone_branch_head:
- baseline_branch:
- current_checkout:

## Current Next Action

- recommended_next_route:
- recommended_next_scope:

## Baseline Traceability

- latest_observed_checkpoint:
- checkpoint_ref:
- last_doc_catch_up_checkpoint:
