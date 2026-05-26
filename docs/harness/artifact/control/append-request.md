---
title: "Append Request"
status: active
updated: 2026-05-25
owner: servo-kernel
last_verified: 2026-05-25
---
# Append Request

管理外部追加请求（append-feature/append-design/append-milestone）的分类与路由，将其归入 goal change、new milestone、new worktrack、scope expansion、design-only 或 design-then-implementation，不直接执行追加内容。

最少应包含：原始请求与 mode、分类结果与理由、对 `GoalCharter`、Milestone Pipeline 和活跃 worktrack 的影响、下一路由与 scope、suggested milestone action（如适用）、suggested node type（如适用）、设计/实现阶段边界（如适用）、权限边界与审批原因、最小缺失信息、`approval_required`、`continuation_ready`、`continuation_blockers`。

`append-milestone` 用于表达 milestone 级追加：创建新的 milestone、注册 planned milestone、激活符合条件的 planned milestone，或向已有 milestone 追加 worktrack 的请求。其分类结果优先为 `new milestone`，下一路由为 `init-milestone-skill`，必须输出 milestone brief 所需的最小字段、审批边界和 `recommended_next_scope: RepoScope`。若请求只是向当前活跃 worktrack 扩范围，仍按 `scope expansion` 处理；若改变 Goal Charter，仍按 `goal change` 处理。

字段一致性：`approval_required: true` 时 `continuation_ready` 须为 `false` 且 `continuation_blockers` 须列出待审批项（已含明确授权时除外）。分类置信度 `low` 或缺失信息阻塞分类/路由/授权时 `continuation_ready` 须为 `false`。仅 `approval_required: false` 且无阻塞性缺失信息时可为 `true`。

硬约束：Append Request 不是 `WorktrackContract` 或 `GoalChangeRequest`。不授权执行，只表达分类与路由。分类结果为 goal change 或 scope expansion 时须显式暴露审批边界。
