---
title: "servo-installer Documentation"
status: active
updated: 2026-07-02
owner: servo-kernel
last_verified: 2026-07-02
---
# servo-installer Documentation

> servo-installer 的独立文档体系。与 `docs/harness/`（Harness 控制面）和 `docs/project-maintenance/`（项目维护治理）分层，专注于 operator 视角的安装、配置、卸载和维护。

## 文档分层原则

| 文档层 | 目录 | 受众 | 内容边界 |
|--------|------|------|---------|
| **servo-installer** | `docs/servo-installer/` | operator（人类、AI、CI） | 安装/卸载/维护 runbook、合同规范、参考说明 |
| **Harness** | `docs/harness/` | Harness 开发者、平台维护者 | 控制回路、artifact 合同、skill 目录 |
| **Project Maintenance** | `docs/project-maintenance/` | 项目维护者 | 治理规则、分支/PR 策略、release channel |

**关键边界：** servo-installer 文档描述"如何使用 servo-installer"，Harness 文档描述"Harness 如何运行"。operator 不应该需要读 Harness 文档才能完成安装。

## 章节结构

```
docs/servo-installer/
├── README.md                       ← 本页：章节索引与阅读路由
│
├── contracts/                      ← 合同与规范（normative）
│   ├── distribution-entrypoint-contract.md
│   ├── deploy-mapping-spec.md
│   ├── aw-runtime-upgrade-contract.md
│   ├── aw-residue-classification-contract.md
│   ├── payload-provenance-trust-boundary.md
│   └── version-marker-contract.md
│
├── runbooks/                       ← 操作步骤（procedural）
│   ├── deploy-runbook.md
│   ├── aw-runtime-upgrade-runbook.md
│   ├── skill-deployment-maintenance.md
│   ├── distribution-maintenance-checklist.md
│   └── uninstall-remove-runbook.md
│
├── reference/                      ← 参考与说明（explanatory）
│   ├── managed-files-ownership.md
│   ├── existing-code-adoption.md
│   ├── legacy-version-handling.md
│   └── tui-aw-runtime-migration-repro.md
│
└── tui/                            ← TUI 合同与实现（MS-003, MS-004）
    ├── README.md                   ← TUI 章节索引
    └── human-cli-contract.md       ← TUI/CLI 职责分离合同
```

## 章节说明

### contracts/ — 合同与规范

定义 servo-installer 的行为合同。这些是 normative 文档：如果 servo-installer 的行为与合同不一致，那就是 bug。

| 文档 | 管理内容 |
|------|---------|
| `distribution-entrypoint-contract.md` | CLI/TUI 包装层语义、命令面合同、backend 枚举、bundle aggregate 模式 |
| `deploy-mapping-spec.md` | canonical source → target 映射链路、最小字段、target 命名约定 |
| `distribution-entrypoint-contract.md` | `reconcile-servo` 与 `migrate-runtime` 的 CLI/TUI 命令面边界 |
| `aw-runtime-upgrade-contract.md` | legacy `.aw/` runtime state 显式升级到 `.servo/` 的安全边界 |
| `aw-residue-classification-contract.md` | `.aw` / `aw-*` / `aw.marker` 遗留的分类、allowlist 与 remediation 判定 |
| `payload-provenance-trust-boundary.md` | payload 来源种类、source/target root 分离、GitHub source 准入 |
| `version-marker-contract.md` | VERSION 标记文件的位置、格式、语义和 operator 解读规则 |

### runbooks/ — 操作步骤

operator 执行具体任务时使用。

| 文档 | 使用场景 |
|------|---------|
| `deploy-runbook.md` | 首次安装或完整重装 |
| `aw-runtime-upgrade-runbook.md` | legacy `.aw/` runtime state 显式升级到 `.servo/` |
| `skill-deployment-maintenance.md` | 已有安装，判断 drift/conflict，diagnose/verify 分流 |
| `distribution-maintenance-checklist.md` | 维护技能源码、适配器载荷、模板、合同或安装器行为时的源码侧同步清单 |
| `uninstall-remove-runbook.md` | 安全卸载，prune --all 边界，bundle 模式行为 |

### reference/ — 参考与说明

解释性文档，帮助 operator 理解 servo-installer 的工作方式。

| 文档 | 说明内容 |
|------|---------|
| `managed-files-ownership.md` | 文件所有权分类：installer payload / .servo/ 运行时 / deploy target / 用户自有 |
| `existing-code-adoption.md` | 既有代码库接入 Harness 时的 `.servo/repo/discovery-input.md` 生成边界 |
| `legacy-version-handling.md` | 0.5.x/0.6.x 来源的旧 `.aw/` runtime 和旧 `aw-*` target dirs 的处理说明；0.7.x 仍保留兼容说明，移除需独立 worktrack 与验证 |
| `tui-aw-runtime-migration-repro.md` | TUI first option 未触发 `.aw -> .servo` runtime migration 的 v0.5.7 复现记录、手动 Windows 步骤和旧文档残留扫描风险 |

