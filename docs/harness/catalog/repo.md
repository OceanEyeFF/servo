---
title: "Harness Skill Catalog / RepoScope"
status: active
updated: 2026-05-16
owner: servo-kernel
last_verified: 2026-05-08
---
# RepoScope Skill Catalog

> 目的：固定 `RepoScope` 下直接面向 `Codex` 的 Harness skills catalog。

`Codex` 直接消费 skills 本身，不经过中间 operator 名称转译。

## 原则

`RepoScope` skills 负责长期基线的观察、判断、目标变更和 repo 状态刷新，不承担编码执行。repo-status-skill 对应 `RepoScope` observing，repo-whats-next-skill 对应 `RepoScope` deciding。repo-status-skill 是顺手调用的稳定观测包，非强制前置。repo-whats-next-skill 须能在无 repo-status-skill 产物时直接基于 repo truth 完成判断。三者都不负责 worktrack 级文档维护。structured handoff 优先使用 `recommended_next_route` 与 canonical approval 字段。`RepoScope` 内可挂载有界分析模式但不应为分析框架新增 skill 数量。Repo Analysis 可喂给 repo-whats-next-skill 但不能替代 Goal/Charter 或 Snapshot/Status。append-feature、append-design 与 append-milestone 由同一 skill 分类，不拆分。需要改动系统状态时由 supervisor 决定是否切入 `WorktrackScope`。

## Catalog

### 0. set-harness-goal-skill

职责：当 Harness 尚未初始化或 `.servo/goal-charter.md` 缺失时，将 programmer 的自然语言目标转化为 Repo Goal/Charter、Engineering Node Map 和初始控制面组件。它是 `RepoScope.SetGoal` 的初始化参考信号入口，不属于常规循环中的目标变更路径。

主要依赖：

- Programmer goal input
- Repo structure
- Harness Control State 初始化模板
- Weak-doc Temporary Understanding 模板（仅弱文档 adoption / onboarding）
- Complex Project Entry Gate（仅复杂项目、弱文档或高风险 Milestone 进入前）

canonical executable source：

- [../../../product/harness/skills/set-harness-goal-skill/SKILL.md](../../../product/harness/skills/set-harness-goal-skill/SKILL.md)
- [../../../product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md](../../../product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md)

当前状态：

- `initial canonical executable skeleton landed`
- `weak-doc temporary understanding template contract landed`

preferred handoff fields：

- `temporary_understanding`
- `understanding_mode`
- `lightweight`
- `full`
- `token_budget_note`
- `token-cost tradeoff`
- `observed_facts`
- `inferred_purpose`
- `operational_purpose`
- `known_risks`
- `unknowns`
- `confirmation_questions`
- `recommended_answers`
- `programmer_decisions_required`
- `promotion_plan`
- `truth_boundary`
- `programmer_confirmed`
- `verified_evidence`
- `programmer confirmation`
- `verified evidence`
- `not_goal_truth`
- `not Goal Charter truth`
- `--weak-doc-onboarding`
- `complex_project_entry_gate`
- `scanner_evidence_ref`
- `complexity_signals`
- `operator_safety_policy`
- `dialog_review_questions`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`
- `needed`
- `recommendation_status`
- `recommendation_type`
- `temporary_understanding_ref`
- `blocks_implementation_until_resolved`

Complex-project adoption handoff is a Milestone-side blocking gate, not fixed heavy mode. scanner output is evidence, not verdict. Worktrack execution modes `normal`、`autoreview`、`yolo` remain user-owned policy choices and do not bypass `milestone_blocking_decision`. Weak-doc reinforcement routing uses structured `reinforcement_milestone_recommendation`; `needed = true` or `blocks_implementation_until_resolved = true` routes to reinforcement documentation / project-understanding Milestone before implementation.

### 1. pre-milestone-intake-skill

职责：在 `init-milestone-skill` 写入或激活 Milestone 前，执行一轮限定范围需求核实、追问、挑战和推荐，产出 `pre_milestone_intake_review`。它不创建 milestone、不创建 worktrack、不修改代码，只决定 milestone brief 是否足够进入初始化。

下游 `init-milestone-skill` 必须按 ready / skipped / questions_required / blocked / missing intake 分支消费该 review；skipped intake 只能表达 programmer 接受风险，不能伪装成 ready。默认路由是 handback / approval，不自动 create、upsert 或 activate；只有同一轮输入明确授权“跳过 intake 后仍允许初始化”时才可继续。字段不全或状态矛盾时，不得把薄弱的 milestone brief 伪装成已确认。

主要依赖：

- Programmer request
- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Harness Control State`
- live Milestone Backlog
- `complex_project_entry_gate`（当命中 complex-project trigger 时）

