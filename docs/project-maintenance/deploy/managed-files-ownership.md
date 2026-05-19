---
title: "Managed Files Ownership"
status: active
updated: 2026-05-19
owner: aw-kernel
last_verified: 2026-05-19
---
# Managed Files Ownership

> 目的：明确 aw-installer 管理文件的所有权边界，区分 installer 管理的 skill payload、`.aw/` 运行时控制状态、deploy target 和用户自有仓库文件。

本页管理文件所有权分类。deploy target 的角色与映射见 [deploy-mapping-spec.md](./deploy-mapping-spec.md)。payload 来源与写入边界见 [payload-provenance-trust-boundary.md](./payload-provenance-trust-boundary.md)。

## 所有权分类

```
target repo root/
├── .agents/           ← deploy target（installer 写入，派生自 canonical source）
│   └── skills/        ← installer 管理的 skill payload
│       └── aw-*/      ← 受管目录（含 aw.marker）
├── .claude/           ← deploy target（installer 写入，派生自 canonical source）
│   └── skills/        ← installer 管理的 skill payload
│       └── */         ← 受管目录（含 marker）
├── .aw/               ← 运行时控制状态（Harness 管理，非 installer payload）
├── src/               ← 用户自有
├── docs/              ← 用户自有
├── package.json       ← 用户自有（npm package 元数据）
└── ...                ← 用户自有
```

## 分类详述

### 1. Installer 管理的 skill payload

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.agents/skills/aw-*` 和 `<targetRepoRoot>/.claude/skills/*` |
| 创建者 | `aw-installer install` |
| 更新者 | `aw-installer update --yes` |
| 删除者 | `aw-installer prune --all` 或 operator 手动删除 |
| 识别方式 | 每个受管目录内的 `aw.marker` 文件 |
| 真相源 | canonical source (`product/harness/skills/`) |

**operator 可以做什么：**
- 使用 `aw-installer prune --all` 安全删除
- 手动删除后运行 `aw-installer verify` 检测不一致

**operator 不应做什么：**
- 不应手动编辑受管目录内的文件——下次 `install`/`update` 会覆盖
- 不应把受管文件当作配置模板来修改——修改应回到 canonical source
- 不应将 deploy target 内容视为版本真相

### 2. 运行时控制状态（`.aw/`）

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.aw/` |
| 创建者 | Harness 初始化流程（`set-harness-goal-skill`） |
| 管理方式 | Harness 控制回路在运行时读写 |
| 是否受 installer 管理 | **否**——`prune --all` 不删除 `.aw/` |
| 生命周期 | 独立于 installer payload；可手动删除以重置 Harness 状态 |

`.aw/` 目录包含：
- `control-state.md` — Harness 控制面配置与状态
- `goal-charter.md` — Repo 目标章程
- `repo/` — 仓库级快照与 backlog
- `worktrack/` — 当前 worktrack 合同、任务队列与证据
- `milestone/` — Milestone artifact 文件

**重要约束：**
- `.aw/` 不是 installer payload，不受 `prune --all` 影响
- `.aw/` 不是 source of truth——真相在 `docs/` 和 `product/`
- `.aw/` 是 gitignored 的运行时状态，不同步到 remote
- 删除 `.aw/` 后 Harness 需要重新初始化

### 3. Deploy target

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.agents/` 和 `<targetRepoRoot>/.claude/` |
| 真相源 | canonical source (`product/harness/`) |
| 写入者 | `aw-installer install` / `aw-installer update --yes` |
| 角色 | 派生副本——承载 backend 运行时可用的 skill 文件 |

**deploy target 是什么：**
- canonical source 在 target repo 中的安装副本
- backend runtime (Codex/Claude) 读取 skill 文件的路径
- 每个 `install`/`update` 操作都会完整替换

**deploy target 不是什么：**
- **不是 source of truth**——真相在 `product/harness/skills/`
- **不是配置位置**——operator 不应手动修改 deploy target 内容
- **不是备份**——`prune --all` 会完全删除
- **不是版本事实**——deploy target 中是否存在文件不能替代 `verify` 命令

### 4. 用户自有文件

所有不在上述分类中的仓库文件均为用户自有。包括但不限于：
- 源代码（`src/`、`product/`、`toolchain/`）
- 文档（`docs/`）
- 配置文件（`package.json`、`tsconfig.json` 等）
- Git 仓库数据（`.git/`）
- 依赖目录（`node_modules/`）

**installer 对用户自有文件的保证：**
- `install` 只写入 deploy target 目录
- `prune --all` 只删除受管目录
- 任何 installer 操作都不会触及用户自有文件
- `check_paths_exist` 在写入前检测冲突，但只读不写

## 非目标（Non-Goals）

以下内容不在 aw-installer 管理文件的所有权范围内：

| 内容 | 原因 | 相关工具 |
|------|------|---------|
| npm 全局安装路径 | npm 管理，非 aw-installer 管理 | `npm uninstall -g aw-installer` |
| `node_modules/` | npm/pnpm/yarn 管理 | 包管理器 |
| `.git/` | Git 管理 | `git` |
| shell profile / PATH | 系统配置 | 手动编辑 |
| `.aw_template/` | repo-local 模板，非 deploy target | 项目维护 |

## 不变量

- installer 只写入 deploy target（`.agents/skills/`、`.claude/skills/`）
- `.aw/` 与 installer payload 生命周期独立
- 用户自有文件永远不会被 installer 修改或删除
- deploy target 不是 source of truth
- 单一真相源保持在 `product/harness/skills/` 和 `docs/`

## 停止线

问题进入 npm 全局安装管理、shell 环境配置、Git 仓库结构或 CI/CD pipeline 时，本文档只提供链接，不展开。
