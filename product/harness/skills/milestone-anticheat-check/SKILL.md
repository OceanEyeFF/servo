---
name: milestone-anticheat-check
description: 当 Milestone Gate 进入四轴复合验收，且需要对当前 milestone 所有已闭环 WT 执行反作弊轴检查，以检测证据伪造、复用、绕过或偏倚信号时，使用这个技能。它是 Milestone Gate 四轴中的 anti-cheat lane，不评判代码正确性，只评判证据可信度。
---

# Milestone 反作弊轴检查技能

## 概览

本技能实现 Milestone Gate 四轴复合验收中的 **anti-cheat lane**（反作弊轴），对应 `milestone-gate-aggregation.md` 中定义的 `composite_lane_rules.lane_axes.anticheat`。它不评判代码是否正确，只评判**证据是否可信**。

本技能检查以下 7 个反作弊维度（A1-A7），针对当前 milestone 下所有已闭环的 worktrack，逐条检测 fake-pass 信号：

| ID | Pattern | 检查语义 |
|----|---------|---------|
| A1 | Mock abuse | 证据是否依赖 mock/stub/fake 而非真实集成路径 |
| A2 | Evidence reuse | 同一份证据是否被多个 WT 重复引用且缺乏独立验证 |
| A3 | Partial validation | 存在真实跨 WT 集成/共享行为/完成依赖时，WT 是否只做了自身范围验证 |
| A4 | Gate bypass | WT 是否跳过了标准 gate 步骤（self-review / gate evidence / closeout record） |
| A5 | Stale evidence | 证据是否来自过期基线（优先依据 source refs / checkpoint / observed hash） |
| A6 | Self-review bias | 同一载体或证据来源是否造成 evidence credibility bias |
| A7 | False positive risk | governance check 全 pass 但实际全部配置为 warning 而非 error |

当 `Harness` 处于 milestone composite acceptance 阶段，已收集该 milestone 所有已闭环 WT 的 single-acceptance verdict、gate evidence、closeout record、self-review record 与 dispatch profile，且需要产出 anti-cheat lane verdict 以供 `milestone-gate-aggregation` 的 composite verdict 综合时，使用这个技能。

这个技能设计为**隔离 SubAgent** 运行：它 MUST NOT 接收或消费其他轴（blackbox、whitebox、composite）的 verdict。若任何其他轴的结论被注入上下文，必须标记 `isolation_guarantee: false` 并记录泄露来源。

## 何时使用

当需要检测 milestone 级证据可信度风险时，使用这个技能：

- 当前 milestone 下至少有两个 WT 已闭环（`closeout record` 已写入）
- 已收集所有已闭环 WT 的 `single_acceptance_verdict`、`gate_evidence`、`closeout_record`、`self_review_record`
- 已获取所有已闭环 WT 的 `dispatch_profile`（谁执行、SubAgent 与否、什么模型）
- 当前 milestone 的 `aggregation_rules` 可用（若缺失，仅在 anti-cheat lane 记录 warning，不 block）
- 需要独立于其他三轴的隔离判定
- 在其他轴（blackbox / whitebox）运行的同时或之前均可执行，但不得消费其 verdict

## 工作流

1. 确认本轴隔离边界：确认上下文中没有其他轴（blackbox / whitebox / composite）的 verdict。若已泄露，先记录 `isolation_guarantee: false` 与泄露来源，再继续执行。
2. 载入当前 milestone 下所有已闭环 WT 的最小必要产物：
   - 每个 WT 的 `single_acceptance_verdict`（来自 `single-acceptance-contract.md`）
   - 每个 WT 的 `gate_evidence`（包含 implementation/validation/policy 三面证据路径与时效性标签）
   - 每个 WT 的 `closeout_record`
   - 每个 WT 的 `self_review_record`（来自 `self-review-contract.md`）
   - 每个 WT 的 `dispatch_profile`（carrier identity、SubAgent 标记、模型标识）
