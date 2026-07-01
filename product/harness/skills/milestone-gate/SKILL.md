---
name: milestone-gate
description: 当 worktrack_list_finished 后，且顶层 Harness 已为 Milestone Gate 产出 blackbox/whitebox/anticheat/composite sibling axis reports 时使用这个技能。它是 Milestone Gate Aggregator：消费显式 axis_reports、axis_dispatch_profile、closed worktrack facts、target_type_rules 与 aggregation_rules，聚合产出 milestone_gate_verdict；不得创建或唤起轴 SubAgent。
---

# Milestone Gate 技能

## 概览

本技能实现 Milestone Gate 的 **聚合层**，是 goal-driven milestone 的 RepoScope 集成验收层，位于"全部 worktrack 关闭"之后、"`purpose_achieved` 判定"之前。

在两层 Milestone Gate 模型中，**Layer 1** 由顶层 Harness 执行 sibling axis dispatch，产出 blackbox / whitebox / anticheat / composite 四份隔离报告；**Layer 2** 由本技能执行 aggregation，只消费显式 `axis_reports` 和 `axis_dispatch_profile`，不得补跑或继续分派轴检查。

它是 **Gate Aggregator**：不自己做轴检查，也不继续分派 SubAgent；顶层 Harness 必须先把 `milestone-blackbox-check`、`milestone-whitebox-check`、`milestone-anticheat-check`、`milestone-composite-check` 作为 sibling axis carriers 执行，并把四个显式 `axis_reports` 与 `axis_dispatch_profile` 交给本技能。本技能只验证输入完整性、解析适用性、运行聚合规则，并产出 `milestone_gate_verdict`。

调用关系：

```
milestone-status-skill（sensor）
  └─ worktrack_list_finished → 顶层 Harness sibling axis dispatch
       ├─ milestone-blackbox-check  → blackbox axis_report
       ├─ milestone-whitebox-check  → whitebox axis_report
       ├─ milestone-anticheat-check → anticheat axis_report
       └─ milestone-composite-check → composite axis_report
            ↓
       milestone-gate（本技能）aggregator → milestone_gate_verdict
```

聚合规则合同（已详述于本技能 §聚合器）。本技能不替代各 worktrack 自己的 gate，也不把上层集成失败回写成单个 worktrack gate 的通过。

## 何时使用

当满足以下条件时使用这个技能：

- 当前 milestone 下所有 worktrack 已闭环（`worktrack_list_finished == true`），由 milestone-status-skill 确认
- 顶层 Harness 已经产出四个 axis reports：blackbox / whitebox / anticheat / composite
- 需要聚合 closed worktrack facts、axis reports、axis dispatch profile、target type rules 与 aggregation rules，产出 `milestone_gate_verdict`
- 需要判断 missing report、not applicable axis、substituted axis、blocked axis、same-carrier contamination、manual exception 事实对 Gate verdict 的影响

以下情况不适用：

- worktrack 未全部闭环 → 应返回 `not_ready`
- 尚未产出 axis reports → 返回 `blocked`，要求顶层 Harness 先完成 sibling axis dispatch
- 需要单个 WT 的 gate 判定 → 使用 `worktrack-gate-skill`
- 需要进度计数 / handback 信号 → 使用 `milestone-status-skill`
- 需要修改代码 / evidence → 禁止（只读）

## 工作流

1. **接收输入**：从 milestone-status-skill 接收：
   - `milestone_id`
   - `closed_worktrack_list`：已闭环 WT 列表，每项含 `{ id, node_type, verdict, critical_failure, closeout_record_ref, closeout_evidence_bundle_ref, closeout_bundle_status, runtime_dispatch_record_ref, subagent_dispatch_record_refs, dispatch_provenance_status, dispatch_result_status, resolved_runtime_dispatch_status, composite_lane_records }`
   - `aggregation_rules`：milestone artifact 的 `aggregation_rules` 字段（缺失时退化 AND）
   - `target_type_rules`：目标类型、目标场景与轴适用性规则
   - `axis_reports`：顶层 Harness 提供的 blackbox / whitebox / anticheat / composite 报告
   - `axis_dispatch_profile`：顶层 Harness 对四轴 carrier 的分派与隔离记录
   - `manual_exception`：仅可表示 programmer final acceptance override 的输入事实，不能改写 Gate pass
