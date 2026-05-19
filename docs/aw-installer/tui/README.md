---
title: "aw-installer TUI Documentation"
status: active
updated: 2026-05-19
owner: aw-kernel
last_verified: 2026-05-19
---
# aw-installer TUI Documentation

> aw-installer 的 TUI（Terminal User Interface）合同与实现文档。TUI 是推荐的人类 operator 交互路径；CLI 是稳定的 AI、CI 和脚本接口。

## 章节

| 文档 | 内容 | 状态 |
|------|------|------|
| [human-cli-contract.md](./human-cli-contract.md) | TUI/CLI 职责分离合同：角色定位、默认行为、固定状态区 | active |
| *(预留)* | TUI bundle 默认与 guided flow 合同 | MS-003 WT-2 |
| *(预留)* | TUI 布局/色彩实现 | MS-004 |
| *(预留)* | TUI PTY 与 package smoke | MS-004 |

## 与 CLI 的关系

TUI 和 CLI 共享同一命令面合同（见 [distribution-entrypoint-contract.md](../contracts/distribution-entrypoint-contract.md)）。TUI 不引入新的 verb 或 mutating 语义——它是同一合同的交互层表达。

## 阅读路由

| 角色 | 入口 |
|------|------|
| 理解 TUI 的设计意图 | [human-cli-contract.md](./human-cli-contract.md) |
| 理解 TUI 和 CLI 的边界 | [human-cli-contract.md](./human-cli-contract.md) |
| 安装/维护 aw-installer | [../runbooks/deploy-runbook.md](../runbooks/deploy-runbook.md) |
