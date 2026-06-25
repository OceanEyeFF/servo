---
name: milestone-whitebox-check
description: 当 Milestone Gate 需要从内部实现视角检查跨 WT 集成路径、接口拼接、状态传递、依赖关系和架构对齐时，使用这个技能。它运行在隔离 SubAgent 中，可以阅读完整实现代码，但不能读取其他轴（blackbox/anticheat/composite）的 verdict。
---

# Milestone Whitebox 轴检查技能

## 概览

本技能实现 Milestone Gate 四轴检查架构中的 **whitebox 轴**（Layer 1 独立检查层），对应 [design-four-axis-skills.md](../../../../docs/harness/artifact/control/milestone-gate-aggregation.md) 中定义的 Skill 2。它从 milestone 的**内部实现视角**出发，检查跨 worktrack 的关键集成路径、接口拼接、状态传递、依赖关系和架构对齐。它是四个轴检查中的实现深度审查者——不同于 blackbox 轴的外部视角（只看合约和用户可见产出），whitebox 轴可以并且必须阅读完整实现代码来完成分析。

当 Milestone Gate orchestrator（`milestone-status-skill`）确认所有 worktrack 已闭环、需要收集 whitebox 轴证据以输入 Layer 2 aggregator 时，使用这个技能。

这个技能设计为在**隔离 SubAgent** 中运行。轴间隔离是架构上的硬约束：whitebox SubAgent 只能接收 whitebox 轴独享的输入材料，不能接收、看到或读取其他轴（blackbox / anticheat / composite）的 verdict。如果因为运行时限制必须在当前载体内执行，必须显式标记 `carrier_isolation_broken: true`。

它负责产出结构化的 `whitebox_verdict`，作为 milestone gate aggregator（[milestone-gate-aggregation.md](../../../../docs/harness/artifact/control/milestone-gate-aggregation.md) 定义的 composite_lane_rules）的输入之一。

## 何时使用

当需要从实现内部视角检查 milestone 的跨 WT 一致性时，使用这个技能：

- Milestone Gate orchestrator 确认 milestone 下所有 worktrack 已闭环（closeout record 已写入）
- 需要收集 whitebox 轴的独立证据，作为 Layer 2 aggregator 的输入
- 运行时支持 SubAgent 分派（或显式接受 current-carrier fallback 并标记隔离破损）
- 存在以下需要从代码层面判断的情况：
  - 两个或多个 WT 修改了同一模块或共享接口
  - WT 之间存在声明的依赖关系，需要验证接口契约是否真实对齐
  - 怀疑存在循环依赖或未声明的跨 WT 依赖
  - 需要确认实现是否遵循 repo 声明的架构分层规则
  - 需要评估跨 WT 关键集成路径的实现质量
- 输入材料已经齐备（WT contracts、完整 diffs、milestone artifact、架构规则），不存在必须等待的外部产物

## 工作流

1. **接收并验证输入完整性**：确认已收到 milestone artifact（purpose、acceptance_criteria）、所有已闭环 WT 的 contract（scope、impacted_modules）、WT 的完整 diff（可阅读代码），以及 repo 的 Engineering Node Map 或路径分层规则。任何缺失材料标记为 `missing_input` 并记录。
2. **确认轴间隔离**：检查输入包中是否包含其他轴（blackbox / anticheat / composite）的 verdict 或检查结果。若有泄露，必须标记 `isolation_guarantee: false`，记录泄露内容和来源，但仍继续本轴的独立分析（不因泄露而中止——但必须暴露）。
3. **识别跨 WT 集成面**：从各 WT 的 `impacted_modules` 和 `scope` 中提取交集——找出被多个 WT 修改的模块、文件或接口，形成集成分析矩阵。如果没有任何跨 WT 交集（所有 WT 修改互不重叠的模块），记录 `integration_surface: none` 并简化后续检查。
4. **执行五项检查（W1-W5）**：按 checklist 逐项检查，每项产出独立的 verdict + finding + evidence_refs。详见「检查清单与判据」节。
5. **构建依赖图**：从代码中的 import / reference / require / include 关系出发，构建 WT 节点之间的依赖图。检测是否存在：
   - 循环依赖（A→B→A 或更长的环）
   - 未声明的依赖（WT-B 依赖了 WT-A 的产物，但 WT-B 的 contract 未声明此依赖）
   - 声明的依赖未被实际引用（contract 中声明了依赖，但代码中无 import）
6. **综合输出**：将五项检查结果和依赖图综合为 `whitebox_verdict`，按「输出格式」节规定返回。
7. **停止**：不进入聚合、裁决或代码修复阶段。

### 检查清单与判据

