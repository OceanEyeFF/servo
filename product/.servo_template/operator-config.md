# Operator Config

> 这是 `.servo/operator-config.md` 的模板来源。
> 本文件承载人类可调的控制配置，与控制状态分拆后的 control-state.md / control-state-repo.md / control-state-wt.md 协同工作。
> `control_state_version: split` 是必填 frontmatter 字段。
> 缺失字段按最保守默认值解释，不能扩大权限。

## Metadata

- updated:
- owner:

## User-Defined Servo Controls

- subagent_dispatch_mode: auto
- subagent_dispatch_mode_override_scope: worktrack-contract-primary
- max_auto_new_worktracks: 3
- auto_slice_continue: false
- require_stop_after_slice: true
- default_work_branch:
- protected_branches: main
- branch_mutation_policy: manual-approval
- allowed_branch_patterns: develop-*, ms/*, wt/*, fix/*, docs/*

## Continuation Authority

- post_contract_autonomy: none
- require_manual_handoff: true
