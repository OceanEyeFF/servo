---
title: "TUI Bundle Default & Guided Flow Contract"
status: active
updated: 2026-05-19
owner: aw-kernel
last_verified: 2026-05-19
---
# TUI Bundle Default & Guided Flow Contract

> 目的：定义 TUI 的 `bundle` 默认 backend 行为与 guided flow 各阶段的合同。bundle 默认仅适用于 TUI，CLI 必须显式指定 `--backend`。

本页管理 TUI 的 backend 默认规则和六阶段引导流程合同。TUI/CLI 职责分离见 [human-cli-contract.md](./human-cli-contract.md)。CLI 的 bundle aggregate 合同见 [distribution-entrypoint-contract.md](../contracts/distribution-entrypoint-contract.md)。

## Bundle Default

### 默认规则

| 接口 | 默认 backend | 可否覆盖 |
|------|-------------|---------|
| **TUI** | `bundle` | 是——operator 可在 TUI 内切换为 `agents` 或 `claude` |
| **CLI** | 无默认 | 必须显式指定 `--backend` |

### 设计理由

TUI 默认 `bundle` 的理由：
- 人类 operator 通常需要同时部署 agents 和 claude 两个 backend
- 默认 `bundle` 减少新 operator 的决策负担
- 引导流程在 diagnose 阶段展示双根状态，operator 可在确认前切换

CLI 不设默认的理由：
- AI agent 和脚本通常只操作单一 backend
- 显式指定避免误操作（如 CI 只想更新 agents 却误触 bundle）
- CLI 的 `--json` 输出不因默认值而产生歧义

### 默认边界

**bundle 默认是 TUI 的 UX 选择，不是 CLI 合同变更。** 以下行为不受 TUI bundle 默认影响：

- CLI 的 `--backend` 参数行为不变
- 脚本中 `aw-installer install` 不带 `--backend` 仍然报错
- CI pipeline 的行为不因 TUI 默认而改变
- `--json` 输出格式不变

## Guided Flow 合同

TUI guided flow 包含六个阶段，每个阶段映射到明确的 CLI verb 或交互行为：

```
┌──────────┐    ┌──────────────┐    ┌─────────┐    ┌──────────────┐    ┌────────┐    ┌─────────┐
│ diagnose │───→│ preview paths│───→│ confirm │───→│install/update│───→│ verify │───→│ summary │
└──────────┘    └──────────────┘    └─────────┘    └──────────────┘    └────────┘    └─────────┘
```

### 1. Diagnose

| 属性 | 值 |
|------|-----|
| CLI 映射 | `aw-installer diagnose --backend bundle --json` |
| TUI 行为 | 展示当前双 root 状态摘要：已安装 backend、版本、受管目录数 |
| 失败处理 | 展示 issue 列表；允许继续到下一步（diagnose 不是阻断 gate） |
| operator 可选操作 | 切换 backend、退出 |

**展示信息：** 每个 backend 的 installed version、managed directory count、last verify status。bundle 模式下同时展示 agents 和 claude 信息，各自带 `[backend=agents]` / `[backend=claude]` 前缀。

### 2. Preview Paths

| 属性 | 值 |
|------|-----|
| CLI 映射 | `aw-installer check_paths_exist --backend bundle` |
| TUI 行为 | 列出将要写入/更新的所有路径，标注冲突 |
| 失败处理 | 如有冲突，展示冲突列表并要求 operator 解决后才可继续 |
| operator 可选操作 | 查看冲突详情、取消 |

**冲突展示：** 按 backend 分组展示冲突路径。每项冲突标注类型（already exists / permission denied / outside target root）。

### 3. Confirm

| 属性 | 值 |
|------|-----|
| CLI 映射 | （无对应 CLI verb——纯交互确认） |
| TUI 行为 | 展示操作摘要，要求 operator 明确确认 |
| 确认内容 | backend 选择、将写入的目录数、将覆盖/新增的文件数 |
| operator 可选操作 | 确认执行、返回修改 backend 选择、取消 |

**确认是显式 gate。** 在 operator 确认之前，任何 mutating 操作都不得执行。确认后进入 install/update 阶段不可撤销。

### 4. Install / Update

| 属性 | 值 |
|------|-----|
| CLI 映射 | `aw-installer install --backend bundle` 或 `aw-installer update --backend bundle --yes` |
| TUI 行为 | 按 ASCII 顺序执行（agents → claude），展示实时进度 |
| 失败处理 | 展示 partial 状态，附 single-backend recovery 建议 |
| operator 可选操作 | 查看失败详情、重试失败 backend |

**进度展示：** 每个 backend 的当前阶段（prune → check → install → verify），失败时立即展示错误信息。bundle 的 aggregate partial 信息在固定状态区持续可见。

### 5. Verify

| 属性 | 值 |
|------|-----|
| CLI 映射 | `aw-installer verify --backend bundle` |
| TUI 行为 | 对双 root 执行严格复验，展示通过/失败状态 |
| 失败处理 | 按 backend 分组展示 issue，附 recovery 建议 |
| operator 可选操作 | 查看 issue 详情、重试 install、退出 |

**verify 是严格 gate。** 任何 backend 的 verify 失败都必须在 summary 中标记为 incomplete，并阻止"全部完成"的结论。

### 6. Summary

| 属性 | 值 |
|------|-----|
| CLI 映射 | （无对应 CLI verb——TUI 汇总视图） |
| TUI 行为 | 汇总所有 backend 最终状态，附下一步建议 |
| 成功时 | 展示版本、backend 数、受管目录数、"install complete" |
| 失败/partial 时 | 展示失败 backend、失败阶段、recovery 命令 |
| operator 可选操作 | 查看详情、重试、退出 |

## 取消与恢复

### 取消

operator 可在 confirm 之前的任何阶段取消流程。取消不执行任何 mutating 操作。

在 install/update 阶段**不可取消**（与 CLI `update --yes` 的事务语义一致：已写入内容保留，不自动回滚）。

### 恢复

partial 失败后的恢复路径：

| 失败场景 | 恢复方式 |
|---------|---------|
| agents 成功，claude 失败 | `aw-installer install --backend claude` 单独重试 |
| 两个 backend 都失败 | 解决根因后重新运行 guided flow |
| verify 失败 | `aw-installer install --backend <name>` 重新部署后 verify |

所有恢复操作可以使用 CLI 或重新进入 TUI guided flow。

## 与其他合同的关系

- **human-cli-contract.md**：定义 TUI/CLI 职责分离。本页是 TUI 侧的 bundle 默认和流程细化。
- **distribution-entrypoint-contract.md**：bundle aggregate 的事务模型（pre-check union all-or-nothing、write each-independent、no cross-backend rollback）。TUI 流程遵循同一事务合同。
- **deploy-runbook.md**：operator 手动执行的三步流程。TUI guided flow 是同一流程的交互式表达。

## 不变量

- TUI 默认 `bundle`，CLI 无默认
- bundle 默认不改变 CLI 的任何行为
- guided flow 的每个 mutating 阶段映射到明确的 CLI verb
- confirm 是显式 gate——确认前零写入
- verify 失败阻止"全部完成"结论
- partial 恢复使用单 backend CLI 命令

## 停止线

TUI guided flow 的具体布局、PTY 渲染和 keyboard 交互由 MS-004 实现。
