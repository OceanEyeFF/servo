---
title: "Milestone Gate 证据聚合合同"
status: active
updated: 2026-06-28
owner: servo-kernel
last_verified: 2026-06-28
---
# Milestone Gate 证据聚合合同

> 定义从 N 个 worktrack gate evidence 与四个显式 axis reports 到 milestone-level verdict 的 per-milestone 可配置聚合规则。本 artifact 是 `milestone-gate` Layer 2 aggregator 的输入/输出合同。

## 一、概述

### 目的

Milestone Gate 不是"全部 WT 都过了 = milestone 过了"的简单布尔 AND。不同 milestone 对证据的要求不同——release milestone 要求所有 critical WT 无矛盾，docs milestone 允许部分 soft-fail，demo milestone 可以接受 limited evidence。

Milestone Gate 分为两个职责面：

- **Axis dispatch**：由顶层 Harness 在 `worktrack_list_finished == true` 后执行。Harness 准备四份 sibling input package，并把 `milestone-blackbox-check`、`milestone-whitebox-check`、`milestone-anticheat-check` 和 `milestone-composite-check` 作为同级 axis carrier 分派。四个 axis carrier 互相不可见。
- **Aggregation**：由 `milestone-gate` skill 执行。它只消费显式 `axis_reports`、closed worktrack verdicts、`target_type_rules` 与 `aggregation_rules`，不得在内部继续分派 SubAgent 或补跑 axis checks。

这个扁平化编排避免依赖"SubAgent 内部继续唤起 SubAgent"的运行时能力。若顶层 Harness 不能真实分派 sibling axis carrier，必须把运行时缺口写入 axis dispatch evidence；`milestone-gate` 只能据此产出 `blocked` / non-pass verdict，不能把 same-carrier 四轴执行声明为真实 pass。

本 artifact 定义 per-milestone 可配置的 `aggregation_rules`，覆盖五个维度：

1. **证据权重**（weight_rules）：哪些 WT 的结论对 milestone verdict 贡献更大
2. **矛盾处理**（contradiction_rules）：两个 critical WT 结论矛盾时的 resolution protocol
3. **目标类型路由**（target_type_rules）：program/code 与 non-program 目标的轴适用性和替代验收规则
4. **Composite lane 消费**（composite_lane_rules）：composite acceptance lanes 在 milestone 级的角色
5. **轴报告输入**（axis_reports）：四个 sibling axis carrier 的显式报告、隔离与运行时证据
6. **退化路径**（degenerate_and_rules）：无矛盾等简化场景的显式退化记录

### 与 Worktrack single-acceptance 的接口

本 artifact 消费 [single-acceptance verdict](../worktrack/single-acceptance-contract.md) 与 [closeout evidence bundle](../worktrack/closeout-evidence-bundle.md) 格式。每个已闭环 worktrack 的 `verdict`（pass / soft-fail / hard-fail / blocked）、`critical_failure` 标记、`completion_signals_trace`、`closeout_evidence_bundle_ref` 和 `closeout_bundle_status` 是 aggregation_rules 的输入。

### 与四轴报告的接口

四轴报告不是 `milestone-gate` 内部临时产物，而是顶层 Harness dispatch 的正式输入。每个 axis report 至少需要包含：

- `axis`: `blackbox` / `whitebox` / `anticheat` / `composite`
- `report_ref`: 稳定 evidence ref 或内联报告位置
- `verdict`: `pass` / `soft_fail` / `hard_fail` / `blocked` / `not_applicable`
- `severity`
- `target_type`
- `axis_applicability_state`
- `expected_method`
- `carrier`
- `runtime_dispatch_profile`
- `isolation_guarantee`
- `carrier_isolation_broken`
- `checklist_results`
- `missing_evidence`