2. **验证就绪**：确认 `closed_worktrack_list`、`axis_reports`、`axis_dispatch_profile` 非空且结构完整。若缺失或污染，返回 `blocked`。每个 closed worktrack 必须携带 `closeout_evidence_bundle_ref`、`closeout_bundle_status`、`runtime_dispatch_record_ref`、`subagent_dispatch_record_refs`、`dispatch_provenance_status`、`dispatch_result_status`、`resolved_runtime_dispatch_status` 和 `composite_lane_records`；`missing`、`incomplete`、`contaminated` 或未解释的 `historical_gap` 都必须作为 non-pass evidence 暴露给 axes 和聚合输出，不得从 closeout prose summary 补造 bundle、dispatch records 或 composite lane records。若只收到 `runtime_dispatch_record_ref` 而缺少 dispatch status，必须 dereference parent record；无法 dereference 时标记 `dispatch_provenance_status: incomplete` 或 `missing`，并设置对应 `resolved_runtime_dispatch_status`。若只收到 lane prose、旧式 lane paragraph 或旧式 scalar lane ref，必须标记对应 lane 为 `incomplete` 或 `historical_gap`，除非可 dereference 为完整 `worktrack-composite-lane-record/v1`。
3. **Axis report input validation**（见下文）
4. **聚合器**（见下文）
5. **产出最终 verdict**：`milestone_gate_verdict` + 聚合状态字段
6. **停止**：不得进入 purpose_achieved 判定或代码修改

---

## Axis Reports 输入合同

顶层 Harness 负责将 milestone 级集成验收分解为 4 个**隔离轴检查**。本技能只消费结果，不创建新的 axis carrier。

### 轴定义

| 轴 | Skill | 视角 | 检查范围 |
|----|-------|------|---------|
| **blackbox** | `milestone-blackbox-check` | 外部用户视角 | 跨 WT 集成一致性、用户承诺兑现、回归风险、路径约定合规、完整性缺口（B1-B5）。**不阅读实现代码。** |
| **whitebox** | `milestone-whitebox-check` | 内部实现视角 | 接口契约一致性、状态流转完整性、依赖图、架构分层合规、关键集成路径实现质量（W1-W5）。**阅读完整实现代码。** |
| **anticheat** | `milestone-anticheat-check` | 证据可信度视角 | Mock abuse、evidence 复用、局部验证、gate bypass、过期 evidence、self-review bias、false positive risk（A1-A7）。**不评判代码正确性，只评判证据可信度。** |
| **composite** | `milestone-composite-check` | 复合验收视角 | 消费 per-WT lane 报告（code-review 等 C1-C6）并聚合成 milestone 级复合验收结论。**不生成新代码检查。** |

### 必需输入字段

`axis_reports` 必须包含四个键：`blackbox`、`whitebox`、`anticheat`、`composite`。每个轴报告至少包含：

```yaml
axis_report:
  axis: blackbox | whitebox | anticheat | composite
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  checklist_results: [...]
  carrier: subagent | current-carrier
  isolation_guarantee: true | false
  carrier_isolation_broken: true | false
  report_ref: ".servo/milestone/...#axis"
  observed_git_hash: "<hash>"
  target_type: program_code | non_program_artifact | mixed | unknown
  target_scenario: runnable_workflow | config_environment | experiment_execution | workflow_policy | documentation_or_skill_contract | research_or_plan_artifact | mixed_delivery | unknown
  target_scenario_source: string
  target_scenario_confidence: high | medium | low
  axis_applicability_state: applicable | not_applicable | substituted | split | blocked
  expected_method: string
  axis_applicability_reason: string
  runtime_dispatch_profile: { ... }
  missing_evidence: [...]
  input_gap_classification: { ... }   # blackbox required; optional N/A for other axes
  substitute_method: string | N/A
  substitution_evidence_ref: string | N/A
  substitute_verdict: pass | soft_fail | hard_fail | blocked | N/A
  evidence_covers_completion_signal: true | false | N/A
  slice_coverage: array | N/A
  unknown_target_inference: object | N/A
```