| ID | 检查项 | 判据 | 执行方法 |
|----|--------|------|---------|
| W1 | **Interface contract consistency**：跨 WT 的共享接口是否一致？ | 接口定义（类型声明、函数签名、API schema、配置文件格式）与消费代码之间是否对齐。若 WT-A 定义了接口/合约、WT-B 消费了该接口，则检查 B 的消费代码是否符合 A 的合约。 | 1. 从 WT contracts 和 diffs 中提取接口定义和消费点；2. 对每个声明-消费对，对比参数类型、返回值、错误语义、前置条件；3. 对配置文件格式变更，检查写入方和读取方是否使用一致的结构。 |
| W2 | **State transition integrity**：跨 WT 的状态流转是否正确？ | 若多个 WT 共同操作或消费一个状态机（如 milestone pipeline 状态、worktrack lifecycle、deploy target 状态），检查：1) 各 WT 对状态的定义是否一致；2) 状态转移是否闭合（不会卡死在未定义状态）；3) WT 之间的交接点是否覆盖所有合法状态。 | 1. 从代码中提取状态机定义（enum、state machine table、lifecycle hook）；2. 为每个状态机构建跨 WT 转移图；3. 检测不可达状态、缺失转移、不一致的状态命名。 |
| W3 | **Dependency graph**：WT 之间是否有循环依赖或未声明的依赖？ | 基于代码中的实际 import/reference/require/include 构建有向图。合法依赖：已在 WT contract 中声明的依赖。违规：1) 循环依赖（有向环）；2) 未声明依赖（边存在但 contract 中无对应声明）；3) 幽灵声明（contract 声明了但代码中无实际引用）。 | 1. 解析每个 WT diff 中的 import 语句；2. 将 import 的目标文件映射到所属 WT（通过 impacted_modules）；3. 构建邻接矩阵并检测环；4. 与 WT contract 中的 `dependencies` 声明对比。 |
| W4 | **Architecture alignment**：实现是否符合声明的架构分层？ | 新增或修改的文件是否放在正确的目录层级。判据来源：repo 的路径分层规则（如 `docs/project-maintenance/foundations/root-directory-layering.md`）、Engineering Node Map、`docs/harness/` 中的架构约定。违规示例：业务逻辑文件出现在 `toolchain/`、文档正文出现在 `.agents/`、源码出现在 `.servo/`（非 runtime artifact）。 | 1. 提取每个 WT diff 中的新增文件和跨目录移动；2. 对每个文件，匹配其路径到声明的分层规则；3. 标记归属不清的文件（文件出现在未在分层规则中声明的目录）。 |
| W5 | **Implementation quality**：关键路径的实现质量是否可接受？ | 对跨 WT 的集成关键路径（W1-W4 中识别的高风险接口、状态转移、依赖边和架构边界点）执行代码审查。使用标准代码审查维度：错误处理、恢复路径、operator-facing 语义、资源管理、可维护性。注意：W5 不替代 per-WT 的 review-evidence（那是 WT 级 gate 的职责），而是只审查**跨 WT 的集成点**——两个 WT 的代码在集成处是否安全、正确、可恢复。 | 1. 从 W1-W4 结果中识别 critical 集成点（接口定义+消费、状态转移关键边、高权重依赖边、架构边界跨越点）；2. 对每个 critical 点阅读相关代码段；3. 按标准审查维度评估。 |

### 检查执行优先级

按依赖关系排序，前一阶段的结果作为后一阶段的输入：

```
W3（依赖图）──→ W1（接口一致性）──→ W2（状态流转）──→ W4（架构对齐）──→ W5（实现质量）
                    │                      │
                    └─ 依赖边提供接口上下文  └─ 状态定义提供转移参考
```

- W1-W4 必须全部执行，即使前一阶段结果较差
- W5 只对 W1-W4 中标记为 `soft_fail` 或 `hard_fail` 的集成点做深入审查；如果 W1-W4 全部 `pass` 且无跨 WT 集成面，W5 可标记为 `不适用`（需说明理由）
- 如果没有任何跨 WT 集成面（所有 WT 互不重叠），所有 W1-W5 标记为 `不适用`，verdict 为 `pass`，但必须记录 `integration_surface: none` 与理由

## 输出协议

- 先生成完整、详尽的 `whitebox_verdict` 报告，包含所有五项检查的结构化结果和依赖图
- 然后从完整报告中提取 `Control Signal` 层：`verdict`、`severity`、关键 `finding` 摘要
- 重复性上下文（如 WT contract 摘要、milestone artifact 全文）的唯一合法呈现形式是文件路径引用。内联全文复制的行为禁止发生
- 如果某个字段无实质内容，唯一合法行为是使用 `N/A` 或省略。用占位符填充的行为必须被阻断
- 每个 checklist item 的 `evidence_refs` 必须指向具体文件路径和行号范围，不得笼统写"见 diff"
- `Supporting Detail` 保留完整内容，只用于后续查阅，不纳入传递给 aggregator 的上下文

