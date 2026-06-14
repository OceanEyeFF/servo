---
title: "Managed Files Ownership"
status: active
updated: 2026-05-22
owner: servo-kernel
last_verified: 2026-06-13
---
# Managed Files Ownership

> 目的：明确 servo-installer 管理文件的所有权边界，区分 installer 管理的 skill payload、`.servo/` 运行时控制状态、deploy target 和用户自有仓库文件。

本页给出通用所有权分类方案，并以本仓库为实例说明每个分类在真实项目中的对应路径。deploy target 的角色与映射见 [deploy-mapping-spec.md](../contracts/deploy-mapping-spec.md)。payload 来源与写入边界见 [payload-provenance-trust-boundary.md](../contracts/payload-provenance-trust-boundary.md)。

## 通用所有权分类

servo-installer 管理的 target repo 中存在四类文件所有权，按"谁写入、谁删除、谁持有真相"区分：

```
target repo root/
├── .agents/           ← deploy target（installer 写入，派生自 canonical source）
│   └── skills/        ← installer 管理的 skill payload
│       └── aw-*/      ← 受管目录（含 aw.marker）
├── .claude/           ← deploy target（installer 写入，派生自 canonical source）
│   └── skills/        ← installer 管理的 skill payload
│       └── */         ← 受管目录（含 marker）
├── .servo/               ← 运行时控制状态（Harness 管理，非 installer payload）
├── .aw/                  ← 旧版运行时控制状态（仅显式升级路径处理）
├── src/               ← 用户自有
├── docs/              ← 用户自有
├── package.json       ← 用户自有（npm package 元数据）
└── ...                ← 用户自有
```

## 分类详述

