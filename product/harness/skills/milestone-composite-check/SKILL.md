---
name: milestone-composite-check
description: 当 Milestone Gate 需要消费 composite acceptance lanes（code-review / feature-completeness / related-influence / intent-completeness / operator-simulation / professional-review），聚合并审查现有的 per-WT lane 报告以产出 milestone 级复合验收结论时，使用这个技能。它聚合已有 lane 报告，不生成新的代码检查。与其他三轴（blackbox / whitebox / anticheat）不同，本轴不主动检查代码。
---

# Milestone 复合验收轴检查技能

## 概览

本技能实现 `Milestone Gate` 四轴检查中的 **composite acceptance** 轴。它是 Layer 1 四个独立 SubAgent skill 中的一个，与其他三轴（milestone-blackbox-check、milestone-whitebox-check、milestone-anticheat-check）并行运行、轴间不可见、各自产出独立的 `composite_verdict`。

与其他三轴不同，本轴**不生成新的代码检查**。它消费每个已闭环 worktrack 上已经产出的 `composite_lane_record` refs/statuses，聚合并审查其完整性和可信度，最终形成 milestone 级的复合验收结论。

本技能在隔离的 SubAgent 上运行，接收限定范围输入包，不得读取其他轴的 verdict。架构位置定义见 milestone-gate-aggregation.md Layer 1 / composite_lane_rules。

## 何时使用

当 Milestone Gate 到达 composite acceptance 轴检查阶段时，使用这个技能：

- milestone 的所有 worktrack 已关闭
- per-WT 的 composite acceptance lane records 已经存在（至少部分存在）或 closeout bundle 已显式标记缺失/历史缺口
- 需要从六条复合验收 lane 的角度判断 milestone 是否可接受
- 需要检测 lane 覆盖完整性、fallback 是否充分、mandatory lane 是否缺失
- 需要综合六条 lane 的 verdict 形成 composite axis 的整体判定
- 系统必须保留每条 lane 的 record ref、status、carrier、fallback、evidence 追溯链、absorbed issue refs 和 residual risks，不能把六条 lane 压缩成一段模糊总结

## 工作流

1. **确认角色边界**：确认这是一轮 composite axis 检查，不是 blackbox / whitebox / anticheat 检查，也不是 milestone-status-skill 内的 aggregator 聚合。
2. **验证输入隔离**：检查输入包是否仅包含本轴所需数据（per-WT lane 报告、milestone composite_acceptance 配置、purpose、acceptance_criteria）。如果输入包中包含其他轴的 verdict 或未经本轴授权的外部判断，必须标记 `isolation_guarantee: false` 并记录泄漏来源。
3. **载入输入**：
   - 所有已闭环 WT 的 composite acceptance lane records（如存在）以及 closeout bundle 中每条 lane 的 ref/status
   - milestone 的 `composite_acceptance` 配置（来自 milestone artifact 的 `composite_acceptance` 字段或聚合合同中的 `composite_lane_rules`）
   - milestone 的 `purpose` 和 `acceptance_criteria`
4. **判定 review depth**：读取 milestone 的 composite_acceptance 配置中的 `review_depth`（`standard` / `deep`），并结合 mandatory trigger table 判定当前深度。若配置缺失，先根据 milestone `target_type`、purpose、node_types、changed paths、risk boundary 与 acceptance criteria 做目标/风险分类；分类命中 deep trigger 才进入 deep，分类明确为普通低风险则进入 standard，分类无法完成时返回 `blocked` / `questions_required`，不得无依据盲目默认 deep。
5. **逐 lane 检查**：对六条 composite acceptance lane 分别执行检查：
   - **C1 (code-review)**：消费 `code-review` lane record，检查其独立代码审查覆盖（非 self-review）结论、证据 refs 与状态。它回答 review coverage 是否存在且覆盖关键 WT，不判定 evidence credibility bias；carrier/provenance 偏倚由 anticheat A6 判定。
   - **C2 (feature-completeness)**：消费 `feature-completeness` lane record，检查 completion_signal→evidence 映射是否由 record refs 支撑。
   - **C3 (related-influence)**：消费 `related-influence` lane record，检查相邻模块影响分析是否由 record refs 支撑。
   - **C4 (intent-completeness)**：消费 `intent-completeness` lane record，检查 deliverables 与 milestone purpose 对齐证据是否由 record refs 支撑。
   - **C5 (operator-simulation)**：审计已有 `operator-simulation` lane record、runbook/workflow/CLI/config evidence refs 与操作路径记录，判断 operator path 是否完整。C5 不生成新的 blackbox 行为场景、不运行 CLI/API、不替代 blackbox 轴的用户可观察行为测试。
   - **C6 (professional-review)**：消费 `professional-review` lane record，检查独立 professional review 信号是否由 record refs 支撑。
