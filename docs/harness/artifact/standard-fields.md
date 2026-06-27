---
title: "Standard Fields Vocabulary"
status: active
updated: "2026-06-27"
owner: "servo-kernel"
last_verified: 2026-06-27
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
| `verdict` | `pass \| soft_fail \| hard_fail \| blocked` | Gate 裁决结果 | `worktrack-gate-skill` |
| `verdict_confidence` | `high \| medium \| low` | 裁决置信度 | `worktrack-gate-skill` |
| `allowed_next_routes` | `string[]` | 允许的下一路由列表 | All |
| `recommended_next_route` | `string` | 建议的下一路由（Skill 名称） | All |
| `recommended_next_scope` | `RepoScope \| WorktrackScope` | 建议的下一 Scope | All |
| `recommended_next_function` | `string` | 建议的下一 Function 算子 | All |
| `continuation_ready` | `boolean` | 是否可继续推进 | All |
| `continuation_blockers` | `string[]` | 继续阻塞项列表 | All |
| `continuation_decision` | `string` | 继续决策说明 | `harness-skill` |

## Milestone Gate 目标类型与轴适用性字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `target_type` | `program_code \| non_program_artifact \| mixed \| unknown` | Milestone Gate 目标类型。决定 blackbox / whitebox / anti-cheat / composite 轴的取证方法 | `milestone-gate`, milestone axis skills |
| `target_type_source` | `programmer_declared \| milestone_artifact \| gate_input \| inferred_from_worktracks \| unknown` | target_type 来源；推断来源必须可追踪 | `milestone-gate`, milestone axis skills |
| `target_type_confidence` | `high \| medium \| low` | target_type 判定置信度 | `milestone-gate`, milestone axis skills |
| `target_type_rules` | `object` | Milestone Gate 目标类型、来源、置信度、轴适用性、替代验收要求和 mixed slice 覆盖的封套；聚合器必须先解析它再聚合 verdict | `milestone-gate` |
| `axis` | `black_box \| white_box \| anti_cheat \| composite` | Milestone Gate 轴标识 | Milestone axis skills |
| `axis_verdict` | `pass \| soft_fail \| hard_fail \| blocked \| not_applicable` | 单轴 verdict。`not_applicable` 只能表示轴不适用，不等于 pass | Milestone axis skills |
| `axis_applicability` | `object` | 四轴适用性封套，按 axis 记录 state、expected_method、substituted_by 与 reason | `milestone-gate` |
| `axis_applicability_resolved` | `boolean` | 四轴适用性是否已解析完成；为 `false` 时 Milestone Gate 最终 verdict 必须阻断 | `milestone-gate` |
| `axis_applicability_state` | `applicable \| not_applicable \| substituted \| blocked` | 单轴适用性状态；这是路由事实，不是成功 verdict | Milestone axis skills |
| `axis_applicability_reason` | `string` | 单轴适用或不适用理由 | Milestone axis skills |
| `applicability_state` | `applicable \| not_applicable \| substituted \| blocked` | `composite_lane_verdicts` 和 `slice_coverage` 内的 lane-local 适用性状态字段；语义等同 `axis_applicability_state`，不代表 pass | `milestone-gate` |
| `expected_method` | `string` | 该轴对当前 target_type 应使用的验收方法，如 `external_behavior_scenario` 或 `structural_internal_analysis` | Milestone axis skills |
| `axis_satisfaction` | `object` | 聚合器输出的轴满足度封套，按 axis 记录 applicability_state、axis_satisfied、reason 和 evidence refs | `milestone-gate` |
| `axis_satisfied` | `boolean` | 轴满足度谓词结果；`applicable` 轴要求 raw verdict pass，`substituted` 轴要求合格替代证据，`not_applicable` 本身为 false | `milestone-gate` |
| `substituted_by` | `string \| N/A` | 当 `axis_applicability_state = substituted` 时，记录替代验收来源 | Milestone axis skills |
| `substitution_evidence_ref` | `string \| N/A` | 替代验收证据引用；缺失时 substituted 不能视为 satisfied | `milestone-gate`, milestone axis skills |
| `substitute_method` | `artifact_acceptance_review \| policy_conformance \| reader_operator_simulation \| cross_reference_validation \| traceability_review \| professional_review \| research_evidence_review \| artifact_structure_review \| string` | 非程序 artifact 替代验收方法；必须贴合 artifact 类型和 axis 语义 | `milestone-gate`, milestone axis skills |
| `substitute_verdict` | `pass \| soft_fail \| hard_fail \| blocked \| not_applicable` | 替代验收自身的 verdict；只有 `pass` 且 evidence 完整时，`substituted` 才可视为 satisfied | `milestone-gate`, milestone axis skills |
| `substitution_evidence_present` | `boolean` | 替代证据是否存在且非占位；为 `false` 时不得把 `substituted` 视为通过 | `milestone-gate`, milestone axis skills |
| `substitution_evidence_summary` | `string` | 替代验收检查内容、覆盖范围、缺口和残留风险摘要 | `milestone-gate`, milestone axis skills |
| `evidence_covers_completion_signal` | `boolean` | 替代证据是否覆盖对应 completion signal 或 acceptance criterion | `milestone-gate`, milestone axis skills |
| `slice_id` | `string` | mixed target 的切片标识；切片可对应 worktrack、completion signal、artifact component 或交付路径 | `milestone-gate`, milestone axis skills |
| `slice_target_type` | `program_code \| non_program_artifact \| unknown` | mixed target 中单个切片的目标类型 | `milestone-gate`, milestone axis skills |
| `slice_coverage` | `object[]` | mixed target 的逐切片覆盖记录，至少包含 slice_id、slice_target_type、axis、applicability_state、expected_method、substitute_method、evidence_ref 和 verdict | `milestone-gate` |
| `veto_triggered` | `boolean` | Milestone Gate lane 是否触发 veto-power 阻断 | `milestone-gate` |
| `weight_modifier_applied` | `boolean` | Milestone Gate lane finding 是否已对对应 WT 权重应用修饰 | `milestone-gate` |

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
| `evidence_dimensions` | `object` | 正交证据维度封套 | `worktrack-review-evidence-skill`, `worktrack-test-evidence-skill`, `worktrack-rule-check-skill` |
| `decisive_evidence` | `string[]` | 决定性证据列表 | `worktrack-gate-skill` |
| `missing_evidence` | `string[]` | 缺失证据列表 | All Verify skills |
| `residual_risk` | `string[]` | 残留风险列表 | All |
| `upstream_constraint_signal` | `boolean` | 是否存在上游约束信号 | `worktrack-gate-skill`, `worktrack-review-evidence-skill` |

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
| `node_type` | `feature \| refactor \| research \| bugfix \| docs \| config \| test` | 节点类型 | `worktrack-init-skill` |
| `baseline_branch` | `string` | 基线分支 | `worktrack-init-skill`, `worktrack-close-skill` |
| `baseline_form` | `string` | 基线形式 | `worktrack-init-skill` |
| `merge_required` | `boolean` | 是否需要合并 | `worktrack-init-skill`, `worktrack-close-skill` |
| `branch_source_ref` | `string` | Worktrack branch 创建来源 ref | `worktrack-init-skill`, `worktrack-close-skill` |
| `worktrack_branch` | `string` | Worktrack 执行分支 | `worktrack-init-skill`, `worktrack-status-skill`, `worktrack-close-skill` |
| `integration_target_ref` | `string` | Worktrack closeout 的集成目标 ref | `worktrack-init-skill`, `worktrack-close-skill`, `repo-refresh-skill` |
| `closeout_target_ref` | `string` | closeout PR/merge/checkpoint 目标 ref | `worktrack-close-skill`, `repo-refresh-skill` |
| `final_baseline_branch` | `string` | Milestone final acceptance 后的最终基线分支 | `worktrack-init-skill`, `worktrack-close-skill` |
| `checkpoint_base_ref` | `string` | Worktrack closeout checkpoint 对比基准 ref | `worktrack-init-skill`, `worktrack-close-skill`, `repo-refresh-skill` |
| `gate_criteria` | `string` | 关卡标准 | `worktrack-init-skill`, `worktrack-schedule-skill` |
| `if_interrupted_strategy` | `string` | 中断处理策略 | `worktrack-init-skill`, `worktrack-recover-skill` |

