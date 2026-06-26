---
title: "Harness Control State"
status: active
updated: 2026-06-26
owner: servo-kernel
last_verified: 2026-06-26
---
# Harness Control State

保存控制平面所处模式，不保存业务真相。最少应包含控制级别、活跃 worktrack、`baseline_branch`、下一动作和关联正式文档路径。不替代 `RepoSnapshot/Status` 或 `WorktrackContract`。

Harness 每轮启动时先读取 `.servo/control-state.md` 恢复控制配置，再进入 `Scope`/`Function` 状态估计。该启动前置读取称为 control config hydration，最少覆盖 `Linked Formal Documents`、`Approval Boundary`、`Continuation Authority`、`Handback Guard`、`Autonomy Ledger` 与跨 scope 路由记忆；git checkpoint 级 Baseline Traceability 字段从 `.servo/control-state-repo.md` 读取。缺失字段按本文默认值降级解释，缺失不得被解释为扩大权限、放宽审批或启用更多自动性，并在本轮状态估计中记录 `config_hydration_gaps`。

## Conservative Runtime Backfill

> `.servo` 运行时正式对象可能落后于当前正式对象合同。对于缺失的增量字段，以保守运行时回填处理：仅向前应用默认值（`false`、`unknown`、`missing`、`blocked`、`not ready`、`N/A` 或空阻塞项，视字段而定），并将缺口记录为运行时证据。回填必须保留已有观测事实，不得推断 programmer 确认，不得授予权限，不得递增计数器，不得将缺失 gate 变为 `ready` 或 `allowed`。

保守运行时回填不是大规模迁移。它可以填平当前路由视图或当前 worktrack 正式对象的增量字段缺口，但不得重写历史 `.servo` 真相或扩大权限。任何控制审批、分派、review pass、effective pass、自治、破坏性操作或 Worktrack Init/Dispatch 的字段，在没有已验证证据或 programmer 确认前，默认值为 blocked/not ready。

守则：保守运行时回填只能是 `forward-only`。It `must not grant permissions`, `must not infer programmer confirmation`, `must not increment counters`, and `must not enable Worktrack Init/Dispatch`。等价中文约束为：不得授予权限，不得推断 programmer 确认，不得递增计数器，不得启用 Worktrack Init/Dispatch。

## Control State Compaction Contract

`.servo/control-state.md` 可以被安全压缩，但压缩是控制面整理动作，不是权限、路由、历史真相或业务真相的重定义。压缩后的文件必须仍能支持 Harness 启动 hydration、Branch Environment Guard、Milestone/Worktrack 路由和 authority 判断；git checkpoint 级 baseline traceability 由 `.servo/control-state-repo.md` 承接。

压缩后必须保留的 hydration-critical 字段组：

- Metadata：`updated`、`owner`、`rotation_count`、`last_rotation_at`、`handback_history_ref`。
- Current Control Level：`repo_scope`、`worktrack_scope`、`current_function`。
- Active Worktrack：`active_worktrack`、`active_worktrack_branch`、`active_worktrack_node_type`、`latest_closed_worktrack_commit`、`worktrack_autonomy_policy`。
- Milestone Pipeline：`active_milestone`、`milestone_status`、`milestone_pipeline_path`、`milestone_pipeline_summary`、`active_milestone_branch`、`active_milestone_branch_sync_state`、`active_milestone_progress`、`active_milestone_branch_head`。
- Milestone Review Gate：`milestone_review_gate_ready`、`latest_review_status`、`milestone_review_count`、`latest_review_checkpoint`、`effective_review_pass`、`review_invalidated_by`，以及 control-state 镜像字段 `active_milestone_review_gate_status`、`active_milestone_review_count`、`active_milestone_review_checkpoint`、`active_milestone_review_blockers`。
- Baseline Branch 与 Branch Environment Guard：`baseline_branch`、`baseline_ref`、`current_checkout`、`current_branch_context`、`expected_branch_context`、`branch_context_guard_status`、`branch_context_required_ref`、`worktrack_branch`。
- Current Next Action 与 Linked Formal Documents：下一路由、下一 scope、当前动作、`repo_snapshot`、`repo_analysis`、`worktrack_contract`、`plan_task_queue`、`gate_evidence`。
- Approval Boundary、User-Defined Servo Controls、Continuation Authority、Handback Guard、Autonomy Ledger。
- Baseline Traceability 指针：`.servo/control-state-repo.md` 持有 git checkpoint 字段（`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint`、`verified_at_history`、checkpoint writeback/read scripts 的目标）；`.servo/control-state.md` 只保留启动 hydration、控制记忆、路由配置与必要 artifact 指针。

