---
title: "Usage Help"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Usage Help

`docs/project-maintenance/usage-help/` 为初次接触 Harness 的使用者提供推荐使用路径，
以及按 backend 聚合的使用帮助，覆盖：target root 解析、override 参数、验证口径、
安装后使用、source 变更后的 operator 决策。

## 推荐入口

- [recommended-usage.md](./recommended-usage.md)：当前 operator 主入口，覆盖安装后的 Harness 调用与正常 Worktrack 路径。
- [recommended-usage.md](./recommended-usage.md)：Skills 使用教程，覆盖 skill 调用方式、backend 差异（agents vs claude）、常见工作流和场景速查。
- [usage-flow-examples.md](./usage-flow-examples.md)：已观察的 Servo 使用流程实例，用于理解真实项目中的 Harness state、docs 和应用代码如何并存。
- [TUI/CLI 合同](../../servo-installer/tui/human-cli-contract.md)：TUI 是人类推荐路径；CLI 是 AI/CI/脚本接口。理解两者的职责边界和引导流程。

## 按 backend 进入

| backend | 页面 | 主要差异 |
|---|---|---|
| `agents` | [codex.md](./codex.md) | 默认 `.agents/skills/`、source 变更决策、Codex Harness manual run |
| `claude` | [claude.md](./claude.md) | Claude runtime 路径、source 变更决策、冷启动 runbook |

关于 Deepseek V4 Pro/Lite、Claude、Pi、GPT-5.5、GPT-5.4/CodeX 等
模型与 runtime 的选择遵循 [Harness 指导思想](../../harness/foundations/Harness指导思想.md) 的 carrier 独立性与边界原则；具体能力由当前 backend 实测确认。
这些记录基于本项目的实测经验，不一定具有泛用性。建议使用者结合自身仓库的
任务情况，自行测试选择适合的 Agent 壳子和模型。

## 按初始化场景进入

| 场景 | 文档 |
|------|------|
| 已有代码项目初始化 Harness | [init-with-code.md](./init-with-code.md) |
| 空项目从零开始 | [recommended-usage.md](./recommended-usage.md) 的初始化入口 |
| 调整目标/追加需求 | [goal-change-guide.md](./goal-change-guide.md) |

## 和 servo-installer 文档的分工

- servo-installer 文档入口：[servo-installer/README.md](../../servo-installer/README.md)
- TUI 引导流程：[bundle-default-contract.md](../../servo-installer/tui/bundle-default-contract.md)
- destructive reinstall 主流程：[deploy-runbook.md](../../servo-installer/runbooks/deploy-runbook.md)
- 外部试用复制粘贴路径：直接看当前 backend 的 usage-help 页面
- 外部试用反馈模板：[trial feedback issue template](../../../.github/ISSUE_TEMPLATE/servo-installer-trial-feedback.yml) 与 [bug/blocker issue template](../../../.github/ISSUE_TEMPLATE/servo-installer-bug.yml)
- registry `npx` 验证、反馈日志与多临时 workdir 验证：[npx Command Test Execution](../testing/npx-command-test-execution.md)
- drift、冲突扫描、故障诊断：[skill-deployment-maintenance.md](../../servo-installer/runbooks/skill-deployment-maintenance.md)
- legacy `.aw/` runtime state 升级步骤：[Legacy `.aw` Runtime Upgrade Runbook](../../servo-installer/runbooks/aw-runtime-upgrade-runbook.md)
- add/update/rename/remove：看当前 backend 的 usage-help 页面

public/near-public trial 主路径仍是 `agents` backend；Claude Code 可安装完整 Harness skill payload，作为 Claude 适配 lane。
