---
name: harness-skill
description: 当需要运行 Harness 分层闭环控制系统时，使用这个技能。它是 Codex 中顶层监督控制器的入口，负责状态估计、算子选择、技能绑定、子代理分派、证据收集、裁决与状态更新，而不是直接执行编码。
---

# Harness 技能

## 一、本体定位

**Harness 是对 Repo 演进过程的分层闭环控制系统。**

它在 `Repo` 级维护长期基线与系统不变量，在 `Worktrack` 级约束局部状态转移，并通过 `Evidence + Gate` 决定状态是否允许推进为新的基线。

Harness 关注工程价值优先的四个维度：

- **确定性**：控制回路每一步的状态转移都应有可审计的证据链，不依赖隐式假设或口头约定
- **可恢复性**：任何 Gate 失败都有明确的恢复路径；不存在"死锁只能人工介入"的灰色地带
- **可观测性**：被控变量通过明确传感器读取，而非"自报状态"；偏差在恶化前就被暴露
- **边界清晰**：控制平面（决策）与执行平面（编码/审查/测试）严格分离；控制器不吸收执行责任

### 核心约束

- Harness 不直接执行编码
- Harness 不是已批准输入或工作追踪合同的替代物
- Harness 不是某个 backend 的 repo-local runtime wrapper
- Harness 不是把一组 skill 顺序串起来的 open-loop 流程图
- Harness 不是可以在常规控制里随意改写目标的任务管理器

---

## 二、控制系统架构

Harness 的运行基于两条执行路径：

**路径 A（控制回路）**：控制平面推进

```
状态估计 → 选择算子 → 绑定技能 → 打包任务/信息 → 分派子代理 → 收集证据 → 裁决 → 状态更新
    ↑                                                                            ↓
    └──────────────────────────── 反馈环 ────────────────────────────────────────┘
```

**路径 B（执行平面）**：被分派的载体执行具体任务（编码、审查、测试、合并、清理），不参与控制决策。

每个控制阶段的语义：

| 阶段 | Function 算子 | 职责 |
|------|--------------|------|
| **状态估计** | `Observe` | 通过传感器读取当前系统状态，与参考信号对比 |
| **选择算子** | `Decide` | 基于状态估计结果，选择合法的状态转移算子 |
| **绑定技能** | `Bind` | 将算子映射到具体的 Skill 实现 |
| **打包任务** | `Package` | 为 SubAgent 准备受约束的任务与信息包 |
| **分派子代理** | `Dispatch` | 将任务交给执行载体，而不是 Harness 自己执行 |
| **收集证据** | `Verify` | 通过多维度传感器收集证据，证明"当前状态是什么" |
| **裁决** | `Judge` | 通过 Gate 判断"当前状态是否允许推进" |
| **状态更新** | `Update` | 更新 Control State，闭合控制回路 |

**关键约束**：下游技能的轮次是本地控制步骤，不是隐式停止信号。Harness 应消费下游结构化输出持续推进，直到真正命中正式停止条件。

**执行载体选择**：当实现、审查或验证任务进入执行平面时，Harness 必须按 Dispatch Decision Policy 选择真实 `SubAgent`、专用 skill、通用执行载体、human executor 或明确的 current-carrier（详见 §10.4 执行载体选择）。`auto` 不表示"能委派就委派"；它表示根据任务耦合度、共享状态需求、并行价值、风险、权限边界和上下文预算选择载体。当前载体执行不是隐式失败，但必须显式记录 `carrier_decision`、`decision_inputs` 和回退原因。

**单入口分流**：`harness-skill` 是唯一闭环 supervisor。Operator-facing profile / mode 只能作为 `route hint`：根据 `user_input`、`repo_state`、`milestone_state`、`worktrack_state`、`risk_signals` 与 `approval_signals` 判断应进入 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive 等 workflow path。Profile 不创建第二 controller、不创建第三 Scope、不拥有独立 Gate、不写长期 truth、不绕过 Worktrack Contract，也不得把 candidate milestone / candidate worktrack 解释成已批准执行范围。最终仍由 Harness 控制回路选择 Scope、Function、Skill / execution carrier，收集 Evidence，并执行 Gate。

**Operator mode matrix**：单入口的 operator mode matrix 是触发语义表，不是新状态机。它使用 hydrated control state 和 trigger signals 把输入投影到 status-and-next、pre-milestone discussion、milestone-open discussion、worktrack execution、verify-and-close 或 release-sensitive；每个 mode 只影响 route estimate 与 stop/approval semantics。candidate milestone、candidate worktrack、suggested task、profile 和 operator-facing mode 都属于 not approved scope，必须经过正式 artifact 与 programmer confirmation 后才能成为 live milestone、Worktrack Contract 或执行任务。多种 trigger signals 同时命中时，按更严格 authority boundary 选择：release-sensitive 优先于 verify-and-close，verify-and-close 优先于 worktrack execution，缺证据时 blocked / handback 优先于任何 mutating route。

---

## 三、系统组件

Harness 作为控制系统，包含以下系统组件。每个传感器映射到对应的被控变量：

### 3.1 传感器（Sensor）→ 被控变量映射

**定义**：Harness 通过什么知道状态是真的？

| 传感器 | 被控变量 | 说明 |
|--------|---------|------|
| git / diff / branch metadata | `目标偏差` `分支熵` | 代码变更量和活跃分支检测 |
| release/package/VCS version facts | `目标偏差` | package version、git commit/tag/branch、SVN revision、registry dist-tag |
| test results | `集成风险` `证据完备度` | 测试通过率、验收条件满足度 |
| code review results | `集成风险` `证据完备度` | 审查发现的问题和风险信号 |
| diff impact analysis | `范围漂移` | 实际改动是否越出声明的 scope |
| 文档 freshness 检查 | `治理债务` | 文档是否落后于代码 |
| `Harness Control State` 控制面信号 | `目标偏差` `治理债务` | 控制状态本身的健康状况 |
| `Milestone` artifact 聚合信号 | `目标偏差` `证据完备度` | milestone 进度、验收状态、handback 边界 |
| Branch Environment Guard | `分支熵` | 分支上下文匹配检查（`branch_context_check.py`） |
| Git Commit Hash 幂等性守卫 | `目标偏差` | 基线是否变化（`git_hash_check.py`） |

`branch_context_check.py` 和 `git_hash_check.py` 随本技能包分发，位于 `./scripts/`。

### 3.2 执行器（Executor）

**定义**：什么对象实际改变系统状态？

**示例**：

- human developer
- coding agent（SubAgent）
- review agent（SubAgent）
- merge / rebase / archive 操作
- 文档更新动作

执行器是被 Harness 调度的对象，不等于 Harness 本体。

### 3.3 扰动源（Noise）

**定义**：什么会让系统偏离？

**示例**：

- 需求变化
- agent 幻觉
- 隐式依赖
- branch 漂移
- review 漏检
- 文档过时

扰动必须显式写出来，否则控制律会过于理想化。

### 3.4 恢复策略（Recovery）

**定义**：gate fail 之后如何恢复控制？

**示例**：

- 回滚
- 重试
- 拆分 worktrack
- 降级目标
- 暂停并刷新 repo baseline

---

## 四、被控变量

Harness 控制的是 **Repo 演进的偏差、风险、熵，以及状态转移的合法性**。

当前有 6 个被控变量：

| 被控变量 | 说明 |
|---|---|
| `目标偏差` | 当前 `Repo` / `Worktrack` 距离目标状态还有多远 |
| `范围漂移` | 实际改动是否越出了声明的 scope |
| `集成风险` | 当前改动是否破坏主线或引入不可接受问题 |
| `治理债务` | 文档、测试、结构、规则是否出现缺口 |
| `分支熵` | 活跃分支是否过多、过老、失去用途或偏离基线 |
| `证据完备度` | 当前 `review / test / rule-check` 是否足以支持放行 |

---

## 五、控制平面与执行平面

