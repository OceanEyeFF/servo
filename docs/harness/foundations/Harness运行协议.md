---
title: Harness 运行协议
status: active
updated: 2026-05-16
owner: OceanEye
last_verified: 2026-05-16
---

# Harness 运行协议

> 目的：作为 Harness runtime protocol 的当前入口，固定运行协议章节边界和全局不变量。Doctrine 边界见 [Harness指导思想.md](./Harness指导思想.md)；正式对象字段见 [artifact/](../artifact/README.md)。

Harness 是 repo 演进的分层闭环控制协议。它不直接替代执行器，而是决定当前处于哪个 Scope、允许哪个 Function 算子、消费哪些 Artifact、绑定哪个 Skill 或执行载体、需要哪些 Evidence、Gate 是否允许推进，以及失败或阻塞后如何恢复。

## Runtime Chapters

| 章节 | 承接内容 |
| --- | --- |
| [runtime-control-loop.md](./runtime-control-loop.md) | 控制链、Scope 状态、合法算子、连续推进与 stop conditions |
| [runtime-dispatch-contract.md](./runtime-dispatch-contract.md) | Dispatch / Implement 边界、执行载体选择、dispatch packet 与 fallback 语义 |
| [runtime-evidence-gate-recovery.md](./runtime-evidence-gate-recovery.md) | Verify / Judge 分离、Gate verdict、Recover route、handback 与交接锁 |
| [runtime-closeout-refresh.md](./runtime-closeout-refresh.md) | closeout、repo refresh、milestone progress 写回与 pipeline advancement |
| [runtime-state-hydration.md](./runtime-state-hydration.md) | `.servo/control-state.md` 恢复、authority 配置、baseline traceability 与 autonomy ledger |

## Global Runtime Invariants

- `RepoScope` 与 `WorktrackScope` 是不同时间尺度的控制层，不能混成同一份工作状态。
- `Function` 是状态转移算子，`Skill` 是实践绑定，`SubAgent` 或 human 是被调度的执行载体。
- `Control State` 只保存控制面位置、配置和路径指针；业务真相写回 repo / worktrack formal artifacts 与对应源码层。
- `Dispatch` 属控制平面，`Implement` 属执行平面；没有真实委派载体时，不得把 current-carrier fallback 说成 SubAgent 委派。
- `Evidence` 证明当前状态，`Gate` 判断是否允许推进；两者必须分开。
- `PR` 不是闭环终点。完整 closeout 覆盖 `merge -> repo refresh -> milestone progress update -> cleanup -> return RepoScope`。
- 目标变更不由普通 `Decide` 选择，必须走显式 change control。

## SubAgent Dispatch Defaults

默认 dispatch policy 由 [Dispatch Decision Policy](./dispatch-decision-policy.md) 承接；本页只保留 runtime 必备关键词，供 governance 检查和读者定位。

- `subagent_dispatch_mode_override_scope` 默认是 `worktrack-contract-primary`。
- 仅当 override scope 为 `global-override` 时，control-state 的 repo 级设置才压过 Worktrack Contract。
- `subagent_dispatch_mode` / `runtime_dispatch_mode` 支持 `auto`、`delegated`、`current-carrier`。
- `delegated` 表示必须真实委派；无法委派时返回运行时缺口或权限边界阻塞。
- `auto` 的 fallback 必须记录为 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe`。
- 权限边界不明确时，不得扩大委派、执行或自动继续权限。

## Owner Boundaries

| 主题 | Owner |
| --- | --- |
| Doctrine / why Harness exists | [Harness指导思想.md](./Harness指导思想.md) |
| Scope state matrices | [../scope/README.md](../scope/README.md) |
| Formal object fields and schemas | [../artifact/README.md](../artifact/README.md) |
| Dispatch carrier policy | [dispatch-decision-policy.md](./dispatch-decision-policy.md) |
| Cross-skill common constraints | [skill-common-constraints.md](./skill-common-constraints.md) |
| Skill inventory and executable source links | [../catalog/README.md](../catalog/README.md) |
| Workflow family policy | [../workflow-families/README.md](../workflow-families/README.md) |
| Project maintenance governance and review/verify rules | [../../project-maintenance/governance/review-verify-handbook.md](../../project-maintenance/governance/review-verify-handbook.md) |

Unpromoted proposal or migration comparison stays in Harness runtime/backlog or worktrack evidence until verified and promoted into the correct owner. Runtime protocol chapters do not own artifact fields, catalog inventory, workflow-family policy, deployment rules, or executable source.

## Runtime Reading Path

1. Read [Harness指导思想.md](./Harness指导思想.md) for doctrine.
2. Read this page to choose the runtime chapter.
3. Read [runtime-control-loop.md](./runtime-control-loop.md) for the normal loop and continuous execution rules.
4. Read [runtime-dispatch-contract.md](./runtime-dispatch-contract.md) when selecting execution carriers or interpreting dispatch packets.
5. Read [runtime-evidence-gate-recovery.md](./runtime-evidence-gate-recovery.md) for evidence, gate, handback, and recovery semantics.
6. Read [runtime-closeout-refresh.md](./runtime-closeout-refresh.md) for merge, refresh, cleanup, milestone progress, and pipeline advancement.
7. Read [runtime-state-hydration.md](./runtime-state-hydration.md) when starting or resuming a Harness round from `.servo/control-state.md`.

## 判断标准

协议清楚时，应同时满足：

- 每个状态只允许有限合法算子。
- `Function -> Skill -> SubAgent/current-carrier` 的绑定边界明确。
- `subagent_dispatch_mode` 与 `runtime_dispatch_mode` 是可开关合同。
- Evidence 与 Gate 分开。
- Gate fail 有明确 recovery route。
- Closeout 以 repo refresh 和回到 RepoScope 结束。
