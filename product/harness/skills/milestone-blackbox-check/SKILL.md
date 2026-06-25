---
name: milestone-blackbox-check
description: 当 milestoone gate 需要从外部视角（用户可观察行为、跨 WT 集成、回归风险）对 milestone 做隔离检查，且不得阅读完整实现代码时，使用这个技能。它是 Milestone Gate 四轴架构中 Layer 1 的 blackbox 轴，运行在隔离 SubAgent 中。
---

# Milestone Blackbox 检查技能

## 概览

本技能实现 Milestone Gate 四轴架构中 Layer 1 的 **blackbox 轴**检查，是 [Milestone Gate 四轴 Skills 与两层编排设计](../../../../docs/harness/artifact/control/milestone-gate-aggregation.md) 定义的四个独立轴检查 Skill 之一。它从 **milstone 外部视角**检查：最终用户看到的结果、跨 worktrack 集成行为、回归风险。

核心原则：**不阅读完整实现代码**。本技能只消费 WT 的 contract、evidence、closeout summary 和 diff summary（文件变更摘要），不做代码级审查。代码级审查由 whitebox 轴（`milestone-whitebox-check`）负责。

本技能与 `milestone-whitebox-check`、`milestone-anticheat-check`、`milestone-composite-check` 共同构成 Milestone Gate 的四轴检查层。四轴之间**严格隔离**——每个轴的 SubAgent 任务包不得包含其他轴的 verdict。

当 `milestone-status-skill`（Layer 2 orchestrator）需要在 milestone 所有 WT 闭环后，从外部集成视角检查 milestone 的交付质量时，使用这个技能。它产出一份结构化的 `blackbox_verdict`，供 Layer 2 aggregator 聚合到 milestone_gate_verdict。

## 何时使用

当满足以下条件时使用这个技能：

- 当前 milestone 下所有 active WT 已闭环（每个 WT 有 single-acceptance verdict + closeout record）
- `milestone-status-skill` 确认 worktrack 列表 finished，可以进入 milestone gate 检查
- 需要从外部用户视角评估：跨 WT 集成是否一致、completion_signals 是否有对应产出、是否有回归风险
- 检查必须隔离运行，不能看到其他轴的 verdict
- 不需要阅读完整实现代码——如果检查需要理解代码内部，应委托给 whitebox 轴

以下情况不适用：

- Milestone 下还有 active WT 未闭环 → 应返回 `not_ready`，由 orchestrator 等待
- 需要逐行代码审查 → 应使用 `milestone-whitebox-check`
- 需要检测证据伪造（mock abuse / self-review bias 等）→ 应使用 `milestone-anticheat-check`
- 需要复合验收 lane 评估（code-review / feature-completeness 等）→ 应使用 `milestone-composite-check`
- 需要对单个 WT 做 gate 判定 → 应使用 `worktrack-gate-skill`
- 当前处于 worktrack scope 而非 milestone scope → 不适用

## 工作流

1. **验证就绪状态**：确认 milestone 下所有 WT 已闭环。若有 active WT，返回 `not_ready` 并列出未闭环 WT。
2. **载入最小输入集**：精确载入 milestone artifact、所有闭环 WT 的 closeout record、single-acceptance verdict、和 WT diff summary。不得载入完整 diff 或实现代码。
3. **建立隔离上下文**：确认当前运行环境（SubAgent 或 current-carrier）。记录 `carrier` 和 `isolation_guarantee`。如果检测到其他轴 verdict 注入上下文，立即标记 `isolation_guarantee: false` 并记录泄漏来源。
4. **执行五项 blackbox 检查**（见下文「检查 checklist」）：
   - B1: Cross-WT integration consistency
   - B2: End-user promise fulfillment
   - B3: Regression risk assessment
   - B4: External consistency with repo conventions
   - B5: Completeness gap analysis