6. **判定 mandatory lanes**：根据 mandatory/deep trigger table 判定当前 milestone 场景下哪些 lane 为 mandatory：
   - 若命中 deep trigger（release / installer/deploy / migration / authority changes / destructive operation / path governance / security/privacy / cross-WT integration / release-prep）：所有 6 条 lane 均为 mandatory
   - 否则：C1 (code-review) + C2 (feature-completeness) 为 mandatory，C3-C6 为 optional
7. **lane fallback 审查**：对每条 lane，检查其 carrier 状态：
   - `carrier: subagent` 且 `delegation_attempted: true`：正常
   - `carrier: current-carrier` 且 `fallback_reason` 有合法记录：可接受，但标记 `fallback: true`
   - `carrier: human` 且 `fallback_reason` 有合法记录：可接受，但标记 `fallback: true`
   - lane record 缺失且无 fallback 记录：该 lane 标记为 `blocked`
   - lane record 存在但 `carrier` / `delegation_attempted` / `fallback_reason` 任一项缺失：该 lane 标记为 `blocked`
   - lane status 为 `missing` / `incomplete` / `historical_gap` / `contaminated`：该 lane 不能 pass，且必须保留原 status、record ref、缺失字段或污染原因
   - lane status 为 `not_applicable`：仅当 `not_applicable_reason` 明确且该 lane 非 mandatory 时可作为不适用记录；不得贡献 positive evidence
8. **综合判定**：对每条 lane 给出独立 verdict，再形成 composite axis 的整体判定：
   - 任一 mandatory lane 为 `blocked` → 整体 verdict = `blocked`
   - 任一 lane 为 `hard_fail` 且 mandatory → 整体 verdict = `hard_fail`
   - 任一 lane 为 `soft_fail` 且 mandatory → 整体 verdict ≥ `soft_fail`
   - 所有 mandatory lane 为 `pass`，optional lane 均为 `pass` 或不存在 → 整体 verdict = `pass`
9. **生成 composite_verdict 报告**：按照输出格式生成完整的结构化 verdict，包含每条 lane 的详细判定、证据引用和发现。
10. **停止并返回**：在产出 composite_verdict 后停止，不进入 aggregator 或其他轴的判定流程。

## 检查约定

### Composite 轴任务简报

- `axis`: composite
- `触发条件`: milestone 所有 worktrack 已关闭，进入 Milestone Gate 四轴检查阶段
- `目标`: 聚合 per-WT composite acceptance lane 报告，产出 milestone 级 composite acceptance verdict
- `milestone_id`: 当前 milestone 标识
- `review_depth`: standard | deep
- `范围内`:
  - 所有已闭环 WT 的 composite acceptance lane 报告
  - milestone composite_acceptance 配置
  - milestone purpose 和 acceptance_criteria
- `范围外`:
  - 代码实现细节（除非 lane 报告已引用）
  - 其他三轴（blackbox / whitebox / anticheat）的 verdict
  - per-WT gate evidence 的重新审查
  - 生成新的代码检查或测试
- `约束`: 只读、轴间不可见、不生成新代码检查
- `完成信号`: 所有 6 条 lane 已完成检查并给出 verdict，composite_verdict 已生成

### Composite 轴信息包

- `milestone_id`
- `review_depth`
- `deep_review_triggered`: true | false
- `deep_review_reason`: 触发 deep review 的具体场景（如 "release + cross-WT integration"）
- `mandatory_lanes`: 根据 deep trigger table 判定的 mandatory lane 列表
- `closed_wt_list`: 已闭环 WT 的 ID 列表及各自状态
- `lane_reports_available`: 每个 WT 是否提供了 composite acceptance lane 报告的摘要
- `composite_lane_records_by_worktrack`: 每个 WT 的六条 lane record refs/statuses
- `milestone_purpose_summary`: milestone purpose 的摘要
- `acceptance_criteria`: milestone 的 acceptance_criteria
- `composite_acceptance_config`: milestone 的 composite_acceptance 配置（如有）
- `missing_inputs`: 缺失的 lane 报告或配置项
- `known_risks`: 已知风险

