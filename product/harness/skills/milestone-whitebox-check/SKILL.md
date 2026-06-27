---
name: milestone-whitebox-check
description: 当 Milestone Gate 需要按 target_type 从内部实现视角检查程序目标的结构/控制流/数据流/状态传递/接口/依赖/架构路径，或对非程序产物执行替代结构审查时，使用这个技能。它运行在隔离 SubAgent 中，可以阅读完整实现代码，但不能读取其他轴（blackbox/anticheat/composite）的 verdict。
---

# Milestone Whitebox 轴检查技能

## 概览

本技能实现 Milestone Gate 四轴检查架构中的 **whitebox 轴**（Layer 1 独立检查层），对应 design-four-axis-skills.md 中定义的 Skill 2。它先识别 milestone 的 `target_type`，再从 milestone 的**内部实现视角**选择检查方法：程序目标执行真实的软件白盒语义检查，即基于内部结构和实现细节的控制流、数据流、状态传递、接口合约、依赖路径和架构对齐分析；非程序目标执行 artifact-appropriate 的替代结构审查或记录不适用，而不是假装执行了软件白盒测试。

它是四个轴检查中的实现深度审查者——不同于 blackbox 轴的外部视角（只看合约和用户可见产出），whitebox 轴在 `program_code` 或 `mixed` 的程序切片中可以并且必须阅读完整实现代码来完成分析。外部行为场景属于 blackbox 轴；whitebox 只在需要追踪验收条件到内部结构时引用其上游声明，不把外部可观察行为测试当作本轴通过依据。

当 Milestone Gate orchestrator（`milestone-status-skill`）确认所有 worktrack 已闭环、需要收集 whitebox 轴证据以输入 Layer 2 aggregator 时，使用这个技能。

这个技能设计为在**隔离 SubAgent** 中运行。轴间隔离是架构上的硬约束：whitebox SubAgent 只能接收 whitebox 轴独享的输入材料，不能接收、看到或读取其他轴（blackbox / anticheat / composite）的 verdict。如果因为运行时限制必须在当前载体内执行，必须显式标记 `carrier_isolation_broken: true`。

它负责产出结构化的 `whitebox_verdict`，作为 milestone gate aggregator（milestone-gate-aggregation.md 定义的 composite_lane_rules）的输入之一。

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

## Target-Type 路由

Whitebox 轴不得把所有 milestone 都当成可执行程序来验收。每次运行必须先读取或推断 `target_type`、`target_type_source` 与 whitebox 轴适用性，并记录在输出中。

| target_type | whitebox 处理方式 |
|-------------|-------------------|
| `program_code` | 适用。必须阅读必要的完整实现代码，并基于内部结构证据执行白盒检查：控制流路径、数据流路径、状态传递路径、接口合约定义/消费、依赖路径、架构边界和关键实现不变量。 |
| `non_program_artifact` | 通常不执行软件白盒测试。改为输出 `substituted` 或 `not_applicable`，并说明替代结构审查方法，例如文档结构审查、合同字段一致性、术语/交叉引用一致性、governance rule conformance、operator procedure traceability 或专业审查。 |
| `mixed` | 分片处理。对程序切片执行完整 whitebox 结构分析；对非程序切片记录替代结构审查或不适用结论；整体 verdict 不得把非程序不适用项计为程序白盒测试通过。 |
| `unknown` | 默认 `blocked`。只有在 milestone artifact、WT contract 或 closeout 中有可追溯证据支持类型推断时，才允许记录 `target_type_source` 后继续。 |

`target_type` 不改变轴间边界：whitebox 只能检查内部结构、实现路径和代码/产物内部一致性。用户可观察行为场景、CLI/API 输出、UI 截图和外部回归场景属于 blackbox 轴；whitebox 可将 milestone acceptance 或 completion signal 作为 traceability 输入，但不得用外部行为场景替代内部结构证据。

## 工作流