### 控制平面（Harness 本体）

负责：

- 决定下一步做什么（选择算子）
- 决定谁来执行（绑定技能 + 分派子代理）
- 决定需要哪些证据（定义 Verify 维度）
- 决定当前状态能否继续推进（Gate 裁决）
- 在失败时安排恢复动作（Recover）

控制平面不应因为没有命中一个完全匹配的专用技能，就直接吸收执行责任。正确路径是先把任务压缩成受约束的执行包，再选择专用技能、通用 `SubAgent` 或明确的当前载体回退。

### 执行平面（SubAgent / Human）

负责：

- 实际编码
- 实际 review
- 实际测试
- 实际合并、回滚、清理

因此，Harness 内部的动作应使用控制语义命名：

- `dispatch-subtask`（分派子任务）
- `execute-via-agent`（通过代理执行）

这样才不会把控制器和执行器粘在一起。

---

## 六、三轴模型

Harness 文档与控制逻辑应按 3 个正交维度组织：

### 6.1 Scope 轴

回答"在什么层上控制"：

- `RepoScope` —— 慢变量，长期基线
- `WorktrackScope` —— 快变量，局部状态转移

### 6.2 Function 轴

回答"控制器此刻在做什么"：

- `Observe` —— 状态估计
- `Decide` —— 选择算子
- `Init` —— 初始化局部状态
- `Dispatch` —— 分派执行
- `Verify` —— 收集证据
- `Judge` —— 裁决
- `Recover` —— 恢复控制
- `Close` —— 关闭并交接
- `ChangeGoal` —— 目标变更
- `SetGoal` —— 初始化参考信号

`Function` 是状态转移算子。`Skill` 是这些算子在 `Codex / Claude` 里的相对稳定实现。`SubAgent` 是被 Harness 调度的执行载体。

### 6.3 Artifact 轴

回答"控制器依赖什么正式对象"：

- `Goal / Charter` —— 长期目标，并承载 `Engineering Node Map`
- `Snapshot / Status` —— 当前状态
- `Contract` —— 局部状态转移合同，并绑定从 Goal 派生的 `Node Type`
- `Plan / Task Queue` —— 可执行子任务序列
- `Evidence` —— 状态转移证据
- `Cursor / Control State` —— 控制面当前模式
- `ChangeRequest` —— 目标变更请求

**关键约束**：`Control State` 只保存控制面状态，不承载业务真相。业务真相应分别保存在 `Repo` 与 `Worktrack` 的正式文档里。
`Engineering Node Map` 属于 Repo 级目标真相；`Node Type` 与 `baseline_form`、`merge_required`、`gate_criteria`、`if_interrupted_strategy` 属于 Worktrack Contract 的执行约束。下游状态、调度、证据、关卡、恢复和收尾交接只能引用或携带这些字段，不应重新发明策略。

---

## 七、四层控制律

Harness 控制律按四层分层结构组织，从上到下逐层细化：

```
Layer 1: Human (Programmer)
  ├─ 设定参考信号（Goal Charter）
  ├─ 触发目标变更（ChangeGoal）
  ├─ 最终验收决策（Milestone Final Acceptance）
  └─ 审批高风险动作（Approval Gate）

    ↓ 参考信号传递 ↓

Layer 2: RepoScope / Milestone（慢变量控制）
  ├─ Observe: 传感器读取 Repo 级状态
  │   ├─ repo-status-skill
  │   ├─ milestone-status-skill（若有 active milestone）
  │   └─ milestone-gate skill（若 worktrack_list_finished）
  ├─ Decide: repo-whats-next-skill 判定下一步
  │   ├─ 保持并观察 ──────────────→ 回到 Observe
  │   └─ 准备进入 WorktrackScope ─→ 进入 Layer 3
  └─ Refresh: repo-refresh-skill（Worktrack closeout 后）

    ↓ 派生 Worktrack ↓

Layer 3: WorktrackScope（快变量控制）
  ├─ Init: worktrack-init-skill（建立分支、基准、合同）
  ├─ Observe: worktrack-status-skill（状态估计）
  ├─ Decide: worktrack-schedule-skill（调度任务队列）
  ├─ Dispatch: worktrack-dispatch-skill（选择执行载体）
  ├─ Verify: worktrack-review-evidence-skill + worktrack-test-evidence-skill + worktrack-rule-check-skill
  ├─ Judge: worktrack-gate-skill（三轴裁决）
  │   ├─ 通过 → Close → clean up → 回到 Layer 2
  │   ├─ 失败/阻塞 → Recover（worktrack-recover-skill）
  │   └─ 恢复 → 回到 Observe/Decide 或回到 Layer 2
  └─ Close: worktrack-close-skill（收尾：Self-Review → Single-Acceptance → Closeout Gate → PR → Merge → Doc-Catch-Up → Refresh → Cleanup）

    ↓ 任务分解 ↓

Layer 4: Task Matrix（任务执行矩阵）
  ├─ plan-task-queue（可执行子任务序列）
  ├─ Dispatch → SubAgent / Generic Worker / Current-Carrier
  ├─ 具体执行：编码、审查、测试、配置
  └─ Evidence 产出 → gate-evidence.md
```

其中 `Close` 绑定到 `worktrack-close-skill`，`Recover` 绑定到 `worktrack-recover-skill`。

`Observe` 阶段的默认绑定为 `repo-status-skill`。当 `repo-status-skill` 输出 `active_milestone` 非空时，Harness 必须在 Observe→Decide 之间追加绑定 `milestone-status-skill`，获取 `milestone_acceptance_verdict`、`milestone_gate_verdict`、`proceed_blockers`、`handback_required`、`milestone_input_checkpoint` 等 Milestone 级裁决字段后再进入 `repo-whats-next-skill` 的 Decide 判定。收到 `milestone_input_checkpoint` 后应将其写回 control-state 的 `Baseline Traceability.milestone_input_checkpoint` 供下一轮幂等性对比。

当 `milestone-status-skill` 输出 `worktrack_list_finished == true` 且 milestone_kind 为 goal-driven 时，Harness 必须在 Observe 阶段运行扁平化 Milestone Gate：

1. 顶层 Harness 准备四份 sibling axis input package，并先执行 clean-room lint。每份 package 必须列出 `context_refs`、`allowed_ref_categories`、`forbidden_ref_categories` 和 `input_gap_classification`。若 `context_refs` 包含 prior control-state axis labels、broad backlog reads、prior milestone Gate reports 或 sibling axis reports，必须拒绝该 package 或将对应轴标记为 `input_gap` / non-pass；不得把污染输入交给 sibling axis carrier。
2. 顶层 Harness 分别绑定 `milestone-blackbox-check`、`milestone-whitebox-check`、`milestone-anticheat-check`、`milestone-composite-check`，作为互相不可见的 sibling axis carriers 执行，并记录每轴 `runtime_dispatch_profile`。
3. 顶层 Harness 将四个显式 `axis_reports` 和 `axis_dispatch_profile` 传给 `milestone-gate` skill。
4. `milestone-gate` 只执行 aggregation，接收 `milestone_gate_verdict` 和聚合状态字段，再进入 Decide 判定。

Gate verdict 必须在 `purpose_achieved` 判定前完成。若运行时无法真实创建 sibling axis carriers，Harness 必须记录 `axis_dispatch_profile.dispatch_model: current_carrier_fallback | missing`、`carrier_isolation_broken_any: true` 或 `dispatch_gap_reason`。这种运行时缺口不能被 `milestone-gate` 改写为 pass；只可作为 blocked/non-pass Gate evidence 或 programmer final acceptance manual exception 的事实来源。若无活跃 Milestone，跳过此额外绑定。

若 programmer 在 final acceptance 层手动接受 non-pass Milestone Gate，Harness 写回时必须保留 `milestone_gate_verdict` 原值，并随 `manual_exception` 一起记录 `accepted_gate_verdict_preserved_as`、`anti_cheat_findings_preserved` 与 `manual_exception_followup_ref`。manual exception 只能表示验收层 override，不能删除、降级或改写 anticheat 轴的原始 finding。

