---
title: "Init Milestone Skill"
status: active
updated: 2026-05-14
owner: servo-kernel
last_verified: 2026-06-13
---

# Init Milestone Skill

> 独立 Milestone 初始化 skill。它是 RepoScope 下的 Milestone 创建/注册算子，处理 latest-override、依赖验证和 pipeline 激活，不修改 version/release 状态。

## 定位

- Scope: `RepoScope`
- Function: 作为 `RepoScope.Init` 的 Milestone 初始化算子
- 输入: programmer 或 harness 提供的 milestone 规格 + milestone-backlog + control-state
- 输出: 结构化 Milestone 初始化结果（milestone_id、status、pipeline_position、writeback 信息）

canonical executable source：

- [../../../../product/harness/skills/milestone-init-skill/SKILL.md](../../../../product/harness/skills/milestone-init-skill/SKILL.md)

## 职责

- 创建或 upsert milestone artifact（`.servo/milestone/{milestone_id}.md`）
- Upsert milestone-backlog（`.servo/repo/milestone-backlog.md`）
- 处理 latest-override 语义（同 milestone_id，时间戳最新覆盖）
- 验证依赖合法性（存在性 + 循环依赖检测）
- 管理激活规则（同一时刻仅一个 active）
- 在 goal-driven milestone 激活前输出结构化 planning brief 并等待 programmer 确认
- 对 milestone 定义变更应用稳定性规则（signals / criteria / threshold 改写触发重新评估）
- 更新 control-state（active_milestone / milestone_pipeline_summary）

## 非职责

- 不分析 Milestone 状态（`milestone-status-skill` 的职责）
- 不选择下一 Worktrack（`repo-whats-next-skill` 的职责）
- 不初始化 worktrack（`worktrack-init-skill` 的职责）
- 不修改 version/release 状态

## 输入

| 输入 | 来源 | 说明 |
|------|------|------|
| Programmer 规格 | 用户输入 | milestone 的 title/purpose/worktrack_list/priority/depends_on 等 |
| Harness 推理规格 | `repo-whats-next-skill` 输出 | harness 推理的 milestone 建议 |
| Milestone backlog | `.servo/repo/milestone-backlog.md` | 唯一性检查 + pipeline 上下文 |
| Control state | `.servo/control-state.md` | active_milestone 状态 |
| Pre-milestone intake review | `milestone-pre-intake-skill` 输出 | 高风险或模糊 milestone create/upsert/activate 前的 ready/skipped/blocked 交接证据 |
| Complex Project Entry Gate | `.servo/repo/complex-project-entry-gate.md` 或 `complex_project_entry_gate` handoff | 复杂项目、弱文档或高风险 milestone create/upsert/activate 前的 Milestone-side blocking gate |
| Milestone Review Gate handoff | `milestone-pre-intake-skill` 输出 | 记录是否形成 `effective_pass` 的执行入口复核；非 pass 状态不得进入 Worktrack 初始化 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| milestone_id | string | 初始化/更新的 Milestone ID |
| milestone_title | string | Milestone 名称 |
| milestone_status | enum | planned / active |
| init_action | enum | created / upserted |
| priority | integer | Pipeline 优先级 |
| pipeline_position | string | 在 pipeline 中的位置 |
| depends_on_validation | object | 依赖检查结果 |
| activation_decision | string | 激活判定理由 |
| activation_brief | object/null | goal-driven 激活前输出的结构化 brief；work-collection 可为 `null` |
| confirmation_required | boolean | 是否必须等待 programmer 确认后才能激活 |
| milestone_reevaluation_required | boolean | 本次 upsert 是否因 signals / criteria / threshold 改写而要求重新评估 |
| ownership_review | string | 追加 worktrack 时的归属判定：belongs_current / suggest_other_milestone / suggest_new_milestone / not_applicable |
| artifact_path | string | milestone artifact 文件路径 |
| backlog_updated | boolean | 是否更新了 backlog |
| control_state_updated | boolean | 是否更新了 control-state |
| override_source | string | programmer / harness / none |
| can_proceed | boolean | 是否可继续 |
| proceed_blockers | array | 阻止推进的因素 |

## Pre-Milestone Intake Handoff

`milestone-init-skill` 消费 `milestone-pre-intake-skill` 的 `pre_milestone_intake_review`，不生成 intake 问题，也不把未确认推断写成 milestone truth。

必需 handoff 字段：

