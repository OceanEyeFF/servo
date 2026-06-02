---
title: "RepoScope 管理文档"
status: active
updated: 2026-05-20
owner: servo-kernel
last_verified: 2026-05-20
---
# RepoScope 管理文档

> 目的：固定 Harness 在 RepoScope 层的控制对象、观测循环、决策逻辑，以及 RepoScope 与 WorktrackScope 之间的切换条件。

## 定位

RepoScope 是 Harness 两层控制模型中的**慢变量层**。它不直接执行代码变更，而是维护长期基线、观测系统整体状态、管理 Milestone Pipeline，并决定何时进入 WorktrackScope 执行局部状态转移。

RepoScope 的权威定义见 [../foundations/Harness指导思想.md](../foundations/Harness指导思想.md)；运行时合法算子见 [../foundations/Harness运行协议.md](../foundations/Harness运行协议.md) 和 [../foundations/runtime-control-loop.md](../foundations/runtime-control-loop.md)。

本文档不复制 doctrine 或 runtime protocol 正文，而是将其组织为 scope 管理视角下的结构化参考。

## RepoScope 控制对象

RepoScope 维护以下慢变量：

| 控制对象 | 存储位置 | 说明 |
|---------|---------|------|
| Goal / Charter | `.servo/goal-charter.md` | 长期参考信号，定义 Repo 的目标状态和 Engineering Node Map |
| Repo Snapshot / Status | `.servo/repo/snapshot-status.md` | RepoScope.Observe 的观测面，记录 `baseline_ref`、`source_baselines`、governance 信号 |
| Milestone Pipeline | `.servo/repo/milestone-backlog.md` | 所有 milestone 的聚合管线，含 planned/active/completed/superseded 状态 |
| Control State | `.servo/control-state.md` | 控制面配置与位置信息（Scope/Function/Route），不承载业务真相 |
| Worktrack Backlog | `.servo/repo/worktrack-backlog.md` | 所有 worktrack 的执行记录与状态追踪 |
| Complex Project Entry Gate | `.servo/repo/complex-project-entry-gate.md` 或结构化 `complex_project_entry_gate` handoff | 复杂项目、弱文档或高风险 Milestone 进入前的 Milestone-side blocking gate |

正式对象字段定义见 [../artifact/README.md](../artifact/README.md)。

## RepoScope 观测循环

### Observe 阶段

RepoScope.Observe 通过以下传感器收集系统状态：

| 传感器 | 绑定技能 | 观测内容 |
|--------|---------|---------|
| Git 基线 | `git rev-parse HEAD` | 当前 HEAD hash，与 `latest_observed_checkpoint` 对比 |
| Milestone 状态 | `milestone-status-skill` | 活跃 milestone 的 progress、acceptance、gate、handback |
| 分支状态 | git branch / log | 活跃分支数、年龄、与基线的偏离 |
| 文档新鲜度 | `last_doc_catch_up_checkpoint` | 文档版本是否落后于代码基线 |
| 治理检查 | governance checks | path_governance、folder_logic、semantic 等 |

当 `active_milestone` 非空时，必须在 Observe→Decide 之间绑定 `milestone-status-skill` 获取 Milestone 级裁决字段。

### Git Hash 幂等性守卫

Reposcope 使用 git commit hash 避免对同一基线重复刷新：

- `latest_observed_checkpoint`：上次 repo-refresh 后的 HEAD hash
- `last_doc_catch_up_checkpoint`：上次 doc-catch-up 后的 HEAD hash
- hash 一致 → 跳过对应刷新动作
- hash 不一致 → 绑定对应刷新技能

