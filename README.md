---
title: "AutoWorkflow"
status: active
updated: 2026-05-07
owner: aw-kernel
last_verified: 2026-05-07
---
# AutoWorkflow

> 一个 Codex-first 的 AI coding harness 平台，通过 repo-side contract layer 实现可控的 AI 编程工作流。

## 安装 Skills

确保有 Node.js 18+，在目标仓库根目录安装 Codex / agents backend 的 Harness Skills：

```bash
npx aw-installer
npx aw-installer tui
```

交互式终端中，已批准 package entrypoint 可以进入最小 TUI；CI、脚本或非交互环境应使用显式 CLI：

```bash
npx aw-installer --version
npx aw-installer diagnose --backend agents --json
npx aw-installer verify --backend agents
npx aw-installer update --backend agents
npx aw-installer update --backend agents --yes
npx aw-installer install --backend agents
```

当前 public / near-public 主路径仍是 `agents` backend，也就是 Codex 使用的 `.agents/skills/` payload。推荐从目标仓库根目录先做只读观察，再显式 apply：

```bash
npx aw-installer diagnose --backend agents --json
npx aw-installer update --backend agents
npx aw-installer update --backend agents --yes
npx aw-installer verify --backend agents
```

进阶安装、TUI、文件软连接和 Claude Code backend 见：

- [快速入门教程](docs/project-maintenance/usage-help/quickstart.md) — **新用户先读这里**
- [推荐使用流程](docs/project-maintenance/usage-help/recommended-usage.md)
- [Codex / agents 后端](docs/project-maintenance/usage-help/codex.md)
- [Claude Code 后端](docs/project-maintenance/usage-help/claude.md)

## 使用 Skills

> 以 Codex 为例

### 初始化仓库

目标仓库还没有 `.aw/` 时，先初始化 Harness 控制面：

```txt
$harness-skill 初始化当前工作目录的 harness 环境，初始化当前工作目录的 git 环境。
```

### 设置仓库 Final State

需要明确或重设仓库最终状态时，给出目标、非目标、验收标准和约束：

```txt
$set-harness-goal-skill 当前仓库期望最终实现一个 [目标描述]。
```

如果是对已有 Goal Charter 做方向变更，走目标变更控制：

```txt
$repo-change-goal-skill 将当前仓库目标调整为 [新目标]，变更理由是 [原因]。
```

### 追加临时任务或者补充需求

已有目标后，追加一个临时任务、新功能、设计请求或当前 worktrack 的补充需求：

```txt
$repo-append-request-skill 补充一个功能：[要新增或补充的内容]；边界是 [希望包含什么，不包含什么]。
```

Harness 会把请求分类为 new worktrack、scope expansion、design-only、design-then-implementation 或 goal change，再给出下一步路由。

## 场景指南

| 场景 | 文档 |
|------|------|
| **新用户快速入门** | [quickstart.md](docs/project-maintenance/usage-help/quickstart.md) |
| 已有代码项目初始化 Harness | [init-with-code.md](docs/project-maintenance/usage-help/init-with-code.md) |
| 空项目从零开始 | [init-greenfield.md](docs/project-maintenance/usage-help/init-greenfield.md) |
| 推荐使用流程 | [recommended-usage.md](docs/project-maintenance/usage-help/recommended-usage.md) |
| 调整目标 / 追加需求 | [goal-change-guide.md](docs/project-maintenance/usage-help/goal-change-guide.md) |

## 仓库维护者

内部结构说明、目录分层、入口分工和项目机制见 [Repository Onboarding](docs/project-maintenance/repo-onboarding.md)、[Docs](docs/README.md) 和 [AGENTS.md](AGENTS.md)。

## 许可证

MIT License，以根目录 [LICENSE](./LICENSE) 文件为准。

## 友情链接

LinuxDo[https://linux.do/]
