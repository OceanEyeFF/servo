---
name: milestone-gate
description: 当 worktrack_list_finished 后需要运行 Milestone Gate 两层集成验收时使用这个技能。它是 Gate Orchestrator：Layer 1 分派 4 个隔离 SubAgent 轴技能（blackbox/whitebox/anticheat/composite），Layer 2 按 per-milestone 可配置 aggregation_rules 运行聚合器→milestone_gate_verdict。由 milestone-status-skill 在确认 worktrack 列表 finished 后调用。
---

# Milestone Gate 技能

## 概览

本技能实现 Milestone Gate 的 **两层集成验收**，是 goal-driven milestone 的 RepoScope 集成验收层，位于"全部 worktrack 关闭"之后、"`purpose_achieved` 判定"之前。

它是 **Gate Orchestrator**：不自己做轴检查，而是分派 4 个隔离 SubAgent 轴技能（Layer 1），收集各轴 verdict 后按 per-milestone 可配置 `aggregation_rules` 运行聚合器（Layer 2），最终产出 `milestone_gate_verdict`。

调用关系：

```
milestone-status-skill（sensor）
  └─ worktrack_list_finished → 调用 milestone-gate-skill（本技能）
       ├─ Layer 1: dispatch 4 axis skills (SubAgent × 4, parallel)
       └─ Layer 2: aggregator → milestone_gate_verdict
```

聚合规则合同（已详述于本技能 §Layer 2 聚合器）。本技能不替代各 worktrack 自己的 gate，也不把上层集成失败回写成单个 worktrack gate 的通过。

## 何时使用

当满足以下条件时使用这个技能：

- 当前 milestone 下所有 worktrack 已闭环（`worktrack_list_finished == true`），由 milestone-status-skill 确认
- 需要运行 Milestone Gate 两层集成验收，产出 `milestone_gate_verdict`
- 4 个轴检查技能（servo-milestone-{blackbox,whitebox,anticheat,composite}-check）已部署
- 运行时支持 SubAgent dispatch（推荐）或接受 current-carrier fallback

以下情况不适用：

- worktrack 未全部闭环 → 应返回 `not_ready`
- 需要单个 WT 的 gate 判定 → 使用 `worktrack-gate-skill`
- 需要进度计数 / handback 信号 → 使用 `milestone-status-skill`
- 需要修改代码 / evidence → 禁止（只读）

## 工作流

1. **接收输入**：从 milestone-status-skill 接收：
   - `milestone_id`
   - `closed_worktrack_list`：已闭环 WT 列表，每项含 `{ id, node_type, verdict, critical_failure, closeout_record_ref }`
   - `aggregation_rules`：milestone artifact 的 `aggregation_rules` 字段（缺失时退化 AND）
2. **验证就绪**：确认 `closed_worktrack_list` 非空。若为空，返回 `blocked`。
3. **Layer 1：分派 4 轴**（见下文）
4. **Layer 2：聚合器**（见下文）
5. **产出最终 verdict**：`milestone_gate_verdict` + 聚合状态字段
6. **停止**：不得进入 purpose_achieved 判定或代码修改

---

## Layer 1：四轴独立 SubAgent 分派

将 milestone 级集成验收分解为 4 个**隔离轴检查**，每个轴由独立 SubAgent 承载、并行执行、轴间不可见。

### 轴定义

| 轴 | Skill | 视角 | 检查范围 |
|----|-------|------|---------|
| **blackbox** | `milestone-blackbox-check` | 外部用户视角 | 跨 WT 集成一致性、用户承诺兑现、回归风险、路径约定合规、完整性缺口（B1-B5）。**不阅读实现代码。** |
| **whitebox** | `milestone-whitebox-check` | 内部实现视角 | 接口契约一致性、状态流转完整性、依赖图、架构分层合规、关键集成路径实现质量（W1-W5）。**阅读完整实现代码。** |
| **anticheat** | `milestone-anticheat-check` | 证据可信度视角 | Mock abuse、evidence 复用、局部验证、gate bypass、过期 evidence、self-review bias、false positive risk（A1-A7）。**不评判代码正确性，只评判证据可信度。** |
| **composite** | `milestone-composite-check` | 复合验收视角 | 消费 per-WT lane 报告（code-review 等 C1-C6）并聚合成 milestone 级复合验收结论。**不生成新代码检查。** |