1. **接收并验证输入完整性**：确认已收到 milestone artifact（purpose、acceptance_criteria、target_type）、所有已闭环 WT 的 contract（scope、impacted_modules）、WT 的完整 diff（程序切片可阅读代码），以及 repo 的 Engineering Node Map 或路径分层规则。任何缺失材料标记为 `missing_input` 并记录。
2. **确认轴间隔离**：检查输入包中是否包含其他轴（blackbox / anticheat / composite）的 verdict 或检查结果。若有泄露，必须标记 `isolation_guarantee: false`，记录泄露内容和来源，但仍继续本轴的独立分析（不因泄露而中止——但必须暴露）。
3. **执行 target_type 路由**：记录 `target_type_source`、whitebox 轴适用性和预期方法。`program_code` 进入结构/实现检查；`non_program_artifact` 进入替代结构审查或不适用；`mixed` 分片；`unknown` 缺少可追溯推断时 `blocked`。
4. **为程序目标建立内部结构证据图**：从完整实现代码、完整 diff、contract 和架构规则中抽取 `control_flow_paths`、`data_flow_paths`、`state_transfer_paths`、`interface_contract_paths`、`dependency_paths`、`architecture_boundaries` 与关键 `implementation_invariants`。证据必须引用具体文件与行号。
5. **识别跨 WT 集成面**：从各 WT 的 `impacted_modules`、`scope`、完整 diff 和内部结构证据图中提取交集——找出被多个 WT 修改或共同依赖的模块、文件、接口、状态、配置、依赖边或架构边界，形成集成分析矩阵。如果没有任何跨 WT 交集（所有 WT 修改互不重叠的模块），记录 `integration_surface: none` 并简化后续检查。
6. **执行五项检查（W1-W5）**：按 checklist 逐项检查，每项产出独立的 verdict + finding + evidence_refs。详见「检查清单与判据」节。
7. **构建依赖图**：从代码中的 import / reference / require / include 关系出发，构建 WT 节点之间的依赖图。检测是否存在：
   - 循环依赖（A→B→A 或更长的环）
   - 未声明的依赖（WT-B 依赖了 WT-A 的产物，但 WT-B 的 contract 未声明此依赖）
   - 声明的依赖未被实际引用（contract 中声明了依赖，但代码中无 import）
8. **综合输出**：将 target_type 路由结果、内部结构证据图、五项检查结果和依赖图综合为 `whitebox_verdict`，按「输出格式」节规定返回。
9. **停止**：不进入聚合、裁决或代码修复阶段。

### 检查清单与判据

对 `program_code`，W1-W5 必须消费内部结构证据图。对 `non_program_artifact`，代码结构检查项应按路由结果输出 `substituted` 或 `not_applicable`，并说明替代结构审查证据；不得把不适用项写成白盒测试通过。

| ID | 检查项 | 判据 | 执行方法 |
|----|--------|------|---------|
| W1 | **Interface contract consistency**：跨 WT 的共享接口是否一致？ | 接口定义（类型声明、函数签名、API schema、配置文件格式）与消费实现之间是否对齐。若 WT-A 定义了接口/合约、WT-B 消费了该接口，则检查 B 的消费代码或产物结构是否符合 A 的合约。 | 1. 从 WT contracts、完整 diff 和实现代码中提取接口定义与消费点；2. 对每个声明-消费对，对比参数类型、返回值、错误语义、前置条件、配置字段和 schema；3. 对非程序切片，替代为合同字段、章节结构或术语引用的一致性审查。 |
| W2 | **Control/Data/State flow integrity**：控制流、数据流与状态传递是否正确？ | 程序切片中，关键分支、错误路径、数据来源/变换/落点和状态转移是否闭合且一致。若多个 WT 共同操作一个状态机、数据模型或生命周期，检查定义、转移、消费和异常路径是否覆盖所有合法状态。 | 1. 从实现代码提取控制流分支、数据流路径、状态机定义（enum、state table、lifecycle hook）和调用链；2. 为关键路径构建跨 WT flow map；3. 检测不可达分支、缺失错误路径、数据字段断裂、缺失转移、不一致状态命名；4. 对非程序切片，替代为过程步骤、章节依赖或规则链路的一致性审查。 |
| W3 | **Dependency graph and dependency paths**：WT 之间是否有循环依赖、未声明依赖或不真实声明？ | 基于代码中的实际 import/reference/require/include、配置读取、接口消费和状态依赖构建有向图。合法依赖：已在 WT contract 中声明且由实现证据支撑的依赖。违规：1) 循环依赖；2) 未声明依赖；3) 幽灵声明；4) 合同依赖方向与实现依赖方向冲突。 | 1. 解析每个 WT diff 和相关实现文件中的引用关系；2. 将引用目标映射到所属 WT 或共享模块；3. 构建邻接矩阵并检测环；4. 与 WT contract 的 `dependencies` 声明对比；5. 对非程序切片，替代为交叉引用/规范依赖图审查。 |
| W4 | **Architecture alignment**：实现是否符合声明的架构分层？ | 新增或修改的代码、脚本、文档或 runtime artifact 是否放在正确目录层级，且跨层调用方向符合 repo 声明的架构边界。判据来源：repo 路径分层规则、Engineering Node Map、声明的架构约定。 | 1. 提取每个 WT diff 中的新增文件、跨目录移动和跨层引用；2. 对每个文件与引用边匹配声明分层规则；3. 标记归属不清、源代码落入 state/deploy target、文档真相落入 deploy target 或工具逻辑落错层的问题。 |
| W5 | **Implementation quality on structural critical paths**：关键内部路径的实现质量是否可接受？ | 对 W1-W4 中识别的高风险接口、控制流分支、数据流路径、状态传递、依赖边和架构边界点执行代码审查。使用标准代码审查维度：错误处理、恢复路径、operator-facing 语义、资源管理、可维护性、内部不变量维护。W5 不替代 per-WT review-evidence，只审查**跨 WT 或 milestone 级结构关键路径**。 | 1. 从 W1-W4 结果中识别 critical structural path；2. 对每个 critical 点阅读相关实现代码段；3. 检查错误/恢复路径、边界条件、内部不变量和维护成本；4. 对非程序切片，替代为关键规则链、章节结构或 procedure traceability 的专业审查。 |

