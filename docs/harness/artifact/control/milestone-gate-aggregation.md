---
title: "Milestone Gate 证据聚合合同"
status: active
updated: 2026-06-27
owner: servo-kernel
last_verified: 2026-06-27
---
# Milestone Gate 证据聚合合同

> 定义从 N 个 worktrack gate evidence 到 milestone-level verdict 的 per-milestone 可配置聚合规则。本 artifact 是 WT2（aggregator implementation）的输入合同。

## 一、概述

### 目的

Milestone Gate 不是"全部 WT 都过了 = milestone 过了"的简单布尔 AND。不同 milestone 对证据的要求不同——release milestone 要求所有 critical WT 无矛盾，docs milestone 允许部分 soft-fail，demo milestone 可以接受 limited evidence。

本 artifact 定义 per-milestone 可配置的 `aggregation_rules`，覆盖五个维度：

1. **证据权重**（weight_rules）：哪些 WT 的结论对 milestone verdict 贡献更大
2. **矛盾处理**（contradiction_rules）：两个 critical WT 结论矛盾时的 resolution protocol
3. **目标类型路由**（target_type_rules）：program/code 与 non-program 目标的轴适用性和替代验收规则
4. **Composite lane 消费**（composite_lane_rules）：composite acceptance lanes 在 milestone 级的角色
5. **退化路径**（degenerate_and_rules）：无矛盾等简化场景的显式退化记录

### 与 MS-20260623-002 的接口

本 artifact 消费 MS-20260623-002 定义的 [single-acceptance verdict](../worktrack/single-acceptance-contract.md) 格式。每个已闭环 worktrack 的 `verdict`（pass / soft-fail / hard-fail / blocked）、`critical_failure` 标记和 `completion_signals_trace` 是 aggregation_rules 的输入。

## 二、aggregation_rules schema

### 整体结构

```yaml
aggregation_rules:
  enabled: true | false           # false 时使用退化 AND（§六）
  weight_rules: { ... }
  contradiction_rules: { ... }
  target_type_rules: { ... }
  composite_lane_rules: { ... }
  degenerate_and_rules: { ... }
```

`enabled = false` 时，所有规则跳过，使用退化 AND 判定。默认值为 `true`（推荐所有 milestone 显式声明规则）。

### 字段约束

| 字段 | 类型 | 必需 | 默认值 |
|------|------|------|--------|
| `enabled` | boolean | 否 | `true` |
| `weight_rules` | object | 是（enabled=true 时） | — |
| `contradiction_rules` | object | 是（enabled=true 时） | — |
| `target_type_rules` | object | 否（新 milestone 推荐显式声明） | `target_type: unknown`，不得默认通过 |
| `composite_lane_rules` | object | 是（enabled=true 时） | — |
| `degenerate_and_rules` | object | 否 | 见 §六 |

## 三、weight_rules：证据权重

### 目的

不同 node_type 的 worktrack 对 milestone 的证据贡献不同。一个 `feature` WT 的实现质量比 `docs` WT 的文档更新对 milestone 的"能不能发布"影响更大。

### Schema

```yaml
weight_rules:
  node_type_weights:
    feature: 4       # 功能实现，影响核心正确性
    release: 4       # 发布/部署，影响交付完整性
    critical: 5      # 显式标记为 critical 的 WT
    config: 3        # 配置变更，影响系统行为
    test: 3          # 测试变更，增强验证信心
    docs: 2          # 文档变更，影响理解但不影响功能
    demo: 1          # 演示/探索，影响最小
  default_weight: 2  # 未声明 node_type 的默认权重
  overrides:         # per-worktrack 覆盖（可选）
    - worktrack_id: "WT-xxx"
      weight: 5
      reason: "provides integration test coverage"
```

### 权重取值

| 值 | 语义 |
|----|------|
| 5 | critical — 不可有任何 hard-fail，fail 则 milestone blocked |
| 4 | high — 重大影响，fail 需 explicit programmer review |
| 3 | medium — 常规影响，参与加权聚合 |
| 2 | low — 参考性，soft-fail 不阻断 milestone |
| 1 | minimal — 可忽略，仅 record-by-default |

