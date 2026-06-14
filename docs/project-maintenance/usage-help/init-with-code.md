---
title: "初始化 Harness：已有代码项目"
status: active
updated: 2026-05-07
owner: servo-kernel
last_verified: 2026-06-13
---

# 初始化 Harness：已有代码项目

> 适用于 target repo 已有代码（正在开发或已存在），需要引入 Harness 控制面管理后续 AI coding 工作。

## 前置条件

- Node.js 18+（`node --version` 确认）
- `npx` 可用（npm 7+ 自带）
- target repo 已 clone 到本地，有 git 历史

## 一、安装 Harness Skills

在目标仓库根目录运行：

```bash
# 只读诊断：确认当前状态和目标路径
npx servo-installer diagnose --backend agents --json

# 安装（写入 skills 到 .agents/skills/）
npx servo-installer install --backend agents

# 验证安装完整性
npx servo-installer verify --backend agents
```

其他 backend 使用对应 `--backend` 参数：

```bash
npx servo-installer diagnose --backend claude --json
npx servo-installer install --backend claude
npx servo-installer verify --backend claude
```

## 二、初始化 Harness 控制面

安装完成后，在 Coding CLI 中调用 `set-harness-goal-skill` 建立控制面。以 Codex 为例：

```txt
$set-harness-goal-skill 请根据当前已有代码项目初始化 Harness，并生成可确认的 Goal Charter 草稿。
```

目标描述应包含：

- 项目最终结果（可执行的边界）
- 当前非目标和禁止触碰范围
- 可验证的验收标准
- 目录、命令、审批和写回约束

## 三、开始第一个 Worktrack

控制面初始化后，Harness 进入 `RepoScope.Observe`。推荐路径：

1. 让 Harness 观察当前状态 -- `$harness-skill`
2. 提出第一项 bounded worktrack 请求
3. 等待 contract 和 plan 建立后执行
4. 完成后验证、gate、closeout

详见 [recommended-usage.md](./recommended-usage.md) 的完整使用流程。

## 四、注意事项

- 已有代码的项目先 `diagnose --json` 做只读确认，避免误覆盖
- 如果 target repo 已有 `.agents/` 或 `.claude/` 目录，`install` 前先 `update --json` 查看 diff
- Harness 控制面（`.servo/`）是 runtime state，不提交到版本控制；skills（`.agents/skills/` 或 `.claude/skills/`）可按需提交或 gitignore
