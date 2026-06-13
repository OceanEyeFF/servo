# .servo_template Manifest（清单跟踪）

> 本文件记录 `product/.servo_template/` 中每个文件与 canonical source 的对应关系及同步状态。
> 每次 canonical source 更新后，应更新本 manifest 并检查对应 template 是否需要同步。
> **最后审计**: 2026-06-13
> **审计依据**: WT-20260613-servo-template-audit

## Manifest Entries

| template 路径 | canonical source | 用途 | 同步状态 | 最后同步 |
|---|---|---|---|---|
| `control-state.md` | `docs/harness/artifact/control/control-state.md` | `.servo/control-state.md` 模板 | ❌ stale (+12134B) | — |
| `goal-charter.md` | `docs/harness/artifact/repo/goal-charter.md` | `.servo/goal-charter.md` 模板 | ❌ stale (+771B) | — |
| `repo/analysis.md` | `docs/harness/artifact/repo/repo-analysis.md` | `.servo/repo/analysis.md` 模板 | ❌ stale (+2528B) | — |
| `repo/snapshot-status.md` | `docs/harness/artifact/repo/snapshot-status.md` | `.servo/repo/snapshot-status.md` 模板 | ❌ stale (+6422B) | — |
| `worktrack/contract.md` | `docs/harness/artifact/worktrack/contract.md` | `.servo/worktrack/contract.md` 模板 | ❌ stale (+3924B) | — |
| `worktrack/gate-evidence.md` | `docs/harness/artifact/worktrack/gate-evidence.md` | `.servo/worktrack/gate-evidence.md` 模板 | ❌ stale (+3023B) | — |
| `worktrack/plan-task-queue.md` | `docs/harness/artifact/worktrack/plan-task-queue.md` | `.servo/worktrack/plan-task-queue.md` 模板 | ❌ stale (+4154B) | — |
| `template/goal-charter.template.md` | `docs/harness/artifact/repo/goal-charter.md` | goal-charter 写作模板 | ❌ stale (+789B) | — |
| `docs/node-type-registry.md` | `docs/harness/artifact/control/node-type-registry.md` | Worktrack 节点类型默认规则 | ✅ synced | 2026-06-13 |
| `README.md` | 自身 | 模板目录入口文档 | — | — |
| `repo/README.md` | 自身 | repo 子目录文档 | — | — |
| `template/README.md` | 自身 | template 子目录文档 | — | — |
| `worktrack/README.md` | 自身 | worktrack 子目录文档 | — | — |

## 同步策略说明

- `.servo_template/` 中的文件是 **runtime bootstrap 模板**，用于 `set-harness-goal-skill` 或 deploy 初始化时生成 `.servo/` 目录结构。
- Canonical source (`docs/harness/artifact/`) 是 **规范参考文档**，内容更详细，包含完整字段定义、使用约定和治理规则。
- Template 版本可以是从 canonical source 精简的可执行副本，不必逐字节对齐，但必须覆盖初始化所需的最小字段和结构。
- **当前问题**：Template 版本严重过时，大部分文件仍停留在早期版本，缺少 milestone_kind、composite acceptance、intake review、refresh signals 等关键字段。
- **建议**：在一个专门的 milestone 中做全量 template sync，将每个 template 对齐到对应 canonical source 的当前版本。

## 更新规则

1. Canonical source 新增字段时，评估是否需要同步到对应 template
2. Template 文件变更后，更新本条目的「同步状态」和「最后同步」
3. 新增 template 文件时，在本 manifest 中追加条目
4. 删除 template 文件时，从本 manifest 中移除条目
5. 每次 milestone closeout 前检查 manifest 中标记为 ❌ 的条目是否需要在当前 milestone 中处理
