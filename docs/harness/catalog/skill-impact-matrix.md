---
title: "Skill Impact Matrix"
status: active
updated: 2026-05-14
owner: servo-kernel
last_verified: 2026-05-14
---

# Skill Impact Matrix

> Catalog boundary：本文件不是 skill inventory 正文，而是历史 Harness 合同变更对 canonical skills 的影响分析与同步追踪记录。可执行源仍以 [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md) 为准。

> 本轮 Harness 合同补强（WT-20260508-harness-contract-hardening）对 canonical skills 的影响分析。
>
> 本轮修改范围为 `docs/harness/` 合同层。`product/harness/skills/` 中的 skill 实现不在本次变更范围内。本 Matrix 记录该轮合同补强后已知的 skill 同步缺口。

## 本轮变更概述

T1-T5 在 `docs/harness/` 合同层完成了以下变更：

| 变更 | 范围 | 内容 |
|------|------|------|
| T1 | 运行协议 + control-state | 新增 Dispatch/Implement 边界定义、Handback 与交接锁（六-A）、Handback Guard 字段 |
| T2 | node-type-registry + worktrack + README | 创建 Node Type Registry，定义 7 种节点类型的默认规则（baseline_form / merge_required / gate_criteria / if_interrupted_strategy） |
| T3 | gate-evidence + plan-task-queue + worktrack-scope | 规范化 verdict/review_dimensions 字段、任务队列字段规范、状态转移矩阵 |
| T4 | dispatch-packet + worktrack + README | 创建 Dispatch Packet Schema，统一 Task Brief / Info Packet / Result 三层字段定义 |
| T5 | milestone + milestone-status-skill + control-state + README | 创建 Milestone Artifact 与 Milestone Status Skill catalog 入口 |

## 影响概览

| Skill | 影响等级 | 需要同步的合同变更 | 同步优先级 |
|-------|---------|-------------------|-----------|
| harness-skill | **medium** | 引用 `node-type-registry.md`（三轴模型 Artifact 轴）；引用 `dispatch-packet.md`（子代理分派阶段）；引用 `milestone.md`（传感器层）；对齐 `Harness运行协议` 六-A Handback 节已在 skill 十一节中覆盖，需确认字段一致性 | P1 |
| repo-status-skill | **medium** | 新增 `milestone.md` 作为 RepoScope 传感器输入源（milestone 定义中明确其为 RepoScope.Observe 的 sensor 输入）；补充 milestone_status 输出字段 | P1 |
| repo-whats-next-skill | **low** | 可选引用 `node-type-registry.md` 作为 `suggested_node_type` 的类型定义上游；Milestone 信号可影响 RepoScope.Decide 决策，需在判定逻辑中考虑 Milestone 完成/阻塞状态 | P2 |
| repo-refresh-skill | **low** | 可选引用 `node-type-registry.md` 作为基线策略默认值的权威来源；Milestone progress counter 更新触发条件（closeout 后检查） | P2 |
| close-worktrack-skill | **medium** | 将"基线固化策略（按节点类型）"内联表替换为对 `node-type-registry.md` 的引用；避免策略定义重复；确保 checkpoint_policy_match 判定使用 registry 默认值作为对比基准 | P1 |
| init-worktrack-skill | **medium** | 新增 `node-type-registry.md` 引用：当 Goal Charter 的 Engineering Node Map 给出节点类型但未指定具体字段值时，从 registry 继承 `baseline_form` / `merge_required` / `gate_criteria` / `if_interrupted_strategy` 默认值 | P1 |
| schedule-worktrack-skill | **medium** | 将 `分派交接包` 输出字段与 `dispatch-packet.md` 的 Dispatch Task Brief schema 对齐；引用 `node-type-registry.md` 获取节点策略默认值；确保 `dispatch_mode` 字段使用统一枚举值 | P1 |
| dispatch-skills | **high** | 核心消费者：全面对齐 `dispatch-packet.md` 三层 schema——Dispatch Task Brief 消费、Dispatch Info Packet 生成、Dispatch Result 消费；统一 `fallback_reason` 枚举值（`runtime fallback` / `permission blocked` / `dispatch package unsafe`）；引用 `node-type-registry.md` 确认 gate_criteria 与 baseline policy 来源 | P0 |
| gate-skill | **medium** | 将"按节点类型的判定差异"内联表替换为对 `node-type-registry.md` 的引用；使用 registry 作为 gate_criteria 默认值的权威来源（skill 已声明 "Node Type Registry 只提供默认标准"，但未给出 registry 路径）；确认 `review_dimensions` 五维度与 `gate-evidence.md` 定义一致 | P1 |
| recover-worktrack-skill | **low** | 可选引用 `node-type-registry.md` 获取 `if_interrupted_strategy` 默认值（当 Worktrack Contract 未显式指定时） | P2 |