### 权重在 verdict 生成中的角色

- critical WT（weight ≥ 4）：hard-fail → milestone blocked。soft-fail → 标记 risk。
- medium WT（weight = 3）：hard-fail → 标记 risk，由 programmer 判定
- low/minimal WT（weight ≤ 2）：hard-fail → record only，不自动阻断 milestone
- 聚合 verdict 的 pass 条件：所有 weight ≥ 3 的 WT 均为 pass（或 soft-fail 且已标记 residual risk）

### overrides 的使用

`overrides` 允许在 milestone gate 裁定阶段提升/降级特定 WT 的权重。典型场景：

- 一个 `docs` WT 实际上写了关键 access control 文档 → 提升到 4
- 一个 `feature` WT 被证明是原型代码，不影响生产 → 降级到 2

**约束**：overrides 必须在 milestone gate 证据中显式记录理由。无理由的 override 视为无效。

## 四、contradiction_rules：矛盾检测与处理

### 目的

当两个（或多个）worktrack 的结论互相矛盾时——例如 WT-A 的 test evidence 说"功能正常"，WT-B 的 review evidence 说"架构不可接受"——aggregation 不能简单地取多数或取平均。

### Scheme

```yaml
contradiction_rules:
  detection:
    scope: critical_only | all          # 矛盾检测范围
    trigger_condition:
      - weight_both_are_at_least: 3     # 双方权重≥此值才触发
      - verdict_types:                  # 什么结论组合算矛盾
          - ["pass", "hard-fail"]
          - ["pass", "blocked"]
          - ["hard-fail", "pass"]
          - ["hard-fail", "pass"]        # 来自不同维度的矛盾
  resolution:
    default_action: block               # 矛盾时默认行为
    block_message_template: |
      "Contradiction detected between [{wt_a_id}] ({verdict_a}) and [{wt_b_id}] ({verdict_b}).
       Recommended: open a verification WT to resolve, or programmer fact-check."
    resolution_paths:
      - path_id: new_verification_worktrack
        description: "创建新 verification WT，用其结论替换冲突 evidence"
        wt_creation_template:
          title: "Contradiction Resolution: {wt_a_title} vs {wt_b_title}"
          purpose: "验证 {contradiction_summary}"
          node_type: test
          expected_evidence: [review-evidence, test-evidence, rule-check]
        block_lift_condition: "new verification WT passes gate"
      - path_id: programmer_resolution
        description: "Programmer 人工事实核查后解除 block"
        required_recording:
          - programmer_decision: "retain_wt_a | retain_wt_b | invalidate_both"
          - reasoning: "factual basis for resolution"
          - override_verdict: "pass | soft-fail | hard-fail"
        block_lift_condition: "programmer explicitly records resolution"
  partial_contradiction:
    # 部分矛盾：1 critical fail + 3 normal pass
    handling: record_as_risk
    risk_label: "partial_contradiction"
    risk_description: "One critical WT [{wt_id}] has hard-fail while {pass_count} other WTs pass. Manual review recommended."
```

### contradiction 判定范围

- `critical_only`（推荐默认）：仅当矛盾双方权重 ≥ 3 时触发。低权重 WT 之间的矛盾仅记录，不 block。
- `all`：所有 verdict_type 矛盾（pass vs hard-fail）均触发 block。保守但手操负担重。

### resolution path 选择

Contradiction block 不能在 aggregation 内部自动解除。合法解除路径：

1. **新 verification WT**：创建专用 WT，重新验证矛盾点。新 WT 的 evidence 替代冲突 evidence。聚合重新运行。
2. **Programmer 手动解除**：programmer 进行事实核查，明确记录决策和理由。

### block_lift

聚合算子在 block 后不应自动重试。Block lift 只在以下条件之一满足时发生：

- 新 verification WT 通过 gate（closeout record 写入）
- Programmer 在 milestone gate evidence 中显式记录 resolution

## 五、target_type_rules：目标类型与轴适用性

### 目的

