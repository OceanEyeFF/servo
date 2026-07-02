# 调度器技能

`product/harness/skills/` 目录存放 `Harness` 调度器的标准可执行源文件。

## Distributed Skill Product Shape

`product/harness/skills/` is the canonical source root for distributed Harness skill packages. Each immediate child skill directory is a distribution unit: after adapter deploy copies it into `.agents/skills/` or `.claude/skills/`, the installed package must remain operator-readable and executable without this source repository.

The source root may link to `docs/harness/` for authoring ownership, doctrine, catalog traceability, and long-form design history. Distributed runtime semantics are stricter: if a skill needs a contract, checklist, template, script, or short reference while it is being executed in a target repository, that material must be in the same skill package and included by the adapter payload.

## Self-contained Skill Rule

Skills are distributed runtime units. If `docs/harness/` is absent from a target repository, every installed skill must still remain logically self-contained: its `SKILL.md`, bundled templates, bundled references, scripts, assets, and explicit runtime artifacts must be sufficient for an operator or agent to understand inputs, boundaries, outputs, forbidden actions, and acceptance criteria.

`docs/harness/` may remain the source-repository maintenance truth and authoring trace. It must not be the runtime dependency that makes a deployed skill correct. Installed skills must not require project-relative docs paths, repo-external absolute paths, parent-directory escapes, or deploy-target paths outside the current skill package to decide what to do.

Allowed runtime package surface:

- `SKILL.md`: the primary executable instruction and runtime contract for the skill.
- `templates/`: files the skill copies, renders, or asks the operator to use.
- `references/`: short runtime references that are bundled with the skill package.
- `scripts/`: skill-private helper scripts. Shared deploy, testing, and governance logic stays in `toolchain/`.
- `assets/`: skill-private static assets.

Distributed skill packages must not require any of the following to execute their runtime semantics:

- `docs/harness/`, `docs/project-maintenance/`, or any other source-repository docs path in the target repo.
- `.agents/`, `.claude/`, `.servo/`, `.nav/`, `.autoworkflow/`, or `.spec-workflow/` paths outside the current package, except as explicitly named deploy targets or runtime artifacts the skill is instructed to create or inspect.
- Parent-directory escapes such as `../` for runtime-authority files.
- Package-external symlinks.
- Repo-external absolute paths, local machine paths, or unpublished contracts.

Trace links to docs are acceptable only as source-side ownership or authoring references. They are not runtime authority for installed packages. When a docs contract becomes necessary at runtime, copy the minimal stable contract into `SKILL.md` or into a bundled file under the same skill package, then ensure adapter payload descriptors include that file.

当前阶段：

- 已落地的顶层入口是 [harness-skill/](./harness-skill/)：顶层监督入口
- 已落地的分派入口是 [worktrack-dispatch-skill/](./worktrack-dispatch-skill/)：`WorktrackScope` 下的限定范围分派与后备执行载体
- 已落地的通用执行载体：
  - [worktrack-generic-worker-skill/](./worktrack-generic-worker-skill/) — 接收限定范围 Prompt 的通用执行 worker
  - [worktrack-doc-catch-up-skill/](./worktrack-doc-catch-up-skill/) — 将已验证实现事实追平到正确文档层
- 已落地的 `RepoScope` 技能骨架：
  - [repo-init-goal-skill/](./repo-init-goal-skill/) — 初始化 Repo Goal/Charter 与控制面参考信号
  - [milestone-pre-intake-skill/](./milestone-pre-intake-skill/) — Milestone 写入/激活前的需求核实、追问和确认 review
  - [repo-status-skill/](./repo-status-skill/) — 代码仓库状态观察
  - [repo-whats-next-skill/](./repo-whats-next-skill/) — 代码仓库下一步判断
  - [repo-append-request-skill/](./repo-append-request-skill/) — 追加请求分类与路由
  - [repo-change-goal-skill/](./repo-change-goal-skill/) — 修改 Repo 目标
  - [repo-refresh-skill/](./repo-refresh-skill/) — 代码仓库刷新
  - [milestone-cleanup-skill/](./milestone-cleanup-skill/) — Milestone closeout 后的 repo/runtime cleanup report 与非破坏性 dry-run 维护
  - [worktrack-cleanup-skill/](./worktrack-cleanup-skill/) — legacy cleanup 兼容入口，保留给既有调用与旧 adapter alias
- [milestone-init-skill/](./milestone-init-skill/) — Milestone 初始化/注册到 Pipeline
- [milestone-status-skill/](./milestone-status-skill/) — Milestone 状态观测/验收分析器
- [milestone-gate/](./milestone-gate/) — Milestone Gate 聚合器（消费顶层 Harness sibling axis reports + aggregation_rules 聚合）
  - Milestone Gate 四轴检查（由顶层 Harness 作为 sibling axis carriers 分派）：
    - [milestone-blackbox-check/](./milestone-blackbox-check/) — 外部视角检查（跨 WT 集成、用户承诺、回归风险、外部一致性、覆盖缺口）
    - [milestone-whitebox-check/](./milestone-whitebox-check/) — 内部实现视角检查（接口契约、状态流转、依赖图、架构对齐、实现质量）
    - [milestone-anticheat-check/](./milestone-anticheat-check/) — 反作弊检查（mock abuse、证据复用、部分验证、gate 绕过、过期证据、自审偏见、假阳性风险）
    - [milestone-composite-check/](./milestone-composite-check/) — 复合验收检查（code-review、feature-completeness、related-influence、intent-completeness、operator-simulation、professional-review lanes）
