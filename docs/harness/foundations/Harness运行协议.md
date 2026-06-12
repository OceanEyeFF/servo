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
| [runtime-control-loop.md](./runtime-control-loop.md) | 控制链、Scope 状态、合法算子、连续推进与停止条件（stop conditions） |
| [runtime-dispatch-contract.md](./runtime-dispatch-contract.md) | Dispatch / Implement 边界、执行载体选择、分发包（dispatch packet）与回退（fallback）语义 |
| [runtime-evidence-gate-recovery.md](./runtime-evidence-gate-recovery.md) | Verify / Judge 分离、准入条件判定（Gate verdict）、恢复路径（Recover route）、交回（handback）与交接锁 |
| [runtime-closeout-refresh.md](./runtime-closeout-refresh.md) | 收尾（closeout）、仓库刷新（repo refresh）、里程碑进度（milestone progress）写回与流水线推进（pipeline advancement） |
| [runtime-state-hydration.md](./runtime-state-hydration.md) | `.servo/control-state.md` 恢复、授权（authority）配置、基准点可追溯性（Baseline Traceability）与自主行为台账（Autonomy Ledger） |

## Global Runtime Invariants

- `RepoScope` 与 `WorktrackScope` 是不同操作粒度的控制层，不能混成同一份工作状态。
- `Function` 是状态转移算子，`Skill` 是实践绑定，`SubAgent` 或 human 是被调度的执行载体。
- `Control State` 只保存控制平面位置、配置和路径指针；业务真相写回 repo / worktrack formal artifacts 与对应源码层。
- `Dispatch` 属控制平面，`Implement` 属执行平面；没有真实分派载体时，不得把 current-carrier fallback 说成 SubAgent 分派。
- `Evidence` 证明当前状态，`Gate` 判断是否允许推进；两者必须分开。
- `PR` 不是闭环终点。完整 closeout 覆盖 `merge -> repo refresh -> milestone progress update -> cleanup -> return RepoScope`。
- 目标变更不由普通 `Decide` 选择，必须走显式 change control。

## SubAgent Dispatch Defaults

默认 dispatch policy 由 [Dispatch Decision Policy](./dispatch-decision-policy.md) 承接；本页只保留 runtime 必备关键词，供 governance 检查和读者定位。

- `subagent_dispatch_mode_override_scope` 默认是 `worktrack-contract-primary`。
- 仅当 override scope 为 `global-override` 时，control-state 的 repo 级设置才覆盖 Worktrack Contract。
- `subagent_dispatch_mode` / `runtime_dispatch_mode` 支持 `auto`、`delegated`、`current-carrier`。
- `delegated` 表示必须真实分派；无法分派时返回运行时缺口或权限边界阻塞。
- `auto` 的 fallback 必须记录为 `runtime fallback`（运行时回退）、`permission blocked`（权限阻断）或 `dispatch package unsafe`（分派包不安全）。
- 权限边界不明确时，不得扩大分派、执行或自动继续权限。

## Owner Boundaries

| 主题 | Owner |
| --- | --- |
| 指导思想 / Harness 存在理由 | [Harness指导思想.md](./Harness指导思想.md) |
| Scope 状态矩阵 | [../scope/README.md](../scope/README.md) |
| 正式对象字段与模式（schema） | [../artifact/README.md](../artifact/README.md) |
| 分派载体策略 | [dispatch-decision-policy.md](./dispatch-decision-policy.md) |
| 跨 skill 公共约束 | [skill-common-constraints.md](./skill-common-constraints.md) |
| Skill 清单与可执行源链接 | [../catalog/README.md](../catalog/README.md) |
| 工作流族策略 | [../workflow-families/README.md](../workflow-families/README.md) |
| 项目维护治理与 review/verify 规则 | [../../project-maintenance/governance/review-verify-handbook.md](../../project-maintenance/governance/review-verify-handbook.md) |

运行时协议各章节不拥有 artifact 字段、catalog inventory、workflow-family policy、deployment rules 或 executable source 的所有权。

## 运行时阅读路径（Runtime Reading Path）

1. 阅读 [Harness指导思想.md](./Harness指导思想.md) 了解指导思想。
2. 阅读本页选择运行时章节。
3. 阅读 [runtime-control-loop.md](./runtime-control-loop.md) 了解常规控制回路与连续执行规则。
4. 选择执行载体或解读分发包时，阅读 [runtime-dispatch-contract.md](./runtime-dispatch-contract.md)。
5. 阅读 [runtime-evidence-gate-recovery.md](./runtime-evidence-gate-recovery.md) 了解证据收集、准入条件判定、交回与恢复的语义。
6. 阅读 [runtime-closeout-refresh.md](./runtime-closeout-refresh.md) 了解合并、刷新、清理、里程碑进度与流水线推进。
7. 从 `.servo/control-state.md` 启动或恢复 Harness 回合时，阅读 [runtime-state-hydration.md](./runtime-state-hydration.md)。

## 判断标准

协议清晰时，应同时满足：

- 每个状态只允许有限合法算子。
- `Worktrack` 初始化前必须完成至少一次有效 `Milestone` review gate 复核。
- `Function -> Skill -> SubAgent/current-carrier` 的绑定边界明确。
- `subagent_dispatch_mode` 与 `runtime_dispatch_mode` 是非自动维护的变量，可以切换这些变量的值来改动 skills 的默认工作方式。
- Evidence 与 Gate 分开。
- Gate fail 有明确 recovery route。
- Closeout 以 repo refresh 和回到 RepoScope 结束。