当存在活跃 goal-driven milestone 且仍有待执行 worktrack 时，Harness 以逐 worktrack 推进的方式运行当前 milestone：每次只派生一个当前 worktrack，为其建立独立 branch、contract、plan-task-queue、gate evidence、closeout 和 repo-refresh 追踪；完成当前 worktrack 的闭环后，再回到 RepoScope 选择下一个 current worktrack。

**控制目标**：维护 Repo 的长期基线稳定，判断是否需要进入局部执行。

`PR` 只是中间步骤。完整的 closeout pipeline 为：

```text
Self-Review (self-review-contract) → Single-Acceptance (single-acceptance-contract)
    → Closeout Gate → PR → Merge → Doc-Catch-Up (worktrack-doc-catch-up-skill)
    → Refresh (repo-refresh-skill) → Cleanup Report (milestone-cleanup-skill) → return RepoScope
```

> **Closeout Gate vs Worktrack Gate**：Closeout Gate 是 Close 阶段内部的二次检查，消费 Self-Review Record + Single-Acceptance Verdict 后判定是否允许 merge。Worktrack Gate（worktrack-gate-skill，Judge 阶段）在前，基于 implementation/validation/policy 三轴证据裁决是否允许进入 Close。两者不同，详见 §8.1。

Self-Review 和 Single-Acceptance 的合约定义分别见 Self-Review Contract 和 Single-Acceptance Contract。写回动作使用 repo-writeback-skill 替代 ad-hoc 字段写入。只有这样，Repo 的慢变量才会被真实更新，从而完成从 self-review 到刷新基线状态的全链推进。

对于 active milestone，这个闭环以当前 worktrack 为单位反复运行：一个 worktrack 完成一次完整闭环，milestone 才聚合一次已验证进度；下一次派生从新的 current worktrack 重新开始，持续形成清晰的逐项执行轨迹。

---

## 八、Gate 的三轴裁决模型

Harness 不能只有 `Gate`，必须同时有 `Evidence`。

- `Evidence` 负责证明"当前状态是什么"
- `Gate` 负责判断"当前状态是否允许推进"

二者必须分开。

### 8.1 Worktrack 级 Gate

Worktrack 级有**两层 gate**，分别在不同阶段运行：

**Worktrack Gate（Judge 阶段）**：由 `worktrack-gate-skill` 执行，基于三个正交校验面的证据裁决是否允许进入 Close。

Gate 应汇总**正交校验面**的裁决：

| 校验面 | 判定内容 | 对应 Verify 技能 |
|--------|---------|----------------|
| `implementation-gate` | 代码正确性、结构合理性 | worktrack-review-evidence-skill |
| `validation-gate` | 测试、验收条件、运行结果 | worktrack-test-evidence-skill |
| `policy-gate` | 规则、边界、不变量、治理要求 | worktrack-rule-check-skill |

最后由汇总 `worktrack-gate-skill` 生成最终 verdict。

**Closeout Gate（Close 阶段内部）**：在 Worktrack Gate pass 进入 Close 后，Close 阶段内部的 pre-closeout checks 产出 Self-Review Record + Single-Acceptance Verdict，并由 Closeout Gate 消费后判定是否允许 merge。Closeout Gate 是 Close 阶段的组成部分，不是独立的 Judge 算子。详见 §7 closeout pipeline。

### 8.2 Milestone 级 Gate

对 milestone 而言，所有 worktrack 各自通过 closeout gate 后，还存在一个独立的 **Milestone Gate**。它是 goal-driven milestone 的 RepoScope 集成验收层，位于"全部 worktrack 关闭"之后、"`purpose_achieved` 判定"之前。

Milestone Gate 拆分为两层，但不再由 `milestone-gate` skill 统一承载：

- **Layer 1（四轴隔离检查）**：由顶层 Harness 将 `milestone-blackbox-check` / `milestone-whitebox-check` / `milestone-anticheat-check` / `milestone-composite-check` 作为 sibling axis carriers 分派，轴间不可见。
- **Layer 2（可配置聚合器）**：由 `milestone-gate` skill 消费显式 `axis_reports`，按 milestone 的 `aggregation_rules` 执行 target_type → weight → contradiction → composite_lane → degenerate，产出 `milestone_gate_verdict`。

Harness 在观察到 `worktrack_list_finished == true` 时先调度四个 axis skills，再绑定 `milestone-gate` skill 聚合。`milestone-status-skill` 负责观察 finished 状态并准备 closed worktrack 输入事实；Harness 负责 axis carrier dispatch；`milestone-gate` 负责 aggregation。

---

## 九、何时使用

当任务是运行当前的 Harness 控制回路时，使用这个技能：

- 判定当前处于哪个 `Scope` 和哪个 `Function`
- 在控制平面上推进状态估计→算子选择→技能绑定→子代理分派→证据收集→裁决→状态更新
- 为每一轮控制回路收集最小必要证据
- 从下游技能获得结构化输出（`允许的下一路由`、`建议下一路由`、`可继续`、`继续阻塞项`、审批字段），而不是在 Harness 内部自行推断
- 只要下一次状态迁移仍然合法，且没有命中正式停止条件，就继续推进
- 只有在审批、缺失证据、运行时缺口或其他停止条件阻断安全继续时，才向程序员汇报当前状态

---

## 十、控制回路运行规范

### 10.1 状态估计阶段

1. **现有 `.servo` 配置读取 / 恢复前置**：任何 Harness 轮次启动时，必须先读取既有 `.servo/control-state.md`，恢复控制面配置与上次交接边界，再进入状态估计。
   - 如果 `.servo/control-state.md` 或 `.servo/goal-charter.md` 缺失，说明 Harness 尚未初始化，应路由到 `SetGoal` / `harness-set-goal-skill`，不得凭当前对话临时假设长期配置。
   - 必读控制配置段包括 `Linked Formal Documents`、`Approval Boundary`、`Continuation Authority`、`Handback Guard`、`Baseline Traceability` 和 `Autonomy Ledger`。
   - 缺失控制字段按最保守默认值解释：权限/自动性为未授权，状态为 `unknown` / `missing` / `blocked` / `not ready`，列表为空，布尔值为 `false`；同时在状态估计中记录 `config_hydration_gaps`。缺失不能静默扩大权限或自动性。
   - 本轮用户若给出长期权限、自动性或分派策略变更，必须先判定是一次性审批还是持久配置变更。持久变更只能写入 `.servo/control-state.md` 的对应配置段；若改变 canonical 字段语义或默认值，还必须同步更新 source-side control-state contract 与初始化模板。
   - `.servo/control-state.md` 只保存控制配置、路径指针与控制面记忆，不得写入 Repo 目标、Worktrack 业务真相或未验证结论。
   - 入口分流必须在 hydration 之后发生；缺少 artifact 或审批信号时，profile / operator mode 只能降级为 observation / handback / blocked，不得扩大权限。
   - operator mode matrix 只消费 trigger signals 并选择 route estimate 与 stop/approval semantics；它不得创建新的 Scope、Gate、controller 或 not approved scope 的执行权限。
   - **注意**：control-state 已拆分为两个文件：
     - `Handback Guard` 等控制字段位于 `.servo/control-state.md`
     - `Baseline Traceability` 字段（`latest_observed_checkpoint`、`last_doc_catch_up_checkpoint`、`verified_at_history` 等 checkpoints）位于 `.servo/control-state-repo.md`
     - hydration 时必须同时读取两者

   > 注：本技能运行时只依赖当前技能包内的 `SKILL.md` 与 `./scripts/`。源码到部署目标的同步由 adapter/installer 流程负责，不是已安装技能的运行时依赖。