## 详细分析

### 1. harness-skill（控制面入口）

**当前状态**：已体现大部分本轮合同概念（Dispatch/Implement 边界在二节、Handback 在十一节与十五节、Milestone 在输出字段中）。缺少对新正式 artifact 的显式引用。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 六、三轴模型 > Artifact 轴 | 列出 7 个正式对象，无 node-type-registry | 新增 `Node Type Registry` 条目，说明其定义所有 Worktrack 节点类型的默认规则，是 Goal Charter、Worktrack Contract 和 gate-skill 的统一引用上游 |
| 二、控制系统架构 > 分派子代理 | "打包任务/信息" 无正式 schema 引用 | 补充对 `dispatch-packet.md` 的引用，说明 Dispatch Task Brief / Info Packet / Result 三层格式 |
| 三、系统组件 > 传感器 | "Harness Control State 中的控制面信号" 无 Milestone 引用 | 新增 Milestone 作为 RepoScope 聚合传感器输入源，引用 `milestone.md` |
| 十-A、控制回路运行规范 > 状态估计 | 引用 control-state.md 的 Linked Formal Documents 等配置段 | 确认 Handback Guard 字段引用与 `control-state.md` 已更新的字段一致（handoff_state / last_handback_signature / handback_lock_active 等） |

### 2. repo-status-skill（RepoScope 状态观察器）

**当前状态**：已消费 Goal Charter、Repo Snapshot/Status、Harness Control State；检查 Engineering Node Map 完整性。但未将 Milestone 纳入传感器源。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 概览 > 传感器源 | 列出 3 个主要输入，无 Milestone | 新增 Milestone artifact 作为 RepoScope 传感器输入（符合 milestone.md 中"Milestone 是 RepoScope.Observe 的 sensor 输入"定义） |
| 预期输出 > 字段 | 包含 `goal_node_map_status` | 新增 `active_milestone`、`milestone_status` 字段，反映当前活跃 Milestone 及其状态 |

### 3. repo-whats-next-skill（RepoScope 决策器）

**当前状态**：已通过 Engineering Node Map 建议 `suggested_node_type`，但未引用 node-type-registry 作为类型定义来源。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 工作流 > Step 12 | "从 Goal Charter 的 Engineering Node Map 给出 suggested_node_type" | 补充：如需获取节点类型默认策略（baseline_form 等），从 `node-type-registry.md` 读取 |
| 判定逻辑 | 仅基于 Goal Charter 与 Snapshot 决策 | 考虑活跃 Milestone 的完成/阻塞状态对 RepoScope 决策的影响（milestone.md 定义"Milestone 完成/阻塞信号影响 RepoScope.Decide 的决策"） |

### 4. repo-refresh-skill（RepoScope 刷新器）

**当前状态**：已处理 close-worktrack 交接中的所有节点策略字段（baseline_branch、baseline_form、merge_required、checkpoint_policy_match）。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 信息包 > 基线验收状态 | `expected_baseline_form` 等字段来自 close handoff | 可选引用 `node-type-registry.md` 作为验证 `expected_baseline_form` 合理性的对比基准 |
| 工作流 | 未提及 Milestone progress 更新 | 在 closeout 后检查 active_milestone 的 progress_counter 是否需要更新（符合 milestone.md "Worktrack closeout 后 Milestone progress counter 更新"） |

### 5. close-worktrack-skill（WorktrackScope 收尾器）

**当前状态**：包含完整的"基线固化策略（按节点类型）"内联表，该表现在与 `node-type-registry.md` 内容重复。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 收尾约定 > 基线固化策略（按节点类型） | 内联 7 种节点类型的固化策略表 | 替换为对 `node-type-registry.md` 的引用，说明"节点类型默认策略以 Node Type Registry 为准；Worktrack Contract 可显式覆盖"。保留"若 Node Type 未定义，fallback 到最保守策略"规则 |
| 代码仓库刷新交接 > 节点策略 | `node_type`、`expected_baseline_form`、`merge_required` | 新增说明：expected_baseline_form 与 merge_required 的默认值来自 node-type-registry，contract 可覆盖 |

