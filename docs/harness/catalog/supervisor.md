---
title: "Harness Skill Catalog / Supervisor"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-13
---
# Supervisor Skill Catalog

> 目的：固定顶层 Harness supervisor skill 的职责与承接位。

## Canonical skill

### harness-skill

职责：启动时先从既有 `.servo/control-state.md` hydration 控制配置与上次交接边界，然后判断当前在 RepoScope 还是 WorktrackScope，按合法状态转移连续推进直到 stop condition；优先消费下游 rounds 返回的结构化 route/continuation/approval 字段而非 prose；汇总已完成的 rounds、证据、状态和下一步建议；只在 authority boundary 或其他 formal stop condition 停下。Branch Environment Guard 必须把当前 checkout 判定为 `baseline`、`milestone`、`worktrack` 或 `unknown`，再按 Scope / Function 与 Worktrack Contract Branch Policy 决定是否允许 mutating step。只有 control state 显式授予 post_contract_autonomy: delegated-minimal 时才允许 contract-boundary 后自动开启同 goal 的最小 follow-up worktrack。连续无状态增量的 handback rounds 应优先返回 stable-handback 而非无限重跑；stable-handback 成立后保持在 awaiting-handoff 直到检测到明确 unlock signal。长期权限、自动性或分派策略变更必须写回 control-state 配置段；一次性审批只进入本轮 evidence / handoff。

入口 profile 只是 route hint：`harness-skill` 仍是唯一闭环 supervisor。profile 可以影响 workflow path、停顿点和审批提示，但不创建第二 controller，不拥有独立 Gate，不写长期 truth，不绕过 Worktrack Contract，也不把 candidate milestone / candidate worktrack 解释成已批准范围。

operator mode matrix 是该单入口的触发语义摘要，不是新状态机。它根据 trigger signals 把输入投影到 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive，并只影响 route estimate 与 stop/approval semantics。candidate milestone、candidate worktrack、suggested task、profile 和 operator-facing mode 都是 not approved scope，必须经过正式 artifact 与 programmer confirmation 才能变成 live milestone、Worktrack Contract 或执行任务。

canonical executable source：

- [../../../product/harness/skills/harness-skill/SKILL.md](../../../product/harness/skills/harness-skill/SKILL.md)

固定输出：

- `Harness Turn Report`

preferred continuation fields：

- `allowed_next_routes`
- `recommended_next_route`
- `continuation_ready`
- `continuation_blockers`
- `approval_required`
- `approval_scope`
- `approval_reason`
- `autonomous_continuation_used`
- `stable_handback_detected`
- `handback_state`
- `handback_lock_active`
- `unlock_signal_detected`
- `config_hydration_gaps`
- `persistent_authority_updates`
- `current_branch_context`
- `expected_branch_context`
- `branch_context_guard_status`
- `branch_context_required_ref`

兼容说明：

- `recommended_next_action`
- `needs_approval`
- `approval_to_apply`

这些旧字段保留为兼容投影，不作为新的 canonical 读口。

这是唯一已落地的 Harness canonical skill；其余 skills 仍停留在 catalog target 层。contract-boundary 后是否允许再开一段 bounded slice 应由 control-state 的 Continuation Authority 策略位控制，不靠 human 每轮重复写长 prompt。bare "继续工作"不应天然清除 handback lock；无新批准/新状态/新 policy 时 supervisor 应稳定停在 handback/awaiting-handoff。
