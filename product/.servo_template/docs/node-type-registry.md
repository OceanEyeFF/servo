---
title: "Node Type Registry"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-06-13
---

# Node Type Registry

> 本 Registry 定义 Worktrack 节点类型的默认规划提示。Goal Charter 选择项目实际使用的节点类型；具体 Worktrack 验收以 initial requirement 和独立 Review 为准。
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
| implementation | 代码正确性、结构合理性（独立 `worktrack-review-skill`） |
| validation | 测试、验收条件、运行结果（PlanWork affected validation + 独立 Review） |
| policy | 规则、边界、不变量、治理要求（对应确定性 guard + 独立 Review） |
| review-only | 仅需 review 维度（research 节点专用） |

## 使用约定

- Repo/Milestone 可以用 Registry 辅助规划，但不得让默认值覆盖已批准的 objective、scope 或 acceptance。
- Candidate Worktrack 的具体入口由 `initial-requirement.yaml` 固定，Review 直接按该入口验收。
- Goal Charter 的 Engineering Node Map 定义本项目使用的节点类型实例；本 Registry 定义每种类型的默认规则

## 与 Goal Charter 的关系

- Charter 的 Engineering Node Map 声明"本项目使用哪些节点类型"（实例声明）
- Registry 定义"每种节点类型的默认规则是什么"（类型定义）
- 若 Charter 引用了 Registry 未定义的类型，上层 Repo/Milestone Orchestrator 必须在创建 Worktrack 前阻塞
- Charter 可以为实例覆盖 Registry 默认值（如某 feature 的 gate_criteria 降级为 validation + policy）

## Skill 部署脚本引用

- 部署入口：`toolchain/scripts/deploy/bin/servo-installer.js` — 所有 backend 的 skill 部署统一入口。
- 部署源路径：`product/harness/adapters/{backend}/skills/` — 各 backend 的 canonical skill payload descriptor source。
- 部署目标路径：`.agents/skills/` (agents backend) / `.claude/skills/` (claude backend) — 运行时消费的 deploy target。
- Skill 与 Node Type 关系：deploy 不按 node type 过滤；Node Type 只作为上层规划提示，不形成 Candidate Worktrack 的第二套验收权威。
- 验证命令：`node toolchain/scripts/deploy/bin/servo-installer.js diagnose --backend agents --json` — 获取当前 skill set 的部署状态；`verify --backend agents` — 验证部署完整性。
- 本 Registry 不直接参与 deploy 流程；deploy 脚本无需引用本 Registry。
