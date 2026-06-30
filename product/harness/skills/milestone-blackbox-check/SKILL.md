---
name: milestone-blackbox-check
description: 当 milestone gate 需要按 target_type 从外部视角（用户可观察行为场景、跨 WT 集成、回归风险，或非程序产物的替代验收）对 milestone 做隔离检查，且不得阅读完整实现代码时，使用这个技能。它是 Milestone Gate 四轴架构中 Layer 1 的 blackbox 轴，运行在隔离 SubAgent 中。
---

# Milestone Blackbox 检查技能

## 概览

本技能实现 Milestone Gate 四轴架构中 Layer 1 的 **blackbox 轴**检查，是 Milestone Gate 四轴 Skills 与两层编排设计定义的四个独立轴检查 Skill 之一。它先识别 milestone 的 `target_type`，再从 **milestone 外部视角**选择验收方法：程序目标检查最终用户看到的结果、跨 worktrack 集成行为和回归风险；非程序目标记录替代验收或不适用结论，而不是假装执行了软件黑盒测试。

核心原则：**不阅读完整实现代码**。本技能只消费 WT 的 contract、evidence、closeout summary、diff summary（文件变更摘要）和可观察行为证据，不做代码级审查。代码级审查由 whitebox 轴（`milestone-whitebox-check`）负责。

本技能与 `milestone-whitebox-check`、`milestone-anticheat-check`、`milestone-composite-check` 共同构成 Milestone Gate 的四轴检查层。四轴之间**严格隔离**——每个轴的 SubAgent 任务包不得包含其他轴的 verdict。

当 `milestone-status-skill`（Layer 2 orchestrator）需要在 milestone 所有 WT 闭环后，从外部集成视角检查 milestone 的交付质量时，使用这个技能。它产出一份结构化的 `blackbox_verdict`，供 Layer 2 aggregator 聚合到 milestone_gate_verdict。

## 何时使用

当满足以下条件时使用这个技能：

- 当前 milestone 下所有 active WT 已闭环（每个 WT 有 single-acceptance verdict + closeout record）
- `milestone-status-skill` 确认 worktrack 列表 finished，可以进入 milestone gate 检查
- 需要按 `target_type` 从外部用户或 operator 视角评估：跨 WT 集成是否一致、completion_signals 是否有对应产出、是否有回归风险
- 检查必须隔离运行，不能看到其他轴的 verdict
- 不需要阅读完整实现代码——如果检查需要理解代码内部，应委托给 whitebox 轴

以下情况不适用：

- Milestone 下还有 active WT 未闭环 → 应返回 `not_ready`，由 orchestrator 等待
- 需要逐行代码审查 → 应使用 `milestone-whitebox-check`
- 需要检测证据伪造（mock abuse / self-review bias 等）→ 应使用 `milestone-anticheat-check`
- 需要复合验收 lane 评估（code-review / feature-completeness 等）→ 应使用 `milestone-composite-check`
- 需要对单个 WT 做 gate 判定 → 应使用 `worktrack-gate-skill`
- 当前处于 worktrack scope 而非 milestone scope → 不适用

## Target-Type 路由

Blackbox 轴不得把所有 milestone 都当成可运行软件来验收。每次运行必须先读取或推断 `target_type`、`target_type_source` 与 blackbox 轴适用性，并记录在输出中。

| target_type | blackbox 处理方式 |
|-------------|-------------------|
| `program_code` | 适用。必须构建外部可观察行为场景，再用这些场景检查程序是否能以用户、operator、CLI、API 或集成面可见的方式满足验收。 |
| `non_program_artifact` | 通常不执行软件黑盒测试。改为输出 `substituted` 或 `not_applicable`，并说明替代验收方法，例如文档/合同审阅、operator simulation、政策一致性检查、交叉引用完整性或专业审查。 |
| `mixed` | 分片处理。对程序切片执行外部行为场景检查；对非程序切片记录替代验收或不适用结论；整体 verdict 不得把非程序不适用项计为程序测试通过。 |
| `unknown` | 默认 `blocked`。只有在 milestone artifact、WT contract 或 closeout 中有可追溯证据支持类型推断时，才允许记录 `target_type_source` 后继续。 |