### 6. init-worktrack-skill（WorktrackScope 初始化器）

**当前状态**：从 Goal Charter 的 Engineering Node Map 确定节点类型并填充 contract 类型化字段，但缺少当 charter 未指定字段值时的默认来源。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 工作流 > Step 6 | "根据节点类型填充 contract 中的类型化字段：baseline_branch、baseline_form、merge_required、gate_criteria、if_interrupted_strategy" | 补充：当 Goal Charter 给出节点类型但未指定具体字段值时，从 `node-type-registry.md` 继承默认值；若 registry 中也未定义该类型，标记为 `node_type_undefined` 风险 |
| 资源 | "Goal Charter 中的 Engineering Node Map" | 新增 `node-type-registry.md` 作为类型默认值的回退来源 |

### 7. schedule-worktrack-skill（WorktrackScope 调度器）

**当前状态**：产出"分派交接包"（Dispatch Task Brief），包含 task brief 和 info packet 草稿。但字段结构未与正式 schema 对齐。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 工作流 > Step 6 | "分派交接包必须引用当前 Worktrack Contract 的 Node Type，并携带本轮适用的 gate_criteria 与 baseline policy" | 将分派交接包字段结构与 `dispatch-packet.md` 的 Dispatch Task Brief schema 对齐（worktrack_id、task_id、task_goal、scope、non_goals、acceptance_criteria、constraints、expected_output、dispatch_mode、rollback_hint）；确保 `dispatch_mode` 使用统一枚举值 `auto` / `delegated` / `current-carrier` |
| 预期输出 > 字段 | `分派任务简报草稿`、`分派信息包草稿` | 显式引用 `dispatch-packet.md#dispatch-task-brief` 作为 schema 来源 |
| 资源 | `templates/plan-task-queue.template.md` | 新增 `dispatch-packet.md` 作为分派包字段规范来源 |

### 8. dispatch-skills（WorktrackScope 分派器）

**当前状态**：已实现 dispatch mode 选择逻辑、task brief 消费、info packet 生成。但 packet 字段未与正式 schema 对齐。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 概览 | "构建限定范围任务简报和信息包" | 显式引用 `dispatch-packet.md` 作为三层 packet 的权威 schema 定义 |
| 工作流 > Step 5 | "复用交接包中的分派任务简报和分派信息包" | 字段对齐：Task Brief 字段名统一为 schema 定义（`task_goal` / `acceptance_criteria` / `constraints` / `expected_output` / `dispatch_mode`）；Info Packet 字段对齐（`goal` / `acceptance` / `allowed_artifacts` / `forbidden_boundaries` / `expected_output_format` / `evidence_format` / `context_files`） |
| 工作流 > Step 11 | "委派式子代理分派 / 当前载体运行时回退" | 统一 fallback_reason 枚举值：`runtime fallback` / `permission blocked` / `dispatch package unsafe`（与 dispatch-packet.md 一致） |
| 预期输出 > 字段 | 含 `交接包来源`、`分派包状态` 等 | 新增 `fallback_reason` 字段，对齐 dispatch-packet.md 的取值为英文枚举 |
| 资源 | 无 | 新增 `dispatch-packet.md` 作为分派 schema 权威来源 |

### 9. gate-skill（WorktrackScope 裁决器）

**当前状态**：包含"按节点类型的判定差异"内联表，已提及"Node Type Registry 只提供默认标准"但未给出具体路径。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 关卡判定规则 > 按节点类型的判定差异 | 内联 7 种节点类型的判定标准表 | 替换为对 `node-type-registry.md` 的引用；说明"节点类型默认 gate_criteria 以 Node Type Registry 为准；Worktrack Contract 可显式覆盖。若 gate_criteria 缺失，按 registry 默认值推导，并在关卡报告中记录 fallback 理由。" |
| 关卡判定交接 > 字段 | `review_dimensions: performance / architecture / security / quality / tests` | 确认与 `gate-evidence.md` 的 5 维度定义对齐（correctness / completeness / consistency / scope_boundary / structural_compliance）；评估是保留旧命名还是迁移到新标准维度 |
| 关卡信息包 | 无 registry 路径 | 新增 `节点类型注册表路径` 字段，引用 `node-type-registry.md` |

