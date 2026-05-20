---
title: "Repo Snapshot / Status"
status: active
updated: 2026-05-16
owner: servo-kernel
last_verified: 2026-05-10
---

# Repo Snapshot / Status

> `RepoScope` 的慢变量观测面。`RepoSnapshot/Status` 捕获 repo 结构化状态，作为 `RepoScope.Observe` 的输入和 `RepoScope.Refresh` 的输出。不替代实时变更日志——是经 Refresh 算子验证后写入的阶段性状态估计。

## 定位

- Scope: RepoScope
- 上游写入: repo-refresh-skill（在 worktrack closeout 后）、harness-skill（首次初始化）、repo-change-goal-skill（Goal Change 后）、milestone-status-skill（Milestone 验收后）
- 下游消费: repo-status-skill、repo-analysis-skill、repo-whats-next-skill、milestone-status-skill
- 与 [worktrack-backlog.md](./worktrack-backlog.md) 的区别: Snapshot 是当前快照（一个 repo 仅一个当前状态）；Backlog 是历史列表（所有 worktrack 条目按时间排列）。
- 与 [milestone-backlog.md](./milestone-backlog.md) 的区别: Snapshot 是当前观测切面；Milestone Backlog 是 pipeline 全集（所有 milestone 条目按优先级排列）。

## Required Fields

| 字段名 | 类型 | 必须 | 说明 |
|--------|------|------|------|
| `baseline_branch` | `string` | required | 当前基线分支名。对应 standard-fields 中的 `baseline_branch` |
| `baseline_ref` | `string` | required | 基线所在 commit hash |
| `current_branch_head` | `string` | required | 当前分支最新 commit hash |
| `working_tree_status` | `clean` \| `dirty` \| `has_untracked` \| `conflict` | required | 工作目录清洁度 |
| `mainline_status` | `stable` \| `ahead` \| `behind` \| `diverged` \| `unknown` | required | 当前分支相对于 baseline_branch 的偏离状态 |
| `latest_observed_checkpoint` | `string` | required | 最近一次观测到的 checkpoint 标识（milestone tag、release ref 等） |
| `last_verified_checkpoint` | `string` | required | 最近一次通过 gate 验证的 checkpoint 标识 |
| `activity_summary` | `object` | required | 近期活动摘要，子字段: `last_worktrack_id` (string)、`last_closeout_time` (ISO 8601 string)、`recent_prs` (string[])、`active_branches` (string[]) |
| `observed_at` | `string` (ISO 8601) | required | Snapshot 观测时间戳 |
| `governance_signals` | `string[]` | optional | 治理信号列表: 如 `config_drift`、`missing_baseline_evidence`、`unverified_writeback`、`stale_goal_charter` |
| `known_risks` | `string[]` | optional | 已知风险列表: 如 `pending_merge_conflict`、`broken_verification_chain`、`orphan_branch` |
| `pending_decisions` | `string[]` | optional | 待处理 RepoScope 决策项: 如 `goal_change_pending`、`append_request_queue_nonempty`、`baseline_rebase_needed` |
| `verification_summary` | `object` | optional | 最近验证结果摘要，子字段: `last_verified_at` (ISO 8601 string)、`verdict` (pass \| soft_fail \| hard_fail \| blocked)、`evidence_dimensions_covered` (string[]，如 `["implementation","test","policy","freshness"]`) |
| `source_baselines` | `object` | optional | 已验证 source root 的 checkpoint 摘要。最少支持 `product_harness_skills`，字段包含 `source_root`、`docs_owner`、`checkpoint_ref`、`git_head`、`verified_at`、`source_change_kind`。 |

## Consumer Contract