详细定义见 [../foundations/runtime-state-hydration.md](../foundations/runtime-state-hydration.md) 和 [../artifact/control/control-state.md#Baseline Traceability](../artifact/control/control-state.md)。

### Decide 阶段

RepoScope.Decide 基于观测结果做出以下判定：

| 判定 | 条件 | 动作 |
|------|------|------|
| 保持观察 | 无活跃 milestone，或无待执行 worktrack | 回到 Observe |
| 进入 WorktrackScope | 存在活跃 milestone、有待执行 worktrack，且 `worktrack_intake_review.ready_for_worktrack_init == true` | Init WorktrackScope，派生当前 worktrack |
| Handback | Milestone 所有 worktrack 已完成，等待 programmer 验收 | 停止，返回控制权 |

**关键约束**：
- `ChangeGoal` 不由常规 Decide 选择；目标变更由外部 `GoalChangeRequest` 触发
- Milestone brief 必须经 programmer 确认后才能激活 goal-driven milestone
- 命中 complex-project trigger 时，`complex_project_entry_gate.milestone_blocking_decision` 必须允许 create / activate / derive-worktrack；scanner output is evidence, not verdict，不能单独清空阻断。gate handoff 必须暴露 `scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 与 `reinforcement_milestone_recommendation`；canonical guard term: not fixed heavy mode；Worktrack execution modes `normal`、`autoreview`、`yolo` 不替代 Milestone-side blocker
- 不要在没有 milestone 上下文的情况下直接创建 worktrack
- 从 active milestone 进入 WorktrackScope 前必须形成 `worktrack_intake_review`，覆盖 `repo_fundamentals`、`snapshot_freshness`、`milestone_purpose_alignment`、`historical_conflict_risk`、`worktrack_adjustment_recommendations`、`add_remove_worktrack_recommendations`、`intake_review_verdict` 与 `ready_for_worktrack_init`

## RepoScope ↔ WorktrackScope 切换

### RepoScope → WorktrackScope

触发条件：
1. `repo-whats-next-skill` 输出建议进入 WorktrackScope
2. 存在活跃 milestone 且有待初始化的 worktrack
3. `worktrack_intake_review.intake_review_verdict` 为 `ready_for_worktrack_init`
4. 若当前 milestone 命中 complex-project trigger，`complex_project_entry_gate` 未要求 `block_derive_worktrack`
5. 当前无阻塞条件（审批、证据缺失、运行时缺口）

进入前审查：
- `repo_fundamentals`：确认当前 milestone、目标/非目标、baseline、已闭环 worktrack 与禁止项仍一致
- `snapshot_freshness`：确认 Repo Snapshot/Status、Control State、milestone-backlog、worktrack-backlog 与 git HEAD 足够新鲜；否则 verdict 为 `refresh_required`
- `milestone_purpose_alignment`：确认候选 worktrack 仍服务于 active milestone 的 purpose、completion signals 与 acceptance criteria
- `historical_conflict_risk`：确认候选 worktrack 不与已关闭 worktrack、既有决策、文档真相或 handback 边界冲突
- `worktrack_adjustment_recommendations`：说明保持、拆分、合并、改写、推迟或阻塞建议
- `add_remove_worktrack_recommendations`：说明是否需要新增、移除或重排 worktrack；无变化时写 `none`
- `intake_review_verdict`：只允许 `ready_for_worktrack_init` / `refresh_required` / `adjust_worktracks` / `blocked`

进入动作：
1. `init-worktrack-skill` 校验并写入 `worktrack_intake_review`
2. `init-worktrack-skill` 创建 worktrack branch、contract、plan-task-queue、gate-evidence
3. Control State 切换到 `worktrack_scope`
4. 控制权移交 WorktrackScope 控制回路

### WorktrackScope → RepoScope

触发条件：
1. WorktrackScope.Close 完成（merge + cleanup）
2. WorktrackScope.Recover 完成且回到 RepoScope

进入动作：
1. `repo-refresh-skill` 刷新 Repo Snapshot/Status
2. `git rev-parse HEAD` 写入 `latest_observed_checkpoint`
3. Milestone progress 更新
4. Control State 切换到 `repo_scope`

完整闭环路径见 [../foundations/runtime-closeout-refresh.md](../foundations/runtime-closeout-refresh.md)。

## ChangeGoal 与 SetGoal

| 算子 | 触发条件 | 说明 |
|------|---------|------|
| `SetGoal` | `.servo/` 未初始化，首次设定参考信号 | 仅执行一次，建立 Goal/Charter |
| `ChangeGoal` | 外部 `GoalChangeRequest` 触发 | 目标变更走独立控制路径，不属于常规循环 |

目标变更的完整流程见 [../artifact/control/goal-change-request.md](../artifact/control/goal-change-request.md)。在 RepoScope 正常循环中，Goal 是不可变的参考信号。

## Milestone Pipeline 管理

RepoScope 负责 Milestone Pipeline 的全局视图：

- 同一时刻最多一个 active milestone（goal-driven）
- Milestone 按 priority 排序
- 依赖关系（`depends_on_milestones`）必须在激活前验证
- Work-collection milestone 完成后自动推进；goal-driven milestone 完成后 handback

Pipeline 恢复动作（损坏、不一致、孤儿绑定）的定义见 Harness 运行协议第十二节。

## 文档新鲜度管理

RepoScope 在以下情况触发文档追平：

- 代码版本变更（git hash 变化）
- Package/release 事实变更
- Deploy/adapter 行为变更
- 验证命令变更
- Operator-facing 文档过时

文档追平由 `doc-catch-up-worker-skill` 执行，完成后写入 `last_doc_catch_up_checkpoint`。

## 治理约束

1. RepoScope 不直接执行代码变更；所有变更通过 WorktrackScope 执行
2. Goal 在常规循环中不可变；目标变更必须走 ChangeGoal
3. Milestone 最终验收权归 programmer
4. Control State 只保存控制面位置信息；业务真相在正式 artifact 中
5. git hash 一致仅跳过重复刷新，不可跳过首次验证和 Gate 裁决