### 10. recover-worktrack-skill（WorktrackScope 恢复器）

**当前状态**：已引用 `if_interrupted_strategy` 从 Worktrack Contract 获取策略；恢复权限边界定义完整。

**需同步的具体内容**：

| 位置 | 当前内容 | 需要变更 |
|------|---------|---------|
| 恢复权限边界 > 重试 | "必须检查 if_interrupted_strategy 是否允许继续同一 worktrack" | 可选：当 Contract 未显式指定 `if_interrupted_strategy` 时，从 `node-type-registry.md` 获取节点类型默认策略作为 fallback |
| 恢复权限边界 > 刷新基准 | "如果 baseline_form 或 merge_required 与当前 checkpoint 状态不匹配" | 可选引用 `node-type-registry.md` 获取该节点类型的预期 baseline_form，作为不匹配判定的对比基准 |

## 同步优先级汇总

| 优先级 | Skill | 核心原因 |
|--------|-------|---------|
| **P0** | dispatch-skills | 核心消费者，必须全面对齐 `dispatch-packet.md` 三层 schema，统一 fallback_reason 枚举值 |
| **P1** | harness-skill | 控制面入口，需引用所有新增正式 artifact（node-type-registry / dispatch-packet / milestone） |
| **P1** | repo-status-skill | 需新增 Milestone 作为 RepoScope 传感器输入源 |
| **P1** | close-worktrack-skill | 内联表与 node-type-registry 重复，需替换为引用 |
| **P1** | init-worktrack-skill | 需添加 node-type-registry 作为类型默认值 fallback |
| **P1** | schedule-worktrack-skill | 分派交接包需与 dispatch-packet.md Task Brief schema 对齐 |
| **P1** | gate-skill | 内联表与 node-type-registry 重复；review_dimensions 命名需与 gate-evidence.md 对齐 |
| **P2** | repo-whats-next-skill | 可选：引用 node-type-registry + Milestone 信号考虑 |
| **P2** | repo-refresh-skill | 可选：引用 node-type-registry + Milestone progress 更新 |
| **P2** | recover-worktrack-skill | 可选：从 node-type-registry 获取 if_interrupted_strategy 默认值 |

## 未受影响的 Skill

以下已部署的 canonical skill 在本轮合同变更中未受影响（不涉及本轮的 artifact 引用变更或语义变更）：

| Skill | 原因 |
|-------|------|
| worktrack-status-skill | 其职责为 WorktrackScope 状态观察；本轮变更主要在 RepoScope 合同层和 Dispatch packet schema，不影响其核心逻辑 |
| review-evidence-skill | 其职责为收集 review 证据；本轮 gate-evidence.md 的 review_dimensions 重定义影响 gate-skill 汇总逻辑，不影响 evidence 收集本身 |
| test-evidence-skill | 同 review-evidence-skill |
| rule-check-skill | 其职责为策略维度检查；本轮变更不改变策略检查的内容范围 |
| generic-worker-skill | 作为执行载体，接收 dispatch-skills 生成的 info packet；执行逻辑本身不受 packet schema 变更影响 |
| doc-catch-up-worker-skill | 文档追平逻辑不受本轮 artifact 变更影响 |
| set-harness-goal-skill | Goal 设定逻辑不受本轮变更影响 |
| repo-change-goal-skill | Goal 变更控制逻辑不受本轮变更影响 |
| repo-append-request-skill | Append request 逻辑不受本轮变更影响 |
| milestone-status-skill | 本 skill 是 T5 新创建的 catalog 条目；其 contract 已在 `docs/harness/catalog/milestone/milestone-status-skill.md` 中定义，无需同步 |

## 验证命令

实现阶段完成后，运行以下验证确认同步完整性：

```bash
# 检查 skill 文件中的 artifact 引用是否完整
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py

# 检查 closeout acceptance gate
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/closeout_acceptance_gate.py --json
```

---

## Milestone Pipeline 升级影响（2026-05-10）

Phase 0 + Phase 1 引入了 Milestone Pipeline 机制，对以下 skills 产生实际变更：