`target_type` 不改变轴间边界：blackbox 只能检查外部可观察行为和交付表面。内部结构、代码路径、接口拼接细节、状态传递、依赖方向和实现一致性属于 whitebox 轴。

## 工作流

1. **验证就绪状态**：确认 milestone 下所有 WT 已闭环。若有 active WT，返回 `not_ready` 并列出未闭环 WT。
2. **载入最小输入集**：精确载入 milestone artifact、`target_type` / `axis_applicability` 信息、所有闭环 WT 的 closeout record、single-acceptance verdict、WT diff summary 和外部可观察行为证据。不得载入完整 diff 或实现代码。
3. **建立隔离上下文**：确认当前运行环境（SubAgent 或 current-carrier）。记录 `carrier` 和 `isolation_guarantee`。如果检测到其他轴 verdict 注入上下文，立即标记 `isolation_guarantee: false` 并记录泄漏来源。
4. **执行 target_type 路由**：记录 `target_type_source`、blackbox 轴适用性和预期方法。`program_code` 进入行为场景检查；`non_program_artifact` 进入替代/不适用验收；`mixed` 分片；`unknown` 缺少可追溯推断时 `blocked`。
5. **为程序目标构建外部行为场景矩阵**：每个场景至少包含 `scenario_id`、触发者、输入/前置条件、可观察表面、期望输出、证据引用、回归期待和覆盖 WT。场景必须来自 milestone 的 completion_signals / acceptance_criteria / WT closeout，不得从实现代码倒推。
6. **执行五项 blackbox 检查**（见下文「检查 checklist」）：
   - B1: Cross-WT integration consistency
   - B2: External behavior scenario coverage
   - B3: External regression scenario assessment
   - B4: External consistency with repo conventions
   - B5: Completeness gap analysis
7. **为每项检查收集证据**：每条 finding 必须附带 `evidence_refs`（引用的文件路径或 artifact ref）。缺失证据必须显式暴露，不能当作隐式通过。
8. **产生分项 verdict**：每项检查独立给出 `pass | soft_fail | hard_fail | blocked | substituted | not_applicable`。`blocked` 表示该检查无法执行（如输入缺失），需要上层干预；`substituted` 和 `not_applicable` 只用于 target_type 路由允许的非程序切片。
9. **综合整体 verdict**：按以下规则从五项分项 verdict 推导整体 blackbox verdict：
   - 任何一项 `blocked` → 整体 `blocked`
   - 任何一项 `hard_fail` → 整体 `hard_fail`
   - 任一项 `soft_fail` → 整体 `soft_fail`（除非已有 `hard_fail` 或 `blocked`）
   - `substituted` / `not_applicable` 不能单独推导为 `pass`；只有适用切片全部 pass 且替代验收无失败时，整体才可为 `pass`
   - 全部适用项 `pass` → 整体 `pass`
10. **产出结构化输出**：按「预期输出」格式生成 `blackbox_verdict`。
11. **在响应中停止**：不得进入 aggregator 计算、gate 判定、恢复决策或代码修改。

## 检查 Checklist

对 `program_code`，B1-B5 必须消费外部行为场景矩阵。对 `non_program_artifact`，B2/B3 等运行时行为项应按路由结果输出 `substituted` 或 `not_applicable`，并说明替代验收证据；不得把不适用项写成测试通过。

### B1: Cross-WT Observable Integration Consistency

**问题**：WT 之间对外暴露的 contract、入口或交付表面是否一致？

如果一个 WT-A 定义了外部 contract、入口、CLI/API 表面、operator workflow 或 artifact 输出，另一个 WT-B 消费了该交付，B 的可观察行为是否与 A 的约定保持一致？本项只使用声明合约、closeout 摘要和可观察证据，不审查内部调用链。

**判据**：

- 扫描所有 WT 的 contract 中的 `interface_contracts`、`module_contracts`、`external_surfaces` 或等价字段
- 对比 WT-A 的合约定义（声明入口、文件路径、数据结构、CLI/API 响应或 artifact 输出）与 WT-B closeout record 中的 `changed_files` / `diff_summary` / observable evidence
- 对 `program_code`，把跨 WT 合约映射到 B2 的行为场景，确认消费者场景能观察到生产者声明的交付
- 检查是否存在：WT-B 未覆盖 WT-A 声明的外部表面、WT-B 消费了 WT-A 未声明的表面、声明响应/输出与可观察证据不一致

