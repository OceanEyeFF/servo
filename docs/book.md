---
title: "Docs Book Spine"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Docs Book Spine

`docs/book.md` 是 `docs/` 的 canonical book-style spine：它定义当前版本中实际存在的完整阅读顺序、章节边界、文档分组关系和路径维护规则。`docs/README.md` 只做入口导航；具体规则正文仍以对应章节内的承接文档为准。

Owner：`servo-kernel`。边界：只覆盖当前 `docs/` 文档分层与阅读路线，不替代 `AGENTS.md` 的 agent boot 规则，不承接 `product/` 源码合同或 `toolchain/` 脚本合同。

## How To Read

1. 先读 [docs/README.md](./README.md) 确认 `docs/` 的入口定位。
2. 回到本页，按 [Full Reading Order](#full-reading-order) 从上到下阅读。Active 条目是当前主线；Retained Historical References 只为路径覆盖和历史追溯保留，不作为当前 truth owner。
3. 需要执行任务时，停在最近章节入口，不要继续扩读不相关章节。
4. 新增、移动、删除或重命名文档时，先按 [Docs Path Maintenance](#docs-path-maintenance) 同步本页、最近章节入口和旧路径引用。

## Full Reading Order

### Part 1：项目基础

了解项目是什么、如何组织、如何上手使用。

#### 1.0 Orientation

1. [docs/README.md](./README.md)

#### 1.1 根目录分层

1. [project-maintenance/foundations/README.md](./project-maintenance/foundations/README.md)
2. [project-maintenance/foundations/root-directory-layering.md](./project-maintenance/foundations/root-directory-layering.md)

#### 1.2 项目上手

1. [project-maintenance/repo-onboarding.md](./project-maintenance/repo-onboarding.md)

#### 1.3 使用帮助

1. [project-maintenance/usage-help/README.md](./project-maintenance/usage-help/README.md)
2. [project-maintenance/usage-help/quickstart.md](./project-maintenance/usage-help/quickstart.md)
3. [project-maintenance/usage-help/recommended-usage.md](./project-maintenance/usage-help/recommended-usage.md)
4. [project-maintenance/usage-help/usage-flow-examples.md](./project-maintenance/usage-help/usage-flow-examples.md)
5. [project-maintenance/usage-help/init-greenfield.md](./project-maintenance/usage-help/init-greenfield.md)
6. [project-maintenance/usage-help/init-with-code.md](./project-maintenance/usage-help/init-with-code.md)
7. [project-maintenance/usage-help/goal-change-guide.md](./project-maintenance/usage-help/goal-change-guide.md)
8. [project-maintenance/usage-help/codex.md](./project-maintenance/usage-help/codex.md)
9. [project-maintenance/usage-help/claude.md](./project-maintenance/usage-help/claude.md)

---

### Part 2：Harness 内核

理解 Harness 控制系统的思想、架构和运行机制。

#### 2.0 Harness 入口

1. [harness/README.md](./harness/README.md)

#### 2.1 思想层（Foundations）

1. [harness/foundations/README.md](./harness/foundations/README.md)
2. [harness/foundations/Harness指导思想.md](./harness/foundations/Harness指导思想.md)
3. [harness/foundations/Harness运行协议.md](./harness/foundations/Harness运行协议.md)
4. [harness/foundations/runtime-control-loop.md](./harness/foundations/runtime-control-loop.md)
5. [harness/foundations/runtime-dispatch-contract.md](./harness/foundations/runtime-dispatch-contract.md)
6. [harness/foundations/runtime-evidence-gate-recovery.md](./harness/foundations/runtime-evidence-gate-recovery.md)
7. [harness/foundations/runtime-closeout-refresh.md](./harness/foundations/runtime-closeout-refresh.md)
8. [harness/foundations/runtime-state-hydration.md](./harness/foundations/runtime-state-hydration.md)
9. [harness/foundations/dispatch-decision-policy.md](./harness/foundations/dispatch-decision-policy.md)
10. [harness/foundations/model-runtime-support.md](./harness/foundations/model-runtime-support.md)
11. [harness/foundations/skill-common-constraints.md](./harness/foundations/skill-common-constraints.md)

#### 2.2 控制范围（Scope）

1. [harness/scope/README.md](./harness/scope/README.md)
2. [harness/scope/repo-scope.md](./harness/scope/repo-scope.md)
3. [harness/scope/worktrack-scope.md](./harness/scope/worktrack-scope.md)

#### 2.3 正式对象（Artifact）

1. [harness/artifact/README.md](./harness/artifact/README.md)
2. [harness/artifact/standard-fields.md](./harness/artifact/standard-fields.md)
3. [harness/artifact/repo/README.md](./harness/artifact/repo/README.md)
4. [harness/artifact/repo/discovery-input.md](./harness/artifact/repo/discovery-input.md)
5. [harness/artifact/repo/complex-project-entry-gate.md](./harness/artifact/repo/complex-project-entry-gate.md)
6. [harness/artifact/repo/goal-charter.md](./harness/artifact/repo/goal-charter.md)
7. [harness/artifact/repo/repo-analysis.md](./harness/artifact/repo/repo-analysis.md)
8. [harness/artifact/repo/snapshot-status.md](./harness/artifact/repo/snapshot-status.md)
9. [harness/artifact/repo/worktrack-backlog.md](./harness/artifact/repo/worktrack-backlog.md)
10. [harness/artifact/repo/decision-log.md](./harness/artifact/repo/decision-log.md)
11. [harness/artifact/repo/milestone-backlog.md](./harness/artifact/repo/milestone-backlog.md)
12. [harness/artifact/repo/milestone-history.md](./harness/artifact/repo/milestone-history.md)
13. [harness/artifact/worktrack/README.md](./harness/artifact/worktrack/README.md)
14. [harness/artifact/worktrack/contract.md](./harness/artifact/worktrack/contract.md)
15. [harness/artifact/worktrack/plan-task-queue.md](./harness/artifact/worktrack/plan-task-queue.md)
16. [harness/artifact/worktrack/dispatch-packet.md](./harness/artifact/worktrack/dispatch-packet.md)
16. [harness/artifact/worktrack/gate-evidence.md](./harness/artifact/worktrack/gate-evidence.md)
17. [harness/artifact/worktrack/debug-evidence.md](./harness/artifact/worktrack/debug-evidence.md)
18. [harness/artifact/control/README.md](./harness/artifact/control/README.md)
19. [harness/artifact/control/control-state.md](./harness/artifact/control/control-state.md)
20. [harness/artifact/control/milestone.md](./harness/artifact/control/milestone.md)
21. [harness/artifact/control/composite-milestone-acceptance.md](./harness/artifact/control/composite-milestone-acceptance.md)
22. [harness/artifact/control/append-request.md](./harness/artifact/control/append-request.md)
23. [harness/artifact/control/goal-change-request.md](./harness/artifact/control/goal-change-request.md)
24. [harness/artifact/control/node-type-registry.md](./harness/artifact/control/node-type-registry.md)

#### 2.4 技能目录（Catalog）

1. [harness/catalog/README.md](./harness/catalog/README.md)
2. [harness/catalog/supervisor.md](./harness/catalog/supervisor.md)
3. [harness/catalog/repo.md](./harness/catalog/repo.md)
4. [harness/catalog/worktrack.md](./harness/catalog/worktrack.md)
5. [harness/catalog/milestone/README.md](./harness/catalog/milestone/README.md)
6. [harness/catalog/milestone/init-milestone-skill.md](./harness/catalog/milestone/init-milestone-skill.md)
7. [harness/catalog/milestone/milestone-status-skill.md](./harness/catalog/milestone/milestone-status-skill.md)

#### 2.5 工作流族（Workflow Families）

1. [harness/workflow-families/README.md](./harness/workflow-families/README.md)
2. [harness/workflow-families/repo-evolution/README.md](./harness/workflow-families/repo-evolution/README.md)
3. [harness/workflow-families/repo-evolution/append-request-routing.md](./harness/workflow-families/repo-evolution/append-request-routing.md)
4. [harness/workflow-families/large-undocumented-repo-onboarding.md](./harness/workflow-families/large-undocumented-repo-onboarding.md)
5. [harness/workflow-families/multi-repo-project-workflow.md](./harness/workflow-families/multi-repo-project-workflow.md)

---

### Part 3：维护治理

如何维护、验证和治理项目质量。

#### 3.0 维护入口

1. [project-maintenance/README.md](./project-maintenance/README.md)

#### 3.1 治理规则

1. [project-maintenance/governance/README.md](./project-maintenance/governance/README.md)
2. [project-maintenance/governance/review-verify-handbook.md](./project-maintenance/governance/review-verify-handbook.md)
3. [project-maintenance/governance/path-governance-checks.md](./project-maintenance/governance/path-governance-checks.md)
4. [project-maintenance/governance/global-language-style.md](./project-maintenance/governance/global-language-style.md)
5. [project-maintenance/governance/branch-pr-governance.md](./project-maintenance/governance/branch-pr-governance.md)

#### 3.2 测试验证

1. [project-maintenance/testing/README.md](./project-maintenance/testing/README.md)
2. [project-maintenance/testing/test-lane-taxonomy.md](./project-maintenance/testing/test-lane-taxonomy.md)
3. [project-maintenance/testing/dogfood-target-repo-registry.md](./project-maintenance/testing/dogfood-target-repo-registry.md)
4. [project-maintenance/testing/python-script-test-execution.md](./project-maintenance/testing/python-script-test-execution.md)
5. [project-maintenance/testing/npx-command-test-execution.md](./project-maintenance/testing/npx-command-test-execution.md)
6. [project-maintenance/testing/codex-post-deploy-behavior-tests.md](./project-maintenance/testing/codex-post-deploy-behavior-tests.md)
7. [project-maintenance/testing/claude-post-deploy-behavior-tests.md](./project-maintenance/testing/claude-post-deploy-behavior-tests.md)

#### 3.3 社区推广

1. [project-maintenance/community/README.md](./project-maintenance/community/README.md)
2. [project-maintenance/community/linuxdo-release-post-v061.md](./project-maintenance/community/linuxdo-release-post-v061.md)

---

### Part 4：部署分发

如何部署、发布和分发 servo-installer。

#### 4.0 部署入口

1. [project-maintenance/deploy/README.md](./project-maintenance/deploy/README.md)

#### 4.1 servo-installer

1. [servo-installer/README.md](./servo-installer/README.md)

##### 4.1.1 合约（Contracts）

1. [servo-installer/contracts/distribution-entrypoint-contract.md](./servo-installer/contracts/distribution-entrypoint-contract.md)
2. [servo-installer/contracts/deploy-mapping-spec.md](./servo-installer/contracts/deploy-mapping-spec.md)
3. [servo-installer/contracts/aw-runtime-upgrade-contract.md](./servo-installer/contracts/aw-runtime-upgrade-contract.md)
4. [servo-installer/contracts/aw-residue-classification-contract.md](./servo-installer/contracts/aw-residue-classification-contract.md)
5. [servo-installer/contracts/payload-provenance-trust-boundary.md](./servo-installer/contracts/payload-provenance-trust-boundary.md)
6. [servo-installer/contracts/version-marker-contract.md](./servo-installer/contracts/version-marker-contract.md)

##### 4.1.2 运行手册（Runbooks）

1. [servo-installer/runbooks/deploy-runbook.md](./servo-installer/runbooks/deploy-runbook.md)
2. [servo-installer/runbooks/aw-runtime-upgrade-runbook.md](./servo-installer/runbooks/aw-runtime-upgrade-runbook.md)
3. [servo-installer/runbooks/skill-deployment-maintenance.md](./servo-installer/runbooks/skill-deployment-maintenance.md)
4. [servo-installer/runbooks/distribution-maintenance-checklist.md](./servo-installer/runbooks/distribution-maintenance-checklist.md)
5. [servo-installer/runbooks/uninstall-remove-runbook.md](./servo-installer/runbooks/uninstall-remove-runbook.md)

##### 4.1.3 参考（Reference）

1. [servo-installer/reference/managed-files-ownership.md](./servo-installer/reference/managed-files-ownership.md)
2. [servo-installer/reference/existing-code-adoption.md](./servo-installer/reference/existing-code-adoption.md)
3. [servo-installer/reference/legacy-version-handling.md](./servo-installer/reference/legacy-version-handling.md)
4. [servo-installer/reference/tui-aw-runtime-migration-repro.md](./servo-installer/reference/tui-aw-runtime-migration-repro.md)

##### 4.1.4 TUI

1. [servo-installer/tui/README.md](./servo-installer/tui/README.md)
2. [servo-installer/tui/human-cli-contract.md](./servo-installer/tui/human-cli-contract.md)
3. [servo-installer/tui/bundle-default-contract.md](./servo-installer/tui/bundle-default-contract.md)

#### 4.2 发布治理

1. [project-maintenance/governance/servo-installer/README.md](./project-maintenance/governance/servo-installer/README.md)
2. [project-maintenance/governance/servo-installer/servo-installer-release-operation-model.md](./project-maintenance/governance/servo-installer/servo-installer-release-operation-model.md)
3. [project-maintenance/governance/servo-installer/servo-installer-release-channel-governance.md](./project-maintenance/governance/servo-installer/servo-installer-release-channel-governance.md)
4. [project-maintenance/governance/servo-installer/servo-installer-release-standard-flow.md](./project-maintenance/governance/servo-installer/servo-installer-release-standard-flow.md)
5. [project-maintenance/governance/servo-installer/servo-installer-pre-publish-governance.md](./project-maintenance/governance/servo-installer/servo-installer-pre-publish-governance.md)
6. [project-maintenance/governance/servo-installer/servo-installer-external-trial-governance.md](./project-maintenance/governance/servo-installer/servo-installer-external-trial-governance.md)

---

### Retained Historical References

These links are kept for explicit reading-order coverage and historical traceability only. They are `status: superseded` and do not act as current Harness truth owners.

1. [harness/workflow-families/repo-evolution/standard-worktrack.md](./harness/workflow-families/repo-evolution/standard-worktrack.md)
2. [harness/workflow-families/repo-evolution/policy-profiles.md](./harness/workflow-families/repo-evolution/policy-profiles.md)

## Chapter Boundaries

### Part 1：项目基础

新文档属于 Part 1，当它回答的是"这个项目是什么、怎么组织和怎么开始使用"。涉及根目录边界时，优先进入 `project-maintenance/foundations/`；涉及使用场景或 backend 差异时，优先进入 `project-maintenance/usage-help/`。

### Part 2：Harness 内核

`docs/harness/` 承接 Harness-first 主线，分成思路层、架构层和实现映射层。未升格的方案分析、迁移比较或实现前设计不作为当前 docs truth 层长期保留。

Harness 子章节放置规则：

- **Foundations**：Harness 指导思想、runtime protocol、跨 skill 公共约束和执行载体选择策略。
- **Scope**：`RepoScope`、`WorktrackScope` 与状态闭环。
- **Artifact**：Harness 正式对象合同，包括 repo/worktrack/control artifact 与标准字段。
- **Catalog**：Codex skill catalog、控制层级映射；可执行源仍归 `product/harness/skills/`。
- **Workflow Families**：可复用 workflow family policy；superseded historical references 不作为当前主线 owner。

新文档属于 Part 2，当它回答的是"Harness 如何思考、调度、记录证据、判定、交接或沉淀 workflow"。

### Part 3：维护治理

`docs/project-maintenance/governance/` 和 `docs/project-maintenance/testing/` 承接维护治理层：review/verify 流程、路径治理检查、语言风格规范、分支/PR 治理、测试 runbook 和 dogfood 注册表。

新文档属于 Part 3，当它回答的是"如何维护这个仓库的质量和一致性"。涉及治理规则时，优先进入 `project-maintenance/governance/`；涉及测试、smoke 或验证命令时，优先进入 `project-maintenance/testing/`。

### Part 4：部署分发

`docs/project-maintenance/deploy/`、`docs/servo-installer/` 和 `docs/project-maintenance/governance/servo-installer/` 承接部署分发层：部署入口、servo-installer 合约/runbook/参考/TUI 文档，以及发布渠道治理。

新文档属于 Part 4，当它回答的是"如何部署、发布和分发 servo-installer"。涉及 deploy 行为时，优先进入 `project-maintenance/deploy/`；涉及 installer 合约和 runbook 时，优先进入 `servo-installer/`；涉及发布渠道、版本策略和外部试用时，优先进入 `project-maintenance/governance/servo-installer/`。

## Grouping And Relationships

- `README.md` 是局部章节入口，只解释该目录的定位和最近路线；不要在 README 中复制完整规则正文。
- 整理章节 `README.md` 时，先写清本文目的，再用一层 `路径 | 功能/何时读取` 表路由到最近 owner；删除服务于 repo 历史、跨层表达或表意不明的迁移段落，把长期规则正文下沉到对应 owner 文档。
- 章节入口里的 executable/source handoff 只保留必要链接；若需要同时指向实现层 root 和具体 source，说明它们是下游实现入口，不要把它们写成 doctrine、artifact 或 workflow owner。
- `docs/book.md` 是当前版本的全量书目和阅读顺序，必须直接链接 `docs/` 下除自身外的每个当前 markdown 文件。
- 承接文档保存规则正文；book 只写章节边界、顺序、分组关系和维护规则。
- docs truth surface 只描述当前已经存在的文档拓扑、owner 和维护规则；未来迁移计划、后续 Worktrack seed 或尚未落地的重构切片不得作为长期 docs 正文保留。
- 一个主题只能有一个稳定主线 owner。若两个章节都需要引用同一主题，非 owner 章节只链接到 owner，不复制正文。
- 跨章节依赖要在相关文档中用相对链接表达，不能只依靠文件路径相邻或读者搜索。

## Placement Checklist

新增或移动文档前，按顺序判断：

1. 是项目基础/使用帮助吗？放 Part 1（`project-maintenance/foundations/` 或 `project-maintenance/usage-help/`）。
2. 是 Harness doctrine、runtime、scope、artifact、catalog 或 workflow 吗？放 Part 2（`harness/` 的最近子章节）。
3. 是维护治理/测试验证吗？放 Part 3（`project-maintenance/governance/` 或 `project-maintenance/testing/`）。
4. 是部署/发布/分发吗？放 Part 4（`project-maintenance/deploy/`、`servo-installer/` 或 `project-maintenance/governance/servo-installer/`）。
5. 如果它无法归入当前存在的四个 Part，不要把它写入 `docs/`；先明确当前 owner 和实际承接路径，再同步最近入口和本页。

新增正文文档后，同步更新最近的 `README.md` 入口和本页的 Full Reading Order；若接管了新的稳定边界，也要清理旧入口，避免双份主线。

## Docs Path Maintenance

当 `docs/` 下的 markdown 文件新增、移动、重命名、删除或改 owner 时，维护顺序如下：

1. 先确定 owner 章节和最近 `README.md`，避免把新正文直接散落在目录里。
2. 更新最近章节 `README.md` 的局部入口或迁移说明。
3. 更新本页的 Full Reading Order，确保除 `docs/book.md` 自身外的每个当前 docs markdown 文件都有直接有序链接。
4. 检查本页正文中的反引号路径：只保留当前 checkout 中真实存在的路径；不要用不存在目录表达预留章节，也不要创建空目录或占位文档来让旧表述成立。
5. 修复旧路径引用；若旧入口仍有读者价值，写清迁移目标。
6. 运行 `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`，确认 book reachability、explicit reading-order coverage 和 inline path coverage 均通过。
7. 若变更影响 review/verify、路径治理或 closeout 规则，同步更新 `docs/project-maintenance/governance/` 的对应文档。

删除或重命名文档时，不只删除文件；必须同步删除或替换本页、最近 README、相关正文和治理文档中的旧链接。
