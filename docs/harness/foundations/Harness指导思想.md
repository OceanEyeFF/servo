---
title: Harness 指导思想
status: active
updated: 2026-05-08
owner: OceanEye
last_verified: 2026-05-08
---

# Harness 指导思想

> 目的：固定 Harness 的 doctrine 边界。本文只回答"它是什么、控制什么"。运行细节见 [Harness运行协议.md](./Harness运行协议.md)。

## 一、总定义

**Harness 是对 Repo 演进的分层闭环控制系统。**

它在 `Repo` 层维护长期基线与系统不变量，在 `Worktrack` 层约束局部状态转移。通过 `Evidence + Gate` 判断状态是否允许推进。

Harness 关注的核心问题：

- 状态和目标状态之间有什么偏差
- 哪个状态转移算子是合法下一步
- 由什么执行器改变系统状态
- 凭什么证据允许推进
- 失败、漂移或阻塞时如何恢复控制

## 二、非目标

Harness 不是：

- 直接编码的主体
- 已批准输入或工作追踪合同的替代物
- backend 的 repo-local runtime wrapper
- 把 skill 顺序串起来的 open-loop 流程图
- 在常规控制里随意改写目标的任务管理器

目标变更属于参考信号重设，必须走 `Goal Change Request`。

## 三、两层控制对象

Harness 只覆盖两个控制层。

| 层 | 作用 | 典型关注点 |
| --- | --- | --- |
| `Repo` | 慢变量，维护长期参考信号 | repo goal、主线现状、架构地图、活跃分支、治理状况、系统不变量、已知风险 |
| `Worktrack` | 快变量，管理局部状态转移 | 任务目标、scope、non-goals、验收、baseline 差异、任务队列、回滚和恢复路径 |

`Repo` 与 `Worktrack` 不能混成同一份"工作状态"。

## 四、三轴模型

Harness 按三条正交轴组织：

| 轴 | 回答的问题 | 典型值 |
| --- | --- | --- |
| `Scope` | 在什么层上控制 | `RepoScope`、`WorktrackScope` |
| `Function` | 控制器此刻做什么 | `Observe`、`Decide`、`Init`、`Dispatch`、`Verify`、`Judge`、`Recover`、`Close` |
| `Artifact` | 控制器依赖什么正式对象 | `Goal / Charter`、`Snapshot / Status`、`Contract`、`Plan / Task Queue`、`Evidence`、`Control State`、`ChangeRequest`、`AppendRequest` |

关键约束：

- `Function` 不是 skill 名，而是状态转移算子。
- `Skill` 是算子在 `Codex / Claude` 中的相对稳定实现。
- `SubAgent` 或 human 是被 Harness 调度的执行载体。
- `Control State` 只保存控制面位置，不承载业务真相。

## 五、控制平面与执行平面

Harness 本体属于控制平面。

控制平面负责：

- 选择下一步合法算子
- 绑定 skill 或执行载体
- 定义证据面
- 裁决状态能否推进
- 在失败时安排恢复动作

执行平面负责：

- 编码
- review
- 测试
- 合并、回滚、清理
- 文档更新

实践层使用 `dispatch-subtask`、`execute-via-agent` 或明确的 `runtime fallback` 表达执行边界。

## 六、核心正式对象

Harness 依赖的正式对象：

| 对象 | 职责 |
| --- | --- |
| `Repo Goal / Charter` | 定义长期目标、成功标准、系统不变量与 `Engineering Node Map` |
| `Repo Snapshot / Status` | 描述 repo 慢变量状态 |
| `Worktrack Contract` | 定义单个 worktrack 的目标、scope、验收、约束与回滚条件 |
| `Plan / Task Queue` | 把 contract 展开成可执行子任务序列 |
| `Gate Evidence` | 保存 review / validation / policy 等证据面 |
| `Harness Control State` | 保存控制级别、活跃 worktrack、baseline 和下一动作 |
| `Goal Change Request` | 管理目标变更影响分析、确认与单独 gate |
| `Append Request` | 对追加 milestone / feature / design 请求做分类与路由 |

字段细节以 [artifact/](../artifact/README.md) 和 [Harness运行协议.md](./Harness运行协议.md) 为准。

## 七、Evidence 与 Gate

Harness 必须同时具备 `Evidence` 与 `Gate`。

- `Evidence` 证明"状态是什么"。
- `Gate` 判断"状态是否允许推进"。

二者分开，避免退化为无裁决能力的执行日志。

## 八、完整闭环

最小闭环是：

```text
RepoScope.Observe
-> RepoScope.Decide
-> WorktrackScope.Init
-> WorktrackScope.Observe
-> WorktrackScope.Decide
-> WorktrackScope.Dispatch
-> WorktrackScope.Verify
-> WorktrackScope.Judge
-> WorktrackScope.Close 或 Recover
-> RepoScope.Refresh
-> RepoScope.Observe
```

`PR` 不是闭环终点。完整 closeout 覆盖 `merge -> refresh repo snapshot -> cleanup -> return RepoScope`。

## 九、已批准输入与写回边界

用户讨论、append request、repo goal 或恢复路径必须先收束进 Harness artifact，尤其是 [Worktrack Contract](../artifact/worktrack/contract.md) 与 [Plan / Task Queue](../artifact/worktrack/plan-task-queue.md)。

阅读路由由 [AGENTS.md](../../../AGENTS.md) 的 Route Contract 承接。写回边界由 [Review / Verify 治理入口](../../project-maintenance/governance/review-verify-handbook.md) 承接。`memory-side`、`task-interface` 与 `adjacent-systems` 已退役。

repo-local runtime 状态属于 `.servo/` 等 state layer，不替代 `docs/`、`product/` 或 `toolchain/` 中的正式真相。

## 十、判断标准

如果下面几句话成立，Harness doctrine 就是清楚的：

- `Repo` 与 `Worktrack` 是两个不同时间尺度的控制层。
- `Scope / Function / Artifact` 没有互相替代。
- `Skill / SubAgent` 是实践绑定。
- 目标变更被排除在普通控制回路之外。
- 控制平面和执行平面分开。
- `Evidence` 与 `Gate` 同时存在。
- closeout 覆盖 PR 后的 repo 状态刷新。