| Skill | 实际变更 | 影响等级 |
|-------|---------|---------|
| init-milestone-skill | **新建** — RepoScope.Init 算子，milestone 创建/upsert/激活 | new |
| harness-skill | Milestone 状态写回机制（10.7）+ Pipeline 恢复路径（十二） | medium |
| milestone-status-skill | `purpose_achieved` 操作化判定 + Writeback 指令 + pipeline_advancement 输出 | medium |
| repo-whats-next-skill | **重构** — milestone-first 三路分支决策（步骤 12），替代直接 Goal→Worktrack | high |
| init-worktrack-skill | milestone 绑定验证 + contract 模板新增 Milestone Binding 段 | medium |
| repo-refresh-skill | worktrack-backlog 写入 milestone_id + milestone-backlog 刷新 | low |
| repo-status-skill | milestone-backlog sensor 源 + pipeline 观测输出字段 | low |

### 新正式对象

| 对象 | 位置 | 说明 |
|------|------|------|
| Milestone Pipeline / Backlog | `docs/harness/artifact/repo/milestone-backlog.md` | Pipeline 运行时 artifact，upsert 语义 |
| init-milestone-skill | `product/harness/skills/init-milestone-skill/SKILL.md` | RepoScope.Init 算子 |
| Milestone Backlog runtime | `.aw/repo/milestone-backlog.md` | 运行时实例（gitignore） |

### 概念变更

- Milestone: 从单例 → Pipeline 队列（多个 planned，单个 active）
- RepoScope.Decide: 从 Goal→Worktrack 直接推理 → milestone-first 推理
- Worktrack: 从独立创建 → active milestone 派生（携带 milestone_id）
- Milestone 验收: 增加 `purpose_achieved` 操作化标准（signal/criterion 逐条验证）

---

## Milestone Work-Collection 升级影响（2026-05-11）

Work-Collection 设计引入了 `milestone_kind` 字段（`goal-driven` / `work-collection`），实现两类 milestone 在验收模型、创建来源和完成行为上的分化。

### 历史设计来源

该升级来自历史设计分析；当前 docs truth 不再保留未升格的 analysis/design 文档。长期可引用内容已经落在下方 artifact contract 与 skill 影响记录中。

### 合同变更

| 文件 | 变更 | 影响等级 |
|------|------|---------|
| `docs/harness/artifact/control/milestone.md` | 新增 `milestone_kind` 字段定义 + Milestone 类型分化表 + 验收模型更新（双重/单重） | high |
| `docs/harness/artifact/repo/milestone-backlog.md` | 字段约定新增 `milestone_kind` + work-collection 自动 superseded 维护约定 | medium |

### Skill 变更

| Skill | 实际变更 | 影响等级 |
|-------|---------|---------|
| milestone-status-skill | 工作流步骤 9-11 按 `milestone_kind` 分化验收行为（goal-driven 双重验收 / work-collection 单重验收 + 声明跳过 purpose_achieved）；handback_required 按 kind 分化；输出字段新增 `milestone_kind`、`verification_model_used` | medium |
| init-milestone-skill | 工作流新增 work-collection 创建路径（自动生成名称/signals/kind=work-collection/最低 priority/直接激活）；新增追加 worktrack 时的信号覆盖判定步骤（fully_covered/partially_covered/not_covered）；输出字段新增 `signals_coverage_reviewed`、`coverage_verdict`、`milestone_kind` | high |
| repo-whats-next-skill | 步骤 12 第一分支（active_milestone 为空）扩展：语义匹配已有 milestone + 内聚性判断 + work-collection 路由；输出字段新增 `milestone_kind`；硬约束新增 work-collection 合法例外 | high |
| harness-skill | 10.7.6 Milestone 状态写回按 `milestone_kind` 分化（work-collection 不触发 handback/自动 superseded/自动 pipeline 推进）；10.2 算子选择新增 work-collection 路由差异；十二恢复策略新增 Work-Collection 专属恢复路径（`defer-and-close`、`dissolve-collection`） | medium |

### 新概念

| 概念 | 说明 |
|------|------|
| `milestone_kind` | enum: `goal-driven` / `work-collection`，决定验证模型与生命周期行为 |
| goal-driven | programmer 定义的、有语义含量的 milestone；双重验收；handback 需 programmer 验收 |
| work-collection | harness 自动创建的无内聚工作容器；单重验收（仅 worktrack_list_finished）；自动完成不触发 handback |
| 信号覆盖判定 | 向 goal-driven milestone 追加 worktrack 时，AI 辅助判定新 worktrack 的验收是否被已有 completion_signals 覆盖；决策权在 programmer |
| 内聚性判断 | repo-whats-next-skill 在无 active milestone 时评估待处理工作是否存在语义内聚，决定走 goal-driven 还是 work-collection 路由 |

