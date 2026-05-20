---
title: "Milestone Skills"
status: active
updated: 2026-05-17
owner: servo-kernel
last_verified: 2026-05-17
---
# Milestone Skills

`docs/harness/catalog/milestone/` 承接 Harness Milestone 管线的两个核心 skill 的 catalog 文档面。

## 目录

| 文档 | Skill | Scope | Function |
|------|-------|-------|----------|
| [init-milestone-skill.md](./init-milestone-skill.md) | Init Milestone Skill | RepoScope | Milestone 初始化/注册算子 |
| [milestone-status-skill.md](./milestone-status-skill.md) | Milestone Status Skill | RepoScope | Milestone 聚合观测/验收分析器 |

## 两个 Skill 的关系

```
init-milestone-skill                    milestone-status-skill
┌──────────────────────┐              ┌──────────────────────┐
│ 创建/注册 Milestone   │              │ 观测/分析 Milestone   │
│ 处理 latest-override  │   创建后     │ 计算 progress        │
│ 验证依赖合法性        │ ────────→   │ 执行 Milestone Gate  │
│ 管理激活规则          │              │ 判定 purpose_achieved │
│ 输出 planning brief  │              │ 决定 handback        │
└──────────────────────┘              └──────────────────────┘
         │                                      │
         └────────── 互补配对 ──────────────────┘
             同属 RepoScope，共享 Milestone artifact
```

- **init-milestone-skill**：写操作，创建和激活 milestone
- **milestone-status-skill**：读操作，观测和分析 milestone 状态
- 两者互补：init 产生 milestone artifact，status 消费并分析它

## Canonical 入口

canonical executable source：

- [../../../../product/harness/skills/init-milestone-skill/SKILL.md](../../../../product/harness/skills/init-milestone-skill/SKILL.md)
- [../../../../product/harness/skills/milestone-status-skill/SKILL.md](../../../../product/harness/skills/milestone-status-skill/SKILL.md)

上游权威文档：

- Milestone artifact 合同：[../../artifact/control/milestone.md](../../artifact/control/milestone.md)
- Milestone Backlog：[../../artifact/repo/milestone-backlog.md](../../artifact/repo/milestone-backlog.md)
- Control State 配置：[../../artifact/control/control-state.md](../../artifact/control/control-state.md)

## 调用时机

| 时机 | 绑定 Skill |
|------|-----------|
| RepoScope.Decide 建议 create/activate milestone | `init-milestone-skill` |
| RepoScope.Observe 有 active milestone | `milestone-status-skill` |
| Worktrack closeout 后检查 milestone 进度 | `milestone-status-skill` |
| Programmer 显式请求 milestone 状态 | `milestone-status-skill` |

## 边界

- 这里是 catalog inventory surface，不是 doctrine 或 artifact contract 正文
- 两个 skill 的完整职责、输入输出见各自的 catalog 页面
- Executable source 入口以 `product/harness/skills/` 为准
