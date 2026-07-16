---
title: Harness 指导思想
status: active
updated: 2026-07-16
owner: servo-kernel
last_verified: 2026-07-16
---

# Harness 指导思想

> 本文只保存 Harness 的稳定设计原则。具体入口、字段、步骤、停止条件和写入权限由对应 canonical `SKILL.md` 及 package-local scripts 管理。

## 定义

Harness 是对 Repo 演进过程的分层闭环控制系统。它维护目标与当前状态之间的可观察差异，选择合法的下一步，把工作交给有边界的执行载体，并依据独立证据决定是否允许状态推进。

Harness 不是直接编码的主体，不是 backend wrapper，不是把 Skills 固定串联起来的开环流程，也不在普通工作中自行改写 Programmer 已批准的目标。

## 分层

- `Repo`：维护长期目标、主线状态、Milestone 编排和跨 Worktrack 一致性。
- `Milestone`：把长期目标拆成可验收的 contribution，并在全部相关 Worktrack 完成后判断组合目标是否达成。
- `Worktrack`：承接一个清楚的任务入口，在独立 branch 上完成 PlanWork、Review、redo 和 Close，再把完成结果交回上层。

上层负责提供清楚的输入和消费模块结果；下层负责自己的 operational contract。任何一层都不应为了兼容旧调用方而吸收另一层的 mapping、判断或恢复逻辑。

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
