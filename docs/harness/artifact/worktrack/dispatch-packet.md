---
title: "Dispatch Packet Schema"
status: active
updated: 2026-05-20
owner: servo-kernel
last_verified: 2026-05-20
---

# Dispatch Packet Schema

> 统一 `schedule-worktrack-skill -> dispatch-skills -> generic-worker-skill` 链路的 packet 字段定义。

## 概述

Dispatch Packet Schema 定义了 Harness 任务分派链路的三层 packet 格式。由调度方、分派方和执行方在不同阶段产出和消费，形成完整的分派闭环：

- **Dispatch Task Brief**：调度阶段产出（schedule-worktrack-skill），告诉 dispatch-skills"要分派什么"
- **Dispatch Info Packet**：dispatch-skills 产出，告诉 SubAgent/执行载体"怎么执行"
- **Dispatch Result**：执行载体产出，回传给 dispatch-skills，在 Harness Verify 阶段被 gate-skill / review-evidence-skill 引用

三层 packet 的关系：

```
schedule-worktrack-skill
        │
        ▼ Dispatch Task Brief
dispatch-skills
        │
        ▼ Dispatch Info Packet
SubAgent / generic-worker-skill / doc-catch-up-worker-skill
        │
        ▼ Dispatch Result
dispatch-skills → gate-skill / review-evidence-skill
```

## Dispatch Task Brief

调度阶段产出，告诉 dispatch-skills"要分派什么"。由 `schedule-worktrack-skill` 生成。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `worktrack_id` | string | 是 | 所属 worktrack 标识 |
| `task_id` | string | 是 | 任务标识，对应 Plan/Task Queue 中的任务项 |
| `task_goal` | string | 是 | 单句任务目标，描述本轮执行要达成的结果 |
| `scope` | string[] | 是 | 范围内，具体文件/模块路径列表 |
| `non_goals` | string[] | 是 | 范围外，明确不应触碰的文件/模块 |
| `acceptance_criteria` | string[] | 是 | 验收标准列表，每条为可验证的条件描述 |
| `constraints` | string[] | 是 | 硬约束，不可修改的文件、不可跨过的边界 |
| `expected_output` | string | 是 | 预期产出格式，指导 dispatch-skills 选择合适的执行载体 |
| `dispatch_mode` | enum | 是 | 分派模式：`auto` / `delegated` / `current-carrier` |
| `rollback_hint` | string | 否 | 失败时的回滚建议，供 recover-worktrack-skill 参考 |

### dispatch_mode 语义

| 值 | 语义 |
|------|------|
| `auto` | 按 [Dispatch Decision Policy](../../foundations/dispatch-decision-policy.md) 选择 SubAgent、专用 skill、generic worker 或 current-carrier；无法安全委派时显式 fallback |
| `delegated` | 必须委派 SubAgent；无法委派时返回 gap/block |
| `current-carrier` | 显式关闭委派，由当前 carrier 直接执行 |

### 约束规则

- `scope` 和 `non_goals` 必须收束在所属 Worktrack Contract 声明的范围内
- `constraints` 不能比 Worktrack Contract 的约束更宽松
- `acceptance_criteria` 必须可验证，不接受模糊描述
- `dispatch_mode` 参考 Contract 的 `runtime_dispatch_mode`，但可由 schedule-worktrack-skill 根据任务特征调整

## Dispatch Info Packet

分派阶段产出，告诉执行载体"怎么执行"。由 `dispatch-skills` 生成。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `worktrack_id` | string | 是 | 所属 worktrack 标识 |
| `task_id` | string | 是 | 任务标识 |
| `goal` | string | 是 | 任务目标，从 Task Brief 的 `task_goal` 继承或细化 |
| `scope` | string[] | 是 | 范围内，从 Task Brief 继承或细化 |
| `non_goals` | string[] | 是 | 范围外，从 Task Brief 继承或细化 |
| `acceptance` | string[] | 是 | 验收标准，从 Task Brief 继承或细化为执行载体可直接理解的表述 |
| `allowed_artifacts` | string[] | 是 | 允许读取的文件和 artifact 路径列表 |
| `forbidden_boundaries` | string[] | 是 | 禁止扩展的边界，包括不可读取或不可修改的区域 |
| `expected_output_format` | string | 是 | 预期输出格式，明确执行载体应产出的结果形式 |
| `evidence_format` | string | 是 | evidence 回传格式，规定执行载体如何组织执行证据 |
| `dispatch_mode` | enum | 是 | 分派模式：`auto` / `delegated` / `current-carrier` |
| `shared_fact_pack` | object | 是 | 必须共享给执行载体的最小项目事实包，见下方定义 |
| `context_budget` | object | 是 | 本轮可读取上下文预算，见下方定义 |
| `runtime_dispatch_profile` | object | 是 | backend/model/runtime 的委派能力画像，见下方定义 |
| `recovery_hint` | string | 否 | 失败恢复提示，供执行载体在出错时参考 |
| `context_files` | string[] | 否 | 需要预加载的上下文文件路径列表（路径引用，非内联全文） |

