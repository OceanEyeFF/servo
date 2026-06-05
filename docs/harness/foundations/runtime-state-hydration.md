---
title: Harness Runtime State Hydration
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
---

# Harness Runtime State Hydration

> 目的：固定 Harness 启动或恢复时如何从 `.servo/control-state.md` 恢复控制配置。字段合同见 [control-state.md](../artifact/control/control-state.md)。

## Hydration First

每次 Harness 启动先读取 `.servo/control-state.md`，恢复控制配置，再判断 Scope / Function。

最小读取面：

- Linked Formal Documents
- Approval Boundary
- Continuation Authority
- Handback Guard
- Baseline Traceability
- Autonomy Ledger

缺失配置按 [control-state.md](../artifact/control/control-state.md) 默认值降级，输出暴露 `config_hydration_gaps`。不得因字段缺失扩大自动性、绕过审批或忽略上次 handback 边界。

## Control State Boundary

`Control State` 只保存控制面状态、路径指针、配置和可复核的 traceability metadata。它不承载 repo 目标、worktrack 业务真相或未验证结论。

业务真相写入：

- repo formal artifacts
- worktrack formal artifacts
- docs truth layer
- product / toolchain source layer

`.servo/` 是 repo-local runtime control-plane state，不替代 `docs/`、`product/` 或 `toolchain/`。

## Authority Updates

如果 programmer 给出长期权限、自动性或分派策略变更，Harness 必须区分一次性审批和持久配置。

- 一次性审批写入本轮 evidence / handoff
- 持久配置变更写入 `.servo/control-state.md` 对应 policy / ledger 字段
- 改变 canonical 字段语义或默认值时，同步更新 control-state artifact 合同与初始化模板

仅当用户明确表达持久授权或更改默认策略时，才可更新长期 authority 字段。

## Baseline Traceability

Harness 使用 git commit hash 作为幂等性锚点，避免对同一代码基线重复执行 repo refresh 和 doc catch-up。

| 字段 | 含义 |
| --- | --- |
| `latest_observed_checkpoint` | 上次 repo refresh 后记录的 git HEAD hash |
| `last_doc_catch_up_checkpoint` | 上次 doc catch-up 后记录的 git HEAD hash |
| `milestone_input_checkpoint` | Milestone Observe 输入指纹 |
| `verified_at` | 最近一次 checkpoint 验证时间 |

git hash 一致只授权跳过重复 refresh 或重复 doc catch-up；首次验证、worktrack gate 和 milestone gate 不可跳过。

## Re-entry Decision

恢复时按以下顺序判断：

1. control-state 是否存在并可读。
2. handback guard 是否激活。
3. 当前 checkout 的 `branch_context` 是否能由 `baseline_branch`、`active_milestone_branch` 或当前 Worktrack Contract 的 `worktrack_branch` 解析。
4. active milestone / active worktrack 指针是否存在并指向有效 artifact。
5. continuation authority 是否允许自动继续。
6. 下一合法 Scope / Function 是否仍在批准边界内。

任一项不可判定时，暴露阻塞项并停在安全的 Observe 或 handback 状态。

`latest_observed_checkpoint` 仍是 repo-refresh 幂等性锚点，但它必须和 branch context 一起解释：Milestone-derived Worktrack 的最新 checkpoint 可以位于 Milestone integration branch，不能因为当前 checkout 不是 `baseline_branch` 就自动判定为非法；也不能因为 hash 一致就跳过 Branch Environment Guard。