### 1. Installer 管理的 skill payload

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.agents/skills/servo-*` 和 `<targetRepoRoot>/.claude/skills/*` |
| 创建者 | `servo-installer install` |
| 更新者 | `servo-installer update --yes` |
| 删除者 | `servo-installer prune --all` 或 operator 手动删除 |
| 识别方式 | 每个受管目录内的 `aw.marker` 文件 |
| 真相源 | canonical source (`product/harness/skills/`) |

**允许操作：**
- 使用 `servo-installer prune --all` 安全删除
- 手动删除后运行 `servo-installer verify` 检测不一致

**禁止操作：**
- 不应手动编辑受管目录内的文件——下次 `install`/`update` 会覆盖
- 不应把受管文件当作配置模板来修改——修改应回到 canonical source
- 不应将 deploy target 内容视为版本真相

### 2. 运行时控制状态（`.servo/`）

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.servo/` |
| 创建者 | Harness 初始化流程（`set-harness-goal-skill`） |
| 管理方式 | Harness 控制回路在运行时读写 |
| 是否受 installer 管理 | **否**——`prune --all` 不删除 `.servo/` |
| 生命周期 | 独立于 installer payload；可手动删除以重置 Harness 状态 |

`.servo/` 目录包含：
- `control-state.md` — Harness 控制面配置与状态
- `goal-charter.md` — Repo 目标章程
- `repo/` — 仓库级快照与 backlog
- `worktrack/` — 当前 worktrack 合同、任务队列与证据
- `milestone/` — Milestone artifact 文件

**重要约束：**
- `.servo/` 不是 installer payload，不受 `prune --all` 影响
- `.servo/` 不是真相源——真相在 `docs/` 和 `product/`
- `.servo/` 通常是 gitignored 的运行时状态，不同步到 remote
- 删除 `.servo/` 后 Harness 需要重新初始化

### 2a. 旧版运行时控制状态（`.aw/`）

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.aw/` |
| 角色 | 旧版 Harness 运行时状态（`.servo/` 的前身） |
| 是否受 installer 管理 | **否**——`prune --all` 不删除 `.aw/` |
| 默认升级行为 | 只允许显式 upgrade path；普通 install/update/verify/diagnose 不迁移 |

`.aw/` 不是 installer payload，也不是 deploy target。它只在旧版运行时迁移场景下作为迁移源参与处理；安全边界见 [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md)。

**重要约束：**
- 不把 `.aw/` 当作 `aw.marker`
- 不把 `.aw/` 默认移动或删除
- 已存在 `.servo/` 时，`.aw/` 到 `.servo/` 的升级默认阻断
- 清理 `.aw/` 必须是 operator 的显式决定

### 3. Deploy target

| 属性 | 值 |
|------|-----|
| 路径 | `<targetRepoRoot>/.agents/` 和 `<targetRepoRoot>/.claude/` |
| 真相源 | canonical source (`product/harness/`) |
| 写入者 | `servo-installer install` / `servo-installer update --yes` |
| 角色 | 派生副本——承载 backend 运行时可用的 skill 文件 |

**deploy target 是什么：**
- canonical source 在 target repo 中的安装副本
- backend runtime (Codex/Claude) 读取 skill 文件的路径
- 每个 `install`/`update` 操作都会完整替换

**deploy target 不是什么：**
- **不是真相源**——真相在 `product/harness/skills/`
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

## 以本仓库为例

以下将通用分类映射到 `servo` 仓库的实际路径，帮助 operator 理解各分类在真实项目中的对应关系。

### 本仓库的文件所有权映射

```
servo/           ← 用户自有（target repo 本身）
│
├── .agents/skills/                ← deploy target（installer 管理）
│   ├── servo-harness-skill/          ← 受管 skill payload
│   ├── servo-close-worktrack-skill/  ← 受管 skill payload
│   ├── servo-gate-skill/             ← 受管 skill payload
│   └── servo-*                       ← 当前 agents 受管 skill payload
│
├── .claude/skills/                ← deploy target（installer 管理）
│   ├── harness-skill/             ← 受管 skill payload
│   ├── close-worktrack-skill/     ← 受管 skill payload
│   ├── gate-skill/                ← 受管 skill payload
│   └── *                          ← 所有目录均为受管
│
├── .servo/                           ← 运行时控制状态（非 installer payload）
│   ├── control-state.md           ← Harness 控制面配置
│   ├── goal-charter.md            ← Repo 目标章程
│   ├── repo/                      ← 仓库级快照与 backlog
│   ├── worktrack/                 ← 当前 worktrack artifacts
│   └── milestone/                 ← Milestone artifacts
├── .aw/                              ← 旧版运行时控制状态（仅显式升级路径处理）
│
├── .git/                          ← 用户自有（Git 仓库数据）
├── docs/                          ← 用户自有（文档真相层）
├── product/                       ← 用户自有（业务源码根）
├── toolchain/                     ← 用户自有（脚本与工具）
├── package.json                   ← 用户自有（npm 元数据）
└── CLAUDE.md                      ← 用户自有（入口文档）
```

### 本仓库的操作对应

| 如果你想... | 操作 | 影响范围 |
|-----------|------|---------|
| 重置所有受管 skill 到当前版本 | `servo-installer install --backend bundle` | 仅 `.agents/skills/` 和 `.claude/skills/` |
| 完全清理 installer 部署产物 | `servo-installer prune --all --backend bundle` | 仅上述两个 skills 目录 |
| 将旧 `aw-*` agents skill 目录收敛到 `servo-*` | `servo-installer update --backend agents --yes` 或 runtime 迁移时加 `--reinstall` | 仅 `.agents/skills/` 受管目录 |
| 重置 Harness 控制状态 | `rm -rf .servo/` 然后重新 `set-harness-goal-skill` | 仅 `.servo/`，不影响源码和文档 |
| 升级旧版 control state | 按 [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md) 先 dry-run，再显式确认 | `.aw/` 作为源；`.servo/` 作为目标 |
| 修改 skill 行为 | 编辑 `product/harness/skills/` 下的 canonical source | 下次 install 时生效 |
| 修改文档 | 编辑 `docs/` 下的文件 | 正常的 git 工作流 |

**关键记忆点：** `.agents/` 和 `.claude/` 是 installer 的写入目标（可随时重建）；`.servo/` 是 Harness 的当前运行时笔记；`.aw/` 是旧版运行时笔记，只能通过显式升级路径处理；其他一切都是你的代码和文档（installer 不会碰）。

## 非目标（Non-Goals）

以下内容不在 servo-installer 管理文件的所有权范围内：

| 内容 | 原因 | 相关工具 |
|------|------|---------|
| npm 全局安装路径 | npm 管理，非 servo-installer 管理 | `npm uninstall -g servo-installer` |
| `node_modules/` | npm/pnpm/yarn 管理 | 包管理器 |
| `.git/` | Git 管理 | `git` |
| shell profile / PATH | 系统配置 | 手动编辑 |
| `.servo_template/` | repo-local 模板，非 deploy target | 项目维护 |

## 不变量

- installer 只写入 deploy target（`.agents/skills/`、`.claude/skills/`）
- `.servo/` 与 installer payload 生命周期独立
- `.aw/` 与 installer payload 生命周期独立；普通 install/update/prune 不迁移或删除 `.aw/`
- 用户自有文件永远不会被 installer 修改或删除
- deploy target 不是真相源
- 单一真相源保持在 `product/harness/skills/` 和 `docs/`

## 停止线

问题进入 npm 全局安装管理、shell 环境配置、Git 仓库结构或 CI/CD pipeline 时，本文档只提供链接，不展开。
