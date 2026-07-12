---
title: "根目录索引"
status: active
updated: 2026-05-14
owner: servo-kernel
last_verified: 2026-05-14
---
# 根目录索引

> 用来按任务目标快速定位当前主线入口。项目定位看 [`README.md`](./README.md)，任务分流看本页。

## 默认启动

Agent 默认只读 [`AGENTS.md`](./AGENTS.md)、本页，以及当前任务命中的一个局部入口。下列基础合同只在任务需要时扩读，不作为默认预加载清单。

## 按需扩读基础合同

| 触发条件 | 入口 |
|------|------|
| 查看 docs 全量阅读顺序、章节边界和路径维护规则 | [`docs/book.md`](./docs/book.md) |
| 进入项目维护主线 | [`docs/project-maintenance/README.md`](./docs/project-maintenance/README.md) |
| 进入 Harness 主线 | [`docs/harness/README.md`](./docs/harness/README.md) |
| 建立根目录边界 | [`docs/project-maintenance/foundations/root-directory-layering.md`](./docs/project-maintenance/foundations/root-directory-layering.md) |
| 建立路径与文档治理边界 | [`AGENTS.md`](./AGENTS.md) |

## 按任务进入

| 任务目标 | 入口 |
|------|------|
| 理解项目目标、承接结构和根目录分层 | [`README.md`](./README.md) |
| 看文档真相层、全量阅读顺序、章节边界与路径维护规则 | [`docs/book.md`](./docs/book.md) |
| 看 Harness 主线与分层合同 | [`docs/harness/README.md`](./docs/harness/README.md) |
| 改执行前工作追踪边界 | [`docs/harness/artifact/worktrack/contract.md`](./docs/harness/artifact/worktrack/contract.md) |
| 改 Worktrack PlanWork / Review / Close 运行合同 | [`product/harness/skills/README.md`](./product/harness/skills/README.md) 后进入对应 `SKILL.md` |
| 改阅读路由或写回规则 | [`AGENTS.md`](./AGENTS.md) / [`review-verify-handbook.md`](./docs/project-maintenance/governance/review-verify-handbook.md) |
| 改业务源码 | [`product/README.md`](./product/README.md) |
| 改工具脚本、部署或评测 | [`toolchain/README.md`](./toolchain/README.md) |
| 使用或排查 `servo-installer` 分发 | [`docs/servo-installer/README.md`](./docs/servo-installer/README.md) |
| 查看 Codex / Claude backend 使用差异 | [`docs/project-maintenance/usage-help/README.md`](./docs/project-maintenance/usage-help/README.md) |
| 运行 npx / package smoke 或部署后行为观察 | [`docs/project-maintenance/testing/README.md`](./docs/project-maintenance/testing/README.md) |
| 确认 release channel、publish 或外部试用治理 | [`docs/project-maintenance/governance/README.md`](./docs/project-maintenance/governance/README.md) |
| 看 repo-local runbook | [`docs/project-maintenance/README.md`](./docs/project-maintenance/README.md) |
| 运行路径治理检查 | [`docs/project-maintenance/governance/path-governance-checks.md`](./docs/project-maintenance/governance/path-governance-checks.md) |
| 看 agent-facing 最小规则 | [`AGENTS.md`](./AGENTS.md) |

## 根目录对象怎么理解

- `product/`：业务代码唯一源码根
- `docs/`：文档真相与知识主线
- `toolchain/`：脚本、部署、测试、评测工具
- `.servo/`：runtime control-plane state，只有运行 Harness 控制回路时按需读取
- `.agents/`、`.claude/`：repo-local mount / deploy target
- `.autoworkflow/`、`.spec-workflow/`：repo-local state / config
- `.nav/`：compatibility navigation
- `tools/`：compatibility shim，真实实现仍归 `toolchain/scripts/test/`

## 默认先不要读

- `.agents/`
- `.claude/`
- `.servo/`（除非当前任务是 Harness control state hydration / runtime artifact 读写）
- `.autoworkflow/`
- `.spec-workflow/`
- `.nav/`

## 停止继续扩读的条件

- 已确认任务落在 `product/`、`docs/` 或 `toolchain/` 的哪一块正式内容区
- 已定位到最小局部入口
- 继续扩读只会重复背景，而不会增加决策价值