### 字段继承与细化规则

- `goal`、`scope`、`non_goals`、`acceptance` 从 Dispatch Task Brief 的同名字段继承
- dispatch-skills 可以细化这些字段，但不能扩大 `scope` 或缩小 `non_goals`
- `dispatch_mode` 继承 Task Brief 的值，dispatch-skills 不得变更
- `forbidden_boundaries` 必须在 `non_goals` 的基础上进一步收束，不能比 Task Brief 的约束更宽松
- `allowed_artifacts` 只能包含在 `scope` 范围内或与任务目标直接相关的文件
- `shared_fact_pack` 只承载必须共同持有的事实引用，不内联长文档正文
- `context_budget` 必须与 `allowed_artifacts`、`context_files` 和 `forbidden_boundaries` 一致

### shared_fact_pack 说明

`shared_fact_pack` 固定执行隔离中的共享事实，避免不同执行载体因前提不足做出互相冲突的隐含决策。

最少包含：

```yaml
shared_fact_pack:
  repo_goal_ref:
  repo_snapshot_ref:
  worktrack_contract_ref:
  plan_task_queue_ref:
  current_decision_refs:
  baseline_ref:
  invariants:
  forbidden_assumptions:
```

### context_budget 说明

`context_budget` 显式限制本轮读取多少上下文：

```yaml
context_budget:
  max_files:
  max_estimated_tokens:
  must_read:
    - shared_fact_pack
    - worktrack_contract
    - task_acceptance_slice
  may_read:
    - local module docs
    - related source files
    - previous gate evidence
  do_not_read:
    - unrelated historical logs
    - unrelated worktracks
    - retired docs
  stop_after_locating_scope: true
  expansion_requires_reason: true
```

如果执行载体需要超过 `context_budget`，必须返回调度或分派阶段请求扩展理由，不得静默读取全仓库上下文。

### context_files 说明

`context_files` 列出执行载体在开始工作前应加载的上下文文件路径。仅提供路径引用，不内联文件全文。dispatch-skills 应确保所列文件均在 `allowed_artifacts` 范围内。

### runtime_dispatch_profile 说明

`runtime_dispatch_profile` 记录本轮运行时是否能真实委派，以及为什么选择或放弃 SubAgent。它不改变权限，只让 `auto` 的判断可审计。

```yaml
runtime_dispatch_profile:
  backend_runtime:
  model_family:
  subagent_dispatch_shell:
  runtime_supports_subagent:
  subagent_permission_state:
  permission_allows_delegation:
  dispatch_package_safety:
  delegation_attempted:
  attempted_carrier:
  carrier_decision:
  selection_reason:
  fallback_reason:
```