3. 载入当前 milestone 的 `aggregation_rules`（若声明），特别是 `composite_lane_rules.anticheat` 段。
4. 对 A1-A7 逐项执行反作弊检测。
5. 将每条检测结果归类为 `pass` / `soft_fail` / `hard_fail` / `blocked`，并记录对应的 `severity`、`evidence_refs` 和 `finding`。
6. 综合 7 项检测结果产出 `anticheat_verdict`。
7. 在综合前，确认没有跨轴泄露：若本轴上下文被注入了其他轴的 verdict，在 verdict 中显式记录。
8. 返回结构化 `anti-cheat lane report`。在 milestone gate 综合之前停止。

## 逐项检测细则

### A1 — Mock Abuse Detection

**检测目标**：判断 WT 的测试证据是否依赖 mock/stub/fake 而非真实集成路径。

**检测方法**：

1. 扫描每个 WT 的 `gate_evidence.validation` 中的证据文件路径。
2. 对每一份测试证据，搜索以下模式：
   - 关键词：`mock`、`stub`、`fake`、`test_double`、`fixture`、`pytest.fixture`（声明性 mock）、`@patch`、`unittest.mock`
   - 模式：测试只覆盖单元逻辑而无集成验证
3. 判定规则：
   - 若该 WT 的 node_type 是 `feature` 或 `release`，但所有测试证据都是 mock-based 且无线集成验证 → `hard_fail`
   - 若该 WT 的 node_type 是 `test`，mock 是测试本身的合理工具 → `pass`（需记录理由）
   - 若该 WT 的 node_type 是 `docs` 或 `demo`，mock 相关性低 → 标记为 `N/A`
   - 混合证据：有 mock 但也能证实存在真实集成测试 → `soft_fail`（记录 mock 面但不过度惩罚）

### A2 — Evidence Reuse Detection

**检测目标**：检测同一份证据是否被多个 WT 交叉引用而未独立验证。

**检测方法**：

1. 从所有 WT 的 `gate_evidence` 中提取 `evidence_refs` 列表。
2. 按证据路径或内容哈希去重。
3. 对任何被 2 个以上 WT 引用的证据路径：
   - 检查每个引用 WT 的 scope 是否真的与该证据相关
   - 若证据产生于 WT-A，被 WT-B 引用但 WT-B 的 scope 与该证据无直接关系 → `hard_fail`
   - 若证据是共享的 milestone 级 baseline（如 verifier 脚本），且各 WT 均独立运行之 → `pass`
6. 判定规则：
   - 存在至少一个不可解释的复用 → 至少 `soft_fail`
   - 存在 3 个以上不可解释的复用，或复用覆盖所有 critical WT → `hard_fail`
   - 无复用或所有复用均可解释 → `pass`

### A3 — Partial Validation Detection

**检测目标**：检测在存在真实跨 WT 集成、共享行为或完成依赖时，WT 是否仅在自身 scope 内验证，从未覆盖跨 WT 集成点。若 milestone 的 WT 彼此独立（如 docs-only、单模块、无共享行为/状态/接口、无完成依赖），A3 不应 hard-fail。

**检测方法**：

1. 先判定 `cross_wt_integration_required`，依据 WT contract、`completion_signals`、`impacted_modules`、changed paths、milestone purpose、`aggregation_rules` 与 closeout record。
2. 以下情况视为需要跨 WT 集成验证：
   - 某 WT 的 deliverable 依赖另一 WT 的输出、状态或接口。
   - 多个 WT 共同修改 shared interface、shared config、control state、canonical skill entrypoint、deploy path 或同一用户可观察 workflow。
   - milestone acceptance 明确要求 integrated workflow、end-to-end path、operator path 或跨 WT 行为。
   - closeout / gate evidence 明确声明 `merge_required`、`integration_target_ref` 或完成依赖。
3. 以下情况可以判定 `cross_wt_integration_required: false`：
   - 所有 WT 均为 docs-only 或彼此独立的单模块文本/配置调整。
   - WT 之间没有共享运行时行为、公共接口、共同入口、状态传递或完成依赖。
   - 每个 WT 的 acceptance signal 可在自身 scope 内被完整证明，且 milestone purpose 不要求集成路径。