可压缩或折叠的内容仅限历史重复行和非当前路由所需的长列表，例如多条旧 `latest_closed_worktrack_commit`、旧 `verified_at`、旧 handback note、旧 closeout 摘要和重复 checkpoint 叙述。压缩时最多保留最近一条当前可路由记录，并用中性 history reference 指向 compaction history artifact。history reference 只能是由 compact 操作显式生成并验证的 artifact；installer-generated backup/update artifacts 不是 history source，不能作为模板默认值、清理输入或 `handback_history_ref` 的默认目标。

压缩动作必须遵守以下事务边界：

1. 先 dry-run，输出将保留、折叠、外部化和拒绝处理的字段列表。
2. 校验所有 hydration-critical 字段存在；缺失字段只能按 Conservative Runtime Backfill 降级，不能静默补成 ready/allowed/pass。
3. 写入前保存可恢复的 compaction history artifact；该 artifact 必须由本次 compact 操作生成，并记录 source checkpoint、created_at、tool/skill、preserved field summary 和 externalized sections。
4. 写入后重新读取 `.servo/control-state.md`，验证 Branch Environment Guard、Milestone Review Gate、Continuation Authority、Handback Guard 和控制路由字段仍可解析；如本轮涉及 git checkpoint，还须读取 `.servo/control-state-repo.md` 验证 Baseline Traceability 可解析。
5. 验证失败时不得提交压缩结果；必须进入 Recover 或 handback，并保留原文件。

停止条件：

- 任一 hydration-critical 字段无法解析。
- 压缩会改变 approval、autonomy、dispatch、review gate、branch guard 或 protected branch 语义。
- history reference 需要依赖 installer-generated backup/update artifacts 才能承接。
- 当前存在 active worktrack 但 Worktrack Contract、Plan / Task Queue 或 gate evidence 指针不可读。
- dry-run 与 apply 后验证结果不一致。

## Linked Formal Documents

Harness Control State 可保存标准 artifact 路径指针（`repo_snapshot`、`repo_analysis`、`worktrack_contract`、`plan_task_queue`、`gate_evidence`、`milestone`）供 supervisor 快速定位正式对象。这些只是路径指针，不含业务真相。若某 artifact 缺失或过期，Control State 不得自行补写业务内容，应通过对应 `Scope` 的 `Observe`/`Decide`/`Init`/`Verify` 路由刷新正式对象。

Milestone 是 `RepoScope` 下的聚合对象，control-state 应在 Linked Formal Documents 中保存 Milestone 相关路径指针：

- `active_milestone`: 当前活跃 Milestone 的 `milestone_id`（单数，同一时刻仅一个 active）
- `milestone_status`: 当前活跃 Milestone 的状态（`planned`/`active`/`completed`/`superseded`）
- `milestone_pipeline_path`: 指向 `.servo/repo/milestone-backlog.md` 的路径指针
- `milestone_history_path`: 指向 `.servo/repo/milestone-history.md` 的路径指针
- `milestone_pipeline_summary`: Pipeline aggregate 快照（planned/active 来自 live backlog，completed/superseded 来自 milestone history）
- `active_milestone_branch`: 当前 active Milestone integration branch 的 routing ref（如存在）
- `active_milestone_continuation_state`: active Milestone 的可继续性镜像（`ready` / `waiting_external` / `paused_by_programmer` / `blocked`）
- `active_milestone_branch_sync_state`: 当前 Milestone branch 相对 baseline 的同步状态摘要，例如 `not_created`、`in_sync`、`needs_baseline_merge`、`conflict`、`unknown`
- `current_branch_context`: 当前 checkout 的 branch context 观测值，合法值为 `baseline` / `milestone` / `worktrack` / `unknown`
- `expected_branch_context`: 当前 Scope / Function 进入 mutating step 前所需的 branch context
- `branch_context_guard_status`: `pass` / `warning` / `blocked` / `unknown`
- `branch_context_required_ref`: 当 guard 需要切换时，记录 control-state 或 Worktrack Contract 指定的目标 ref