**证据来源**：

- WT contract（`interface_contracts`、`module_contracts`）
- WT closeout record（`changed_files`、`diff_summary`）
- Milestone artifact（`worktrack_dependencies` 或等价依赖声明）
- B2 behavior scenario matrix（仅限 `program_code` 或 `mixed` 的程序切片）

**分项 verdict 规则**：

- `pass`：所有声明的跨 WT 外部表面一致，无遗漏消费，无未声明消费；程序场景能观察到声明交付
- `soft_fail`：存在轻微不一致（如命名差异但不影响行为），或依赖 WT 的 contract 未显式声明外部表面但 closeout 显示合理消费
- `hard_fail`：存在外部集成断裂（WT-A 定义入口/输出但 WT-B 未覆盖、或消费了不存在/不匹配的入口/输出）
- `blocked`：缺少必要的 contract 文件或 closeout record，无法完成检查

### B2: External Behavior Scenario Coverage

**问题**：从用户或 operator 视角，milestone 声明的 completion_signals 是否已经被外部可观察行为场景覆盖，并且每个场景都有可追溯证据？

Milestone artifact 中的 `completion_signals` 声明了"用户能看到什么变化"。当 `target_type=program_code` 时，本检查必须把每个 signal 转成一个或多个行为场景，用场景输入和可观察输出验证程序交付，而不是只统计文件变更覆盖。

**判据**：

- 提取 milestone artifact 中的 `target_type`、`completion_signals`、`acceptance_criteria` 和 WT closeout 的 `completion_signals_trace`
- 对 `program_code`，为每个 signal 建立行为场景，场景必须包含：
  - `scenario_id`
  - `user_or_operator_trigger`
  - `input_or_precondition`
  - `observable_surface`（UI / CLI / API / log / file output / integration behavior 等）
  - `expected_observable_result`
  - `evidence_refs`
  - `regression_expectation`
  - `covered_by_wt`
- 检查每个场景是否有外部证据支撑，例如命令输出、API 响应、截图、日志片段、验收测试摘要、operator simulation 记录或 closeout 中明确列出的可观察行为
- 对 `non_program_artifact`，记录替代验收方法和证据；若没有可运行软件表面，输出 `substituted` 或 `not_applicable`
- 对 `mixed`，分别输出程序切片场景和非程序切片替代验收

**证据来源**：

- Milestone artifact（`purpose`、`completion_signals`、`acceptance_criteria`）
- 每个 WT 的 closeout record（`changed_files`、`completion_signals_trace`）
- 每个 WT 的 single-acceptance verdict（`verdict`、`critical_failure`）
- WT gate evidence 中的外部验证摘要（命令输出、截图、CLI/API 示例、operator simulation 结果等）

**分项 verdict 规则**：

- `pass`：所有适用的程序 completion_signals 都有外部行为场景，场景证据可追溯，且覆盖 WT 的 single-acceptance verdict 为 pass
- `soft_fail`：所有适用 signals 有场景覆盖，但部分场景证据偏弱、间接，或覆盖 WT 的 single-acceptance 为 soft_fail
- `hard_fail`：存在适用的程序 completion_signal 没有行为场景覆盖，或场景期望与实际可观察结果冲突，或覆盖 WT 的 single-acceptance 为 hard_fail
- `blocked`：缺少 `target_type`、completion_signals、acceptance_criteria 或 WT closeout 中的必要 trace，且无法做可追溯推断
- `substituted`：非程序切片已用 artifact-appropriate 方法验收，并有替代证据
- `not_applicable`：非程序切片没有可运行黑盒表面，且已说明不适用原因

### B3: External Regression Scenario Assessment

**问题**：任一 WT 的变更是否可能破坏其他 WT 已声明的外部可观察结果？

检查每个 WT 的变更文件集、依赖声明和行为场景是否存在交叉影响，评估潜在的外部回归风险。本检查可以使用文件摘要定位风险面，但不得通过阅读完整实现代码判断内部正确性。

**判据**：

