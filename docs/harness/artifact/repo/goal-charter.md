---
title: "Goal / Charter"
status: active
updated: 2026-05-09
owner: servo-kernel
last_verified: 2026-06-13
---

# Goal / Charter

定义 repo 的长期目标和方向，作为 Harness 控制循环的基准参照信号（reference signal）。由 `repo-init-goal-skill` 初始化生成，`repo-change-goal-skill` 变更，所有下游 skill 以此为事实源对齐。

Goal Charter 是高抽象目标、设计框架和系统不变量的 anchor / guardrail，不是高频 Milestone planner。成熟项目中，Milestone / Worktrack 与 Final Goal 存在较大 abstraction distance 是正常状态；具体任务通常来自用户追加、repo runtime state、append request、pre-intake、repo-whats-next、已有 artifact drift 或维护面下沉。判断重点是这些任务是否仍在同一抽象设计框架内推进，而不是是否能由 Goal Charter 直接推导。

## 结构化字段表

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_vision` | text | 项目愿景：该项目为何存在，解决的长期问题 |
| `core_product_goals` | list[text] | 核心功能目标：可验证的产品级交付物列表 |
| `technical_direction` | text | 技术方向：技术栈、架构约束、演进路线 |
| `engineering_node_map` | table | 工程节点类型规划，见下方子表 |
| `success_criteria` | list[text] | 成功标准：可度量的验收条件 |
| `system_invariants` | list[text] | 系统不变量：不可违反的约束（安全、合规、数据完整性等） |
| `notes` | text | 备注：元信息、决策上下文、已知限制 |

### Engineering Node Map 子表

定义本 Goal 下预期产生的工程节点类型及其约束。canonical 来源为 `docs/harness/artifact/control/node-type-registry.md`；Goal Charter 中列出的是本 Goal 实例化的子集。

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | enum | 节点类型：`feature` / `refactor` / `research` / `bugfix` / `docs` / `config` / `test` |
| `merge_required` | boolean | 是否必须合并到 mainline |
| `baseline_form` | enum | 基线固化形式：`commit-on-feature-branch` / `annotated-tag-or-report` / `explicit-declaration` 等 |
| `gate_criteria` | text | 关卡判定标准组合（implementation / validation / policy） |
| `if_interrupted_strategy` | enum | 中断处理策略：`checkpoint-or-recover` / `checkpoint-or-rollback` / `preserve-report-and-stop` |
| `expected_count` | integer | 预期产生的该类节点数量（可选，用于容量预估） |

### Node Dependency Graph

节点间依赖关系，格式：`source_type → target_type (reason)`。例如 `research → feature (调研结论驱动功能设计)`。

### Default Baseline Policy

- `if_worktrack_interrupted`: stash-and-tag / commit-with-note / explicit-declaration
- `if_no_merge`: document-alternative-traceability

## 消费者契约

以下 skill 以 Goal Charter 为输入源，按约定字段读取：

| 消费者 | 读取字段 | 用途 |
|--------|---------|------|
| `repo-init-goal-skill` | 全部 | 初始化生成 Charter |
| `repo-change-goal-skill` | 全部 | 目标变更时更新 Charter |
| `repo-status-skill` | `project_vision`, `success_criteria`, `system_invariants` | Repo 状态快照中对齐 Goal |
| `worktrack-init-skill` | `engineering_node_map`, `core_product_goals` | 初始化 worktrack 时绑定节点类型与基线策略 |

## 跨引用

- Engineering Node Map 的 canonical 类型定义见 `docs/harness/artifact/control/node-type-registry.md`
- Worktrack contract 中的 `Node Type` 字段必须与 Goal Charter 的 `engineering_node_map` 一致，见 `docs/harness/artifact/worktrack/contract.md`
- Goal 层的写入与回写流程见 `product/harness/skills/repo-init-goal-skill/SKILL.md`