`milestone-gate` 必须把缺失 axis report、隔离被破坏、或运行时无法证明 sibling carrier 的情况作为聚合输入处理，不得在聚合阶段自行创建新 axis verdict。

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
    blackbox:
      state: applicable | not_applicable | substituted | blocked
      expected_method: external_behavior_scenario | artifact_acceptance_review | operator_simulation | N/A
      substituted_by: composite | professional_review | policy_check | N/A
      reason: string
    whitebox:
      state: applicable | not_applicable | substituted | blocked
      expected_method: structural_internal_analysis | artifact_structure_review | policy_structure_review | N/A
      substituted_by: composite | professional_review | policy_check | N/A
      reason: string
    anticheat:
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
      axis: blackbox | whitebox | anticheat | composite
      applicability_state: applicable | not_applicable | substituted | blocked
      expected_method: string
      substitute_method: string | N/A
      evidence_ref: string | N/A
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
```

### Target routing matrix

| target_type | blackbox | whitebox | anticheat | composite |
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

### Aggregator execution order and final verdict priority

Aggregator 必须按固定顺序执行，不能先看 raw axis verdict 再回填 target type：

1. 解析 `target_type_rules`、`axis_applicability`、替代验收字段与 mixed `slice_coverage`。
2. 计算 `weight_rules`。
3. 检测 `contradiction_rules`。
4. 消费 `composite_lane_rules`，并使用 `axis_satisfied(axis)` 判断 mandatory applicable / substituted 轴是否满足。
5. 在 Step 0 已解析完成的前提下，才允许触发 `degenerate_and_rules`。

最终 verdict 的阻断优先级：

| 优先级 | 条件 | verdict |
|--------|------|---------|
| 0 | `target_type = unknown`、`axis_applicability_resolved = false`、替代证据缺失、mixed 缺少 `slice_coverage`、或 `aggregation_rules_missing` 导致无法解释轴适用性 | `blocked` |
| 1 | veto-power 轴适用且 hard_fail / blocked，或 mandatory substituted 轴 `axis_satisfied = false` | `blocked` |
| 2 | `contradiction_blocked = true` | `blocked` |
| 3a | 所有 weight ≥ 3 的 WT pass，所有 mandatory applicable / substituted axes 满足 `axis_satisfied = true`，显式 `not_applicable` 轴均有 target_type reason | `pass` |
| 3b | 任一 weight ≥ 3 的 WT hard-fail，且无 critical fail | `soft-fail` |
| 3c | 任一 weight ≥ 4 的 WT hard-fail | `hard-fail` |
| 4 | 退化 AND 条件全部满足，且 Step 0 适用性解析完成 | `pass`（标记 `degenerate_and_applied`） |

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
    blackbox:
      aggregate: "lane-level verdict = AND of all WT black-box lane findings"
      veto_power: true   # black-box fail → milestone blocked，无论 per-WT aggregation 结果
    whitebox:
      aggregate: "lane-level verdict = AND of all WT white-box lane findings"
      veto_power: true
    anticheat:
      aggregate: "lane-level verdict = AND of all WT anti-cheat signals; any high-severity finding → lane fail"
      veto_power: true   # cheating signal → milestone blocked
    composite:
      aggregate: "lane-level verdict = AND of all WT composite lane findings"
      veto_power: false  # composite lane 是总体判断，不单独 block
  weight_modifier:
    # 有限 B 降级：lane finding 可调整特定 WT 的权重，但不替代四轴判定
    enabled: true
    rules:
      - lane: anticheat
        finding: high_severity
        target_wt_weight: 0        # cheating signal 将对应 WT 的权重清零
      - lane: blackbox
        finding: high_severity
        target_wt_weight: 0        # black-box 严重缺陷将对应 WT 权重清零
  final_verdict:
    pass_condition: |
      per_WT_aggregation_verdict == pass
      AND axis_satisfied(blackbox)
      AND axis_satisfied(whitebox)
      AND axis_satisfied(anticheat)
      AND composite_verdict != hard_fail
```

### 推荐理由