Milestone Gate 必须先识别当前 milestone 的目标类型，再选择黑盒、白盒、反作弊和复合验收轴的取证方法。程序/代码目标需要真实软件工程验收；非程序目标不能被强行套入运行时测试语义。

### Schema

```yaml
target_type_rules:
  target_type: program_code | non_program_artifact | mixed | unknown
  target_type_source: programmer_declared | milestone_artifact | gate_input | inferred_from_worktracks | unknown
  target_type_confidence: high | medium | low
  axis_applicability:
    black_box:
      state: applicable | not_applicable | substituted | blocked
      expected_method: external_behavior_scenario | artifact_acceptance_review | operator_simulation | N/A
      substituted_by: composite | professional_review | policy_check | N/A
      reason: string
    white_box:
      state: applicable | not_applicable | substituted | blocked
      expected_method: structural_internal_analysis | artifact_structure_review | policy_structure_review | N/A
      substituted_by: composite | professional_review | policy_check | N/A
      reason: string
    anti_cheat:
      state: applicable | not_applicable | substituted | blocked
      expected_method: evidence_integrity_review | N/A
      substituted_by: N/A
      reason: string
    composite:
      state: applicable | not_applicable | substituted | blocked
      expected_method: composite_acceptance_lanes | professional_review | N/A
      substituted_by: N/A
      reason: string
  substitution_evidence_required: true
  substitution_evidence_contract:
    substitute_method: artifact_acceptance_review | policy_conformance | reader_operator_simulation | cross_reference_validation | traceability_review | professional_review | research_evidence_review | artifact_structure_review
    substitution_evidence_ref: string | N/A
    substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable
    evidence_covers_completion_signal: true | false
  slice_coverage:                 # required when target_type = mixed
    - slice_id: string
      slice_target_type: program_code | non_program_artifact | unknown
      axis: black_box | white_box | anti_cheat | composite
      applicability_state: applicable | not_applicable | substituted | blocked
      expected_method: string
      substitute_method: string | N/A
      evidence_ref: string | N/A
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
```

### Target routing matrix

| target_type | black_box | white_box | anti_cheat | composite |
|-------------|-----------|-----------|------------|-----------|
| `program_code` | `applicable`; use externally observable behavior scenarios, user-visible workflows, CLI/API responses, integration behavior, or regression scenarios. Must not read full implementation code. | `applicable`; use structural/internal evidence such as control flow, data flow, state transfer, interface contracts, dependency paths, and architecture alignment. May read implementation code. | `applicable`; verify evidence provenance, dispatch/profile integrity, and bypass risk. | `applicable`; consume code-review, feature-completeness, related-influence, intent-completeness, operator-simulation, and professional-review lanes. |
| `non_program_artifact` | Usually `substituted` or `not_applicable`; use artifact acceptance review, reader/operator simulation, policy conformance, cross-reference validation, or professional review. Do not force runtime scenario tests when no program exists. | Usually `substituted` or `not_applicable`; use artifact structure review, rule consistency, traceability, terminology/interface consistency, or governance conformance. Do not pretend this is code-internal white-box testing. | `applicable`; evidence integrity still matters for docs, skill text, workflow policy, and research artifacts. | `applicable`; composite lanes are often the primary non-program acceptance surface. |
| `mixed` | Split by worktrack, completion signal, or artifact component. Program/code slices use behavior scenarios; non-program slices use substitute acceptance. | Split by worktrack, completion signal, or artifact component. Program/code slices use structural/internal analysis; non-program slices use artifact structure review. | `applicable` across all slices. | `applicable`; must record slice-level coverage. |
| `unknown` | `blocked` unless the gate can produce a justified type inference. | `blocked` unless the gate can produce a justified type inference. | `blocked` if evidence boundary is unclear. | `blocked` or `substituted` only with explicit programmer or gate evidence. |

### Applicability state is not verdict

`axis_applicability.state` is a routing fact, not a pass/fail verdict:

