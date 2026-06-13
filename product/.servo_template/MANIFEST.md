# .servo_template Manifest（清单跟踪）

> 本文件记录 `product/.servo_template/` 中每个文件的对应关系。
> **最后审计**: 2026-06-13（WT-20260613-servo-template-audit）
>
> ⚠️ **注意**：Canonical source **不是** `docs/harness/artifact/`（那是字段规范文档），
> 而是 **写入该 template 的 skill**（skill 的「预期输出」字段定义才决定 template 应该长什么样）。
> 当前列出的 skill 映射需要在新 milestone 中逐一验证。

## Manifest Entries

| template 路径 | 写入它的 skill | 用途 | 审计状态 |
|---|---|---|---|
| `control-state.md` | `harness-skill`（状态更新阶段） | `.servo/control-state.md` 初始化模板 | ⚠️ 未与 skill 输出字段对比 |
| `goal-charter.md` | `set-harness-goal-skill` / `repo-change-goal-skill` | `.servo/goal-charter.md` 初始化模板 | ⚠️ 未与 skill 输出字段对比 |
| `repo/analysis.md` | `repo-whats-next-skill`（优先级重构模式） | `.servo/repo/analysis.md` 模板 | ⚠️ 未与 skill 输出字段对比 |
| `repo/snapshot-status.md` | `repo-refresh-skill` | `.servo/repo/snapshot-status.md` 模板 | ⚠️ 未与 skill 输出字段对比 |
| `worktrack/contract.md` | `init-worktrack-skill` | `.servo/worktrack/contract.md` 模板 | ⚠️ 未与 skill 输出字段对比 |
| `worktrack/gate-evidence.md` | `gate-skill` / `review-evidence-skill` / `test-evidence-skill` / `rule-check-skill` | `.servo/worktrack/gate-evidence.md` 模板 | ⚠️ 未与 skill 输出字段对比 |
| `worktrack/plan-task-queue.md` | `schedule-worktrack-skill` | `.servo/worktrack/plan-task-queue.md` 模板 | ⚠️ 未与 skill 输出字段对比 |
| `template/goal-charter.template.md` | `set-harness-goal-skill`（before-start question 模板） | goal-charter 写作模板 | ⚠️ 未与 skill 输出字段对比 |
| `docs/node-type-registry.md` | 直接复制自 `docs/harness/artifact/control/` | Worktrack 节点类型默认规则 | ✅ 2026-06-13 刚加入 |
| `README.md` | 自身 | 模板目录入口文档 | — | — |
| `repo/README.md` | 自身 | repo 子目录文档 | — | — |
| `template/README.md` | 自身 | template 子目录文档 | — | — |
| `worktrack/README.md` | 自身 | worktrack 子目录文档 | — | — |

## 同步策略说明

- `.servo_template/` 中的文件是 **runtime bootstrap 模板**，用于 skill 初始化时生成 `.servo/` 目录结构。
- 真正的 canonical source 是 **写入该文件的 skill 的「预期输出」字段定义**，不是 `docs/harness/artifact/`（那是字段规范文档）。
- 审计方法：读 skill SKILL.md 的「预期输出」章节 → 列出 skill 会写入的所有字段 → 与 template 对比，找出缺失字段。
- **当前问题**：8 个 template 未与对应 skill 的输出字段做过审计对比，可能存在保守 backfill 覆盖的字段缺口。
- **建议**：在新 milestone 中安排多个 worktrack，逐个 template 与对应 skill 做字段级审计。

## 更新规则

1. 对应 skill 的「预期输出」字段变化时，检查是否需要同步 template
2. Template 文件变更后，更新本条目的审计状态和日期
3. 新增 template 文件时，在本 manifest 中追加条目并标注写入 skill
4. 删除 template 文件时，从本 manifest 中移除条目