- **四轴独立**：各 lane 的结论清晰可追溯，不会被 per-WT 权重"稀释"
- **Veto power**：black-box 测试失败就是失败，不应被其他 WT 的 pass 覆盖
- **有限 B 降级**：anti-cheat finding 可以将特定 WT 的权重清零，防止 cheating WT 的 pass 拉高聚合分数

### 与 Worktrack composite lane 的交接

Worktrack 级 implementation / validation / policy 证据会被 closeout 和 composite acceptance lane 汇总后输入 Milestone Gate 四轴。本 artifact 定义的 `lane_axes` aggregate 逻辑是这些 lane 结论在 milestone 级的消费方。

## 七、degenerate_and_rules：退化 AND 判定

### 触发条件

以下条件**全部**满足时，允许使用退化 AND：

```yaml
degenerate_and_rules:
  trigger_conditions:
    all_satisfied:
      - no_contradiction_detected: true       # 无任何矛盾
      - no_anticheat_high_severity: true      # 无反作弊高严重信号
      - all_lanes_consistent: true             # 所有 lane 一致（无 lane 级矛盾）
      - axis_applicability_resolved: true      # 所有轴均有 applicable / substituted / not_applicable / blocked 之一，且无 blocked
      - all_mandatory_axes_satisfied: true     # mandatory applicable / substituted 轴均满足 axis_satisfied
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

## 八、顶层四轴分派与 milestone-gate aggregator 交接

### 顶层 Harness axis dispatch contract

当 `worktrack_list_finished == true` 且 goal-driven milestone 需要 Milestone Gate 时，顶层 Harness 必须先执行四轴 sibling dispatch，再调用 `milestone-gate` 聚合。推荐流程：

1. 从 milestone-status-skill 的观察结果准备共享 facts：`milestone_id`、closed worktrack list、milestone artifact refs、target type hints、aggregation rules、closeout/evidence refs。
2. 为四个 axis 生成互相隔离的 input package。每份 package 只包含该 axis 需要的输入，不包含其他 axis 的 verdict、finding 或 report ref。
3. 使用 `dispatch_mode_recommend.py` 和 runtime dispatch profile 记录实际载体选择。若 `runtime_dispatch_mode = delegated` 且不能真实分派，axis dispatch 必须返回 runtime gap，不得自动降级成聚合通过。
4. 将四个 axis report 写入稳定 evidence refs，或以内联结构传入 `milestone-gate`，但二者都必须保留每轴的 `runtime_dispatch_profile` 和 `isolation_guarantee`。
5. 调用 `milestone-gate` 时传入 `axis_reports`。`milestone-gate` 只聚合，不重新执行 axis skill。

同一当前载体顺序运行四轴只能作为 fallback evidence 或 manual exception 的事实来源，不能满足真实四轴隔离。若 milestone 最终由 programmer 手动接受，必须记录为 acceptance override，而不是把 `milestone_gate_verdict` 改写为 `pass`。

### aggregator 的输入

```yaml
aggregator_input:
  per_worktrack:
    - worktrack_id: "WT-xxx"
      single_acceptance_verdict: { ... }  # from single-acceptance-contract.md
      gate_evidence: { ... }              # implementation/validation/policy gate verdicts
      closeout_record: { ... }
      closeout_evidence_bundle_ref: ".servo/milestone/...#WT-xxx-Closeout-Evidence-Bundle"
      closeout_bundle_status: complete | incomplete | contaminated | historical_gap | missing
      composite_lane_findings:            # per-WT composite lane findings
        blackbox: pass | soft_fail | hard_fail
        whitebox: pass | soft_fail | hard_fail
        anticheat: pass | high_severity
        composite: pass | soft_fail | hard_fail
  axis_reports:
    blackbox:
      axis: blackbox
      report_ref: string
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      severity: low | medium | high
      carrier: subagent | current-carrier | human | missing
      runtime_dispatch_profile: { ... }
      isolation_guarantee: true | false
      carrier_isolation_broken: true | false
      target_type: program_code | non_program_artifact | mixed | unknown
      axis_applicability_state: applicable | not_applicable | substituted | split | blocked
      expected_method: string
      checklist_results: [ ... ]
      missing_evidence: [ ... ]
    whitebox: { ... }
    anticheat: { ... }
    composite: { ... }
  axis_dispatch_profile:
    dispatch_owner: top_level_harness
    dispatch_model: sibling_delegated | current_carrier_fallback | missing
    delegation_attempted_by_axis:
      blackbox: true | false
      whitebox: true | false
      anticheat: true | false
      composite: true | false
    carrier_isolation_broken_any: true | false
    same_carrier_cross_axis: true | false
    dispatch_gap_reason: string | N/A
  aggregation_rules: { ... }              # per-milestone 配置，来自本 artifact
  target_type_rules: { ... }              # target_type 与 axis_applicability
  manual_exception:
    present: true | false
    exception_type: programmer_acceptance_override | N/A
    reason: string | N/A
    accepted_gate_verdict_preserved_as: pass | soft_fail | hard_fail | blocked | N/A
    anti_cheat_findings_preserved: true | false | N/A
    manual_exception_followup_ref: string | N/A