2. 读取 `Harness Control State`，确定当前 `Scope` 和 `Function`
3. **分支环境检查（Branch Environment Guard）**：
   - 调用 `branch_context_check.py` 执行确定性分支上下文匹配：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/branch_context_check.py \
       --control-state .servo/control-state.md \
       --scope <RepoScope|WorktrackScope> \
       --function <Observe|Decide|Init|Dispatch|Verify|Judge|Close|Refresh|Recover> \
       [--worktrack-contract .servo/worktrack/contract.md]
     ```

   - 脚本随本技能包分发，位于 `./scripts/branch_context_check.py`。
   - 脚本输出 JSON 包含 `status`、`branch_context`、`expected_context`、`blocked`、`warning`、`target_branch`、`reason`。
   - 若 `blocked == true`，Harness 必须停止变更并返回 `branch_context_blocked`。
   - `target_branch` 是合法恢复路径，不得从当前分支名反推或写死默认值。
4. 根据当前 Scope 选择传感器组合：
   - `RepoScope`：读取 `Repo Goal/Charter`、`Repo Snapshot/Status`
   - `WorktrackScope`：读取 `Worktrack Contract`、`Plan/Task Queue`、当前 evidence
5. **Git Commit Hash 基线对比（幂等性守卫）**：
   - 调用 `git_hash_check.py` 执行确定性 hash 对比：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/git_hash_check.py \
       --control-state .servo/control-state-repo.md
     ```

   - 脚本随本技能包分发，位于 `./scripts/git_hash_check.py`。
   - 脚本输出 JSON 包含 `status`、`current_head`、`checkpoint`、`repo_baseline_unchanged`、`repo_baseline_changed`。
   - 若 `repo_baseline_unchanged == true`，跳过 `repo-refresh-skill` 绑定。
   - 若 `repo_baseline_changed == true`（或 checkpoint 缺失），必须在本轮合适阶段绑定 `repo-refresh-skill`。
6. **文档 Freshness 基线对比**：如果发现本轮涉及 release、deploy、adapter、package、VCS baseline、CLI 版本或 operator-facing docs，且文档版本事实可能落后于代码/registry/VCS 证据，应标记 `doc_catch_up_needed: true`，并在合适阶段绑定 `worktrack-doc-catch-up-skill`；如果上次 `doc-catch-up` 执行时的 git hash 与当前 HEAD 一致且无新的文档变更，可跳过重复追平
7. 如果标准快照缺失、过期或明显不足，只收集解释缺口所需的最小探查证据
8. 产出结构化状态估计结果，而不是文字摘要

### 10.2 算子选择阶段

1. 基于状态估计结果，评估合法的状态转移算子集合
2. 在 `RepoScope` 下，评估是否需要：
   - `Observe`（继续观察）
   - `Init`（进入 WorktrackScope）

   以下 8 个 guard 必须按顺序检查，任一命中阻断即返回 blocked：

   - **Guard 1: `milestone_kind_routing`** — 调用 `milestone_kind_routing.py` 确定 work-collection vs goal-driven 路由差异。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/milestone_kind_routing.py \
       --milestone .servo/milestone/{milestone_id}.md
     ```

   - **Guard 2: `pre_milestone_intake_guard`** — Goal-driven milestone 的 create/upsert/activate/append_worktracks 前，调用 `pre_milestone_intake_guard.py`。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/pre_milestone_intake_guard.py \
       --intake-review .servo/repo/pre-milestone-intake-{id}.md
     ```

     只有 `intake_status == "ready"` 且各字段满足放行条件，或 `intake_status == "skipped"` 且 programmer 显式接受风险时，才允许继续。
   - **Guard 3: `complex_project_entry_gate_check`** — 调用 `complex_project_entry_gate_check.py` 检查 entry gate blocking。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/complex_project_entry_gate_check.py \
       --gate-source .servo/repo/pre-milestone-intake-{id}.md
     ```

     canonical guard term: not fixed heavy mode。scanner output is evidence, not verdict。这是一个 Milestone-side blocking gate；若 `reinforcement_milestone_recommendation.needed == true`，必须建议 reinforcement milestone 并阻断实现型 milestone 的 create/activate。gate 缺失、blank、placeholder、pending、incomplete 时，unresolved gate blocking default 强制返回 blocked，不得当作 not_applicable。Worktrack execution modes `normal`、`autoreview`、`yolo` 是 user-owned safety policy，不替代 Milestone-side blocker。`milestone_blocking_decision` 输出值含 `block_create`、`block_upsert`、`block_activate`、`block_derive_worktrack`。`operator_safety_policy` 记录 operator 自定义安全策略。`complexity_signals` 列出检测到的复杂度信号。`scanner_evidence_ref` 引用 scanner 输出的 JSON 证据路径。`dialog_review_questions` 包含需要 reviewer 确认的问题列表。
   - **Guard 4: `milestone_review_gate_check`** — 进入 WorktrackScope.Init 前，调用 `milestone_review_gate_check.py`。这是 Milestone Review Gate：一个 route guard，检查 milestone 级审查状态。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/milestone_review_gate_check.py \
       --control-state .servo/control-state.md
     ```

     `milestone_review_gate_ready` 允许继续；`milestone_review_gate_not_ready` 阻断。Gate 检查 `latest_review_status`、`milestone_review_count`、`latest_review_checkpoint`。`effective_review_pass` 和 `effective_pass` 是路由决策的缓存字段。`review_invalidated_by` 记录失效原因；若被 `invalidated`，gate 视为 not ready。`questions_required` 指示是否需要额外澄清问题。

   - **Guard 5: `runtime_backfill_detect`** — 调用 `runtime_backfill_detect.py` 检测缺失字段。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/runtime_backfill_detect.py \
       --artifact .servo/control-state.md
     ```

     缺失字段按 `false`、`unknown`、`missing`、`blocked`、`not ready` 解释。Guard terms: must not grant permissions, must not infer programmer confirmation, must not increment counters, must not enable Worktrack Init/Dispatch。保守运行时回填合同（conservative runtime backfill）要求 `forward-only`：只能补充缺失字段，不得回退已有字段值，不得重新解释已有语义。
   - **Guard 6: `worktrack_intake_review_check`** — 调用 `worktrack_intake_review_check.py`。

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/worktrack_intake_review_check.py \
       --intake-review .servo/repo/worktrack-intake-{id}.md
     ```

     只有 `intake_review_verdict == ready_for_worktrack_init` 且 `ready_for_worktrack_init == true` 才允许绑定 `worktrack-init-skill`。审查维度含 `repo_fundamentals`（仓库基本面）和 `snapshot_freshness`（快照新鲜度）。`milestone_purpose_alignment` 检查 worktrack 是否与 milestone 目标对齐。`historical_conflict_risk` 评估历史冲突风险。`worktrack_adjustment_recommendations` 和 `add_remove_worktrack_recommendations` 输出调整建议。若 `refresh_required`，必须先刷新基线再继续。若需 `adjust_worktracks`，在继续前调整 worktrack 列表。
   - **Guard 7: `ChangeGoal`** — 不由常规 Decide 选择。目标变更由外部请求触发，完成后系统重新进入 Observe。
   - **Guard 8: `milestone_brief`** — 当 `repo-whats-next-skill` 建议 create/activate/append_worktracks 时，Harness 必须先把结构化 `milestone brief` 交给 programmer 确认。

3. 在 `WorktrackScope` 下，评估是否需要：
   - `Init`（初始化局部状态）
   - `Observe`（状态估计）
   - `Decide`（调度）
   - `Dispatch`（分派执行）
   - `Verify`（收集证据）
   - `Judge`（裁决）
   - `Recover`（恢复）
   - `Close`（收尾）
4. 只推荐一个算子，并投影成显式路由、阻塞项集合与审批状态

### 10.3 技能绑定阶段

_已合并入 §10.4 前置段落。_

### 10.4 执行载体选择

本节承接 §2「两条执行路径」中的执行载体选择原则，将算子映射到具体的 Skill 实现并选择执行载体。

