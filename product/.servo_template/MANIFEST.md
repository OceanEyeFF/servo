# .servo_template Manifest（清单跟踪）

> 本文件记录 `product/.servo_template/` 中每个文件的对应关系。
> **最后审计**: 2026-06-26（MS-20260625-003，WT-20260625-installer-template-sync）
>
> ✅ **MS-20260625-003 更新**：新增 3 个分拆模板（operator-config、control-state-repo、control-state-wt），更新 control-state 模板为精简跨 scope 记忆版本。validate 全部通过。

## Manifest Entries

| template 路径 | 写入它的 skill | 用途 | 审计状态 |
|---|---|---|---|
| `control-state.md` | `harness-skill`（状态更新阶段） | `.servo/control-state.md` 初始化模板（分拆后仅保留跨 scope 记忆） | ✅ 2026-06-26 — MS-20260625-003 更新为分拆版本 |
| `operator-config.md` | `harness-set-goal-skill` | `.servo/operator-config.md` 初始化模板（人类可调配置） | ✅ 2026-06-26 — MS-20260625-003 新增 |
| `repo/control-state-repo.md` | `harness-set-goal-skill` | `.servo/control-state-repo.md` 初始化模板（Repo + Milestone 级） | ✅ 2026-06-26 — MS-20260625-003 新增 |
| `worktrack/control-state-wt.md` | `harness-set-goal-skill` | `.servo/control-state-wt.md` 初始化模板（Worktrack 级） | ✅ 2026-06-26 — MS-20260625-003 新增 |
| `goal-charter.md` | `harness-set-goal-skill` / `repo-change-goal-skill` | `.servo/goal-charter.md` 初始化模板 | ✅ 2026-06-13 — 12 missing (6 cross-artifact)/2 extra/1 naming deviation |
| `repo/discovery-input.md` | `harness-set-goal-skill`（Existing Code Project Adoption） | `.servo/repo/discovery-input.md` 只读事实输入模板 | ✅ 2026-06-14 — restored for set-harness-goal adoption fixture and package smoke |
| `repo/temporary-understanding.md` | `harness-set-goal-skill`（Weak-doc onboarding） | `.servo/repo/temporary-understanding.md` 临时理解模板 | ✅ 2026-06-14 — restored for weak-doc onboarding fixture |
| `repo/complex-project-entry-gate.md` | `harness-set-goal-skill`（Complex Project Entry Gate） | `.servo/repo/complex-project-entry-gate.md` 复杂项目准入 gate 模板 | ✅ 2026-06-14 — restored for complex gate fixture |
| `repo/analysis.md` | `repo-whats-next-skill`（优先级重构模式） | `.servo/repo/analysis.md` 模板 | ✅ 2026-06-13 — 12 missing (7 transient)/0 extra/2 naming deviations |
| `repo/snapshot-status.md` | `repo-refresh-skill` | `.servo/repo/snapshot-status.md` 模板 | ✅ 2026-06-13 — 10 missing (3 from Contract, 7 transient)/0 extra |
| `worktrack/contract.md` | `worktrack-init-skill` | `.servo/worktrack/contract.md` 模板 | ✅ 2026-06-13 — 8 missing/0 extra/3 naming deviations；synced: Milestone Review Gate, Branch Policy, milestone_id |
| `worktrack/gate-evidence.md` | `worktrack-gate-skill` / `worktrack-review-evidence-skill` / `worktrack-test-evidence-skill` / `worktrack-rule-check-skill` | `.servo/worktrack/gate-evidence.md` 模板 | ✅ 2026-06-13 — 5 missing/4 extra (bootstrap)/2 naming deviations |
| `worktrack/plan-task-queue.md` | `worktrack-schedule-skill` | `.servo/worktrack/plan-task-queue.md` 模板 | ✅ 2026-06-13 — 6 missing/2 extra (bootstrap)/1 naming deviation |
| `template/goal-charter.template.md` | `harness-set-goal-skill`（before-start question 模板） | goal-charter 写作模板 | ✅ 2026-06-13 — 2 missing/1 extra；identical to goal-charter.md template |
| `docs/node-type-registry.md` | 直接复制自 `docs/harness/artifact/control/` | Worktrack 节点类型默认规则 | ✅ 2026-06-13 刚加入 |
| `README.md` | 自身 | 模板目录入口文档 | — | — |
| `repo/README.md` | 自身 | repo 子目录文档 | — | — |
| `template/README.md` | 自身 | template 子目录文档 | — | — |
| `worktrack/README.md` | 自身 | worktrack 子目录文档 | — | — |

## 同步策略说明

- `.servo_template/` 中的文件是 **runtime bootstrap 模板**，用于 skill 初始化时生成 `.servo/` 目录结构。
- 真正的 canonical source 是 **写入该文件的 skill 的「预期输出」字段定义**，不是 `docs/harness/artifact/`（那是字段规范文档）。
- 审计方法：读 skill SKILL.md 的「预期输出」章节 → 列出 skill 会写入的所有字段 → 与 template 对比，找出缺失字段。
- **当前状态**：8 个 template 全部审计 + 同步完成。所有 MANIFEST ✅。
- backup/update artifacts and runtime history rows intentionally not templated

## 更新规则

1. 对应 skill 的「预期输出」字段变化时，检查是否需要同步 template
2. Template 文件变更后，更新本条目的审计状态和日期
3. 新增 template 文件时，在本 manifest 中追加条目并标注写入 skill
4. 删除 template 文件时，从本 manifest 中移除条目