```

### aggregator 的输出

```yaml
aggregator_output:
  milestone_gate_verdict: pass | soft_fail | hard_fail | blocked
  milestone_gate_execution_model:
    dispatch_owner: top_level_harness
    aggregation_owner: milestone-gate
    axis_dispatch_consumed: true | false
    nested_axis_dispatch_attempted: false
  axis_report_status: complete | missing | contaminated | isolation_broken | blocked_axis
  axis_report_status_by_axis:
    blackbox: present | missing | stale | contaminated | blocked
    whitebox: present | missing | stale | contaminated | blocked
    anticheat: present | missing | stale | contaminated | blocked
    composite: present | missing | stale | contaminated | blocked
  axis_dispatch_profile: { ... }
  aggregation_rules_applied: true | false
  aggregation_rules_missing: true | false
  aggregation_rules_source: string
  target_type: program_code | non_program_artifact | mixed | unknown
  target_type_source: programmer_declared | milestone_artifact | gate_input | inferred_from_worktracks | unknown
  axis_applicability_resolved: true | false
  axis_satisfaction:
    blackbox:
      applicability_state: applicable | not_applicable | substituted | split | blocked
      axis_satisfied: true | false
      reason: string
      evidence_refs: [string]
    whitebox:
      applicability_state: applicable | not_applicable | substituted | split | blocked
      axis_satisfied: true | false
      reason: string
      evidence_refs: [string]
    anticheat:
      applicability_state: applicable | not_applicable | substituted | split | blocked
      axis_satisfied: true | false
      reason: string
      evidence_refs: [string]
    composite:
      applicability_state: applicable | not_applicable | substituted | split | blocked
      axis_satisfied: true | false
      reason: string
      evidence_refs: [string]
  substitution_evidence_summary:
    by_axis:
      blackbox | whitebox | anticheat | composite:
        substitute_method: string | N/A
        substitution_evidence_ref: string | N/A
        substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
        evidence_covers_completion_signal: true | false | N/A
        checked_scope: string
  per_worktrack_weights: { ... }          # 每个 WT 的最终权重（含 overrides）
  contradiction_findings: [...]           # 已检测到的矛盾
  contradiction_resolution_status:         # 若有矛盾
    blocked: true | false
    resolution_path: new_verification_worktrack | programmer_resolution | none
  composite_lane_verdicts:                 # 四轴聚合结论
    blackbox:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | split | blocked
      substituted_by: string | N/A
      axis_satisfied: true | false
      veto_triggered: true | false
      weight_modifier_applied: true | false
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
      evidence_covers_completion_signal: true | false | N/A
    whitebox:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | split | blocked
      substituted_by: string | N/A
      axis_satisfied: true | false
      veto_triggered: true | false
      weight_modifier_applied: true | false
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
      evidence_covers_completion_signal: true | false | N/A
    anticheat:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | split | blocked
      substituted_by: string | N/A
      axis_satisfied: true | false
      veto_triggered: true | false
      weight_modifier_applied: true | false
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
      evidence_covers_completion_signal: true | false | N/A
    composite:
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      applicability_state: applicable | not_applicable | substituted | blocked
      substituted_by: string | N/A
      axis_satisfied: true | false
      veto_triggered: true | false
      weight_modifier_applied: true | false
      substitute_method: string | N/A
      substitution_evidence_ref: string | N/A
      substitute_verdict: pass | soft_fail | hard_fail | blocked | not_applicable | N/A
      evidence_covers_completion_signal: true | false | N/A
  slice_coverage:                         # required for target_type = mixed
    - slice_id: string
      slice_target_type: program_code | non_program_artifact | unknown
      axis: blackbox | whitebox | anticheat | composite
      applicability_state: applicable | not_applicable | substituted | split | blocked
      expected_method: string
      substitute_method: string | N/A
      evidence_ref: string | N/A
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
  degenerate_and_applied: true | false
  degenerate_and_reason: string | N/A
  manual_exception:
    present: true | false
    exception_type: programmer_acceptance_override | N/A
    gate_verdict_preserved: pass | soft_fail | hard_fail | blocked | N/A
    reason: string | N/A
  accepted_gate_verdict_preserved_as: pass | soft_fail | hard_fail | blocked | N/A
  anti_cheat_findings_preserved: true | false | N/A
  manual_exception_followup_ref: string | N/A
  aggregation_summary: string