## Repo Snapshot 专有字段

| 标准字段名 | 类型 | 说明 | 适用 Skill |
|-----------|------|------|-----------|
| `source_baselines` | `object` | 已验证 source root 的 checkpoint 摘要，按 source root key 分组 | `repo-refresh-skill`, `repo-status-skill` |
| `source_root` | `string` | source root 的 repo-relative 路径 | `repo-refresh-skill`, `worktrack-doc-catch-up-skill` |
| `docs_owner` | `string` | 对应 docs/catalog owner 路径 | `repo-refresh-skill`, `worktrack-doc-catch-up-skill` |
| `git_head` | `string` | 对应 source root 最近 verified checkpoint 的 git HEAD | `repo-refresh-skill`, `worktrack-doc-catch-up-skill` |
| `source_change_kind` | `string` | source baseline 变化类型，如 `source-change` / `source-index-change` / `docs-source-traceability-change` | `repo-refresh-skill`, `worktrack-doc-catch-up-skill` |

## 字段使用约定

1. **优先使用英文标准名**：所有结构化输出字段使用上表定义的英文名
2. **中文仅用于展示**：中文标签仅用于面向程序员的报告展示层
3. **新增字段**：如需新增字段，先检查本表是否有等价字段；若确实需要，提交 PR 更新本文档
4. **废弃字段**：不得在输出中包含已废弃的字段别名