### Lane 检查细则

每条 lane 检查时需记录以下结构：

```yaml
lane_check:
  check_id: C1..C6
  lane_name: code-review | feature-completeness | related-influence | intent-completeness | operator-simulation | professional-review
  mandatory: true | false
  per_wt_assessment:
    - worktrack_id: "WT-xxx"
      has_lane_report: true | false
      lane_record_ref: string | N/A
      lane_status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
      carrier: subagent | current-carrier | human | missing
      delegation_attempted: true | false | unknown
      fallback: true | false
      fallback_reason: "..." | N/A
      lane_verdict: pass | soft_fail | hard_fail | blocked | missing
      severity: none | low | medium | high
      evidence_refs: [...]
      absorbed_issue_refs: [...]
      residual_risks: [...]
      producer_ref: string | N/A
      validation_ref: string | N/A
      missing_required_fields: [...]
      contaminated_reason: string | N/A
      findings: "..."
      gap_notes: "..."
  aggregate_verdict: pass | soft_fail | hard_fail | blocked
  aggregate_severity: low | medium | high
  aggregate_finding: "..."
```

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `composite_verdict` 报告：

- `轴判定摘要`
- `deep review 触发分析`
- `逐 lane 详细检查`
- `mandatory lane 强制检查`
- `lane fallback 审计`
- `整体 composite verdict`
- `carrier 隔离声明`

结果必须包含以下字段的 `composite_verdict`：

```yaml
composite_verdict:
  axis: composite
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  mandatory_lanes_applied: true | false
  deep_review_triggered: true | false
  deep_review_reason: "..." | N/A
  checklist_results:
    - check_id: C1
      lane_name: code-review
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      lane_status: captured | linked | incomplete | missing | historical_gap | contaminated | not_applicable
      lane_record_refs: [...]
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      absorbed_issue_refs: [...]
      residual_risks: [...]
      finding: "..."
    - check_id: C2
      lane_name: feature-completeness
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      finding: "..."
    - check_id: C3
      lane_name: related-influence
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      finding: "..."
    - check_id: C4
      lane_name: intent-completeness
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      finding: "..."
    - check_id: C5
      lane_name: operator-simulation
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      finding: "..."
    - check_id: C6
      lane_name: professional-review
      verdict: pass | soft_fail | hard_fail | blocked
      mandatory: true | false
      severity: low | medium | high
      carrier: subagent | human | current-carrier
      fallback: true | false
      fallback_reason: "..." | N/A
      evidence_refs: [...]
      finding: "..."
  carrier: subagent | current-carrier
  isolation_guarantee: true | false
  isolation_leak_detail: "..." | N/A
  carrier_isolation_broken: true | false
  carrier_isolation_broken_reason: "..." | N/A
```

## 六条 Lane 检查清单

### C1: code-review

| 维度 | 内容 |
|------|------|
| **判据** | 每项已闭环 WT 是否有独立代码审查覆盖（非 self-review），且 critical WT 是否被覆盖？ |
| **检查方法** | 读取每个 WT 的 `code-review` `composite_lane_record`；检查其 evidence refs 是否指向独立 reviewer、programmer review、peer review 或等效复核记录。若 lane record 缺失、状态为 non-pass，或只有 self-review 标记（implementer == reviewer）且无独立 review 记录，则为 coverage 缺失。不得从 closeout prose summary 补造 review coverage。 |
| **pass 条件** | 所有已闭环 WT 均有独立 reviewer 记录，或 self-review 记录中声明了独立复核（如 programmer review）。 |
| **soft_fail 条件** | 部分低权重 WT（weight ≤ 2）缺失独立 review，但所有 critical WT（weight ≥ 3）均有独立 review。 |
| **hard_fail 条件** | 任一 critical WT 缺失独立 review 且无合理解释。 |
| **blocked 条件** | lane 数据完全缺失，无法判断。 |

**边界说明**：C1 只回答“是否存在独立 review 覆盖”，不把 carrier identity 重叠本身当成反作弊结论。若发现 reviewer / implementer / gate_judge / evidence producer 的身份重叠，应在 C1 中记录 coverage 影响，并把 evidence credibility bias 留给 anticheat A6。C1 的 hard_fail 来源是 critical WT 缺少独立 review 覆盖，而不是 provenance 风险本身。

