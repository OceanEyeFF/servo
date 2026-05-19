# Deploy Runbooks

`docs/project-maintenance/deploy/` 包含 deploy 主路径与部署后维护。发布治理、外部试用治理和 backend 使用说明已迁出。测试执行、本地 `.tgz` smoke、registry `npx` smoke、Codex/Claude 部署后行为观察统一放在 [Testing Runbooks](../testing/README.md)。

## 单一管理原则

| 文档 | 只管理什么 | 不再管理什么 |
| --- | --- | --- |
| [deploy-runbook.md](./deploy-runbook.md) | 首次安装与完整重装的三步主流程 | 诊断分流、发布流程、pack/smoke 细节 |
| [skill-deployment-maintenance.md](./skill-deployment-maintenance.md) | `diagnose`/`verify` 与恢复分流 | 首次安装、发布、testing 执行 |
| [distribution-entrypoint-contract.md](./distribution-entrypoint-contract.md) | `aw-installer` CLI/TUI 包装层语义 | operator runbook、发布步骤 |
| [deploy-mapping-spec.md](./deploy-mapping-spec.md) | canonical source/payload/target 映射合同 | operator 执行步骤、release 流程 |
| [payload-provenance-trust-boundary.md](./payload-provenance-trust-boundary.md) | payload source kind、source/target root、GitHub source trust boundary | release channel、任意 remote update |
| [harness-version-marker-contract.md](./harness-version-marker-contract.md) | `product/harness/skills/harness-skill/VERSION` 标记的格式、语义与 operator 解读规则 | package version、npm publish、release channel |
| [existing-code-adoption.md](./existing-code-adoption.md) | 既有代码库接入 Harness 时的 `.aw/repo/discovery-input.md` 生成边界 | artifact 正文、skill workflow 实现 |

## 按问题进入

| 问题 | 入口 |
| --- | --- |
| 首次安装或完整重装 | [deploy-runbook.md](./deploy-runbook.md) |
| 已有安装，判断 drift/conflict/unrecognized | [skill-deployment-maintenance.md](./skill-deployment-maintenance.md) |
| 确认 canonical source 到 target 的正式映射 | [deploy-mapping-spec.md](./deploy-mapping-spec.md) |
| 确认 package/CLI/TUI 必须保持的语义 | [distribution-entrypoint-contract.md](./distribution-entrypoint-contract.md) |
| 查看 payload provenance 与 update trust boundary | [payload-provenance-trust-boundary.md](./payload-provenance-trust-boundary.md) |
| 查看 Harness payload 版本标记语义与 operator 解读规则 | [harness-version-marker-contract.md](./harness-version-marker-contract.md) |
| 既有代码库接入 Harness | [existing-code-adoption.md](./existing-code-adoption.md) |
| 改 skills 或 `.aw_template/` 后的 operator 决策 | [Usage Help](../usage-help/README.md) |
| package/registry smoke 或部署后行为观察 | [Testing Runbooks](../testing/README.md) |
| 发布准入、发布顺序或试用治理 | [Governance](../governance/README.md) |

## 当前主线口径

安装主流程、wrapper、mapping、trust boundary 由各自合同页承接。deploy target 不是 source of truth。release/testing/usage help 不在 deploy 下留副本。

## 已移除的内容

一次性 release approval、historical smoke evidence、Codex/Claude 行为测试副本、registry `npx` smoke runbook 副本、多页面双主线说明。

## 模板消费

`product/.aw_template/` 是 repo-local execution template layer，为 `.aw/` 提供 scaffold 样例。它不是 artifact truth、skill deploy source 或 backend payload source。

保留 `control-state.md`、`goal-charter.md`、`repo/`、`worktrack/`、`template/` 结构位。`repo/` 与 `worktrack/` 对应 `.aw/repo/` 与 `.aw/worktrack/` 落位；`template/` 用于不直接进入 `.aw/` 的回答流模板。

不应长期归属 `.aw_template/` 的对象：`contract`、`plan-task-queue`、`gate-evidence`、goal change/correction 类回答流。其 artifact truth 由 `docs/harness/artifact/` 定义；可执行模板应由 owning skill 或 `set-harness-goal-skill/assets/` 承担。

`.aw_template/` 不参与 skill 部署包分发，是 legacy `.aw/` scaffold 来源而非 payload descriptor、backend payload 或 target install 设计。`aw_scaffold.py` 已随 P0-067 Python cleanup 移除，不再作为 scaffold 工具。

停止线：需改变 artifact 结构时先改 `docs/harness/artifact/`；需改变 skill 初始化资产时先改 owning skill；需改变 deploy target install 行为时回 deploy mapping/entrypoint/provenance 合同页。
