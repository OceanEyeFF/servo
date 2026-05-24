---
title: "Goal Change Request"
status: active
updated: 2026-05-09
owner: servo-kernel
last_verified: 2026-05-09
---

# Goal Change Request

> Goal Change Request 是 Repo 目标变更的正式请求 artifact，记录变更的完整上下文、影响分析和审批决策，是 `ChangeGoal` 控制算子的唯一正式输入。不替代 `GoalCharter`、`ControlState` 或 `WorktrackContract`。

## 目的

Goal Change Request 服务于 Harness 控制回路的参考信号变更层。当需修改 `RepoScope` 级 `GoalCharter` 时，本 artifact 承载变更请求的结构化记录：变更理由、影响范围、幅度评估和审批边界。目标变更改变的是控制系统参考信号而非常规状态转移，与 `Observe`/`Decide`/`Dispatch`/`Verify` 回路解耦，须单独 gate 和审批。

## 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `change_request_id` | `string` | 是 | 唯一标识，格式 `cr-YYYYMMDD-N` |
| `requested_by` | `string` | 是 | 请求来源：`programmer` / `harness` / `external` |
| `change_rationale` | `string` | 是 | 变更理由，说明为什么需要修改目标 |
| `change_magnitude` | `enum` | 是 | 变更幅度：`minor`（局部调整）/ `moderate`（结构性调整）/ `major`（方向性变更） |
| `current_goal_summary` | `string` | 是 | 当前 Goal Charter 摘要（含 Engineering Node Map 概览） |
| `proposed_goal_summary` | `string` | 是 | 变更后 Goal Charter 摘要（含 Engineering Node Map 概览） |
| `engineering_node_map_diff` | `object` | 是 | 节点类型差异：新增/删除/变更的节点类型、default baseline policy 变化、node dependency graph 变化 |
| `affected_worktracks` | `array` | 是 | 受影响活跃 worktrack 列表，每项含 worktrack_id、影响描述、推荐动作（继续/重新验证/暂停/终止/重新绑定节点类型） |
| `threatened_invariants` | `array` | 条件 | 受威胁的系统不变条件列表及每项的变更方式（增/删/改）；无受威胁项时填入空数组并注明 `none` |
| `approval_boundary` | `object` | 是 | 审批边界：`needs_approval` (boolean)、`approval_scope` (string)、`approval_reason` (string) |
| `decision` | `enum` | 是 | 决策结果：`accepted` / `deferred` / `rejected` / `redirected` |
| `resolution_notes` | `string` | 条件 | 执行确认：实际改写的文件清单、后续必要动作；`accepted` 或 `redirected` 时必填 |

## 字段约束

- `change_magnitude` 为 `major` 时，`affected_worktracks` 须包含 baseline 重建评估，`resolution_notes` 须说明是否重建 baseline 或重新初始化 worktracks。
- `engineering_node_map_diff` 若导致活跃 worktrack 的节点类型不再被覆盖，`affected_worktracks` 须显式标记重新绑定或终止。
- `approval_boundary.needs_approval` 为 `true` 时，`decision` 不得为 `accepted`（`resolution_notes` 含审批确认记录时除外）。
- `decision` 为 `accepted` 且已执行改写后，须同步更新 `control-state.md` 和 `repo/snapshot-status.md`。

## 生命周期

1. **创建**：programmer 提出目标变更意图时创建，或 harness 收到目标级变更请求后按本 artifact 格式创建。
2. **审批**：programmer 审批；`major` 幅度变更可能需额外 stakeholder 确认。审批边界在 `approval_boundary` 中显式声明。
3. **决策**：审批后填入 `decision`（`accepted`/`deferred`/`rejected`/`redirected`）。
4. **执行**：`decision` 为 `accepted` 时，`repo-change-goal-skill` 执行对 `goal-charter.md`、`control-state.md`、`repo/snapshot-status.md` 的改写，结果记入 `resolution_notes`。
5. **闭包**：改写完成后，本 request 进入已解决状态；后续 `Observe` 须从新 `GoalCharter` 重新开始。

## 关联文档

- 执行 Skill：`product/harness/skills/repo-change-goal-skill/SKILL.md`
- 分析模板：`product/harness/skills/repo-change-goal-skill/templates/goal-change-request.template.md`
- 下游依赖：`GoalCharter`、`ControlState`、`NodeTypeRegistry`

## 硬约束

- Goal Change Request 不是 `GoalCharter`、`ControlState` 或 `WorktrackContract`。
- 本 artifact 是正式记录，不得与 `repo-change-goal-skill` 产生的临时分析报告合并。
- 目标变更执行后须写回 `resolution_notes`，不得仅靠对话记忆。
- 审批完成前不得将 `decision` 预填为 `accepted`。
- 歧义须显式暴露为未解决问题；禁止将歧义当作已批准的变更写入本 artifact。
