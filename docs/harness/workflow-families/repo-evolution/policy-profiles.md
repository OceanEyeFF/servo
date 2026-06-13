---
title: "Policy Profiles"
status: superseded
updated: 2026-05-09
owner: servo-kernel
last_verified: 2026-06-13
---
# Policy Profiles

> **状态：已废弃。** Policy profile 概念已收敛到 `docs/harness/foundations/skill-common-constraints.md` 的 C-1 至 C-7 公共约束，以及 `servo-harness-skill/SKILL.md` 的两层控制律。本文档保留为历史引用。

> 目的（历史）：将可复用的 workflow 经验收敛成 profile/variant。

当前处理原则：

- workflow/profile 名称只作为 profile 语义来源，不直接作为 repo 当前 skill/source 入口
- 若后续重新引入 policy profile，先在 `docs/harness/` 固定 profile 语义，再决定是否需要新的 executable package

这些 profile 经验可继续复用其 prompt（提示词）、gate（关卡）、entrypoint（入口）设计，但不承接 Harness 主线定义。