1. 为选定的 Skill 构建限定范围任务简报和信息包
2. **执行载体选择决策**：
   - 调用 `dispatch_mode_recommend.py` 执行确定性载体推荐：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/dispatch_mode_recommend.py \
       --task-coupling low|medium|high \
       --state-sharing low|medium|high \
       --parallel-value low|medium|high \
       --risk-profile low|medium|high \
       --context-budget-fit yes|no \
       --runtime-supports-subagent yes|no|unknown \
       --permission-allows-delegation yes|no|unknown \
       --dispatch-package-safe yes|no
     ```

   - 脚本输出 JSON 包含 `recommended_mode`、`confidence`、`reasons`、`needs_llm_review`。
   - 读取执行载体开关：先看 `.servo/control-state.md` 的 `subagent_dispatch_mode_override_scope`。默认 `worktrack-contract-primary` 表示当前 `Worktrack Contract` 的 `runtime_dispatch_mode` 优先；只有显式 `global-override` 才让 `.servo/control-state.md` 的 `subagent_dispatch_mode` 压过 worktrack。
   - `runtime_dispatch_mode` / `subagent_dispatch_mode` 支持 `auto` / `delegated` / `current-carrier`
3. **Dispatch Profile 完整性校验**：
   - 每次分派后调用 `dispatch_profile_check.py` 验证 `runtime_dispatch_profile` 字段完整性：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/dispatch_profile_check.py \
       --profile-json '<json>'
     ```

  - 必填字段包括 `backend_runtime`、`model_family`、`subagent_dispatch_shell`、`runtime_supports_subagent`、`subagent_permission_state`、`permission_allows_delegation`、`dispatch_package_safety`、`delegation_attempted`、`attempted_carrier`、`carrier_decision`、`fallback_reason`。
  - 若 profile 声称 spawned SubAgent 或 `carrier_decision: delegated_subagent`，还必须记录 `parent_runtime_dispatch_record_ref`、`spawned_subagent_record_ref`、`carrier_instance_id` 和 `isolation_boundary`。缺少 parent runtime dispatch linkage、child SubAgent record 或 concrete carrier instance 时，不得声称 SubAgent 隔离成立。若尝试委派 SubAgent 后实际使用 current-carrier，必须记录 `boundary_violation_recorded: true` 或等价运行时边界缺口。
4. `auto` 表示按 §2 Dispatch Decision Policy 选择 SubAgent、专用 skill、generic worker 或 current-carrier：综合 `task_coupling`、`state_sharing_need`、`parallel_value`、`risk_profile`、`context_budget_fit`、`runtime_supports_subagent`、`permission_allows_delegation` 与 `dispatch_package_safety`；高共享/低并行价值默认 current-carrier，低耦合/高并行价值且运行时允许时优先 SubAgent，高风险实现可保持当前载体但 review/test/policy evidence 应独立验证。运行时没有稳定分派壳层、权限边界禁止委派，或任务包不满足安全分派条件时，必须显式 fallback。
5. `delegated` 表示必须真实创建委派载体；如果无法委派，应返回运行时缺口或权限阻塞，而不是自动改为当前载体执行
6. `current-carrier` 表示本轮显式关闭 SubAgent 委派，允许当前载体在同一份限定范围约定内执行
7. 发生当前载体运行时回退时，必须显式记录回退原因、未委派原因和保持的任务/信息边界
8. 不要声称已经分派了子代理，除非宿主运行时真的创建了委派载体
9. 每轮 Dispatch 必须记录 `runtime_dispatch_profile`，至少包含 §10.4 步骤 3 列出的 11 个必填字段。在 ClaudeCodeCLI / Deepseek 兼容 lane 中，无法证明 SubAgent shell 可用时，不得静默 current-carrier；必须把 capability probe 与 fallback 证据写入 dispatch result 或 gate evidence。
10. **Milestone Gate 四轴分派偏好**：当 goal-driven milestone 的 `worktrack_list_finished == true` 时，Harness 推荐把四个 axis skills 作为 sibling delegated carriers 分派，并为每轴记录 `runtime_dispatch_profile`。`milestone-gate` 本身是 aggregation carrier，不应再在内部继续分派四轴。若运行时不支持 sibling carrier dispatch，记录 `axis_dispatch_profile.dispatch_model: current_carrier_fallback | missing`、`same_carrier_cross_axis` 和 `carrier_isolation_broken_any`；该缺口必须传入 `milestone-gate`，不得静默宣称四轴隔离达成。当前载体或 ambiguous spawned-axis claims 不能 masquerade 为真实 SubAgent；只有存在 parent runtime dispatch record、spawned SubAgent record、concrete carrier instance 和 isolation boundary 时，才能声明 spawned SubAgent carrier。

### 10.5 证据收集与裁决

本节合并原 §10.5（证据收集阶段）和 §10.6（裁决阶段）。

**证据收集**：

1. 消费子代理返回的结构化输出
2. 在 `Verify` 阶段，收集三个正交维度的证据：
   - 审查维度（代码正确性、结构合理性）
   - 验证维度（测试、验收条件）
   - 策略维度（规则、边界、不变量）
3. 证据必须结构化，不能是文字摘要

**裁决**：

1. 基于收集到的证据，执行 Gate 裁决
2. 在三个校验面上分别判定
3. 汇总生成最终 verdict：
   - `通过`
   - `软失败`
   - `硬失败`
   - `阻塞`

### 10.6 裁决阶段

_已合并入 §10.5。_

### 10.7 状态更新阶段

1. 根据裁决结果更新 `Harness Control State`
2. 如果是 `通过` → 进入 `Close`（内部执行 Self-Review → Single-Acceptance → Closeout Gate → PR → Merge → Doc-Catch-Up → Refresh → Cleanup）→ 回到 RepoScope
   - **显式绑定 `repo-refresh-skill`**，从已验证 `关卡证据` 刷新 `Repo Snapshot/Status`
   - 刷新完成后，调用 `checkpoint_writeback.py` 写入 observed checkpoint：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/checkpoint_writeback.py \
       --checkpoint-type observed \
       --control-state .servo/control-state-repo.md
     ```

   - 此脚本将当前 `git rev-parse HEAD` hash 写入 `.servo/control-state-repo.md` 的 `Baseline Traceability.latest_observed_checkpoint` 并追加 `verified_at_history` 时间戳。
3. 如果是 `失败/阻塞` → 进入 `Recover`。以下 5 种 recover mode 对应 control-state 迁移：

   | recover mode | control-state 迁移 | 触发条件 |
   |-------------|-------------------|---------|
   | `retry` | worktrack_state → `observing` | 目标与基准仍然有效 |
   | `rollback` | worktrack_state → `recovering`, 追加 `recovery_baseline_ref` | 当前状态已不可安全继续 |
   | `split_worktrack` | 当前 worktrack 标记 blocked，派生新 worktrack 并更新 milestone artifact | 范围过宽或多独立验收切片 |
   | `refresh_baseline` | 更新 `Baseline Traceability.latest_observed_checkpoint` | 上游真相变化使分支比较失效 |
   | `replan` | scope → `RepoScope`, function → `Observe` | 当前路径整体不可行 |

   恢复动作由 `worktrack-recover-skill` 执行。恢复成功后的收尾由 `worktrack-close-skill` 负责。
4. **文档追平收口**：在 Close、handback 或 release/post-smoke 收口前，如果本轮改变了代码版本、package/release 事实、git/SVN baseline、deploy/adapter 行为、验证命令或 operator-facing 文档，必须调用或显式安排 `worktrack-doc-catch-up-skill`。
   调用 `checkpoint_writeback.py` 写入 doc-catch-up checkpoint：

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/checkpoint_writeback.py \
     --checkpoint-type doc-catch-up \
     --control-state .servo/control-state-repo.md
   ```

