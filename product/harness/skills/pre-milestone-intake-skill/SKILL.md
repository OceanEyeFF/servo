---
name: pre-milestone-intake-skill
description: 当需要在创建、更新或激活 Milestone 前对用户需求做一轮限定范围核实、追问、挑战和推荐，并产出 pre_milestone_intake_review 时，使用这个技能。
---

# Pre-Milestone Intake Skill

## 概览

把这个技能作为 `RepoScope` 下的 Milestone 前置 intake / grill gate 使用。

本技能运行在 `init-milestone-skill` 之前。它接收 programmer 的自然语言需求、已有 repo truth、当前控制状态和最小代码仓库上下文，先把需求整理为可确认的 milestone brief 草案，再识别模糊点、风险点、范围扩张点和需要 programmer 决策的地方。它的输出是结构化 `pre_milestone_intake_review`，供 `init-milestone-skill` 消费。

本技能不创建 milestone，不写入 `.servo/milestone/`，不更新 milestone-backlog，不创建 worktrack，不修改代码，不替 programmer 确认业务目标。

## 何时使用

以下情况应使用本技能：

- 新建 goal-driven milestone。
- 用户需求模糊，例如"优化一下"、"完善一下"、"重构一下"、"做一个方案"。
- 涉及 release、publish、migration、数据、权限、安全、兼容性或部署边界。
- 涉及多 repo、跨系统、跨团队或 integration acceptance。
- 涉及大型无文档或弱文档代码库。
- 涉及 Harness doctrine、artifact contract、canonical skill 或 workflow family 变更。
- `init-milestone-skill` 准备 create / upsert / activate，但 milestone brief 仍依赖未确认假设。

以下情况可轻量跳过，但必须记录跳过理由：

- 用户给出明确、低风险、单文件或单模块的小修复。
- 当前 active milestone 下执行已确认 worktrack。
- 纯只读检查或验证。
- 用户明确要求不追问并接受风险。

## 工作流

1. 确认这是一轮 Milestone 前置 intake，不是 milestone 初始化、worktrack 初始化或实现执行。
2. 读取当前需求、Goal Charter、Repo Snapshot、Control State、live milestone-backlog，以及回答当前问题所需的最小 repo context。
3. 将输入分为：
   - `observed_facts`：可从 repo 或已给输入直接证明的事实；
   - `inferred_assumptions`：模型推断但未确认的假设；
   - `unknowns`：影响 scope、risk 或 acceptance 的未知项；
   - `programmer_decisions_required`：必须由 programmer 决策的事项。
4. 生成 `request_summary` 和 `suggested_milestone_brief` 草案，至少包含 title、purpose、scope、non_goals、candidate worktracks、completion signals、acceptance criteria、risk flags。
5. 执行 grill gate：
   - 优先提出 3 到 5 个最高杠杆问题；
   - 每个问题必须说明为什么要问；
   - 每个问题必须给出 recommended answer；
   - 每个 recommended answer 必须说明取舍影响；
   - 能从 repo 查到的事实先查，不把可发现事实全部推给 programmer。
6. 判定是否 ready：
   - 若关键 scope、non-goal、acceptance 或 risk boundary 缺失，`ready_for_init_milestone = false`；
   - 若剩余未知项不影响安全初始化，可记录 residual risk 并设置 ready；
   - 若 programmer 已确认必要问题，设置 `programmer_confirmed = true`。
7. 输出结构化 `pre_milestone_intake_review`。
8. 停止并交给 `init-milestone-skill` 或返回 programmer；本技能不得自行写入/激活 milestone。

## 硬约束

遵循 [docs/harness/foundations/skill-common-constraints.md] 中定义的公共约束 C-1 至 C-7。

- 不得创建、更新或激活 milestone。
- 不得创建 worktrack 或执行实现。
- 不得把 inferred assumptions 写成 programmer-confirmed truth。
- 不得一次性提出大量低价值问题；问题应限于本轮 highest leverage。
- 每个 open question 必须携带 recommended answer 和 tradeoff。
- 当 high-risk trigger 命中且缺少 programmer confirmation 时，必须设置 `ready_for_init_milestone = false`。
- 若用户明确要求跳过 intake，应记录 `intake_skipped = true`、`skip_reason` 和 `accepted_risk`，不得假装已经完成 grill gate。
- 本技能输出的 milestone brief 是草案；只有 `init-milestone-skill` 可以写入 artifact 和 backlog。

## 预期输出

使用本技能时，产出一份至少包含以下章节的 `pre_milestone_intake_review`：

- `Intake Status`
- `Request Summary`
- `Observed Facts`
- `Inferred Assumptions`
- `Unknowns`
- `Risk Flags`
- `Open Questions`
- `Recommended Answers`
- `Scope Boundary`
- `Non Goals`
- `Acceptance Signals`
- `Suggested Milestone Brief`
- `Confirmation State`
- `Handoff To Init Milestone`

字段至少包含：

- `intake_status`: ready / questions_required / blocked / skipped
- `request_summary`
- `observed_facts`
- `inferred_assumptions`
- `unknowns`
- `risk_flags`
- `open_questions`
- `recommended_answers`
- `scope_boundary`
- `non_goals`
- `acceptance_signals`
- `suggested_milestone_brief`
- `confirmation_required`
- `programmer_confirmed`
- `ready_for_init_milestone`
- `intake_skipped`
- `skip_reason`
- `accepted_risk`
- `handoff_to_init_milestone`

## 资源

使用当前需求、`.servo/goal-charter.md`、`.servo/repo/snapshot-status.md`、`.servo/control-state.md`、`.servo/repo/milestone-backlog.md`，以及本轮核实所需的最小 repo context。对大型无文档 repo，应参考 [docs/harness/workflow-families/large-undocumented-repo-onboarding.md]；对多 repo 项目，应参考 [docs/harness/workflow-families/multi-repo-project-workflow.md]。