- `applicable` means the axis must run and produce its normal verdict.
- `not_applicable` means the axis does not apply to this target type; aggregation must record it separately and must not coerce it to `pass`.
- `substituted` means the axis's usual software-testing method is replaced by an artifact-appropriate method; aggregation may treat the axis as satisfied only when the substitute evidence is present and accepted.
- `blocked` means the milestone gate cannot legally complete until target type, evidence, or substitute method is clarified.

### Substitute acceptance evidence contract

For non-program artifact slices, `substituted` is valid only when the substitute method matches the artifact and the evidence is concrete enough for a later reviewer to replay the judgment. The allowed substitute methods are:

| substitute_method | Primary use | Required evidence |
|-------------------|-------------|-------------------|
| `artifact_acceptance_review` | docs, skill text, workflow policy, planning artifacts | purpose / completion signal / acceptance criterion mapping with explicit pass, gap, or blocked status |
| `policy_conformance` | governance rules, run protocols, adapter or deploy policy text | checked rule refs, applicable must/must-not clauses, outcome, and exceptions |
| `reader_operator_simulation` | user-facing or operator-facing instructions and interactive prompts | reader/operator path walked, expected action, observed ambiguity, failure point, and outcome |
| `cross_reference_validation` | artifact with links, paths, field names, or upstream/downstream refs | reference target, existence/semantic check result, stale or missing refs |
| `traceability_review` | completion signals, criteria, evidence linkage | per-signal or per-criterion evidence refs and uncovered items |
| `professional_review` | research, policy, UX/interaction, or domain-specific judgment | reviewer perspective, judgment basis, verdict, and residual risk |
| `research_evidence_review` | research claims and option analysis | source quality, claim boundary, counterevidence/limitations, and supported conclusion |
| `artifact_structure_review` | schemas, field contracts, structured docs, skill output contracts | required sections/fields, internal consistency, terminology/interface consistency, and downstream fit |

Minimal fields for every substituted axis:

- `substitute_method`: one of the artifact-appropriate methods above.
- `substitution_evidence_ref`: stable reference to evidence, a changed file section, command output, or reviewer record.
- `substitute_verdict`: `pass`, `soft_fail`, `hard_fail`, `blocked`, or `not_applicable`.
- `evidence_covers_completion_signal`: boolean, or an equivalent per-signal trace.
- `substitution_evidence_summary`: short statement of what was checked and what remains uncovered.

`substitute_verdict = pass` is required before aggregation may treat a substituted axis as satisfied. `soft_fail`, `hard_fail`, `blocked`, missing evidence, placeholder evidence, or evidence that does not cover the relevant completion signal must keep the axis unsatisfied or blocked according to milestone policy.

### Mixed target slice coverage

When `target_type = mixed`, aggregation must evaluate slices before producing a milestone-level verdict. A slice can be a worktrack, completion signal, artifact component, or delivery path. Each slice records `slice_id`, `slice_target_type`, `axis`, `applicability_state`, `expected_method`, `substitute_method`, `evidence_ref`, and verdict.

Program/code slices keep normal software validation semantics: black-box behavior scenarios and white-box structural/internal analysis. Non-program slices use substitute acceptance. Anti-cheat and composite remain applicable across slices unless their evidence boundary is explicitly blocked. A pass on one slice type cannot cover missing evidence on another slice type.

### Final verdict interaction

Milestone Gate final verdict must evaluate each axis through an `axis_satisfied` predicate instead of raw verdict equality:

```text
axis_satisfied(axis) =
  axis.applicability.state == applicable
    AND axis.verdict == pass
  OR axis.applicability.state == substituted
    AND axis.substitute_method is artifact_appropriate
    AND axis.substitution_evidence_ref != N/A
    AND axis.substitute_verdict == pass
    AND axis.substitution_evidence_present == true
    AND axis.evidence_covers_completion_signal == true
```

`not_applicable` can remove an axis from mandatory pass calculation only when the target type and reason are explicit. It does not create positive evidence and must remain visible in `composite_lane_verdicts`.

## 六、composite_lane_rules：Composite lane 消费

### 目的

Composite acceptance lanes（black-box / white-box / anti-cheat / composite）在 worktrack 级产出 per-WT lane 结论。在 milestone 级，这些 lane 需要被聚合后与 per-WT aggregation verdict 共同构成 milestone gate 的完整判定。

