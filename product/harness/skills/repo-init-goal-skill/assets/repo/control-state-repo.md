# Harness Control State — Repo Level

> 这是 `.servo/control-state-repo.md` 的模板来源，承载 Repo + Milestone 级的慢变量控制状态。
> 与 `.servo/control-state.md`（跨 scope 记忆）和 `.servo/control-state-wt.md`（Worktrack 级）协同工作。
> `control_state_version: split` 是必填 frontmatter 字段。

## Metadata

- updated:
- owner:

## Repo Metadata

- rotation_count: 0
- last_rotation_at:
- handback_history_ref:

## Repo Control Level

- repo_scope: initialized
- repo_next_action:

## Active Worktrack Registry

- closed_worktrack_commits: []

## Milestone Pipeline — Active Milestone

- active_milestone:
- milestone_status:
- milestone_kind:
- active_milestone_branch:
- active_worktrack:
- active_worktrack_branch:
- milestone_pipeline_summary:
- active_milestone_branch_sync_state:
- active_milestone_progress:
- active_milestone_branch_head:

## Baseline Traceability

> `latest_observed_checkpoint` 与 `last_doc_catch_up_checkpoint` 是 git hash 幂等性锚点。
> 空值表示锚点尚未建立，首次观察必须完整刷新。

- latest_observed_checkpoint:
- last_doc_catch_up_checkpoint:
- verified_at_history:
- milestone_input_checkpoint:
- baseline_branch:
