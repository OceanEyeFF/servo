---
title: "Append Request Routing"
status: active
updated: 2026-05-25
owner: servo-kernel
last_verified: 2026-06-13
---
# Append Request Routing

> 目的：固定 `repo-evolution` family 下 append-feature / append-design / append-milestone 追加请求的分类与路由规则。

## 定位

追加请求 intake 发生在执行前，回答"这条新增要求应进入哪条控制路由"。支持 append-feature、append-design 和 append-milestone 三个 mode，由同一个 `repo-append-request-skill` 承接。

## 分类结果

### goal change

追加请求改变 repo 长期参考信号：改变愿景/核心目标/成功标准/系统不变量、需修改 Engineering Node Map、与现有 Goal Charter 冲突。下一路由：`repo-change-goal-skill`。

### new milestone

追加请求属于 Milestone Pipeline 层：需要创建新 milestone、注册 planned milestone、激活符合条件的 milestone，或向已有 milestone 追加 worktrack 并触发 coverage review。下一路由：`milestone-init-skill`。输出必须包含 milestone brief 边界、`suggested_milestone_action`、RepoScope 路由和审批字段；在 milestone brief 未确认前不得写入或激活。

### new worktrack

追加请求在 repo 目标内但应独立成为新 worktrack：不属于活跃 worktrack 批准范围、可绑定到 Node Map 候选 node type、需独立 branch/baseline/contract/plan/gate。下一路由：`worktrack-init-skill`。

### scope expansion

追加请求扩大活跃 worktrack：存在活跃 worktrack、请求不在已批准范围内、会改变验收/影响模块/风险/验证要求/完成定义。下一路由：scope-expansion-approval，审批后才允许更新 contract 或重新初始化。

### design-only

追加请求只要求设计判断/产物：设计结果可独立验收、证据不足不进入实现、append-design 默认优先考虑该类。下一路由：设计型 worktrack，产出 design artifact 后返回 gate。

### design-then-implementation

追加请求先设计再实现：用户明确要求、feature 风险或架构不确定性要求先形成设计结论、设计是 implementation 的前置 gate。下一路由：两阶段 worktrack，第一阶段 design gate 后才允许 implementation。

## 优先级

goal change 优先于所有其他分类。append-milestone 默认优先归为 new milestone；但如果用户要求把新目标塞进当前活跃 worktrack，则按 scope expansion 停在审批边界。scope expansion 与 new worktrack 冲突时以用户是否要求纳入活跃 worktrack 为判定点。append-design 仅在用户明确授权实现时才归为 design-then-implementation。分类证据不足时返回最小缺失信息。

## 输出

路由结果包含 mode、原始请求、分类结果与理由、目标影响、Milestone Pipeline 影响、活跃 worktrack 影响、下一路由与 scope、suggested_milestone_action（如适用）、权限边界、最小缺失信息、continuation readiness。

## Continuation 规则

`approval_required`/`continuation_ready`/`continuation_blockers` 保持一致：需新审批或 authority boundary 未满足时 `approval_required: true`、`continuation_ready: false`；goal change 与 scope expansion 默认停在审批边界；缺失信息阻塞分类或路由时 `continuation_ready: false`、在 `continuation_blockers` 中列出；无待审批项且无阻塞性缺失信息时才允许 `continuation_ready: true`，但本 workflow 仍只返回推荐 route。

## 非目标

不执行 feature/design/milestone 创建、创建 branch、改写 Goal Charter、milestone-backlog 或 worktrack contract、或替代 `repo-whats-next-skill` 的 repo 级判断。
