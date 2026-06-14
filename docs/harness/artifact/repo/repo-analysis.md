---
title: "Repo Analysis"
status: active
updated: 2026-04-26
owner: servo-kernel
last_verified: 2026-06-13
---
# Repo Analysis

Repo Analysis 是 `RepoScope` 的决策支撑 artifact，将仓库事实压缩为可复核的优先级判断。回答当前仓库事实、推断/未知项、主要矛盾、最高优先级、路由投影、可写回长期 truth 的结论。不回答新目标、worktrack 任务队列、实现切片编码，或未验证结论是否应进入长期文档。

## Position

Repo Analysis 位于 `GoalCharter` 与 `RepoSnapshot/Status` 下游：Goal 定义长期参考信号和 Engineering Node Map，Snapshot 定义慢变量状态，Repo Analysis 基于两者做阶段性矛盾分析和优先级判断。`repo-whats-next-skill` 可消费它，但不得当作目标真相替代品。

## Required Inputs

一份合格的 Repo Analysis 至少引用 `GoalCharter`、`RepoSnapshot/Status`、`ControlState`、本轮必要入口文档或模块证据，以及影响判断的最近 `WorktrackContract`/`PlanTaskQueue`/`GateEvidence` 最小边界摘要。禁止将 deploy target、本地挂载结果或未验证报告当作唯一事实来源。

## Required Fields

`Repo Analysis` 至少包含以下 Control Signal 字段：

- `analysis_status`
- `baseline_branch`
- `baseline_ref`
- `facts`
- `inferences`
- `unknowns`
- `current_main_contradiction`
- `main_aspect`
- `current_highest_priority`
- `long_term_highest_priority`
- `do_not_do_now`
- `recommended_repo_action`
- `recommended_next_route`
- `suggested_node_type`
- `continuation_ready`
- `continuation_blockers`
- `writeback_eligibility`

Supporting Detail 可包含完整分析等，但路由关键字段必须出现在 Control Signal 层。

## Analysis Rules

事实、推断、未知项须分开写。主要矛盾和最高优先级各仅可有一个。证据不足以选择主要矛盾时 `continuation_ready` 须为 `false` 并列出缺失信息。不可将 task list 当作 repo 分析，或将分析报告写成新的 `GoalCharter`（目标变更仅可走 `repo-change-goal-skill`）。

## Lifecycle

1. `RepoScope.Observe` 读取 Goal/Snapshot/Control State。
2. `RepoScope.Decide` 在需优先级重构时生成 Repo Analysis。
3. 输出建议 repo action 和路由投影。
4. 进入 `WorktrackScope.Init` 时 `WorktrackContract` 仅可引用分析结论，不得复制全文。
5. Worktrack closeout 后 `RepoScope.Refresh` 根据验证事实更新 snapshot；未验证的分析判断不进入长期 truth。

## 上游刷新机制

Repo Analysis 的上游刷新遵循项目基本面刷新触发规则（见 harness-skill §10.7 item 9）：

| 触发条件 | 刷新动作 |
|---------|---------|
| Worktrack closeout 后 | `repo-refresh-skill` 消费已验证 gate evidence，更新 Repo Snapshot/Status；若优先级或矛盾变化，标记 `analysis_stale: true` |
| Milestone closeout 后 | Milestone 验收完成后刷新 Snapshot 并更新 Pipeline；若 Goal Charter scope 变化，必须重新生成 Repo Analysis |
| Git hash 变更后（新会话） | Harness Observe 阶段检测 hash 变化 → 绑定 `repo-refresh-skill` 刷新 baseline 观察 → 若 snapshot 过期则重新生成 |
| Goal Charter 变更后 | 由 `repo-change-goal-skill` 触发；Charter 变化后必须重新生成 Repo Analysis（Charter 是最上游参考信号） |
| `analysis_stale` 标记 | 任何下游 worktrack 的验证事实与当前 analysis 结论矛盾时，由 gate-skill 或 repo-refresh-skill 标记；下一轮 Decider 必须消费该标记 |

**刷新动作不自动触发新 worktrack**；重新生成 Repo Analysis 后由 `repo-whats-next-skill` 决定是否需要新 worktrack。Analysis 是决策支撑 artifact，不是执行 contract。

## Writeback Policy

可写回长期 truth layer：已被后续 worktrack 验证的 repo 状态变化、被 gate 接受的 artifact/workflow/skill 规则、已同步到 docs/product/toolchain 的执行约定。不可写回：未验证市场判断、未验证外部需求、只来自一次分析报告的战略推断、与 Goal Charter 冲突但未走目标变更控制的结论。

## Consumer Contract

repo-whats-next-skill 可使用最新 Repo Analysis 作为判定输入，前提是 baseline 仍匹配或明确标注过期、Control Signal 字段完整、没有混入目标变更/任务/队列。即使没有新鲜 Repo Analysis，repo-whats-next-skill 也必须能直接基于 Goal/Snapshot/Control State 完成限定范围判定。

## Machine Check

Repo Analysis 的 reusable template sources 必须能通过轻量 contract check：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/repo_analysis_contract_check.py
```

该检查只验证 markdown required sections 与 keyed fields 是否存在。它不把运行时 `.servo/` 产物提升为 canonical source，也不替代 `repo-whats-next-skill` 的实际优先级判断。