`backend_runtime` 可记录 `codex-cli`、`claude-code-cli` 或 `unknown`；`model_family` 可记录 `gpt`、`claude`、`deepseek` 或 `unknown`。当 `backend_runtime = claude-code-cli`（ClaudeCodeCLI）或 `model_family = deepseek`（Deepseek）且 `subagent_dispatch_shell` 非 `available` 时，必须将 `fallback_reason` 写为 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe` 中的一个具体原因，不得静默落到 `current-carrier`。

## Dispatch Result

执行完成后的回传格式。由 SubAgent / generic-worker-skill / doc-catch-up-worker-skill 产出，dispatch-skills 消费。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `worktrack_id` | string | 是 | 所属 worktrack 标识 |
| `task_id` | string | 是 | 任务标识 |
| `status` | enum | 是 | 执行状态：`completed` / `partial` / `failed` / `blocked` |
| `summary` | string | 是 | 执行摘要，不超过 5 句 |
| `files_modified` | string[] | 是 | 修改的文件路径列表 |
| `files_created` | string[] | 是 | 新建的文件路径列表 |
| `evidence_generated` | string[] | 是 | 产出的 evidence 文件路径列表 |
| `unresolved_issues` | string[] | 是 | 未解决的问题列表 |
| `blockers` | string[] | 否 | 阻塞项列表，当 status 为 `blocked` 时必填 |
| `recommendations` | string[] | 否 | 对下一步的建议 |
| `dispatch_mode_used` | enum | 是 | 实际使用的分派模式：`auto` / `delegated` / `current-carrier` |
| `dispatch_policy_ref` | string | 是 | 使用的执行载体选择策略引用，通常为 `docs/harness/foundations/dispatch-decision-policy.md` |
| `runtime_dispatch_profile` | object | 是 | 本轮 backend/model/runtime 委派能力画像 |
| `carrier_decision` | string | 是 | 实际载体选择：如 `SubAgent` / `current-carrier` / `doc-catch-up-worker-skill` / `generic-worker-skill` |
| `decision_inputs` | object | 否 | `auto` 模式下用于选择载体的输入摘要 |
| `delegation_attempted` | enum | 是 | 是否真实尝试委派：`yes` / `no` |
| `attempted_carrier` | string | 是 | 被尝试或被选择的载体：`SubAgent` / `generic-worker-skill` / `doc-catch-up-worker-skill` / `current-carrier` / `none` |
| `fallback_reason` | string | 否 | 如果发生 fallback，记录原因 |
| `artifacts_produced` | string[] | 否 | 产出的 artifact 路径列表 |

### status 语义

| 值 | 语义 | 对 Verify 阶段的影响 |
|------|------|------|
| `completed` | 全部验收标准满足 | gate-skill 正常执行全量 evidence 汇总 |
| `partial` | 部分验收标准满足，有已知缺口 | gate-skill 仅对已完成的验收标准做 evidence 汇总，缺口标记为 open |
| `failed` | 执行失败，未满足验收标准 | 触发 recover-worktrack-skill，gate-skill 跳过本项 |
| `blocked` | 被外部因素阻塞，无法继续 | 触发 recover-worktrack-skill，`blockers` 字段必填 |

### fallback_reason 取值

| 值 | 说明 |
|------|------|
| `runtime fallback` | 运行时因权限、环境或依赖缺口无法委派，退回当前 carrier 执行 |
| `permission blocked` | 权限边界阻止委派，例如目标 SubAgent 不可达或超出授权范围 |
| `dispatch package unsafe` | dispatch packet 内容不安全（scope 过大、context_files 越界等），dispatch-skills 拒绝转发 |

### 约束规则

- `files_modified` 和 `files_created` 中的所有文件路径必须在 Dispatch Info Packet 的 `allowed_artifacts` 范围内
- `artifacts_produced` 列出本任务产出的所有 artifact 路径，包括 evidence 文件
- 当 `dispatch_mode_used` 与 Task Brief 的 `dispatch_mode` 不一致时，必须在 `fallback_reason` 中说明
- 当 `carrier_decision` 为 `current-carrier` 且 dispatch mode 为 `auto` 时，必须填写 `runtime_dispatch_profile`、`decision_inputs`、`delegation_attempted`、`attempted_carrier` 和 `fallback_reason` 或明确的 `selection_reason`
- `status` 为 `blocked` 时，`blockers` 必须至少包含一条具体阻塞项描述

## 与 Worktrack Contract 的关系

- Dispatch Task Brief 的 `scope` 和 `non_goals` 必须收束在 Worktrack Contract 声明的范围内
- Task Brief 的 `constraints` 不能比 Contract 的约束更宽松
- Dispatch Info Packet 的 `forbidden_boundaries` 必须比 Task Brief 的 `constraints` 更严格或等同
- Dispatch Result 的 `status` 决定 Verify 阶段的起点和 gate-skill 的处理路径
- `dispatch_mode` 默认从 Contract 的 `runtime_dispatch_mode` 继承，schedule-worktrack-skill 可按任务特征调整

## 与 Plan/Task Queue 的关系

- Dispatch Task Brief 的 `task_id` 必须对应 Plan/Task Queue 中的已有任务项
- 执行完成后，Dispatch Result 的 `status` 应回写到 Plan/Task Queue 中对应任务项的状态
- 若 Dispatch Result 的 `status` 为 `partial`，schedule-worktrack-skill 应将未完成的验收标准拆分为新的子任务

## 与 Gate Evidence 的关系

- `evidence_generated` 中列出的文件路径是 gate-skill 验证时的输入来源
- Dispatch Result 的 `summary` 和 `unresolved_issues` 可作为 gate-envelope 的补充上下文
- `status` 为 `completed` 时，`evidence_generated` 应覆盖所有 `acceptance` 条件对应的验证证据
