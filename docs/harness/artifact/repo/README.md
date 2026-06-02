# Harness Artifact / Repo

`docs/harness/artifact/repo/` 承接 `RepoScope` 的长期基线对象。

当前入口：

- [discovery-input.md](./discovery-input.md)
- [complex-project-entry-gate.md](./complex-project-entry-gate.md) — 运行时 artifact / handoff contract：在复杂项目、弱文档或高风险 milestone 创建/激活/派生 worktrack 前记录 `complex_project_entry_gate`、scanner evidence、operator safety policy 和 Milestone-side blocking decision
- [goal-charter.md](./goal-charter.md)
- [repo-analysis.md](./repo-analysis.md)
- [snapshot-status.md](./snapshot-status.md)
- [decision-log.md](./decision-log.md) — 运行时 artifact：记录影响后续 worktrack 或 Harness 规则的关键决策理由，并通过 `decision_refs` 与 Worktrack Backlog 关联
- [milestone-backlog.md](./milestone-backlog.md) — 运行时 artifact：记录 live Milestone Pipeline（planned/active），由 init-milestone-skill 创建条目，harness-skill 执行状态转移，milestone-status-skill 和 repo-whats-next-skill 作为 pipeline 推理输入
- [milestone-history.md](./milestone-history.md) — 运行时 artifact：记录 completed/superseded milestone 历史，供依赖解析、审计和 stale marker 检查使用
- [worktrack-backlog.md](./worktrack-backlog.md) — 运行时 artifact：记录所有 worktrack 的完成状态（done/deferred/blocked/resolved），由 repo-refresh-skill 在 worktrack closeout 后写入，由 milestone-status-skill 在 Milestone Observe 时消费