### C2: feature-completeness

| 维度 | 内容 |
|------|------|
| **判据** | 所有 `completion_signals` 是否都有对应的证据？每个 signal 是否有至少一个 WT 的 evidence 支持？ |
| **检查方法** | 提取 milestone 的 `completion_signals` 列表；对每个 signal，读取已闭环 WT 的 `feature-completeness` `composite_lane_record` 和其 evidence refs，构建 signal→evidence 映射。不得从 closeout prose summary 搜索并合成 lane evidence。 |
| **pass 条件** | 每条 completion_signal 至少有一条来自 WT 的可信证据。 |
| **soft_fail 条件** | 部分非关键 signal 缺少直接证据但有间接证据（如相关 WT 的产出隐含覆盖了该 signal）。 |
| **hard_fail 条件** | 关键 signal 完全无证据支撑，或 signal→evidence 映射中存在明显断裂。 |
| **blocked 条件** | completion_signals 定义缺失或 lane 报告全部缺失。 |

### C3: related-influence

| 维度 | 内容 |
|------|------|
| **判据** | 每项 WT 是否检查了对相邻系统的影响？每个 WT 是否考虑了变更对相邻模块、文档、部署流程、测试系统的影响？ |
| **检查方法** | 读取每个 WT 的 `related-influence` `composite_lane_record` 和其 evidence refs；必要时只用 WT contract 的 `impacted_modules` 作为 expected coverage 对照，不得把 contract prose 当作 lane record。 |
| **pass 条件** | 所有已闭环 WT 均有相邻影响分析记录，且分析覆盖了实际变更涉及的相邻模块。 |
| **soft_fail 条件** | 部分 WT 的相邻影响分析不完整，但未发现遗漏对 critical 模块的影响。 |
| **hard_fail 条件** | 任一 WT 的变更明显触及相邻模块（如 shared interface、common config），但未做影响分析。 |
| **blocked 条件** | lane 报告全部缺失且无法从 WT contract 推断。 |

### C4: intent-completeness

| 维度 | 内容 |
|------|------|
| **判据** | 实现是否忠实于原始 purpose？每项 WT 的 deliverables 是否与 milestone purpose 在语义上对齐？ |
| **检查方法** | 读取每个 WT 的 `intent-completeness` `composite_lane_record`，用其 evidence refs 对齐 milestone purpose、acceptance_criteria 与每个 WT 的 scope / deliverables；检查是否存在 scope drift、偏移或过度实现。 |
| **pass 条件** | 所有 WT 的 deliverables 与 milestone purpose 一致，无偏离。 |
| **soft_fail 条件** | 存在可接受的轻微偏离（如 scope 内未计划但有益的小改进），但核心 purpose 未受影响。 |
| **hard_fail 条件** | 任一 WT 的 deliverables 与 milestone purpose 存在实质性偏离，或遗漏了关键意图。 |
| **blocked 条件** | purpose 定义缺失或 lane 报告全部缺失。 |

### C5: operator-simulation

| 维度 | 内容 |
|------|------|
| **判据** | 已有 operator-simulation 证据是否覆盖真实 operator path，是否暴露或遗漏可用性断裂？ |
| **检查方法** | 读取已有 per-WT `operator-simulation` `composite_lane_record`、runbook、workflow、CLI/config evidence refs 和操作路径记录；审计这些记录是否覆盖关键步骤、恢复路径和边界条件。不得新建 blackbox 行为场景或实际运行 CLI/API。 |
| **pass 条件** | operator 操作路径完整、可执行，所有关键步骤有明确的操作指南或自动化支持。 |
| **soft_fail 条件** | 操作路径可用但有低严重度的可用性瑕疵（如某些边缘情况的文档不完整）。 |
| **hard_fail 条件** | 操作路径存在断裂（如某步骤缺乏必要的前置配置说明、错误恢复路径缺失导致不可恢复状态）。 |
| **blocked 条件** | 无法构建 operator 操作路径（产出物不足以支撑模拟）。 |

**边界说明**：C5 的“operator-simulation”是对已有 operator-path 证据的复合验收审计，不是新的 blackbox execution lane。需要从外部用户视角构建场景、运行 CLI/API、检查用户可观察行为或回归路径时，应由 milestone-blackbox-check 承担；C5 只能把缺失或不充分的 operator evidence 记录为 `blocked` / `soft_fail` / `hard_fail`。

