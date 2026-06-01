---
title: Harness Skill Catalog
status: active
updated: 2026-05-16
owner: servo-kernel
last_verified: 2026-05-14
---

# Harness Skill Catalog

`docs/harness/catalog/` 承接 `Codex` 语境下的 Harness skill inventory。

直接回答 Harness 在 Codex 中需要哪些 skills、它们服务于哪个控制层级、哪些已有 canonical executable source，以及哪些条目当前只保留 catalog 文档面。

Catalog 条目只允许承接：

- skill 名称、Scope / Function、职责摘要、输入输出摘要和当前状态
- 上游 doctrine、runtime protocol、artifact contract、workflow policy 的反向链接或极短摘要
- canonical executable source 链接，权威入口为 [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md)

Catalog 不承接 doctrine 正文、runtime protocol、artifact contract、workflow family policy、方案分析、执行源或部署规则。

入口：

- [supervisor.md](./supervisor.md)：顶层 supervisor 入口
- [repo.md](./repo.md)：RepoScope 能力入口
- [milestone/README.md](./milestone/README.md)：Milestone Skills，Milestone 初始化与状态分析
- [worktrack.md](./worktrack.md)：WorktrackScope 能力入口
- [skill-impact-matrix.md](./skill-impact-matrix.md)：Skill Impact Matrix，历史影响分析与同步追踪记录；不是 skill inventory 正文

边界：

- 这里是 skill inventory，不是 doctrine 主文档
- 这组规则依托上游 [../foundations/Harness指导思想.md](../foundations/Harness指导思想.md) 和 [../foundations/Harness运行协议.md](../foundations/Harness运行协议.md)
- 可执行源入口仍以 [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md) 为准

## 非 Catalog 材料边界

| 当前材料 | 当前保留原因 | 当前权威 owner |
|----------|--------------|----------------|
| `supervisor.md`、`repo.md`、`worktrack.md` 中的运行策略摘要 | 用于解释 skill 选择和 handoff 字段，不作为独立规则正文 | doctrine / runtime protocol 归 [../foundations/README.md](../foundations/README.md)；正式对象字段归 [../artifact/README.md](../artifact/README.md)；workflow policy 归 [../workflow-families/README.md](../workflow-families/README.md) |
| `milestone/` 中的 milestone 行为摘要 | 用于固定两个 milestone skills 的 inventory surface | Milestone artifact 合同归 [../artifact/README.md](../artifact/README.md)；运行协议归 [../foundations/README.md](../foundations/README.md)；executable source 归 [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md) |
| `skill-impact-matrix.md` | 历史合同变更对 skill 的影响分析与同步追踪记录 | 当前文件本身是历史分析记录；skill inventory 正文仍以本 catalog 的 skill 条目为准 |

新增 catalog 页面时，若正文超过 inventory surface，需要先确认目标 owner；不能把分析、policy 或协议正文长期沉淀在 `catalog/`。

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
| [supervisor.md](./supervisor.md) | [harness-skill](../../../product/harness/skills/harness-skill/) |
| [repo.md](./repo.md) | [set-harness-goal-skill](../../../product/harness/skills/set-harness-goal-skill/), [pre-milestone-intake-skill](../../../product/harness/skills/pre-milestone-intake-skill/), [repo-status-skill](../../../product/harness/skills/repo-status-skill/), [repo-whats-next-skill](../../../product/harness/skills/repo-whats-next-skill/), [repo-append-request-skill](../../../product/harness/skills/repo-append-request-skill/), [repo-change-goal-skill](../../../product/harness/skills/repo-change-goal-skill/), [repo-refresh-skill](../../../product/harness/skills/repo-refresh-skill/) |
| [milestone/init-milestone-skill.md](./milestone/init-milestone-skill.md) | [init-milestone-skill](../../../product/harness/skills/init-milestone-skill/) |
| [milestone/milestone-status-skill.md](./milestone/milestone-status-skill.md) | [milestone-status-skill](../../../product/harness/skills/milestone-status-skill/) |
| [worktrack.md](./worktrack.md) | [worktrack-status-skill](../../../product/harness/skills/worktrack-status-skill/), [init-worktrack-skill](../../../product/harness/skills/init-worktrack-skill/), [schedule-worktrack-skill](../../../product/harness/skills/schedule-worktrack-skill/), [dispatch-skills](../../../product/harness/skills/dispatch-skills/), [generic-worker-skill](../../../product/harness/skills/generic-worker-skill/), [doc-catch-up-worker-skill](../../../product/harness/skills/doc-catch-up-worker-skill/), [review-evidence-skill](../../../product/harness/skills/review-evidence-skill/), [test-evidence-skill](../../../product/harness/skills/test-evidence-skill/), [rule-check-skill](../../../product/harness/skills/rule-check-skill/), [gate-skill](../../../product/harness/skills/gate-skill/), [recover-worktrack-skill](../../../product/harness/skills/recover-worktrack-skill/), [close-worktrack-skill](../../../product/harness/skills/close-worktrack-skill/) |

Deploy targets such as `.agents/` or `.claude/` may consume these sources after deployment, but they are not canonical source locations.