### 方案分析

| 方案 | 描述 | 可追溯性 | 复杂度 | 退化风险 |
|------|------|---------|--------|---------|
| A. 独立四轴 | 各 lane 作为独立 axis，与 per-WT aggregation verdict 取交集 | ★★★★★ | 低 | 低 |
| B. 虚拟 WT | 各 lane 结论视为特殊 WT 输入 aggregation_rules | ★★★☆☆ | 中 | 中 |
| C. 权重修饰 | Lane findings 下调对应 WT 的权重 | ★★☆☆☆ | 高 | 高 |

### 推荐方案：A（独立四轴） + 有限 B 降级

```yaml
composite_lane_rules:
  consumption_mode: independent_axes_with_weight_modifier
  lane_axes:
    black_box:
      aggregate: "lane-level verdict = AND of all WT black-box lane findings"
      veto_power: true   # black-box fail → milestone blocked，无论 per-WT aggregation 结果
    white_box:
      aggregate: "lane-level verdict = AND of all WT white-box lane findings"
      veto_power: true
    anti_cheat:
      aggregate: "lane-level verdict = AND of all WT anti-cheat signals; any high-severity finding → lane fail"
      veto_power: true   # cheating signal → milestone blocked
    composite:
      aggregate: "lane-level verdict = AND of all WT composite lane findings"
      veto_power: false  # composite lane 是总体判断，不单独 block
  weight_modifier:
    # 有限 B 降级：lane finding 可调整特定 WT 的权重，但不替代四轴判定
    enabled: true
    rules:
      - lane: anti_cheat
        finding: high_severity
        target_wt_weight: 0        # cheating signal 将对应 WT 的权重清零
      - lane: black_box
        finding: high_severity
        target_wt_weight: 0        # black-box 严重缺陷将对应 WT 权重清零
  final_verdict:
    pass_condition: |
      per_WT_aggregation_verdict == pass
      AND axis_satisfied(black_box)
      AND axis_satisfied(white_box)
      AND axis_satisfied(anti_cheat)
      AND composite_verdict != hard_fail
```

### 推荐理由

- **四轴独立**：各 lane 的结论清晰可追溯，不会被 per-WT 权重"稀释"
- **Veto power**：black-box 测试失败就是失败，不应被其他 WT 的 pass 覆盖
- **有限 B 降级**：anti-cheat finding 可以将特定 WT 的权重清零，防止 cheating WT 的 pass 拉高聚合分数

### 与 WT3（三轴→四轴映射）的交接

WT3 将 worktrack 的 implementation-validation-policy 三轴映射到 milestone 的 black-box-white-box-anti-cheat-composite 四轴。本 artifact 定义的 `lane_axes` 的 aggregate 逻辑是 WT3 映射的消费方。

## 七、degenerate_and_rules：退化 AND 判定

### 触发条件

以下条件**全部**满足时，允许使用退化 AND：

```yaml
degenerate_and_rules:
  trigger_conditions:
    all_satisfied:
      - no_contradiction_detected: true       # 无任何矛盾
      - no_anti_cheat_high_severity: true      # 无反作弊高严重信号
      - all_lanes_consistent: true             # 所有 lane 一致（无 lane 级矛盾）
      - axis_applicability_resolved: true      # 所有轴均有 applicable / substituted / not_applicable / blocked 之一，且无 blocked
      - no_weight_override_applied: true        # 无手动权重覆盖
      - all_critical_wt_pass: true             # 所有 weight ≥ 4 的 WT 均 pass
  recording_required: true
  recording_fields:
    - degenerate_reason: "No contradiction detected across {n} worktracks; all critical WTs pass; all lanes consistent."
    - degenerate_verified_at: timestamp
    - degenerate_verified_by: "aggregator"
    - skipped_rules: [contradiction, composite_lane_weight_modifier]
```

### 退化与正常 AND 的区别

