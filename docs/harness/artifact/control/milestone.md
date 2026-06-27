---
title: "Milestone Artifact"
status: active
updated: 2026-06-28
owner: servo-kernel
last_verified: 2026-06-28
---

# Milestone Artifact

> Milestone 是 `RepoScope` 下的聚合对象/控制条件/progress counter/environment probe。不创建第三 Scope，不接管 version management。

## 定位

- 属于 `RepoScope`，是 `Observe`/`Decide` 阶段的输入。
- 记录多个 worktrack 的聚合目标、完成阈值和验收边界。
- 不选择下一 Worktrack（`RepoScope.Decide` 的职责）。
- 不初始化 worktrack（`worktrack-init-skill` 的职责）。
- 不修改 version/release 状态。

## 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| milestone_id | string | 唯一标识 |
| title | string | Milestone 名称 |
| purpose | string | Milestone 目的描述 |
| status | enum | planned / active / completed / superseded |
| worktrack_list | array | 包含的 worktrack ID 列表及每个 worktrack 的预期状态 |
| completion_signals | array | 完成信号列表（可观察的事实） |
| acceptance_criteria | array | Milestone 级验收标准 |
| progress_counter | object | 进度计数器（total / completed / blocked / deferred） |
| environment_probe | object | [reserved] 预留字段，暂无操作语义 |
| aggregated_evidence | array | 聚合的 evidence 引用 |
| milestone_review_gate | object | Milestone 执行入口复核 Gate 的业务事实，包含 `milestone_review_count`、`latest_review_status`、`latest_review_checkpoint`、`review_invalidated_by` 与 `effective_review_pass` |
| composite_acceptance | object | goal-driven milestone 的复合验收证据引用与 verdict；字段合同见 [composite-milestone-acceptance.md](./composite-milestone-acceptance.md) |
| milestone_branch | string | Milestone integration branch 名称或 ref；用于聚合该 Milestone 下已通过 Worktrack closeout 的变更 |
| branch_baseline | object | Milestone branch 创建/同步基线，至少包含 `baseline_branch`、`baseline_ref`、`milestone_branch_head`、`last_synced_baseline_ref` |
| continuation_state | enum | `ready` / `waiting_external` / `paused_by_programmer` / `blocked`；表示当前 Milestone 是否可继续派生 Worktrack，不替代 `status` |
| pause_resume | object | 暂停、外部等待与恢复元数据，包含 `pause_reason`、`external_dependency`、`resume_condition`、`parallel_work_allowed`、`paused_baseline_ref`、`paused_branch_head` |
| release_version_consideration | string | 对 version/release 的提示（不接管 decision） |
| developer_decision_boundary | array | 标记哪些决定必须由 developer 做出 |
| depends_on_milestones | array | 前置 Milestone 列表 |
| aggregation_rules | object | Per-milestone 可配置的证据聚合规则；字段合同见 [milestone-gate-aggregation.md](./milestone-gate-aggregation.md)。未声明时默认使用退化 AND 并在 milestone gate evidence 中标记 `aggregation_rules_missing: true` |
| target_type | enum | Milestone Gate 目标类型：`program_code` / `non_program_artifact` / `mixed` / `unknown`。用于决定黑盒、白盒、反作弊与复合验收轴的适用性 |
| target_type_source | enum | `programmer_declared` / `milestone_artifact` / `gate_input` / `inferred_from_worktracks` / `unknown`。推断来源必须写入 evidence |
| gate_axis_applicability | object | Milestone Gate 四轴适用性声明；每轴包含 `state`、`expected_method`、`substituted_by`、`reason`，字段语义见 [milestone-gate-aggregation.md](./milestone-gate-aggregation.md#五target_type_rules目标类型与轴适用性) |
| gate_axis_reports | object | Milestone Gate 四个 sibling axis carrier 产出的显式报告引用与状态；每轴至少记录 `report_ref`、`axis_verdict`、`carrier`、`runtime_dispatch_profile`、`isolation_guarantee`、`carrier_isolation_broken` 与缺失/污染状态 |
| gate_axis_dispatch_profile | object | 顶层 Harness 四轴分派画像；记录 `dispatch_owner: top_level_harness`、`dispatch_model`、per-axis delegation attempts、same-carrier fallback、runtime gap 和隔离破坏事实 |
| updated | date | 最后更新时间 |
| `priority` | integer | Pipeline 中的优先级（数值越小优先级越高） |
| `activation_rules` | string | 自动激活条件（optional，harness-inferred）；描述 harness 可自动激活的前提，空值表示仅 manual |
| `created_by` | enum | `programmer` / `harness` — 创建来源 |
| `milestone_kind` | enum | `goal-driven` / `work-collection` — milestone 类型，默认 `goal-driven` |
| `completion_threshold_pct` | integer | goal-driven milestone 的完成阈值百分比，默认 `100`；仅当 `signal_satisfaction_pct` 与 `criteria_pass_pct` 均达到该阈值时，`purpose_achieved == true` |
| `milestone_task_complexity_assessment` | object | 任务复杂度评估结构化字段，由 milestone-pre-intake-skill 产出；缺失时等同于 blocked |

## Milestone Task Complexity Assessment

`milestone_task_complexity_assessment` 是 milestone-pre-intake-skill 产出的结构化复杂度评估，写入 Milestone artifact 并被 downstream consumers（harness-skill、milestone-init-skill、milestone-status-skill）消费。它以固定字段集量化 Milestone 的风险、范围和不确定度，为入口守卫和阻断决策提供结构化依据。

### 字段定义

| 字段 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `assessment_required` | boolean | yes | 本轮是否需要复杂度评估；`false` 仅用于 intake_skipped 场景 |
| `overall_complexity` | enum | yes | `low` / `medium` / `high` / `very-high` |
| `scope_clarity` | enum | yes | `low` / `medium` / `high` — 需求和边界的清晰度 |
| `worktrack_count_estimate` | integer | yes | 预估 worktrack 数量 |
| `worktrack_split_confidence` | enum | yes | `low` / `medium` / `high` — 拆分可信度 |
| `unknowns_level` | enum | yes | `low` / `medium` / `high` — 未知项程度 |
| `integration_risk` | enum | yes | `low` / `medium` / `high` — 集成风险 |
| `validation_cost` | enum | yes | `low` / `medium` / `high` — 验证成本 |
| `permission_or_external_side_effect_risk` | enum | yes | `low` / `medium` / `high` — 权限/外部副作用风险 |
| `documentation_governance_cost` | enum | yes | `low` / `medium` / `high` — 文档与治理成本 |
| `recommended_route` | enum | yes | `normal_milestone_with_required_intake` / `lightweight_intake_only` / `complex_project_entry_gate_required` / `discovery_or_reinforcement_needed` |
| `discovery_or_reinforcement_needed` | boolean | yes | 是否需要先执行发现/强化 milestone |
| `rationale` | array[string] | yes | 复杂度评级的理由说明 |

### Lightweight vs Full 评估

| 维度 | Full（goal-driven） | Lightweight（work-collection） |
|------|---------------------|-------------------------------|
| 触发条件 | 所有 goal-driven milestone 必须 full | work-collection milestone 可使用 lightweight |
| 必选字段 | 全部字段必选 | 仅 `overall_complexity`、`worktrack_count_estimate`、`recommended_route` 必选；其余标记为 `N/A` |
| 阻断行为 | 缺失必选字段 → blocked | 缺失必选字段 → blocked（lightweight 也有最低字段集） |
| `discovery_or_reinforcement_needed` | 必须判定；true 时阻断实现型 Milestone create/activate/derive worktrack | 不适用，默认 `false` |

### 阻断语义（Blocking Semantics）

本字段合同是所有 downstream consumer 的统一阻断依据。以下情况均视为 blocked，不得创建/激活/派生 worktrack：

1. **缺失 assessment**：milestone artifact 不含 `milestone_task_complexity_assessment` → blocked（不得推断为 ready）
2. **required 字段不全**：任一必选字段缺失或空值 → 等同于缺失 assessment（blocked）
3. **discovery_or_reinforcement_needed = true**：必须路由到 reinforcement documentation / project-understanding milestone，不得 create/activate implementation-oriented milestone
4. **recommended_route 与其他字段矛盾**：如 overall_complexity=very-high 但 recommended_route=lightweight → blocked，需 programmer 审查
5. **保守运行时回填**：旧 `.servo/milestone/*.md` 缺少该字段时，backfill 为 `assessment_required: false`（intake_skipped 默认值），其他字段按 `missing` / `blocked` / `N/A` 处理，不得解释为 ready

Guard terms: conservative runtime backfill must not grant permissions, must not infer programmer confirmation, must not increment counters, and must not enable Worktrack Init/Dispatch.

## Milestone 类型分化

`milestone_kind` 决定 milestone 的验证模型与生命周期行为：

| 维度 | goal-driven | work-collection |
|------|------------|----------------|
| 创建来源 | programmer（或 programmer 确认后的 harness） | harness 自动创建 |
| purpose | programmer 定义，有语义含量 | `"工作集合 {milestone_id}"`（无特异性） |
| completion_signals | programmer 定义 | 自动生成 = worktrack_list 逐条映射 |
| acceptance_criteria | programmer 定义 | 空（不适用） |
| completion_threshold_pct | programmer 定义，默认 `100` | 声明跳过（不适用） |
| 验收模型 | 双重验收（worktrack_list_finished + purpose_achieved；`purpose_achieved` 前置 Milestone Gate） | 单重验收（仅 worktrack_list_finished） |
| purpose_achieved 判定 | 逐 signal/criterion 验证；`signal_satisfaction_pct` 与 `criteria_pass_pct` 均需 `>= completion_threshold_pct` | 声明跳过，验收下沉到各 worktrack 的 Gate |
| completed 后行为 | handback 等 programmer 验收 | 自动完成，不触发 handback |
| pipeline 优先级 | 按 priority 字段 | 始终最低，不阻塞 goal-driven milestone |
| 生命周期 | 完整四态（planned → active → completed → superseded） | 同四态，但 completed 后自动 superseded |

## Entry Gate

对于复杂项目、弱文档、高风险操作或跨系统 milestone，goal-driven milestone 在 create / upsert / activate 或派生首个 Worktrack 前，必须先消费 [Complex Project Entry Gate](../repo/complex-project-entry-gate.md)。该 gate 是 Milestone-side blocking gate，不是固定 heavy mode；canonical guard term: not fixed heavy mode。低风险小请求可记录 `entry_verdict = not_applicable` 后轻量跳过。

`complex_project_entry_gate` 至少要把 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与 `reinforcement_milestone_recommendation` 暴露给 downstream skill。scanner output is evidence, not verdict；scanner 阈值和信号只作为 LLM / reviewer 判定依据，不把启发式输出写成 truth。

unresolved gate blocking default: missing, blank, placeholder, pending, or incomplete gate 不能解释为 `clear` 或 `not_applicable`；必须保持 milestone create / upsert / activate / derive-worktrack 阻断，直到 programmer confirmation 或 verified evidence 存在。

当 `entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true`、`blocks_implementation_until_resolved = true` 或 `blocked` 时，implementation-oriented milestone 不得继续 activate 或 derive Worktrack。弱文档命中时，默认建议新增 reinforcement documentation / project-understanding milestone，而不是把未确认理解写入当前 milestone truth。`reinforcement_milestone_recommendation` 至少携带 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`。

Worktrack execution modes `normal`、`autoreview`、`yolo` 仍属于 WorktrackScope / user safety policy，不替代 Milestone-side blocker。

## Milestone Review Gate

`milestone_review_gate` 是 goal-driven milestone 在进入 Worktrack 初始化或执行前的执行入口复核记录。它解决的是“当前 milestone brief 是否已经经过至少一次有效的 pre-milestone intake 复核”，不替代 Complex Project Entry Gate、Milestone Gate 或 Final Acceptance。

业务事实归属 Milestone artifact，控制路由状态归属 Control State：

- Milestone artifact 持久保存 `milestone_review_count`、`latest_review_status`、`latest_review_checkpoint`、`latest_reviewed_at`、`latest_review_ref`、`review_invalidated_by` 与 `effective_review_pass`。
- Control State 只保存当前 active milestone 的 review gate routing state，例如 `active_milestone_review_gate_status`、`active_milestone_review_count`、`active_milestone_review_checkpoint`、`active_milestone_review_required` 和 `active_milestone_review_blockers`。
- `milestone_review_count >= 1` 且 `latest_review_status = effective_pass` 且 `effective_review_pass = true` 才能视为有效 review pass。
- `skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全都不是有效 review pass；不得把 skipped/questions_required/blocked intake 当成 pass。
- `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化时，必须写入 `review_invalidated_by`，并把 `latest_review_status` 视为 `invalidated`，直到新的 milestone-pre-intake-skill review 产生 fresh checkpoint。
- `milestone_review_gate_handoff` 是 `pre_milestone_intake_review` 到 Milestone artifact 的结构化交接对象；review checkpoint 应引用该 handoff 的稳定摘要或输入指纹；缺失 checkpoint 时不得进入 Worktrack Init/Dispatch。

Conservative runtime backfill applies when older `.servo/milestone/*.md` artifacts lack additive `milestone_review_gate` fields. Missing additive fields must default to `missing`, `false`, `unknown`, `0`, `N/A`, `blocked`, or `not ready`: `milestone_review_count = 0`, `latest_review_status = missing`, `effective_review_pass = false`, `latest_review_checkpoint = N/A`, and `review_invalidated_by` treated as blocking until verified. Backfill must be forward-only, preserve existing observed facts, avoid broad historical rewrites, and must not infer programmer confirmation, grant permissions, increment review counters, or create an `effective_pass`.

Guard terms: conservative runtime backfill must not grant permissions, must not infer programmer confirmation, must not increment counters, and must not enable Worktrack Init/Dispatch.

该 gate 只阻断 milestone 进入 Worktrack 工作，不自动改变 milestone purpose、验收标准或 final acceptance 结论。

## Milestone Gate Target Type And Axis Reports

`target_type` 是 goal-driven milestone 的 Milestone Gate 前置路由字段。它回答“这个 milestone 最终交付物是什么类型”，从而决定黑盒、白盒、反作弊与复合验收轴应该如何取证。该字段不创建第三 Scope，不替代 `milestone_kind`，也不替代 Worktrack Contract。

Milestone Gate 的四轴执行由顶层 Harness 扁平化分派。`milestone-gate` skill 只消费顶层 Harness 提供的 `gate_axis_reports` 并运行 aggregation；它不得在自身内部继续唤起 blackbox/whitebox/anticheat/composite SubAgent。这样可以避免依赖某个 SubAgent 是否还能继续创建子 SubAgent。

`gate_axis_dispatch_profile` 是执行隔离事实，不是验收结论。它至少记录：

- `dispatch_owner: top_level_harness`
- `dispatch_model: sibling_axis_carriers | current_carrier_fallback | missing`
- `delegation_attempted_by_axis`
- `carrier_isolation_broken_any`
- `same_carrier_cross_axis`
- `dispatch_gap_reason`

`gate_axis_reports` 是 `milestone-gate` 的正式输入。每轴至少记录：

- `axis`: `black_box` / `white_box` / `anti_cheat` / `composite`
- `report_ref`
- `axis_verdict`
- `target_type`
- `axis_applicability_state`
- `expected_method`
- `carrier`
- `runtime_dispatch_profile`
- `isolation_guarantee`
- `carrier_isolation_broken`
- `checklist_results`
- `missing_evidence`

缺失 axis report、same-carrier 四轴污染、运行时无法证明 sibling carrier、或 `carrier_isolation_broken_any: true` 时，Milestone Gate 不能声明真实 pass。程序员可以在 final acceptance 阶段手动接受一个 blocked Gate 作为 override，但该 override 必须记录为 `milestone_acceptance_verdict: accepted_with_manual_exception` 或等价字段，不得把 `milestone_gate_verdict` 改写成 `pass`。

Canonical values:

| target_type | 适用场景 | Milestone Gate 路由 |
|-------------|----------|---------------------|
| `program_code` | 可运行程序、CLI、API、库、adapter、脚本、前端/后端功能、测试工具等会产生运行时行为的目标 | blackbox 必须使用外部可观察行为场景；whitebox 必须使用结构/内部实现分析；anti-cheat 与 composite 仍按证据可信度和复合验收执行 |
| `non_program_artifact` | 文档、治理规则、skill 文本、workflow policy、研究报告、计划或其他非运行时代码交付物 | 不强制作软件运行测试；blackbox/whitebox 可声明 `substituted` 或 `not_applicable`，并使用 artifact review、policy conformance、reader/operator simulation、professional review 等替代验收 |
| `mixed` | 同一 milestone 同时包含可运行程序和非程序 artifact | 必须按 worktrack 或 completion signal 拆分适用性；不能把整项 milestone 一概视为 program 或 non-program |
| `unknown` | 目标类型缺失、矛盾或证据不足 | Milestone Gate 不得把任何轴默认为 pass；必须记录 `blocked`、`needs_programmer_review` 或 conservative fallback |

`gate_axis_applicability` 记录四轴适用性。每个轴的 `state` 只能是：

- `applicable`: 该轴按自身语义执行并产出 verdict。
- `not_applicable`: 该轴对当前 target type 不适用；必须写明原因，且不能被聚合器当成 pass。
- `substituted`: 该轴的软件测试语义被 artifact-appropriate 验收替代；必须写明 `substituted_by`、替代方法和证据引用。
- `blocked`: 目标类型或输入不足，无法合法判定适用性。

Program/code target 的最低约束：

- blackbox 轴必须从外部用户/调用者可观察行为出发，构造或引用 scenario acceptance；不得阅读完整实现代码来补判断。
- whitebox 轴必须从内部结构、控制流、数据流、接口拼接、状态传递、依赖关系或架构路径等结构性证据出发；需要读取实现代码时由 whitebox 负责。

Non-program target 的最低约束：

- 不得为了模拟软件工程术语而强制运行不存在的程序测试。
- 替代验收必须贴合 artifact 类型，例如文档可读性/完整性审查、governance rule conformance、operator simulation、cross-reference validation、professional review 或 research evidence review。
- `not_applicable` 和 `substituted` 都是适用性状态，不是成功 verdict。聚合器必须分别记录它们，并检查替代证据是否满足该 milestone 的 acceptance criteria。

Non-program substitute acceptance 的最低证据合同：

| substitute_method | 适用 artifact | 最低证据 |
|-------------------|---------------|----------|
| `artifact_acceptance_review` | 文档、skill 文本、workflow policy、计划 artifact | 对照 purpose / completion signals / acceptance criteria 的覆盖记录，列出满足项、缺口和阻断项 |
| `policy_conformance` | governance rule、运行协议、adapter/deploy 规则文本 | 指向被检查规则和承接文档，说明目标 artifact 是否符合必须/不得/例外条件 |
| `reader_operator_simulation` | 面向人类或 operator 执行的说明、runbook、skill 提问交互 | 从外部读者或 operator 视角走读预期流程，记录可理解性、可执行性、歧义和失败点 |
| `cross_reference_validation` | 含路径、链接、字段名或上下游引用的 artifact | 验证引用目标存在、语义未漂移，并记录不再有效的引用 |
| `traceability_review` | completion signal、acceptance criteria、worktrack evidence 的映射 | 逐项把完成信号/验收标准映射到具体章节、字段或 evidence ref；缺口不得被 `substituted` 掩盖 |
| `professional_review` | 需要领域判断的研究报告、策略、交互设计或复杂治理文本 | 记录 reviewer 视角、判断依据、结论和残留风险；不能只写“已审查” |
| `research_evidence_review` | 研究结论、外部事实、方案比较 | 记录来源质量、证据边界、反例/限制和结论是否足以支撑 milestone purpose |
| `artifact_structure_review` | 结构化文档、schema、字段合同、skill 输出合同 | 检查结构完整性、字段一致性、术语一致性、内部引用和上下游接口拼接 |

`substituted` 只有在同时满足以下条件时，才可被 `axis_satisfied` 视为满足：

- `substitute_method` 属于 artifact-appropriate 方法，并与该 axis 的 `expected_method` 匹配。
- `substitution_evidence_ref` 指向具体 evidence、文件章节、命令输出或 reviewer 记录。
- `substitute_verdict = pass`，且 evidence 明确覆盖对应 completion signal 或 acceptance criterion。
- evidence 中保留未覆盖项、残留风险和 reviewer/operator 视角，不把“未运行软件测试”写成 pass。

`not_applicable` 只能说明某个软件测试轴对目标类型不适用。它可以从 mandatory pass calculation 中移除该轴，但不能产生正向完成证据；对应 completion signal 仍必须由 composite、professional review、artifact review 或其他适配方法证明。

Mixed target 的最低约束：

- 必须记录 slice-level coverage，最小粒度可以是 worktrack、completion signal、artifact component 或交付物路径。
- 每个 slice 至少记录 `slice_id`、`slice_target_type`、适用 axis、`axis_applicability_state`、`substitute_method` 或正常测试方法、`evidence_ref` 与 verdict。
- program_code slice 仍使用真实黑盒场景和白盒结构/内部分析；non_program_artifact slice 使用替代验收；不得用某一类 slice 的 pass 覆盖另一类 slice 的缺证。

## 生命周期

Milestone 的 primary lifecycle status 仍只有四个状态：

```
planned ──→ active ──→ completed
  │                        │
  └──────→ superseded ←────┘
```

- **planned**: 已创建，尚未激活。等待前置 milestone 完成或 programmer 手动激活。
- **active**: 当前正在推进，worktrack 执行中。同一时刻仅允许一个 active milestone。
- **completed**: 目的达成（goal-driven: `worktrack_list_finished == true`，且 `Milestone Gate == pass`，且 `purpose_achieved == true`；work-collection: `worktrack_list_finished == true`）。验收通过后由 `harness-skill` 执行状态转移。
- **superseded**: 被更新的 milestone 替换（programmer override），保留历史但不参与激活队列。work-collection milestone 在 completed 后自动标记为 superseded。

### Continuation State

暂停、外部等待或人工暂停不是新的 lifecycle status，不得写成 `status: suspended`。这些语义由 `continuation_state` 和 `pause_resume` 表达：

- `ready`: Milestone 当前可由 RepoScope.Decide 选择下一个 Worktrack。
- `waiting_external`: Milestone 目标仍有效，但当前推进依赖外部输入或非 repo-local 事实，例如实验室标注结果、第三方审核或外部环境完成。若 `parallel_work_allowed: true`，Harness 可在记录暂停证据后释放 active slot 并激活其他 planned milestone；同一时刻仍只能有一个 primary `active` milestone。
- `paused_by_programmer`: programmer 明确暂停当前 Milestone。恢复前必须消费 `resume_condition` 并刷新 baseline / branch head。
- `blocked`: 当前 Milestone 存在阻断，不能继续派生 Worktrack；需要 Recover、调整 scope、追加 worktrack 或 programmer 决策。

`continuation_state` 是 Milestone 当前可继续性的正交维度，不改变 `planned / active / completed / superseded` 计数，也不进入 milestone-history。消费者必须先看 primary `status`，再看 `continuation_state` 判断能否派生 Worktrack。

### Milestone Branch

Milestone branch 是该 Milestone 的 integration branch，不是第三 Scope，不替代 Worktrack branch，也不是随手开发分支。建议命名为 `ms/{milestone_id}-{slug}`，具体 slug 规范由初始化/分支策略实现定义。

Milestone branch 的职责：

- 从 servo-managed `baseline_branch` 创建。
- 接收该 Milestone 下 Worktrack closeout 的 merge。
- 在进入或恢复 Milestone 时，同步当前 baseline，默认通过 merge baseline into milestone branch 记录同步，而不是对已共享/已记录的 runtime branch 做 rebase 或 force-push。
- 仅在 goal-driven Milestone final acceptance 后合回 servo-managed baseline branch。

Worktrack 实现仍必须在独立 Worktrack branch 中完成。Milestone branch 只接收 Worktrack closeout merge 和 baseline sync merge；直接在 Milestone branch 上做实现改动必须由对应 Worktrack Contract 明确批准，否则视为范围漂移。

典型字段：

```yaml
milestone_branch:
  name: "ms/MS-YYYYMMDD-NNN-slug"
  role: "integration"
  source_baseline_branch: "develop"
  source_baseline_ref: "develop@<hash>"
  head_ref: "ms/...@<hash>"
  last_synced_baseline_ref: "develop@<hash>"
  sync_strategy: "merge-baseline-into-milestone-branch"
  final_merge_target: "develop"
```

暂停/恢复字段：

```yaml
continuation_state: "waiting_external"
pause_resume:
  paused_at: "ISO-8601"
  paused_by: "programmer|harness-skill"
  pause_reason: "等待实验室完成数据标注"
  external_dependency:
    owner: "lab"
    expected_input: "标注结果"
    handoff_ref: "batch-or-report-ref"
  resume_condition: "标注结果返回并通过完整性检查"
  parallel_work_allowed: true
  paused_baseline_ref: "develop@<hash>"
  paused_branch_head: "ms/...@<hash>"
```

若 `parallel_work_allowed: true` 且 programmer 或 Milestone policy 允许切换，Harness 可将该 Milestone 从 active slot 中移出并激活另一个 ready planned Milestone；恢复时必须从 RepoScope.Observe 开始，比较 `paused_baseline_ref`、`paused_branch_head` 和当前 baseline，再决定 sync、recover 或重新初始化 continuation Worktrack。

## Pipeline 语义

Milestone 作为 Pipeline 中的节点，遵循以下规则：

- 多个 milestone 可同时处于 `planned` 状态，按 `priority`（升序）排列激活顺序
- 同一时刻仅允许一个 `active` milestone
- 等待/暂停的 Milestone 不通过新增 primary status 表达；live backlog 中仍只使用 `planned` / `active`，并用 `continuation_state` / `pause_resume` 暴露可继续性
- `depends_on_milestones` 中的所有前置 milestone 必须为 `completed` 或 `superseded`，当前 milestone 才可激活
- milestone 完成后（`active` → `completed`），pipeline 按优先级自动选择下一个满足条件的 `planned` milestone 激活
- work-collection milestone（`milestone_kind == "work-collection"`）的 priority 始终视为最低，不阻塞 goal-driven milestone 的激活
- `priority` 同值时按 `updated` 时间排序
- `activation_rules` 非空时，harness 可在满足描述的条件后自动激活；空值表示需 programmer 显式审批
- goal-driven milestone 在 `planned` → `active` 前，harness 必须先输出结构化激活 brief 并等待 programmer 确认；work-collection milestone 可继续按既有自动激活语义推进
- 对命中 complex-project trigger 的 goal-driven milestone，激活 brief 之前还必须先清空 `complex_project_entry_gate.milestone_blocking_decision` 中的阻断项
- goal-driven milestone 在派生首个 Worktrack 前，必须满足 Milestone Review Gate：至少一次 `effective_pass` 的 `pre_milestone_intake_review`，且 review checkpoint 未被 `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化失效

完整 Pipeline 编排规则（upsert 语义、tie-breaker、激活顺序）以 [milestone-backlog.md](../repo/milestone-backlog.md#Pipeline 语义) 为权威源。

## Final Acceptance 写回事务

goal-driven milestone 的 `completed` 写入分两层理解：

- `milestone-status-skill` 输出 `milestone_acceptance_verdict == achieved` 且 `milestone_gate_verdict == pass`，表示该 milestone 已达到可交给 programmer final acceptance 的状态。
- `milestone_gate_verdict != pass` 时，自动路径不得把 milestone 视为 achieved。若 programmer 明确选择带例外接受，写回的是 `milestone_acceptance_verdict: accepted_with_manual_exception`（或等价 final acceptance override），并必须保留 `milestone_gate_verdict`、`accepted_gate_verdict_preserved_as`、`manual_exception.reason` 和相关 axis/anti-cheat findings。
- programmer 明确接受后，`harness-skill` 才执行 final acceptance writeback，把验收事实持久化为 runtime control-plane 状态。

final acceptance writeback 是一个逻辑事务，不是只改某一个文件。事务最小写入集合包括 `.servo/milestone/{milestone_id}.md`、`.servo/repo/milestone-backlog.md`、`.servo/repo/milestone-history.md`、`.servo/control-state.md`，必要时还包括 `.servo/repo/worktrack-backlog.md` 中对应 worktrack 状态的归一化。写回前必须校验输入状态，写回后必须复核 artifact 一致性；失败时进入 `writeback_incomplete` / `milestone_pipeline_stale` 阻塞，不得把 milestone 伪装成已完成。

Manual exception 不改变证据层含义。尤其是反作弊轴发现的 evidence reuse、gate bypass、same-carrier contamination、stale checkpoint 或 self-review bias，不能因为 programmer 接受 milestone 而被从 Gate report 中删除、降级或改写为 pass。后续 status/cleanup/history 读者必须能同时看到：原始 Gate verdict、人工接受原因、被保留的 anti-cheat finding 和任何 follow-up milestone/worktrack 引用。

## Latest Override 语义

同一 `milestone_id` 的写入遵循 latest-override：

- 以 `updated` 时间戳为判断依据：更新的写入覆盖旧数据
- programmer 和 harness 均可写入，同时间戳 programmer 优先
- `superseded` 状态是 override 的一种形式：创建新 milestone 时可标记旧 milestone 为 superseded

## 标准稳定性规则

- 修改 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct` 时，视为 milestone 完成合同被改写；harness 必须将此前的 `purpose_achieved` 结论视为失效，并触发 milestone 重新评估。
- 追加 worktrack 到 `worktrack_list` 不自动触发 milestone 重新评估，前提是 harness 已确认该 worktrack 归属当前 milestone 的 `purpose`/`completion_signals`/`acceptance_criteria`。
- 若追加的 worktrack 不归属当前 milestone，harness 应建议 programmer 将其归入其他现有 milestone，或创建新的 milestone；不得通过放宽当前 milestone signals/criteria 来静默吸收。

## 激活前规划简报

goal-driven milestone 在激活前，harness 必须向 programmer 输出结构化 brief，最少包含：

- `goal` / `purpose`
- `completion_signals`
- `acceptance_criteria`
- `worktrack_list`
- `completion_threshold_pct`
- `depends_on_milestones`
- `activation_reason`
- `developer_decision_boundary`

brief 发出后，harness 必须等待 programmer 确认，方可执行 `planned` → `active`。该确认是激活边界，不引入第三 Scope。work-collection milestone 可输出同结构 brief 作为可观察性信息，但不阻塞其自动激活语义。

## 验收模型

Milestone 验收模型由 `milestone_kind` 决定：

### goal-driven：双重验收模型

goal-driven milestone 完成判定必须满足以下顺序约束：

1. **worktrack_list_finished**: 声明的 worktrack 列表已完成 / 被明确移出 / 阻塞有决策
2. **Milestone Gate**: 所有声明的 worktrack 关闭后，先执行 milestone 级集成验证
3. **purpose_achieved**: Milestone 原始目的是否经聚合 evidence 证明达成

其中：

- `Milestone Gate` 是独立的 milestone 级验证层，最少包含 target-type-aware 黑盒验收、白盒验收、反作弊检测，以及 goal-driven milestone 的 [Composite Milestone Acceptance](./composite-milestone-acceptance.md) lanes。程序/代码目标使用真实黑盒行为场景和白盒结构/内部分析；非程序目标使用 artifact-appropriate 替代验收，并显式记录轴适用性。
- `signal_satisfaction_pct` = 已满足的 `completion_signals` 数 / 总 `completion_signals` 数。
- `criteria_pass_pct` = 已通过的 `acceptance_criteria` 数 / 总 `acceptance_criteria` 数。
- `purpose_achieved == true` 仅当 `signal_satisfaction_pct >= completion_threshold_pct` 且 `criteria_pass_pct >= completion_threshold_pct`。默认阈值 `completion_threshold_pct = 100`。

任一环节未通过时，不得自动判定 Milestone 完成。

### Milestone Gate 与 Worktrack Gate 的分层关系

- Worktrack Gate 位于 `WorktrackScope`，负责单个 worktrack 的 closeout 裁决。
- Milestone Gate 位于 `RepoScope` 的 milestone 验收路径中，只在相关 worktrack 全部关闭后运行，验证跨 worktrack 的集成结果。
- Milestone Gate 不回溯替代 Worktrack Gate；它消费各 worktrack Gate 产出的 evidence，并按 [Milestone Gate 证据聚合合同](./milestone-gate-aggregation.md) 中定义的 per-milestone 可配置 aggregation_rules 进行聚合——不是简单布尔 AND。
- 聚合规则覆盖证据权重（按 node_type 预设）、矛盾检测与 resolution protocol、composite acceptance lane 消费模式和退化 AND 的显式记录。
- 该分层仍属于既有 `RepoScope` / `WorktrackScope` 结构，不创建第三 Scope。

### 复合验收与 Final Acceptance

goal-driven milestone 在交给 programmer final acceptance 前，必须提供 composite acceptance report，或在 report 中记录每个 mandatory lane 的合法 fallback。复合验收最少覆盖：

- `code-review`
- `feature-completeness`
- `related-influence`
- `intent-completeness`
- `operator-simulation`
- `professional-review`

当 milestone 触及 release、installer/deploy、migration、authority、destructive operation、path governance、安全/隐私或跨 worktrack 集成时，必须使用 deep composite review。任一 required lane 为 `blocked`，或 `needs_followup_worktrack` 未经 programmer 明确接受为后续范围，均不得把 milestone 判为 final-acceptance-ready。

### work-collection：单重验收模型

work-collection milestone 完成判定仅需满足：

1. **worktrack_list_finished**: 声明的 worktrack 列表已完成 / 被明确移出 / 阻塞有决策

`purpose_achieved` 声明跳过（恒为 true），`completion_threshold_pct` 与 Milestone Gate 均不适用。验收下沉到各 worktrack 的 Gate——每个 worktrack 的 Gate 裁决结果即为其验收证据。Milestone 级不再追加深层语义验证。

## 与 Worktrack 的关系

- Milestone 引用 Worktrack，不控制 Worktrack 内部状态转移。
- goal-driven milestone 以逐 worktrack 聚合方式推进：RepoScope.Decide 每轮只能从 `worktrack_list` 中选出一个 `selected_worktrack_id` / current worktrack。每个 current worktrack 建立独立 branch、contract、plan-task-queue、gate evidence、closeout 和 repo-refresh 追踪，然后将结果汇入 milestone 聚合状态。
- `worktrack_list` 是 Milestone 级声明列表，不是执行队列；它可以记录多个 worktrack，但不得被解释成可一次 dispatch 的批量任务窗口。
- Milestone-level scheduler 一次只选择一个 Worktrack；Worktrack-level scheduler 才能在该 Worktrack 的 Plan / Task Queue task window 内规划多个 task。
- 新增、移除、重排或同时选择多个 worktrack 都是 Milestone / RepoScope 边界变更，必须回到 RepoScope.Decide，并在需要时触发 programmer approval。
- Worktrack closeout 后，Milestone progress counter 更新。
- 在 Milestone branch 模型下，Worktrack closeout 的集成目标可以是当前 Milestone branch；Milestone final acceptance 后再由 Milestone closeout 路径合回 servo-managed baseline branch。具体 Worktrack branch source 和 closeout target 由 Worktrack Contract 承接。
- 不替代 `WorktrackContract` 或 `PlanTaskQueue`。

## Candidate Recommendation Boundary

Milestone artifact 保存已经创建、激活或完成的 milestone truth；候选 Milestone recommendation 不是该 artifact 的 live truth，除非已经经过 programmer confirmation 并由 `milestone-init-skill` 写入。

RepoScope 可以在 pre-milestone 场景输出 candidate milestone brief，但该 brief 必须与 live artifact 区分：

- `candidate` 表示方向建议，不同于 `planned`、`active` 或 `completed`。
- candidate brief 必须携带 `observed_facts`、`inferred_assumptions`、`unknowns`、`primary_contradiction`、`main_aspect_now`、acceptance signals、risk boundary 和 programmer confirmation requirement。
- candidate brief 不得增加 `progress_counter`，不得占用 `worktrack_list`，不得触发 pipeline advancement。
- candidate brief 中列出的 candidate worktracks 是方向建议，不等同于 Worktrack Plan/Task Queue、task window 或执行队列。
- programmer 确认后，candidate brief 才能进入 milestone create / upsert / activate 路径；仍必须满足 Milestone Review Gate、Complex Project Entry Gate 和对应 init skill 的字段约束。

Milestone 是方向、目的、验收信号和聚合进度对象；Worktrack 是独立执行单元；Plan / Task Queue 是单个 Worktrack 内的任务窗口 / task window。三者不得互相替代。

## 与 RepoScope 的关系

- Milestone 是 `RepoScope.Observe` 的 sensor 输入。
- Milestone 完成/阻塞信号影响 `RepoScope.Decide` 的决策。
- Milestone 验收边界是 continuous execution 的合法 handback 点。

## 使用约定

- 由 programmer 或 `harness-skill`（`RepoScope.Decide` 阶段）创建。
  - goal-driven：由 programmer 定义（或 programmer 确认后的 harness 创建），purpose/signals/criteria 由 programmer 提供。
  - work-collection：由 harness 在无内聚任务场景下自动创建，名称格式 `工作集合 MS-YYYYMMDD-NNN`，priority 最低。
- 进度由 `milestone-status-skill` 独立分析。
- 不自动触发 release/publish/version bump。