5. **长期权限配置写回**：
   - 调用 `autonomy_policy_check.py` 判定当前操作是否命中 forbidden / stop_condition：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/autonomy_policy_check.py \
       --operation {observe|schedule|dispatch|verify|close|recover|change_goal|init_milestone|init_worktrack|cleanup|doc_catch_up} \
       --skill <skill_name> \
       --control-state .servo/control-state.md
     ```

   - `forbidden` 命中即阻断：

     **Low-Risk Default-Flow Autonomy Policy** forbidden boundaries: `goal change`（目标变更）、`scope expansion`（范围扩展）、`milestone final acceptance`（Milestone 最终验收）、`release / publish / package version / tag / dist-tag`（发布/打包/标签）、GitHub Release、`protected branch mutation`（受保护分支变更）、`force push`（强制推送）、大量文件删除、`destructive cleanup`（破坏性清理）、`secret/security/privacy`（密钥/安全/隐私）、`deploy/network/database migration`（部署/网络/数据库迁移）、`跨 repo 副作用`（跨仓库副作用）、外部付费/配额消耗。
   - `stop_condition` 命中即停止：证据缺失或冲突、分支不匹配、Gate 失败、上下文噪音/遗忘、需要程序员判断、权限边界不清、Contract 外扩、受保护分支策略命中、破坏性操作命中、发布敏感信号、Milestone 最终验收边界。`route decision` 需要已记录的确定性路由决策。`runtime dispatch profile` 需要完整的 runtime dispatch profile。`repo-refresh checkpoint` 需要已验证的 repo-refresh 检查点。
   - 连续执行或低风险 Worktrack 自批必须同时满足：`allowed` 命中、`forbidden` 未命中、`stop_condition` 未命中、`evidence_required` 已能满足或已安排。
   - 如果本轮经程序员明确批准了持久权限、自动性或分派策略变更，必须把配置事实写回 `.servo/control-state.md` 的 `Approval Boundary`、`Continuation Authority` 或 `Autonomy Ledger`，并记录审批理由；一次性审批只能写入本轮 evidence / handoff，不得伪装成长期默认配置。
6. **Milestone 状态写回**：
   - 调用 `writeback_bridge.py` 桥接 milestone-status-skill 输出到 repo-writeback-skill 期望格式：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/writeback_bridge.py \
       --milestone-id <id> \
       --instructions-json '<json>'
     ```

   - `writeback_bridge.py` 将 `writeback_instructions` 翻译为 `repo-writeback-skill` 可消费的多步指令格式。
   - 写回动作使用 repo-writeback-skill 作为 orchestrator 执行，不再使用 ad-hoc 字段写入。
   - 收到 `milestone-status-skill` 输出后，`harness-skill` 必须执行以下写回动作（按 `milestone_kind` 分化）：

   **Gate 状态透传**：`milestone-status-skill` 输出中的 gate 特定字段来自 `milestone-gate` skill 产出，由 sensor skill 透传到 writeback_instructions。Harness 按 writeback_instructions 逐字段写入，不自行解释 gate 语义。

   - **Final Acceptance 事务边界**：goal-driven milestone handback 前必须存在 composite acceptance report。goal-driven milestone 的最终验收由 programmer 决定。programmer 明确接受后，acceptance writeback 必须作为一个逻辑事务处理。该事务的最小写入集合为 `.servo/milestone/{milestone_id}.md`、`.servo/repo/milestone-backlog.md`、`.servo/repo/milestone-history.md`、`.servo/control-state.md`。写回后必须校验一致性。
   - **Milestone Artifact 更新**、**Control State 更新**、**Pipeline 推进**：按 `milestone-status-skill` 输出的 `writeback_instructions` 执行。
   - 若 `milestone_gate_verdict != "pass"`：不得把 Milestone 标记为完成，不得自动推进 pipeline。
7. 如果命中正式停止条件 → 向程序员返回控制权
8. **证据完整性检查**：
   - 在 Gate 裁决前，调用 `evidence_completeness_check.py`：

     ```bash
     PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/evidence_completeness_check.py \
       --evidence-file .servo/worktrack/gate-evidence.md
     ```

   - 脚本输出 JSON 包含 `complete`、`missing`、`present`、`checked_items`。检查 9 项必需证据：`route_decision`、`worktrack_contract_scope`、`selected_task_dispatch_packet`、`runtime_dispatch_profile`、`validation_evidence`、`governance_policy_evidence`、`gate_verdict`、`closeout_record`、`repo_refresh_checkpoint`。
9. **项目基本面刷新触发**：以下 5 个条件任意满足时触发刷新：
   - **Worktrack closeout 后**：merge → cleanup → 返回到 RepoScope 时刷新 Repo 级慢变量
   - **Milestone closeout 后**：Goal-driven milestone 被 programmer 接受后刷新全部 backlog 和 control-state
   - **Git hash 变更后**：`latest_observed_checkpoint` 与当前 HEAD 不一致时标记 `repo_baseline_changed: true`
   - **Pipeline 不一致检测**：milestone-backlog、worktrack-backlog、control-state 之间不一致时触发 pipeline 恢复
   - **Recovery 基线刷新**：§10.7 步骤 3 的 `refresh_baseline` 模式触发时，刷新 `latest_observed_checkpoint`
   - 以上触发条件是项目基本面刷新的最小必要时机；不得因为"未见明显变化"而跳过 closeout 后或 hash 变更后的刷新动作。

### 10.8 收尾规范

_（保留）_

### 10.9 Git Commit Hash 幂等性守卫

Harness 使用 git commit hash 作为幂等性锚点，避免对同一代码基线重复执行 `repo-refresh-skill` 和 `worktrack-doc-catch-up-skill`。

**存储位置**：`.servo/control-state-repo.md` 的 `Baseline Traceability` 段。`.servo/control-state.md` 只保留 root control fields、路径指针与控制面记忆。

**字段定义**：

| 字段 | 含义 | 更新时机 |
|------|------|---------|
| `latest_observed_checkpoint` | 上次 `repo-refresh-skill` 执行后记录的 git HEAD hash | `RepoScope.Refresh` 完成后由 `checkpoint_writeback.py --checkpoint-type observed` 写入 |
| `last_doc_catch_up_checkpoint` | 上次 `worktrack-doc-catch-up-skill` 执行后记录的 git HEAD hash | 文档追平完成后由 `checkpoint_writeback.py --checkpoint-type doc-catch-up` 写入 |
| `verified_at_history` | 最近一次 checkpoint 验证时间列表 | 每次 `checkpoint_writeback.py` 调用自动追加 |

**工作逻辑**：

```text
Harness 启动 → 状态估计阶段
  ├─ git_hash_check.py → 当前 hash
  ├─ 读取 latest_observed_checkpoint
  │   ├─ hash 一致 → repo_baseline_unchanged: true → 跳过 repo-refresh-skill
  │   └─ hash 不一致/缺失 → repo_baseline_changed: true → 绑定 repo-refresh-skill
  ├─ 读取 last_doc_catch_up_checkpoint
  │   ├─ hash 一致且本轮无文档变更 → 跳过 worktrack-doc-catch-up-skill
  │   └─ hash 不一致或有文档变更 → doc_catch_up_needed: true → 绑定 worktrack-doc-catch-up-skill
  └─ 继续正常控制回路

Close/Refresh 完成 → 状态更新阶段
  ├─ checkpoint_writeback.py --checkpoint-type observed → 写入 latest_observed_checkpoint = HEAD hash
  └─ checkpoint_writeback.py --checkpoint-type doc-catch-up → 写入 last_doc_catch_up_checkpoint = HEAD hash
```

**脚本引用**：

| 脚本 | 位置 | 用途 |
|------|------|------|
| `git_hash_check.py` | `./scripts/` | §10.1 步骤 5：读取并对比 hash |
| `checkpoint_writeback.py` | `./scripts/` | §10.7 步骤 2/4：写入 observed / doc-catch-up checkpoint |

**硬约束**：

