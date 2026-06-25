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
