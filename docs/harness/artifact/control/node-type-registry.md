---
title: "Node Type Registry"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-05-08
---

# Node Type Registry

> 本 Registry 定义所有 Worktrack 节点类型的默认规则。它是 Goal Charter Engineering Node Map、Worktrack Contract 和 gate-skill 的统一引用上游。
>
> Goal Charter 定义**实例**（本项目使用哪些节点类型），Registry 定义**类型默认值**（每种节点类型的标准行为）。

## 节点类型定义

### feature

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-feature-branch |
| gate_criteria | implementation + validation + policy |
| if_interrupted_strategy | checkpoint-or-recover |
| description | 新增 Harness、adapter、scaffold 或 distribution 能力 |

### refactor

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-refactor-branch |
| gate_criteria | validation + policy |
| if_interrupted_strategy | checkpoint-or-rollback |
| description | 结构性清理，无意图行为变更 |

### research

| 字段 | 值 |
|------|-----|
| merge_required | no |
| baseline_form | annotated-tag-or-report |
| gate_criteria | review-only |
| if_interrupted_strategy | preserve-report-and-stop |
| description | 调查后决定是否准入新真相或实现方向 |

### bugfix

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-bugfix-branch |
| gate_criteria | implementation + validation + policy |
| if_interrupted_strategy | checkpoint-or-rollback |
| description | 修复 skill、deploy、governance、gate 或 docs 中的缺陷 |

### docs

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-docs-branch |
| gate_criteria | review + policy |
| if_interrupted_strategy | checkpoint-or-recover |
| description | 真相层、runbook、governance 或 artifact 文档更新 |

### config

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-config-branch |
| gate_criteria | validation + policy |
| if_interrupted_strategy | checkpoint-or-rollback |
| description | Adapter payload、deploy mapping、hook、package 或 backend 配置变更 |

### test

| 字段 | 值 |
|------|-----|
| merge_required | yes |
| baseline_form | commit-on-test-branch |
| gate_criteria | validation + policy |
| if_interrupted_strategy | checkpoint-or-recover |
| description | governance、deploy、scaffold、adapter 或 gate 行为的聚焦测试 |

## Gate Criteria 组合语义

| criteria | 含义 |
|----------|------|
| implementation | 代码正确性、结构合理性（review-evidence-skill） |
| validation | 测试、验收条件、运行结果（test-evidence-skill） |
| policy | 规则、边界、不变量、治理要求（rule-check-skill） |
| review-only | 仅需 review 维度（research 节点专用） |

## 使用约定

- Worktrack Contract 的 `node_type` 字段必须匹配本 Registry 中已定义的类型
- Contract 中的 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` 从 Registry 继承默认值，可在 contract 中显式覆盖
- gate-skill 根据 node_type 查找对应的 gate_criteria 以确定需要收集的证据面
- Goal Charter 的 Engineering Node Map 定义本项目使用的节点类型实例；本 Registry 定义每种类型的默认规则

## 与 Goal Charter 的关系

- Charter 的 Engineering Node Map 声明"本项目使用哪些节点类型"（实例声明）
- Registry 定义"每种节点类型的默认规则是什么"（类型定义）
- 若 Charter 引用了 Registry 未定义的类型，gate-skill 应标记为 `policy-gate: blocked`
- Charter 可以为实例覆盖 Registry 默认值（如某 feature 的 gate_criteria 降级为 validation + policy）