### 分派规则

1. **并行 SubAgent 分派**：若运行时支持 SubAgent dispatch，4 个轴作为 SubAgent **并行分派**。每个 SubAgent 的任务包只包含该轴独享的输入材料，**不得包含其他轴的 verdict 或检查结果**。
2. **超时处理**：若任一轴 SubAgent 失败或超时，该轴标记 `verdict: blocked` 并记录失败原因。已完成的轴 verdict 正常收集。
3. **SubAgent 不可用降级**：若运行时完全不支持 SubAgent dispatch，降级为 current-carrier **顺序执行** 4 个轴技能。此时必须标记 `carrier_isolation_broken: true`，并在 `isolation_guarantee` 中记录降级原因。顺序执行时，每个轴的检查必须在完全独立的上下文中进行。
4. **隔离约束**：收到各轴输出后，若任一侧标记 `isolation_guarantee: false`，记录到聚合状态但继续聚合（隔离破坏本身不自动阻断——由裁决逻辑决定影响）。

### 各轴输出格式

每个轴技能产出结构化 YAML verdict：

```yaml
{axis}_verdict:
  axis: blackbox | whitebox | anticheat | composite
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  checklist_results: [...]
  carrier: subagent | current-carrier
  isolation_guarantee: true | false
  carrier_isolation_broken: true | false
```

各轴的完整 checklist（B1-B5、W1-W5、A1-A7、C1-C6）和 verdict 推导规则定义在各自 SKILL.md 中。

---

## Layer 2：可配置聚合器（Aggregator）

本层在收集齐全 4 轴 verdict 后执行。聚合器消费四类输入：

1. **per-WT single-acceptance verdicts**：每个已闭环 WT 的 `verdict`、`node_type`、`critical_failure`
2. **4 轴 verdicts**：Layer 1 产出的 4 个结构化 verdict
3. **target_type_rules / axis_applicability**：来自 milestone artifact、轴输出或已验证 docs/harness 合同的目标类型与轴适用性字段
4. **aggregation_rules**：来自 milestone artifact 的 `aggregation_rules` 字段。若缺失，默认使用 `enabled: false`（退化 AND），标记 `aggregation_rules_missing: true`

聚合分五步执行，顺序不可颠倒。Step 0 必须先完成；后续步骤不得把 `not_applicable` 或 `substituted` 当成原始 `pass` 使用。

### Step 0：target_type_rules / axis_applicability resolution（目标类型与轴适用性解析）

先解析 milestone 的 `target_type_rules`、每个轴 verdict 中的 `target_type` / `axis_applicability`，以及非程序替代验收字段：

- `target_type` 允许表达 `program_code`、`non_program_artifact`、`mixed` 或 `unknown`。
- `axis_applicability` 至少区分 `applicable`、`not_applicable`、`substituted`、`blocked`。
- `not_applicable` 必须带有 `target_type` 与明确原因；它只能把该轴从 mandatory pass 计算中移除，不能产生正向 evidence、不能覆盖 completion signal、不能等价为 `pass`。
- `substituted` 必须带有 `substitute_method`、`substitution_evidence_ref`、`substitute_verdict`、`evidence_covers_completion_signal`。只有 `substitute_verdict: pass` 且 `evidence_covers_completion_signal: true` 时，替代轴才可被判为 satisfied。
- `mixed` 目标必须提供 `slice_coverage`，每个 slice 记录 `slice_target_type`、适用轴、使用方法、证据引用和 verdict。程序/代码 slice 的 pass 不能覆盖非程序 slice 的替代证据缺失；非程序 substitute pass 也不能覆盖程序/代码 slice 的 blackbox/whitebox 缺失。
- 目标类型未知、适用性字段互相矛盾、替代证据缺失、`slice_coverage` 缺失或无法映射 completion signal 时，设置 `axis_applicability_resolved: false`，最终 verdict 必须为 `blocked`。

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
- `no_anti_cheat_high_severity == true`
- `all_lanes_consistent == true`
- `no_weight_override_applied == true`
- `all_critical_wt_pass == true`（所有 final_weight ≥ 4 的 WT pass）
- 所有 mandatory applicable / substituted veto-power axes 满足 `axis_satisfied(axis) == true`

触发后：`degenerate_and_applied: true` + 退化理由，判定=简单 AND