- 已落地的 `WorktrackScope` 技能骨架：
  - [worktrack-status-skill/](./worktrack-status-skill/) — 工作追踪状态观察
  - [worktrack-init-skill/](./worktrack-init-skill/) — 初始化工作追踪
  - [worktrack-schedule-skill/](./worktrack-schedule-skill/) — 调度工作追踪
  - [worktrack-review-evidence-skill/](./worktrack-review-evidence-skill/) — 审查证据
  - [worktrack-test-evidence-skill/](./worktrack-test-evidence-skill/) — 测试证据
  - [worktrack-rule-check-skill/](./worktrack-rule-check-skill/) — 规则检查
  - [worktrack-gate-skill/](./worktrack-gate-skill/) — 关卡判定
  - [worktrack-recover-skill/](./worktrack-recover-skill/) — 恢复工作追踪
  - [worktrack-close-skill/](./worktrack-close-skill/) — 关闭工作追踪
- 上游技能目录见 [../../../docs/harness/catalog/README.md](../../../docs/harness/catalog/README.md)
- 后续新增内容应从 `docs/harness/` 的操作员定义、工作流程与治理规则推导而来
- 不应先复制局部提示词，再反向让它生长出本体论

这里适合放：

- `Harness` 的操作员落地实现
- `Harness` 工作流程/配置的标准可执行源文件
- 最小必要的参考资料

## 技能目录布局

每个技能目录必须有 `SKILL.md`。下列子目录是当前允许的可选结构，只有在能被该技能稳定消费时才保留：

- `templates/`：技能执行时会复制、渲染或要求使用的模板
- `references/`：技能本体需要随包分发的短参考材料
- `scripts/`：技能私有辅助脚本；共享部署、测试或治理逻辑仍应放在 `toolchain/`
- `assets/`：技能私有静态资产

没有对应资产的技能应保持仅 `SKILL.md`，不需要补空目录。新增子目录类型前，先更新本页并补对应治理检查。

这里不适合放：

- 教义长文正文
- 后端包装器
- 代码仓库本地挂载结果

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [harness-skill/](./harness-skill/) | [docs/harness/catalog/supervisor.md](../../../docs/harness/catalog/supervisor.md) |
| [repo-init-goal-skill/](./repo-init-goal-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [milestone-pre-intake-skill/](./milestone-pre-intake-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [repo-status-skill/](./repo-status-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [repo-whats-next-skill/](./repo-whats-next-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [repo-append-request-skill/](./repo-append-request-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [repo-change-goal-skill/](./repo-change-goal-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [repo-refresh-skill/](./repo-refresh-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [milestone-cleanup-skill/](./milestone-cleanup-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [worktrack-cleanup-skill/](./worktrack-cleanup-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [milestone-init-skill/](./milestone-init-skill/) | [docs/harness/catalog/milestone/milestone-init-skill.md](../../../docs/harness/catalog/milestone/milestone-init-skill.md) |
| [milestone-status-skill/](./milestone-status-skill/) | [docs/harness/catalog/milestone/milestone-status-skill.md](../../../docs/harness/catalog/milestone/milestone-status-skill.md) |
| [milestone-gate/](./milestone-gate/) | [docs/harness/artifact/control/milestone-gate-aggregation.md](../../../docs/harness/artifact/control/milestone-gate-aggregation.md) |
| [milestone-blackbox-check/](./milestone-blackbox-check/) | [docs/harness/artifact/control/milestone-gate-aggregation.md](../../../docs/harness/artifact/control/milestone-gate-aggregation.md) |
| [milestone-whitebox-check/](./milestone-whitebox-check/) | [docs/harness/artifact/control/milestone-gate-aggregation.md](../../../docs/harness/artifact/control/milestone-gate-aggregation.md) |
| [milestone-anticheat-check/](./milestone-anticheat-check/) | [docs/harness/artifact/control/milestone-gate-aggregation.md](../../../docs/harness/artifact/control/milestone-gate-aggregation.md) |
| [milestone-composite-check/](./milestone-composite-check/) | [docs/harness/artifact/control/milestone-gate-aggregation.md](../../../docs/harness/artifact/control/milestone-gate-aggregation.md) |
| [worktrack-status-skill/](./worktrack-status-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-init-skill/](./worktrack-init-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-schedule-skill/](./worktrack-schedule-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-dispatch-skill/](./worktrack-dispatch-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-generic-worker-skill/](./worktrack-generic-worker-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-doc-catch-up-skill/](./worktrack-doc-catch-up-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-review-evidence-skill/](./worktrack-review-evidence-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-test-evidence-skill/](./worktrack-test-evidence-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-rule-check-skill/](./worktrack-rule-check-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-gate-skill/](./worktrack-gate-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-recover-skill/](./worktrack-recover-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [worktrack-close-skill/](./worktrack-close-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
| [repo-writeback-skill/](./repo-writeback-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |

This table is the source-side backlink to the docs/catalog owner surface. Keep it synchronized when adding, renaming, retiring, or moving canonical skill source. Do not replace these links with deploy target paths.

## Source Baseline Versioning

The current verified git checkpoint for this source root is recorded by Harness runtime artifacts, not by per-skill prose in this README:

- checkpoint runtime owner: `.servo/repo/snapshot-status.md`
- idempotency runtime owner: `.servo/control-state.md`
- closeout evidence runtime owner: `.servo/worktrack/closeout-record.md`
- checkpoint contract: [docs/harness/artifact/repo/snapshot-status.md](../../../docs/harness/artifact/repo/snapshot-status.md)
- idempotency contract: [docs/harness/artifact/control/control-state.md](../../../docs/harness/artifact/control/control-state.md)

When canonical skill source or this source index changes, closeout records the verified git HEAD and repo refresh updates the source baseline summary. Keep long-term docs linked to source roots and docs owners; do not scatter manual commit hashes through individual skill descriptions.
