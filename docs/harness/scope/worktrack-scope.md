---
title: "WorktrackScope 状态机"
status: active
updated: 2026-05-17
owner: servo-kernel
last_verified: 2026-05-17
---
# WorktrackScope 状态机

> 目的：固定 WorktrackScope 内部的 11 个合法状态、状态转移矩阵、异常路径和治理约束。两层 Scope 之间的闭环管理见 [repo-scope.md](./repo-scope.md)。

WorktrackScope 是 Harness 两层控制模型中的**快变量层**，负责单个 worktrack 从初始化到关闭的完整生命周期。两层 Scope 之间的闭环（RepoScope → WorktrackScope → RepoScope）见 [repo-scope.md](./repo-scope.md#reposcope--worktrackscope-切换)。

闭环路径（单 worktrack 视角）：RepoScope 观测决定 → Worktrack Contract → 初始化 Worktrack 和 baseline → 调度执行 → 收集 verify evidence → gate verdict → PR/merge/cleanup → 回到 RepoScope 刷新快照。失败判定（任一条即为未闭环）：仅发 PR 未完成 closeout、closeout 结果未回写 repo 级状态、RepoScope 与 WorktrackScope 混为同一文档。

## WorktrackScope 状态定义

WorktrackScope 下的合法状态共 11 个：

| 状态 | 含义 | 进入动作 |
|------|------|----------|
| `initializing` | Worktrack 刚创建，baseline 尚未建立 | 创建上下文，初始化 task queue 骨架 |
| `observing` | 观测当前 repo 状态，收集分析信息 | 执行 RepoScope 观测，生成快照 |
| `scheduling` | 制定任务队列与执行计划 | 展开 Contract 为 task queue、依赖图、覆盖矩阵 |
| `dispatching` | 按 Dispatch Decision Policy 选择执行载体 | 生成 dispatch handoff，标记 in_progress |
| `implementing` | 选定执行载体执行具体任务 | 执行变更（代码/文档），记录产出物 |
| `verifying` | 收集验证证据（测试/检查/review） | 按 review_profile 选择 review lanes，收集三类 evidence 面 |
| `judging` | 对 evidence 进行 gate verdict | 汇总 review 结果，按维度评分，输出 verdict |
| `recovering` | 处理 hard-fail 或异常后恢复 | 分析失败原因，修复问题，重新排队 |
| `closing` | 执行 PR/merge/cleanup | 创建 PR、合并、回写状态到 RepoScope |
| `blocked` | 不满足继续执行条件，需等待 | 记录阻塞原因，释放执行资源 |
| `closed` | 终端状态，Worktrack 生命周期结束 | 归档所有 artifact，清理临时状态 |

## 状态转移条件矩阵

下表定义每个状态允许的目标状态及转移条件。行=当前状态，列=目标状态。空单元格=不允许转移。

| 当前 \ 目标 | initializing | observing | scheduling | dispatching | implementing | verifying | judging | recovering | closing | blocked | closed |
|-------------|:-----------:|:---------:|:----------:|:-----------:|:------------:|:---------:|:-------:|:----------:|:-------:|:-------:|:------:|
| **initializing** | - | baseline 快照完成 | - | - | - | - | - | - | - | 初始化失败或外部依赖缺失 | - |
| **observing** | - | - | 观测完成且无歧义 | - | - | - | - | - | - | 观测数据不可用 | - |
| **scheduling** | - | Contract 变更需重观测 | - | task queue 非空且无阻塞项 | - | - | - | - | - | 依赖信息不足无法生成队列 | - |
| **dispatching** | - | - | dispatch 超时或无可用 task | - | 执行载体已领取 handoff packet | - | - | - | - | 无可用执行载体 | - |
| **implementing** | - | - | - | - | - | 所有 task 完成或触发 early-verify | 所有 task 完成 | 需中断实施回退 | - | 外部阻塞 | - |
| **verifying** | - | - | - | - | evidence 不足需补充实施 | - | 所有 evidence 面收集完毕 | 验证过程发现严重问题 | - | 缺少必要验证工具 | - |
| **judging** | - | - | - | soft-fail 带条件推进 | hard-fail | hard-fail 需重验证 | pass | hard-fail | pass 或 soft-fail | evidence 不完整 | - |
| **recovering** | - | 恢复至干净状态重新观测 | 恢复后重新排队 | - | 轻量修复可直接实施 | 修复后重新验证 | - | - | 确认恢复后关闭 | 恢复失败 | - |
| **blocked** | - | 阻塞解除后重新观测 | 阻塞解除后继续调度 | - | - | - | - | 需恢复处理 | - | - | - |
| **closing** | - | - | - | - | - | - | - | closeout 失败需恢复 | - | closeout 过程中外部阻塞 | PR 合并且回写完成 |
| **closed** | - | - | - | - | - | - | - | - | - | - | - |

## 异常路径

### 通用异常：到 blocked 的转移

任何非终端状态在以下条件满足时，允许转移到 `blocked`：

| 触发条件 | 说明 |
|----------|------|
| 外部依赖不可用 | API 宕机、外部工具链不可用 |
| 人工审批等待 | human reviewer 未响应 |
| 资源不可用 | 无可用执行载体、token 配额耗尽 |
| 证据缺失 | judging 阶段关键 evidence 面未生成 |
| 环境异常 | 文件系统只读、权限不足 |

进入 `blocked` 时必须记录：
- `blocked_reason`：阻塞原因
- `blocked_since`：阻塞开始时间戳
- `source_state`：从哪个状态进入 blocked
- `resolution_condition`：解除阻塞的条件（可验证的断言）

### 通用异常：到 recovering 的转移

任何非终端状态在以下条件满足时，允许转移到 `recovering`：

| 触发条件 | 说明 |
|----------|------|
| `hard-fail` verdict | judging 输出 hard-fail |
| 一致性异常 | 状态数据与 repo 实际状态不一致 |
| 合同违约 | Contract 声明约束被违反 |
| 未处理异常 | 未被其他 handler 捕获的错误 |
| 人工干预请求 | human 要求 abort 当前流程 |

进入 `recovering` 时必须记录：
- `recovery_reason`：触发恢复的原因
- `recovery_source_state`：从哪个状态进入
- `recovery_plan`：恢复计划（分析 -> 修复 -> 重新排队）

### blocked -> recovering 恢复路径

```
blocked →（阻塞解除 + 状态不一致）→ recovering
blocked →（阻塞解除 + 状态一致）→ observing
blocked →（阻塞解除 + 状态一致 + 任务队列完整）→ scheduling
```

典型进入 `recovering` 场景：baselines 过期无法回原状态、阻塞期间 repo 外部变更、阻塞原因永久性（工具废弃）。

从 `recovering` 恢复步骤：分析阻塞原因和 repo 状态 → 评估外部变更影响 → 重建 baselines → 修复任务队列 → 转移到 `scheduling`。

### recovering 返回路径

```
recovering →（恢复成功 + 需重新观测）→ observing
recovering →（恢复成功 + 任务队列已修复）→ scheduling
recovering →（恢复成功 + 确认关闭）→ closing
recovering →（恢复失败）→ blocked
```

### implementing 状态异常路径

| 场景 | 处理方式 |
|------|----------|
| plan 不可行 | 标记当前 task blocked，回到 scheduling 重新规划 |
| 结果与预期偏差 | 微调继续；大改则进入 recovering |
| SubAgent 超时/无响应 | task 标记 blocked，dispatch 备用 SubAgent 或等待 |
| 产出物冲突 | 进入 recovering 冲突解决 |

## 状态转移的治理约束

1. 所有状态转移必须记录在 Worktrack 日志中（时间戳、源状态、目标状态、触发条件）
2. `closed` 是终端状态，不可转移至任何其他状态
3. `closed` 进入条件：PR 合并完成 + repo snapshot 已刷新 + 所有 artifact 已归档
4. 不允许跨状态跳转（如 `scheduling` 直接跳到 `verifying`），除非通过异常路径
5. 同一时刻 WorktrackScope 处于唯一状态，不允许状态并存