`active_milestone` 缺失但 `milestone_pipeline_path` 存在且 pipeline 非空时，表示 pipeline 中有 planned milestone 但尚未激活。设置后 Milestone 进度由 `milestone-status-skill` 独立分析，Pipeline 推进由 `harness-skill` 在收到 `milestone_acceptance_verdict` 后执行，不替代 `RepoScope.Decide` 的决策权。

Milestone final acceptance 写回后，Control State 必须与 `.servo/repo/milestone-backlog.md` 和 `.servo/repo/milestone-history.md` 保持一致：`active_milestone` 只能指向 live backlog 中唯一 `active` milestone；没有 active milestone 时应写为 `none`；`milestone_status` 必须与 active milestone 状态一致或为 `none`；`milestone_pipeline_summary` 的 planned/active 计数必须等于 live backlog 实际条目，completed/superseded 计数必须等于 milestone history 实际条目。若写回后不一致，Harness 必须停在 `writeback_incomplete` / `milestone_pipeline_stale`，不得继续 Worktrack 初始化或 pipeline advancement。

Milestone branch 与 continuation 字段在 Control State 中只是 routing metadata，不是业务真相。权威 branch/pause/resume 事实属于 `.servo/milestone/{milestone_id}.md`，live pipeline 摘要属于 `.servo/repo/milestone-backlog.md`。Control State 不得通过修改 `active_milestone_branch` 或 `active_milestone_continuation_state` 来创建、暂停、恢复或接受 Milestone；必须由 RepoScope Decide/Init/Recover/Close 对正式 artifact 做事务写回。

若 `active_milestone_continuation_state` 为 `waiting_external`、`paused_by_programmer` 或 `blocked`，Harness 不得进入 Worktrack Init/Dispatch，除非正式 Milestone artifact 同时证明 `resume_condition` 已满足并且 RepoScope.Observe 已刷新 baseline 与 Milestone branch head。若暂停 Milestone 释放 active slot，Control State 必须把 `active_milestone` 改为新的唯一 active milestone 或 `none`，并在 handback/last_stop_reason 中记录 transition authority。

## Branch Environment Guard

Branch Environment Guard 是控制平面路由守卫，不是分支真相来源。它消费 `baseline_branch`、`active_milestone_branch` 与当前 Worktrack Contract 的 Branch Policy 字段来判定当前 checkout 是否处在合法变更上下文。

合法上下文：

- `baseline`: 当前 checkout 等于 servo-managed `baseline_branch`。
- `milestone`: 当前 checkout 等于 active Milestone 的 `active_milestone_branch`。
- `worktrack`: 当前 checkout 等于当前 Worktrack Contract 的 `worktrack_branch`。
- `unknown`: 缺少必要字段或当前 checkout 不匹配任何已声明 ref。

Scope / Function 约束：

- RepoScope 只读 Observe / Decide 可在任意上下文观察，但必须记录 `current_branch_context` 和 `branch_context_guard_status`。
- RepoScope 中会改变 baseline、创建 Milestone branch、激活或切换 Milestone 的动作默认要求 `expected_branch_context = baseline`。
- WorktrackScope.Init 对 milestone-derived Worktrack 要求 `expected_branch_context = milestone`，并从 `active_milestone_branch` 创建 `worktrack_branch`；非 milestone-derived Worktrack 要求 `baseline`。
- WorktrackScope.Dispatch / Implement / Verify / Judge 的变更动作要求 `expected_branch_context = worktrack`。
- WorktrackScope.Close / RepoScope.Refresh 使用 Worktrack Contract 的 `closeout_target_ref` / `checkpoint_base_ref`；Milestone-derived Worktrack 的 direct closeout/refresh 可在 `milestone` 上完成，Milestone final acceptance 后才允许合回 `baseline`。

