---
title: ".nav Compatibility Navigation"
status: active
updated: 2026-05-06
owner: servo-kernel
last_verified: 2026-05-06
---
# .nav/

> 本目录只提供当前有效的快捷导航入口，不承接主线结构定义。

根层级与 agent-facing 规则见：

- [root-directory-layering.md](../docs/project-maintenance/foundations/root-directory-layering.md)
- [AGENTS.md](../AGENTS.md)

## 当前入口

| 链接 | 目标 | 用途 |
|------|------|------|
| `@docs` | `docs/` | 文档 truth boundary 入口 |
| `@skills` | `product/harness/skills/` | Harness canonical skills 入口 |

## 当前主线怎么进

| 任务 | 正式入口 |
|------|------|
| 文档主线 | [docs/README.md](../docs/README.md) |
| 项目维护、deploy、testing、usage help | [docs/project-maintenance/README.md](../docs/project-maintenance/README.md) |
| Harness 跨模块指导思想 | [Harness指导思想.md](../docs/harness/foundations/Harness指导思想.md) |
| Canonical Skill contracts | [product/harness/skills/README.md](../product/harness/skills/README.md) |
| Codex / Claude backend 使用差异 | [usage-help/README.md](../docs/project-maintenance/usage-help/README.md) |
| `servo-installer` deploy 主流程 | [deploy/README.md](../docs/project-maintenance/deploy/README.md) |
| npx / package smoke 与部署后行为观察 | [testing/README.md](../docs/project-maintenance/testing/README.md) |

## 使用方式

```bash
# 快速进入 docs 模块
cd .nav/@docs

# 快速查看所有 skill
ls .nav/@skills/
```

## 使用边界

- 只在本地快速跳转时使用 `.nav/`
- 正式文档引用应指向真实路径，不使用 `.nav/` 路径
- 不要把 `.nav/` 当成真实目录结构定义
- 不要在 `.nav/` 下新增 `@docs` / `@skills` 之外的兼容入口

## 当前状态

- `.nav/` 只保留 `@skills` 与 `@docs`
- `.nav/` 只服务快速跳转，不反向定义仓库结构
