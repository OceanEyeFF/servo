---
title: "Gate Evidence"
status: active
updated: 2026-05-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Gate Evidence

为状态转移裁决提供证据。最少应包含 review/validation/policy 三类证据面。review evidence 使用 `review_profile` 按风险选择 lane，而非对所有变更均固定使用四路 SubAgent。四个可用 review lanes 为：`static-semantic-review`（静态语义解释）、`test-review`（测试 review）、`project-security-review`（security review）、`complexity-performance-review`（代码复杂度和性能 review）。无法分派所选 lanes 时记录 fallback 原因。还需记录每条证据面的 freshness/缺失状态、残余风险、上游约束信号、gate intake readiness、`verdict` 和后续动作。

## review_profile 字段

`review_profile` 决定本轮 review evidence 的 lane 选择。

| Profile | Lanes | 适用场景 |
| --- | --- | --- |
| `light` | `static-semantic-review` | 文档小修、入口文字小改、无执行语义变化 |
| `standard` | `static-semantic-review`, `test-review` | 普通 skill/docs/test 修改，风险集中在正确性和验收覆盖 |
| `risky` | `static-semantic-review`, `test-review`, `project-security-review` | dispatch、authority、path safety、adapter/deploy 边界 |
| `deep` | `static-semantic-review`, `test-review`, `project-security-review`, `complexity-performance-review` | control-state、gate、installer/publish、destructive action、安全边界 |

选择规则：

- docs-only 小修默认 `light`，但必须说明安全/性能/测试维度不适用的理由。
- 普通 canonical skill 修改默认 `standard`。
- dispatch、authority、path governance、adapter/deploy 安全边界默认 `risky`。
- control-state、gate、installer/publish、destructive action 默认 `deep`。
- `deep` 等价于原四路 SubAgent 覆盖；无法真实并行分派时保留 lane 覆盖状态和 fallback 原因。

## Node Type

gate_criteria 因 node_type 而异，具体规则见 `worktrack-gate-skill` §按节点类型的判定差异。node_type 注册表见 `docs/harness/artifact/control/node-type-registry.md`。

| Node Type | gate_criteria 覆盖维度 | 说明 |
|-----------|----------------------|------|
| research | review | 仅 review 维度，不强制 test/policy |
| docs | review, policy | 文档类需 review + 策略合规 |
| feature | review, test, policy | 全维度覆盖 |
| fix | review, test | 修复类需 review + 测试验证 |
| refactor | review, test, policy | 重构需 review + 测试 + 策略合规 |
| config | review, policy | 配置变更需 review + 策略合规 |
| ops | review, test | 运维类需 review + 验收测试 |

> 完整 per-node-type gate criteria 映射以 `worktrack-gate-skill` §按节点类型的判定差异 为准。

## Verdict 字段定义

Gate 推演结果以 `verdict` 字段记录，必须为以下四种值之一：

| Verdict | 语义 | 推进规则 |
|---------|------|----------|
| `pass` | 所有校验面（review/validation/policy）均通过，未发现任何需阻塞的问题 | 允许直接推进至下一状态（dispatching 或 closing） |
| `soft-fail` | 存在可接受的低严重度问题，不影响核心功能、安全或架构一致性 | 可带条件推进，但必须记录吸收理由、问题清单及后续跟踪计划 |
| `hard-fail` | 存在不可接受的中/高严重度问题，涉及正确性、安全性、结构性或合同违约 | 必须进入 Recover 阶段（retry/rollback/split_worktrack/refresh_baseline/replan），不可强行推进 |
| `blocked` | 缺失必要证据（如某证据面未完成）或外部依赖未满足，无法做出判定 | 保持当前上下文等待；若为可恢复阻塞源（缺失证据可重采集、外部依赖可重获取），可触发 Recover 机制（retry/refresh_baseline/replan）；依赖满足后重新 intake |

Verdict 判定流程：

1. 收集三类证据面（review / validation / policy），检查每条证据的 freshness 和缺失状态
2. 逐面评估是否存在问题及严重度
3. 汇总所有发现后按上述四种 verdict 做出判定
4. 记录 verdict、判据摘要、吸收项（如有）和后续动作

## 低严重度吸收规则

### 严重度分级

