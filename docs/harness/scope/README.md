---
title: "Harness Scope"
status: active
updated: 2026-05-17
owner: servo-kernel
last_verified: 2026-05-17
---
# Harness Scope

`docs/harness/scope/` 固定 Harness 的两个控制 Scope（RepoScope / WorktrackScope）、RepoScope 内的 Milestone 子层控制，以及两层 Scope 之间的状态闭环。

本目录不复制 doctrine 或 runtime protocol 正文。`RepoScope` / `WorktrackScope` 的概念定义见 [../foundations/Harness指导思想.md](../foundations/Harness指导思想.md)，运行时合法算子与连续推进规则见 [../foundations/Harness运行协议.md](../foundations/Harness运行协议.md) 和 [../foundations/runtime-control-loop.md](../foundations/runtime-control-loop.md)。

## 目录结构

| 文档 | 回答的问题 |
|------|-----------|
| [repo-scope.md](./repo-scope.md) | RepoScope 管理什么？慢变量如何观测？何时进入 WorktrackScope？两层 Scope 如何切换？ |
| [worktrack-scope.md](./worktrack-scope.md) | WorktrackScope 内部有哪些合法状态？状态之间如何转移？异常路径和治理约束是什么？ |

## 两层 Scope 的关系

```
RepoScope (慢变量层，含 Milestone 子层)         WorktrackScope (快变量层)
┌───────────────────────────┐              ┌──────────────────────┐
│ 维护长期基线              │   Decide     │ 单个 worktrack 的    │
│ Milestone: 目标分批+闸门  │ ────────→   │ 完整生命周期        │
│ 管理 Pipeline             │              │ Init→Dispatch→      │
│ 观测→决策循环             │  ←────────  │ Verify→Judge→       │
│                           │  Close/      │ Close/Recover        │
│                           │  Refresh     │                      │
└───────────────────────────┘              └──────────────────────┘
```

- **RepoScope** 是决策层：判断什么时候需要执行、执行什么
- **WorktrackScope** 是执行层：在受约束的局部范围内完成一次状态转移
- 闭环 = RepoScope.Decide → WorktrackScope.Init → ... → WorktrackScope.Close → RepoScope.Refresh → RepoScope.Observe

## 阅读顺序

1. 先读 [repo-scope.md](./repo-scope.md) 理解两层 Scope 的整体关系和切换条件
2. 再读 [worktrack-scope.md](./worktrack-scope.md) 理解 WorktrackScope 内部 11 个状态的转移规则

## 非本目录内容

以下内容不在 scope 目录管理范围内，查阅对应 owner：

| 内容 | 权威 owner |
|------|-----------|
| 两层 Scope 的概念定义 | [../foundations/Harness指导思想.md](../foundations/Harness指导思想.md) |
| 运行时控制回路协议 | [../foundations/Harness运行协议.md](../foundations/Harness运行协议.md) |
| Artifact 正式对象字段 | [../artifact/README.md](../artifact/README.md) |
| Workflow family policy | [../workflow-families/README.md](../workflow-families/README.md) |
| Skill 清单与入口 | [../catalog/README.md](../catalog/README.md) |