- git hash 对比仅作为"跳过重复刷新"的条件，不得作为"跳过首次验证"的借口
- `doc-catch-up` 的 hash 对比只能跳过"代码未变且文档未变"的重复追平；如果本轮明确修改了文档，即使 hash 未变也必须触发文档追平检查

---

## 十一、正式停止条件

只有在以下至少一个条件成立时才停止并返回控制权：

- **`审批门控`**：目标变更、范围扩张、破坏性动作或其他权限边界把 `需要审批` 置为 `真`
- **`证据门控`**：所需产物或证据缺失、过期或互相矛盾，已经无法安全继续
- **`路由阻塞`**：当前路由命中 `软失败`、`硬失败`、`阻塞`，或抛出了显式 `继续阻塞项`
- **`运行时缺口`**：宿主运行时缺少供下一个执行载体使用的安全分派壳层
- **`约定边界`**：下一步动作将越出已批准的代码仓库或工作追踪约定

**`autonomy_policy_check.py` 输出 → 停止条件映射**：

| autonomy_policy_check 输出 | 对应停止条件 | 行为 |
|---|---|---|
| `blocked == true` | 路由阻塞 | 停止执行，返回 blocked reason |
| `stop_condition_hit == true` | 路由阻塞 | 停止执行，暴露具体 stop_condition |
| `forbidden_hit == true` | 审批门控 / 约定边界 | 停止执行，标记 needs_approval |
| `needs_approval == true` | 审批门控 | handback 等待 programmer |
| `evidence_required_complete == false` | 证据门控 | 停止执行，暴露 missing evidence |

---

## 十二、恢复策略

当 Gate 裁决为失败或阻塞时，Harness 必须进入恢复模式。合法恢复算子：

| 恢复算子 | 适用条件 | 限制 | 对应 §10.7 步骤 3 recover mode |
|---------|---------|------|------|
| `重试` | 当前目标、排除目标与基准仍然有效 | 不得扩大范围或重定义验收 | `retry` |
| `回滚` | 当前状态已不可安全继续 | 除非程序员明确批准，否则执行破坏性变更前必须停止 | `rollback` |
| `拆分 Worktrack` | 当前范围过宽或包含多个独立验收切片 | 不得静默创建新 Worktrack；必须明确验收标准分配 | `split_worktrack` |
| `刷新基准` | 上游真相变化使当前分支比较失效 | 不得改写 Repo Snapshot/Status 或目标/章程 | `refresh_baseline` |
| `重新规划` | 当前路径整体不可行 | 必须回到 RepoScope 重新 Decide | `replan` |

恢复策略由 `worktrack-recover-skill` 实现。Gate 裁决为失败或阻塞时，应绑定 `worktrack-recover-skill` 执行恢复动作；恢复成功后的收尾由 `worktrack-close-skill` 负责。

### Milestone Pipeline 恢复

当 Milestone Pipeline 出现不一致时，`harness-skill` 在 Observe 阶段应检测并执行以下恢复动作：

| 恢复动作 | 触发条件 | 操作 |
|---------|---------|------|
| `rebuild-pipeline` | milestone-backlog 损坏或与 `.servo/milestone/` 目录不一致 | 重新扫描 `.servo/milestone/` 目录，从 artifact 文件重建 milestone-backlog |
| `reconcile-active` | control-state `active_milestone` 指向不存在的 milestone | 清空 `active_milestone`，标记 `milestone_pipeline_stale: true`，触发 pipeline 重新评估 |
| `repair-binding` | worktrack-backlog 中存在 milestone_id 但对应 milestone 不存在 | 标记为 orphan binding，在 milestone-status-skill 输出中暴露，等待 programmer 决策 |
| `clear-stale-reference` | milestone artifact 文件存在但不在 backlog 中 | 按 artifact 文件重建 backlog 条目（保留原始 created_at/created_by） |

检测到以上任一情况时，`harness-skill` 应标记为 `pipeline_corruption_detected` 并执行相应恢复动作。恢复后重新绑定 `milestone-status-skill` 做完整状态评估。若自动恢复失败（如 artifact 文件本身损坏），必须 handback 等待 programmer 介入。

> 注：当前这些恢复动作由 harness-skill 以 LLM 推断方式检测。未来可考虑添加 `milestone_pipeline_check.py` 脚本提供确定性检测，与 §10.2 的 8-guard 链保持一致模式。

### Work-Collection 专属恢复

work-collection milestone（`milestone_kind == "work-collection"`）在以下场景有专属恢复路径：

| 恢复动作 | 触发条件 | 操作 |
|---------|---------|------|
| `defer-and-close` | work-collection 内单个 worktrack 阻塞且无法推进 | 将该 worktrack 标记为 deferred，完成剩余 worktrack 后正常关闭 milestone（标记 superseded）；被 defer 的 worktrack 由 programmer 决定重新归入或放弃 |
| `dissolve-collection` | work-collection 内所有 worktrack 均阻塞或 deferred | 关闭 milestone（标记 superseded），将所有 worktrack 释放为未归属状态，等待 programmer 重新分配 |

---

## 十三、输出规范

使用这个技能时，产出一份 `Harness 控制回路报告`。

### 通用核心字段

所有 Function 输出必须包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `current_scope` | string | 当前 Scope（RepoScope / WorktrackScope） |
| `current_function` | string | 当前 Function 算子 |
| `artifacts_read` | list | 本轮读取的 artifact 路径 |
| `status_or_verdict` | string | 状态或裁决结果 |
| `allowed_next_routes` | list | 允许的下一路由 |
| `recommended_next_route` | string | 推荐的下一路由 |
| `continuation_ready` | boolean | 是否可以继续推进 |
| `continuation_decision` | string | 继续决策说明 |
| `stop_conditions_hit` | list | 命中的停止条件 |
| `approval_required` | boolean | 是否需要审批 |
| `needs_approval` | boolean | 是否有待审批项 |
| `config_hydration_gaps` | list | 配置 hydration 缺口 |
| `persistent_authority_updates` | list | 长期权限变更记录 |

### Function 专项字段

各 Function 算子应附加以下专项字段：

| Function | 专项字段 |
|----------|---------|
| `Observe` | `estimated_state`, `sensor_readings`, `branch_context`, `repo_baseline_changed`, `repo_baseline_unchanged`, `doc_catch_up_needed`, `config_hydration_gaps` |
| `Decide` | `selected_operator`, `blocked_routes`, `approval_status`, `guard_results`（8 guards） |
| `Init` | `initialized_worktrack`, `branch_created`, `baseline_ref`, `contract_ref` |
| `Dispatch` | `dispatch_mode`, `execution_carrier`, `runtime_dispatch_profile`, `carrier_decision`, `decision_inputs` |
| `Verify` | `evidence_collected`, `review_findings`, `test_results`, `policy_check_results` |
| `Judge` | `gate_verdict`, `per_axis_verdict`, `blocking_findings` |
| `Recover` | `recover_mode`, `recovery_target`, `recovery_constraints` |
| `Close` | `closeout_commit`, `merge_target`, `cleanup_done`, `snapshot_refreshed` |
| `ChangeGoal` | `goal_diff`, `impact_analysis`, `approval_status` |
| `SetGoal` | `goal_charter_created`, `initialization_status` |

### 路由决策字段

| 字段 | 说明 |
|------|------|
| `recommended_next_scope` | 推荐的下一 Scope |
| `recommended_next_function` | 推荐的下一 Function |
| `continuation_blockers` | 继续阻塞项列表 |
| `handback_required` | 是否需要 handback |
| `handoff_state` | 当前交接状态 |
| `handback_lock_active` | 交接锁是否激活 |
| `handback_unlock_signal` | 解锁信号描述 |

---

## 十四、Artifact Output Protocol

所有 skill 产出的 artifact 必须遵守以下全局协议：