- 为每个 WT 构建变更文件集（从 closeout record 的 `changed_files` 或 diff summary 提取）
- 构建跨 WT 引用矩阵：对于每个文件，列出哪些 WT 变更了它、哪些 WT 依赖它
- 对 `program_code`，把风险映射回 B2 的行为场景，确认共享文件、依赖文件或基础设施变更是否可能改变 CLI/API 响应、用户流程、日志/文件输出或集成行为
- 检测风险模式：
  - **共享文件变更**：同一文件被多个 WT 修改 → 可能有 merge 冲突或逻辑覆盖
  - **依赖文件变更**：WT-A 变更了 WT-B 的依赖文件 → 可能破坏 B 的行为
  - **基础设施文件变更**：shared config、common utility、build script 等被修改 → 影响范围大

**证据来源**：

- 所有 WT 的 closeout record（`changed_files`）
- 所有 WT 的 diff summary（文件变更摘要）
- WT contract（`impacted_modules`、`dependencies`）
- Repo 路径分层规则（见 Goal Charter 的 Engineering Node Map 与路径分层定义）

**分项 verdict 规则**：

- `pass`：没有任何文件被多个 WT 修改，且所有变更文件不被其他 WT 依赖；程序场景没有外部回归风险
- `soft_fail`：存在共享文件变更或多 WT 依赖同一文件，但外部行为场景证据显示风险可控或非冲突
- `hard_fail`：存在明确的外部回归风险——同一逻辑单元/接口/配置项被多个 WT 以不同方向修改，且会影响 CLI/API 响应、用户流程、operator 工作流或集成行为
- `blocked`：closeout record 缺少 changed_files，无法完成文件级分析

### B4: External Consistency with Repo Conventions

**问题**：Milestone 产出是否与 repo 现有结构和约定一致？

检查所有 WT 新增的文件路径是否遵循 repo 的分层规则，新引入的字段是否与现有字段语义兼容。

**判据**：

- 提取所有 WT closeout record 中的 `new_files`
- 对照 repo 路径分层规则检查每个新文件是否落在正确的层级目录：
  - `product/` 是否放业务代码、`docs/` 是否放文档、`toolchain/` 是否放脚本工具
  - 是否有文件放在了 `.servo/`、`.agents/`、`.claude/` 等被禁止产出的 state layer
- 检查新引入的配置字段或 API 字段是否与现有字段语义冲突（如重名但含义不同）
- 检查 milestone 产出是否保持 canonical source → deploy target 的声明关系；deploy target 不得被反向当作 source truth

**证据来源**：

- 所有 WT closeout record（`new_files`）
- Repo 路径分层规则（可通过 checkpoint 或 known rules 引用）
- Milestone artifact（`purpose`）
- 各 WT contract（`scope`）

**分项 verdict 规则**：

- `pass`：所有新文件路径符合分层规则，无字段语义冲突
- `soft_fail`：存在路径边缘情况（如新目录归属有争议但不破坏现有规则），或字段命名可改进但不造成歧义
- `hard_fail`：新文件落在禁止产出层（state layer），或新字段与现有字段语义冲突（同名不同义）
- `blocked`：无法获取路径分层规则或缺乏足够的路径信息

### B5: Completeness Gap Analysis

**问题**：是否存在 completion_signals 声明了但没有程序行为场景、WT 覆盖或替代验收证据的空洞？是否存在 milestone 级的缺失证据？

本检查构建 signal → WT / scenario / substitute 覆盖矩阵，并检测跨维度缺失。B5 与 B2 互补：B2 关注"用户能否看到"，B5 关注"验收覆盖是否完整"。

**判据**：

- 构建 signal → WT / scenario / substitute 覆盖矩阵：行为 completion_signal 一行，列为每个 WT、行为场景或替代验收是否覆盖该 signal
- 检测：
  - **空行**：某个 signal 无任何 WT 覆盖
  - **弱覆盖**：某个 signal 只有低权重 WT（如 docs）覆盖，但 milestone 要求更高权重或程序行为场景
  - **替代缺口**：非程序 signal 声明了 substituted，但缺少替代方法、替代证据或验收结果
  - **证据缺口**：覆盖 WT 的 gate evidence 中是否有缺失维度（如某个 WT 没有 test evidence）