### 检查执行优先级

按依赖关系排序，前一阶段的结果作为后一阶段的输入：

```
W3（依赖图）──→ W1（接口一致性）──→ W2（控制/数据/状态流）──→ W4（架构对齐）──→ W5（关键路径实现质量）
                    │                      │
                    └─ 依赖边提供接口上下文  └─ flow map 提供转移与数据参考
```

- W1-W4 必须全部执行，即使前一阶段结果较差
- W5 只对 W1-W4 中标记为 `soft_fail` 或 `hard_fail` 的集成点做深入审查；如果 W1-W4 全部 `pass` 且无跨 WT 集成面，W5 可标记为 `不适用`（需说明理由）
- 对 `program_code`，如果没有任何跨 WT 集成面（所有 WT 互不重叠），W1-W5 可标记为 `not_applicable`，verdict 可为 `pass`，但必须记录 `integration_surface: none`、target_type 路由结果和理由
- 如果 target_type 为 `non_program_artifact` 且没有程序结构可审查，相关代码白盒项必须输出 `substituted` 或 `not_applicable`，不得把替代审查写成软件白盒测试 `pass`

## 输出协议

- 先生成完整、详尽的 `whitebox_verdict` 报告，包含 target_type 路由、内部结构证据图、五项检查的结构化结果和依赖图
- 然后从完整报告中提取 `Control Signal` 层：`verdict`、`severity`、关键 `finding` 摘要
- 重复性上下文（如 WT contract 摘要、milestone artifact 全文）的唯一合法呈现形式是文件路径引用。内联全文复制的行为禁止发生
- 如果某个字段无实质内容，唯一合法行为是使用 `N/A` 或省略。用占位符填充的行为必须被阻断
- 每个 checklist item 的 `evidence_refs` 必须指向具体文件路径和行号范围，不得笼统写"见 diff"
- `Supporting Detail` 保留完整内容，只用于后续查阅，不纳入传递给 aggregator 的上下文

### 输出格式

