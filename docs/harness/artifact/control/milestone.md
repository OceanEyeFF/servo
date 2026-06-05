---
title: "Milestone Artifact"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
---

# Milestone Artifact

> Milestone 是 `RepoScope` 下的聚合对象/控制条件/progress counter/environment probe。不创建第三 Scope，不接管 version management。

## 定位

- 属于 `RepoScope`，是 `Observe`/`Decide` 阶段的输入。
- 记录多个 worktrack 的聚合目标、完成阈值和验收边界。
- 不选择下一 Worktrack（`RepoScope.Decide` 的职责）。
- 不初始化 worktrack（`init-worktrack-skill` 的职责）。
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
| release_version_consideration | string | 对 version/release 的提示（不接管 decision） |
| developer_decision_boundary | array | 标记哪些决定必须由 developer 做出 |
| depends_on_milestones | array | 前置 Milestone 列表 |
| updated | date | 最后更新时间 |
| `priority` | integer | Pipeline 中的优先级（数值越小优先级越高） |
| `activation_rules` | string | 自动激活条件（optional，harness-inferred）；描述 harness 可自动激活的前提，空值表示仅 manual |
| `created_by` | enum | `programmer` / `harness` — 创建来源 |
| `milestone_kind` | enum | `goal-driven` / `work-collection` — milestone 类型，默认 `goal-driven` |
| `completion_threshold_pct` | integer | goal-driven milestone 的完成阈值百分比，默认 `100`；仅当 `signal_satisfaction_pct` 与 `criteria_pass_pct` 均达到该阈值时，`purpose_achieved == true` |

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
- `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化时，必须写入 `review_invalidated_by`，并把 `latest_review_status` 视为 `invalidated`，直到新的 pre-milestone-intake-skill review 产生 fresh checkpoint。
- `milestone_review_gate_handoff` 是 `pre_milestone_intake_review` 到 Milestone artifact 的结构化交接对象；review checkpoint 应引用该 handoff 的稳定摘要或输入指纹；缺失 checkpoint 时不得进入 Worktrack Init/Dispatch。

Conservative runtime backfill applies when older `.servo/milestone/*.md` artifacts lack additive `milestone_review_gate` fields. Missing additive fields must default to `missing`, `false`, `unknown`, `0`, `N/A`, `blocked`, or `not ready`: `milestone_review_count = 0`, `latest_review_status = missing`, `effective_review_pass = false`, `latest_review_checkpoint = N/A`, and `review_invalidated_by` treated as blocking until verified. Backfill must be forward-only, preserve existing observed facts, avoid broad historical rewrites, and must not infer programmer confirmation, grant permissions, increment review counters, or create an `effective_pass`.

Guard terms: conservative runtime backfill must not grant permissions, must not infer programmer confirmation, must not increment counters, and must not enable Worktrack Init/Dispatch.

该 gate 只阻断 milestone 进入 Worktrack 工作，不自动改变 milestone purpose、验收标准或 final acceptance 结论。

## 生命周期

Milestone 在其生命周期中经历四个状态：

```
planned ──→ active ──→ completed
  │                        │
  └──────→ superseded ←────┘
```

- **planned**: 已创建，尚未激活。等待前置 milestone 完成或 programmer 手动激活。
- **active**: 当前正在推进，worktrack 执行中。同一时刻仅允许一个 active milestone。
- **completed**: 目的达成（goal-driven: `worktrack_list_finished == true`，且 `Milestone Gate == pass`，且 `purpose_achieved == true`；work-collection: `worktrack_list_finished == true`）。验收通过后由 `harness-skill` 执行状态转移。
- **superseded**: 被更新的 milestone 替换（programmer override），保留历史但不参与激活队列。work-collection milestone 在 completed 后自动标记为 superseded。

## Pipeline 语义

Milestone 作为 Pipeline 中的节点，遵循以下规则：

- 多个 milestone 可同时处于 `planned` 状态，按 `priority`（升序）排列激活顺序
- 同一时刻仅允许一个 `active` milestone
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
- programmer 明确接受后，`harness-skill` 才执行 final acceptance writeback，把验收事实持久化为 runtime control-plane 状态。

final acceptance writeback 是一个逻辑事务，不是只改某一个文件。事务最小写入集合包括 `.servo/milestone/{milestone_id}.md`、`.servo/repo/milestone-backlog.md`、`.servo/repo/milestone-history.md`、`.servo/control-state.md`，必要时还包括 `.servo/repo/worktrack-backlog.md` 中对应 worktrack 状态的归一化。写回前必须校验输入状态，写回后必须复核 artifact 一致性；失败时进入 `writeback_incomplete` / `milestone_pipeline_stale` 阻塞，不得把 milestone 伪装成已完成。

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

- `Milestone Gate` 是独立的 milestone 级验证层，最少包含黑盒测试、白盒测试、反作弊检测，以及 goal-driven milestone 的 [Composite Milestone Acceptance](./composite-milestone-acceptance.md) lanes。
- `signal_satisfaction_pct` = 已满足的 `completion_signals` 数 / 总 `completion_signals` 数。
- `criteria_pass_pct` = 已通过的 `acceptance_criteria` 数 / 总 `acceptance_criteria` 数。
- `purpose_achieved == true` 仅当 `signal_satisfaction_pct >= completion_threshold_pct` 且 `criteria_pass_pct >= completion_threshold_pct`。默认阈值 `completion_threshold_pct = 100`。

任一环节未通过时，不得自动判定 Milestone 完成。

### Milestone Gate 与 Worktrack Gate 的分层关系

- Worktrack Gate 位于 `WorktrackScope`，负责单个 worktrack 的 closeout 裁决。
- Milestone Gate 位于 `RepoScope` 的 milestone 验收路径中，只在相关 worktrack 全部关闭后运行，验证跨 worktrack 的集成结果。
- Milestone Gate 不回溯替代 Worktrack Gate；它消费各 worktrack Gate 产出的 evidence，并补充 milestone 级黑盒/白盒/反作弊检查和复合验收 lanes。
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
- 不替代 `WorktrackContract` 或 `PlanTaskQueue`。

## Candidate Recommendation Boundary

Milestone artifact 保存已经创建、激活或完成的 milestone truth；候选 Milestone recommendation 不是该 artifact 的 live truth，除非已经经过 programmer confirmation 并由 `init-milestone-skill` 写入。

RepoScope 可以在 pre-milestone 场景输出 candidate milestone brief，但该 brief 必须与 live artifact 区分：

- `candidate` 表示方向建议，不等于 `planned`、`active` 或 `completed`。
- candidate brief 必须携带 `observed_facts`、`inferred_assumptions`、`unknowns`、`primary_contradiction`、`main_aspect_now`、acceptance signals、risk boundary 和 programmer confirmation requirement。
- candidate brief 不得增加 `progress_counter`，不得占用 `worktrack_list`，不得触发 pipeline advancement。
- candidate brief 中列出的 candidate worktracks 不是 Worktrack `Plan / Task Queue`、不是 task window，也不是 `.servo/worktrack/*` 的执行队列。
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
