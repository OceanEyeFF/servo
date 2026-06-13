---
title: "Dispatch Decision Policy"
status: active
updated: 2026-05-20
owner: servo-kernel
last_verified: 2026-06-13
---

# Dispatch Decision Policy

> 定义 `dispatch_mode: auto` 如何在 SubAgent、专用 skill、generic worker 和 current-carrier 之间选择执行载体。字段合同见 [dispatch-packet.md](../artifact/worktrack/dispatch-packet.md)。

## Policy Goal

`auto` 不是"能分派就分派"。`auto` 表示调度与分派阶段必须根据任务耦合度、上下文共享需求、风险面、可验证性和运行时权限选择执行载体。

选择执行载体时保持两个目标：

- 避免控制器吸收执行平面工作
- 避免为强共享状态、连续编码或单模块重构制造无价值的上下文分裂

## Carrier Selection Matrix

| 任务类型 | 默认执行载体 | 说明 |
| --- | --- | --- |
| 小范围连续编码 | `current-carrier` | 共享状态强、切换成本高，保持单一执行上下文 |
| 单模块 bugfix | `current-carrier` 或 `one-shot worker` | 能清晰打包且边界窄时可分派，否则当前载体执行 |
| 多文件强一致性重构 | `current-carrier + review SubAgent` | 实现保持一致上下文，审查可分派 |
| 多源搜索 / 调研 | `SubAgent fanout` | 输入可分片、输出可汇总，适合并行 |
| repo analysis | `SubAgent` 可用 | 适合独立读取和结构化回传 |
| code review | 按 `review_profile` 选择 SubAgent lanes | 由 Gate Evidence 的风险档位决定 |
| debug log 提取 | `log-extract worker` 或 current-carrier fallback | 原始日志不直接进入主上下文，先产出 Debug Evidence 摘要 |
| 文档追平 | `doc-catch-up-worker-skill` | 已验证事实写回长期文档层 |
| 大范围实现 | 先 `split-worktrack` | 不通过单次 dispatch 吞入大批次 |

## Decision Inputs

`auto` 分派必须显式考虑：

- `task_coupling`: `low | medium | high`
- `state_sharing_need`: `low | medium | high`
- `parallel_value`: `low | medium | high`
- `risk_profile`: `low | medium | high`
- `context_budget_fit`: `yes | no`
- `runtime_supports_subagent`: `yes | no`
- `permission_allows_delegation`: `yes | no`
- `runtime_dispatch_profile`: 当前 backend/model/runtime 的能力画像
- `backend_runtime`: 如 `codex-cli`、`claude-code-cli`、`unknown`
- `model_family`: 如 `gpt`、`claude`、`deepseek`、`unknown`
- `subagent_dispatch_shell`: `available | unavailable | unknown`
- `subagent_permission_state`: `allowed | blocked | unknown`
- `dispatch_package_safety`: `safe | unsafe | unknown`
- `delegation_attempted`: `yes | no`
- `attempted_carrier`: `SubAgent | generic-worker-skill | doc-catch-up-worker-skill | current-carrier | none`

`ClaudeCodeCLI` / `Deepseek` 这类兼容 lane 不应被静默解释为 `current-carrier`。如果宿主运行时无法证明存在真实 SubAgent dispatch shell，必须把 `subagent_dispatch_shell = unavailable | unknown` 写入 `runtime_dispatch_profile`，并在 `delegation_attempted`、`attempted_carrier` 和 `fallback_reason` 中说明没有分派或分派失败的原因。

当 `dispatch_package_safety = unsafe` 时，fallback reason 必须使用 `dispatch package unsafe`，并返回调度阶段收紧 scope、context_budget 或 forbidden boundaries。

## Decision Rules

1. `state_sharing_need: high` 且 `parallel_value` 不高时，默认选择 `current-carrier`。
2. `parallel_value: high` 且任务可拆成独立输入/输出时，优先选择 `SubAgent` 或 fanout。
3. `risk_profile: high` 时，实现可保持当前载体，但 review/test/policy evidence 应按风险选择独立验证 lane。
4. `context_budget_fit: no` 时不得强行分派，应返回调度阶段拆分或收紧上下文。
5. `runtime_supports_subagent: no` 或 `permission_allows_delegation: no` 时，若任务仍可安全执行，可 `current-carrier` fallback，并记录 `runtime fallback` 或 `permission blocked`；同时必须记录 `runtime_dispatch_profile`、`delegation_attempted`、`attempted_carrier` 与 `fallback_reason`。
6. `delegated` 模式不走 policy 降级；无法真实分派时返回 gap/block。
7. `current-carrier` 模式显式关闭分派，不再重新评估 SubAgent。
8. `auto` 模式下，如果 `parallel_value: high`、`task_coupling: low|medium`、`context_budget_fit: yes`、`subagent_permission_state: allowed` 且 `subagent_dispatch_shell: available`，应尝试 `SubAgent` 或记录为什么没有尝试；直接选择 `current-carrier` 但缺少理由的行为必须返回 blocked。

## Required Output

每次 `auto` 选择执行载体时，dispatch result 必须说明：

- `dispatch_policy_ref`
- `runtime_dispatch_profile`
- `carrier_decision`
- `decision_inputs`
- `delegation_attempted`
- `attempted_carrier`
- `selection_reason`
- `fallback_reason`（如有）

省略选择理由或把 current-carrier fallback 伪装成真实 SubAgent 分派的行为必须返回 blocked。