各轴的完整 checklist（B1-B5、W1-W5、A1-A7、C1-C6）和 verdict 推导规则定义在各自 SKILL.md 中。

`axis_dispatch_profile` 至少包含：

- `dispatch_owner`: `top_level_harness`
- `dispatch_model`: `sibling_delegated` / `mixed` / `current_carrier_fallback` / `missing`
- `required_axes`: blackbox / whitebox / anticheat / composite
- `completed_axes`
- `missing_axes`
- `delegation_attempted_by_axis`: object
- `same_carrier_cross_axis`: boolean
- `carrier_isolation_broken_any`: boolean
- `dispatch_gap_reason`: string | N/A
- `per_axis_runtime_dispatch_profile`: object
- `nested_axis_dispatch_attempted`: false

每个 `runtime_dispatch_profile` 若声称 `attempted_carrier: SubAgent`、`carrier_decision: delegated_subagent` 或等价 spawned SubAgent，必须同时携带 `parent_runtime_dispatch_record_ref`、`spawned_subagent_record_ref`、`carrier_instance_id` 和 `isolation_boundary`。缺少这些 linkage 的 SubAgent claim 必须被视为 ambiguous spawned-axis claim；若实际执行载体是 current-carrier，除非存在明确 `boundary_violation_recorded: true` 或等价运行时边界缺口记录，否则不得把它聚合为真实 sibling SubAgent 隔离。

Blackbox 轴的 `input_gap_classification` 必须区分输入缺口与真实行为失败，至少包含 `input_gap_status`、`missing_target_type`、`missing_aggregation_rules`、`missing_completion_signals_trace`、`missing_scenario_inputs`、`behavior_failure_present` 和 `classification_reason`。缺少 target_type、aggregation_rules、completion_signals_trace 或 scenario inputs 时，应标记 `input_gap` / non-pass，而不是报告为行为场景执行失败或 pass。

### Axis Report Status

本技能必须先产出 `axis_report_status`：

- `complete`: 四个报告齐全、结构完整、report refs 可追踪、且隔离记录未显示污染。
- `missing`: 任一 required axis report 缺失。
- `contaminated`: 任一 report 的输入含其他轴 verdict / 检查结果，或 `same_carrier_cross_axis == true` 且没有合法隔离证据。
- `isolation_broken`: `carrier_isolation_broken_any == true` 或任一轴 `isolation_guarantee == false`。
- `blocked_axis`: 任一 mandatory axis report verdict 为 `blocked`。

`missing`、`contaminated`、`isolation_broken`、`blocked_axis` 都是 non-pass Gate facts。它们不能被聚合器改写为 `pass`；若 programmer 后续选择手动接受，只能记录为 final acceptance `manual_exception`，并保留原始 `milestone_gate_verdict`。

---

## 可配置聚合器（Aggregator）

本层在验证 axis reports 后执行。聚合器消费五类输入：

1. **per-WT closeout evidence bundles**：每个已闭环 WT 的 `closeout_evidence_bundle_ref`、`closeout_bundle_status`、`runtime_dispatch_record_ref`、`subagent_dispatch_record_refs`、`dispatch_provenance_status`、`dispatch_result_status`、`resolved_runtime_dispatch_status`、`composite_lane_records`、`verdict`、`node_type`、`critical_failure`
2. **axis_reports**：顶层 Harness sibling axis carriers 产出的 4 个结构化报告
3. **target_type_rules / axis_applicability**：来自 milestone artifact、轴输出或已验证 docs/harness 合同的目标类型与四轴适用性封套
4. **aggregation_rules**：来自 milestone artifact 的 `aggregation_rules` 字段。若缺失，默认使用 `enabled: false`（退化 AND），标记 `aggregation_rules_missing: true`
5. **axis_dispatch_profile / axis_report_status**：顶层 Harness 分派与隔离证据

聚合分五步执行，顺序不可颠倒。Step 0 必须先完成；后续步骤不得把 `not_applicable` 或 `substituted` 当成原始 `pass` 使用。

### Step 0：target_type_rules / axis_applicability resolution（目标类型与轴适用性解析）

