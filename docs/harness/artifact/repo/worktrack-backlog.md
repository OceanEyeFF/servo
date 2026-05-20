---
title: "Worktrack Backlog"
status: active
updated: 2026-05-10
owner: servo-kernel
last_verified: 2026-05-10
---

# Worktrack Backlog

> `.servo/repo/worktrack-backlog.md` 是 `RepoScope` 运行时 artifact，记录所有 worktrack 的完成状态。不是部署模板。由 `repo-refresh-skill` 在 worktrack closeout 后写入（upsert-by-worktrack_id），`harness-skill` 作为 supervisor/binder 负责调度 `repo-refresh`，由 `milestone-status-skill` 在 Milestone Observe 时消费。

## 定位

- Scope: `RepoScope`
- 性质: 运行时 artifact（非 git 追溯，`.servo/` 被 gitignore）
- 产生时机: 首个 worktrack closeout 时由 `repo-refresh-skill` 创建
- 更新时机: 每次 worktrack closeout 后由 `repo-refresh-skill` 写入（upsert-by-worktrack_id）；`harness-skill` 作为 supervisor 调度 `repo-refresh` 执行写入
- 消费方: `milestone-status-skill`（Milestone Observe 时对照 `worktrack_list` 计算 progress）

## 字段约定

每个 worktrack 条目至少包含:

- `worktrack_id`: 唯一标识 (如 `WT-20260508-p0-074-milestone-impl`)
- `milestone_id`: 所属 Milestone ID（optional，无绑定时为 null）
- `status`: `done` / `deferred` / `blocked` / `resolved`
- `node_type`: 从 Goal Charter 的 Engineering Node Map 绑定
- `scope`: 简要变更说明
- `merge_commit`: 合并 hash（如有）
- `validation`: 验证结果摘要
- `decision_refs`: 关联 Decision Log 条目 ID 列表（如无关键跨 worktrack 决策则为空列表）
- `intake_route`: 追加请求来源

`milestone-status-skill` 读取 backlog 时先按 `milestone_id` 过滤（匹配当前 active milestone），再将 `status` 按以下映射转换后参与 progress 计算：`done`/`resolved` -> completed，`deferred` -> deferred，`blocked` -> blocked。

## 与正式 artifact 的关系

- 不替代 `docs/harness/artifact/repo/snapshot-status.md`（snapshot-status 是 Repo 级当前快照，backlog 是历史列表）。
- 不替代 `docs/harness/artifact/worktrack/contract.md`（contract 是单个 worktrack 的局部合同）。
- 不替代 `docs/harness/artifact/repo/decision-log.md`（decision log 记录关键决策理由；backlog 只通过 `decision_refs` 引用）。
- `milestone-status-skill` 使用 backlog 对照 Milestone 的 `worktrack_list` 统计 completed/blocked/deferred，计算 progress counter。

## 维护约定

- `repo-refresh-skill` 在 worktrack closeout 后按 `worktrack_id` upsert 条目；相同 id 更新为新状态，不产生重复行。
- 条目按时间倒序排列（最新在前）；`milestone-status-skill` 消费时按 `worktrack_id` 去重取最新。
- `deferred` 条目保留原状直到 programmer 重新决策。