canonical executable source：

- [../../../product/harness/skills/pre-milestone-intake-skill/SKILL.md](../../../product/harness/skills/pre-milestone-intake-skill/SKILL.md)
- [../../../product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md](../../../product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md)

当前状态：

- `initial canonical executable skeleton landed`
- `before-start question template contract landed`

preferred handoff fields：

- `pre_milestone_intake_review`
- `intake_status`
- `request_summary`
- `observed_facts`
- `inferred_assumptions`
- `unknowns`
- `programmer_decisions_required`
- `risk_flags`
- `open_questions`
- `why_it_matters`
- `recommended_answers`
- `recommended_answer`
- `tradeoff`
- `scope_boundary`
- `out_of_scope`
- `non_goals`
- `acceptance_signals`
- `suggested_milestone_brief`
- `confirmation_required`
- `template_contract_ref`
- `intake_skipped`
- `skip_reason`
- `accepted_risk`
- `programmer_confirmed`
- `ready_for_init_milestone`
- `handoff_to_init_milestone`
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

Milestone Review Gate handoff records whether pre-milestone intake produced an `effective_pass` before Worktrack Init/Dispatch. It must carry `milestone_review_gate`, `milestone_review_gate_handoff`, `milestone_review_count`, `latest_review_status`, `latest_review_checkpoint`, `effective_review_pass`, and `review_invalidated_by`. Non-pass states `questions_required`, `blocked`, `skipped`, `missing`, `stale`, and `invalidated` are not pass states. Changing `worktrack_list`, `completion_signals`, `acceptance_criteria`, scope/non-goals, or risk boundary invalidates the checkpoint and requires a fresh review.

These complex gate fields represent a Milestone-side blocking gate, not fixed heavy mode. scanner output is evidence, not verdict. Worktrack execution modes `normal`、`autoreview`、`yolo` remain WorktrackScope policy choices. Missing, blank, placeholder, pending, or incomplete gate handoff must use unresolved gate blocking default and must not be interpreted as clear or `not_applicable`.

When weak docs are the blocker, `reinforcement_milestone_recommendation` must be structured with `needed`, `recommendation_status`, `recommendation_type`, `suggested_title` or `suggested_purpose`, `reason` or `recommendation_reason`, `temporary_understanding_ref`, `evidence_refs`, `confirmation_required`, and `blocks_implementation_until_resolved`. `recommendation_status` values include `not_needed`, `recommended`, `required`, and `pending_operator_review`. `needed = true` or `blocks_implementation_until_resolved = true` blocks implementation-oriented Worktrack derivation; `needed = false` alone must not block a low-risk clear / `not_applicable` gate.

### 2. repo-status-skill

职责：读取当前 repo 基线、汇总主线/活跃分支/治理状态/已知风险、为 harness-skill 产出格式稳定的 observation packet、并明确本轮是否足够进入下一步 repo judgment。

主要依赖：

- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/repo-status-skill/SKILL.md](../../../product/harness/skills/repo-status-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred handoff fields：

- `repo_judgment_ready`
- `recommended_next_route`
- `continuation_ready`
- `continuation_blockers`
- `approval_required`
- `approval_reason`

### 3. repo-whats-next-skill

职责：基于当前 repo 状态判断下一步演进方向——切入 worktrack、刷新 baseline 或进入 goal change control。保留 recommended_repo_action 字段同时回写 recommended_next_route 供 supervisor 消费。可直接基于 Goal/Charter、Snapshot/Status 与 Control State 完成一轮判定，不要求先有 repo-status-skill 产物。canonical skill 保留完整 RepoScope.deciding 动作空间但 deploy profile 收窄时输出必须反映 active route boundary。Worktrack Contract 只能作为边界证据而非 repo 级任务队列。默认 next-step 偏松时启用 priority reframe/contradiction analysis 模式；完全无更新内容时启用 overview fallback 模式生成候选建议。用 Facts / Inferences / Unknowns、单一 Primary Contradiction、Top Priority Now、Do Not Do 等字段压缩判断。新鲜 Repo Analysis 可作为结构化输入但无此 artifact 时仍需直接判定。recommended_repo_action 必须投影成 recommended_next_route 等字段。overview fallback 可参考 project-dialectic-planning-skill 的 dialectical planning 方法论但必须压缩为候选建议。只返回 candidate_worktracks 与 top_candidate，不创建工作追踪，不改变 Harness 控制状态。这些模式属于 RepoScope 分析模式，不是新 skill。

主要依赖：

- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Harness Control State`
- `Goal Change Request`
- `Complex Project Entry Gate`

canonical executable source：

- [../../../product/harness/skills/repo-whats-next-skill/SKILL.md](../../../product/harness/skills/repo-whats-next-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed, with bounded priority reframe mode folded into the same skill`
- `agents deploy copies the canonical skill surface directly; runtime route boundaries should come from current repo artifacts and control state, not legacy payload metadata`
- `overview fallback mode landed for no-action-found cases`

preferred decision fields：

- `recommended_repo_action`
- `recommended_next_route`
- `allowed_repo_actions`
- `route_boundary_source`
- `continuation_ready`
- `continuation_blockers`
- `approval_required`
- `approval_scope`
- `approval_reason`
- `overview_trigger_reason`
- `candidate_worktracks`
- `top_candidate`
- `complex_project_entry_gate`
- `milestone_blocking_decision`
- `reinforcement_milestone_recommendation`
- unresolved gate blocking default
- `blocks_implementation_until_resolved`

### 4. repo-append-request-skill

说明：在 RepoScope 下处理外部追加请求 intake，支持 append-feature、append-design 与 append-milestone 三个 mode，只做分类与路由，不执行目标变更/scope expansion/Milestone 创建/设计/实现。

职责：接收请求并判断应归入 goal change/new milestone/new worktrack/scope expansion/design-only/design-then-implementation；输出路由结果、下一 route/scope、suggested milestone action、suggested node type、审批边界与最小缺失信息；命中目标变更或范围扩展时显式返回 authority boundary；保持 approval_required/continuation_ready/continuation_blockers 一致。

主要依赖：

- `Append Request`
- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Harness Control State`
- 必要的活跃 `Worktrack Contract` 摘要

canonical executable source：

- [../../../product/harness/skills/repo-append-request-skill/SKILL.md](../../../product/harness/skills/repo-append-request-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred decision fields：

- `append_mode`
- `append_classification`
- `classification_confidence`
- `recommended_next_route`
- `recommended_next_scope`
- `suggested_milestone_action`
- `suggested_node_type`
- `approval_required`
- `approval_scope`
- `approval_reason`
- `continuation_ready`
- `continuation_blockers`

### 5. repo-change-goal-skill

说明：在 RepoScope 下执行目标变更，包含分析→草案→确认→执行改写完整闭环，在当前 carrier 直接分析不再打包给 SubAgent。

职责：接收并分析目标级变更请求、评估对现有 worktracks/baseline/不变量影响、生成 goal-charter 草案等待用户确认、确认后直接改写 goal-charter.md/snapshot-status.md/control-state.md。

主要依赖：

- `Goal Change Request`
- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/repo-change-goal-skill/SKILL.md](../../../product/harness/skills/repo-change-goal-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 6. repo-refresh-skill

职责：在 worktrack closeout 后刷新 repo 慢变量状态，把已验证结果回收到 repo 级正式对象，只处理 repo 级 writeback 不处理 .servo/worktrack/* 维护。刷新成功后必须把当前 HEAD 写回 `Harness Control State` 的 `Baseline Traceability.latest_observed_checkpoint`，并同步 `checkpoint_ref` / `verified_at` 等观测锚点；首次刷新或字段为空时不得把空值解释为可跳过刷新。

主要依赖：

- `Repo Goal / Charter`
- `Repo Snapshot / Status`
- `Gate Evidence`
- `Harness Control State`

checkpoint writeback:

- `latest_observed_checkpoint`: repo-refresh 成功后的 git HEAD；空值表示从未建立该幂等锚点，必须执行完整状态估计和刷新
- `checkpoint_ref`: 与该 HEAD 对应的 branch/ref 描述
- `verified_at`: 本次刷新验证日期

canonical executable source：

- [../../../product/harness/skills/repo-refresh-skill/SKILL.md](../../../product/harness/skills/repo-refresh-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`