先解析 milestone 的 `target_type_rules`、`target_scenario`、每个轴报告中的 `target_type` / `target_scenario` / `axis_applicability_state`，以及非程序替代验收字段：

- `target_type` 允许表达 `program_code`、`non_program_artifact`、`mixed` 或 `unknown`。
- `target_scenario` 是 `target_type` 下的场景细分，允许表达 `runnable_workflow`、`config_environment`、`experiment_execution`、`workflow_policy`、`documentation_or_skill_contract`、`research_or_plan_artifact`、`mixed_delivery` 或 `unknown`；它不得扩展顶层 target type，也不得降低证据要求。
- 轴报告内的 `axis_applicability_state` 至少区分 `applicable`、`not_applicable`、`substituted`、`split`、`blocked`；`axis_applicability` 仅保留给 milestone/target_type_rules 的四轴封套使用。
- `not_applicable` 必须带有 `target_type` 与明确原因；它只能把该轴从 mandatory pass 计算中移除，不能产生正向 evidence、不能覆盖 completion signal、不能等价为 `pass`。
- `substituted` 必须带有 `substitute_method`、`substitution_evidence_ref`、`substitute_verdict`、`evidence_covers_completion_signal`。只有 `substitute_verdict: pass` 且 `evidence_covers_completion_signal: true` 时，替代轴才可被判为 satisfied。
- `split` 或 `mixed` 目标必须提供 `slice_coverage`，每个 slice 记录 `slice_target_type`、`slice_target_scenario`、适用轴、使用方法、证据引用和 verdict。程序/代码 slice 的 pass 不能覆盖非程序 slice 的替代证据缺失；非程序 substitute pass 也不能覆盖程序/代码 slice 的 blackbox/whitebox 缺失。
- 目标类型未知、目标场景未知且无高置信可追溯推断、适用性字段互相矛盾、替代证据缺失、`slice_coverage` 缺失或无法映射 completion signal 时，设置 `axis_applicability_resolved: false`，最终 verdict 必须为 `blocked`。
- 未知目标场景的可追溯推断必须记录 `inferred_target_type`、`inferred_target_scenario`、`confidence`、`evidence_refs`、`uncertainty` 和 `recommended_axis_profile`。`medium`、`low` 或 contradictory confidence 不能产出 pass。

默认场景 profile：

| target_scenario | blackbox | whitebox | anticheat | composite |
|-----------------|----------|----------|-----------|-----------|
| `runnable_workflow` | `applicable` external behavior scenario | `applicable` structural/internal analysis | `applicable` evidence integrity review | `applicable` composite lanes |
| `config_environment` | runtime config 为 `applicable`；policy-only config 为 `substituted` | runtime config load/propagation 为 `applicable`；config contract 为 `substituted` | `applicable` | `applicable` |
| `experiment_execution` | executable experiment 为 `applicable`；report/conclusion 为 `substituted` | experiment code 为 `applicable`；research structure 为 `substituted` | `applicable` | `applicable` |
| `workflow_policy` | usually `substituted` reader/operator simulation or policy conformance | usually `substituted` policy/artifact structure review | `applicable` | `applicable` |
| `documentation_or_skill_contract` | usually `substituted` artifact acceptance / reader simulation | usually `substituted` artifact structure / traceability review | `applicable` | `applicable` |
| `research_or_plan_artifact` | usually `substituted` research evidence / professional review | usually `substituted` claim/assumption/evidence structure review | `applicable` | `applicable` |
| `mixed_delivery` | `split` by slice | `split` by slice | `applicable` across slices | `applicable` with slice-level lane coverage |
| `unknown` | `blocked` without high-confidence inference | `blocked` without high-confidence inference | `blocked` if evidence boundary unclear | `blocked` or questions_required |

替代边界：blackbox substitution 不能覆盖已有程序 slice 的外部行为场景；whitebox substitution 不能用外部行为结果冒充内部结构证据；anticheat 不替代 blackbox/whitebox，只评证据可信度；composite 不后验合成缺失的 axis evidence。

Mixed / unknown 处理：

