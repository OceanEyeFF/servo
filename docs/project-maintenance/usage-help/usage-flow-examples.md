---
title: "使用流程示例"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# 使用流程示例

本页列出已经观察到的项目，帮助 operator 理解 Servo 在真实仓库中的使用方式。示例只作为参考材料，不替代本仓库的 Harness artifact contracts、review / verify gates 或 release approval flow。

阅读本页时按三层权重理解：

- 当前 Servo 仓库是 primary public dogfooding reference，因为它展示了 Servo 如何管理自身的长期演进。
- Maintainer-local showcase candidate 可能更能代表 Harness 能力，但在导出、脱敏或单独整理成面向外部读者的材料前，不应作为公开证明。
- Public lightweight example 的价值在于读者可以直接检查，但它们未必覆盖完整 Harness 能力面。

## 主要公开 Dogfooding 参考

| 项目 | 展示内容 | 说明 |
|---|---|---|
| 本仓库（`vibecoding_autoworkflow` / Servo） | Servo 对自身的反复迭代管理：Harness artifact contracts、canonical skills、installer packaging、release governance、Milestone / Worktrack 执行、Append Request routing、backlog / history hygiene，以及 pre-release documentation gates。 | 这是长期、可追溯 Servo operation 的主要公开展示。它是 dogfooding reference，不是独立第三方产品案例。 |

本仓库是目前最强的公开证据，因为 Servo control layer、product source、governance docs、installer flow 和 milestone history 都在这里共同演进。它展示的不是一次性初始化，而是跨多轮迭代的 worktrack execution、gate evidence、release preparation 和 runtime-state writeback。

## 公开轻量示例

| 项目 | 展示内容 | 说明 |
|---|---|---|
| [OceanEyeFF/reqflow](https://github.com/OceanEyeFF/reqflow) | 一个轻量需求工单协作应用上的 Servo-managed product development。 | 公开仓库，包含 `.servo/`、项目文档、Next.js / TypeScript 源码、Prisma data layer 和 test / build scripts。它适合作为可检查的 onboarding example，而不是当前 Harness 能力的最强证明。 |

`reqflow` 的价值在于公开且简单。它的代码增量相对较小，因此不应作为 Servo 能够管理更大规模、多阶段项目演进的主要证据。

## Maintainer-Local 展示候选

| 项目 | 展示内容 | 当前可见性 |
|---|---|---|
| `/mnt/f/小游戏/MiniGame1` | 更强的本地 Harness-managed product evolution 示例：Godot 活跃实现、冻结的 Node TUI reference、`.aw` 到 `.servo` 的迁移痕迹、项目文档、升级历史、可运行游戏产物，以及多层 design / evidence 文档。 | Maintainer-local path。在公开仓库、脱敏案例或导出文档包可用前，只作为内部评估证据。 |

`MiniGame1` 比 `reqflow` 更能展示能力，因为它有更大的产品面和更多生命周期压力：引擎迁移决策、冻结历史实现、活跃实现、artifact / evidence docs，以及 runtime-state evolution。由于它目前只是本地仓库路径，公开 operator 文档只应把它描述为 showcase candidate，而不是要求外部读者依赖它。

## 如何使用这些示例

应把示例当作具体项目历史，而不是可直接搬运的 policy。把其他仓库的模式应用到目标仓库时：

1. 先从 [quickstart.md](./quickstart.md) 或 [recommended-usage.md](./recommended-usage.md) 进入当前支持的 operator path。
2. 复制任何结构前，先把示例中的 `.servo/` state shape 与当前 [Harness artifact contracts](../../harness/artifact/README.md) 对照。对仍包含 `.aw/` 的 legacy 示例，除非目标仓库明确记录当前 `.aw` compatibility boundary，否则应把它视为迁移历史。
3. 在目标仓库重新运行 local install、governance 和 worktrack verification，不继承示例仓库中的 evidence。
4. 除非已经单独验证为可复用 Harness 行为，否则不要把项目特定的产品决策、UI 选择、技术栈选择和数据库布局写进 Servo-level 文档。

## 升格规则

只有在 dedicated Worktrack 验证某种行为可跨仓库复用之后，示例才可以升格成更强的 documented pattern。在此之前，示例只保留在 `usage-help` 中，作为面向 operator 的参考材料。
