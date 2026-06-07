---
title: "Harness Skill Catalog / WorktrackScope"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
---
# WorktrackScope Skill Catalog

> 目的：固定 `WorktrackScope` 下直接面向 `Codex` 的 Harness skills catalog。

这里记录的是 worktrack 闭环里实际会被 supervisor 选择和调用的 skills。

## 原则

`WorktrackScope` skills 负责局部状态转移闭环，消费 contract/plan/evidence/control state，可派发下游 `SubAgent` 但不伪装成”控制平面+执行平面一体”。schedule-worktrack-skill 是 `selected_next_action` 与 dispatch handoff packet 的唯一 authority；dispatch-skills 只消费 scheduling packet 不反向改写 queue。generic-worker-skill 是无专用 skill 时的通用执行载体；doc-catch-up-worker-skill 是 Harness 入口观察和 closeout 前推荐使用的文档基线追平载体，release / publish / version / VCS tracking 事实变化后也必须承担 version fact sync。freshly seeded 或 autonomous continuation 的首个 execution-facing round，初始 slice 必须先收紧到最小可验证子片段。`runtime_dispatch_mode` 读取顺序：默认 worktrack-contract-primary 下 contract 的 `runtime_dispatch_mode` 优先；仅 global-override 时 control-state 覆盖；contract 未声明时使用 control-state 默认值。control-state 的 `subagent_dispatch_mode` 与 `subagent_dispatch_mode_override_scope` 只提供 repo 级默认和覆盖边界。`runtime_dispatch_mode` 支持 `auto`/`delegated`/`current-carrier`，默认 `auto`；无法委派需记录 runtime fallback 和 dispatch package unsafe 等边界事实。