### C6: professional-review

| 维度 | 内容 |
|------|------|
| **判据** | 是否有领域专家或同行复核？检查是否存在外部/独立 review 信号。 |
| **检查方法** | 读取每个 WT 的 `professional-review` `composite_lane_record`；检查其 evidence refs 是否指向 programmer review、外部 reviewer 签名、peer review 记录、或等效的独立复核信号。不得从 closeout prose summary 合成 professional review。 |
| **pass 条件** | milestone 级存在至少一个独立的 professional review 信号（如 programmer 对整体 milestone 的 review、或有记录的 peer review）。 |
| **soft_fail 条件** | professional review 存在但覆盖不完整（如仅覆盖部分 WT），或 review 来自同一团队且独立性有限。 |
| **hard_fail 条件** | 完全无 professional review 证据且 milestone 涉及 deep review 触发场景。 |
| **blocked 条件** | lane 报告缺失且无法判断。 |

## Mandatory / Deep Trigger 表

以下场景触发 deep review，使所有 6 条 lane 均为 mandatory：

| 场景 | Mandatory | 所有 6 条 lane 均为 mandatory | 说明 |
|------|-----------|------------------------------|------|
| release | yes | yes | 发布场景，所有 lane 必须覆盖 |
| installer/deploy | yes | yes | 安装/部署场景，operator-simulation 和 related-influence 尤为关键 |
| migration | yes | yes | 迁移场景，intent-completeness 和 related-influence 必须覆盖 |
| authority changes | yes | yes | 权限变更场景，professional-review 和 code-review 必须覆盖 |
| destructive operation | yes | yes | 破坏性操作场景，operator-simulation 和 code-review 必须覆盖 |
| path governance | yes | yes | 路径治理变更场景，related-influence 和 code-review 必须覆盖 |
| security/privacy | yes | yes | 安全/隐私场景，code-review 和 professional-review 必须覆盖 |
| cross-WT integration | yes | yes | 跨 WT 集成场景，feature-completeness 和 related-influence 必须覆盖 |
| release-prep | yes | yes | 发布准备场景，所有 lane 必须覆盖 |
| 其他场景 | — | C1 + C2 mandatory，C3-C6 optional | 标准场景，仅核心 lane 为 mandatory |

**判定优先级**：

1. 先检查 milestone artifact 的 `composite_acceptance.review_depth` 是否显式声明为 `deep` 或 `standard`。若显式声明为 `deep`，所有 6 条 lane 为 mandatory；若显式声明为 `standard`，仍需检查是否命中不可降级 deep trigger。
2. 若 `composite_acceptance` 配置缺失，不得直接默认 deep。必须先基于 `target_type`、purpose、node_types、changed paths、risk boundary、acceptance criteria 与 known risks 分类当前 milestone。
3. 若分类命中上述 trigger table 中任一 deep trigger 场景，所有 6 条 lane 为 mandatory，并记录 `deep_review_reason`。
4. 若分类明确不命中 deep trigger，按 standard：C1 (code-review) + C2 (feature-completeness) 为 mandatory，C3-C6 为 optional。
5. 若配置缺失且目标/风险分类无法完成，返回 `blocked` 并记录 `questions_required`、`missing_inputs` 与 `composite_acceptance_config_missing: true`；不得为了保守而无证据扩大为 deep，也不得静默降级为 standard。

**判定记录**：无论是否命中 deep trigger，都必须在输出中记录 `deep_review_triggered`（true/false）和 `deep_review_reason`（命中场景或 `N/A`）。

## 硬约束

本技能特有约束：

1. **权限边界**：只读操作。消费现有的 per-WT lane 报告。禁止修改任何代码、禁止生成新的 review 内容、禁止重新执行代码检查。本轴聚合已有报告，不产生新的代码级发现。

2. **轴间隔离**：禁止接收或读取其他三轴（blackbox / whitebox / anticheat）的 verdict。如果输入包中注入了其他轴的 verdict 或判断，必须标记 `isolation_guarantee: false`，记录泄漏详情到 `isolation_leak_detail`，并在该约束被打破的条件下继续完成本轴检查（标记但不阻断——阻断交由 orchestrator 判定）。

