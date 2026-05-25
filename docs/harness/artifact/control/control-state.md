---
title: "Harness Control State"
status: active
updated: 2026-05-25
owner: servo-kernel
last_verified: 2026-05-25
---
# Harness Control State

保存控制面所处模式，不保存业务真相。最少应包含控制级别、活跃 worktrack、`baseline_branch`、下一动作和关联正式文档路径。不替代 `RepoSnapshot/Status` 或 `WorktrackContract`。

Harness 每轮启动时先读取 `.servo/control-state.md` 恢复控制配置，再进入 `Scope`/`Function` 状态估计。该启动前置读取称为 control config hydration，最少覆盖 `Linked Formal Documents`、`Approval Boundary`、`Continuation Authority`、`Handback Guard`、`Baseline Traceability` 与 `Autonomy Ledger`。缺失字段按本文默认值降级解释，缺失不得被解释为扩大权限、放宽审批或启用更多自动性，并在本轮状态估计中记录 `config_hydration_gaps`。

## Linked Formal Documents

Harness Control State 可保存标准 artifact 路径指针（`repo_snapshot`、`repo_analysis`、`worktrack_contract`、`plan_task_queue`、`gate_evidence`、`milestone`）供 supervisor 快速定位正式对象。这些只是路径指针，不含业务真相。若某 artifact 缺失或过期，Control State 不得自行补写业务内容，应通过对应 `Scope` 的 `Observe`/`Decide`/`Init`/`Verify` 路由刷新正式对象。

Milestone 是 `RepoScope` 下的聚合对象，control-state 应在 Linked Formal Documents 中保存 Milestone 相关路径指针：

- `active_milestone`: 当前活跃 Milestone 的 `milestone_id`（单数，同一时刻仅一个 active）
- `milestone_status`: 当前活跃 Milestone 的状态（`planned`/`active`/`completed`/`superseded`）
- `milestone_pipeline_path`: 指向 `.servo/repo/milestone-backlog.md` 的路径指针
- `milestone_history_path`: 指向 `.servo/repo/milestone-history.md` 的路径指针
- `milestone_pipeline_summary`: Pipeline aggregate 快照（planned/active 来自 live backlog，completed/superseded 来自 milestone history）

`active_milestone` 缺失但 `milestone_pipeline_path` 存在且 pipeline 非空时，表示 pipeline 中有 planned milestone 但尚未激活。设置后 Milestone 进度由 `milestone-status-skill` 独立分析，Pipeline 推进由 `harness-skill` 在收到 `milestone_acceptance_verdict` 后执行，不替代 `RepoScope.Decide` 的决策权。

Milestone final acceptance 写回后，Control State 必须与 `.servo/repo/milestone-backlog.md` 和 `.servo/repo/milestone-history.md` 保持一致：`active_milestone` 只能指向 live backlog 中唯一 `active` milestone；没有 active milestone 时应写为 `none`；`milestone_status` 必须与 active milestone 状态一致或为 `none`；`milestone_pipeline_summary` 的 planned/active 计数必须等于 live backlog 实际条目，completed/superseded 计数必须等于 milestone history 实际条目。若写回后不一致，Harness 必须停在 `writeback_incomplete` / `milestone_pipeline_stale`，不得继续 Worktrack 初始化或 pipeline advancement。

若支持 contract-boundary 后自主续跑，还需最小 Continuation Authority 策略位：

- `post_contract_autonomy`: `delegated-minimal`（默认）/`manual-only`（strict handback 诊断）
- `autonomy_scope`: 默认 `current-goal-only`
- `max_auto_new_worktracks`: 默认 `1`，大于 1 为显式 override
- `stop_after_autonomous_slice`: 默认 `yes`
- `subagent_dispatch_mode`: `auto`（默认）/`delegated`/`current-carrier`；repo 级默认值，不遮蔽 worktrack 级策略
- `subagent_dispatch_mode_override_scope`: 默认 `worktrack-contract-primary`；仅 `global-override` 才压过 worktrack contract
- `subagent_default_model`: 可选，不改变权限边界
- `runtime_dispatch_profile`: 最近一次 dispatch 能力画像摘要，可包含 `backend_runtime`、`model_family`、`subagent_dispatch_shell`、`runtime_supports_subagent`、`subagent_permission_state`、`permission_allows_delegation`、`dispatch_package_safety`

以上字段属于 control policy，不回答 repo 目标，不替代 `WorktrackContract`。`subagent_dispatch_mode` 是 SubAgent 委派的 repo 级默认策略，语义与 worktrack 级 `runtime_dispatch_mode` 一致：`auto` 按 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier；`delegated` 必须委派否则返回 gap/block；`current-carrier` 关闭委派。若权限边界、运行时缺口或 `dispatch package unsafe` 阻止委派，fallback 原因须写入执行结果或 `gate evidence`，并使用 `runtime fallback` 标记运行时回退。若 runtime 为 ClaudeCodeCLI 或 model family 为 Deepseek 且无法证明 SubAgent shell 可用，必须把 `runtime_dispatch_profile`、`delegation_attempted`、`attempted_carrier`、`carrier_decision` 与 `fallback_reason` 写入本轮 evidence，不得静默使用 current-carrier。

程序员授予的长期权限、自动性或分派策略变更必须写回本 artifact 对应配置段，不得仅停留于对话记忆。一次性审批仅对当前 worktrack、gate 或 destructive action 生效，应写入本轮 `evidence`/`handoff`，不得改变长期默认值。仅当用户明确表达持久授权或更改默认策略时，才可更新 `post_contract_autonomy`、`max_auto_new_worktracks`、`stop_after_autonomous_slice`、`subagent_dispatch_mode`、`subagent_dispatch_mode_override_scope` 或其他长期 authority 字段。若字段语义或默认值改变，须同步更新初始化模板和 canonical skill 说明。