- 按 milestone 的 `aggregation_rules.weight_rules` 检查覆盖 WT 的权重是否满足该 signal 的最低要求

**证据来源**：

- Milestone artifact（`completion_signals`、`aggregation_rules`）
- 所有 WT 的 closeout record（`completion_signals_trace`）
- 所有 WT 的 single-acceptance verdict（`verdict`）
- 所有 WT 的 gate evidence（`implementation_gate`、`validation_gate`、`policy_gate`——仅读取 verdict 结论，不展开完整内容）
- B2 behavior scenario matrix 或替代验收说明

**分项 verdict 规则**：

- `pass`：所有适用 signals 有充分覆盖（程序 signal 有行为场景，非程序 signal 有替代验收证据），覆盖 WT 权重满足 milestone 要求，无跨维度证据缺口
- `soft_fail`：所有 signals 有覆盖但部分覆盖 WT 权重偏低、场景证据偏弱，或存在非关键的证据维度缺失
- `hard_fail`：存在 completion_signal 完全空覆盖，关键程序 signal 无行为场景，或关键非程序 signal 缺少替代证据
- `blocked`：缺少 `target_type`、aggregation_rules 或 completion_signals 定义，无法完成分析
- `substituted`：该项只覆盖非程序切片，且替代验收证据完整
- `not_applicable`：该项对当前目标类型无意义，且原因明确；不得计为 pass

## Blackbox 检查约定

每次运行这个技能时，都使用同一套限定范围约定格式。

### Blackbox 检查任务简报

- `触发条件`：milestone 下所有 WT 已闭环
- `检查目标`：按 target_type 从外部视角验证 milestone 的跨 WT 集成质量、程序行为场景或非程序替代验收
- `当前里程碑`：milestone ID 和 purpose 摘要
- `target_type 路由`：`program_code | non_program_artifact | mixed | unknown`，来源、适用性和预期方法
- `检查范围`：所有闭环 WT 的 contract、evidence、closeout record、diff summary、可观察行为证据和替代验收证据
- `排除范围`：完整实现代码、其他轴 verdict、单个 WT 的代码质量（属 whitebox）、单个证据可信度（属 anticheat）
- `检查项`：B1-B5
- `隔离约束`：不得接收或读取其他轴 verdict
- `完成信号`：产出结构化 blackbox_verdict

### Blackbox 检查信息包

- `输入产物`：milestone artifact、所有闭环 WT 的 contract / single-acceptance verdict / gate evidence / closeout record / diff summary
- `target_type 信息`：`target_type`、`target_type_source`、`axis_applicability.blackbox`、`expected_method`
- `里程碑约定摘要`：milestone 的 purpose、completion_signals、acceptance_criteria
- `WT 列表`：所有闭环 WT 的 ID、node_type、verdict 摘要
- `依赖关系`：WT 之间的声明依赖（从 contract 的 dependencies 字段提取）
- `文件变更矩阵`：每个 WT → 变更文件列表（从 closeout record 和 diff summary 提取）
- `信号覆盖矩阵`：每个 completion_signal → 覆盖的 WT 列表
- `行为场景矩阵`：对 `program_code` 和 `mixed` 的程序切片列出 scenario_id、触发、输入、可观察表面、期望输出、证据、回归期待和覆盖 WT
- `替代验收说明`：对 `non_program_artifact` 和 `mixed` 的非程序切片列出 substituted / not_applicable 状态、替代方法和证据
- `input_gap_classification`：显式区分缺少 `target_type`、`aggregation_rules`、`completion_signals_trace` 或 behavior scenario inputs 的输入缺口，与真实外部行为场景执行失败
- `路径分层规则引用`：已知的 repo 分层规则
- `已知风险`：从 milestone artifact 或 WT closeout 中已声明风险

## 硬约束

遵循本包内最小公共约束 C-1 至 C-8：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现；C-8 每个 canonical skill package 必须自洽，不依赖包外路径进行运行时语义。

本技能特有约束：

