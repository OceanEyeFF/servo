---
title: "aw-installer Documentation"
status: active
updated: 2026-05-19
owner: aw-kernel
last_verified: 2026-05-19
---
# aw-installer Documentation

> aw-installer 的独立文档体系。与 `docs/harness/`（Harness 控制面）和 `docs/project-maintenance/`（项目维护治理）分层，专注于 operator 视角的安装、配置、卸载和维护。

## 文档分层原则

| 文档层 | 目录 | 受众 | 内容边界 |
|--------|------|------|---------|
| **aw-installer** | `docs/aw-installer/` | operator（人类、AI、CI） | 安装/卸载/维护 runbook、合同规范、参考说明 |
| **Harness** | `docs/harness/` | Harness 开发者、平台维护者 | 控制回路、artifact 合同、skill 目录 |
| **Project Maintenance** | `docs/project-maintenance/` | 项目维护者 | 治理规则、分支/PR 策略、release channel |

**关键边界：** aw-installer 文档描述"如何使用 aw-installer"，Harness 文档描述"Harness 如何运行"。operator 不应该需要读 Harness 文档才能完成安装。

## 章节结构

```
docs/aw-installer/
├── README.md                       ← 本页：章节索引与阅读路由
│
├── contracts/                      ← 合同与规范（normative）
│   ├── distribution-entrypoint-contract.md
│   ├── deploy-mapping-spec.md
│   ├── payload-provenance-trust-boundary.md
│   └── version-marker-contract.md
│
├── runbooks/                       ← 操作步骤（procedural）
│   ├── deploy-runbook.md
│   ├── skill-deployment-maintenance.md
│   └── uninstall-remove-runbook.md
│
├── reference/                      ← 参考与说明（explanatory）
│   ├── managed-files-ownership.md
│   └── existing-code-adoption.md
│
└── tui/                            ← 预留：TUI 合同与实现（MS-003, MS-004）
    └── (future)
```

## 章节说明

### contracts/ — 合同与规范

定义 aw-installer 的行为合同。这些是 normative 文档：如果 aw-installer 的行为与合同不一致，那就是 bug。

| 文档 | 管理内容 |
|------|---------|
| `distribution-entrypoint-contract.md` | CLI/TUI 包装层语义、命令面合同、backend 枚举、bundle aggregate 模式 |
| `deploy-mapping-spec.md` | canonical source → target 映射链路、最小字段、target 命名约定 |
| `payload-provenance-trust-boundary.md` | payload 来源种类、source/target root 分离、GitHub source 准入 |
| `version-marker-contract.md` | VERSION 标记文件的位置、格式、语义和 operator 解读规则 |

### runbooks/ — 操作步骤

operator 执行具体任务时使用。

| 文档 | 使用场景 |
|------|---------|
| `deploy-runbook.md` | 首次安装或完整重装 |
| `skill-deployment-maintenance.md` | 已有安装，判断 drift/conflict，diagnose/verify 分流 |
| `uninstall-remove-runbook.md` | 安全卸载，prune --all 边界，bundle 模式行为 |

### reference/ — 参考与说明

解释性文档，帮助 operator 理解 aw-installer 的工作方式。

| 文档 | 说明内容 |
|------|---------|
| `managed-files-ownership.md` | 文件所有权分类：installer payload / .aw/ 运行时 / deploy target / 用户自有 |
| `existing-code-adoption.md` | 既有代码库接入 Harness 时的 `.aw/repo/discovery-input.md` 生成边界 |

### tui/ — 预留

为 MS-20260519-003（Human-First TUI Contract）和 MS-20260519-004（TUI Full-Flow Implementation）预留的文档空间。具体章节结构由对应 milestone 确定。

## 阅读路由

### 按角色

| 角色 | 推荐阅读顺序 |
|------|-------------|
| 新 operator（首次安装） | runbooks/deploy-runbook → reference/managed-files-ownership |
| operator（日常维护） | runbooks/skill-deployment-maintenance → runbooks/uninstall-remove-runbook |
| operator（理解行为） | contracts/distribution-entrypoint-contract → reference/managed-files-ownership |
| CI/脚本集成 | contracts/distribution-entrypoint-contract → contracts/deploy-mapping-spec |
| Harness 开发者 | contracts/ (全部) → 回到 docs/harness/ |

### 按问题

| 问题 | 入口 |
|------|------|
| 安装 aw-installer 管理的 skills | runbooks/deploy-runbook.md |
| 更新到新版本 | runbooks/skill-deployment-maintenance.md |
| 诊断安装状态 | runbooks/skill-deployment-maintenance.md |
| 完全卸载 | runbooks/uninstall-remove-runbook.md |
| 理解 installer 写入哪些文件 | reference/managed-files-ownership.md |
| 理解 CLI 命令不变量 | contracts/distribution-entrypoint-contract.md |
| 理解 canonical source 到 target 的映射 | contracts/deploy-mapping-spec.md |
| 理解 payload 来源与信任边界 | contracts/payload-provenance-trust-boundary.md |
| 理解版本标记的语义 | contracts/version-marker-contract.md |
| 既有项目接入 Harness | reference/existing-code-adoption.md |

## 与旧路径的关系

`docs/project-maintenance/deploy/` 原是 aw-installer 文档的唯一存放位置。本体系建立后：

- `docs/project-maintenance/deploy/README.md` 简化为指向 `docs/aw-installer/README.md` 的路由指针
- 所有 aw-installer 的 operator 文档迁移到 `docs/aw-installer/` 对应章节
- 与 aw-installer 无关的项目维护内容保留在 `docs/project-maintenance/`

## 不变量

- aw-installer 文档只描述 operator 如何使用，不描述 Harness 如何实现
- 合同文档是 normative——行为不一致时合同优先
- 新 aw-installer 功能必须先确定文档归属章节再实现
- `docs/book.md` 的阅读顺序始终反映当前文档结构

## 停止线

问题进入 Harness 控制回路、skill 实现、release channel 治理或 npm publish 流程时，本文档只提供链接，不展开。