Worktrack Contract 的 `node_type` 字段合法值来自 [Node Type Registry](../artifact/control/node-type-registry.md)，Contract 中的 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` 从 Registry 继承默认值并可在 Contract 中显式覆盖；gate-skill 根据 `node_type` 查找对应 `gate_criteria` 确定需要收集的证据面。

Worktrack Contract 还拥有 Branch Policy 字段：`baseline_branch` 表示 servo-managed final baseline；`branch_source_ref` 表示 Worktrack branch 从哪里创建；`integration_target_ref` / `closeout_target_ref` 表示 closeout 直接合入哪里。Milestone-derived Worktrack 默认从 active Milestone branch 创建并合回该 Milestone branch，Milestone final acceptance 后再由 Milestone closeout 合回 baseline branch。下游 init/close/refresh skills 不得从当前 checkout 或默认分支名推断这些目标。

## Catalog

### 0. worktrack-status-skill

职责：在 `WorktrackScope.Observe` 阶段读取当前 Worktrack Contract、Plan / Task Queue、Gate Evidence 与相关控制态，形成结构化工作追踪状态估计。它只做状态观察，不选择下一任务、不执行实现、不裁决 Gate。

主要依赖：

- `Worktrack Contract`
- `Plan / Task Queue`
- `Gate Evidence`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/worktrack-status-skill/SKILL.md](../../../product/harness/skills/worktrack-status-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 1. init-worktrack-skill

职责：创建 bounded branch、初始化 baseline 和 Worktrack Contract、建立最小 Plan/Task Queue、产出面向 schedule-worktrack-skill 的 seed/handoff 而非新鲜权威 dispatch packet。

主要依赖：

- `Worktrack Contract`
- `Plan / Task Queue`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/init-worktrack-skill/SKILL.md](../../../product/harness/skills/init-worktrack-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred initialization fields：

- `worktrack_id`
- `initial_queue_items`
- `queue_seed_status`
- `schedule_handoff_packet`
- `recommended_next_route`
- `approval_required`

### 2. schedule-worktrack-skill

职责：根据当前 contract/验收/证据/阻塞刷新任务队列，决定当前下一动作；首个 execution-facing round 优先选择最小可验证 acceptance slice 而非端到端包；显式说明当前动作与剩余队列如何对齐验收条件；产出唯一权威的 dispatch handoff packet。

主要依赖：

- `Worktrack Contract`
- `Plan / Task Queue`
- `Gate Evidence`

canonical executable source：

- [../../../product/harness/skills/schedule-worktrack-skill/SKILL.md](../../../product/harness/skills/schedule-worktrack-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred scheduling fields：

- `selected_next_action_id`
- `selected_next_action`
- `slice_boundary_reason`
- `dispatch_task_brief_draft`
- `dispatch_info_packet_draft`
- `dispatch_packet_ready`
- `recommended_next_route`

### 3. dispatch-skills

职责：接收 Worktrack 的下一任务，校验 scheduling handoff packet，拒收 oversized packet 退回 schedule-worktrack-skill。优先选择语义匹配的专门 skill；无专门 skill 时 fallback 到 generic-worker-skill 或 current-carrier。文档追平优先绑定 doc-catch-up-worker-skill。按 runtime_dispatch_mode 选择载体：auto 按 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier；delegated 必须委派否则返回 gap/block；current-carrier 显式关闭委派。跑一轮 bounded execution 并回传 evidence。

主要依赖：

- `Worktrack Contract`
- `Plan / Task Queue`
- `Harness Control State`
- 当前任务相关的最小上下文

dispatch contract：Dispatch Task Brief（task/goal/in_scope/out_of_scope/constraints/acceptance_criteria_for_this_round/atomicity_justification/verification_requirements/done_signal）；Dispatch Info Packet（current_worktrack_state/acceptance_alignment_used/relevant_artifacts/required_context/shared_fact_pack/context_budget/known_risks/executor_candidates/fallback_reason）；Dispatch Result（selected_executor/selection_reason/dispatch_policy_ref/carrier_decision/decision_inputs/fallback_used/dispatch_packet_status/packet_boundedness_verdict/dispatch_contract_gaps/actions_taken/files_touched_or_expected/evidence_collected/open_issues/recommended_next_action）。字段定义和继承规则的权威来源见 [Dispatch Packet Schema](../artifact/worktrack/dispatch-packet.md)。

选择规则：只有专门 skill 对当前 work item 有清晰语义贴合时才优先绑定；否则 fallback 到 generic-worker-skill 且不得扩大 scope 或绕过 verification_requirements。文档追平优先绑定 doc-catch-up-worker-skill。handoff packet 缺失/不完整或已膨胀成多 slices/多队列项时，必须退回 schedule-worktrack-skill。

canonical executable source：

- [../../../product/harness/skills/dispatch-skills/SKILL.md](../../../product/harness/skills/dispatch-skills/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 4. generic-worker-skill

职责：接收限定范围 Prompt 并在当前权限边界内完成实现/修复/调查/验证任务，作为无专用 skill 时的通用执行载体，避免 Harness 主控制器吸收执行责任。返回执行报告、触及文件、验证结果和残留风险。

主要依赖：

- `Dispatch Task Brief`
- `Dispatch Info Packet`
- 当前任务相关的最小上下文

canonical executable source：

- [../../../product/harness/skills/generic-worker-skill/SKILL.md](../../../product/harness/skills/generic-worker-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 5. doc-catch-up-worker-skill

职责：将已验证实现事实追平到正确长期文档层，清理旧路径/数量/命令/流程/边界描述，在 Harness 入口观察和 closeout 前降低后续开发引用过期上下文的风险。版本相关工作中还负责 version fact sync：区分 source version、published version、VCS tracking facts 与 docs freshness，在 harness entry observation、pre-publish readiness、post-publish verification、post-smoke closeout、harness closeout 或 failed publish/rollback 后同步 registry dist-tag、published version、gitHead、tarball、approval lock、selector、git commit/tag/branch 与 SVN revision（如适用）事实。追平成功后必须把当前 HEAD 写回 `Harness Control State` 的 `Baseline Traceability.last_doc_catch_up_checkpoint`；字段为空表示从未建立文档追平幂等锚点，不得作为跳过追平的依据。

主要依赖：

- 当前 diff 与验证证据
- source version facts 与 published version facts
- VCS tracking facts（git 或 SVN）
- `docs/project-maintenance/`
- `docs/harness/`
- 相关入口页和承接层正文

checkpoint writeback:

- `last_doc_catch_up_checkpoint`: doc-catch-up 成功后的 git HEAD；空值表示未执行过文档追平或锚点未知
- `checkpoint_ref`: 与该 HEAD 对应的 branch/ref 描述
- `verified_at`: 本次追平验证日期

canonical executable source：

- [../../../product/harness/skills/doc-catch-up-worker-skill/SKILL.md](../../../product/harness/skills/doc-catch-up-worker-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`
- `version fact sync mode landed; harness entry should mark freshness risk, and release closeout should call this skill after registry verification and before final handback`