1. **权限边界（只读）**：本技能只做检查与报告，不得修改任何代码、contract、evidence 或 artifact。任何形式的代码改写行为必须返回 `blocked`。
2. **不得读取完整实现代码**：本技能只消费 WT diff summary（文件变更摘要），不得读取完整 diff 内容或实现代码源文件。如果某项检查需要阅读完整代码才能判断，将其标记为 `blocked` 并建议委托给 whitebox 轴，而不是绕过隔离规则去读代码。
3. **轴间隔离（Isolation Guarantee）**：本技能运行在隔离 SubAgent 或 current-carrier 上下文中，不得接收或读取其他三轴（whitebox / anticheat / composite）的 verdict。如果检测到其他轴 verdict 被注入当前上下文，必须立即：
   - 标记 `isolation_guarantee: false`
   - 在 `finding` 中记录泄漏来源和内容摘要
   - 若泄漏内容可能实质性影响本轴判断，将该检查项标记为 `blocked` 并说明泄漏污染
4. **SubAgent 要求**：本技能设计运行在隔离 SubAgent 中。当 SubAgent 不可用（`subagent_dispatch_shell = unavailable`），可降级为 current-carrier sequential 执行，但必须：
   - 标记 `carrier: current-carrier`
   - 标记 `carrier_isolation_broken: true`（因为 current-carrier 可能在同进程中看到了其他轴的输出）
   - 在 `isolation_guarantee` 中记录降级原因
   - 若声称已 spawned SubAgent，必须记录 `parent_runtime_dispatch_record_ref`、`spawned_subagent_record_ref`、`carrier_instance_id` 和 `isolation_boundary`。缺少这些 linkage 的 spawned-axis claim 必须标记为 ambiguous/non-pass；current-carrier 不得 masquerade 为 SubAgent，除非同时记录具体 runtime boundary violation。
5. **不得进入后续阶段**：本技能产出 verdict 后立即停止。从本技能直接跳到 aggregator 计算、gate 判定、恢复决策、worktrack 创建或代码修改的行为必须返回 `blocked`。唯一合法的下一步是将输出交给 orchestrator（milestone-status-skill）。
6. **缺失输入必须暴露**：缺少完成检查所必需的任何输入（如 milestone 无 completion_signals、WT 无 closeout record 等）时，唯一合法行为是将对应检查项标记为 `blocked` 并说明缺失内容。假定缺失数据为 pass 的行为必须返回 `blocked`。
6a. **input_gap 不等于行为失败**：当缺少 `target_type`、`aggregation_rules`、`completion_signals_trace` 或 behavior scenario inputs 时，必须在 `input_gap_classification` 中标记 `input_gap_status: input_gap` 或 `mixed_input_gap_and_behavior_failure`，并列出对应布尔字段。未执行或无法构造场景时，不得把结果描述为外部行为 hard_fail；只有已经构造并执行/观察到 scenario 的实际不符合，才可标记 `behavior_failure_present: true`。
7. **证据引用必须具体**：每条 finding 的 `evidence_refs` 必须是可追溯的文件路径或 artifact ref（如 `WT-xxx/closeout-record.md`、`milestone-artifact.md#completion_signals`）。不得出现无法定位的模糊引用（如"综合所有 WT 来看"）。
8. **输出必须包含完整的五项检查结果**：即使某项检查因输入不足被 `blocked`，也必须显式输出该项的 verdict 和 finding，不得省略。跳过某项检查的行为必须返回 `blocked`。
9. **target_type 必须显式化**：输出必须包含 `target_type`、`target_type_source`、`axis_applicability_state` 和 `expected_method`。缺少 `target_type` 且无法从已批准产物可追溯推断时，整体 verdict 必须为 `blocked`。
10. **程序目标必须有行为场景**：当 `target_type=program_code` 或 `mixed` 的程序切片存在时，B2 必须输出 behavior scenario matrix。只有文件变更覆盖、代码路径解释或内部实现摘要，不足以让 B2 通过。
11. **非程序目标不得伪装成运行时测试**：当 `target_type=non_program_artifact` 或 `mixed` 的非程序切片存在时，运行时黑盒项只能输出 `substituted` / `not_applicable` 或失败/阻塞。`not_applicable` 不等于 `pass`，不得被当作测试通过计入整体结论。
12. **白盒边界不可跨越**：如果判断需要内部结构、完整代码、调用链、状态传递或依赖方向分析，必须标记为 `blocked` 或把风险建议交给 whitebox 轴；不得在 blackbox 轴内补做白盒审查。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `Blackbox 检查报告`：