- **正常 AND**（enabled=false）：跳过所有规则，任何 WT 的 hard-fail 即 milestone failed。不记录退化理由。
- **退化 AND**（enabled=true 但触发退化条件）：规则正常配置，但因当前 evidence 状态简单而无矛盾。必须显式记录退化理由——说明"不是跳过了规则，而是规则运行时没有发现需要干预的情况"。

### 退化理由的可追溯性

退化 AND 不是静止跳过：如果将来任何退化条件不再满足（如新 WT 引入了矛盾），退化解锁，正常规则重新激活。退化理由记录确保 audit trail 可解释"为什么这次 milestone gate 看起来是简单 AND"。

## 八、与 WT2（evidence-aggregator）的交接

### aggregator 的输入

```yaml
aggregator_input:
  per_worktrack:
    - worktrack_id: "WT-xxx"
      single_acceptance_verdict: { ... }  # from single-acceptance-contract.md
      gate_evidence: { ... }              # implementation/validation/policy gate verdicts
      closeout_record: { ... }
      composite_lane_findings:            # per-WT composite lane findings
        black_box: pass | soft_fail | hard_fail
        white_box: pass | soft_fail | hard_fail
        anti_cheat: pass | high_severity
        composite: pass | soft_fail | hard_fail
  aggregation_rules: { ... }              # per-milestone 配置，来自本 artifact
  target_type_rules: { ... }              # target_type 与 axis_applicability
```

### aggregator 的输出

```yaml
aggregator_output:
  milestone_gate_verdict: pass | soft_fail | hard_fail | blocked
  per_worktrack_weights: { ... }          # 每个 WT 的最终权重（含 overrides）
  contradiction_findings: [...]           # 已检测到的矛盾
  contradiction_resolution_status:         # 若有矛盾
    blocked: true | false
    resolution_path: new_verification_worktrack | programmer_resolution | none
  composite_lane_verdicts:                 # 四轴聚合结论
    black_box:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | blocked
      substituted_by: string | N/A
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
    white_box:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | blocked
      substituted_by: string | N/A
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
    anti_cheat:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | blocked
      substituted_by: string | N/A
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
    composite:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | blocked
      substituted_by: string | N/A
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
  slice_coverage:                         # required for target_type = mixed
    - slice_id: string
      slice_target_type: program_code | non_program_artifact | unknown
      axis: black_box | white_box | anti_cheat | composite
      applicability_state: applicable | not_applicable | substituted | blocked
      expected_method: string
      substitute_method: string | N/A
      evidence_ref: string | N/A
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
  degenerate_and_applied: true | false
  degenerate_and_reason: string | N/A
  aggregation_summary: string
```

### WT2 实现时需注意

- `per_worktrack_weights` 的计算顺序：先解析 target_type_rules 与 axis_applicability，再取 node_type_weights 默认值，再应用 overrides，再应用 composite_lane weight_modifier
- contradiction detection 在 weight 应用之后执行——先确定哪些 WT 是 critical，再检测 critical 之间的矛盾
- block lift 不可自动：aggregator 检测到之前在同一 milestone 下的 contradiction resolution（新 verification WT 的 closeout），自动重算但保留 block 直到 resolution 的 evidence 满足 block_lift_condition

## 九、示例：Release Milestone 的 aggregation_rules

```yaml
aggregation_rules:
  enabled: true
  weight_rules:
    node_type_weights:
      feature: 4
      release: 5
      test: 3
      docs: 2
    default_weight: 2
  contradiction_rules:
    detection:
      scope: critical_only
      trigger_condition:
        weight_both_are_at_least: 3
    resolution:
      default_action: block
      resolution_paths:
        - path_id: new_verification_worktrack
        - path_id: programmer_resolution
    partial_contradiction:
      handling: record_as_risk
  target_type_rules:
    target_type: program_code
    target_type_source: milestone_artifact
    target_type_confidence: high
    axis_applicability:
      black_box: { state: applicable, expected_method: external_behavior_scenario }
      white_box: { state: applicable, expected_method: structural_internal_analysis }
      anti_cheat: { state: applicable, expected_method: evidence_integrity_review }
      composite: { state: applicable, expected_method: composite_acceptance_lanes }
  composite_lane_rules:
    consumption_mode: independent_axes_with_weight_modifier
    lane_axes:
      black_box: { veto_power: true }
      white_box: { veto_power: true }
      anti_cheat: { veto_power: true }
      composite: { veto_power: false }
    weight_modifier:
      enabled: true
  degenerate_and_rules:
    recording_required: true
```

