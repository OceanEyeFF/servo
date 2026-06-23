---
title: "Worktrack Self-Review Contract"
artifact_type: "harness-artifact-contract"
status: "active"
updated: "2026-06-23"
owner: "servo-kernel"
last_verified: "2026-06-23"
---
# Worktrack Self-Review Contract

> 本 contract 定义 worktrack closeout gate 前的结构化 self-review 步骤。每个 worktrack 在进入 closeout 阶段前，必须执行 self-review 并产出结构化 self-review record。

## 一、定位

Self-review 是 closeout gate 的**前置检查步骤**，不是替代 gate 裁决。

| 对比 | Self-Review | Gate |
|------|-------------|------|
| 执行者 | worktrack executor (current-carrier / SubAgent) | 独立审查载体 (review / test / policy skills) |
| 性质 | 自查 + 记录 | 正式裁决 |
| 阻断语义 | 记录 + critical failure 升级阻断 | 硬裁决 (pass / soft-fail / hard-fail / blocked) |
| 时机 | closeout 阶段开始前 | closeout 阶段中 (merge 前) |

## 二、检查维度

Self-review 覆盖 3 个检查维度：

### 2.1 Artifact 更新完整性 (`artifact_completeness`)

检查 worktrack 执行完毕后，所有应更新的 `.servo/` artifact 是否已正确更新。

Check items:

| # | Item | 检查方法 |
|---|------|---------|
| A1 | `milestone/{milestone_id}.md` 的 `progress_counter` 是否反映当前 worktrack 完成状态 | 对比 milestone artifact 中的 total/completed/blocked/deferred 与 worktrack-backlog |
| A2 | `.servo/repo/worktrack-backlog.md` 中本 worktrack 条目状态是否为 `done` / `deferred` / `blocked` | 读取 worktrack-backlog 中本 worktrack_id 条目 |
| A3 | `.servo/control-state.md` 的 `latest_closed_worktrack_commit` 是否已追加本 worktrack 的 closeout commit | 读取 control-state Active Worktrack 段 |
| A4 | 其他受影响的 artifact（contract、plan-task-queue、gate-evidence 等）是否已更新到最终状态 | 逐项检查 worktrack contract 中声明的 impacted modules |

Verdict:

- `pass`: 所有 check items 通过
- `fail`: 任一 check item 不通过 → 标记为 `artifact_not_updated`

### 2.2 Scope 合规 (`scope_compliance`)

检查实际改动是否在 worktrack contract 声明的 scope 范围内。

Check items:

| # | Item | 检查方法 |
|---|------|---------|
| S1 | `git diff branch_source_ref..HEAD` 是否仅涉及 worktrack contract 中 `impacted_modules` 声明的模块 | 对比 diff 文件列表与 impact_modules |
| S2 | 是否存在 worktrack contract `non-goals` 中明确排除的改动 | 交叉检查 diff 内容与 non-goals |
| S3 | 是否存在未在 worktrack contract 中声明的新文件或新目录 | 检查 untracked/new files |

Verdict:

- `pass`: 所有改动在 scope 内
- `failure_non_blocking`: 存在轻微漂移但可解释（如 docs 入口更新、模板同步等关联改动）→ 记录但放行
- `blocking`: 存在明确 scope 外改动且无法解释 → 标记为 `scope_drift`

### 2.3 Docs 一致性 (`docs_consistency`)

检查受影响的 docs 是否与代码/配置变更保持一致。

Check items:

| # | Item | 检查方法 |
|---|------|---------|
| D1 | 若 worktrack 修改了 skill 源码或配置，对应 docs/harness/ 文档是否同步更新 | 对比 skill 源码变更与 docs/harness/ 变更 |
| D2 | 若 worktrack 新增/修改/删除了 artifact contract，docs/harness/README.md 入口导航是否更新 | 检查 docs README 中的引用 |
| D3 | 若 worktrack 涉及 docs/ 文件修改，frontmatter (title/status/updated/owner/last_verified) 是否完整 | 检查修改的 docs 文件 frontmatter |