5. **为每项检查收集证据**：每条 finding 必须附带 `evidence_refs`（引用的文件路径或 artifact ref）。缺失证据必须显式暴露，不能当作隐式通过。
6. **产生分项 verdict**：每项检查独立给出 `pass | soft_fail | hard_fail | blocked`。`blocked` 表示该检查无法执行（如输入缺失），需要上层干预。
7. **综合整体 verdict**：按以下规则从五项分项 verdict 推导整体 blackbox verdict：
   - 任何一项 `blocked` → 整体 `blocked`
   - 任何一项 `hard_fail` → 整体 `hard_fail`
   - 任一项 `soft_fail` → 整体 `soft_fail`（除非已有 `hard_fail` 或 `blocked`）
   - 全部 `pass` → 整体 `pass`
8. **产出结构化输出**：按「预期输出」格式生成 `blackbox_verdict`。
9. **在响应中停止**：不得进入 aggregator 计算、gate 判定、恢复决策或代码修改。

## 检查 Checklist

### B1: Cross-WT Integration Consistency

**问题**：WT 之间的接口是否一致？

如果一个 WT-A 定义了合约（contract/interface）、另一个 WT-B 消费了该合约，B 的实现是否在接口层面与 A 的约定保持一致？

**判据**：

- 扫描所有 WT 的 contract 中的 `interface_contracts` 或 `module_contracts` 字段
- 对比 WT-A 的合约定义（声明的接口、文件路径、数据结构）与 WT-B closeout record 中的 `changed_files` / `diff_summary`
- 检查是否存在：WT-B 未消费 WT-A 声明的接口、WT-B 消费了 WT-A 未声明的接口、接口签名不一致

**证据来源**：

- WT contract（`interface_contracts`、`module_contracts`）
- WT closeout record（`changed_files`、`diff_summary`）
- Milestone artifact（`worktrack_dependencies` 或等价依赖声明）

**分项 verdict 规则**：

- `pass`：所有声明的跨 WT 接口一致，无遗漏消费，无未声明消费
- `soft_fail`：存在轻微不一致（如命名差异但不影响行为），或依赖 WT 的 contract 未显式声明接口但 closeout 显示合理消费
- `hard_fail`：存在接口断裂（WT-A 定义接口但 WT-B 未消费、或消费了不存在/不匹配的接口）
- `blocked`：缺少必要的 contract 文件或 closeout record，无法完成检查

### B2: End-User Promise Fulfillment

**问题**：从用户视角，milestone 声明的 completion_signals 是否已经有对应的可观察产出？

Milstone artifact 中的 `completion_signals` 声明了"用户能看到什么变化"。本检查验证每个 signal 是否有一条或多条 WT 的 closeout 实际产出了对应变更。

**判据**：

- 提取 milestone artifact 中的 `completion_signals` 列表
- 为每个 signal 建立 WT 覆盖映射：列出哪些 WT 的 closeout record 中包含了与该 signal 对应的文件变更或行为变更
- 检查覆盖缺口：是否存在 signal 没有任何 WT 覆盖

**证据来源**：

- Milestone artifact（`purpose`、`completion_signals`、`acceptance_criteria`）
- 每个 WT 的 closeout record（`changed_files`、`completion_signals_trace`）
- 每个 WT 的 single-acceptance verdict（`verdict`、`critical_failure`）

**分项 verdict 规则**：

- `pass`：所有 completion_signals 至少有一个 WT 覆盖，且覆盖 WT 的 single-acceptance verdict 为 pass
- `soft_fail`：所有 signals 有覆盖，但部分覆盖 WT 的 single-acceptance 为 soft_fail
- `hard_fail`：存在 completion_signal 没有任何 WT 覆盖（空洞），或覆盖 WT 的 single-acceptance 为 hard_fail
- `blocked`：milestone artifact 缺少 completion_signals 字段，或所有 WT closeout 缺少 completion_signals_trace

### B3: Regression Risk Assessment

**问题**：任一 WT 的变更是否可能破坏其他 WT 的结果？

检查每个 WT 的变更文件集是否与 milestone 下其他 WT 的依赖面存在交集，评估潜在的回归风险。

