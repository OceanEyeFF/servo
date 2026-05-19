# Usage Help

`docs/project-maintenance/usage-help/` 保存新 operator 推荐使用路径，以及按 backend 聚合的使用帮助：target root 解析、override 参数、验证口径、安装后使用、source 变更后 operator 决策。

## 推荐入口

- [quickstart.md](./quickstart.md)：**新 operator 先读这里**。10 分钟快速教程：安装、初始化、第一个 Worktrack、handback 和显式 unlock 边界。
- [recommended-usage.md](./recommended-usage.md)：Skills 使用教程，覆盖 skill 调用方式、backend 差异（agents vs claude）、常见工作流和场景速查。

## 按 backend 进入

| backend | 页面 | 主要差异 |
|---|---|---|
| `agents` | [codex.md](./codex.md) | 默认 `.agents/skills/`、[quickstart 快速入门](./quickstart.md)、source 变更决策、Codex Harness manual run |
| `claude` | [claude.md](./claude.md) | Claude runtime 路径、[quickstart 快速入门](./quickstart.md)、source 变更决策、冷启动 runbook |

## 按初始化场景进入

| 场景 | 文档 |
|------|------|
| 已有代码项目初始化 Harness | [init-with-code.md](./init-with-code.md) |
| 空项目从零开始 | [init-greenfield.md](./init-greenfield.md) |
| 调整目标/追加需求 | [goal-change-guide.md](./goal-change-guide.md) |

## 和 Deploy 文档的分工

- 通用 deploy 入口：[deploy/README.md](../deploy/README.md)
- destructive reinstall 主流程：[deploy-runbook.md](../../aw-installer/runbooks/deploy-runbook.md)
- 外部试用复制粘贴路径：直接看当前 backend 的 usage-help 页面
- 外部试用反馈模板：[trial feedback issue template](../../../.github/ISSUE_TEMPLATE/aw-installer-trial-feedback.yml) 与 [bug/blocker issue template](../../../.github/ISSUE_TEMPLATE/aw-installer-bug.yml)
- registry `npx` 验证、反馈日志与多临时 workdir 验证：[npx Command Test Execution](../testing/npx-command-test-execution.md)
- drift、冲突扫描、故障诊断：[skill-deployment-maintenance.md](../../aw-installer/runbooks/skill-deployment-maintenance.md)
- add/update/rename/remove：看当前 backend 的 usage-help 页面

public/near-public trial 主路径仍是 `agents` backend；Claude Code 可安装完整 Harness skill payload，作为 Claude 适配 lane。
