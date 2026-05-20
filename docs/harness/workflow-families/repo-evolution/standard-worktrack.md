---
title: "Standard Worktrack"
status: superseded
updated: 2026-05-09
owner: servo-kernel
last_verified: 2026-05-09
---
# Standard Worktrack

> **状态：已废弃。** 标准 worktrack 闭环的权威定义已迁移至 [Harness运行协议.md](../../foundations/Harness运行协议.md)、[runtime-control-loop.md](../../foundations/runtime-control-loop.md)，以及 `harness-skill/SKILL.md` 的两层控制律（第七节）。本文档保留为历史引用。
>
> 完整状态闭环：`RepoScope.SetGoal -> Observe -> Decide -> WorktrackScope.Init -> Observe -> Decide -> Dispatch -> Verify -> Judge -> Close/Recover -> RepoScope.Refresh -> Observe`

最小序列（历史记录）：

1. 冻结目标、范围、非目标、验收、风险与验证要求
2. 初始化 `Worktrack Contract` 与 task queue
3. 调度执行并生成变更
4. 收集 evidence，执行 verify
5. 形成 gate verdict
6. fail 时 recover，pass 时 integrate/close
7. 回写 repo 级状态