- `intake_status`
- `request_summary`
- `observed_facts`
- `inferred_assumptions`
- `unknowns`
- `programmer_decisions_required`
- `risk_flags`
- `open_questions`
- `answered_questions`
- `unresolved_questions`
- `continuation_state`
- `continuation_reason`
- `next_required_question`
- `next_question_blocks_ready`
- `why_it_matters`
- `recommended_answer`
- `tradeoff`
- `recommended_answers`
- `scope_boundary`
- `out_of_scope`
- `non_goals`
- `acceptance_signals`
- `suggested_milestone_brief`
- `confirmation_required`
- `programmer_confirmed`
- `ready_for_init_milestone`
- `intake_skipped`
- `skip_reason`
- `accepted_risk`
- `residual_risk_accepted`
- `accepted_residual_risk`
- `handoff_to_init_milestone`
- `template_contract_ref`
- `milestone_review_gate_handoff`
- `milestone_review_count`
- `latest_review_status`
- `latest_review_checkpoint`
- `effective_review_pass`
- `review_invalidated_by`
- `complex_project_entry_gate`
- `scanner_evidence_ref`
- `complexity_signals`
- `operator_safety_policy`
- `dialog_review_questions`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`
- `milestone_task_complexity_assessment`

状态语义：

- `ready`: 只有 `ready_for_init_milestone = true`、`programmer_confirmed = true` 且 `intake_skipped = false` 时才允许 create/upsert/activate。
- `skipped`: 只能表示 programmer 显式接受跳过风险；必须记录 `skip_reason` 和 `accepted_risk`，不得伪装成 ready。默认路由是 handback / approval，不自动 create、upsert 或 activate；只有同一轮输入明确授权“跳过 intake 后仍允许初始化”时才可继续。
- `questions_required`: 必须返回 blocked，保留 `continuation_state` 和 `next_required_question`，并路由回 `milestone-pre-intake-skill` 继续 one-question-at-a-time；不得当成 approval。
- `blocked`: 必须返回 blocked 并暴露阻断原因。
- missing / 字段不全 / 状态矛盾：必须返回 blocked，不得把薄弱的 milestone brief 伪装成已确认。

Milestone Review Gate handoff 只能在 `intake_status = ready`、`programmer_confirmed = true`、`ready_for_init_milestone = true`、`intake_skipped = false` 且 `review_status = effective_pass` 时增加 `milestone_review_count`。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或缺少 `latest_review_checkpoint` 都不得当成 pass，必须保持 Worktrack Init/Dispatch blocked。若 `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 改变，必须写入 `review_invalidated_by` 并要求 fresh checkpoint。

## Complex Project Entry Gate Handoff

当 milestone creation/upsert/activation 命中复杂项目、弱文档、高风险操作或跨系统触发条件时，`milestone-init-skill` 必须消费 `complex_project_entry_gate`。该 gate 是 Milestone-side blocking gate，不是固定 heavy mode；canonical guard term: not fixed heavy mode。scanner output is evidence, not verdict。Worktrack execution modes `normal`、`autoreview`、`yolo` 不替代该 gate。

必需 handoff 字段：

- `complex_project_entry_gate`
- `scanner_evidence_ref`
- `complexity_signals`
- `operator_safety_policy`
- `dialog_review_questions`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`

`entry_verdict = blocked` 或 `milestone_blocking_decision` 包含 `block_create`、`block_upsert` 或 `block_activate` 时，必须返回 blocked，不得写入或激活 implementation-oriented milestone。缺失、空白、placeholder、`pending_programmer_confirmation` 或字段不全的 gate 必须按 unresolved gate blocking default 处理，不得解释为 `clear` 或 `not_applicable`。Canonical terms: missing, blank, placeholder, pending, incomplete。`entry_verdict = needs_reinforcement_milestone`、`reinforcement_milestone_recommendation.needed = true` 或 `blocks_implementation_until_resolved = true` 时，默认 recommendation 是创建 reinforcement documentation / project-understanding milestone，而不是把弱文档推断升格为 milestone truth。结构化 recommendation 至少携带 `needed`、`recommendation_status`、`recommendation_type`、`suggested_title` 或 `suggested_purpose`、`reason` 或 `recommendation_reason`、`temporary_understanding_ref`、`evidence_refs`、`confirmation_required` 与 `blocks_implementation_until_resolved`；`recommendation_status` 可为 `not_needed`、`recommended`、`required` 或 `pending_operator_review`。

## 激活与稳定性约定

- goal-driven milestone 在 `planned` → `active` 前，必须先输出结构化 brief，最少包含 `goal`、`completion_signals`、`acceptance_criteria`、`worktrack_list`、`completion_threshold_pct`、`depends_on_milestones` 和 `activation_reason`。
- brief 发出后，`confirmation_required = true`，skill 必须等待 programmer 确认后才能实际激活 milestone。
- work-collection milestone 保持既有自动激活语义；可输出同结构 brief 作为信息提示，但不形成阻塞确认边界。
- 若本次 upsert 修改了 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct`，必须输出 `milestone_reevaluation_required = true`，并要求后续由 `milestone-status-skill` 重新评估 milestone。
- 若仅向 `worktrack_list` 追加 worktrack，且该 worktrack 已确认归属当前 milestone 的 `purpose`/`signals`/`criteria`，则不触发 milestone 重新评估。
- 追加进入当前 milestone 的 worktrack 以独立执行单元形式推进：专属 branch、contract、queue、evidence、closeout 和 repo-refresh 追踪由下游 `worktrack-init-skill` / closeout 路径承接。
- 若追加的 worktrack 不归属当前 milestone，`ownership_review` 必须返回 `suggest_other_milestone` 或 `suggest_new_milestone`；不得通过静默改写当前 milestone 定义来吸收该 worktrack。

## 调用时机

- `RepoScope.Decide` 阶段（`repo-whats-next-skill` 输出 `suggested_milestone_action == "create"` 或 `"activate"` 时）
- Programmer 显式声明新 milestone 目标
- Programmer 或 harness 请求修改 milestone signals / criteria / threshold
- Programmer 或 harness 请求向 milestone 追加 worktrack
- Pipeline 中无符合条件的 planned milestone 可激活时