- `target_type: mixed` 或任一轴 `axis_applicability_state: split` 时，必须输出 `slice_coverage`。每个 slice 至少包含 `slice_id`、`slice_target_type`、`slice_target_scenario`、`axis`、`applicability_state`、`expected_method`、`evidence_ref` 和 verdict。
- 程序 slice 缺少 blackbox/whitebox 证据时，该轴保持 unsatisfied；不能用非程序替代证据补位。
- 非程序 slice 缺少 substitute evidence 时，该 slice 保持 unsatisfied；不能用程序测试 pass 补位。
- `unknown_target_inference` 必须在目标类型或目标场景缺失/矛盾时输出，字段至少包含 `inferred_target_type`、`inferred_target_scenario`、`confidence`、`evidence_refs`、`uncertainty`、`contradictory_evidence_refs`、`recommended_axis_profile` 和 `questions_required`。
- `confidence: medium | low`、未解决矛盾、空 evidence refs 或 inferred unknown 都必须设置 `axis_applicability_resolved: false`，最终 verdict 为 `blocked` 或显式 non-pass。

聚合器必须产出 `axis_satisfaction`，并用以下谓词代替原始 `verdict == pass`：

```text
axis_satisfied(axis) =
  applicable:
    axis.verdict == pass
  substituted:
    substitute_method is present
    and substitution_evidence_ref is present
    and substitute_verdict == pass
    and evidence_covers_completion_signal == true
  not_applicable:
    false, but axis may be excluded from mandatory pass only when target_type and reason are explicit
  blocked or missing:
    false
```

`axis_satisfied(axis)` 是轴满足度，不是轴 verdict 改写；原始轴 verdict、applicability state、替代方法和证据引用必须保留在输出中。

### Step 1：weight_rules（证据权重计算）

从每个 WT 的 `node_type` 映射到基础权重，叠加 overrides：

| node_type | weight | 语义 |
|-----------|--------|------|
| critical | 5 | 不可有任何 hard-fail |
| feature | 4 | 重大影响 |
| release | 4 | 发布/部署 |
| config | 3 | 配置变更 |
| test | 3 | 测试变更 |
| docs | 2 | 文档变更 |
| demo | 1 | 演示/探索 |
| 未声明 | 2 | default_weight |

- `overrides`：按 worktrack_id 匹配，替换 final_weight，需附带 reason
- 产出：`per_worktrack_weights`，每项含 `{ worktrack_id, node_type, base_weight, final_weight, overridden, override_reason }`

### Step 2：contradiction_rules（矛盾检测与处理）

检测两个 critical WT 的 verdict 是否矛盾。触发条件：双方 `final_weight >= weight_both_are_at_least`（默认 3）且 verdict 组合命中 trigger_condition。

- 矛盾输出：`contradiction_finding { wt_a_id, verdict_a, wt_b_id, verdict_b, severity, recommended_resolution }`
- 矛盾未解决 → `contradiction_blocked: true` → milestone blocked
- 解除路径：`new_verification_worktrack`（新验证 WT）或 `programmer_resolution`（人工决策）
- 部分矛盾（1 critical fail + N normal pass）：记录 `partial_contradiction` risk，不 block

### Step 3：composite_lane_rules（四轴 verdict 聚合）

消费模式：`independent_axes_with_weight_modifier`

- **Applicability first**：先读取 Step 0 的 `axis_satisfaction`，不得直接用 raw verdict 判定轴通过。
- **Veto power**：blackbox / whitebox / anticheat 的 veto_power=true（默认）。当适用轴 hard_fail / blocked，或替代轴缺少合格 substitute evidence 导致 `axis_satisfied == false` 时，milestone 直接 blocked。
- **not_applicable**：若目标类型证明该轴不适用，记录 `applicability_state: not_applicable` 和 reason；该轴不触发 veto，也不得贡献 pass 或 positive evidence。
- **composite 轴**：veto_power=false，fail 记录 risk 不自动 block
- per-milestone 可配置各轴 veto_power
- **Weight modifier**：anticheat 或 blackbox 发现 high severity → 涉及 WT 的 final_weight=0

产出：`composite_lane_verdicts { blackbox, whitebox, anticheat, composite }`。每个轴至少包含 `{ verdict, severity, veto_power, applicability_state, axis_satisfied, veto_triggered, weight_modifier_applied, substitute_method, substitution_evidence_ref, substitute_verdict, evidence_covers_completion_signal }`。