3. **SubAgent 要求**：本技能设计为在隔离 SubAgent 上运行。当 SubAgent 不可用时，降级为 current-carrier 执行，但必须在输出中标记 `carrier_isolation_broken: true` 并记录 `carrier_isolation_broken_reason`。标记 `carrier: current-carrier` 的同时不得声称 `isolation_guarantee: true`。若声称已 spawned SubAgent，必须记录 `parent_runtime_dispatch_record_ref`、`spawned_subagent_record_ref`、`carrier_instance_id` 和 `isolation_boundary`。缺少这些 linkage 的 spawned-axis claim 必须标记为 ambiguous/non-pass；current-carrier 不得 masquerade 为 SubAgent，除非同时记录具体 runtime boundary violation。

4. **Lane fallback 记录**：如果某条 lane 无法由 SubAgent 执行而 fallback 到 current-carrier 或 human，必须记录该 lane 名称、fallback 类型和 fallback 原因。缺失 lane 且无 fallback 记录 → 该 lane 的 verdict 必须为 `blocked`。不得在无证据的情况下将缺失 lane 标记为 `pass`。

5. **Mandatory lane 强制**：如果 mandatory trigger table 判定某条 lane 为 mandatory，且该 lane 的 verdict 为 `blocked` 或缺失，则整体 `composite_verdict.verdict` 必须为 `blocked`，无论其他 lane 是否 pass。mandatory lane 的缺失不可被 optional lane 的 pass 补偿。

6. **不生成新检查**：本轴不执行代码审查、不运行测试、不扫描漏洞、不分析依赖。所有判断必须基于已有的 per-WT `composite_lane_record` 内容。如果某 lane record 不存在、状态为 `missing` / `incomplete` / `historical_gap` / `contaminated`，唯一合法行为是保留该状态并记录缺失——不得自行补充分析。本约束是本轴与其他三轴的本质区分：blackbox / whitebox / anticheat 可以生成新发现，composite 只能聚合已有 records。

7. **缺失配置不得盲目 deep**：当 `composite_acceptance` 配置缺失时，必须先做 target/risk classification。分类依据不足时返回 `blocked` / `questions_required`，而不是无条件 deep review。只有存在可引用 deep trigger 证据时，才允许将缺失配置场景升级为 deep。

8. **边界不重复**：C1 负责 independent review coverage，A6 负责 evidence credibility bias；C5 负责审计已有 operator path 证据，blackbox 负责生成和执行用户可观察行为/场景测试。Composite 不得用 C1/C5 复制 anticheat 或 blackbox 的主动检查职责。

9. **Lane verdict 审计链**：每条 lane 的 verdict 必须有明确的 `record_ref`、`lane_status` 和证据引用（`evidence_refs`）。不得给出无证据引用的 verdict。如果证据指向的文件路径与 WT 的 closeout record 不一致，必须标记并记录差异。

10. **Lane record 状态保真**：`captured` / `linked` 可作为候选 evidence；`missing` / `incomplete` / `historical_gap` / `contaminated` 必须作为 non-pass evidence 保留；`not_applicable` 必须保留 reason，且不能贡献 positive evidence。禁止从 prose closeout summary、旧 composite paragraph 或 milestone summary 后验合成 `composite_lane_record`。

11. **输出协议**：先生成完整的 checklist_results（6 条 lane 各自完整的 per-WT 评估），再提取 composite_verdict。空字段使用 `N/A` 或省略。重复上下文使用 artifact 引用，不得内联全文复制。

## 资源

- Milestone Gate 证据聚合合同 — §五 composite_lane_rules：composite acceptance lanes 在 milestone 级的消费规则和 veto power 定义。
- Composite Milestone Acceptance — composite acceptance 的 lane 定义、verdict model 和 fallback 规则。
- Composite Lane Evidence Records — `docs/harness/artifact/worktrack/composite-lane-records.md` 定义 per-WT lane record schema、status 语义和 closeout bundle link shape。
- milestone-gate-aggregation.md — Milestone Gate 聚合合同，定义 composite_lane_rules 和 Layer 2 聚合逻辑。本技能（composite lane check）是 Layer 2 的输入之一。
- milestone.md — Milestone artifact 合同，定义 aggregation_rules 字段和 composite_acceptance 配置。
- Skill 公共约束已内联于 §硬约束
- Single-Acceptance Verdict — per-WT 单体验收结果，定义 single-acceptance verdict 的结构化格式与判定规则。C2 (feature-completeness) lane 应消费其中的 `completion_signals_passed` / `completion_signals_failed` 字段作为预聚合证据。
