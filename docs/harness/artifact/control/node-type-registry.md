---
title: "Node Type Registry"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-06-13
---

# Node Type Registry

> 本 Registry 定义所有 Worktrack 节点类型的默认规则。它是 Goal Charter Engineering Node Map、Worktrack Contract 和 worktrack-gate-skill 的统一引用上游。
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
| implementation | 代码正确性、结构合理性（worktrack-review-evidence-skill） |
| validation | 测试、验收条件、运行结果（worktrack-test-evidence-skill） |
| policy | 规则、边界、不变量、治理要求（worktrack-rule-check-skill） |
| review-only | 仅需 review 维度（research 节点专用） |

## 使用约定

- Worktrack Contract 的 `node_type` 字段必须匹配本 Registry 中已定义的类型
- Contract 中的 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` 从 Registry 继承默认值，可在 contract 中显式覆盖
- worktrack-gate-skill 根据 node_type 查找对应的 gate_criteria 以确定需要收集的证据面
- Goal Charter 的 Engineering Node Map 定义本项目使用的节点类型实例；本 Registry 定义每种类型的默认规则

## 与 Goal Charter 的关系

- Charter 的 Engineering Node Map 声明"本项目使用哪些节点类型"（实例声明）
- Registry 定义"每种节点类型的默认规则是什么"（类型定义）
- 若 Charter 引用了 Registry 未定义的类型，worktrack-gate-skill 应标记为 `policy-gate: blocked`
- Charter 可以为实例覆盖 Registry 默认值（如某 feature 的 gate_criteria 降级为 validation + policy）

## Skill 部署脚本引用

- 部署入口：`toolchain/scripts/deploy/bin/servo-installer.js` — 所有 backend 的 skill 部署统一入口。
- 部署源路径：`product/harness/adapters/{backend}/skills/` — 各 backend 的 canonical skill payload descriptor source。
- 部署目标路径：`.agents/skills/` (agents backend) / `.claude/skills/` (claude backend) — 运行时消费的 deploy target。
- Skill 与 Node Type 关系：每个 skill 对应一种或多种 node type 的执行能力；deploy 时无需按 node type 过滤，但 `worktrack-gate-skill` 在 gate 阶段会按 Worktrack Contract 中的 `node_type` 查找对应的 `gate_criteria` 以确定证据面。
- 验证命令：`node toolchain/scripts/deploy/bin/servo-installer.js diagnose --backend agents --json` — 获取当前 skill set 的部署状态；`verify --backend agents` — 验证部署完整性。
- 本 Registry 是 worktrack-gate-skill 的 node type 默认值来源，不直接参与 deploy 流程；deploy 脚本无需引用本 Registry。