**判据**：

- 为每个 WT 构建变更文件集（从 closeout record 的 `changed_files` 或 diff summary 提取）
- 构建跨 WT 引用矩阵：对于每个文件，列出哪些 WT 变更了它、哪些 WT 依赖它
- 检测风险模式：
  - **共享文件变更**：同一文件被多个 WT 修改 → 可能有 merge 冲突或逻辑覆盖
  - **依赖文件变更**：WT-A 变更了 WT-B 的依赖文件 → 可能破坏 B 的行为
  - **基础设施文件变更**：shared config、common utility、build script 等被修改 → 影响范围大

**证据来源**：

- 所有 WT 的 closeout record（`changed_files`）
- 所有 WT 的 diff summary（文件变更摘要）
- WT contract（`impacted_modules`、`dependencies`）
- Repo 路径分层规则（`docs/project-maintenance/foundations/root-directory-layering.md`）

**分项 verdict 规则**：

- `pass`：没有任何文件被多个 WT 修改，且所有变更文件不被其他 WT 依赖
- `soft_fail`：存在共享文件变更或多 WT 依赖同一文件，但经分析属于非冲突性变更（如不同函数、不同配置项）
- `hard_fail`：存在明确的冲突风险——同一逻辑单元/接口/配置项被多个 WT 以不同方向修改
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
- 检查 milestone 产出是否在 `.agents/skills/` 和 `product/harness/skills/` 之间保持了 canonical → deploy target 的分发关系

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

**问题**：是否存在 completion_signals 声明了但没有任何 WT 覆盖的空洞？是否存在 milestone 级的缺失证据？

本检查构建 signal → WT 覆盖矩阵，并检测跨维度缺失。B5 与 B2 互补：B2 关注"用户能否看到"，B5 关注"架构上是否完整"。

**判据**：

- 构建 signal → WT 覆盖矩阵：行为 completion_signal 一行，列为每个 WT 是否覆盖该 signal
- 检测：
  - **空行**：某个 signal 无任何 WT 覆盖
  - **弱覆盖**：某个 signal 只有低权重 WT（如 docs）覆盖，但 milestone 要求更高权重
  - **证据缺口**：覆盖 WT 的 gate evidence 中是否有缺失维度（如某个 WT 没有 test evidence）
- 按 milestone 的 `aggregation_rules.weight_rules` 检查覆盖 WT 的权重是否满足该 signal 的最低要求

**证据来源**：

- Milestone artifact（`completion_signals`、`aggregation_rules`）
- 所有 WT 的 closeout record（`completion_signals_trace`）
- 所有 WT 的 single-acceptance verdict（`verdict`）
- 所有 WT 的 gate evidence（`implementation_gate`、`validation_gate`、`policy_gate`——仅读取 verdict 结论，不展开完整内容）

**分项 verdict 规则**：

- `pass`：所有 signals 有充分覆盖（覆盖 WT 权重满足 milestone 要求），无跨维度证据缺口
- `soft_fail`：所有 signals 有覆盖但部分覆盖 WT 权重偏低，或存在非关键的证据维度缺失
- `hard_fail`：存在 completion_signal 完全空覆盖，或关键 signal 的覆盖 WT 存在 gate evidence 缺口
- `blocked`：缺少 aggregation_rules 或 completion_signals 定义，无法完成分析

## Blackbox 检查约定

每次运行这个技能时，都使用同一套限定范围约定格式。

### Blackbox 检查任务简报

- `触发条件`：milestone 下所有 WT 已闭环
- `检查目标`：从外部视角验证 milestone 的跨 WT 集成质量
- `当前里程碑`：milestone ID 和 purpose 摘要
- `检查范围`：所有闭环 WT 的 contract、evidence、closeout record、diff summary
- `排除范围`：完整实现代码、其他轴 verdict、单个 WT 的代码质量（属 whitebox）、单个证据可信度（属 anticheat）
- `检查项`：B1-B5
- `隔离约束`：不得接收或读取其他轴 verdict
- `完成信号`：产出结构化 blackbox_verdict