### Step 4：degenerate_and_rules（退化 AND 判定）

全部满足时触发：

- `axis_applicability_resolved == true`
- `no_contradiction_detected == true`
- `no_anticheat_high_severity == true`
- `all_lanes_consistent == true`
- `no_weight_override_applied == true`
- `all_critical_wt_pass == true`（所有 final_weight ≥ 4 的 WT pass）
- 所有 mandatory applicable / substituted veto-power axes 满足 `axis_satisfied(axis) == true`

触发后：`degenerate_and_applied: true` + 退化理由，判定=简单 AND

### 最终裁决（milestone_gate_verdict）

| 优先级 | 条件 | verdict |
|--------|------|---------|
| -1 | `axis_report_status` 为 `missing` / `contaminated` / `isolation_broken` / `blocked_axis`，或 `nested_axis_dispatch_attempted == true` | `blocked` |
| 0 | target type unknown、target scenario unknown 且无高置信可追溯推断、`axis_applicability_resolved == false`、替代证据缺失、mixed 缺少 `slice_coverage`、或 `aggregation_rules_missing` 导致无法解释轴适用性 | `blocked` |
| 1 | veto-power 轴适用且 hard_fail/blocked，或 mandatory substituted 轴 `axis_satisfied == false` | `blocked` |
| 2 | contradiction_blocked | `blocked` |
| 3a | 所有 weight ≥ 3 的 WT pass，且所有 mandatory applicable / substituted axes 满足 `axis_satisfied(axis) == true`，显式 `not_applicable` 轴均有 target_type reason | `pass` |
| 3b | 任一 weight ≥ 3 的 WT hard-fail，无 critical fail | `soft-fail` |
| 3c | 任一 weight ≥ 4 的 WT hard-fail | `hard-fail` |
| 4 | 退化 AND，且 Step 0 适用性解析完成 | `pass`（标记 degenerate_and_applied） |

可能值：`pass / soft-fail / hard-fail / blocked`

`verdict != "pass"` 时阻断 milestone closeout。

---

## 预期输出

使用本技能时，产出一份至少包含以下字段的结构化输出：