### 输出格式

```yaml
whitebox_verdict:
  axis: whitebox
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  integration_surface: cross_wt | none
  checklist_results:
    - check_id: W1
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      evidence_refs:
        - "path/to/file.ts#L10-L25 (interface definition)"
        - "path/to/consumer.py#L42-L58 (consumption point)"
      finding: "对接口 X 的定义与消费一致，参数类型和错误语义对齐。"
    - check_id: W2
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      evidence_refs:
        - "path/to/state_machine.go#L30-L55"
      finding: "..."
    - check_id: W3
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      evidence_refs: [...]
      finding: "..."
    - check_id: W4
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      evidence_refs: [...]
      finding: "..."
    - check_id: W5
      verdict: pass | soft_fail | hard_fail | blocked | not_applicable
      evidence_refs: [...]
      finding: "..."
  dependency_graph:
    nodes:
      - worktrack_id: "WT-xxx"
        impacted_modules: ["module_a", "module_b"]
      - worktrack_id: "WT-yyy"
        impacted_modules: ["module_b", "module_c"]
    edges:
      - from: "WT-yyy"
        to: "WT-xxx"
        type: import | interface_consumption | state_dependency | config_dependency
        declared: true | false
        files: ["path/to/consumer.ts#L15 (import)"]
  circular_dependencies: []  # 若存在：[{cycle: ["WT-a", "WT-b", "WT-a"], evidence: [...]}]
  undeclared_dependencies:
    - from: "WT-yyy"
      to: "WT-xxx"
      type: import
      evidence: ["path/to/file.ts#L15"]
  ghost_declarations:
    - worktrack_id: "WT-yyy"
      declared_dependency: "WT-zzz"
      finding: "contract 声明依赖 WT-zzz，但代码中无实际 import"
  carrier: subagent | current-carrier
  isolation_guarantee: true | false
  isolation_leak_detail: "N/A 或 描述泄露内容与来源"
  carrier_isolation_broken: true | false  # 仅当 carrier=current-carrier 时为 true
```

### verdict 判定规则

| 条件 | verdict |
|------|---------|
| 所有 W1-W5 为 `pass` 或 `not_applicable`（含 `integration_surface: none`） | `pass` |
| 任一 checklist item 为 `soft_fail`，但无 `hard_fail` 或 `blocked` | `soft_fail` |
| 任一 checklist item 为 `hard_fail` | `hard_fail` |
| 任一 checklist item 为 `blocked`（如关键输入缺失导致无法完成检查） | `blocked` |
| 存在循环依赖（不论其他项结果） | `hard_fail` |
| 存在未声明的依赖（1-2 个低风险边） | 降级为 `soft_fail`（若当前已是 `hard_fail` 则不变） |
| 存在未声明的依赖（3 个及以上，或任一涉及 critical WT） | `hard_fail` |

`severity` 映射：

- `pass` 且无风险信号 → `low`
- `soft_fail` 或 `pass` 但存在未声明依赖/幽灵声明 → `medium`
- `hard_fail` 或 `blocked` → `high`

### 依赖图构建细则

- **节点**：以 `worktrack_id` 为标识，附加 `impacted_modules` 列表
- **边类型**：
  - `import`：代码中的 import/reference/require/include
  - `interface_consumption`：WT-B 消费了 WT-A 定义的接口/合约
  - `state_dependency`：WT-B 的状态转移依赖 WT-A 设置的 state
  - `config_dependency`：WT-B 消费了 WT-A 写入的配置文件
- **声明状态**：`declared: true` 当该边在 WT-B 的 contract 中有对应依赖声明；否则 `false`
- **检测范围**：仅检测 WT 之间的依赖，WT 内部文件间的依赖不在本轴范围（那是 per-WT review 的职责）
- **循环依赖**：在依赖图上运行 DFS 检测有向环。记录完整环路径

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: `docs/harness/foundations/skill-common-constraints.md`。

本技能特有约束：

- **Permission boundary**：只读。可以为了分析目的阅读完整实现代码，但**禁止修改任何代码**。禁止生成修复建议、补丁或代码变更。输出的唯一合法形式是检查报告——不包含代码片段（证据引用除外）。
- **Isolation**：**禁止**接收或阅读其他轴（blackbox / anticheat / composite）的 verdict。若输入包中意外包含了其他轴的 verdict，必须：
  1. 标记 `isolation_guarantee: false`
  2. 在 `isolation_leak_detail` 中记录泄露内容和来源
  3. 继续完成本轴的独立分析（不因泄露而中止）
  4. 不将泄露信息用于本轴的判定
