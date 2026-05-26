---
title: "模型 Runtime 支持边界"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# 模型 Runtime 支持边界

> 目的：记录 Servo 已测试过的 model/runtime 支持边界，同时避免把观察到的兼容性写成永久认证声明。

Servo 的定位是 repo-side contract layer。稳定合同来自本仓库中的 artifact / skill 协议；model runtime 是执行载体，不同 runtime 在工具 shell、SubAgent 支持、上下文处理和权限行为上可能不同。

## 已测试支持

截至 2026-05-26，Servo workflow 已在以下 model/runtime 家族上进行过使用验证，整体支持情况良好：

| Runtime family | 观察到的支持情况 | 说明 |
| --- | --- | --- |
| Deepseek V4 Pro | 良好 | 当外层 CLI / tool shell 提供所需 filesystem 和 git 操作时，适合承载 Harness control-loop 工作。 |
| Deepseek V4 Lite | 良好 | 适合较轻量的 Harness 和文档工作；涉及大范围实现变更时应使用更严格的验证。 |
| Claude | 良好 | 通过 `claude` backend 兼容路径和 repo-local `.claude/skills/` payload 支持。 |
| Pi | 良好 | 作为执行载体兼容性观察记录；仍需与其他载体一样提供 artifact 和 gate evidence。 |
| GPT-5.5 | 良好 | 在可通过 Codex-compatible tooling 使用时，适合复杂控制、实现、审查和恢复工作。 |
| GPT-5.4 / CodeX | 良好 | 当前 `agents` backend workflow 和 repo-local `.agents/skills/` payload 的主要 Codex-facing 路径。 |

这些观察只表示对应 model/runtime 家族已经成功承载过 Servo workflow。它们不能绕过 Worktrack contract、gate evidence 或 repo governance checks。

## 边界

模型支持事实不能替代：

- `servo-installer verify` 对 deploy target alignment 的证明
- Worktrack Contract 中的 scope、non-goals 和 acceptance criteria
- test / review / rule evidence
- programmer 对 Milestone 的最终验收
- npm 发布所需的 release-channel approval

当某个 runtime 无法证明 SubAgent dispatch 支持时，Harness 应使用 dispatch decision policy，并记录 current-carrier fallback，而不是声明已经完成 delegated execution。

## 后续入口

- Codex / agents 使用说明：[../../project-maintenance/usage-help/codex.md](../../project-maintenance/usage-help/codex.md)
- Claude backend 使用说明：[../../project-maintenance/usage-help/claude.md](../../project-maintenance/usage-help/claude.md)
- Dispatch carrier policy：[dispatch-decision-policy.md](./dispatch-decision-policy.md)
- Runtime dispatch contract：[runtime-dispatch-contract.md](./runtime-dispatch-contract.md)