- `milestone_gate_verdict`：pass / soft-fail / hard-fail / blocked — 最终判定
- `milestone_gate_summary`：聚合摘要
- `milestone_gate_execution_model`：`axis_report_aggregation`
- `nested_axis_dispatch_attempted`：false
- `axis_reports`：object — blackbox / whitebox / anticheat / composite 原始报告引用与压缩摘要
- `axis_report_status`：complete / missing / contaminated / isolation_broken / blocked_axis
- `axis_dispatch_profile`：object — dispatch_owner、dispatch_model、required_axes、completed_axes、missing_axes、delegation_attempted_by_axis、same_carrier_cross_axis、carrier_isolation_broken_any、dispatch_gap_reason、per_axis_runtime_dispatch_profile、nested_axis_dispatch_attempted
- `aggregation_rules_applied`：boolean
- `aggregation_rules_missing`：boolean
- `aggregation_rules_source`：string
- `target_type`：program_code / non_program_artifact / mixed / unknown
- `target_type_source`：string
- `target_scenario`：runnable_workflow / config_environment / experiment_execution / workflow_policy / documentation_or_skill_contract / research_or_plan_artifact / mixed_delivery / unknown
- `target_scenario_source`：string
- `target_scenario_confidence`：high / medium / low
- `operator_situation`：string | N/A
- `axis_applicability_resolved`：boolean
- `axis_satisfaction`：object — 每轴包含 `applicability_state`、`axis_satisfied`、reason 和 evidence refs
- `slice_coverage`：array | N/A — mixed target 时必须列出每个 slice 的 target type、适用轴、方法、证据和 verdict
- `unknown_target_inference`：object | N/A — target type 或 scenario 缺失/矛盾时必须列出推断、置信度、证据、未决问题和 recommended axis profile
- `substitution_evidence_summary`：object — 每个 substituted 轴的 substitute method、evidence ref、substitute verdict 和 completion-signal coverage
- `per_worktrack_weights`：array — `{ worktrack_id, node_type, base_weight, final_weight, overridden, override_reason }`
- `closeout_bundle_status_by_worktrack`：object — 每个 WT 的 `closeout_evidence_bundle_ref` 与 `complete / incomplete / contaminated / historical_gap / missing` 状态
- `dispatch_provenance_by_worktrack`：object — 每个 WT 的 `runtime_dispatch_record_ref`、`subagent_dispatch_record_refs`、`dispatch_provenance_status`（`captured / linked / incomplete / missing / historical_gap / contaminated`）、raw `dispatch_result_status` 与 `resolved_runtime_dispatch_status`
- `composite_lane_records_by_worktrack`：object — 每个 WT 的六条 composite lane record refs/statuses，至少包含 `code-review`、`feature-completeness`、`related-influence`、`intent-completeness`、`operator-simulation`、`professional-review` 的 `record_ref`、`status`、`producer_ref`、`validation_ref`、缺失字段、污染原因和不适用原因
- `missing_composite_lane_records`：array — lane record 缺失或不可追溯的 `{ worktrack_id, lane_id }`
- `historical_gap_composite_lane_records`：array — 明确标记 historical_gap 且未被合成 evidence 的 `{ worktrack_id, lane_id }`
- `contaminated_composite_lane_records`：array — 标记 contaminated 且保留污染原因的 `{ worktrack_id, lane_id, reason }`
- `missing_closeout_bundle_refs`：array — 缺少 bundle ref 或 bundle 不可追溯的 WT
- `historical_gap_worktracks`：array — 明确标记 historical_gap 且未被合成 evidence 的 WT
- `contradiction_findings`：array — `{ wt_a_id, verdict_a, wt_b_id, verdict_b, severity, recommended_resolution }`
- `contradiction_blocked`：boolean
- `composite_lane_verdicts`：object — `{ blackbox, whitebox, anticheat, composite }`，每轴含 `{ verdict, severity, veto_power, applicability_state, axis_satisfied, veto_triggered, weight_modifier_applied, substitute_method, substitution_evidence_ref, substitute_verdict, evidence_covers_completion_signal }`
- `degenerate_and_applied`：boolean
- `degenerate_and_reason`：string | N/A
- `carrier_isolation_broken`：boolean
- `same_carrier_cross_axis`：boolean
- `isolation_note`：string
- `manual_exception`：object | N/A — 只记录 programmer final acceptance override 的输入事实；不得把 Gate verdict 改写为 pass
- `accepted_gate_verdict_preserved_as`：string | N/A
- `anti_cheat_findings_preserved`：boolean | N/A — manual exception 后是否完整保留 anticheat 原始 finding、severity、affected evidence refs 与 affected scope
- `manual_exception_followup_ref`：string | N/A — manual exception 产生的后续 milestone/worktrack/evidence 引用；无 follow-up 时必须显式 N/A

## 硬约束

本技能特有约束：