- **SubAgent requirement**：设计为在隔离 SubAgent 中运行。当 SubAgent 不可用时，fallback 到 current-carrier 执行必须：
  1. 标记 `carrier: current-carrier`
  2. 标记 `carrier_isolation_broken: true`
  3. 在当前载体内顺序执行——但不得因此降低检查标准或简化分析
- **No code generation**：本技能检查和报告，**绝不**生成或修改代码。即使发现应该修复的问题，唯一合法行为是记录在 finding 中并标记对应的 verdict 等级。产出修复建议、代码补丁或"推荐改法"的行为必须被阻断。
- W1-W4 的五项检查不得因前一阶段 verdict 较差而跳过后续阶段。所有五项必须全部执行（标记为 `not_applicable` 的项除外，必须有明确理由）。
- 依赖图构建必须基于代码中的**实际引用关系**，不能仅依赖 WT contract 中声明的依赖列表。contract 中的声明用于与实际情况对比，不是图构建的唯一来源。
- 当发现未声明依赖或循环依赖时，必须在 `finding` 中显式说明依赖的具体形式（import 语句、接口消费、配置依赖等）及其影响范围。笼统写"存在未声明依赖"的行为必须被阻断。
- 每个 checklist item 的 `evidence_refs` 必须引用具体文件路径和行号（或行号范围）。使用"见 diff"、"见 WT-A 的变更"等非具体引用的行为必须被阻断。
- W5（Implementation quality）只审查跨 WT 集成关键路径；审查范围扩大到单 WT 内部实现质量的行为必须被阻断（那是 per-WT review-evidence 的职责）。
- 从本技能输出直接进入 milestone gate 裁决或代码修复的行为必须被阻断。本技能的唯一合法下游消费者是 milestone gate aggregator（Layer 2）。
- 当运行时在 current-carrier 内执行且本载体可能已接触过其他轴信息时，不得声称 `isolation_guarantee: true`；必须标记 `carrier_isolation_broken: true`。
- 证据时效性：检查必须基于 milestone 当前 branch head 的最新代码。如果 WT diff 与当前 head 存在差异（如后续其他变更覆盖了 WT 的修改），必须标记 `stale_baseline_warning` 并说明差异。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `whitebox 轴检查报告`：

- `白盒检查触发条件`
- `输入材料接收摘要`
- `跨 WT 集成面分析`
- `检查清单执行结果`（W1-W5 每项独立结果）
- `依赖图`
- `整体判定结果`
- `返回 Milestone Gate Orchestrator`

结果中至少应包含以下字段或等价表达：

- `子代理模型`（SubAgent 模式或 current-carrier）
- `axis: whitebox`
- `verdict`（pass / soft_fail / hard_fail / blocked）
- `severity`（low / medium / high）
- `integration_surface`（cross_wt / none）
- `integration_surface_detail`
- `checklist_results[].check_id`（W1-W5）
- `checklist_results[].verdict`
- `checklist_results[].evidence_refs`
- `checklist_results[].finding`
- `dependency_graph.nodes`
- `dependency_graph.edges`
- `circular_dependencies`
- `undeclared_dependencies`
- `ghost_declarations`
- `carrier`（subagent / current-carrier）
- `isolation_guarantee`（true / false）
- `isolation_leak_detail`
- `carrier_isolation_broken`（true / false）
- `stale_baseline_warning`（若适用）
- `missing_input`（若适用）
- `需要人工复核`（若 whitebox 分析发现需要 programmer 判断的模糊边界）
- `如何审查`（指导 programmer 如何复核本报告）

## 资源

- 设计文档：`docs/harness/artifact/control/milestone-gate-aggregation.md` — 四轴检查架构总设计，Skill 2（whitebox）的定义
- 聚合合同：`docs/harness/artifact/control/milestone-gate-aggregation.md` — composite_lane_rules 中 whitebox 轴的 veto_power 和消费规则
- 公共约束：`docs/harness/foundations/skill-common-constraints.md` — 所有 Skill 的 C-1 至 C-7 公共约束
- 架构分层：`docs/project-maintenance/foundations/root-directory-layering.md` — 路径分层规则，用于 W4 架构对齐检查
- 运行协议：`docs/harness/foundations/Harness运行协议.md` — Harness 控制回路中 Milestone Gate 阶段的位置
- 编排者入口：`product/harness/skills/milestone-status-skill/SKILL.md` — Layer 2 orchestrator（消费本轴输出）
- 输出模板参考：`docs/harness/artifact/control/milestone-gate-aggregation.md` §五 composite_lane_rules — whitebox 轴在聚合中的 veto_power 和 weight_modifier 角色
