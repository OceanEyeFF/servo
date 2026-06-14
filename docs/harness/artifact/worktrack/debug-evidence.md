---
title: "Debug Evidence"
status: active
updated: 2026-05-13
owner: servo-kernel
last_verified: 2026-06-13
---

# Debug Evidence

> 记录调试日志、复现步骤和根因假设的压缩证据。原始日志可以归档，但进入主控制上下文的只能是本 artifact 的结构化摘要。

## 定位

- Scope: `WorktrackScope`
- Function: `Verify` / `Recover`
- 上游输入: 原始日志、命令输出、复现步骤、失败截图或外部错误报告
- 下游消费: `review-evidence-skill`、`test-evidence-skill`、`recover-worktrack-skill`、`gate-skill`

Debug Evidence 不替代 Gate Evidence。它只回答"调试观察到什么、哪些事实已确认、哪些假设被排除"。

## Required Fields

| 字段 | 类型 | 必须 | 说明 |
| --- | --- | --- | --- |
| `source_logs` | `string[]` | required | 原始日志路径、命令引用或外部报告引用；不内联大段日志 |
| `symptom` | `string` | required | 用户或测试可观察到的症状 |
| `reproduction_steps` | `string[]` | required | 最小复现步骤 |
| `observed_error` | `string` | required | 关键错误摘要，避免粘贴完整日志 |
| `root_cause_hypothesis` | `string[]` | required | 当前根因假设 |
| `confirmed_facts` | `string[]` | required | 已通过日志、测试或代码检查确认的事实 |
| `discarded_hypotheses` | `string[]` | required | 已排除的假设及排除理由 |
| `affected_files` | `string[]` | optional | 可能受影响文件 |
| `fix_attempts` | `string[]` | optional | 已尝试修复及结果 |
| `remaining_unknowns` | `string[]` | required | 仍未确认的事实 |
| `next_debug_action` | `string` | required | 下一步调试动作 |

## Raw Log Boundary

- 原始日志应保存在 `.servo/tmp/`、外部 CI、测试报告或明确 artifact 路径中。
- 主上下文只接收 `observed_error`、`confirmed_facts`、`discarded_hypotheses` 和 `remaining_unknowns`。
- 单条原始日志超过当前 `context_budget` 时，必须先由 log-extract worker 或 current-carrier 摘要成 Debug Evidence。
- 不得把 unrelated historical logs 作为默认上下文传入 dispatch packet。

## Gate Intake

Gate 消费 Debug Evidence 时应检查：

- 复现步骤是否足够最小
- confirmed facts 是否能支撑 root cause 或 recovery route
- discarded hypotheses 是否避免重复调试
- remaining unknowns 是否阻塞 verdict
- next_debug_action 是否仍在当前 Worktrack Contract 范围内

Debug Evidence 不足时，Gate verdict 应为 `blocked` 或路由到 `recover-worktrack-skill`，不得把未确认根因当成已验证事实写回长期文档层。