```yaml
whitebox_verdict:
  axis: whitebox
  verdict: pass | soft_fail | hard_fail | blocked | not_applicable
  severity: low | medium | high
  target_type: program_code | non_program_artifact | mixed | unknown
  target_type_source: "milestone-artifact.md#target_type"
  axis_applicability_state: applicable | substituted | not_applicable | split | blocked
  expected_method: structural_whitebox_analysis | artifact_structure_review | split_by_slice | blocked_pending_type
  substituted_by:
    - method: "artifact_structure_review | policy_conformance | traceability_review | professional_review | N/A"
      scope: "non-program slice or N/A"
      evidence_refs:
        - "path/to/evidence.md#L10-L25"
  integration_surface: cross_wt | none
  internal_structure_evidence:
    - evidence_id: "WB-STRUCT-001"
      target_slice: "program slice or non-program slice"
      analysis_method: control_flow | data_flow | state_transfer | interface_contract | dependency_path | architecture_boundary | code_review | artifact_structure_review
      implementation_refs:
        - "path/to/file.py#L10-L42"
      internal_path_or_invariant: "critical branch, data path, state transition, dependency edge, architecture boundary, or artifact rule chain"
      expected_internal_property: "N/A or expected structural property"
      observed_internal_property: "N/A or observed structural property"
      covered_by_wt:
        - "WT-xxx"
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
  checklist_results:
    - check_id: W1
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/file.ts#L10-L25 (interface definition)"
        - "path/to/consumer.py#L42-L58 (consumption point)"
      finding: "对接口 X 的定义与消费一致，参数类型和错误语义对齐。"
    - check_id: W2
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/state_machine.go#L30-L55"
      finding: "..."
    - check_id: W3
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs: [...]
      finding: "..."
    - check_id: W4
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs: [...]
      finding: "..."
    - check_id: W5
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
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
        type: import | interface_consumption | control_flow | data_flow | state_dependency | config_dependency | architecture_dependency
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
| `target_type=unknown` 且无法可追溯推断，或 `axis_applicability_state=blocked` | `blocked` |
| 轴明确不适用且理由完整，`axis_applicability_state=not_applicable` | `not_applicable` |
| 所有适用 W1-W5 为 `pass`，且 `substituted` 项有替代结构审查证据（含 `integration_surface: none`） | `pass` |
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
- `not_applicable` 且理由完整 → `low`

### 依赖图构建细则

- **节点**：以 `worktrack_id` 为标识，附加 `impacted_modules` 列表
- **边类型**：
  - `import`：代码中的 import/reference/require/include
  - `interface_consumption`：WT-B 消费了 WT-A 定义的接口/合约
  - `control_flow`：WT-B 的分支、调用链或错误路径依赖 WT-A 的入口或实现路径
  - `data_flow`：WT-B 的数据来源、转换、字段语义或落点依赖 WT-A 的产物
  - `state_dependency`：WT-B 的状态转移依赖 WT-A 设置的 state
  - `config_dependency`：WT-B 消费了 WT-A 写入的配置文件
  - `architecture_dependency`：WT-B 通过跨层调用、目录边界或运行时 artifact 依赖 WT-A 的结构位置
- **声明状态**：`declared: true` 当该边在 WT-B 的 contract 中有对应依赖声明；否则 `false`
- **检测范围**：仅检测 WT 之间的依赖，WT 内部文件间的依赖不在本轴范围（那是 per-WT review 的职责）
- **循环依赖**：在依赖图上运行 DFS 检测有向环。记录完整环路径

## 硬约束

遵循本包内最小公共约束 C-1 至 C-8：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现；C-8 canonical skill package 必须自洽，不依赖包外路径进行运行时语义。

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
- **Target type explicitness**：输出必须包含 `target_type`、`target_type_source`、`axis_applicability_state` 和 `expected_method`。缺少 `target_type` 且无法从已批准产物可追溯推断时，整体 verdict 必须为 `blocked`。
- **Program-code structural evidence**：当 `target_type=program_code` 或 `mixed` 的程序切片存在时，必须输出 `internal_structure_evidence`。证据至少覆盖适用的控制流、数据流、状态传递、接口合约、依赖路径、架构边界或关键实现审查项；只有外部行为场景、文件列表或 WT 摘要不足以让 whitebox 通过。
- **Non-program substitution boundary**：当 `target_type=non_program_artifact` 或 `mixed` 的非程序切片存在时，软件代码白盒项只能输出 `substituted` / `not_applicable` 或失败/阻塞。`substituted` 必须有替代结构审查方法和证据引用；`not_applicable` 不等于 `pass`，不得被当作软件白盒测试通过计入整体结论。
- **Blackbox boundary**：用户可观察行为场景、CLI/API 输出、UI 截图、外部回归场景和 operator-visible results 只能作为 traceability context；不得作为 whitebox 的内部结构证据。需要判断外部行为是否满足验收时，必须交给 blackbox 轴。
- **Canonical source / deploy target boundary**：本技能的 canonical source 位于 `product/harness/skills/milestone-whitebox-check/SKILL.md`。`.agents/skills/milestone-whitebox-check/SKILL.md` 与 `.claude/skills/milestone-whitebox-check/SKILL.md` 是分发/部署目标；同步应由明确的 deploy/adapter 流程或后续授权 worktrack 承接，不得在本轴检查运行中修改。
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
- `Target-Type 路由结果`（类型、来源、适用性、预期方法、替代/不适用说明）
- `内部结构证据图`（程序切片列控制流、数据流、状态传递、接口、依赖、架构和实现不变量；非程序切片列替代结构审查）
- `跨 WT 集成面分析`
- `检查清单执行结果`（W1-W5 每项独立结果）
- `依赖图`
- `整体判定结果`
- `返回顶层 Harness / Milestone Gate Aggregator`

结果中至少应包含以下字段或等价表达：

- `子代理模型`（SubAgent 模式或 current-carrier）
- `axis: whitebox`
- `verdict`（pass / soft_fail / hard_fail / blocked / not_applicable）
- `severity`（low / medium / high）
- `target_type`（program_code / non_program_artifact / mixed / unknown）
- `target_type_source`
- `axis_applicability_state`（applicable / substituted / not_applicable / split / blocked）
- `expected_method`
- `substituted_by`
- `internal_structure_evidence`
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

- Milestone Gate 聚合合同 — 四轴检查架构总设计与 whitebox 轴定义
- 路径分层规则 — 用于 W4 架构对齐检查
- milestone-status-skill — Layer 2 orchestrator（消费本轴输出）
