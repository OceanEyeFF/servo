---
title: "servo-installer External Trial Governance"
status: active
updated: 2026-05-05
owner: servo-kernel
last_verified: 2026-05-05
---
# servo-installer External Trial Governance

> 目的：定义 post-RC `servo-installer` 外部试用的目标列表模板与反馈合同。

本页属于 [Governance](./README.md)。

- trial_status: planned
- trial_sources: programmer-owned repos + forum volunteer repos
- future_npm_publish_allowed: false
- public_recruitment_copy: false
- private_repo_identifiers_in_long_term_docs: false
- supported_backend: `agents`
- feedback_decision_goal: determine next main contradiction (adoption/reliability/documentation)

## Trial Target Categories

| Category | Purpose | Minimum count | Privacy rule |
| --- | --- | ---: | --- |
| programmer-owned repository | first realistic trial under trusted operator control | 2 | store only aliases unless explicit approval allows names |
| forum volunteer repository | observe cold external operator friction | 2 | store only anonymized aliases and consented facts |
| intentionally unsupported repository | confirm failure messaging and recovery path | 1 | store only anonymized shape and failure category |

不在长期文档中存储私有仓库名、URL、token、含 secret 的日志或用户 handle，除非另行批准。

## Command Feedback Fields

每个 trial 报告应包含：target alias/category、candidate version/source、install 命令、shell/runtime 路径、脱敏 log、命令结果（help/version/tui/diagnose/update/install/verify）、operator confusion、adoption blocker、reuse intent、trust concern、workflow-fit concern、recovery attempted、final verdict。

## Operator Confusion Taxonomy

`entrypoint-confusion` / `backend-confusion` / `target-root-confusion` / `update-boundary-confusion` / `approval-boundary-confusion` / `diagnose-output-confusion` / `docs-navigation-confusion` / `no-confusion-observed`

## Decision Criteria

首批外部试用后归类主要矛盾：install/verify 多目标失败 -> reliability；命令通过但 operator 选不对路 -> documentation；理解 doc 但不采用 -> adoption；失败集中在未支持 repo 形态 -> target compatibility；困惑在 update/publish 预期 -> release-channel communication。

最低门槛：至少 2 个 programmer-owned target 完成或失败并有证据；至少 1 个 volunteer 完成或命名具体 blocker；不需要 private identifier 即可理解结果。

## Related Documents

- [servo-installer Release Channel Governance](./servo-installer-release-channel-governance.md)
- [npx Command Test Execution](../../testing/npx-command-test-execution.md)
- [trial feedback issue template](../../../../.github/ISSUE_TEMPLATE/servo-installer-trial-feedback.yml)
- [bug/blocker issue template](../../../../.github/ISSUE_TEMPLATE/servo-installer-bug.yml)