### 6. review-evidence-skill

职责：按 `review_profile` 选择并行 review SubAgent lanes，而不是所有改动固定四路执行。`light` 只跑 `static-semantic-review`；`standard` 增加 `test-review`；`risky` 增加 `project-security-review`；`deep` 使用四路 review（static-semantic-review、test-review、project-security-review、complexity-performance-review），分别覆盖静态语义解释、测试 review、security review、代码复杂度和性能 review。运行时无法委派所选 lanes 时记录 fallback，汇总 code review/静态检查/结构评估结果，形成 review lane envelope 供 gate 汇总，对低严重度噪声做截断并将重复症状标为可能的上游约束问题。

主要依赖：

- `Gate Evidence`

canonical executable source：

- [../../../product/harness/skills/review-evidence-skill/SKILL.md](../../../product/harness/skills/review-evidence-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred review-lane fields：

- `lane_id`
- `review_profile`
- `light`
- `standard`
- `risky`
- `deep`
- `review_subagent_lanes`
- `static-semantic-review`
- `test-review`
- `project-security-review`
- `complexity-performance-review`
- `freshness`
- `lane_verdict`
- `confidence_reason`
- `low_severity_absorption_applied`
- `ready_for_gate`

### 7. test-evidence-skill

职责：汇总测试执行结果与验收条件覆盖情况，形成 validation lane envelope。

主要依赖：

- `Gate Evidence`
- `Worktrack Contract`

canonical executable source：

- [../../../product/harness/skills/test-evidence-skill/SKILL.md](../../../product/harness/skills/test-evidence-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred validation-lane fields：

- `lane_id`
- `freshness`
- `lane_verdict`
- `confidence`
- `confidence_reason`
- `ready_for_gate`

### 8. rule-check-skill

职责：检查项目规则、边界和治理约束，形成 policy 证据面。

主要依赖：

- `Gate Evidence`
- repo governance rules

canonical executable source：

- [../../../product/harness/skills/rule-check-skill/SKILL.md](../../../product/harness/skills/rule-check-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 9. gate-skill

职责：汇总 review/test lane envelopes（兼容 policy 旧入口），生成当前 round 的 gate verdict，吸收低严重度 residual risks，命中上游约束信号时强制改道路由。

主要依赖：

- `Gate Evidence`

canonical executable source：

- [../../../product/harness/skills/gate-skill/SKILL.md](../../../product/harness/skills/gate-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

preferred gate fields：

- `required_evidence_lanes`
- `evidence_lanes`
- `overall_confidence`
- `freshness_blockers`
- `allowed_next_routes`
- `recommended_next_route`

### 10. recover-worktrack-skill

职责：在 gate fail 或 blocked 时选择重试、回滚、拆分或刷新 baseline。

主要依赖：

- `Gate Evidence`
- `Plan / Task Queue`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/recover-worktrack-skill/SKILL.md](../../../product/harness/skills/recover-worktrack-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`

### 11. close-worktrack-skill

职责：处理 PR -> merge -> cleanup -> repo refresh handoff，明确 closeout 后的下一层级动作。

主要依赖：

- `Gate Evidence`
- `Harness Control State`

canonical executable source：

- [../../../product/harness/skills/close-worktrack-skill/SKILL.md](../../../product/harness/skills/close-worktrack-skill/SKILL.md)

当前状态：

- `initial canonical executable skeleton landed`
