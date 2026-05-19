---
title: "Uninstall / Remove Runbook"
status: active
updated: 2026-05-19
owner: aw-kernel
last_verified: 2026-05-19
---
# Uninstall / Remove Runbook

> 目的：为 operator 提供安全卸载 aw-installer 部署产物的操作指南，明确 `prune --all` 的受管边界、删除范围、保留内容和 bundle 模式行为。

本页管理卸载与移除的安全边界。`prune --all` 的合同语义见 [distribution-entrypoint-contract.md](./distribution-entrypoint-contract.md)。payload 来源与写入边界见 [payload-provenance-trust-boundary.md](./payload-provenance-trust-boundary.md)。

## 快速决策

| 你的情况 | 入口 |
|---------|------|
| 想完全移除一个 backend 的安装产物 | [单 backend 卸载](#单-backend-卸载) |
| 想完全移除所有 backend 的安装产物 | [bundle 模式卸载](#bundle-模式卸载) |
| 不确定安装了什么 | 先运行 `aw-installer diagnose` 查看当前状态 |
| 只想验证但不执行删除 | [安全预览（dry-run）](#安全预览dry-run) |
| 想重装而不是卸载 | 见 [deploy-runbook.md](./deploy-runbook.md) |

## 核心概念

### `prune --all` 做什么

`prune --all` 删除当前 backend 可识别的**所有受管目录**。受管目录是由 aw-installer 在此前 `install` 操作中创建的目录，通过 `aw.marker` 文件识别。

### `prune --all` 不做什么

- **不删除** target repo 的工作目录（如 `src/`、`docs/` 等）
- **不删除** `.aw/` 运行时控制状态目录
- **不删除** `.git/` 仓库数据
- **不删除** `package.json`、`node_modules/` 等 npm 相关文件
- **不删除** 用户在 target repo 中手动创建的任何非受管文件
- **不卸载** `aw-installer` npm package 本身（用 `npm uninstall -g aw-installer` 处理）

## 单 backend 卸载

### agents backend

```bash
aw-installer prune --all --backend agents
```

**删除内容：**
- `<targetRepoRoot>/.agents/skills/` 下所有 `aw-` 前缀的受管目录
- 每个受管目录内的 `aw.marker` 文件

**保留内容：**
- `<targetRepoRoot>/.agents/` 目录本身（如果为空则保留空目录）
- `<targetRepoRoot>/.aw/` 运行时状态
- 用户手动添加到 `.agents/` 的非受管文件

### claude backend

```bash
aw-installer prune --all --backend claude
```

**删除内容：**
- `<targetRepoRoot>/.claude/skills/` 下所有受管 skill 目录
- 每个受管目录内的 marker 文件

**保留内容：**
- `<targetRepoRoot>/.claude/` 目录本身
- `<targetRepoRoot>/.aw/` 运行时状态
- 用户手动添加到 `.claude/` 的非受管文件

## bundle 模式卸载

```bash
aw-installer prune --all --backend bundle
```

bundle 模式同时作用于 agents 和 claude 两个 backend。

**执行顺序：** 按 ASCII 顺序先 agents 后 claude。pre-check 阶段采用 union all-or-nothing：任一根的预检查失败，任何根都不进入删除阶段。删除阶段按序执行，前者失败立即停止，后者不开始。

**失败恢复：** 如果 agents 删除成功但 claude 删除失败（partial 状态），已删除的内容保留删除状态。使用以下命令单独重试失败的 backend：

```bash
# 假设 claude 失败，单独重试
aw-installer prune --all --backend claude
```

**stderr 输出格式：**
```
[backend=agents] prune complete: 3 directories removed
[backend=claude] prune failed: permission denied at <path>
aggregate prune partial: agents=complete, claude=failed
```

## 安全预览（dry-run）

`prune --all` 没有独立的 dry-run 模式。使用 `diagnose` 代替预览：

```bash
# 查看 agents backend 当前受管目录
aw-installer diagnose --backend agents --json

# 查看 bundle 双 backend 当前受管目录
aw-installer diagnose --backend bundle --json
```

`diagnose --json` 输出中的 `managed_directories` 字段列出将被 `prune --all` 删除的所有目录。

## 完整卸载检查清单

彻底移除 aw-installer 的所有痕迹：

| 步骤 | 命令 | 说明 |
|------|------|------|
| 1. 查看当前状态 | `aw-installer diagnose --backend bundle` | 了解受管目录范围 |
| 2. 删除 agents 产物 | `aw-installer prune --all --backend agents` | 清理 agents backend |
| 3. 删除 claude 产物 | `aw-installer prune --all --backend claude` | 清理 claude backend |
| 4. 验证清理 | `aw-installer verify --backend bundle` | 应报告 no managed install |
| 5. 移除 .aw/（可选） | `rm -rf .aw/` | 删除运行时控制状态 |
| 6. 卸载 npm package | `npm uninstall -g aw-installer` | 移除 aw-installer 命令 |

> `bundle` 模式下步骤 2 和 3 可合并为 `aw-installer prune --all --backend bundle`。分步执行可在 partial 失败时独立重试。

## 恢复场景

### 误删后重装

如果误执行了 `prune --all`：
1. 不要 panic——`.aw/` 运行时状态未被删除
2. 运行 `aw-installer install --backend <backend>` 重新部署
3. 运行 `aw-installer verify --backend <backend>` 验证完整性

### prune 失败后的恢复

如果 `prune --all` 部分失败：
1. 查看 stderr 确认失败 backend 和原因
2. 解决权限或文件锁定问题
3. 对失败的 backend 单独重试 `aw-installer prune --all --backend <failed-backend>`
4. 运行 `aw-installer diagnose` 确认清理完成

## 不变量

- `prune --all` 只删除通过 `aw.marker` 识别的受管目录
- 非受管文件和用户数据永远不会被 prune 触及
- `.aw/` 运行时状态不受 prune 影响
- bundle 模式的删除顺序固定为 agents → claude

## 停止线

问题进入 npm 包卸载、全局 node 环境清理或 deploy target 目录删除时，本文档只提供链接，不展开。
