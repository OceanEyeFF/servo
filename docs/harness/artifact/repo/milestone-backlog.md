---
title: "Milestone Backlog"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-13
---

# Milestone Backlog

> `.servo/repo/milestone-backlog.md` 是 `RepoScope` 运行时 artifact，记录 Milestone Pipeline 中仍可行动的 live milestone：`planned` 与至多一个 `active`。完成或替换后的 milestone 移入 `.servo/repo/milestone-history.md`，不继续挤占 live backlog 视图。不是部署模板。由 `milestone-init-skill` 创建 live 条目，`harness-skill` 执行状态转移，`milestone-status-skill` 和 `repo-whats-next-skill` 作为 pipeline 推理输入。

## 定位

- Scope: `RepoScope`
- 性质: 运行时 artifact（非 git 追溯，`.servo/` 被 gitignore）
- 产生时机: 首个 milestone 创建时由 `milestone-init-skill` 创建
- 更新时机: milestone 创建/状态转移/关闭时写入（upsert-by-milestone_id）
- 消费方: `repo-status-skill`（pipeline 快照）、`milestone-status-skill`（pipeline 上下文）、`repo-whats-next-skill`（milestone-first 推理）
- 历史承接: `.servo/repo/milestone-history.md` 保存 `completed` / `superseded` 条目，供依赖解析、审计和 stale marker 检查使用。

## 字段约定

每个 milestone 条目至少包含:

- `milestone_id`: 唯一标识（如 `MS-001`）
- `title`: Milestone 名称
- `purpose`: Milestone 目的描述
- `status`: `planned` / `active`（live backlog）；`completed` / `superseded` 必须移入 milestone history
- `priority`: 整数排序（数值越小优先级越高）
- `depends_on_milestones`: 前置 Milestone ID 列表（激活前必须完成）
- `worktrack_list`: 本 milestone 包含的 worktrack ID 列表
- `selected_worktrack_id`: RepoScope.Decide 每轮从 active milestone 的 `worktrack_list` 中选出的唯一 current worktrack（运行时可在 handoff/control state 中表达；不是 live backlog 必填字段）
- `created_by`: `programmer` / `harness`
- `created_at`: 创建时间（ISO 8601）
- `updated`: 最后更新时间（ISO 8601）
- `updated_by`: 最后修改者
- `activation_rules`: 自动激活条件（optional，harness-inferred）
- `milestone_kind`: `goal-driven` / `work-collection` — 默认 `goal-driven`
- `milestone_branch`: optional；Milestone integration branch 的名称或摘要。live backlog 可保存短字段供 RepoScope.Decide 快速判断，完整 branch 事实归单个 Milestone artifact。
- `continuation_state`: optional；`ready` / `waiting_external` / `paused_by_programmer` / `blocked`。该字段不替代 `status`，不参与 planned/active/completed/superseded 计数。
- `pause_resume`: optional；暂停/等待/恢复的短摘要，如 `pause_reason`、`resume_condition`、`parallel_work_allowed`、`paused_baseline_ref`、`paused_branch_head`。

## Pipeline 语义

- 同一 live 条目按 `milestone_id` upsert：相同 id 更新（latest override wins），不同 id 追加
- 同一时刻仅允许一个 milestone 处于 `active` 状态
- `planned` milestone 按 `priority`（升序）排列激活顺序；同 priority 按 `created_at` 排列
- `depends_on_milestones` 中的所有前置 milestone 必须能在 live backlog 或 milestone history 中解析；前置状态必须为 `completed` 或 `superseded` 后才能激活
- `completed` 表示 milestone 已完成并移入 history；`superseded` 表示被更新的 milestone 替换（programmer override），保留在 history 但不再参与激活队列
- 暂停/等待不是 live backlog 的 primary `status`。不得写入 `status: suspended`；使用 `continuation_state` 表达当前 Milestone 是否可继续派生 Worktrack。
- 当 active milestone 因 `continuation_state: waiting_external` 或 `paused_by_programmer` 且 `parallel_work_allowed: true` 释放 active slot 时，Harness 必须保留该 milestone 的 `milestone_branch`、`paused_baseline_ref`、`paused_branch_head` 和 `resume_condition`，并把另一个 milestone 激活过程记录为显式 programmer-approved 或 policy-approved transition。
- live backlog 应保持短而可操作，正常只保留真实待处理项（目标量级约 5-7 个）
- `milestone_pipeline_summary` 是 aggregate summary：planned/active 来自 live backlog，completed/superseded 来自 milestone history
- `worktrack_list` 只表达 Milestone 的声明范围和聚合进度。Milestone-level scheduler 一次只允许选择一个 `selected_worktrack_id` / current worktrack；不得把 `worktrack_list` 当成 Worktrack `Plan / Task Queue`、task window、dispatch queue 或 candidate milestone list。
- 若需要新增、移除、重排 worktrack，必须通过 RepoScope.Decide / append-worktrack 路由和必要的 programmer approval；不得在 WorktrackScope 或 Plan / Task Queue 中静默改写 Milestone backlog。

## 与正式 artifact 的关系

- 不替代 `docs/harness/artifact/control/milestone.md`（milestone artifact 是单个 milestone 的完整定义，backlog 是 live pipeline 目录）
- 不替代 `docs/harness/artifact/repo/worktrack-backlog.md`（worktrack backlog 追踪 worktrack 完成状态，milestone backlog 追踪 milestone pipeline 状态）
- `milestone-status-skill` 使用 live backlog 获取可行动 pipeline 上下文（active/planned、下一个候选 milestone），并使用 milestone history 解析 completed/superseded dependency 与历史一致性。

## 维护约定

- `milestone-init-skill` 按 `milestone_id` upsert 条目；programmer 和 harness 均可写入，时间戳最新者覆盖
- 条目按 priority（升序）→ created_at（升序）排列
- `harness-skill` 在 milestone closeout 或 pipeline advancement 时更新条目 status；当 live 条目进入 `completed` 或 `superseded`，必须从 live backlog 移入 `.servo/repo/milestone-history.md`
- `superseded` 条目保留在 history 中直到 programmer 手动清理
- work-collection milestone（`milestone_kind == "work-collection"`）在 `completed` 后自动标记为 `superseded` 并移入 history，不阻塞 pipeline
- 仅当 `milestone_acceptance_verdict == achieved`（goal-driven 双重验收通过；work-collection 单重验收通过）时，`Harness-skill` 可将 `active` → `completed`
- goal-driven milestone 经 programmer final acceptance 后，history 条目不得保留 `(planned)` 或 `(active)` worktrack marker；所有声明 worktrack 必须归一化为 `(done)`、`(deferred)`、`(blocked)` 或等价已决状态。
- 每次 final acceptance writeback 后，control-state 的 `active_milestone`、`milestone_status` 与 `milestone_pipeline_summary` 必须与 live backlog 中的唯一 active 条目、history 中的 completed/superseded 条目和 aggregate planned/active/completed/superseded 计数一致。
- Milestone branch 字段是 live routing metadata。完整 branch source、sync strategy、head ref 和 pause/resume evidence 应写在 `.servo/milestone/{milestone_id}.md`；backlog 只保存足以排序、激活和恢复的短摘要。
