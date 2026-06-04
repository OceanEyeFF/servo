---
title: "Plan / Task Queue"
status: active
updated: 2026-06-04
owner: servo-kernel
last_verified: 2026-06-04
---
# Plan / Task Queue

将 `WorktrackContract` 展开为可执行子任务序列。

Plan / Task Queue 是单个 Worktrack 内的局部任务窗口 / task window，不是 Repo backlog、Milestone backlog、candidate milestone 列表或候选 Milestone 列表。它只能展开当前已批准的 `WorktrackContract`，不得创建 milestone、追加 worktrack、改变 milestone purpose，或把 RepoScope.Decide 的候选建议解释成执行队列。

在同一 Worktrack Contract 范围内，queue 可以规划多个连续小任务，并按依赖、验收映射和 dispatch handoff 连续推进。连续推进不等于一次 dispatch 执行整个 queue：`schedule-worktrack-skill` 每轮只能选择一个当前下一步动作，并生成 bounded dispatch handoff packet；`dispatch-skills` 只消费该 packet，不反向改写 queue。

最少应包含：

- 子任务列表
- 执行顺序
- 依赖关系
- 阻塞项
- 下一动作
- 下一动作的稳定标识
- 当前 round 的 dispatch handoff packet
- 验收条件与任务队列的对齐关系

## 任务队列字段规范

每个 task 条目必须包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 全局唯一标识，格式 `WT-{编号}` 或 `{阶段缩写}-{序号}`，如 `WT-001`、`IMPL-003` |
| `status` | enum | 是 | `pending` / `in_progress` / `completed` / `blocked` / `deferred` |
| `priority` | enum | 是 | `P0`（阻塞级，必须立即处理）/ `P1`（当前 round 必须完成）/ `P2`（可延后至下一轮） |
| `assigned` | string | 是 | 执行者标识：`SubAgent/{name}` / `current-carrier` / `human` |
| `description` | string | 是 | 任务描述，一句话概括任务目标 |
| `depends_on` | list[string] | 是（可空） | 前置任务的 `task_id` 列表，硬依赖（未完成前不能开始） |
| `acceptance` | list[string] | 是 | 验收标准列表，每项需映射到 contract 中的验收标准编号 |
| `estimated_effort` | enum | 否 | 工作量估算：`S`（<1h）/ `M`（1-4h）/ `L`（4h-1d）/ `XL`（>1d） |

### 状态流转

```
pending → in_progress → completed
  ↓          ↓
blocked   blocked
  ↓          ↓
pending   pending（阻塞解除后）

deferred → pending（被重新激活时）
```

- `pending`：任务入队但未开始，依赖未满足时不得转为 `in_progress`
- `in_progress`：当前正在执行，同一时刻每个 SubAgent 最多持有一个 `in_progress` 任务
- `completed`：任务完成且验收通过
- `blocked`：任务因外部原因（非依赖）被阻塞，需等待外部事件
- `deferred`：任务被主动延后，不在当前 round 执行范围

## 依赖与阻塞格式

### 硬依赖（depends_on）

`depends_on` 表示任务级硬依赖：列出的 `task_id` 必须全部 `completed` 后，当前任务才能从 `pending` 转为 `in_progress`。

```yaml
task_id: "IMPL-003"
depends_on:
  - "IMPL-001"
  - "IMPL-002"
```

若 `depends_on` 为空列表，表示无硬依赖，可立即开始。

### 外部阻塞（blocked_by）

`blocked_by` 记录非任务依赖的外部阻塞项，与 `depends_on` 区分：

| 字段 | 类型 | 说明 |
|------|------|------|
| `blocked_by.type` | string | 阻塞类型：`approval` / `external-service` / `resource` / `decision` |
| `blocked_by.description` | string | 阻塞原因描述 |
| `blocked_by.since` | datetime | 阻塞开始时间 |
| `blocked_by.resolution_target` | datetime | 期望解决时间（可选） |

```yaml
task_id: "VER-002"
status: blocked
blocked_by:
  type: approval
  description: "等待 human reviewer 对 gate evidence 的确认"
  since: "2026-05-08T10:00:00Z"
  resolution_target: "2026-05-09T18:00:00Z"
```

### 后继阻塞（blocks）

`blocks` 字段列出被当前任务阻塞的后续任务列表，用于正向追踪影响面：

```yaml
task_id: "IMPL-001"
blocks:
  - "IMPL-003"
  - "VER-001"
```

`blocks` 是 `depends_on` 的反向索引，由工具自动维护，不要求人工填写。

### 阻塞项处理规则

1. 当 `blocked_by` 非空时，任务状态必须设为 `blocked`
2. 当 `depends_on` 中有任意任务未 `completed` 时，任务不得从 `pending` 转为 `in_progress`
3. 阻塞解除后，任务自动回到 `pending`（如果之前是 `blocked`）并重新参与调度
4. 连续阻塞超过 48 小时的任务应触发 escalation 并通知 human

## 验收映射

每个 task 的 `acceptance` 列表必须与 `Worktrack Contract` 中的验收标准（AC）建立映射关系。

### 映射格式

```yaml
task_id: "IMPL-002"
description: "实现 gate-evidence.md 的 verdict 字段定义"
acceptance:
  - ref: "AC-GE-001"
    description: "verdict 字段包含四种取值，每种有明确语义"
  - ref: "AC-GE-002"
    description: "低严重度吸收规则完整且可执行"
```

其中 `ref` 对应 `contract.md` 中定义的验收标准编号。

### 覆盖矩阵

任务队列完成后，需生成覆盖矩阵确认所有 AC 都有对应任务（且所有任务都有 AC 对应）：

| AC 编号 | 对应 task_id | 状态 |
|---------|-------------|------|
| AC-GE-001 | IMPL-002 | completed |
| AC-PT-001 | IMPL-003 | in_progress |
| AC-SL-001 | IMPL-004 | pending |

覆盖矩阵应在 `scheduling` 状态时生成，在 `verifying` 状态时逐项验证。

## Worktrack Task Window

任务窗口用于把一个 bounded Worktrack 分解成可连续推进的小任务：

- window 的边界等于当前 `WorktrackContract` 的目标、范围、非目标、验收标准和验证要求。
- window 可以包含多个 pending task，但同一调度轮只选一个 `selected_next_action`。
- task 之间通过 `depends_on`、`blocks`、`acceptance` 和 queue status 形成局部执行顺序。
- 当前 task 完成后，若没有 gate fail、scope drift、approval boundary、runtime gap 或 evidence conflict，WorktrackScope 可以继续调度 window 内的下一 task。
- window 内任务不得修改 RepoScope 目标、Milestone Pipeline 或 Worktrack list；需要新增/移除/重排 Worktrack 时，必须回到 RepoScope.Decide / programmer approval。
- queue 完成只表示当前 Worktrack 的任务窗口完成；仍需 Verify、Judge、Close 和 RepoScope.Refresh 后，结果才可汇入 Milestone progress。

该语义与 Milestone 方向选择分离：Milestone 选择“下一段 repo 演进方向”，Plan / Task Queue 只安排“当前 Worktrack 合同内接下来做什么”。

### 验收标准引用约定

- Contract 中的 AC 编号格式：`AC-{域缩写}-{序号}`
- 域缩写映射：GE = Gate Evidence, PT = Plan/Task Queue, SL = State Loop, CT = Contract
- 每个 task 至少包含 1 个 `acceptance` 条目
- 每个 AC 至少被 1 个 task 覆盖
