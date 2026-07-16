---
title: "Docs Book Spine"
status: active
updated: 2026-07-05
owner: servo-kernel
last_verified: 2026-07-05
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
2. [project-maintenance/usage-help/recommended-usage.md](./project-maintenance/usage-help/recommended-usage.md)
3. [project-maintenance/usage-help/usage-flow-examples.md](./project-maintenance/usage-help/usage-flow-examples.md)
4. [project-maintenance/usage-help/init-with-code.md](./project-maintenance/usage-help/init-with-code.md)
5. [project-maintenance/usage-help/goal-change-guide.md](./project-maintenance/usage-help/goal-change-guide.md)
6. [project-maintenance/usage-help/codex.md](./project-maintenance/usage-help/codex.md)
7. [project-maintenance/usage-help/claude.md](./project-maintenance/usage-help/claude.md)

---

### Part 2：Harness 内核

1. [harness/foundations/Harness指导思想.md](./harness/foundations/Harness指导思想.md)

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
6. [project-maintenance/testing/servo-installer-dogfood-layering.md](./project-maintenance/testing/servo-installer-dogfood-layering.md)
7. [project-maintenance/testing/codex-post-deploy-behavior-tests.md](./project-maintenance/testing/codex-post-deploy-behavior-tests.md)
8. [project-maintenance/testing/claude-post-deploy-behavior-tests.md](./project-maintenance/testing/claude-post-deploy-behavior-tests.md)

#### 3.3 社区推广与对外技术叙事

1. [project-maintenance/community/README.md](./project-maintenance/community/README.md)
2. [project-maintenance/community/external-positioning.md](./project-maintenance/community/external-positioning.md)
3. [project-maintenance/community/external-technical-architecture.md](./project-maintenance/community/external-technical-architecture.md)
4. [project-maintenance/community/对外发布整理/linuxdo-release-post-v061_context-version.md](./project-maintenance/community/对外发布整理/linuxdo-release-post-v061_context-version.md)
5. [project-maintenance/community/对外发布整理/linuxdo-release-post-v061.md](./project-maintenance/community/对外发布整理/linuxdo-release-post-v061.md)

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

## Chapter Boundaries

### Part 1：项目基础

新文档属于 Part 1，当它回答的是"这个项目是什么、怎么组织和怎么开始使用"。涉及根目录边界时，优先进入 `project-maintenance/foundations/`；涉及使用场景或 backend 差异时，优先进入 `project-maintenance/usage-help/`。

### Part 2：Harness 内核

`docs/harness/foundations/Harness指导思想.md` 是唯一长期 Harness 思想文档。Skill 的入口、运行步骤、字段和停止边界由对应 `product/harness/skills/*/SKILL.md` 自己维护，不在 docs 中建立镜像。

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
2. 是跨模块 Harness 指导思想吗？收敛进 Part 2 的唯一文档；若是 Skill 运行合同，写入对应 `SKILL.md`。
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
6. 在外围治理工具重构完成前，通过实际路径扫描和独立内容 Review 确认 book 不含悬空链接。
7. 若变更影响 review/verify、路径治理或 closeout 规则，同步更新 `docs/project-maintenance/governance/` 的对应文档。

删除或重命名文档时，不只删除文件；必须同步删除或替换本页、最近 README、相关正文和治理文档中的旧链接。
