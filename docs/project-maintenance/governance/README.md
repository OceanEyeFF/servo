---
title: "Governance"
status: active
updated: 2026-05-17
owner: servo-kernel
last_verified: 2026-06-13
---
# Governance

`docs/project-maintenance/governance/` 保存 review、gate、检查、branch/PR 治理规则，以及 servo-installer 发布治理。分支治理基线由 `origin/HEAD` 动态解析，当前已确认解析结果为 `origin/HEAD -> master`。

## 单一管理原则

### 核心治理

| 文档 | 只管理什么 | 不再管理什么 |
| --- | --- | --- |
| [review-verify-handbook.md](./review-verify-handbook.md) | plan→implement→verify→review→writeback 五步复核闭环与入口 | 具体检查脚本实现、发布流程 |
| [path-governance-checks.md](./path-governance-checks.md) | 路径治理与文档治理的最小回归检查命令和本地执行方式 | review 流程、branch/PR 规则 |
| [branch-pr-governance.md](./branch-pr-governance.md) | 分支创建/命名/合并约束与 PR 审批边界 | review 内容标准、发布准入 |
| [global-language-style.md](./global-language-style.md) | 跨任务可读输出的默认风格与收口约束 | 具体文档格式、代码规范 |

### 发布治理

servo-installer 发布治理已归入独立子目录，入口见 [servo-installer/README.md](./servo-installer/README.md)。

| 文档 | 只管理什么 | 不再管理什么 |
| --- | --- | --- |
| [servo-installer/README.md](./servo-installer/README.md) | servo-installer 发布操作模型、渠道准入、发布流程、pre-publish 就绪边界、外部试用治理 | 具体发布执行步骤（见子文档） |

## 按场景进入

| 场景 | 入口 |
| --- | --- |
| 完成 worktrack 后做 review/verify 收口 | [review-verify-handbook.md](./review-verify-handbook.md) |
| 新增/移动/删除文档后跑治理检查 | [path-governance-checks.md](./path-governance-checks.md) |
| 创建分支或 PR 前确认规则 | [branch-pr-governance.md](./branch-pr-governance.md) |
| 统一 AI 输出风格与判断收口 | [global-language-style.md](./global-language-style.md) |
| 确认当前发布模型与注册渠道 | [servo-installer/servo-installer-release-operation-model.md](./servo-installer/servo-installer-release-operation-model.md) |
| 发布前检查就绪状态 | [servo-installer/servo-installer-pre-publish-governance.md](./servo-installer/servo-installer-pre-publish-governance.md) |
| 执行候选版本发布流程 | [servo-installer/servo-installer-release-standard-flow.md](./servo-installer/servo-installer-release-standard-flow.md) |
| 查看或更新 npm 发布渠道准入规则 | [servo-installer/servo-installer-release-channel-governance.md](./servo-installer/servo-installer-release-channel-governance.md) |
| 管理外部试用目标与反馈 | [servo-installer/servo-installer-external-trial-governance.md](./servo-installer/servo-installer-external-trial-governance.md) |
| 部署相关治理 | [../deploy/README.md](../deploy/README.md) |
| 测试执行与 smoke | [../testing/README.md](../testing/README.md) |

## 非本目录内容

| 内容 | 权威位置 |
|------|---------|
| Deploy runbook 与安装流程 | [../deploy/README.md](../deploy/README.md) |
| 测试执行、smoke、行为观察 | [../testing/README.md](../testing/README.md) |
| Backend 使用差异与场景路由 | [../usage-help/README.md](../usage-help/README.md) |
| 根目录分层规则 | [../foundations/README.md](../foundations/README.md) |
| Harness 跨模块指导思想 | [../../harness/foundations/Harness指导思想.md](../../harness/foundations/Harness指导思想.md) |
| Skill operational contract | [../../../product/harness/skills/README.md](../../../product/harness/skills/README.md) |

## 已移除的内容

一次性 release approval 记录、historical smoke evidence，以及已迁至 testing/ 的测试执行说明。
