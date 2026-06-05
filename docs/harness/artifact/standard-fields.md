---
title: "Standard Fields Vocabulary"
status: active
updated: "2026-06-05"
owner: "servo-kernel"
last_verified: "2026-06-05"
---

# Standard Fields Vocabulary

所有 Skill 的结构化输出必须使用以下标准字段名。本词汇表是 Harness 下游消费的统一接口约定。

---

## Scope & Function 字段

| 标准字段名 | 类型 | 说明 | 适用 Scope |
|-----------|------|------|-----------|
| `current_scope` | `RepoScope \| WorktrackScope` | 控制范围 | All |
| `current_function` | `Observe \| Decide \| Init \| Dispatch \| Verify \| Judge \| Recover \| Close \| ChangeGoal \| SetGoal` | 控制算子 | All |
| `repo_scope` | `RepoScope` | Repo 级 scope 标记 | RepoScope Skills |
| `worktrack_scope` | `active \| initializing \| observing \| scheduling \| dispatching \| verifying \| judging \| recovering \| closing \| none` | Worktrack 级 scope 标记 | WorktrackScope Skills |

## 判定 & 路由字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `verdict` | `pass \| soft_fail \| hard_fail \| blocked` | Gate 裁决结果 | `gate-skill` |
| `verdict_confidence` | `high \| medium \| low` | 裁决置信度 | `gate-skill` |
| `allowed_next_routes` | `string[]` | 允许的下一路由列表 | All |
| `recommended_next_route` | `string` | 建议的下一路由（Skill 名称） | All |
| `recommended_next_scope` | `RepoScope \| WorktrackScope` | 建议的下一 Scope | All |
| `recommended_next_function` | `string` | 建议的下一 Function 算子 | All |
| `continuation_ready` | `boolean` | 是否可继续推进 | All |
| `continuation_blockers` | `string[]` | 继续阻塞项列表 | All |
| `continuation_decision` | `string` | 继续决策说明 | `harness-skill` |

## 审批 & 权限字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `approval_required` | `boolean` | 是否需要程序员审批 | All |
| `approval_scope` | `string` | 审批范围说明 | All |
| `approval_reason` | `string` | 审批理由 | All |
| `needs_approval` | `boolean` | 有待审批项 | `harness-skill` |

## 证据 & 风险字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `evidence_dimensions` | `object` | 正交证据维度封套 | `review-evidence-skill`, `test-evidence-skill`, `rule-check-skill` |
| `decisive_evidence` | `string[]` | 决定性证据列表 | `gate-skill` |
| `missing_evidence` | `string[]` | 缺失证据列表 | All Verify skills |
| `residual_risk` | `string[]` | 残留风险列表 | All |
| `upstream_constraint_signal` | `boolean` | 是否存在上游约束信号 | `gate-skill`, `review-evidence-skill` |

## 控制回路元数据

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `artifacts_read` | `string[]` | 本轮已读取的 artifact 路径列表 | `harness-skill` |
| `stop_conditions_hit` | `string[]` | 命中的停止条件列表 | `harness-skill` |
| `config_hydration_gaps` | `string[]` | 配置 hydration 缺口 | `harness-skill` |
| `handoff_state` | `string` | 交接状态 | `harness-skill` |
| `handoff_lock_active` | `boolean` | 交接锁是否激活 | `harness-skill` |

## Worktrack 专有字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `worktrack_id` | `string` | Worktrack 标识符 | WorktrackScope Skills |
| `node_type` | `feature \| refactor \| research \| bugfix \| docs \| config \| test` | 节点类型 | `init-worktrack-skill` |
| `baseline_branch` | `string` | 基线分支 | `init-worktrack-skill`, `close-worktrack-skill` |
| `baseline_form` | `string` | 基线形式 | `init-worktrack-skill` |
| `merge_required` | `boolean` | 是否需要合并 | `init-worktrack-skill`, `close-worktrack-skill` |
| `branch_source_ref` | `string` | Worktrack branch 创建来源 ref | `init-worktrack-skill`, `close-worktrack-skill` |
| `worktrack_branch` | `string` | Worktrack 执行分支 | `init-worktrack-skill`, `worktrack-status-skill`, `close-worktrack-skill` |
| `integration_target_ref` | `string` | Worktrack closeout 的集成目标 ref | `init-worktrack-skill`, `close-worktrack-skill`, `repo-refresh-skill` |
| `closeout_target_ref` | `string` | closeout PR/merge/checkpoint 目标 ref | `close-worktrack-skill`, `repo-refresh-skill` |
| `final_baseline_branch` | `string` | Milestone final acceptance 后的最终基线分支 | `init-worktrack-skill`, `close-worktrack-skill` |
| `checkpoint_base_ref` | `string` | Worktrack closeout checkpoint 对比基准 ref | `init-worktrack-skill`, `close-worktrack-skill`, `repo-refresh-skill` |
| `gate_criteria` | `string` | 关卡标准 | `init-worktrack-skill`, `schedule-worktrack-skill` |
| `if_interrupted_strategy` | `string` | 中断处理策略 | `init-worktrack-skill`, `recover-worktrack-skill` |

## Repo Snapshot 专有字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `source_baselines` | `object` | 已验证 source root 的 checkpoint 摘要，按 source root key 分组 | `repo-refresh-skill`, `repo-status-skill` |
| `source_root` | `string` | source root 的 repo-relative 路径 | `repo-refresh-skill`, `doc-catch-up-worker-skill` |
| `docs_owner` | `string` | 对应 docs/catalog owner 路径 | `repo-refresh-skill`, `doc-catch-up-worker-skill` |
| `git_head` | `string` | 对应 source root 最近 verified checkpoint 的 git HEAD | `repo-refresh-skill`, `doc-catch-up-worker-skill` |
| `source_change_kind` | `string` | source baseline 变化类型，如 `source-change` / `source-index-change` / `docs-source-traceability-change` | `repo-refresh-skill`, `doc-catch-up-worker-skill` |

## 字段使用约定

1. **优先使用英文标准名**：所有结构化输出字段使用上表定义的英文名
2. **中文仅用于展示**：中文标签仅用于面向程序员的报告展示层
3. **新增字段**：如需新增字段，先检查本表是否有等价字段；若确实需要，提交 PR 更新本文档
4. **废弃字段**：不得在输出中包含已废弃的字段别名
