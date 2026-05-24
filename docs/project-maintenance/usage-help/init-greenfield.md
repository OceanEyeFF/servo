---
title: "初始化 Harness：空项目（Greenfield）"
status: active
updated: 2026-05-07
owner: servo-kernel
last_verified: 2026-05-07
---

# 初始化 Harness：空项目（Greenfield）

> 适用于从零开始的新项目，先建立 Harness 控制面，再在控制面下推进开发。

## 前置条件

- Node.js 18+（`node --version` 确认）
- `npx` 可用（npm 7+ 自带）
- 已创建空目录并初始化 git：`mkdir my-project && cd my-project && git init`

## 一、安装 Harness Skills

```bash
# 只读诊断
npx servo-installer diagnose --backend agents --json

# 安装
npx servo-installer install --backend agents

# 验证
npx servo-installer verify --backend agents
```

## 二、设置项目目标

以 Codex 为例：

```txt
$set-harness-goal-skill 当前空仓库期望最终实现一个 [目标描述]。
```

目标描述示例：

> 构建 RESTful API 服务，使用 Express + TypeScript，支持用户注册登录和资源 CRUD。数据库使用 PostgreSQL。第一轮只做用户模块。不接入第三方 OAuth，不做前端。

设定目标后，Harness 创建 `.servo/goal-charter.md`，包含项目愿景、核心目标、技术方向和工程节点映射。

## 三、启动第一个 Worktrack

目标设定完成后：

1. `$harness-skill` 进入控制回路
2. 提出第一个 feature 请求（如"搭建 Express + TypeScript 项目骨架"）
3. Harness 创建 worktrack contract -> plan -> dispatch -> verify -> gate -> closeout

## 四、空项目的推荐节奏

1. **Round 0**：项目初始化（install + set-harness-goal）
2. **Round 1**：项目骨架（目录结构、配置文件、CI 基础）
3. **Round 2+**：按功能模块拆分 bounded worktrack

## 五、注意事项

- 空项目没有历史 baseline，Goal Charter 是唯一参考信号
- 第一轮 worktrack 建议保守：只搭建骨架和基础设施
- 不一次性定义完整项目架构，通过追加需求逐步演进（详见 [goal-change-guide.md](./goal-change-guide.md)）