### 向后兼容

- `milestone_kind` 默认值为 `goal-driven`，已有 milestone 无需迁移
- 新增字段不破坏现有解析逻辑
- work-collection milestone 不阻塞 goal-driven milestone 的 pipeline 推进

### 残余问题

| 问题 | 严重程度 | 处理策略 |
|------|---------|---------|
| work-collection milestone 堆积 | 低 | completed 后自动 superseded；backlog 视图可折叠 |
| 信号覆盖判定 AI 非确定性 | 低（已降级） | 所有判定结果需 programmer 确认；假阳性代价从"静默绕过门控"降级为"多余确认交互" |
| work-collection 内单个 worktrack 阻塞 | 非新问题 | 新增 `defer-and-close` 恢复路径 |
| worktrack 从 work-collection 迁移到 goal-driven | 远期 | 非本次范围 |

---

## Milestone v0.3 Update 影响（2026-05-11）

本轮 `milestone v0.3 update` 在合同/协议层新增了 threshold、Milestone Gate、稳定性规则和激活前 brief，直接影响 milestone 相关技能的输入输出与 handback 边界。

### 合同变更

| 文件 | 变更 | 影响等级 |
|------|------|---------|
| `docs/harness/artifact/control/milestone.md` | 新增 `completion_threshold_pct`（默认 `100`）；明确 `signal_satisfaction_pct` 与 `criteria_pass_pct` 均需达到 threshold 才算 `purpose_achieved`；新增 Milestone Gate、稳定性规则与激活前 brief 合同 | high |
| `docs/harness/foundations/Harness运行协议.md` | 将 Milestone Gate 插入 `worktrack closeout -> purpose_achieved` 之间；新增 goal-driven 激活前确认边界与 milestone 定义改写后的重新评估规则 | high |
| `docs/harness/catalog/milestone/milestone-status-skill.md` | 新增 threshold / Milestone Gate / reevaluation 输出语义与调用时机 | high |
| `docs/harness/catalog/milestone/init-milestone-skill.md` | 新增 activation brief、confirmation_required、ownership review 与 milestone_reevaluation_required 约定 | high |

### Skill 变更

| Skill | 实际变更 | 影响等级 |
|-------|---------|---------|
| milestone-status-skill | 需在 goal-driven milestone 上先执行 Milestone Gate（黑盒/白盒/反作弊），再按 threshold 计算 `purpose_achieved`；signals / criteria / threshold 改写时输出重新评估标记 | high |
| init-milestone-skill | 激活前必须生成结构化 brief 并等待 programmer 确认；仅追加归属当前 milestone 的 worktrack 时不触发重评估，否则给出路由建议 | high |
| harness-skill | 需把 goal-driven milestone 激活 brief 当作正式 handback/确认边界；在全部 worktrack closeout 后插入 Milestone Gate 再决定是否推进 pipeline | medium |
| repo-whats-next-skill | 向当前 milestone 追加 worktrack 前，需先判断归属；不归属时应建议归入其他 milestone 或创建新 milestone | medium |

### 新概念

| 概念 | 说明 |
|------|------|
| `completion_threshold_pct` | goal-driven milestone 的完成阈值，默认 `100` |
| `signal_satisfaction_pct` | `completion_signals` 的满足率；需与 `criteria_pass_pct` 一同达到 threshold |
| `criteria_pass_pct` | `acceptance_criteria` 的通过率；需与 `signal_satisfaction_pct` 一同达到 threshold |
| `Milestone Gate` | 位于所有相关 worktrack 关闭后、`purpose_achieved` 前的 milestone 级集成验证层，包含黑盒/白盒/反作弊检测 |
| milestone stability rule | 修改 signals / criteria / threshold 必须重新评估 milestone；仅追加已确认归属的 worktrack 不触发该重评估 |
| activation brief | goal-driven milestone 激活前的结构化规划简报与确认边界 |

### 向后兼容

- `completion_threshold_pct` 默认值为 `100`，已有 goal-driven milestone 在未显式声明时按既有全量通过语义处理。
- work-collection milestone 继续采用单重验收模型；`Milestone Gate`、threshold 和激活前阻塞确认均不改变其自动激活/自动完成语义。
- 新增规则不引入第三 Scope；Milestone Gate 仍属于既有 `RepoScope` / `WorktrackScope` 分层中的 repo 级集成验证步骤。
