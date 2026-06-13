---
title: "Milestone History"
status: active
updated: 2026-05-25
owner: servo-kernel
last_verified: 2026-06-13
---

# Milestone History

> `.servo/repo/milestone-history.md` 是 `RepoScope` 运行时 artifact，承接已完成或已替换 milestone 的历史条目。它让 `.servo/repo/milestone-backlog.md` 保持为 live backlog，只展示 `planned` / `active` 的真实待处理 pipeline。

## 定位

- Scope: `RepoScope`
- 性质: 运行时 artifact（非 git 追溯，`.servo/` 被 gitignore）
- 产生时机: 首个 milestone 从 live backlog 进入 `completed` 或 `superseded` 时创建
- 更新时机: milestone final acceptance、work-collection 自动 supersede、programmer override 或 pipeline cleanup
- 消费方: `milestone-status-skill`、`repo-whats-next-skill`、`harness-skill`、治理检查

## 字段约定

每个 history 条目沿用 milestone backlog 条目结构，至少包含：

- `milestone_id`
- `title`
- `purpose`
- `status`: `completed` / `superseded`
- `priority`
- `depends_on_milestones`
- `worktrack_list`
- `created_by`
- `created_at`
- `updated`
- `updated_by`
- `milestone_kind`
- `acceptance` 或 `handback`（如适用）

## 语义

- history 按 `milestone_id` upsert；相同 id 的更新遵循 latest override。
- history 不参与 next milestone 激活队列排序。
- dependency resolution 必须同时读取 live backlog 和 history；依赖只有在 history 中为 `completed` / `superseded`，或 live backlog 中明确已达等价状态时才算满足。
- completed / accepted history 条目不得包含 `(planned)` 或 `(active)` worktrack marker。
- `milestone_pipeline_summary` 的 completed/superseded 计数来自 history；planned/active 计数来自 live backlog。

## 维护约定

- `harness-skill` 执行 final acceptance writeback 时，必须把 goal-driven completed milestone 从 live backlog 移入 history。
- work-collection milestone 完成后自动标记 `superseded` 并移入 history。
- 如果 history 文件缺失但 live backlog 仍含 completed/superseded 条目，治理检查应提示需要清理迁移，而不是把单文件模型继续视为长期目标。
- 如果同一 `milestone_id` 同时存在于 live backlog 与 history，除非 live 条目是显式 override，否则必须标记 pipeline stale。
