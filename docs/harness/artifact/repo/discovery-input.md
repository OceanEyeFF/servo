---
title: "Repo Discovery Input"
status: active
updated: 2026-04-25
owner: servo-kernel
last_verified: 2026-06-13
---
# Repo Discovery Input

`Repo Discovery Input` 是 Existing Code Project Adoption 模式下的只读事实输入,记录 Harness 初始化前对既有代码库的观察结果。运行落位为 `.servo/repo/discovery-input.md`。

## Purpose

只承接"看见了什么"：现有目录/模块/入口/构建/测试线索、已存在文档/约定/配置/脚本/治理提示、分支/基线/未提交变更/已知风险、可追溯事实、待确认问题、不确定点。不承接"项目应该变成什么"；长期目标、成功标准和系统不变量仅可进入 `goal-charter.md` 且须用户确认。

> **一次性使用**：`discovery-input.md` 是 Existing Code Project Adoption 模式下的初始化前只读事实采集 artifact。它在 Harness 初始化（`repo-init-goal-skill`）时生成一次，之后不再主动更新。后续 repo 观测由 `repo/snapshot-status.md` 承接。若项目在初始化后新增模块、变更结构或迁移工具链，这些变化应写入 `snapshot-status.md`，而不是回头修改 `discovery-input.md`。

## Non-Authority

`discovery-input.md` 仅作为探索性输入。将推测性产品愿景写成已确认目标、将现有实现倒推为用户同意的长期方向、替代 `goal-charter.md` 或 `repo/snapshot-status.md`、直接驱动 worktrack 拆分、作为覆盖用户目标的依据的行为不得发生。与用户确认冲突时以 `goal-charter.md` 为准;与后续观测冲突时以 `repo/snapshot-status.md` 为准。

## Relationship To Other Repo Artifacts

- **`goal-charter.md`**:`discovery-input.md` 可作为 `repo-init-goal-skill` 起草 Goal Charter 的事实依据,但仅提供候选信息;`goal-charter.md` 是用户确认后的长期目标 truth。
- **`repo/snapshot-status.md`**:`discovery-input.md` 是初始化前采集输入;`snapshot-status.md` 是初始化后的 repo 慢变量观测面,可引用 discovery 作为来源,但应按确认状态重写/归纳/纠正。
- **`control-state.md`**:可链接 `discovery-input.md` 作为 adoption 证据,不得将 discovery 字段提升为控制指令。

## Minimum Shape

`discovery-input.md` 最少应包含:

- metadata
- adoption mode
- source materials
- repository facts
- architecture and module inventory
- build, test, and runtime signals
- governance and documentation signals
- risks and unknowns
- candidate goal signals
- confirmation questions
- downstream mapping notes

`candidate goal signals` 只能写可追溯候选项,不能写成已批准目标。