4. 若 `cross_wt_integration_required: false`，A3 verdict 应为 `N/A` 或 `pass_with_rationale`，必须记录 rationale 与 source refs；不得因缺少跨 WT 引用直接 hard-fail。
5. 若 `cross_wt_integration_required: true`，再检查 gate evidence 是否包含可信跨 WT 集成引用、测试、smoke/dogfood 记录、operator path 证据或合并后验证。
6. 判定规则：
   - `cross_wt_integration_required: true` 且所有 WT 的 gate evidence 均只覆盖自身 scope，没有任何跨 WT 引用 → `hard_fail`
   - `cross_wt_integration_required: true` 且至少存在 1 个可信跨 WT 集成验证覆盖所有关键依赖 → `pass`
   - `cross_wt_integration_required: true` 但覆盖不完整或只覆盖低风险依赖 → `soft_fail`
   - 无法判定是否存在真实跨 WT 依赖 → `blocked`，记录缺失字段，不得默认 hard-fail
   - milestone 仅含 1 个 WT → `N/A`（无需跨 WT 验证）

### A4 — Gate Bypass Detection

**检测目标**：检测 WT 是否跳过了标准的 gate 步骤。

**检测方法**：

1. 对每个 WT，检查 closeout record 是否包含以下三段：
   - `self_review_record`（来自 self-review-contract.md）
   - `gate_evidence`（implementation / validation / policy 三面）
   - `closeout_gate_verdict`（worktrack-gate-skill 产出的 verdict）
2. 判定规则：
   - 任一 WT 缺失上述三段中任一段 → `hard_fail`
   - 所有 WT 三段完整 → `pass`
   - 某 WT 三段存在但内容为空或 N/A 填充且无合理解释 → `soft_fail`
3. 特别注意：若 closeout record 中 gate verdict 时间戳早于 evidence 时间戳，说明 gate 在 evidence 就绪前已执行 → `hard_fail`

### A5 — Stale Evidence Detection

**检测目标**：检测证据是否基于过期基线产生。A5 的主证据是 source refs、checkpoint refs、observed git hash、merge commit、closeout commit 与 milestone input checkpoint；文件系统 mtime 只能作为辅助信号，不得作为唯一 hard-fail 依据。

**检测方法**：

1. 获取当前 milestone 分支的 HEAD commit 与 `milestone_input_checkpoint`。
2. 获取每个 WT 的 `checkpoint_base_ref`、`observed_git_hash`、`closeout_commit`、`merge_commit`、evidence source refs 与 evidence freshness label。
3. 先比较 ref/hash 关系：证据声称覆盖的 commit 是否等于或包含当前 milestone 聚合所要求的 checkpoint。
4. 再比较 closeout/merge timeline：证据是否产生于 WT closeout 之前、merge 之前，或是否在后续 WT merge 后仍被错误标记为覆盖全 milestone。
5. 最后才使用文件系统 mtime 作为辅助交叉检查。mtime 与 ref/hash 冲突时，优先相信 git/source ref 并记录 mtime discrepancy。
4. 判定规则：
   - 任何 evidence 的 `observed_git_hash` / source ref 明确早于所声称覆盖的 checkpoint，且被标记为 `fresh` 或 full milestone coverage → `hard_fail`
   - evidence 只覆盖某 WT closeout commit，却被复用为后续 WT merge 后的 milestone-level fresh evidence → `hard_fail`
   - evidence 被标记为 `reused` 或 `mixed`，source refs 清楚但缺少后续刷新说明 → `soft_fail`
   - source refs / checkpoint / observed hash 与 freshness 标签一致 → `pass`
   - 缺少 ref/hash/source checkpoint 导致无法判断 → `blocked`，记录缺失字段
   - 仅文件 mtime 早于 milestone branch HEAD，但 ref/hash 能证明证据覆盖正确 checkpoint → 不得 hard-fail；记录 `mtime_auxiliary_only: true`

### A6 — Self-Review Bias Detection