| 严重度 | 定义 | 示例 | 可吸收 |
|--------|------|------|--------|
| 低 | 不影响功能、安全、架构一致性的表面问题 | 拼写错误、格式不一致、非关键文档 freshness 轻微延迟（不超过 3 天） | 是 |
| 中 | 可能影响可维护性、可读性或局部正确性，但不会导致系统级故障 | 缺少边界注释、非核心路径测试覆盖不足、命名不规范 | 否，触发 hard-fail |
| 高 | 影响功能正确性、安全性、数据完整性或架构合同 | 逻辑错误、安全漏洞、路径/分层违规、合同未满足 | 否，触发 hard-fail |

> **严重度符号映射**：部分 skill 使用 P1/P2/P3 符号体系。映射关系：`P1 = high`、`P2 = medium`、`P3 = low`。本 contract 中统一使用 low/medium/high。

### 吸收规则

1. 低严重度问题可在 `soft-fail` verdict 中吸收（即在 soft-fail 下标注问题但允许推进）
2. 中/高严重度问题**不得吸收**，必须触发 `hard-fail`
3. 每项吸收必须记录以下字段：
   - `issue_description`：问题描述
   - `severity`：严重度评级（low / medium / high）
   - `absorption_rationale`：吸收理由（为什么可以带条件推进）
   - `follow_up_plan`：后续跟踪计划（何时、如何修复）
   - `follow_up_deadline`：跟踪截止时间（可选，但建议给出）
4. 低严重度问题的升级围栏：仅当低严重度发现跨越至少两个校验面（如同时出现于 review 和 validation 面），或形成系统性模式并实质性降低对验收或恢复的信心时，才应从 `soft-fail` 升级为 `hard-fail`。停留在单一层面且未形成威胁的低严重度发现必须保留在残留风险中。纯数量阈值的升级方式已被废止，详见 [worktrack-gate-skill 关卡判定规则](../../../product/harness/skills/worktrack-gate-skill/SKILL.md#关卡判定规则)。
5. 吸收项必须在下一轮 verify gate 中被重新检查；未在截止时间前修复的吸收项在下一轮自动升级为中严重度

### 吸收记录示例

```yaml
verdict: soft-fail
absorbed_issues:
  - issue_description: "CHANGELOG 未更新本次变更记录"
    severity: low
    absorption_rationale: "本次变更为内部重构，对外接口无变化，CHANGELOG 更新可推迟至下一轮"
    follow_up_plan: "在下一轮 closeout 前补充 CHANGELOG"
    follow_up_deadline: "2026-05-12"
  - issue_description: "plan-task-queue.md 中一处任务描述存在拼写错误"
    severity: low
    absorption_rationale: "不影响任务理解和执行"
    follow_up_plan: "下次修改该文件时一并修复"
```

## review_dimensions 字段

Gate evidence 中的每条 review 证据面应覆盖以下标准维度。每个维度独立评分（pass / soft-fail / hard-fail / blocked）：

| 维度 | 名称 | 含义 | 检查要点 |
|------|------|------|----------|
| `correctness` | 正确性 | 代码/文档的正确性，是否实现了声明的目标 | 逻辑无错误、边界条件正确处理、与验收标准一致 |
| `completeness` | 完整性 | 是否覆盖所有验收标准，无遗漏 | 对照 contract 中的 acceptance criteria 逐项检查 |
| `consistency` | 一致性 | 与现有架构、模式和约定的协调性 | 命名规范、接口模式、数据流方向与现有设计对齐 |
| `scope_boundary` | 范围边界 | 是否越出声明范围，引入未授权的变更 | 变更集是否严格限定在 plan 声明的范围内 |
| `structural_compliance` | 结构性合规 | 路径/分层/治理规则的符合性 | 文件放置于正确目录、遵循分层规则、满足治理基线 |

四个可用 SubAgent lane 的 review 覆盖映射：

| SubAgent | 主要覆盖维度 |
|----------|-------------|
| static-semantic-review | correctness, consistency, structural_compliance |
| test-review | correctness, completeness |
| project-security-review | correctness, scope_boundary, structural_compliance |
| complexity-performance-review | correctness, consistency |

Gate 维度到 SubAgent Lane 的映射（用于 per-milestone gate 四轴判定时交叉引用）：

| Gate Dimension (gate-skill) | Nearest SubAgent Lane | Coverage |
|-----------------------------|----------------------|----------|
| performance | complexity-performance-review | Direct |
| architecture | static-semantic-review (structural_compliance) | Partial |
| security | project-security-review | Direct |
| quality | static-semantic-review (correctness, consistency) | Partial |
| tests | test-review | Direct |

每个 SubAgent 返回的 review 结果应包含每个维度的评分和具体发现。Gate 汇总时按维度取最严格评分（任一 SubAgent 报告 hard-fail 则该维度 hard-fail）。