若 `branch_context_guard_status = blocked`，任何 mutating Function 都必须停止。合法恢复路径只能切换到 `branch_context_required_ref` 或重新进入 RepoScope.Observe / Recover；不得从当前分支名、默认分支名或历史习惯推断目标。缺失字段的 conservative runtime backfill 为 `current_branch_context = unknown`、`expected_branch_context = unknown`、`branch_context_guard_status = blocked`，直到正式 artifact 提供足够证据。

## Milestone Review Gate Routing State

Active Milestone 的执行入口复核路由状态也保存在 Control State，但只作为 routing metadata，不保存业务真相。字段默认值必须保守，不得扩大权限。业务事实来自 Milestone artifact 的 `milestone_review_gate` 和 pre-intake 输出的 `milestone_review_gate_handoff`；Control State 只镜像 routing 所需字段：

- `active_milestone_review_gate_status`: `missing`（默认）/`effective_pass`/`questions_required`/`blocked`/`skipped`/`stale`/`invalidated`
- `active_milestone_review_count`: integer，默认 `0`
- `active_milestone_review_checkpoint`: string or `N/A`
- `latest_review_status`: active milestone 最近一次 review 状态的镜像
- `latest_review_checkpoint`: active milestone 最近一次 review checkpoint 的镜像
- `review_invalidated_by`: active milestone review gate 的失效原因镜像
- `active_milestone_review_required`: boolean，goal-driven 默认 `true`
- `active_milestone_review_blockers`: array，默认包含缺失或失效原因

