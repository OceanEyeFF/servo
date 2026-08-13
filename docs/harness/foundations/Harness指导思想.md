---
title: Harness 指导思想
status: active
updated: 2026-08-11
owner: servo-kernel
last_verified: 2026-08-11
---

# Harness 指导思想

> 本文只保存 Harness 的稳定设计原则。具体入口、字段、步骤、停止条件和写入权限由对应 canonical `SKILL.md` 及 package-local scripts 管理。

## 定义

Harness 是对 Repo 演进过程的分层闭环控制系统。它维护目标与当前状态之间的可观察差异，选择合法的下一步，把工作交给有边界的执行载体，并依据独立证据决定是否允许状态推进。

Harness 不是直接编码的主体，不是 backend wrapper，不是把 Skills 固定串联起来的开环流程，也不在普通工作中自行改写 Programmer 已批准的目标。

## Agent 灰盒测试边界（规划原则）

Pi 等 Agent 的灰盒测试是独立的 operator-testing 能力：它把模型内部决策保持为黑盒，只对工具、权限、目标状态、worker 结果和证据链等执行边界建立可观察、可复核的事实。它不是普通 Repo / Milestone / Worktrack Harness 的隐含实现细节，也不应由每个已规划工作重新临时搭建。

该能力应在独立项目与明确 owner 下演进，拥有可版本化的场景格式、冻结输入、隔离 runner、事件适配、证据封存、结果判定和恢复合同。当前实验 Lab 只产生该抽取方向的诊断证据；在形成稳定、可发布的独立合同前，不得把某次实验的通过结论泛化为通用 Skill、Pi、worker 或 sandbox 结论。

对日常 Worktrack，只消费已发布的灰盒测试能力及其稳定 result ref；是否启动、扩展场景、改变判定语义或重新执行付费测试，必须由对应 operator 显式批准。

## 分层

- `Repo`：维护长期目标、主线状态、Milestone 编排和跨 Worktrack 一致性。
- `Milestone`：把长期目标拆成可验收的 contribution，并在全部相关 Worktrack 完成后判断组合目标是否达成。
- `Worktrack`：承接一个清楚的任务入口，在独立 branch 上完成 PlanWork、Review、redo 和 Close，再把完成结果交回上层。

上层负责提供清楚的输入和消费模块结果；下层负责自己的 operational contract。任何一层都不应为了兼容旧调用方而吸收另一层的 mapping、判断或恢复逻辑。

## Milestone 文档原则

每个已规划 Milestone 只有一份 canonical document，负责保存 `milestone_id`、revision、`draft | planned` maturity、`open | finished | superseded` planned disposition、目标与范围、跨 Worktrack 决定、Milestone-level acceptance、声明式 Worktrack TodoList、amendment、Harness 接受的稳定 Worktrack result refs，以及最终 Gate 与验收 refs。完整对话、未采用方案、Agent 推理、backlog、snapshot、progress counter 和 status projection 都不是 Milestone 真相或恢复前提；`active` 与 `current` 只由 Harness 的 `active_milestone_ref` 表达。

planned Milestone 可以声明稳定 branch contract：`milestone_branch` 是其集成分支，`baseline_ref` 是不可变的创建来源，`close_target` 是最终集成目标。该合同不表示当前 checkout 或 live HEAD。Harness 负责观察当前 Git 状态、选择每次 Worktrack 的确切 source checkpoint 并把它冻结进 immutable initial requirement；Worktrack 完成后回到声明的 Milestone branch。planned 后改变 branch contract 与改变其他业务语义一样，必须形成更高 revision 和 amendment，且不得改写已有 Worktrack requirement 或 verdict。

Milestone TodoList entry 只声明 `worktrack_id`、一句话 outcome、依赖或执行条件、`required | conditional | deferred | superseded` condition、覆盖的 acceptance IDs、`result_ref`，以及确有冲突风险时的一条简短 boundary hint。它不保存 branch、queue、round、carrier 或执行阶段。`[x]` 当且仅当同一 entry 已登记 Harness 接受的稳定 `result_ref`；执行、Review、redo 或 Close 本身不会改变 checkbox。

draft 可以丢弃；planned 业务真相的变化必须使用下一 revision，并在 amendment 中记录改动、原因、受影响 Worktracks、仍有效与需要重验的 evidence，以及 approval ref。对同一 ID、revision 和 canonical content 的重复提交是零写入 `already_applied`；同一 ID/revision 的不同内容是 conflict；更低或跳号 revision 必须拒绝。

Harness 只把接受的稳定 Worktrack 结果登记回 Milestone，并通过直接读取 canonical TodoList、当前 acceptance、amendments 和稳定 result/final refs 回答普通状态问题。该观察零写入，不选择下一 Worktrack，也不允许 projection 或 cache 成为第二套裁决真相。Milestone Init 的具体交互、验证、原子写入和 handoff 合同由 canonical Skill package 自己承接。

## 控制与执行

Harness 主对话负责观察、选择、分派、聚合和状态写回。PlanWork、独立 Review、Milestone axes 等执行工作可以由 SubAgent 承载；SubAgent 之间不直接调用，是否继续、返工或切换层级由上层 Orchestrator 决定。

普通工作可由 current-carrier 在明确 scope、mutation boundary、stop condition 和 validation requirement 内执行。独立性有实际价值时才使用独立 carrier；不设置额外通用执行 Skill 也不意味着没有执行边界。

## Worktrack 原则

Candidate Worktrack 的主线是：

```text
Repo/Milestone
→ worktrack-plan-work-skill
→ independent worktrack-review-skill
→ redo loop 或 ready_to_close
→ worktrack-close-skill
→ Repo Refresh / Milestone
```

- PlanWork 负责 setup synthesis、branch、计划、实现、受影响验证和 redo。
- Review 独立读取初始要求、完整 round chain、实现 checkpoint 和 evidence，负责技术验收。
- Close 只处理已经 `ready_to_close` 的 Worktrack，完成 merge、持久 handback 和 Repo Refresh handoff，不重新进行技术判断。
- Skill 必须在未预读外部 Harness docs 时仍能直接理解和运行。
- `.servo/tmp/<worktrack-id>/` 是临时 round handoff，不是长期文档真相。

## 证据与权限

证据说明发生了什么，审批说明允许做什么，两者不能互相替代。实现载体不能批准 scope、objective 或 acceptance 扩大；Review 不能批准 mission change；Close 不能把未通过的技术结果提升为完成。

当证据不足、权限缺失、checkpoint stale 或 mutation 越界时，系统应停止并把明确 request 交回拥有权限的上层，而不是从旧字段、评论正文或兼容路径猜测结论。

## Truth Ownership

- `AGENTS.md`：agent-facing 最小仓库规则与阅读路由。
- 本文：稳定 Harness doctrine。
- `product/harness/skills/*/SKILL.md`：每个 Skill 的完整 operational contract。
- package-local scripts/references/assets：随 Skill 分发的确定性实现和内部依赖。
- `docs/project-maintenance/`：项目维护、部署和治理规则。
- `.servo/`：当前 repo 的运行控制面和 handoff，不是跨项目文档层。
- `.agents/`、`.claude/`：deploy target，不是 canonical source。

新增规则时先确定 owner。Skill 私有步骤不复制到 docs，跨层接口不复制 Skill 内部流程，临时运行数据不升格为长期 truth。删除其他 `docs/harness/` 文件后，canonical Skill 仍必须能够仅凭自身 package 完成工作。
