---
title: "Decision Log"
status: active
updated: 2026-05-13
owner: servo-kernel
last_verified: 2026-05-13
---

# Decision Log

> `.aw/repo/decision-log.md` 是 `RepoScope` 运行时 artifact，用来记录影响后续 worktrack 或 Harness 规则的关键决策理由。它补足 Worktrack Backlog 的"做了什么"，回答"为什么这样做，以及哪些方案被排除"。

## 定位

- Scope: `RepoScope`
- 性质: 运行时 artifact（非 git 追溯，`.aw/` 被 gitignore）
- 产生时机: 出现会影响后续实现、调度、治理、分层、权限或 artifact 合同的稳定决策时
- 更新时机: 决策被接受、替代、废弃或关联 worktrack closeout 时
- 消费方: `harness-skill`、`repo-status-skill`、`repo-whats-next-skill`、`init-worktrack-skill`、`repo-refresh-skill`

## 字段约定

每条 Decision Record 至少包含:

- `decision_id`: 唯一标识，如 `ADR-20260513-001`
- `date`: 决策日期
- `status`: `accepted` / `superseded` / `rejected`
- `context`: 决策背景和约束
- `decision`: 已采纳或明确拒绝的决定
- `alternatives_considered`: 评估过的替代方案
- `why_not_chosen`: 替代方案未采纳的原因
- `consequences`: 已知影响、代价和后续约束
- `affected_artifacts`: 受影响 artifact 或源码路径
- `related_worktracks`: 相关 worktrack IDs
- `related_commits`: 相关 commit refs（如有）
- `supersedes`: 被本决策替代的 decision IDs（如有）

## 关系

- 不替代 [worktrack-backlog.md](./worktrack-backlog.md)。Worktrack Backlog 记录 worktrack 状态和验证摘要；Decision Log 记录跨 worktrack 可复用的决策理由。
- 不替代 [snapshot-status.md](./snapshot-status.md)。Snapshot 记录 repo 当前慢变量；Decision Log 记录为什么某些慢变量以当前方式存在。
- Worktrack Backlog 条目的 `decision_refs` 应引用本文件中的 `decision_id`，让 closeout 结果能追溯到关键设计理由。

## 维护约定

- 相同 `decision_id` 使用 latest override，保留 superseded/rejected 状态而不是删除历史。
- 只记录会影响后续行为的稳定决策；一次性执行细节留在 worktrack evidence 或 closeout report。
- 未验证、未采纳或仍在讨论中的判断不得写成 `accepted`。