只有当 `active_milestone_review_gate_status = effective_pass`、`active_milestone_review_count >= 1`、`active_milestone_review_checkpoint` 非空且 Milestone artifact 中 `effective_review_pass = true` 时，Control State 才能允许进入 Worktrack Init/Dispatch。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段缺失都必须按 blocked 解释。`worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 改变时，control-state 的 routing state 必须降级为 `invalidated` 或 `stale`，等待新的 `pre_milestone_intake_review` checkpoint。

对于缺失的增量 Milestone Review Gate 字段，保守运行时回填为：`active_milestone_review_gate_status = missing`，`active_milestone_review_count = 0`，`effective_review_pass = false`，`latest_review_checkpoint = N/A`，`milestone_review_gate_ready = false`；目标驱动型 Milestone 的 `active_milestone_review_required = true`，且 `active_milestone_review_blockers` 包含 `milestone_review_gate_not_ready`。这些默认值不得递增 `milestone_review_count`，不得设置 `effective_pass`，且必须阻断 Worktrack Init/Dispatch。

## User-Defined Servo Controls

初始化 Harness 控制平面时，Servo 只应询问用户可定义且会影响后续审批边界的控制变量。默认问题集为：

- `continuous_progression_permission`: 是否允许在已批准 milestone / worktrack 边界内连续推进。
- `per_milestone_automatic_worktrack_budget`: 每个 Milestone 内允许自动连续开启或推进的 Worktrack 额度。
- `default_servo_work_branch`: Servo 默认工作分支或工作分支命名策略。
- `protected_branch_policy`: 不允许 Servo 直接修改、强推、删除或自动合并的受保护分支策略。
- `branch_mutation_policy`: 分支创建、切换、合并、删除与远端推送的默认审批策略。
- `milestone_branch_policy`: Milestone integration branch 命名、创建、baseline sync 与 final merge 的默认策略。

这些字段属于 user-defined controls，应存放在 `User-Defined Servo Controls`、`Continuation Authority` 或等价控制配置段中；它们不是 repo 目标，也不替代 `WorktrackContract`。未回答时必须按保守默认解释：不扩大连续推进权限，不提高自动 Worktrack 额度，不放宽受保护分支规则。

初始化不得向用户询问 Servo 可以自动维护的 runtime facts；模板中以 `auto_maintained_runtime_facts_not_asked` 列出这些禁止提问项，例如 `active_milestone`、`active_worktrack`、`observed_git_hash`、`progress_counters`、`runtime_dispatch_profile`、`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint` 或 `milestone_pipeline_summary`。这些事实由 Observe / Refresh / Dispatch / Close 等控制步骤写回，不能被用户偏好伪装成真相。

一次性执行授权只写入本轮 evidence / handoff / Autonomy Ledger，不得伪装成长期默认。只有用户明确表达持久偏好时，才可更新上述 user-defined controls。

## Low-Risk Default-Flow Autonomy Policy

当 `continuous_progression_permission` 与当前 Milestone / Worktrack 授权允许连续推进时，Harness 仍只能对低风险默认流程静默推进。该策略必须用结构化字段表达：

- `allowed`: 已批准 milestone / worktrack 边界内的只读观察、artifact hydration、状态一致性检查、队列调度、非破坏性文档/模板/测试编辑、匹配范围的本地验证、已通过 Gate 后的 repo-refresh 写回，以及不会产生外部副作用的 scaffold validation。
- `forbidden`: goal change、scope expansion、milestone final acceptance、release / publish / package version / tag / dist-tag 变更、GitHub Release 或 publish workflow、protected branch mutation、force push、大量文件删除、destructive cleanup、secret/security/privacy 处理、deploy/network/database migration、跨 repo 副作用、外部付费/配额消耗，以及任何用户标记为需通知的动作。
- `stop_condition`: 证据缺失或冲突、branch mismatch、Gate soft-fail / hard-fail / blocked、context noise 或提示遗忘明显、需要 programmer 判断、权限边界不清、Worktrack Contract 外扩、protected branch policy 命中、destructive operation 命中、release-sensitive 信号命中、Milestone final acceptance 边界命中。
- `evidence_required`: route decision、Worktrack Contract 与 scope boundary、selected task / dispatch packet、runtime dispatch profile（发生 dispatch 时）、validation / governance / policy evidence、Gate verdict、closeout record、repo-refresh checkpoint（基线变化时）。

低风险静默推进不是默认扩大权限。任一 `forbidden` 或 `stop_condition` 命中时，Harness 必须 handback 或进入审批 / recover 路由；不得用 `allowed` 项覆盖更严格的 authority boundary。一次性连续执行额度只适用于当前批准周期，不能写成长期默认。

若支持 contract-boundary 后自主续跑，还需最小 Continuation Authority 策略位：

- `post_contract_autonomy`: `delegated-minimal`（默认）/`manual-only`（strict handback 诊断）
- `autonomy_scope`: 默认 `current-goal-only`
- `max_auto_new_worktracks`: 默认 `1`，大于 1 为显式 override
- `stop_after_autonomous_slice`: 默认 `yes`
- `subagent_dispatch_mode`: `auto`（默认）/`delegated`/`current-carrier`；repo 级默认值，不遮蔽 worktrack 级策略
- `subagent_dispatch_mode_override_scope`: 默认 `worktrack-contract-primary`；仅 `global-override` 才覆盖 worktrack contract
- `subagent_default_model`: 可选，不改变权限边界
- `runtime_dispatch_profile`: 最近一次 dispatch 能力画像摘要，可包含 `backend_runtime`、`model_family`、`subagent_dispatch_shell`、`runtime_supports_subagent`、`subagent_permission_state`、`permission_allows_delegation`、`dispatch_package_safety`

以上字段属于 control policy，不回答 repo 目标，不替代 `WorktrackContract`。`subagent_dispatch_mode` 是 SubAgent 分派的 repo 级默认策略，语义与 worktrack 级 `runtime_dispatch_mode` 一致：`auto` 按 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier；`delegated` 必须分派否则返回 gap/block；`current-carrier` 关闭分派。若权限边界、运行时缺口或 `dispatch package unsafe` 阻止分派，fallback 原因须写入执行结果或 `gate evidence`，并使用 `runtime fallback` 标记运行时回退。若 runtime 为 ClaudeCodeCLI 或 model family 为 Deepseek 且无法证明 SubAgent shell 可用，必须把 `runtime_dispatch_profile`、`delegation_attempted`、`attempted_carrier`、`carrier_decision` 与 `fallback_reason` 写入本轮 evidence，不得静默使用 current-carrier。

程序员授予的长期权限、自动性或分派策略变更必须写回本 artifact 对应配置段，不得仅停留于对话记忆。一次性审批仅对当前 worktrack、gate 或 destructive action 生效，应写入本轮 `evidence`/`handoff`，不得改变长期默认值。仅当用户明确表达持久授权或更改默认策略时，才可更新 `post_contract_autonomy`、`max_auto_new_worktracks`、`stop_after_autonomous_slice`、`subagent_dispatch_mode`、`subagent_dispatch_mode_override_scope` 或其他长期 authority 字段。若字段语义或默认值改变，须同步更新初始化模板和 canonical skill 说明。

仅有 Continuation Authority 不够——若 handback/re-entry 边界未持久化到下一轮会话，”继续工作”可能被误读为 fresh handoff 并错误新建 worktrack。因此还需 Handback Guard / Autonomy Ledger：

- `handoff_state`: `none`/`awaiting-handoff`/`autonomous-slice-active`
- `last_stop_reason` / `last_handback_signature`
- `handback_reaffirmed_rounds`: 默认 0（阈值 `stable_handback_threshold`，默认 2）
- `handback_lock_active`: 默认 false
- `last_unlock_signal`: N/A 或最近有效解锁描述
- `autonomy_budget_remaining` / `autonomous_worktracks_opened`

以上字段属于 control memory，不替代 `RepoSnapshot/Status`、`WorktrackContract` 或 `GateEvidence`。

此外应保存 Baseline Traceability，用于 `WorktrackScope` 关闭后快速定位已验证基线。git checkpoint 字段（`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint`、`verified_at_history` 与 checkpoint writeback/read scripts 的读写目标）属于 `.servo/control-state-repo.md`；`.servo/control-state.md` 保留跨 scope control memory、权限配置、路由状态和路径指针。

其中 `latest_observed_checkpoint` 与 `last_doc_catch_up_checkpoint` 是 git hash 幂等性锚点，分别记录 `repo-refresh-skill` 和 `worktrack-doc-catch-up-skill` 上次执行时的 HEAD hash，供 `harness-skill` 启动时从 `.servo/control-state-repo.md` 对比以跳过重复刷新。

## Skill Source Baseline Traceability

Canonical skill 源版本事实由 repo 级 checkpoint 正式对象持有，而非散布在 catalog 页面的 prose hash 引用中。对于 `product/harness/skills/`，稳定关系为：

- canonical 源根：`product/harness/skills/`
- docs/catalog 所有者：`docs/harness/catalog/`
- 当前源 checkpoint 所有者：`.servo/repo/snapshot-status.md`（经 `repo-refresh-skill` 后）
- 当前控制平面幂等所有者：`.servo/control-state-repo.md` 的 `Baseline Traceability`

已验证的 worktrack 变更 canonical skill 源、源侧 skill 索引或文档/源码可追溯性时，closeout 记录将证据与合并提交写入其 closeout 记录，随后 `repo-refresh-skill` 将刷新后的 git HEAD 写入 `latest_observed_checkpoint` 和 `checkpoint_ref`。若同一变更同时更新了 operator-facing 文档或版本事实，`worktrack-doc-catch-up-skill` 将该 HEAD 记录为 `last_doc_catch_up_checkpoint`。

长期文档应链接到源根或 catalog 所有者，不应为每个 skill 嵌入一次性 commit hash。若审计交接需要 commit hash，保留在运行时正式对象中，如 closeout 记录、repo snapshot 或 release/version evidence。部署目标是源基线的消费者，不得成为基线所有者。

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