```

### Aggregator 实现时需注意

- `axis_reports` 缺失、被污染、无法追溯或缺少 `runtime_dispatch_profile` 时，`axis_applicability_resolved` 不得为 true；最终 verdict 必须为 `blocked`，除非该 axis 被 target type 明确 `not_applicable` 且不需要 positive evidence。
- `closeout_evidence_bundle_ref` 缺失、bundle 不完整、bundle contaminated，或只有 prose closeout summary 时，不得后验合成 self-review、dispatch provenance 或 composite lane evidence。该 worktrack 必须以 `missing` / `incomplete` / `contaminated` / `historical_gap` 状态进入 axis checks 和 aggregation。
- `axis_dispatch_profile.same_carrier_cross_axis == true` 或 `carrier_isolation_broken_any == true` 时，聚合器必须把真实四轴隔离视为未满足。该事实可被 programmer final acceptance override 接受，但 `milestone_gate_verdict` 仍应保持 `blocked` 或其他真实 non-pass verdict。
- `manual_exception` 只描述 final acceptance override，不参与 `axis_satisfied(axis)` 计算，不得把 `blocked` 改写成 `pass`。
- `anticheat` 轴的 finding 是 evidence credibility verdict，不是可被 manual exception 消除的普通 residual risk。若 anticheat 报告 evidence reuse、same-carrier contamination、stale checkpoint、gate bypass 或 self-review bias，manual exception 只能说明 programmer 接受该风险继续 closeout；原 finding、severity、affected evidence refs、`axis_report_status` 和 `axis_report_status_by_axis` 必须原样保留，并显式记录 `anti_cheat_findings_preserved: true`。
- `milestone_gate_verdict` 与 `milestone_acceptance_verdict` 是两层不同结论：前者回答 Gate 是否通过，后者回答 programmer 是否在看到 Gate 结果后接受 milestone。`accepted_with_manual_exception` 只能出现在 final acceptance 层，不能反向改变 Gate verdict、axis verdict 或 anti-cheat verdict。
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
      blackbox: { state: applicable, expected_method: external_behavior_scenario }
      whitebox: { state: applicable, expected_method: structural_internal_analysis }
      anticheat: { state: applicable, expected_method: evidence_integrity_review }
      composite: { state: applicable, expected_method: composite_acceptance_lanes }
  composite_lane_rules:
    consumption_mode: independent_axes_with_weight_modifier
    lane_axes:
      blackbox: { veto_power: true }
      whitebox: { veto_power: true }
      anticheat: { veto_power: true }
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
      blackbox:
        state: substituted
        expected_method: artifact_acceptance_review
        substituted_by: operator_simulation
      whitebox:
        state: substituted
        expected_method: artifact_structure_review
        substituted_by: professional_review
      anticheat:
        state: applicable
        expected_method: evidence_integrity_review
      composite:
        state: applicable
        expected_method: composite_acceptance_lanes
  composite_lane_rules:
    consumption_mode: independent_axes_with_weight_modifier
    lane_axes:
      blackbox: { veto_power: false }    # docs milestone 不强依赖 black-box
      whitebox: { veto_power: true }
      anticheat: { veto_power: false }
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
- **Axis report 先于聚合 verdict**：未收到四轴显式报告时，`milestone-gate` 不得在内部补跑轴检查或制造默认 axis verdict
- **Same-carrier fallback 不是隔离 pass**：current-carrier 顺序执行四轴只能产生运行时缺口或 manual exception evidence，不能满足 sibling axis isolation
- **Manual exception 不是 anti-cheat 消音器**：programmer 可以接受 blocked Gate 的业务风险，但不得删除、降级或改写 anti-cheat finding；证据可信度 verdict 必须保留给后续审计和 follow-up milestone。
- **Acceptance verdict 不反写 Gate verdict**：`milestone_acceptance_verdict: accepted_with_manual_exception` 不等价于 `milestone_gate_verdict: pass`。任何读者必须同时读取 preserved Gate verdict 和 acceptance override，不能只看最终 completed 状态。
- **not_applicable 不是 pass**：`not_applicable` 只能移出 mandatory pass 计算，不能提供正向完成证据
- **substituted 必须有证据**：`substituted` 只有在替代验收证据存在并通过时才可视为 axis satisfied
- **退化 AND 必须记录**：即使当前 evidence 状态简单到不需要聚合规则，也必须说明"为什么简单"而不是"跳过了规则"

### 向后兼容

- 已完成的 milestone（completed/superseded）不需要补充 aggregation_rules
- 活跃 milestone 如果尚未声明 aggregation_rules，默认使用 `enabled: false`（退化 AND），但必须在 milestone gate evidence 中标记 `aggregation_rules_missing: true`。当缺失规则导致 target type 或 axis applicability 无法解释时，最终 verdict 必须为 `blocked`；只有适用性已由其他可追踪输入解析完成时，它才是 warning。
- 旧 milestone 缺少 `target_type_rules` 时，Milestone Gate 必须在 evidence 中记录 `target_type: unknown` 或一个有来源的 runtime inference；不得把缺失解释为 program_code、non_program_artifact 或 pass
- 此行为确保新 Gate 语义不会静默改变旧 milestone 的目标类型判断。

## 十二、相关文档

- [Single-Acceptance Contract](../worktrack/single-acceptance-contract.md) — 被消费的 verdict 格式
- [Worktrack Contract](../worktrack/contract.md) — worktrack 级 gate 定义
- [Milestone Artifact Control](../control/milestone.md) — milestone gate 的上级定义
- [milestone-gate](../../../../product/harness/skills/milestone-gate/SKILL.md) — 可执行 Gate aggregator，消费顶层 Harness 提供的显式四轴报告
- [milestone-blackbox-check](../../../../product/harness/skills/milestone-blackbox-check/SKILL.md) — 外部行为场景与非程序替代验收轴
- [milestone-whitebox-check](../../../../product/harness/skills/milestone-whitebox-check/SKILL.md) — 内部结构分析与非程序结构替代审查轴