Verdict:

- `pass`: 所有 docs 一致性通过
- `failure_non_blocking`: docs 存在轻微不同步但可后续追平（如 README 入口遗漏但 contract 本身正确）
- `blocking`: docs 严重落后于代码变更（如新增 contract 无任何文档引用）

## 三、Self-Review Record 输出格式

```yaml
self_review_record:
  worktrack_id: "WT-xxxx"
  milestone_id: "MS-xxxx"
  review_timestamp: "ISO8601"
  reviewer: "carrier-identity"

  artifact_completeness:
    verdict: "pass" | "fail"
    check_results:
      - item: "A1"
        passed: true | false
        detail: "description"
      - item: "A2"
        passed: true | false
        detail: "description"
      # ... A3, A4
    blocking_issues: []

  scope_compliance:
    verdict: "pass" | "failure_non_blocking" | "blocking"
    check_results:
      - item: "S1"
        passed: true | false | "partial"
        detail: "description"
      # ... S2, S3
    out_of_scope_files: []
    blocking_issues: []

  docs_consistency:
    verdict: "pass" | "failure_non_blocking" | "blocking"
    check_results:
      - item: "D1"
        passed: true | false
        detail: "description"
      # ... D2, D3
    stale_docs: []
    blocking_issues: []

  overall_verdict: "clear" | "blocked"
  recommendation: "proceed_to_closeout" | "fix_and_retry" | "handback"
```

## 四、阻断条件

### 4.1 升级为 blocking 的条件

| 条件 | 来源维度 | 行为 |
|------|---------|------|
| `artifact_not_updated` | artifact_completeness | 阻断 closeout，返回 "需要先更新 artifact" |
| `scope_drift` (blocking) | scope_compliance | 阻断 closeout，handback with diff summary |
| `docs_serious_stale` (blocking) | docs_consistency | 阻断 closeout，返回 "需要先同步 docs" |

### 4.2 记录但不阻断的条件

| 条件 | 来源维度 | 行为 |
|------|---------|------|
| `scope_drift_non_blocking` | scope_compliance | 记录到 closeout record，放行 |
| `docs_minor_stale` | docs_consistency | 记录为 follow-up note，放行 |

### 4.3 阻断后的处理

```
self-review blocked
  ├─ artifact_not_updated → 更新 artifact → 重新 self-review
  ├─ scope_drift → handback programmer 决策：
  │     ├─ 接受漂移（更新 scope）→ 重新 self-review
  │     ├─ 回退漂移 → 重新 self-review
  │     └─ 拆分为新 worktrack
  └─ docs_serious_stale → 补 docs → 重新 self-review
```

## 五、与 Closeout Pipeline 的集成

Self-review 在 close-worktrack-skill 中的插入位置：

```text
Gate pass
    ↓
Self-Review (本 contract 定义)          ← 新增步骤
    ↓
    ├─ clear → 继续 closeout
    └─ blocked → handback / fix
    ↓
Closeout phases:
    准备合并请求 → PR → Merge → Cleanup → Repo Refresh
```

Self-review 的输入来自 `Worktrack Contract.closeout_checklist` 字段（由 WT-20260623-wt-contract-checklist 定义），该字段列出本 worktrack 完成后必须更新的 `.servo/` 产物及对应字段。

## 六、与 Single-Acceptance 的关系

| 步骤 | 执行者 | 时机 |
|------|--------|------|
| Self-Review | worktrack executor | closeout 前 |
| Single-Acceptance | close-worktrack-skill 内部 | closeout gate 前 (merge 前) |
| Closeout Gate | gate-skill | merge 前 / merge 后 |

Self-review 是自查，single-acceptance 是结构化验收。两者互补但不可替代。

## 七、Contract 引用

- 本 contract 被 `close-worktrack-skill` 引用
- 本 contract 消费 `closeout_checklist` 字段（来自 WT-20260623-wt-contract-checklist）
- 本 contract 产出 `self-review record`，被 gate-skill 和 closeout record 消费
