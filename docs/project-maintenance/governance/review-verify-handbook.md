---
title: "Review / Verify 治理入口"
status: active
updated: 2026-06-02
owner: servo-kernel
last_verified: 2026-06-02
---
# Review / Verify 治理入口

> 目的：把 `plan -> implement -> verify -> review -> writeback` 收成一个 repo-local、可复用、可引用的复核入口。本文说明执行阶段的最小复核动作，不作为长期真相本体。

## 一、适用范围

在任务收口前、改完代码后、或需要固定 review checklist 时先读本文。不适用作 canonical truth、长期架构设计或开发计划。

## 二、默认流程

`plan -> implement -> verify -> review -> writeback`；先确认目标与范围，只改当前任务不扩边界，`verify` 先于 `review`，`writeback` 只录已验证事实。修复类任务须检查相邻状态、恢复路径、operator-facing 语义和脏数据场景。

## 三、推荐复核清单

默认覆盖性能、架构、安全、质量、测试五个独立面；docs-only 或 governance-only 变更需显式标出不适用面及理由。

### 1. 变更范围

- diff 是否只覆盖当前任务，是否触碰不在 scope 内的文件层，是否存在未声明的新目录/入口/规则

### 2. 规则同步

- root/partition/path/hidden-layer 变更需同步 foundations、关键入口页和治理检查
- AGENTS.md、INDEX.md、默认启动阅读路径或执行流程变更需同步本文，并保持 `AGENTS.md -> INDEX.md -> 当前任务局部入口` 的轻量路由主线
- runbook/usage-help/testing/Harness 长文变更需说明当前页类型（入口/runbook/合同/指导）并清理重复正文
- 新增、移动、重命名、删除或改为 `status: superseded` 的 `docs/` markdown 文档必须维护 `docs/book.md` spine：先更新最近章节 `README.md`，再更新 `docs/book.md` 的 Full Reading Order，确认除 `docs/book.md` 自身外的所有 `docs/**/*.md` 都有直接有序链接，最后修复旧路径引用，并检查 `docs/book.md` markdown 链接与反引号 inline path 都指向当前 checkout 真实存在的 docs 路径或 owner 边界；superseded 文档只能通过显式 historical references 区块暴露，并应说明当前 owner 或接管路径
- deploy/adapter 变更需同步对应 runbook、maintenance 与 usage-help，口径保持 destructive reinstall model
- package/release/version/VCS baseline 事实变更需调用 `doc-catch-up-worker-skill` 做 version fact sync；pre-publish 只同步 source version facts 与 VCS tracking facts，post-publish registry verification 后才能同步 published version facts；canonical skill source baseline 由 repo snapshot 的 `source_baselines.product_harness_skills` 和 control-state Baseline Traceability 承接，长期 docs 不手写分散 git hash
- docs/harness/、product/harness/skills/ 或 adapters 变更需保持合同层与 executable layer 分工
- branch/PR/baseline 规则变更需从 `origin/HEAD` 或 Worktrack Contract 的 `baseline_branch` 取值，不写死默认分支名
- 新功能若改变 Harness 控制流、canonical skill 行为、adapter/deploy 行为、CLI/operator runbook 或用户实际操作路径，必须把真实 Claude Code dogfood 作为验证策略的一层；mock、fixture、generator smoke 和单元测试只能证明回归面，不能单独替代真实 backend 行为观察。若本轮不跑 Claude dogfood，closeout 必须写明不适用理由或延期 Worktrack。
- 单人维护模式下 release PR 不要求外部 reviewer；GitHub 不允许 PR author approve 自己的 PR，因此 self-approval 不作为治理要求；owner/admin self-merge 前需记录 checks、PR head SHA、release tuple 和后续 release/tag/publish 动作；`reviewDecision` 为空不是失败，draft、required check failure、pending/skipped required check 或 release-readiness 证据缺失才是阻断信号
- release PR 正文只能声明实际运行且有本地输出或 CI run/job URL 支撑的验证结果；被 CI 跳过、尚未运行或只计划运行的检查必须标成 pending/not-run，不能写成 passed
- 退役/删除文档域需同步入口页、旧路径引用和治理检查
- SKILL.md 变更需保持最小 executable body；已退役 references 需同步清理
- product/.servo_template/ 变更只承接 scaffold 模板，不生长 canonical truth 或运行状态
- docs/harness/workflow-families/ 变更需明确文档真相层定位，对 product/harness/ 只能当下游 executable root

### 3. 验证结果

按改动面选择最小验证集；所有 Python 命令默认使用 `PYTHONDONTWRITEBYTECODE=1 python3 ...`。