### Blackbox 检查信息包

- `输入产物`：milestone artifact、所有闭环 WT 的 contract / single-acceptance verdict / gate evidence / closeout record / diff summary
- `里程碑约定摘要`：milestone 的 purpose、completion_signals、acceptance_criteria
- `WT 列表`：所有闭环 WT 的 ID、node_type、verdict 摘要
- `依赖关系`：WT 之间的声明依赖（从 contract 的 dependencies 字段提取）
- `文件变更矩阵`：每个 WT → 变更文件列表（从 closeout record 和 diff summary 提取）
- `信号覆盖矩阵`：每个 completion_signal → 覆盖的 WT 列表
- `路径分层规则引用`：已知的 repo 分层规则
- `已知风险`：从 milestone artifact 或 WT closeout 中已声明风险

## 硬约束

遵循本包内最小公共约束 C-1 至 C-8：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现；C-8 每个 canonical skill package 必须自洽，不依赖包外路径进行运行时语义。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

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
5. **不得进入后续阶段**：本技能产出 verdict 后立即停止。从本技能直接跳到 aggregator 计算、gate 判定、恢复决策、worktrack 创建或代码修改的行为必须返回 `blocked`。唯一合法的下一步是将输出交给 orchestrator（milestone-status-skill）。
6. **缺失输入必须暴露**：缺少完成检查所必需的任何输入（如 milestone 无 completion_signals、WT 无 closeout record 等）时，唯一合法行为是将对应检查项标记为 `blocked` 并说明缺失内容。假定缺失数据为 pass 的行为必须返回 `blocked`。
7. **证据引用必须具体**：每条 finding 的 `evidence_refs` 必须是可追溯的文件路径或 artifact ref（如 `WT-xxx/closeout-record.md`、`milestone-artifact.md#completion_signals`）。不得出现无法定位的模糊引用（如"综合所有 WT 来看"）。
8. **输出必须包含完整的五项检查结果**：即使某项检查因输入不足被 `blocked`，也必须显式输出该项的 verdict 和 finding，不得省略。跳过某项检查的行为必须返回 `blocked`。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 `Blackbox 检查报告`：

- `Blackbox 检查目标`
- `输入接收状态`（哪些输入已就绪、哪些缺失）
- `轴间隔离声明`（isolation guarantee、是否检测到泄漏）
- `分项检查结果`（B1-B5，每项包含 verdict、evidence_refs、finding）
- `整体 Blackbox Verdict`
- `风险摘要与建议`

结果必须包含以下结构化 YAML：