仅有 Continuation Authority 不够——若 handback/re-entry 边界未持久化到下一轮会话，”继续工作”可能被误读为 fresh handoff 并错误新建 worktrack。因此还需 Handback Guard / Autonomy Ledger：

- `handoff_state`: `none`/`awaiting-handoff`/`autonomous-slice-active`
- `last_stop_reason` / `last_handback_signature`
- `handback_reaffirmed_rounds`: 默认 0（阈值 `stable_handback_threshold`，默认 2）
- `handback_lock_active`: 默认 false
- `last_unlock_signal`: N/A 或最近有效解锁描述
- `autonomy_budget_remaining` / `autonomous_worktracks_opened`

以上字段属于 control memory，不替代 `RepoSnapshot/Status`、`WorktrackContract` 或 `GateEvidence`。

此外应保存 Baseline Traceability，用于 `WorktrackScope` 关闭后快速定位已验证基线：`last_verified_checkpoint`、`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint`、`checkpoint_type`、`checkpoint_ref`、`verified_at`、`if_no_commit_reason`、`alternative_traceability`。

其中 `latest_observed_checkpoint` 与 `last_doc_catch_up_checkpoint` 是 git hash 幂等性锚点，分别记录 `repo-refresh-skill` 和 `doc-catch-up-worker-skill` 上次执行时的 HEAD hash，供 `harness-skill` 启动时对比以跳过重复刷新。

## Skill Source Baseline Traceability

Canonical skill source version facts are owned by repo-level checkpoint artifacts, not by scattered prose hash mentions in catalog pages. For `product/harness/skills/`, the stable relation is:

- canonical source root: `product/harness/skills/`
- docs/catalog owner: `docs/harness/catalog/`
- current source checkpoint owner: `.servo/repo/snapshot-status.md` after `repo-refresh-skill`
- current control-plane idempotency owner: `.servo/control-state.md` `Baseline Traceability`

When a verified worktrack changes canonical skill source, source-side skill indexes, or docs/source traceability, closeout records the evidence and merge commit in its closeout record, then `repo-refresh-skill` writes the refreshed git HEAD to `latest_observed_checkpoint` and `checkpoint_ref`. If the same change also updates operator-facing docs or version facts, `doc-catch-up-worker-skill` records the HEAD as `last_doc_catch_up_checkpoint`.

Long-term docs should link to the source root or catalog owner, not embed one-off commit hashes for each skill. If a commit hash is needed for an audit handoff, keep it in runtime artifacts such as closeout records, repo snapshot, or release/version evidence. Deploy targets remain consumers of the source baseline and must not become the baseline owner.

`milestone_input_checkpoint` 是 Milestone 输入指纹锚点，由 `milestone-status-skill` 按 `milestone-input-checkpoint/v1` 计算（格式 `sha256:<64 位小写 hex>`）。算法对 milestone artifact、worktrack backlog、gate evidence、repo snapshot 的已纳入字段取 SHA-256，使用字典键排序、repo-relative POSIX path、稳定列表顺序和显式 `null` 值。不得纳入文件 mtime、时间戳、绝对路径、上次 checkpoint 或 progress counter 等易变/派生值。该指纹与 git HEAD 独立（`.servo/` 下 artifact 变化不产生 git commit）。下一轮 `Observe` 仅当 `milestone_input_checkpoint` 与新指纹一致且 `latest_observed_checkpoint` 与 `git rev-parse HEAD` 一致时，才可跳过 Milestone 进度重算。

`milestone_pipeline_checkpoint` 是 Milestone Pipeline 指纹锚点，由 `milestone-status-skill` 在 pipeline 存在多条目时计算。算法对 live `milestone-backlog.md` 与 `milestone-history.md` 中所有条目的 (`milestone_id`, `status`, `priority`, `depends_on_milestones`, `worktrack_list`) 取 SHA-256，使用字典键排序，并标记来源为 `live` 或 `history`。该指纹用于判断 pipeline 结构是否变化（新增/移除/重排 milestone、完成项移入 history），与单个 milestone 的进度指纹（`milestone_input_checkpoint`）互补。当 `milestone_pipeline_checkpoint` 与已存指纹一致时，可跳过 pipeline 结构重分析；但单个 milestone 的 progress counter 仍由 `milestone_input_checkpoint` 独立判定。

空值或缺失表示该锚点尚未建立，须执行完整状态估计。不得将空值解释为”当前基线无需刷新”。以上字段属于 traceability metadata，不替代 `RepoSnapshot/Status`。

补充约束：

- `post_contract_autonomy: manual-only`：仅可 handback，不得自动开新 worktrack。`delegated-minimal`：仅 `current-goal-only` 消费一次 budget。
- `WorktrackScope` 关闭后返回 `RepoScope` 也不得自动清空 `handoff_state`。
- `awaiting-handoff` 且无新 programmer 决策仅允许复核同一 handback 边界。
- `delegated-minimal` 下仅 `awaiting-handoff` 且 budget > 0 可切新 bounded slice，开启即消费预算。
- autonomous slice 结束后应再次 handback，不得无限链式续跑。`stop_after_autonomous_slice: yes` 时 slice 结束写回 `awaiting-handoff`。
- stable-handback 是 runtime verdict，control-state 持久化 `last_handback_signature` 与 reaffirm 计数。
- `awaiting-handoff` 且 `handback_lock_active = true` 仅显式 unlock signal 可解除交接锁。裸"重试""继续工作"或重复文字摘要不构成有效 unlock signal，须由 programmer 发出新实质指令或新信息。