- 根目录/路径/分层/hidden/state 规则变更：`folder_logic_check.py` + `path_governance_check.py` + `governance_semantic_check.py`
- 新增、移动、拆分、重命名或删除 `docs/` 正文：`path_governance_check.py`，确认新正文可从 `docs/book.md` spine 到达、在 Full Reading Order 中有直接有序链接、最近章节入口已更新、旧路径引用已处理，且 `docs/book.md` 不使用不存在目录、未来规划、空目录或占位文档来满足 book
- 默认阅读路径或 route contract 变更：`path_governance_check.py` + `governance_semantic_check.py`，确认 `AGENTS.md` 未恢复成固定长 Read First 清单
- skills/templates 分层规则变更：`path_governance_check.py` + `governance_semantic_check.py`
- branch/PR/baseline 或 hook 变更：`git symbolic-ref` + `bash -n pre-push` + dry-run
- `.servo_template`/`.servo/` scaffold 变更：`path_governance_check.py` + `governance_semantic_check.py`
- closeout/gate/backfill 变更：`closeout_acceptance_gate.py --json` + 对应最小 pytest；closeout 按 `scope_gate -> spec_gate -> static_gate -> cache_gate -> test_gate -> smoke_gate` 收口；`cache_gate` 扫描 `docs/`、`product/`、`toolchain/` 和 `tools/` 下的 Python / pytest 运行缓存；`scope_gate` 允许 root `README.md` 与 `product/.servo_template/`；`test_gate` 运行 closeout/folder/path/semantic/adapter 回归 + deploy package Node unit tests + npm packlist + publish dry-run + tarball smoke
- deploy mapping/payload contract 变更：`test_agents_adapter_contract.py`；改 gate 链路再补 `closeout_acceptance_gate.py --json`
- adapter/deploy 变更：`test_agents_adapter_contract.py` + npm test + smoke + 双端 `npm pack --dry-run --json` + publish dry-run + tarball 全命令 smoke（diagnose/update/install/verify）+ 隔离 target repo full smoke
- Harness runtime 观察或 operator-facing runbook 变更：先跑对应 deploy/adapter 最小验证，再按 [Codex Post-Deploy Behavior Tests](../testing/codex-post-deploy-behavior-tests.md) 和 [Claude Post-Deploy Behavior Tests](../testing/claude-post-deploy-behavior-tests.md) 做真实观察；Claude dogfood 是新功能影响实际使用路径时的默认真实 backend 验证层，不用 mock smoke 替代

### 3.1 真实 Claude Dogfood 准入

默认需要真实 Claude dogfood 的变更：

- 新增或改变 Harness / skill / gate / dispatch / closeout / worktrack 行为。
- 改 `servo-installer`、adapter payload、Claude skill 分发、CLI 使用方式或 operator-facing runbook。
- 改 scanner、门禁、弱文档路由、安全策略等会影响用户开工决策的逻辑。
- 用户明确质疑 mock/fixture 覆盖不足，或要求真实 Claude 测试。

可显式说明不适用的变更：

- 纯 typo、链接、frontmatter 日期、历史事实补录，且不改变操作流程。
- 只改内部测试实现，不改变用户可见行为或 backend payload。
- 当前环境没有可用 Claude 认证；这种情况必须记录阻塞证据，并把真实 dogfood 作为后续 Worktrack 或 residual risk。

Claude dogfood 证据至少记录：Claude Code 版本、真实 backend smoke、是否验证 `/skill-name` invocation、目标 repo/fixture 来源、隔离路径、安全边界、prompt 摘要、预算 cap、输出结论、失败/复核轮次和残余风险。

### 3.2 修复完整性

bugfix/review 响应/回归修复需覆盖根因或相邻执行链状态，检查相邻 phase/state/recovery path、operator-facing 视图与 CLI 返回码一致性；补回归测试，不破坏已有 healthy/dirty/malformed path；未声明支持的 nested target layout 标成 contract expansion topic 而非 patch bug。

### 4. 回写要求

已验证结果写进 `docs/harness/` 或 `docs/project-maintenance/`；不把临时推理写成长期真相；优先复用现有模板；文档精简时需说明保留内容、删除内容、以及入口与合同是否清晰。

### 4.1 Docs 重构收口

docs restructuring closeout 必须记录 reader-coherence evidence，至少说明 `docs/book.md` Full Reading Order、最近章节入口和移动后的正文之间的阅读路径，以及删除/迁移后的旧入口如何处理。若当前任务无法完成 reader-coherence 验证，必须在 closeout 中写明 explicit deferral：延期原因、剩余入口风险、后续验证命令和接管位置。

## 四、完成标准

变更范围清楚、必要验证已跑、review 无未处理风险、同步文档已更新、writeback 已完成。修复类任务还需验证相邻状态与回归路径。收口说明遵循[全局语言风格](./global-language-style.md)。

## 五、相关文档

- [AGENTS.md](../../../AGENTS.md)
- [路径与文档治理检查运行说明](./path-governance-checks.md)
- [Claude Post-Deploy Behavior Tests](../testing/claude-post-deploy-behavior-tests.md)
- [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)
- [Skill Deployment 维护流](../../servo-installer/runbooks/skill-deployment-maintenance.md)
- [Branch / PR 治理规则](./branch-pr-governance.md)
