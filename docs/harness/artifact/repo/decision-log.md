---
title: "Decision Log"
status: active
updated: 2026-06-14
owner: servo-kernel
last_verified: 2026-06-14
---
# Decision Log

> `.servo/repo/decision-log.md` 是 `RepoScope` 运行时 artifact，用于记录会影响长期 repo 行为、Harness 合同或后续 Worktrack 路由的结构化决策。它补充 milestone/worktrack backlog 的状态事实，不替代正式文档、gate evidence 或 closeout record。

## 定位

- Scope: `RepoScope`
- 性质: 运行时 artifact（非 git 追溯，`.servo/` 被 gitignore）
- 产生时机: 需要保留跨 worktrack 决策理由、替代方案或影响面的 closeout / repo-refresh
- 消费方: `harness-skill`、`repo-refresh-skill`、`milestone-status-skill`、后续 Worktrack intake/review

## 字段约定

每条 decision 至少包含:

- `decision_id`: 唯一标识
- `date`: 决策日期或时间
- `status`: `accepted` / `superseded` / `rejected`
- `context`: 决策背景和触发条件
- `decision`: 实际采纳的决策
- `alternatives_considered`: 已考虑的替代方案
- `why_not_chosen`: 替代方案未采用原因
- `consequences`: 已知后果、限制和后续影响
- `affected_artifacts`: 受影响的 docs / product / toolchain / `.servo` artifact
- `related_worktracks`: 相关 worktrack id 列表
- `related_commits`: 相关 commit 或 merge checkpoint
- `supersedes`: 被本决策取代的 decision id；无则为 `none`

`accepted`、`superseded` 和 `rejected` 只能作为 `status` 取值，不得混用为 milestone 或 worktrack 的完成状态。

## 与正式 artifact 的关系

- 不替代 `docs/harness/artifact/repo/milestone-backlog.md` 或 `worktrack-backlog.md`；backlog 记录状态，decision log 记录理由。
- 不替代 `docs/harness/artifact/worktrack/gate-evidence.md`；gate evidence 记录当前关卡证据，decision log 记录跨周期可复用的取舍。
- Worktrack backlog 可通过 `decision_refs` 链回本 artifact，形成执行记录到决策理由的 traceability。
