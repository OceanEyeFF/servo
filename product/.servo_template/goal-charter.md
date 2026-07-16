# Repo Goal / Charter

> 这是 `.servo/goal-charter.md` 的 template-owned seed，用来记录当前 repo 的长期目标和方向。

## Metadata

- repo:
- owner:
- updated:
- status:

## Project Vision

-

## Core Product Goals

-

## Technical Direction

-

## Engineering Node Map

> 本 Goal 涉及的工程节点类型规划，供 Repo/Milestone 编排 Worktrack 时参考。

### Node Type Registry

| type | merge_required | baseline_form | gate_criteria | if_interrupted_strategy | 说明 |
|------|---------------|---------------|---------------|-------------------------|------|
| `feature` | yes | commit-on-feature-branch | implementation + validation + policy | checkpoint-or-recover | 新功能开发 |
| `refactor` | yes | commit-on-refactor-branch | validation + policy | checkpoint-or-rollback | 重构，不改变外部行为 |
| `research` | no | annotated-tag-or-report | review-only | preserve-report-and-stop | 调研/探针，产出可能不可合并 |
| `bugfix` | yes | commit-on-bugfix-branch | implementation + validation + policy | checkpoint-or-rollback | 缺陷修复 |
| `docs` | yes | commit-on-docs-branch | review + policy | checkpoint-or-recover | 文档更新 |
| `config` | yes | commit-on-config-branch | validation + policy | checkpoint-or-rollback | 配置/部署变更 |
| `test` | yes | commit-on-test-branch | validation + policy | checkpoint-or-recover | 专项测试 |

### This Goal's Node Types

> 列出本 Goal 实际使用的节点类型。可添加多个条目，每条对应一个 type。

- type:
  - expected_count:
  - merge_required:
  - baseline_form:
  - gate_criteria:
  - if_interrupted_strategy:
- type:
  - expected_count:
  - merge_required:
  - baseline_form:
  - gate_criteria:
  - if_interrupted_strategy:
- type:
  - expected_count:
  - merge_required:
  - baseline_form:
  - gate_criteria:
  - if_interrupted_strategy:

### Node Dependency Graph

- source_type -> target_type (reason)

### Default Baseline Policy

- if_worktrack_interrupted:
- if_no_merge:

## Success Criteria

-

## System Invariants

-

## Notes

-
