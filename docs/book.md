---
title: "Docs Book Spine"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-05-27
---
# Docs Book Spine

`docs/book.md` 是 `docs/` 的 canonical book-style spine：它定义当前版本中实际存在的完整阅读顺序、章节边界、文档分组关系和路径维护规则。`docs/README.md` 只做入口导航；具体规则正文仍以对应章节内的承接文档为准。

Owner：`servo-kernel`。边界：只覆盖当前 `docs/` 文档分层与阅读路线，不替代 `AGENTS.md` 的 agent boot 规则，不承接 `product/` 源码合同或 `toolchain/` 脚本合同，不把未来迁移计划或后续 Worktrack seed 写成 docs truth。

## How To Read

1. 先读 [docs/README.md](./README.md) 确认 `docs/` 的入口定位。
2. 回到本页，按 [Full Reading Order](#full-reading-order) 从上到下阅读。Active 条目是当前主线；Retained Historical References 只为路径覆盖和历史追溯保留，不作为当前 truth owner。
3. 需要执行任务时，停在最近章节入口，不要继续扩读不相关章节。
4. 新增、移动、删除或重命名文档时，先按 [Docs Path Maintenance](#docs-path-maintenance) 同步本页、最近章节入口和旧路径引用。

## Full Reading Order

### 0. Orientation

1. [docs/README.md](./README.md)

### 1. Project Maintenance

1. [project-maintenance/README.md](./project-maintenance/README.md)
2. [project-maintenance/foundations/README.md](./project-maintenance/foundations/README.md)
3. [project-maintenance/foundations/root-directory-layering.md](./project-maintenance/foundations/root-directory-layering.md)
4. [project-maintenance/governance/README.md](./project-maintenance/governance/README.md)
5. [project-maintenance/governance/review-verify-handbook.md](./project-maintenance/governance/review-verify-handbook.md)
6. [project-maintenance/governance/path-governance-checks.md](./project-maintenance/governance/path-governance-checks.md)
7. [project-maintenance/governance/global-language-style.md](./project-maintenance/governance/global-language-style.md)
8. [project-maintenance/governance/branch-pr-governance.md](./project-maintenance/governance/branch-pr-governance.md)
9. [project-maintenance/governance/servo-installer/README.md](./project-maintenance/governance/servo-installer/README.md)
10. [project-maintenance/governance/servo-installer/servo-installer-release-operation-model.md](./project-maintenance/governance/servo-installer/servo-installer-release-operation-model.md)
11. [project-maintenance/governance/servo-installer/servo-installer-release-channel-governance.md](./project-maintenance/governance/servo-installer/servo-installer-release-channel-governance.md)
12. [project-maintenance/governance/servo-installer/servo-installer-release-standard-flow.md](./project-maintenance/governance/servo-installer/servo-installer-release-standard-flow.md)
13. [project-maintenance/governance/servo-installer/servo-installer-pre-publish-governance.md](./project-maintenance/governance/servo-installer/servo-installer-pre-publish-governance.md)
14. [project-maintenance/governance/servo-installer/servo-installer-external-trial-governance.md](./project-maintenance/governance/servo-installer/servo-installer-external-trial-governance.md)
14. [project-maintenance/deploy/README.md](./project-maintenance/deploy/README.md)
15. [project-maintenance/testing/README.md](./project-maintenance/testing/README.md)
16. [project-maintenance/testing/python-script-test-execution.md](./project-maintenance/testing/python-script-test-execution.md)
17. [project-maintenance/testing/npx-command-test-execution.md](./project-maintenance/testing/npx-command-test-execution.md)
18. [project-maintenance/testing/codex-post-deploy-behavior-tests.md](./project-maintenance/testing/codex-post-deploy-behavior-tests.md)
19. [project-maintenance/testing/claude-post-deploy-behavior-tests.md](./project-maintenance/testing/claude-post-deploy-behavior-tests.md)
20. [project-maintenance/usage-help/README.md](./project-maintenance/usage-help/README.md)
21. [project-maintenance/usage-help/recommended-usage.md](./project-maintenance/usage-help/recommended-usage.md)
22. [project-maintenance/usage-help/usage-flow-examples.md](./project-maintenance/usage-help/usage-flow-examples.md)
23. [project-maintenance/usage-help/init-greenfield.md](./project-maintenance/usage-help/init-greenfield.md)
24. [project-maintenance/usage-help/init-with-code.md](./project-maintenance/usage-help/init-with-code.md)
25. [project-maintenance/usage-help/goal-change-guide.md](./project-maintenance/usage-help/goal-change-guide.md)
26. [project-maintenance/usage-help/codex.md](./project-maintenance/usage-help/codex.md)
27. [project-maintenance/usage-help/claude.md](./project-maintenance/usage-help/claude.md)
28. [project-maintenance/usage-help/quickstart.md](./project-maintenance/usage-help/quickstart.md)
29. [project-maintenance/repo-onboarding.md](./project-maintenance/repo-onboarding.md)

### 2. servo-installer

1. [servo-installer/README.md](./servo-installer/README.md)
2. [servo-installer/contracts/distribution-entrypoint-contract.md](./servo-installer/contracts/distribution-entrypoint-contract.md)
3. [servo-installer/contracts/deploy-mapping-spec.md](./servo-installer/contracts/deploy-mapping-spec.md)
4. [servo-installer/contracts/aw-runtime-upgrade-contract.md](./servo-installer/contracts/aw-runtime-upgrade-contract.md)
5. [servo-installer/contracts/payload-provenance-trust-boundary.md](./servo-installer/contracts/payload-provenance-trust-boundary.md)
6. [servo-installer/contracts/version-marker-contract.md](./servo-installer/contracts/version-marker-contract.md)
7. [servo-installer/runbooks/deploy-runbook.md](./servo-installer/runbooks/deploy-runbook.md)
8. [servo-installer/runbooks/aw-runtime-upgrade-runbook.md](./servo-installer/runbooks/aw-runtime-upgrade-runbook.md)
9. [servo-installer/runbooks/skill-deployment-maintenance.md](./servo-installer/runbooks/skill-deployment-maintenance.md)
10. [servo-installer/runbooks/uninstall-remove-runbook.md](./servo-installer/runbooks/uninstall-remove-runbook.md)
11. [servo-installer/reference/managed-files-ownership.md](./servo-installer/reference/managed-files-ownership.md)
12. [servo-installer/reference/existing-code-adoption.md](./servo-installer/reference/existing-code-adoption.md)
13. [servo-installer/reference/legacy-version-handling.md](./servo-installer/reference/legacy-version-handling.md)
14. [servo-installer/reference/tui-aw-runtime-migration-repro.md](./servo-installer/reference/tui-aw-runtime-migration-repro.md)
15. [servo-installer/tui/README.md](./servo-installer/tui/README.md)
16. [servo-installer/tui/human-cli-contract.md](./servo-installer/tui/human-cli-contract.md)
17. [servo-installer/tui/bundle-default-contract.md](./servo-installer/tui/bundle-default-contract.md)

### 3. Harness

1. [harness/README.md](./harness/README.md)
2. [harness/foundations/README.md](./harness/foundations/README.md)
3. [harness/foundations/Harness指导思想.md](./harness/foundations/Harness指导思想.md)
4. [harness/foundations/Harness运行协议.md](./harness/foundations/Harness运行协议.md)
5. [harness/foundations/runtime-control-loop.md](./harness/foundations/runtime-control-loop.md)
6. [harness/foundations/runtime-dispatch-contract.md](./harness/foundations/runtime-dispatch-contract.md)
7. [harness/foundations/runtime-evidence-gate-recovery.md](./harness/foundations/runtime-evidence-gate-recovery.md)
8. [harness/foundations/runtime-closeout-refresh.md](./harness/foundations/runtime-closeout-refresh.md)
9. [harness/foundations/runtime-state-hydration.md](./harness/foundations/runtime-state-hydration.md)
10. [harness/foundations/dispatch-decision-policy.md](./harness/foundations/dispatch-decision-policy.md)
11. [harness/foundations/model-runtime-support.md](./harness/foundations/model-runtime-support.md)
12. [harness/foundations/skill-common-constraints.md](./harness/foundations/skill-common-constraints.md)
13. [harness/scope/README.md](./harness/scope/README.md)
14. [harness/scope/repo-scope.md](./harness/scope/repo-scope.md)
15. [harness/scope/worktrack-scope.md](./harness/scope/worktrack-scope.md)
16. [harness/artifact/README.md](./harness/artifact/README.md)
17. [harness/artifact/standard-fields.md](./harness/artifact/standard-fields.md)
18. [harness/artifact/repo/README.md](./harness/artifact/repo/README.md)
19. [harness/artifact/repo/discovery-input.md](./harness/artifact/repo/discovery-input.md)
20. [harness/artifact/repo/goal-charter.md](./harness/artifact/repo/goal-charter.md)
21. [harness/artifact/repo/repo-analysis.md](./harness/artifact/repo/repo-analysis.md)
22. [harness/artifact/repo/snapshot-status.md](./harness/artifact/repo/snapshot-status.md)
23. [harness/artifact/repo/worktrack-backlog.md](./harness/artifact/repo/worktrack-backlog.md)
24. [harness/artifact/repo/milestone-backlog.md](./harness/artifact/repo/milestone-backlog.md)
25. [harness/artifact/repo/milestone-history.md](./harness/artifact/repo/milestone-history.md)
26. [harness/artifact/repo/decision-log.md](./harness/artifact/repo/decision-log.md)
27. [harness/artifact/worktrack/README.md](./harness/artifact/worktrack/README.md)
28. [harness/artifact/worktrack/contract.md](./harness/artifact/worktrack/contract.md)
29. [harness/artifact/worktrack/plan-task-queue.md](./harness/artifact/worktrack/plan-task-queue.md)
30. [harness/artifact/worktrack/dispatch-packet.md](./harness/artifact/worktrack/dispatch-packet.md)
31. [harness/artifact/worktrack/gate-evidence.md](./harness/artifact/worktrack/gate-evidence.md)
32. [harness/artifact/worktrack/debug-evidence.md](./harness/artifact/worktrack/debug-evidence.md)
33. [harness/artifact/control/README.md](./harness/artifact/control/README.md)
34. [harness/artifact/control/control-state.md](./harness/artifact/control/control-state.md)
35. [harness/artifact/control/milestone.md](./harness/artifact/control/milestone.md)
36. [harness/artifact/control/composite-milestone-acceptance.md](./harness/artifact/control/composite-milestone-acceptance.md)
37. [harness/artifact/control/append-request.md](./harness/artifact/control/append-request.md)
38. [harness/artifact/control/goal-change-request.md](./harness/artifact/control/goal-change-request.md)
39. [harness/artifact/control/node-type-registry.md](./harness/artifact/control/node-type-registry.md)
40. [harness/catalog/README.md](./harness/catalog/README.md)
41. [harness/catalog/supervisor.md](./harness/catalog/supervisor.md)
42. [harness/catalog/repo.md](./harness/catalog/repo.md)
43. [harness/catalog/worktrack.md](./harness/catalog/worktrack.md)
44. [harness/catalog/milestone/README.md](./harness/catalog/milestone/README.md)
45. [harness/catalog/milestone/init-milestone-skill.md](./harness/catalog/milestone/init-milestone-skill.md)
46. [harness/catalog/milestone/milestone-status-skill.md](./harness/catalog/milestone/milestone-status-skill.md)
47. [harness/catalog/skill-impact-matrix.md](./harness/catalog/skill-impact-matrix.md)
48. [harness/workflow-families/README.md](./harness/workflow-families/README.md)
49. [harness/workflow-families/repo-evolution/README.md](./harness/workflow-families/repo-evolution/README.md)
50. [harness/workflow-families/repo-evolution/append-request-routing.md](./harness/workflow-families/repo-evolution/append-request-routing.md)

### Retained Historical References

These links are kept for explicit reading-order coverage and historical traceability only. They are `status: superseded` and do not act as current Harness truth owners.

1. [harness/workflow-families/repo-evolution/standard-worktrack.md](./harness/workflow-families/repo-evolution/standard-worktrack.md)
2. [harness/workflow-families/repo-evolution/policy-profiles.md](./harness/workflow-families/repo-evolution/policy-profiles.md)

## Chapter Boundaries

### 1. Project Maintenance

`docs/project-maintenance/` 承接 operator-facing 项目维护：根目录分层、review/verify/gate 治理、部署 runbook、测试入口、backend usage help 和 repo onboarding。

新文档属于这里，当它回答的是“这个仓库如何维护、验证、部署、接入或使用”。涉及长期治理规则时，优先进入 `project-maintenance/governance/`；涉及目录边界时，优先进入 `project-maintenance/foundations/`；涉及命令运行或 smoke 时，优先进入 `project-maintenance/testing/`。

### 2. Harness

`docs/harness/` 承接 Harness-first 主线，分成思路层、架构层和实现映射层。未升格的方案分析、迁移比较或实现前设计不作为当前 docs truth 层长期保留。

Harness 子章节放置规则：

- 思路层：`harness/foundations/` 说明 Harness 指导思想、runtime protocol、跨 skill 公共约束和执行载体选择策略。
- 架构层：`harness/scope/` 说明 `RepoScope`、`WorktrackScope` 与状态闭环。
- 架构层：`harness/artifact/` 说明 Harness 正式对象合同，包括 repo/worktrack/control artifact 与标准字段。
- 架构层：`harness/workflow-families/` 说明可复用 workflow family policy；superseded historical references 不作为当前主线 owner。
- 实现映射层：`harness/catalog/` 说明 Codex skill catalog、控制层级映射和 skill 影响矩阵；可执行源仍归 `product/harness/skills/`。

新文档属于这里，当它回答的是“Harness 如何思考、调度、记录证据、判定、交接或沉淀 workflow”。未验证的方案先留在 runtime/backlog 或工作追踪证据中；已验证并需要长期承接的内容，应升格到对应 foundations、scope、artifact、workflow-families 或 catalog owner。

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

1. 它是维护/治理/部署/测试/usage 吗？放 `project-maintenance/`。
2. 它是 Harness doctrine、runtime、scope、artifact、workflow 或 skill 映射吗？放 `harness/` 的最近子章节。
3. 如果它无法归入当前存在的两个章节，不要把它写入 `docs/`；先明确当前 owner 和实际承接路径，再同步最近入口和本页。

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