| Consumer Skill | 触发 Function | 消费字段 | 消费场景 |
|---------------|--------------|---------|---------|
| `repo-status-skill` | RepoScope.Observe | 全字段 | 生成人类可读的 repo 状态报告 |
| `repo-analysis-skill` | RepoScope.Decide | `baseline_branch`、`baseline_ref`、`mainline_status`、`activity_summary`、`governance_signals`、`known_risks`、`pending_decisions` | 结合 Goal Charter 做阶段性矛盾分析和优先级判断 |
| `repo-whats-next-skill` | RepoScope.Decide | `baseline_branch`、`baseline_ref`、`mainline_status`、`pending_decisions`、`known_risks` | 无新鲜 Repo Analysis 时，直接基于 Snapshot + Goal 做限定范围判定 |
| `repo-refresh-skill` | RepoScope.Refresh | 全字段（以写入为主，写入前也会读取当前 snapshot 做 diff） | worktrack closeout 后全量刷新 snapshot |
| `milestone-status-skill` | RepoScope.Observe | `latest_observed_checkpoint`、`last_verified_checkpoint`、`activity_summary.recent_prs`、`governance_signals`、`known_risks` | 对照 Milestone 的 `worktrack_list` 计算进度，结合 milestone-backlog 做 pipeline 上下文分析 |

Consumer 读取 Snapshot 时，若 `observed_at` 距今超过合理窗口（默认 24 小时）或 `baseline_ref` 与当前 repo 实际 HEAD 不一致，应标记为 stale 并在输出中暴露过期信号。不得将过期 snapshot 当作当前真相。

## Update Triggers

Snapshot/Status 只在以下触发点被显式写入，不随每次 Observe 自动刷新:

1. **Worktrack closeout 后** (primary trigger): repo-refresh-skill 在 worktrack merge -> cleanup 完成后，重新观测 repo 状态（branch、checkpoint、治理信号等）并全量更新 snapshot
2. **RepoScope 首次初始化**: harness-skill 在首次进入 RepoScope.Observe 时，若 snapshot 缺失则生成初始快照
3. **Goal Change 处理后**: repo-change-goal-skill 重新评估 baseline 后刷新 `baseline_branch`、`baseline_ref` 和相关 `governance_signals`
4. **Milestone 验收后**: milestone-status-skill 确认 checkpoint 后更新 `last_verified_checkpoint` 和 `verification_summary`

未经 Refresh 算子验证的状态不得写入 snapshot。`governance_signals`、`known_risks`、`pending_decisions` 只能由对应的 Observe/Decide/Refresh 算子写入，不得在执行平面（Implement）直接修改。

当 worktrack 改动 `product/harness/skills/`、`product/harness/skills/README.md`、或 `docs/harness/catalog/` 中的 canonical skill source traceability 时，repo refresh 应更新 `source_baselines.product_harness_skills`。该字段只保存经 gate/closeout 验证的 source root checkpoint 摘要，不保存 deploy target 状态，也不替代 release/package version facts。

## 字段命名一致性

本 artifact 遵循 [standard-fields.md](../standard-fields.md) 的约定:

- `baseline_branch` (string): 直接引用 standard-fields 的 Worktrack 专有字段，语义为基线分支
- `baseline_ref` (string): repo-analysis.md 同名字段，语义为基线 commit hash
- `source_baselines.*.git_head` (string): 对应 source root 在最近验证 checkpoint 中的 git HEAD
- 未在 standard-fields 中覆盖的领域字段（`mainline_status`、`activity_summary`、`governance_signals`、`known_risks`、`pending_decisions`、`verification_summary`、`observed_at` 等）使用 snake_case 英文名，与 standard-fields 风格一致
- 新增字段前必须先检查 standard-fields 是否有等价字段；若确实需要新增，提交 PR 更新 standard-fields 后再引入本 artifact

## Writeback Policy

可写入 Snapshot: 经 worktrack 验证的 repo 状态变化（branch、checkpoint、merge 记录）、经 gate 接受的 evidence 摘要、经 Refresh 算子确认的 mainline_status 和 working_tree_status。

不可写入 Snapshot: 未验证的市场判断、未经过 gate 的 speculative 分析结论、与 Goal Charter 冲突但未走 ChangeGoal 的状态声明。

## Machine Check

Snapshot/Status 的 contract 正确性由 contract check 验证（检查 required sections 与 keyed fields 是否存在），检查脚本路径与 repo-analysis 对齐:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/repo_snapshot_contract_check.py
```

该检查只验证 markdown 结构和关键字段存在性，不替代 `repo-refresh-skill` 的实际观测与写入逻辑，也不把运行时 `.aw/` 产物提升为 canonical source。