- `Blackbox 检查目标`
- `输入接收状态`（哪些输入已就绪、哪些缺失）
- `Target-Type 路由结果`（类型、来源、适用性、预期方法、替代/不适用说明）
- `轴间隔离声明`（isolation guarantee、是否检测到泄漏）
- `行为场景矩阵或替代验收说明`（程序目标列场景，非程序目标列替代方法）
- `分项检查结果`（B1-B5，每项包含 verdict、evidence_refs、finding，适用时包含 scenario_results）
- `整体 Blackbox Verdict`
- `风险摘要与建议`

结果必须包含以下结构化 YAML：

```yaml
blackbox_verdict:
  axis: blackbox
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  target_type: program_code | non_program_artifact | mixed | unknown
  target_type_source: "milestone-artifact.md#target_type"
  axis_applicability_state: applicable | substituted | not_applicable | split | blocked
  expected_method: external_behavior_scenario | artifact_appropriate_review | split_by_slice | blocked_pending_type
  substituted_by:
    - method: "operator_simulation | artifact_review | policy_conformance | cross_reference_review | professional_review"
      scope: "non-program slice or N/A"
      evidence_refs:
        - "path/to/evidence.md"
  scenario_results:
    - scenario_id: "BB-SCENARIO-001"
      target_slice: "program_code"
      user_or_operator_trigger: "用户或 operator 执行动作"
      input_or_precondition: "输入、环境或前置条件"
      observable_surface: "UI | CLI | API | log | file output | integration behavior"
      expected_observable_result: "外部可观察的期望结果"
      actual_observable_result: "证据中显示的实际结果，未知时写 N/A"
      regression_expectation: "该场景保护的回归期待"
      covered_by_wt:
        - "WT-xxx"
      evidence_refs:
        - "path/to/wt-xxx-closeout.md#completion_signals_trace"
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
  input_gap_classification:
    input_gap_status: none | input_gap | behavior_failure | mixed_input_gap_and_behavior_failure
    missing_target_type: true | false
    missing_aggregation_rules: true | false
    missing_completion_signals_trace: true | false
    missing_scenario_inputs: true | false
    behavior_failure_present: true | false
    classification_reason: "说明缺口或行为失败的来源；若未执行场景，必须说明不是 behavior failure"
  checklist_results:
    - check_id: B1
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/wt-a-contract.md"
        - "path/to/wt-b-closeout.md"
      finding: "具体发现描述。WT-A 定义了接口 X（contract.md#L12），WT-B 在 closeout 中显示消费了接口 X 但签名存在差异：A 期望 Y 参数，B 传入 Z。"
    - check_id: B2
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/milestone-artifact.md#completion_signals"
        - "path/to/wt-xxx-closeout.md#completion_signals_trace"
      scenario_results:
        - "BB-SCENARIO-001"
      finding: "具体发现描述。Signal '用户可配置超时时间' 被场景 BB-SCENARIO-001 覆盖：operator 通过 CLI 传入 timeout=30，期望 API 响应中 timeout_policy=30；证据来自 WT-002 closeout。Signal '超时后自动重试' 无任何行为场景覆盖——缺失。"
    - check_id: B3
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/wt-a-closeout.md#changed_files"
        - "path/to/wt-b-closeout.md#changed_files"
      finding: "具体发现描述。文件 shared/config.go 被 WT-A 和 WT-B 同时修改，A 修改了连接池大小配置，B 修改了超时配置——不同配置项，无冲突。"
    - check_id: B4
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/wt-xxx-closeout.md#new_files"
        - 路径分层规则文档
      finding: "具体发现描述。WT-003 新增文件 .servo/custom-config.yaml——.servo/ 为 state layer，业务代码产出不应落在此目录。"
    - check_id: B5
      verdict: pass | soft_fail | hard_fail | blocked | substituted | not_applicable
      evidence_refs:
        - "path/to/milestone-artifact.md#completion_signals"
        - "path/to/wt-xxx-closeout.md#completion_signals_trace"
      finding: "具体发现描述。3 个 completion_signals 中 2 个有覆盖（WT-001、WT-002），1 个无覆盖。覆盖 WT 权重：WT-001(4)、WT-002(3)，满足 milestone 配置的权重要求（≥3）。"
  carrier: subagent | current-carrier
  isolation_guarantee: true | false
  carrier_isolation_broken: true | false
  isolation_note: "具体说明。如：'未检测到其他轴 verdict 注入。' 或 '检测到 whitebox verdict 泄漏：[具体内容摘要]，已标记隔离破坏。'"
```

