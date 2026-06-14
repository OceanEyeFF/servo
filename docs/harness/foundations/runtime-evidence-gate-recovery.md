---
title: Harness Runtime Evidence Gate Recovery
status: active
updated: 2026-05-16
owner: servo-kernel
last_verified: 2026-06-13
---

# Harness Runtime Evidence Gate Recovery

> 目的：固定 Verify、Judge、Recover、handback 与交接锁的运行语义。Evidence 字段见 [gate-evidence.md](../artifact/worktrack/gate-evidence.md)，Control State 字段见 [control-state.md](../artifact/control/control-state.md)。

## Verify And Gate

`Verify` 收集证据，`Judge` 做放行裁决。二者独立。

最小证据面：

- implementation / review
- validation / test
- policy / governance
- artifact freshness

最小 verdict：

- `pass`
- `soft-fail`
- `hard-fail`
- `blocked`

Gate 输出至少包含：

- verdict
- route decision
- evidence 摘要
- unresolved risks
- required recovery 或 next route

缺失证据的唯一合法处理方式是显式暴露缺口。不得把缺失证据当成隐式成功。

## Recover

Recover 只在 gate、状态估计或 authority boundary 阻断时触发。

合法恢复动作：

- `retry`
- `replan`
- `rollback`
- `split-worktrack`
- `refresh-baseline`
- `return RepoScope`
- `wait-for-approval`

恢复动作说明必须覆盖：

- 触发原因
- 保留的 artifact
- 废弃的 artifact
- 是否需要用户确认
- 回到哪个 Scope / Function

破坏性操作、范围扩张或目标重定义必须触发 programmer approval。

## Handback Triggers

Handback 在以下条件触发：

- 审批门控：需要 programmer 批准的 goal change、scope expansion、destructive action 或 authority boundary
- 证据门控：必需 artifact / evidence 缺失、过时或冲突，且无法在本轮自动补齐
- 路由阻塞：`Gate` 给出 `soft-fail` / `hard-fail` / `blocked`，且 Recover 无法自动恢复
- 运行时缺口：host runtime 缺少合法 execution carrier / dispatch shell
- 约定边界：下一动作越过已批准输入、`Worktrack Contract` 或 repo baseline
- 稳定交接：同一交接边界在连续无变化轮次中被再次确认

## Stable Handback And Unlock Signal

stable-handback 指同一交接边界在连续 `handback_reaffirmed_rounds` 轮次中被再次确认。默认阈值 `stable_handback_threshold = 2`。

一旦 stable-handback 达成，运行时进入 `handoff_state = awaiting-handoff`，`handback_lock_active = true`，所有控制回路阶段进入阻断状态。

有效 unlock signal 必须满足以下至少之一：

- 新目标或新 scope 声明
- 对阻塞原因的实质性分析或新信息
- 显式权限授予或策略变更
- 明确的新任务指令

裸"重试"、裸"继续工作"或重复文字摘要不构成 unlock signal。

## Handback Re-entry

下一轮启动时，Harness 必须从 `last_handback_signature` 恢复 handback 上下文。不得将 handback 误读为 fresh handoff。

re-entry 时：

- 若 `handback_lock_active = true`，先验证 unlock signal 有效性，再决定是否解除交接锁
- 若 `handback_lock_active = false`，按 `handoff_state` 与 `continuation_authority` 决定是续跑还是等待
- 不得在 lock active 状态下跳过交接锁验证直接进入新的 worktrack