```yaml
blackbox_verdict:
  axis: blackbox
  verdict: pass | soft_fail | hard_fail | blocked
  severity: low | medium | high
  checklist_results:
    - check_id: B1
      verdict: pass | soft_fail | hard_fail | blocked
      evidence_refs:
        - "path/to/wt-a-contract.md"
        - "path/to/wt-b-closeout.md"
      finding: "具体发现描述。WT-A 定义了接口 X（contract.md#L12），WT-B 在 closeout 中显示消费了接口 X 但签名存在差异：A 期望 Y 参数，B 传入 Z。"
    - check_id: B2
      verdict: pass | soft_fail | hard_fail | blocked
      evidence_refs:
        - "path/to/milestone-artifact.md#completion_signals"
        - "path/to/wt-xxx-closeout.md#completion_signals_trace"
      finding: "具体发现描述。Signal '用户可配置超时时间' 由 WT-002 覆盖（config 变更），产出文件为 product/config/timeout.yaml。Signal '超时后自动重试' 无任何 WT 覆盖——缺失。"
    - check_id: B3
      verdict: pass | soft_fail | hard_fail | blocked
      evidence_refs:
        - "path/to/wt-a-closeout.md#changed_files"
        - "path/to/wt-b-closeout.md#changed_files"
      finding: "具体发现描述。文件 shared/config.go 被 WT-A 和 WT-B 同时修改，A 修改了连接池大小配置，B 修改了超时配置——不同配置项，无冲突。"
    - check_id: B4
      verdict: pass | soft_fail | hard_fail | blocked
      evidence_refs:
        - "path/to/wt-xxx-closeout.md#new_files"
        - "docs/project-maintenance/foundations/root-directory-layering.md"
      finding: "具体发现描述。WT-003 新增文件 .servo/custom-config.yaml——.servo/ 为 state layer，业务代码产出不应落在此目录。"
    - check_id: B5
      verdict: pass | soft_fail | hard_fail | blocked
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
| `verdict` | enum | 整体 blackbox 判定。`blocked`：输入不足无法完成检查。`hard_fail`：存在 hard_fail 项。`soft_fail`：存在 soft_fail 项且无 hard_fail。`pass`：全部 pass |
| `severity` | enum | 对 milestone 的影响严重度。`low`：发现不影响交付（仅为 soft_fail 低权重项）。`medium`：存在实质性但可修复的问题。`high`：存在 hard_fail 或 blocked，里程碑交付受阻 |
| `checklist_results[*].verdict` | enum | 分项判定。`blocked`：检查无法执行（输入缺失） |
| `checklist_results[*].evidence_refs` | list | 引用的文件路径或 artifact ref，用于追溯 |
| `checklist_results[*].finding` | string | 具体发现描述，包含对比细节和结论 |
| `carrier` | enum | 运行载体：`subagent`（隔离 SubAgent）或 `current-carrier`（降级） |
| `isolation_guarantee` | bool | 轴间隔离是否得到保证。`false` 意味着检测到其他轴 verdict 泄漏或 current-carrier 降级 |
| `carrier_isolation_broken` | bool | 仅 current-carrier 降级时标记为 `true`。SubAgent 但检测到泄漏时 `isolation_guarantee: false` 但此字段可为 `false` |
| `isolation_note` | string | 隔离状态的详细说明，包括泄漏内容摘要或降级原因 |

### Severity 判定规则

- `high`：任一 check_id verdict 为 `hard_fail` 或 `blocked` → milestone 存在严重外部可见问题或无法完成检查
- `medium`：存在多个 `soft_fail` 项，或单个 `soft_fail` 涉及高权重 WT（weight ≥ 4）的产出
- `low`：仅有单个 `soft_fail` 且涉及低权重 WT（weight ≤ 2），或所有项 pass 但有注记性发现

## 资源

- 本技能的设计依据：[Milestone Gate 四轴 Skills 与两层编排设计稿](../../../../docs/harness/artifact/control/milestone-gate-aggregation.md) — 定义四轴架构、Skill 层级、输入/输出合同
- Milestone Gate 聚合合同：[docs/harness/artifact/control/milestone-gate-aggregation.md](../../../../docs/harness/artifact/control/milestone-gate-aggregation.md) — 定义 aggregation_rules 和 Layer 2 输入格式（本技能是 Layer 2 的输入来源之一）
- Single-Acceptance Contract：[docs/harness/artifact/worktrack/single-acceptance-contract.md](../../../../docs/harness/artifact/worktrack/single-acceptance-contract.md) — 定义被消费的 WT verdict 格式
- Worktrack Contract：[docs/harness/artifact/worktrack/contract.md](../../../../docs/harness/artifact/worktrack/contract.md) — 定义 WT 的 scope、node_type、completion_signals_trace 等字段
- 公共约束：[docs/harness/foundations/skill-common-constraints.md](../../../../docs/harness/foundations/skill-common-constraints.md) — 所有 Skill 必须遵守的 C-1 至 C-8 约束
- 路径分层规则：[docs/project-maintenance/foundations/root-directory-layering.md](../../../../docs/project-maintenance/foundations/root-directory-layering.md) — B4 检查所需的 repo 目录分层定义

以上 docs 引用为源侧 authoring trace。本技能作为 canonical skill package 自洽分发时，不依赖这些路径的运行时可用性（C-8）。
