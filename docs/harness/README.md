# Harness

`docs/harness/` 是当前仓库的 Harness-first 文档主线，承接 Harness doctrine、runtime protocol、scope、artifact contracts、skill inventory 与 workflow family policy。

本文只做 Harness 文档域入口导航：帮助读者选择最近 owner 和下一跳路径，不承载 doctrine、runtime protocol、artifact contract、workflow policy 或历史迁移规则。

## 当前分层

| 层 | 路径 | 功能 |
| --- | --- | --- |
| 思路层 | [foundations/README.md](./foundations/README.md) | 说明 Harness 为什么这样运行、运行时共同遵守的原则，以及控制面如何选择载体和推进状态 |
| 架构层 | [scope/README.md](./scope/README.md) | 说明 `RepoScope`、`WorktrackScope` 与两层状态闭环 |
| 架构层 | [artifact/README.md](./artifact/README.md) | 说明 Repo / Worktrack / Control 正式对象和字段 |
| 架构层 | [workflow-families/README.md](./workflow-families/README.md) | 说明多个 worktrack 如何组成稳定流程 |
| 实现映射层 | [catalog/README.md](./catalog/README.md) | 说明这些结构在 Codex skill 体系里对应哪些入口 |

## 阅读边界

| 路径 | 何时读取 |
| --- | --- |
| `foundations/` | 查 Harness 为什么这样运行、runtime protocol、停顿/交接/继续、dispatch 载体选择和跨 skill 约束 |
| `scope/` | 查 RepoScope、WorktrackScope 或 scope 间状态转移 |
| `artifact/` | 查运行时对象字段、证据、队列、control state、milestone 或 worktrack 合同 |
| `catalog/` | 查有哪些 skill、每个 skill 的职责摘要、控制层级和状态 |
| `workflow-families/` | 查一组 worktrack 如何组成可复用流程或 policy profile |

完整 docs 阅读顺序、章节边界和路径维护规则见 [../book.md](../book.md)。Agent boot 与 route contract 见 [../../AGENTS.md](../../AGENTS.md)。

## Owner 边界

| 主题 | 权威 owner |
| --- | --- |
| Doctrine / 指导思想 | [foundations/README.md](./foundations/README.md) |
| Runtime protocol / 运行协议 | [foundations/README.md](./foundations/README.md) |
| Scope / 状态闭环 | [scope/README.md](./scope/README.md) |
| Artifact contracts / 正式对象字段 | [artifact/README.md](./artifact/README.md) |
| Skill inventory / skill 清单 | [catalog/README.md](./catalog/README.md) |
| Workflow policy / workflow family | [workflow-families/README.md](./workflow-families/README.md) |
| Executable root / 实现层入口 | [../../product/harness/README.md](../../product/harness/README.md) |
| Executable skill source / 可执行技能源 | [../../product/harness/skills/README.md](../../product/harness/skills/README.md) |

Model/runtime 支持边界见 [foundations/model-runtime-support.md](./foundations/model-runtime-support.md)。该页记录 Deepseek、Claude、Pi、GPT/CodeX 等执行载体的已测试支持状态，但不替代 Worktrack Contract、Gate evidence 或 release approval。

未升格的方案分析、迁移比较或实现前设计不作为当前 docs truth 层长期保留；先留在 Harness runtime/backlog 或工作追踪证据中，等内容验证后再升格到对应 owner。

`catalog/` 不承接 doctrine、runtime protocol、artifact contract、workflow policy、方案分析或 executable source。若 catalog 页面为了定位 skill 而引用这些内容，只能作为摘要和反向链接；权威正文仍在对应 owner。