**检测目标**：检测同一载体或证据来源是否同时承担实现、审查、gate 或证据生产角色，从而造成 evidence credibility bias。A6 关注的是证据可信度偏倚与 provenance 风险，不负责衡量独立 review 覆盖完整性；独立 review 覆盖由 composite C1 判定。

**检测方法**：

1. 从每个 WT 的 dispatch profile 中提取：
   - `implementer`：执行实现的 carrier identity（SubAgent 模型标识或 current-carrier 标记）
   - `reviewer`：执行 review evidence 的 carrier identity
   - `gate_judge`：执行 gate 裁决的 carrier identity
2. 检查是否存在以下重叠：
   - `implementer == reviewer` → `self-review overlap: true`
   - `implementer == gate_judge` → `self-gate overlap: true`
3. 判定规则：
   - 任一 WT 存在 `self-review overlap` 且该 self-review 被用作唯一可信度证据 → 至少 `soft_fail`
   - 同一 carrier 出现在该 milestone 下 3 个以上 WT 的 implementer 位置且从不出现在 reviewer 位置 → `pass`（专一角色，无偏倚）
   - 存在 `self-gate overlap` → `hard_fail`（gate 裁决必须独立）
   - 所有 WT 实现者与审查者严格分离 → `pass`
4. 输出格式：对每个检测到的 self-review 实例，记录 `self_review_findings`：

   ```yaml
   self_review_findings:
     - worktrack_id: "..."
       implementer: "..."
       reviewer: "..."
       overlap: true
       overlap_type: "self-review" | "self-gate"
   ```

**边界说明**：A6 可以报告 `self-review overlap`、`self-gate overlap`、`evidence_producer == reviewer`、同一 carrier 反复产出并审查同类证据等 provenance 风险；但不得因为缺少独立 reviewer 覆盖而单独 hard-fail。若问题是“有没有独立 review 覆盖每个 WT”，应在 composite C1 中判定，并在 A6 中只记录为相关背景或 `see_composite_C1`。

### A7 — False Positive Risk Detection

**检测目标**：检测 governance check 全 pass 但全部配置为 warning 而非 error 的虚假安全状态。

**检测方法**：

1. 检查该 milestone 下所有 WT 的 policy evidence（由 rule-check-skill 产出）。
2. 检查其中 governance check 的 severity 配置：
   - 若 governance check 结果全部为 `pass` 或 `soft_fail`，但进一步检查发现所有 rule 均配置为 `severity: warning`（而非 `error`）→ 系统性 false positive 风险
3. 判定规则：
   - 所有 governance rule 均为 `severity: warning` 且没有 `error` 级别 → `hard_fail`
   - 存在 `error` 级别的 governance rule 且全部通过 → `pass`
   - 部分 rule 为 `warning` 但存在至少 1 个 `error` 级 rule 通过 → `pass`
   - 无法确定 governance rule 的 severity 配置 → `soft_fail`（记录数据缺口）
4. 若 milestone 无 governance check 配置 → `N/A`

## 综合判定规则

7 项检测完成后，按以下规则产出整体 `anticheat_verdict`：

### 整体 verdict 推导

| 条件 | 整体 verdict |
|------|-------------|
| 任何单项为 `blocked`（且非 N/A） | `blocked` |
| 任何单项为 `hard_fail` | `hard_fail` |
| 任何单项为 `soft_fail` 且无 `hard_fail` 或 `blocked` | `soft_fail` |
| 全部 7 项均为 `pass` 或 `N/A` | `pass` |

### 整体 severity 推导

| 条件 | 整体 severity |
|------|--------------|
| 存在 `high` severity 单项 | `high` |
| 存在 `medium` severity 单项且无 `high` | `medium` |
| 全部为 `low` 或 `pass`/`N/A` | `low` |

### 与 milestone-gate-aggregation 的接口

根据 `milestone-gate-aggregation.md` 的 `composite_lane_rules`：

