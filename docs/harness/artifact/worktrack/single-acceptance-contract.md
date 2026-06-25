---
title: "Worktrack Single-Acceptance Contract"
artifact_type: "harness-artifact-contract"
status: "active"
updated: "2026-06-23"
owner: "servo-kernel"
last_verified: "2026-06-23"
---
# Worktrack Single-Acceptance Contract

> 本 contract 定义单 worktrack 级别的验收步骤 (single-worktrack acceptance)，在 worktrack-close-skill 内执行，对照 worktrack contract 的 completion signals 逐条验证，产出结构化 single-acceptance verdict。

## 一、定位

Single-acceptance 是 worktrack 级别的结构化验收，与 Milestone composite acceptance 形成层级映射：

| 层级 | 执行者 | 时机 | 输入 | 输出 |
|------|--------|------|------|------|
| Self-Review | worktrack executor | closeout 前 | closeout_checklist | self-review record |
| Single-Acceptance | worktrack-close-skill | closeout gate 前 | completion_signals | single-acceptance verdict |
| Closeout Gate | worktrack-gate-skill | merge 前 | all evidence | gate verdict |
| Composite Acceptance | MS-20260623-003 | milestone 全 WT 闭环后 | N 个 single-acceptance verdicts | composite acceptance report |

## 二、Completion Signal → Verification Item 映射

Single-acceptance 以 worktrack contract 中的 `completion_signals` 为验收基准，逐条映射为 verification item：

```yaml
# 示例
completion_signals:
  - "worktrack-close-skill 包含 structured self-review 步骤"  # CS1

verification_items:
  - signal_ref: "CS1"
    verification: "检查 worktrack-close-skill SKILL.md 是否包含 self-review 步骤引用"
    evidence_type: "file_content_check"
    evidence_path: ".agents/skills/servo-worktrack-close-skill/SKILL.md"
```

映射规则：

1. 每个 completion signal 至少映射一个 verification item
2. 每个 verification item 必须指定 evidence_type：`file_content_check` / `artifact_reference_check` / `governance_check` / `test_result` / `manual_review`
3. 每个 verification item 必须指定 evidence_path（待检查的文件或 artifact 路径）

## 三、Single-Acceptance Verdict 格式

```yaml
single_acceptance_verdict:
  worktrack_id: "WT-xxxx"
  milestone_id: "MS-xxxx"
  acceptance_timestamp: "ISO8601"
  acceptor: "worktrack-close-skill"

  completion_signals_checked: 6  # total signals checked
  completion_signals_passed: 5   # signals passed
  completion_signals_failed: 1   # signals failed

  verification_items:
    - item_id: "V1"
      signal_ref: "CS1"
      evidence_type: "file_content_check"
      evidence_path: ".agents/skills/servo-worktrack-close-skill/SKILL.md"
      verdict: "pass" | "fail" | "partial"
      detail: "description of what was found"
    # ... more items

  critical_failures: []  # list of signal_refs that triggered critical failure
  non_critical_failures: []  # list of signal_refs with non-blocking failure

  overall_verdict: "accepted" | "accepted_with_notes" | "blocked"
  recommendation: "proceed_to_gate" | "fix_and_retry" | "handback"
  notes: "optional contextual notes"
```

## 四、Critical Failure 判定

根据 milestone design_decision Q1（记录为主 + critical failure 升级阻断）：

### 4.1 Critical Failure 触发条件

| 条件 | 判定 |
|------|------|
| 核心功能 completion signal 明确不满足 | critical_failure |
| 安全/权限/数据完整性 signal 不满足 | critical_failure |
| 治理/合规 signal 不满足且无法在后续 milestone 补救 | critical_failure |
| 上游 contract 未完成（非本 WT 责任） | critical_failure → 记录但标记为 upstream_blocked |
| docs/template/非核心 signal 不满足 | non_critical → 记录为 accepted_with_notes |

### 4.2 Verdict 路由

```
overall_verdict
  ├─ accepted            → proceed to closeout gate
  ├─ accepted_with_notes → proceed to gate, notes recorded in closeout
  └─ blocked             → handback with failure detail
      ├─ critical_failure (own)     → fix required before retry
      └─ critical_failure (upstream) → record, optional defer
```

## 五、与 Closeout Pipeline 的集成

Single-acceptance 在 worktrack-close-skill 中的位置：

```text
Self-Review
    ↓
Single-Acceptance (本 contract 定义)    ← 新增步骤
    ↓
    ├─ accepted / accepted_with_notes → Closeout Gate
    └─ blocked → handback / fix
    ↓
Closeout Gate (worktrack-gate-skill)
    ↓
PR → Merge → Cleanup → Repo Refresh
```

## 六、与 Milestone Composite Acceptance 的接口

为 MS-20260623-003 消费，每个 single-acceptance verdict 提供以下输入：

```yaml
# Composite acceptance input (per worktrack)
composite_acceptance_input:
  worktrack_id: "WT-xxxx"
  single_acceptance_verdict: "accepted" | "accepted_with_notes" | "blocked"
  completion_signals_total: 6
  completion_signals_passed: 5
  critical_failure_count: 0
  non_critical_failure_count: 1
  verification_items_summary: "5/6 signals passed, 1 non-critical (docs navigation)"
```

MS-20260623-003 负责：

- 聚合 N 个 worktrack 的 input
- 定义权重和冲突裁决规则
- 产出 composite acceptance report

本 contract 不定义聚合逻辑。

## 七、Contract 引用

- 本 contract 被 `worktrack-close-skill` 引用
- 本 contract 消费 worktrack contract 的 `completion_signals` 字段
- 本 contract 产出 `single-acceptance verdict`，被 closeout record 和 MS-20260623-003 消费