1. **先完整生成，再做压缩**：每个 skill 先生成尽可能长且完整的原始内容，确保信息不丢失；然后通过压缩步骤提取 `Control Signal` 层。
2. **控制结论优先**：影响下一动作决策的信息放在 `Control Signal` 层；完整证据、日志、原始输出放在 `Supporting Detail` 层。
3. **禁止平铺重复**：已在其他 artifact 中记录的信息，使用引用（文件路径 + section）而不是内联全文复制。
4. **空值压缩**：无实质内容的字段使用 `N/A`，删除占位符行（如 `-` 或 `待填写`）。
5. **引用格式**：引用其他 artifact 时使用 `[artifact-path#section]` 格式，例如 `[.servo/worktrack/contract.md#Task Goal]`。
6. **压缩不是省略**：`Supporting Detail` 层必须保留完整内容，只是不纳入传递/决策上下文；后续如需查阅细节，可直接读取。
7. **脚本输出是权威控制信号源**：所有 guard、check 和 routing 决策必须优先消费当前技能包 `./scripts/` 下对应脚本的结构化 JSON 输出，不得用 LLM 自行推断替代确定性脚本结果。脚本返回 `blocked == true` 即硬阻断，不得覆盖。

---

## 十五、硬约束

遵循本包内最小公共约束 C-1 至 C-8：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close/ChangeGoal/SetGoal 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。

本技能特有约束：

- **Harness 输出只能是控制决策结构体**（Scope/Function/Route/Verdict/Evidence 引用）；代码块和直接执行指令禁止出现在 Harness 输出中。
- **Function 算子必须在控制面上显性化**为 `Observe → Decide → Init → Dispatch → Verify → Judge → Recover → Close → ChangeGoal → SetGoal` 的控制语义；禁止仅通过技能名称隐式传达当前算子。
- **Harness 仅负责选择算子、绑定技能和裁决 Gate**；具体代码仓库动作、任务列表内容和执行任务的细节由下游技能的算子实现负责。
- **SubAgent 使用必须是可开关参数，而不是硬编码行为。** 控制态字段 `subagent_dispatch_mode` 与工作追踪约定字段 `runtime_dispatch_mode` 支持 `auto` / `delegated` / `current-carrier`；控制态字段 `subagent_dispatch_mode_override_scope` 默认是 `worktrack-contract-primary`，只有显式 `global-override` 才是全局覆盖；默认 `auto` 表示按 Dispatch Decision Policy 选择载体（调用 `dispatch_mode_recommend.py`），不得把运行时支持 SubAgent 单独当成默认委派理由。未委派时必须将原因记录为 `runtime fallback`、`permission blocked` 或 `dispatch package unsafe`。
- **执行载体选择必须走确定性决策流程**：先调用 `dispatch_mode_recommend.py` 获取推荐模式，再结合 `subagent_dispatch_mode` / `runtime_dispatch_mode` 开关确定最终载体；每轮 Dispatch 后必须调用 `dispatch_profile_check.py` 验证 runtime_dispatch_profile 字段完整性。
- **`autonomy_policy_check.py` forbidden 命中时必须 handback，不得静默继续。** `forbidden` 命中后即使 `allowed` 字段为 true，也必须将控制权交回 programmer，等待审批或显式解除阻断。
- **现有 `.servo` 控制配置必须先 hydration 再决策。** Harness 不得忽略上一轮 `.servo/control-state.md` 中的 linked artifact、approval boundary、continuation authority、handback guard、baseline traceability 或 autonomy ledger；缺失字段只能按 artifact 合同默认值降级解释，不能静默扩大权限。
- **长期权限变更必须写回控制配置。** 程序员授予的持久自动性、分派模式、审批边界或预算变更必须写入 `.servo/control-state.md` 的配置段；若只是本轮一次性批准，必须保留为本轮 evidence / handoff，不得改变长期默认值。
- **约定后自动工作追踪仅当 `Harness Control State` 明确授予 `约定后自动性：最小委派` 时才可开启**；否则必须保持手动交接模式。
- **自动继续推进的边界严格等于当前 `Worktrack Contract` 的 scope**；超出 scope 的改动、目标重定义或预算超支必须触发审批门控。
- **自动切片仅可在当前切片未收束时串接**；一旦切片收束且 `要求自动切片后停止` 为真，必须停止执行并重新交接。
- **稳定交接达成后，运行时唯一合法状态是 `等待交接`**；仅当观测到显式解锁信号时方可退出此状态。
- **解锁信号必须是程序员显式发出的新指令或实质性新信息**；裸 `重试`、裸 `继续工作` 或重复文字摘要不构成解锁信号。
- **交接锁激活时，所有控制回路阶段的进入必须被阻断**；仅当有效解锁信号出现后控制回路方可恢复。

**Handback Lock 激活流程**：

1. 每次 handback 时 `harness-skill` 检查 `handback_reaffirmed_rounds`
2. 若当前 handoff 与前次相同（上下文未变化）→ increment `handback_reaffirmed_rounds`
3. 若 `handback_reaffirmed_rounds >= stable_handback_threshold` → 设置 `handback_lock_active = true`
4. Lock 激活后，仅显式 programmer unlock signal 可解除
5. 若收到新的实质性 programmer 输入（不同上下文）→ reset `handback_reaffirmed_rounds = 0`

**Unlock 验证流程**（在 §10.1 Observe 阶段执行）：

1. 若 `handback_lock_active == true`：检查 `last_unlock_signal`
2. 有效 unlock signal 条件：programmer 显式发出的新指令或实质性新信息（非裸 `重试`/`继续`/重复摘要）
3. 验证通过 → 设置 `handback_lock_active = false`，记录 `last_unlock_signal`，清空 `handback_reaffirmed_rounds`
4. 验证失败 → 保持 lock，返回 blocked

Unlock signal 结构化格式：

```
- source: "programmer"
- instruction: "具体的新指令文本"
- timestamp: "ISO8601"
- confirmation: "unlock MS-XXXX-XXX" 或等效显式确认
```

- **技能轮次返回结构化输出是正常控制回路产物**；停止条件仅由 [十一、正式停止条件] 定义的正式条件触发。
- **Evidence、Verdict 和 NextAction 必须在输出中分节独立呈现**；每节仅包含对应类型的内容，禁止将三者合并为一段叙述。
- **相邻系统的引用仅当本轮证据确实消费了其输出时才可包含**；否则 `adjacent_system_referenced` 必须为 `false`。
- **Control State 仅保存控制面位置信息**（Scope/Function/Route）；业务真相必须保存在 `Repo` 与 `Worktrack` 的正式文档中，禁止写入 Control State。
- **git hash 一致仅授权跳过重复刷新和重复文档追平**；首次验证和 Gate 裁决在任何情况下都不可跳过。
- **分支环境守卫（Branch Environment Guard）**：任何会改变代码状态的 Function 必须先通过 `branch_context_check.py` 匹配合法 `branch_context`。
- **控制态规范化**：如果 control-state.md 出现重复 key（如多个 `- verified_at:`、重复的 singleton key），应在 hydration 后调用 `normalize_control_state.py` 消除歧义：

  ```bash
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/normalize_control_state.py \
    --input .servo/control-state.md
  ```

---

## 十六、资源

使用当前 `Harness Control State`、当前 Scope 所需的正式产物，以及下游技能的结构化输出作为本轮的权威依据。

判断下一次合法继续推进是否被允许时，应优先使用下游结构化输出，而不是本地叙述性摘要。所有 guard 决策必须优先消费当前技能包 `./scripts/` 下对应脚本的结构化 JSON 输出（见 §10.2 的 8 个 guard 脚本调用和 §10.7 的 `autonomy_policy_check.py` 引用）。

三轴参考：

- `Scope` 回答"在什么层上控制"
- `Function` 回答"控制器此刻在做什么"（10 个算子：`Observe` / `Decide` / `Init` / `Dispatch` / `Verify` / `Judge` / `Recover` / `Close` / `ChangeGoal` / `SetGoal`）
- `Artifact` 回答"控制器依赖什么正式对象"

---

## 十七

_（本节已删除，内容合并入 §13 输出规范）_