### tui/ — TUI 合同与实现

TUI 是推荐的人类 operator 交互路径。合同定义职责分离、屏幕模型和引导流程；实现由 MS-004 负责。

| 文档 | 说明内容 |
|------|---------|
| `README.md` | TUI 章节索引与阅读路由 |
| `human-cli-contract.md` | TUI/CLI 职责分离：角色定位、默认行为差异、屏幕模型、色彩语义、引导流程 |

## 阅读路由

### 按角色

| 角色 | 推荐阅读顺序 |
|------|-------------|
| 新 operator（首次安装） | runbooks/deploy-runbook → reference/managed-files-ownership |
| operator（日常维护） | runbooks/skill-deployment-maintenance → runbooks/uninstall-remove-runbook |
| operator（legacy `.aw` runtime） | reference/legacy-version-handling → runbooks/aw-runtime-upgrade-runbook → contracts/aw-runtime-upgrade-contract |
| operator（理解行为） | contracts/distribution-entrypoint-contract → reference/managed-files-ownership |
| CI/脚本集成 | contracts/distribution-entrypoint-contract → contracts/deploy-mapping-spec |
| 人类 operator（TUI 交互） | tui/human-cli-contract → runbooks/deploy-runbook |
| Harness 开发者 | contracts/ (全部) → 回到 docs/harness/ |

### 按问题

| 问题 | 入口 |
|------|------|
| 安装 servo-installer 管理的 skills | runbooks/deploy-runbook.md |
| 更新到新版本 | runbooks/skill-deployment-maintenance.md |
| 更新已有 `.servo/` 管理体系模板 | runbooks/deploy-runbook.md#servo-模板调和reconcile-servo |
| 诊断安装状态 | runbooks/skill-deployment-maintenance.md |
| 完全卸载 | runbooks/uninstall-remove-runbook.md |
| 理解 installer 写入哪些文件 | reference/managed-files-ownership.md |
| 理解 CLI 命令不变量 | contracts/distribution-entrypoint-contract.md |
| 理解 canonical source 到 target 的映射 | contracts/deploy-mapping-spec.md |
| 升级 legacy `.aw/` runtime state | runbooks/aw-runtime-upgrade-runbook.md |
| 区分 `.servo` 模板调和与 legacy `.aw -> .servo` runtime migration | contracts/distribution-entrypoint-contract.md |
| 分类 `.aw` / `aw-*` / `aw.marker` 分发遗留 | contracts/aw-residue-classification-contract.md |
| 理解旧版本兼容处理窗口 | reference/legacy-version-handling.md |
| 复现 TUI `.aw -> .servo` migration 缺口 | reference/tui-aw-runtime-migration-repro.md |
| 理解 payload 来源与信任边界 | contracts/payload-provenance-trust-boundary.md |
| 理解版本标记的语义 | contracts/version-marker-contract.md |
| 既有项目接入 Harness | reference/existing-code-adoption.md |
| 理解 TUI 和 CLI 的职责边界 | tui/human-cli-contract.md |

## 诊断日志

- CLI 命令可加 `--log-dir <path>` 写入一份 sanitized JSON run log。
- TUI 默认把日志写到目标仓库 `.logs/servo-installer/`，并在退出时打印具体日志文件路径；使用默认目标仓库日志目录时，installer 必须确保目标 `.gitignore` 包含 `.logs/`。
- 日志包含平台、shell hint、Node/npm 版本、命令参数、backend/source selector、目标 `.aw/.servo/.agents/.claude` 状态、阶段输出摘要和最终 verdict。
- 日志不写入完整环境变量 dump；token、secret、password 等敏感参数会被 redacted。

## 与旧路径的关系

`docs/project-maintenance/deploy/` 原是 servo-installer 文档的唯一存放位置。本体系建立后：

- `docs/project-maintenance/deploy/README.md` 简化为指向 `docs/servo-installer/README.md` 的路由指针
- 所有 servo-installer 的 operator 文档迁移到 `docs/servo-installer/` 对应章节
- 与 servo-installer 无关的项目维护内容保留在 `docs/project-maintenance/`

## 不变量

- servo-installer 文档只描述 operator 如何使用，不描述 Harness 如何实现
- 合同文档是 normative——行为不一致时合同优先
- 新 servo-installer 功能必须先确定文档归属章节再实现
- `docs/book.md` 的阅读顺序始终反映当前文档结构

## 停止线

问题进入 Harness 控制回路、skill 实现、release channel 治理或 npm publish 流程时，本文档只提供链接，不展开。