各字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `verdict` | enum | 整体 blackbox 判定。`blocked`：输入不足或 target_type 未解析。`hard_fail`：存在 hard_fail 项。`soft_fail`：存在 soft_fail 项且无 hard_fail。`pass`：所有适用项通过，且 substituted 项有替代证据；`not_applicable` 不提供正向通过证据 |
| `severity` | enum | 对 milestone 的影响严重度。`low`：发现不影响交付（仅为 soft_fail 低权重项）。`medium`：存在实质性但可修复的问题。`high`：存在 hard_fail 或 blocked，里程碑交付受阻 |
| `target_type` | enum | Milestone 交付目标类型：`program_code`、`non_program_artifact`、`mixed` 或 `unknown` |
| `target_type_source` | string | 类型来源或可追溯推断来源 |
| `axis_applicability_state` | enum | blackbox 轴适用性状态：`applicable`、`substituted`、`not_applicable`、`split` 或 `blocked`；这是路由事实，不是成功 verdict |
| `expected_method` | enum | 当前类型下 blackbox 轴应使用的方法 |
| `substituted_by` | list | 替代验收方法和证据。仅在 `axis_applicability_state = substituted` 或 `split` 时有效 |
| `scenario_results` | list | 程序目标或 mixed 程序切片的外部行为场景结果 |
| `input_gap_classification` | object | 区分输入缺口与实际行为失败。缺少 `target_type`、`aggregation_rules`、`completion_signals_trace` 或 scenario inputs 时，必须记录为 `input_gap` / non-pass，而不是伪装成行为失败或 pass |
| `checklist_results[*].verdict` | enum | 分项判定。`blocked`：检查无法执行（输入缺失）。`substituted`：该项用替代验收承接。`not_applicable`：该项明确不适用，不能计为 pass |
| `checklist_results[*].evidence_refs` | list | 引用的文件路径或 artifact ref，用于追溯 |
| `checklist_results[*].finding` | string | 具体发现描述，包含对比细节和结论 |
| `carrier` | enum | 运行载体：`subagent`（隔离 SubAgent）或 `current-carrier`（降级） |
| `isolation_guarantee` | bool | 轴间隔离是否得到保证。`false` 意味着检测到其他轴 verdict 泄漏或 current-carrier 降级 |
| `carrier_isolation_broken` | bool | 仅 current-carrier 降级时标记为 `true`。SubAgent 但检测到泄漏时 `isolation_guarantee: false` 但此字段可为 `false` |
| `isolation_note` | string | 隔离状态的详细说明，包括泄漏内容摘要或降级原因 |

### Severity 判定规则

- `high`：任一 check_id verdict 为 `hard_fail` 或 `blocked` → milestone 存在严重外部可见问题或无法完成检查
- `medium`：存在多个 `soft_fail` 项，或单个 `soft_fail` 涉及高权重 WT（weight ≥ 4）的产出
- `low`：仅有单个 `soft_fail` 且涉及低权重 WT（weight ≤ 2），或所有适用项 pass / substituted 证据完整但有注记性发现

## 资源

- 本技能的设计依据：Milestone Gate 四轴 Skills 与两层编排设计稿 — 定义四轴架构、Skill 层级、输入/输出合同
- Milestone Gate 聚合合同 — 定义 aggregation_rules 和 Layer 2 输入格式（本技能是 Layer 2 的输入来源之一）
- Single-Acceptance Contract — 定义被消费的 WT verdict 格式
- Worktrack Contract — 定义 WT 的 scope、node_type、completion_signals_trace 等字段
- Skill 公共约束 C-1 至 C-8（已内联于 §硬约束）
- 路径分层规则 — B4 检查所需的 repo 目录分层定义

以上 docs 引用为源侧 authoring trace。本技能作为 canonical skill package 自洽分发时，不依赖这些路径的运行时可用性（C-8）。