### 最终裁决（milestone_gate_verdict）

| 优先级 | 条件 | verdict |
|--------|------|---------|
| 0 | target type unknown、`axis_applicability_resolved == false`、替代证据缺失、mixed 缺少 `slice_coverage`、或 `aggregation_rules_missing` 导致无法解释轴适用性 | `blocked` |
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
- `aggregation_rules_applied`：boolean
- `aggregation_rules_missing`：boolean
- `aggregation_rules_source`：string
- `target_type`：program_code / non_program_artifact / mixed / unknown
- `target_type_source`：string
- `axis_applicability_resolved`：boolean
- `axis_satisfaction`：object — 每轴包含 `applicability_state`、`axis_satisfied`、reason 和 evidence refs
- `slice_coverage`：array | N/A — mixed target 时必须列出每个 slice 的 target type、适用轴、方法、证据和 verdict
- `substitution_evidence_summary`：object — 每个 substituted 轴的 substitute method、evidence ref、substitute verdict 和 completion-signal coverage
- `per_worktrack_weights`：array — `{ worktrack_id, node_type, base_weight, final_weight, overridden, override_reason }`
- `contradiction_findings`：array — `{ wt_a_id, verdict_a, wt_b_id, verdict_b, severity, recommended_resolution }`
- `contradiction_blocked`：boolean
- `composite_lane_verdicts`：object — `{ blackbox, whitebox, anticheat, composite }`，每轴含 `{ verdict, severity, veto_power, applicability_state, axis_satisfied, veto_triggered, weight_modifier_applied, substitute_method, substitution_evidence_ref, substitute_verdict, evidence_covers_completion_signal }`
- `degenerate_and_applied`：boolean
- `degenerate_and_reason`：string | N/A
- `carrier_isolation_broken`：boolean
- `isolation_note`：string

## 硬约束

本技能特有约束：

1. **只读**：不修改任何代码、evidence、artifact。只产出结构化 verdict。
2. **不得替代 worktrack gate**：Milestone Gate 位于所有 worktrack closeout 之后，不替代单个 WT 的 gate。
3. **轴间隔离**：分派 SubAgent 时，任务包不得包含其他轴的 verdict。
4. **SubAgent 降级显式记录**：SubAgent 不可用时降级为 current-carrier，标记 `carrier_isolation_broken: true`。
5. **聚合顺序不可颠倒**：target_type / axis_applicability → weight → contradiction → composite_lane → degenerate 顺序必须执行，不可跳过。
6. **缺失输入必须暴露**：aggregation_rules 缺失时标记 `aggregation_rules_missing: true`，不可静默假设。
7. **不得进入后续阶段**：产出 verdict 后停止。purpose_achieved 判定和 writeback 由 milestone-status-skill 负责。
8. **阻断必须显式**：veto / contradiction / critical fail 导致的 block 必须记录具体原因和可追溯证据。
9. **轴适用性先于轴裁决**：未解析 `target_type_rules` / `axis_applicability` 时，不得把 raw axis verdict 聚合成 pass。
10. **not_applicable 不是 pass**：`not_applicable` 只能在 target type 和 reason 明确时移出 mandatory pass 计算，不能贡献 positive evidence、completion-signal coverage 或 weight bonus。
11. **substituted 必须有证据**：`substituted` 轴缺少 `substitute_method`、`substitution_evidence_ref`、`substitute_verdict: pass` 或 `evidence_covers_completion_signal: true` 时，`axis_satisfied(axis)` 必须为 false；若该轴 mandatory/veto-power，则 milestone verdict 为 `blocked`。
12. **mixed 目标必须逐 slice 覆盖**：`target_type: mixed` 缺少 `slice_coverage` 或任一 slice 缺少对应适用轴证据时，不能用其他 slice 的 pass 补位，最终 verdict 必须为 `blocked` 或显式非 pass。

## 资源

- milestone-gate-aggregation.md — aggregation_rules 合同
- milestone-status-skill — 调用方 sensor skill
- milestone-blackbox-check — 轴技能 1
- milestone-whitebox-check — 轴技能 2
- milestone-anticheat-check — 轴技能 3
- milestone-composite-check — 轴技能 4
- single-acceptance-contract.md — WT verdict 格式
- Skill 公共约束已内联于 §硬约束
