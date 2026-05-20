# Harness Foundations

`docs/harness/foundations/` 承接 Harness 的 thought layer：指导思想、runtime protocol、跨 skill 公共约束和执行载体选择策略。

本目录只回答 Harness 为什么这样运行、运行时共同遵守哪些原则、以及控制面如何选择载体和推进状态。Artifact 字段、scope 状态矩阵、skill inventory、workflow-family policy 和 executable source 不在本目录重复承接。

## 当前入口

| 路径 | 功能 |
| --- | --- |
| [Harness指导思想.md](./Harness指导思想.md) | Doctrine 主文档：固定 Harness 是什么、控制什么、不是什么 |
| [Harness运行协议.md](./Harness运行协议.md) | Runtime protocol 索引：选择控制循环、dispatch、gate/recovery、closeout 和 hydration 章节 |
| [runtime-control-loop.md](./runtime-control-loop.md) | 控制链、Scope 状态、合法算子、连续推进与 stop conditions |
| [runtime-dispatch-contract.md](./runtime-dispatch-contract.md) | Dispatch / Implement 边界、执行载体选择、dispatch packet 与 fallback 语义 |
| [runtime-evidence-gate-recovery.md](./runtime-evidence-gate-recovery.md) | Verify / Judge 分离、Gate verdict、Recover route、handback 与交接锁 |
| [runtime-closeout-refresh.md](./runtime-closeout-refresh.md) | closeout、repo refresh、milestone progress 写回与 pipeline advancement |
| [runtime-state-hydration.md](./runtime-state-hydration.md) | `.servo/control-state.md` 恢复、authority 配置、baseline traceability 与 autonomy ledger |
| [dispatch-decision-policy.md](./dispatch-decision-policy.md) | `dispatch_mode: auto` 的执行载体选择策略 |
| [skill-common-constraints.md](./skill-common-constraints.md) | 所有 Harness Skills 的公共约束定义（C-1 至 C-7） |

## Owner Boundaries

| 主题 | 权威入口 |
| --- | --- |
| Doctrine / 指导思想 | [Harness指导思想.md](./Harness指导思想.md) |
| Runtime protocol / 运行协议 | [Harness运行协议.md](./Harness运行协议.md) |
| Scope docs / 状态管理 | [../scope/README.md](../scope/README.md) |
| Artifact contracts / 正式对象字段 | [../artifact/README.md](../artifact/README.md) |
| Catalog inventory / skill 清单 | [../catalog/README.md](../catalog/README.md) |
| Workflow policy / workflow family | [../workflow-families/README.md](../workflow-families/README.md) |
| Executable skill surfaces / 可执行技能源 | [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md) |

未升格的方案分析、迁移比较或实现前设计不作为当前 docs truth 层长期保留；先留在 Harness runtime/backlog 或工作追踪证据中，等内容验证后再升格到对应 owner。