1. **只读**：不修改任何代码、evidence、artifact。只产出结构化 verdict。
2. **不得替代 worktrack gate**：Milestone Gate 位于所有 worktrack closeout 之后，不替代单个 WT 的 gate。
3. **不得创建轴 carrier**：本技能不得调用、模拟调用或继续唤起 blackbox / whitebox / anticheat / composite axis skills。`nested_axis_dispatch_attempted` 必须为 false；若本技能尝试创建轴 carrier，最终 verdict 必须为 `blocked`。
4. **轴间隔离只消费证据**：轴间隔离由顶层 Harness 的 `axis_dispatch_profile` 和各 axis reports 证明；本技能只能验证和聚合这些证据。
5. **聚合顺序不可颠倒**：target_type / axis_applicability_state → weight → contradiction → composite_lane → degenerate 顺序必须执行，不可跳过。
6. **缺失输入必须暴露**：axis_reports、axis_dispatch_profile 或 aggregation_rules 缺失时必须标记对应缺口；axis report 缺失或隔离缺口不可静默假设。
6c. **Axis input package clean-room lint 必须保真**：若上游传入的 axis input package 或 axis report summary 显示读取了 prior control-state axis labels、broad backlog reads、prior milestone Gate reports 或 sibling axis reports，该轴必须标记为 `contaminated` 或对应 `input_gap` / non-pass。聚合器不得把污染输入产出的 report 视为 clean-room axis evidence。
6a. **Closeout bundle / dispatch records 不得后验合成**：closed worktrack 缺少 `closeout_evidence_bundle_ref`、bundle 字段不完整、缺少 `runtime_dispatch_record_ref`，或只存在 prose summary 时，必须记录为 `missing` / `incomplete` / `historical_gap`。当 parent runtime record 的 `dispatch_result_status` 表示 `delegated` 时，缺少 `subagent_dispatch_record_refs` 也是缺失证据；当 parent record 明确表示 `current_carrier_fallback`、`permission_blocked`、`runtime_gap`、`dispatch_package_unsafe`、`blocked` 或 `historical_gap` 时，空 child refs 必须保留为该状态而不是合成缺失 delegated execution。Milestone Gate 必须 preserve 或 dereference 出 `dispatch_result_status`，并在输出中传播 `resolved_runtime_dispatch_status`；可以聚合这些缺口，但不能把缺口改写为 pass evidence，也不能凭 prose synthesis 声称真实 delegated SubAgent execution。
6b. **Composite lane records 不得后验合成**：closed worktrack 缺少 `composite_lane_records`、某条 lane 缺少 `record_ref`、lane status 为 `missing` / `incomplete` / `historical_gap` / `contaminated`，或只存在 prose composite summary 时，必须保留原状态并在输出中列出 affected `{ worktrack_id, lane_id }`。`not_applicable` 必须保留 reason 且不得贡献 positive evidence。Milestone Gate 可以聚合 composite axis verdict，但不能把 closeout prose、milestone summary、旧式 lane paragraph 或 operator narrative 改写为 lane record、lane finding、absorbed issue refs、residual risks 或 validation refs。
7. **不得进入后续阶段**：产出 verdict 后停止。purpose_achieved 判定和 writeback 由 milestone-status-skill 负责。
8. **阻断必须显式**：veto / contradiction / critical fail 导致的 block 必须记录具体原因和可追溯证据。
9. **轴适用性先于轴裁决**：未解析 `target_type_rules` / axis report 的 `axis_applicability_state` 时，不得把 raw axis verdict 聚合成 pass。
10. **not_applicable 不是 pass**：`not_applicable` 只能在 target type 和 reason 明确时移出 mandatory pass 计算，不能贡献 positive evidence、completion-signal coverage 或 weight bonus。
11. **substituted 必须有证据**：`substituted` 轴缺少 `substitute_method`、`substitution_evidence_ref`、`substitute_verdict: pass` 或 `evidence_covers_completion_signal: true` 时，`axis_satisfied(axis)` 必须为 false；若该轴 mandatory/veto-power，则 milestone verdict 为 `blocked`。
12. **mixed 目标必须逐 slice 覆盖**：`target_type: mixed` 缺少 `slice_coverage` 或任一 slice 缺少对应适用轴证据时，不能用其他 slice 的 pass 补位，最终 verdict 必须为 `blocked` 或显式非 pass。
13. **same-carrier fallback 不是隔离 pass**：`same_carrier_cross_axis == true`、`carrier_isolation_broken_any == true` 或 `dispatch_model: current_carrier_fallback` 只能作为 blocked/non-pass Gate evidence，不能被声明为 true isolation pass。
14. **manual exception 不改写 Gate verdict**：manual exception 只属于 programmer final acceptance override。若 Gate verdict 因隔离或报告缺口 blocked，输出必须保留 blocked，并通过 `manual_exception` / `accepted_gate_verdict_preserved_as` / `anti_cheat_findings_preserved` / `manual_exception_followup_ref` 记录后续人工接受事实与保留证据。

## 资源

- milestone-gate-aggregation.md — aggregation_rules 合同
- milestone-status-skill — 调用方 sensor skill
- milestone-blackbox-check — 轴技能 1
- milestone-whitebox-check — 轴技能 2
- milestone-anticheat-check — 轴技能 3
- milestone-composite-check — 轴技能 4
- single-acceptance-contract.md — WT verdict 格式
- Skill 公共约束已内联于 §硬约束
