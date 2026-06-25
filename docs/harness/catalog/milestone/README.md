---
title: "Milestone Skills"
status: active
updated: 2026-06-23
owner: servo-kernel
last_verified: 2026-06-23
---
# Milestone Skills

`docs/harness/catalog/milestone/` 承接 Harness Milestone 管线的核心 skill 的 catalog 文档面。

## 目录

| 文档 | Skill | Scope | Function |
|------|-------|-------|----------|
| [milestone-init-skill.md](./milestone-init-skill.md) | Init Milestone Skill | RepoScope | Milestone 初始化/注册算子 |
| [milestone-status-skill.md](./milestone-status-skill.md) | Milestone Status Skill | RepoScope | Milestone 聚合观测/验收分析器（Sensor） |
| — | milestone-gate | RepoScope | Milestone Gate 两层集成验收（Orchestrator） |
| — | milestone-blackbox-check | RepoScope | Gate Layer 1 — blackbox 轴检查 |
| — | milestone-whitebox-check | RepoScope | Gate Layer 1 — whitebox 轴检查 |
| — | milestone-anticheat-check | RepoScope | Gate Layer 1 — anticheat 轴检查 |
| — | milestone-composite-check | RepoScope | Gate Layer 1 — composite 轴检查 |

## Skill 关系

```
milestone-init-skill                    milestone-status-skill (Sensor)
┌──────────────────────┐              ┌──────────────────────┐
│ 创建/注册 Milestone   │              │ 观测进度 + handback   │
│ 处理 latest-override  │   创建后     │ worktrack_list_finished?│
│ 验证依赖合法性        │ ────────→   │   └─ yes → invoke    │
│ 管理激活规则          │              │      milestone-gate  │
│ 输出 planning brief  │              │ purpose_achieved?    │
└──────────────────────┘              └──────────┬───────────┘
                                                 │
                                    ┌────────────┘
                                    ▼
                          milestone-gate (Orchestrator)
                          ┌──────────────────────────┐
                          │ Layer 1: 4 轴 SubAgent    │
                          │  ├─ blackbox-check       │
                          │  ├─ whitebox-check       │
                          │  ├─ anticheat-check      │
                          │  └─ composite-check      │
                          │ Layer 2: Aggregator      │
                          │  weight→contradiction    │
                          │  →composite_lane         │
                          │  →degenerate             │
                          │  →milestone_gate_verdict │
                          └──────────────────────────┘
```

- **milestone-init-skill**：写操作，创建和激活 milestone
- **milestone-status-skill**：读操作，观测和分析 milestone 状态（Sensor）
- **milestone-gate**：Gate orchestrator，仅在 worktrack_list_finished 时触发
- **4 轴检查**：Layer 1 隔离 SubAgent，并行执行、轴间不可见

## Canonical 入口

canonical executable source：

- [../../../../product/harness/skills/milestone-init-skill/SKILL.md](../../../../product/harness/skills/milestone-init-skill/SKILL.md)
- [../../../../product/harness/skills/milestone-status-skill/SKILL.md](../../../../product/harness/skills/milestone-status-skill/SKILL.md)
- [../../../../product/harness/skills/milestone-gate/SKILL.md](../../../../product/harness/skills/milestone-gate/SKILL.md)
- [../../../../product/harness/skills/milestone-blackbox-check/SKILL.md](../../../../product/harness/skills/milestone-blackbox-check/SKILL.md)
- [../../../../product/harness/skills/milestone-whitebox-check/SKILL.md](../../../../product/harness/skills/milestone-whitebox-check/SKILL.md)
- [../../../../product/harness/skills/milestone-anticheat-check/SKILL.md](../../../../product/harness/skills/milestone-anticheat-check/SKILL.md)
- [../../../../product/harness/skills/milestone-composite-check/SKILL.md](../../../../product/harness/skills/milestone-composite-check/SKILL.md)

上游权威文档：

- Milestone artifact 合同：[../../artifact/control/milestone.md](../../artifact/control/milestone.md)
- Milestone Gate 聚合合同：[../../artifact/control/milestone-gate-aggregation.md](../../artifact/control/milestone-gate-aggregation.md)
- Milestone Backlog：[../../artifact/repo/milestone-backlog.md](../../artifact/repo/milestone-backlog.md)
- Control State 配置：[../../artifact/control/control-state.md](../../artifact/control/control-state.md)

## 调用时机

| 时机 | 绑定 Skill |
|------|-----------|
| RepoScope.Decide 建议 create/activate milestone | `milestone-init-skill` |
| RepoScope.Observe 有 active milestone | `milestone-status-skill` |
| worktrack_list_finished → Gate 触发 | `milestone-gate`（SubAgent delegated 推荐） |
| Worktrack closeout 后检查 milestone 进度 | `milestone-status-skill` |

## 边界

- 这里是 catalog inventory surface，不是 doctrine 或 artifact contract 正文
- 两个 skill 的完整职责、输入输出见各自的 catalog 页面
- Executable source 入口以 `product/harness/skills/` 为准