- 本 lane 的 `verdict` 作为 `lane_axes.anticheat.aggregate verdict` 输出
- 本 lane 有 `veto_power: true`：`hard_fail` 或 `blocked` → milestone blocked，无论其他轴结果
- 任何 `high` severity finding → 触发 `weight_modifier`：将对应 WT 的权重清零（cheating signal 使该 WT 失去对 milestone verdict 的贡献权重）

## 反作弊轴约定

每次运行本技能时，使用以下固定格式约定。

### 反作弊任务简报

- `轴标识`：`anti-cheat`
- `触发条件`：milestone composite acceptance 阶段，至少 2 个 WT 已闭环
- `目标`：检测当前 milestone 下所有已闭环 WT 的证据可信度风险
- `当前 milestone`：milestone_id
- `已闭环 WT 数量`：N
- `范围内`：A1-A7 全部 7 项检测
- `范围外`：代码正确性、功能验收、性能评估、安全性测试（属于其他轴）
- `隔离要求`：MUST NOT 接收其他轴 verdict
- `判定选项`：pass / soft_fail / hard_fail / blocked
- `完成信号`：7 项检测全部完成 + isolation_guarantee 已确认 + 结构化 verdict 已产出

### 反作弊信息包

- `milestone_id`
- `aggregation_rules`（若声明）
- `per_worktrack.single_acceptance_verdict`：N 个 WT 的 single-acceptance verdict 摘要
- `per_worktrack.gate_evidence`：N 个 WT 的 gate evidence 路径与时效性标签
- `per_worktrack.closeout_record`：N 个 WT 的 closeout record 路径
- `per_worktrack.self_review_record`：N 个 WT 的 self-review 记录
- `per_worktrack.dispatch_profile`：N 个 WT 的 carrier identity / SubAgent 标记 / 模型标识
- `milestone_branch_head_timestamp`：当前 milestone 分支 HEAD commit 时间戳
- `governance_check_severity_config`：governance check 的 severity 配置（rule-check-skill 产出）
- `已知风险`：提前标注的可能触发 A1-A7 的 WT 或 evidence

### 反作弊报告

- `轴标识`：`anti-cheat`
- `milestone_id`
- `检查时间戳`
- `carrier`：subagent | current-carrier
- `isolation_guarantee`：true | false
- `isolation_leak_detail`（若 `isolation_guarantee: false`）
- `carrier_isolation_broken`（若 SubAgent 不可用，当前载体运行时）
- `checklist_results`：A1-A7 逐项结果
- `self_review_findings`（若 A6 检测到 bias）
- `整体 anticheat_verdict`
- `整体 severity`
- `recommendation`：下一步建议（proceed / investigate / block）
- `已准备好进入 milestone gate 综合`

## 预期输出

使用本技能时，产出一份至少包含以下章节的 `反作弊轴检查报告`：

- `反作弊轴触发条件`
- `输入 WT 摘要`（N 个已闭环 WT 的 ID、verdict、node_type、closeout 时间戳）
- `A1 Mock Abuse 检测`
- `A2 Evidence Reuse 检测`
- `A3 Partial Validation 检测`
- `A4 Gate Bypass 检测`
- `A5 Stale Evidence 检测`
- `A6 Self-Review Bias 检测`
- `A7 False Positive Risk 检测`
- `综合 anticheat_verdict`
- `隔离保证声明`
- `返回 Milestone Gate 综合`

结果中至少应包含以下字段或等价表达：

- `轴标识`
- `milestone_id`
- `carrier`
- `isolation_guarantee`
- `checklist_results[].check_id`
- `checklist_results[].verdict`
- `checklist_results[].severity`
- `checklist_results[].evidence_refs`
- `checklist_results[].finding`
- `self_review_findings[].worktrack_id`
- `self_review_findings[].implementer`
- `self_review_findings[].reviewer`
- `self_review_findings[].overlap`
- `anticheat_verdict.axis`
- `anticheat_verdict.verdict`
- `anticheat_verdict.severity`
- `整体置信度`
- `整体置信度理由`
- `决定性证据`
- `缺失或冲突数据`
- `需要 upstream 路由`
- `路由理由`
- `已准备好进入 milestone gate 综合`
- `how_to_review`

## 硬约束

