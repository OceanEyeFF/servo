---
title: "Init Milestone Skill"
status: active
updated: 2026-05-14
owner: servo-kernel
last_verified: 2026-05-14
---

# Init Milestone Skill

> 独立 Milestone 初始化 skill。它是 RepoScope 下的 Milestone 创建/注册算子，处理 latest-override、依赖验证和 pipeline 激活，不修改 version/release 状态。

## 定位

- Scope: `RepoScope`
- Function: 作为 `RepoScope.Init` 的 Milestone 初始化算子
- 输入: programmer 或 harness 提供的 milestone 规格 + milestone-backlog + control-state
- 输出: 结构化 Milestone 初始化结果（milestone_id、status、pipeline_position、writeback 信息）

canonical executable source：

- [../../../../product/harness/skills/init-milestone-skill/SKILL.md](../../../../product/harness/skills/init-milestone-skill/SKILL.md)

## 职责

- 创建或 upsert milestone artifact（`.aw/milestone/{milestone_id}.md`）
- Upsert milestone-backlog（`.aw/repo/milestone-backlog.md`）
- 处理 latest-override 语义（同 milestone_id，时间戳最新覆盖）
- 验证依赖合法性（存在性 + 循环依赖检测）
- 管理激活规则（同一时刻仅一个 active）
- 在 goal-driven milestone 激活前输出结构化 planning brief 并等待 programmer 确认
- 对 milestone 定义变更应用稳定性规则（signals / criteria / threshold 改写触发重新评估）
- 更新 control-state（active_milestone / milestone_pipeline_summary）

## 非职责

- 不分析 Milestone 状态（`milestone-status-skill` 的职责）
- 不选择下一 Worktrack（`repo-whats-next-skill` 的职责）
- 不初始化 worktrack（`init-worktrack-skill` 的职责）
- 不修改 version/release 状态

## 输入

| 输入 | 来源 | 说明 |
|------|------|------|
| Programmer 规格 | 用户输入 | milestone 的 title/purpose/worktrack_list/priority/depends_on 等 |
| Harness 推理规格 | `repo-whats-next-skill` 输出 | harness 推理的 milestone 建议 |
| Milestone backlog | `.aw/repo/milestone-backlog.md` | 唯一性检查 + pipeline 上下文 |
| Control state | `.aw/control-state.md` | active_milestone 状态 |

## 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| milestone_id | string | 初始化/更新的 Milestone ID |
| milestone_title | string | Milestone 名称 |
| milestone_status | enum | planned / active |
| init_action | enum | created / upserted |
| priority | integer | Pipeline 优先级 |
| pipeline_position | string | 在 pipeline 中的位置 |
| depends_on_validation | object | 依赖检查结果 |
| activation_decision | string | 激活判定理由 |
| activation_brief | object/null | goal-driven 激活前输出的结构化 brief；work-collection 可为 `null` |
| confirmation_required | boolean | 是否必须等待 programmer 确认后才能激活 |
| milestone_reevaluation_required | boolean | 本次 upsert 是否因 signals / criteria / threshold 改写而要求重新评估 |
| ownership_review | string | 追加 worktrack 时的归属判定：belongs_current / suggest_other_milestone / suggest_new_milestone / not_applicable |
| artifact_path | string | milestone artifact 文件路径 |
| backlog_updated | boolean | 是否更新了 backlog |
| control_state_updated | boolean | 是否更新了 control-state |
| override_source | string | programmer / harness / none |
| can_proceed | boolean | 是否可继续 |
| proceed_blockers | array | 阻止推进的因素 |

## 激活与稳定性约定

- goal-driven milestone 在 `planned` → `active` 前，必须先输出结构化 brief，最少包含 `goal`、`completion_signals`、`acceptance_criteria`、`worktrack_list`、`completion_threshold_pct`、`depends_on_milestones` 和 `activation_reason`。
- brief 发出后，`confirmation_required = true`，skill 必须等待 programmer 确认后才能实际激活 milestone。
- work-collection milestone 保持既有自动激活语义；可输出同结构 brief 作为信息提示，但不形成阻塞确认边界。
- 若本次 upsert 修改了 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct`，必须输出 `milestone_reevaluation_required = true`，并要求后续由 `milestone-status-skill` 重新评估 milestone。
- 若仅向 `worktrack_list` 追加 worktrack，且该 worktrack 已确认归属当前 milestone 的 `purpose`/`signals`/`criteria`，则不触发 milestone 重新评估。
- 追加进入当前 milestone 的 worktrack 以独立执行单元形式推进：专属 branch、contract、queue、evidence、closeout 和 repo-refresh 追踪由下游 `init-worktrack-skill` / closeout 路径承接。
- 若追加的 worktrack 不归属当前 milestone，`ownership_review` 必须返回 `suggest_other_milestone` 或 `suggest_new_milestone`；不得通过静默改写当前 milestone 定义来吸收该 worktrack。

## 调用时机

- `RepoScope.Decide` 阶段（`repo-whats-next-skill` 输出 `suggested_milestone_action == "create"` 或 `"activate"` 时）
- Programmer 显式声明新 milestone 目标
- Programmer 或 harness 请求修改 milestone signals / criteria / threshold
- Programmer 或 harness 请求向 milestone 追加 worktrack
- Pipeline 中无符合条件的 planned milestone 可激活时