## 十、示例：Docs Milestone 的 aggregation_rules

```yaml
aggregation_rules:
  enabled: true
  weight_rules:
    node_type_weights:
      docs: 3
      config: 2
    default_weight: 1
  contradiction_rules:
    detection:
      scope: all                          # docs milestone 也检测所有矛盾
      trigger_condition:
        weight_both_are_at_least: 2       # 但阈值更低（docs WT 默认 weight=3）
    resolution:
      default_action: block
  target_type_rules:
    target_type: non_program_artifact
    target_type_source: milestone_artifact
    target_type_confidence: high
    axis_applicability:
      black_box:
        state: substituted
        expected_method: artifact_acceptance_review
        substituted_by: operator_simulation
      white_box:
        state: substituted
        expected_method: artifact_structure_review
        substituted_by: professional_review
      anti_cheat:
        state: applicable
        expected_method: evidence_integrity_review
      composite:
        state: applicable
        expected_method: composite_acceptance_lanes
  composite_lane_rules:
    consumption_mode: independent_axes_with_weight_modifier
    lane_axes:
      black_box: { veto_power: false }    # docs milestone 不强依赖 black-box
      white_box: { veto_power: true }
      anti_cheat: { veto_power: false }
      composite: { veto_power: false }
    weight_modifier:
      enabled: false                      # docs milestone 不需要权重修饰
  degenerate_and_rules:
    recording_required: true
```

注意 release vs docs milestone 的区别：

- release 的 black-box 和 anti-cheat 有 veto power
- docs 的 white-box（review quality）有 veto power，但 black-box 没有
- 这体现了"不同 milestone 对证据的要求不同"

## 十一、约束与保证

### 不变式

- **Contradiction block 不可自动解除**：aggregator 不能因为"后来的 WT 都过了"就静默消解之前的矛盾
- **Weight 不超过 node_type 的语义边界**：docs WT 的 weight 不能超过 feature WT（overrides 除外，需显式理由）
- **Veto power 不可被 per-WT aggregation 覆盖**：black-box fail 即 milestone blocked，无论其他 WT 如何
- **Target type 先于轴 verdict**：未解析 target_type 或 axis_applicability 时，不得把黑盒/白盒轴默认为 pass
- **not_applicable 不是 pass**：`not_applicable` 只能移出 mandatory pass 计算，不能提供正向完成证据
- **substituted 必须有证据**：`substituted` 只有在替代验收证据存在并通过时才可视为 axis satisfied
- **退化 AND 必须记录**：即使当前 evidence 状态简单到不需要聚合规则，也必须说明"为什么简单"而不是"跳过了规则"

### 向后兼容

- 已完成的 milestone（completed/superseded）不需要补充 aggregation_rules
- 活跃 milestone 如果尚未声明 aggregation_rules，默认使用 `enabled: false`（退化 AND），但必须在 milestone gate evidence 中标记 `aggregation_rules_missing: true` 作为 warning
- 旧 milestone 缺少 `target_type_rules` 时，Milestone Gate 必须在 evidence 中记录 `target_type: unknown` 或一个有来源的 runtime inference；不得把缺失解释为 program_code、non_program_artifact 或 pass
- 此行为确保 MS-20260623-003 合入后不影响正在执行的 other milestones

## 十二、相关文档

- [Single-Acceptance Contract](../worktrack/single-acceptance-contract.md) — 被消费的 verdict 格式
- [Worktrack Contract](../worktrack/contract.md) — worktrack 级 gate 定义
- [Milestone Artifact Control](../control/milestone.md) — milestone gate 的上级定义
- [harness-skill §8](../../../../product/harness/skills/harness-skill/SKILL.md) — 三轴 Gate 模型
