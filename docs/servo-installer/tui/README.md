---
title: "servo-installer TUI Documentation"
status: active
updated: 2026-05-19
owner: servo-kernel
last_verified: 2026-06-13
---
# servo-installer TUI Documentation

> servo-installer 的 TUI（Terminal User Interface）合同与实现文档。TUI 是面向 operator 的推荐交互方式；CLI 是面向 AI、CI 和脚本的稳定接口。

## 章节

| 文档 | 内容 | 状态 |
|------|------|------|
| [human-cli-contract.md](./human-cli-contract.md) | TUI/CLI 职责分离合同：角色定位、默认行为、固定状态区 | active |
| [bundle-default-contract.md](./bundle-default-contract.md) | TUI bundle 默认与 guided flow 六阶段合同 | active |
| *(预留)* | TUI 布局/色彩实现 | MS-004 |
| *(预留)* | TUI PTY 与 package smoke | MS-004 |

## 与 CLI 的关系

TUI 和 CLI 共享同一套命令合同（见 [distribution-entrypoint-contract.md](../contracts/distribution-entrypoint-contract.md)）。TUI 不引入新的操作动词或变更语义——它是同一合同在交互层的表达。

## 阅读路由

| 角色 | 入口 |
|------|------|
| 理解 TUI 的设计意图 | [human-cli-contract.md](./human-cli-contract.md) |
| 理解 TUI 和 CLI 的边界 | [human-cli-contract.md](./human-cli-contract.md) |
| 安装/维护 servo-installer | [../runbooks/deploy-runbook.md](../runbooks/deploy-runbook.md) |
