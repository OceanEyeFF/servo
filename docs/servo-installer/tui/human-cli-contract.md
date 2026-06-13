---
title: "TUI / CLI Responsibility Split Contract"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-06-13
---
# TUI / CLI Responsibility Split Contract

> 目的：定义 servo-installer 的 TUI 和 CLI 的职责分离合同。TUI 是面向人工操作的推荐交互方式；CLI 是面向 AI、CI 和脚本的稳定接口。两者共享同一命令合同，TUI 不引入独立的 mutating 语义。

本页管理 TUI/CLI 的职责边界、默认行为差异、屏幕模型和色彩语义。命令合同见 [distribution-entrypoint-contract.md](../contracts/distribution-entrypoint-contract.md)。

## 角色定位

| 接口 | 角色 | 默认受众 |
|------|------|---------|
| **TUI** | 面向人工操作的推荐交互方式 | 人工操作（首次安装、日常维护、卸载） |
| **CLI** | 稳定的机器接口 | AI agent、CI pipeline、shell 脚本 |

**关键约束：** TUI 不拥有独立于 CLI 的 install/update/prune 语义。所有 mutating TUI 动作必须映射到明确的 CLI verb。

## 接口选择

| 场景 | 推荐接口 | 原因 |
|------|---------|------|
| 首次安装（人工操作） | TUI | 引导式流程、状态可见、减少失误 |
| 日常维护（人工操作） | TUI | diagnose/verify 结果可视化 |
| 卸载（人工操作） | TUI 或 CLI | 简单操作，两种均可 |
| AI agent 调用 | CLI | 稳定输出、非交互、可脚本化 |
| CI pipeline | CLI | 非交互环境、`--json` 机器输出 |
| Shell 脚本 | CLI | 退出码、stdout/stderr 标准处理 |

## 默认行为差异

| 行为 | TUI 默认 | CLI 默认 |
|------|---------|---------|
| backend 选择 | `bundle`（同时部署 agents + claude） | 必须显式指定 `--backend` |
| 输出格式 | 交互式固定布局 | 纯文本，`--json` 可选 |
| 确认步骤 | 交互式确认（可跳过） | `update` 需 `--yes` 才执行 |
| 错误呈现 | 固定状态区 + 颜色提示 | stderr 文本 |

**`bundle` 默认仅适用 TUI。** CLI 的 `--backend` 必须显式指定，不因 TUI 的默认行为而改变。

## TUI 屏幕模型

TUI 必须包含以下固定状态信息，在整个交互过程中持续可见：

| 信息 | 来源 | 说明 |
|------|------|------|
| **版本** | canonical VERSION 标记或 payload descriptor | 当前 servo-installer 版本 |
| **source** | package-local 或 checkout-local | payload 来源类型 |
| **target repo** | 当前工作目录或 `SERVO_HARNESS_TARGET_REPO_ROOT` | 安装目标仓库路径 |
| **当前 backend** | 用户选择或默认 `bundle` | 当前操作的 backend |
| **当前步骤** | 流程阶段 | `diagnose → preview → confirm → install → verify → done` |
| **验证结果** | `verify` 命令输出 | 最后验证的状态（通过/失败/未执行） |
| **日志位置** | target-local `.logs/servo-installer/` 或 `--log-dir` | 可上传的 sanitized run log 路径 |

屏幕模型是合同要求，具体布局由 MS-004 实现。各信息项须在固定区域渲染，不随交互滚动而移出视野。

## 色彩语义

色彩是**次要状态线索**，永远不是状态的唯一载体。每个色彩信号必须有同等的文字/符号表达。

| 色彩 | 语义 | 等价文字表达 |
|------|------|------------|
| 绿色 | 通过 / 完成 | `[OK]` 或 `✓` |
| 黄色 | 警告 / 需确认 | `[WARN]` 或 `!` |
| 红色 | 失败 / 阻断 | `[FAIL]` 或 `✗` |
| 白色/默认 | 中性信息 | 无前缀 |
| 青色/蓝色 | 当前步骤指示 | `>` 或 `→` |

**不变量：** 在无色终端或色盲模式下，所有状态信息必须通过文字/符号完整传达。

## TUI 引导流程

TUI 的 guided flow 对应 CLI 的命令序列，不引入新的 verb：

```
diagnose → preview paths → confirm → install/update → verify → summary
```

| 步骤 | 对应 CLI | TUI 行为 |
|------|---------|---------|
| diagnose | `servo-installer diagnose --backend bundle` | 展示当前状态摘要 |
| preview paths | `servo-installer check_paths_exist --backend bundle` | 展示将要写入的路径，标注冲突 |
| confirm | （交互式确认） | 要求 operator 确认，可查看详情 |
| install/update | `servo-installer install --backend bundle` 或 `update --yes` | 执行并展示进度 |
| verify | `servo-installer verify --backend bundle` | 展示验证结果 |
| summary | （最终摘要） | 汇总各 backend 状态，附下一步建议 |

每一步都可以取消。取消时 TUI 不执行任何 mutating 操作。

当 diagnose 发现 installer-managed 旧版 target 目录（例如 agents backend 的旧 `aw-*` skill 目录）时，TUI 必须展示与 CLI 相同的更新指引，并把 mutating 收敛动作映射到 `servo-installer update --backend <backend> --yes` 或 runtime 迁移路径中的 `migrate-runtime --from aw --to servo --yes --reinstall --backend <backend>`。TUI 不得引入独立的旧版清理操作。

TUI 默认必须写入 sanitized run log，并在退出时打印具体日志路径。默认位置为目标仓库 `.logs/servo-installer/`；使用默认目标仓库日志目录时，installer 必须确保目标 `.gitignore` 包含 `.logs/`，避免 TUI 运行日志变成未跟踪根目录噪声。若实现支持 `--log-dir`，显式路径优先。日志只能记录诊断所需的命令、环境摘要、目标状态、阶段输出和最终 verdict，不得写入完整环境变量 dump、token、credential 或 secret 值。

## 受众路径

| 受众 | 推荐路径 | 文档入口 |
|------|---------|---------|
| 新 operator | TUI guided flow | quickstart → TUI |
| 有经验的 operator | TUI 或 CLI | usage-help → 按需查阅 |
| AI agent | CLI `--json` | codex.md / claude.md |
| CI pipeline | CLI `--json` + 退出码 | testing runbooks |
| 脚本 | CLI | usage-help / runbooks |

## 与现有合同的关系

- **distribution-entrypoint-contract.md**：定义 CLI/TUI 不变量（TUI 不得拥有独立的 install/update 语义，所有 mutating TUI 动作必须映射到 CLI verb）。本页是该合同中 TUI/CLI 职责分离的细化。
- **deploy-mapping-spec.md**：canonical source → target 映射链路不受 TUI/CLI 分离影响。
- **payload-provenance-trust-boundary.md**：payload 来源与信任边界不受交互接口选择影响。

## 不变量

- TUI 不引入独立于 CLI 的 mutating 语义
- CLI `--json` 输出仅供机器消费，不混入交互渲染
- 非交互环境不得隐式启动 TUI
- `bundle` 默认只适用于 TUI；CLI 必须显式 `--backend`
- 色彩永远不是状态的唯一载体
- 固定状态区在任何正常流程中保持可见

## 停止线

问题进入 TUI 实现（布局、PTY、smoke）时，本文档只定义合同，不展开。实现见 MS-004。
