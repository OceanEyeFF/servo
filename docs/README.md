---
title: "Docs 文档层入口"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Docs

`docs/` 承载文档真相与仓库操作说明。

完整 docs 阅读顺序、章节边界和路径维护规则见 [book.md](./book.md)。本页只做 `docs/` 入口导航，不重复定义 book spine。

## 核心定位

- 构建 `Codex-first` 的 AI coding harness 平台，作为 repo-side contract layer 分发到多个项目
- `Harness` 是一级文档域，负责 repo 演进控制面的 doctrine、artifact、catalog 与 workflow family
- 退役的 `memory-side`、`task-interface`、adjacent-system 文档域的执行边界由 `AGENTS.md`、`docs/harness/artifact/`、`docs/project-maintenance/governance/` 承接
- canonical skills 与 adapters 在 `product/`，部署/评测/治理脚本在 `toolchain/`

## 当前结构

- [book.md](./book.md)：`docs/` canonical book-style spine，说明完整阅读顺序、章节边界、分组关系与路径维护规则
- [project-maintenance/README.md](./project-maintenance/README.md)：项目维护、治理、部署与 backend usage
- [harness/README.md](./harness/README.md)：Harness 主线 doctrine、scope、artifact、catalog 与 workflow families

## 阅读顺序

Agent boot 以 [AGENTS.md](../AGENTS.md) 为权威；`docs/` 的全量书式阅读顺序以 [book.md](./book.md) 为入口。

## 文档治理规则

章节边界、新增/移动/删除文档的路径维护规则与 full reading order 见 [book.md](./book.md)。Agent 默认启动、frontmatter 与写回约束仍以 [AGENTS.md](../AGENTS.md) 为准。

## AI 默认路径

先读 [AGENTS.md](../AGENTS.md) 和 [../INDEX.md](../INDEX.md)；需要进入 `docs/` 时，再读 [book.md](./book.md) 与最近章节入口。