本技能特有约束：

1. **Permission boundary**：Read-only。可读取 evidence metadata、dispatch profiles、closeout records 和 aggregation_rules。MUST NOT 修改任何代码、evidence 或 control state。
2. **Isolation**：MUST NOT 接收或读取其他轴（blackbox、whitebox、composite）的 verdict。若另一轴 verdict 被注入上下文，必须标记 `isolation_guarantee: false` 并记录泄露来源（文件路径或注入方式）。隔离被破坏时，仍产出 verdict 但置信度降级为 `low`。
3. **SubAgent requirement**：设计为隔离 SubAgent 运行。当 SubAgent 不可用时，fallback 到 current-carrier 必须标记 `carrier_isolation_broken: true` 并降级置信度。在同一个 current-carrier 上下文中运行所有四轴的行为禁止发生 — 若检测到，必须返回 `blocked` 并标记 `cross-axis-contamination: true`。
4. **Anti-cheat is NOT code review**：本技能不评判代码正确性、性能、安全性或架构质量。它只评判证据的可信度。即使所有代码从技术角度正确，若检测到 fake evidence 信号，仍必须报告 `hard_fail` 且不可被其他轴覆盖。
5. **False positive handling**：若某条检测看起来命中反作弊 pattern 但存在可解释的合法理由（如 `A1` 中 test-type WT 合理使用 mock），其 verdict 应记录为 `pass` 并附带解释。不得压制检测结果或静默降级 — 合法理由必须显式记录在 `finding` 字段中。
6. **Stale evidence 时效性**：A5 的主判断依据是 source refs、checkpoint refs、observed git hash、merge commit、closeout commit 与 milestone input checkpoint；milestone 分支 HEAD 是目标基线，不是 main/master。若 milestone 分支在 WT closeout 之后有新的 commit（如另一个 WT 的 closeout），A5 应基于 ref/hash 关系解释时间线。文件系统 mtime 只能作为辅助信号，不得作为唯一 hard-fail 依据。
7. **Veto power 不可被稀释**：anti-cheat lane 有 veto_power，任何 `hard_fail` 或 `blocked` 必须导致 milestone gate 综合时为 `blocked`。per-WT aggregation 的 pass 不可覆盖 anti-cheat 的 hard_fail — 此行为由 `milestone-gate-aggregation.md` 保证，本技能只负责产出准确的 lane verdict。
8. **数据缺失不可视为通过**：若某 WT 缺失 `dispatch_profile`、`closeout_record` 或 `gate_evidence`，导致 A1-A7 中某项无法检测，该项 verdict 必须为 `blocked`（而非 `pass` 或静默跳过）。`blocked` 项必须显式暴露缺失数据及影响的 check_id。
9. **跨 WT 矛盾与 A2 的区别**：A2 检测证据复用但未独立验证。若两 WT 的 single-acceptance verdict 互相矛盾（如一个 pass 一个 hard-fail 但共享同一 evidence），A2 标记为复用风险，而矛盾本身应由 `contradiction_rules`（聚合规则的矛盾检测）处理。本技能不负责矛盾裁决 — 只负责指出证据复用可能掩盖了矛盾。
10. **输出格式**：整体 verdict 的唯一合法呈现形式是 `anticheat_verdict` yaml 格式（见上方）。将 A1-A7 压成一段模糊文字摘要的行为禁止发生。`finding` 字段必须包含具体证据路径、时间戳或 carrier identity — 不得使用笼统描述。

## 资源

- Milestone Gate 证据聚合合同 — 本技能消费的 aggregation_rules 与 composite_lane_rules 定义
- Worktrack Self-Review Contract — self_review_record 格式（A4 / A6 输入）
- Worktrack Single-Acceptance Contract — single_acceptance_verdict 格式（per-WT 输入）
- Gate Evidence — gate_evidence 格式与时效性标签定义（A1 / A2 / A5 输入）
- Skill 公共约束 — C-1 至 C-8 公共约束定义
- Runtime Dispatch Contract — dispatch_profile 字段定义（A6 输入）
