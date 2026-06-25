---
title: "servo-installer Pre-Publish Governance"
status: active
updated: 2026-06-17
owner: servo-kernel
last_verified: 2026-06-17
---
# servo-installer Pre-Publish Governance

> 目的：定义 publish 前必须满足的最小 release-readiness 边界。

本页属于 [Governance](./README.md)。

管理 candidate tuple readiness、packlist/docs freshness、preflight 证据、approval lock。不管理发布序列、channel 策略、smoke 执行。

## Stop Rule

Tuple 不一致、preflight/smoke 证据缺失、docs 指向错误选择器或旧行为、本地 package smoke 未通过时停止；npm 版本不可变。

发布型 PR 标题、正文、release notes 草稿或 operator handoff 提到的版本，必须与 source tuple 一致；发现不一致时先修 tuple 和 source-version docs，再重新跑 preflight，不进入 approve/merge/release。

## 0. Prepare Candidate Version

版本号更新必须先于 release PR approval、merge 和 GitHub Release 创建完成。不要只改 PR 标题或 release notes；source tuple 必须先落到代码仓库。

1. 选择 candidate version 和 channel：
   - stable：`<major>.<minor>.<patch>` -> `latest`
   - RC/alpha/beta：`<major>.<minor>.<patch>-rc.N` / `-alpha.N` / `-beta.N` -> `next`
   - canary：prerelease segment 包含 `canary` -> `canary`
2. 确认 candidate 没有被占用：

```bash
NPM_CONFIG_CACHE=/tmp/servo-npm-cache npm view servo-installer@<version> version --json
git tag --list "v<version>"
git ls-remote --tags origin "v<version>"
```

`npm view` 返回 404 且 tag 查询为空才可继续；任何已存在的 npm version 或 tag 都必须换新版本号。

3. 更新 source tuple：

```bash
npm pkg set version="<version>"
npm --prefix toolchain/scripts/deploy pkg set version="<version>"
npm pkg set servoInstallerRelease.realPublishApproval="approved"
npm pkg set servoInstallerRelease.approvedVersion="<version>"
npm pkg set servoInstallerRelease.approvedGitTag="v<version>"
npm pkg set servoInstallerRelease.approvedChannel="<latest|next|canary>"
```

4. 核对 tuple 输出：

```bash
node toolchain/scripts/deploy/bin/servo-installer.js --version
npm_config_dry_run=true node toolchain/scripts/deploy/bin/check-root-publish.js
SERVO_INSTALLER_RELEASE_GIT_TAG="v<version>" \
  SERVO_INSTALLER_RELEASE_CHANNEL="<latest|next|canary>" \
  npm_config_tag="<latest|next|canary>" \
  SERVO_INSTALLER_PUBLISH_APPROVED=1 \
  CI=true \
  node toolchain/scripts/deploy/bin/check-root-publish.js
```

第一条必须输出 `servo-installer <version>`；第二条只验证 dry-run 前也必须成立的 package/scaffold 结构；第三条模拟真实 publish guard 的 tuple/channel 判断，不执行 publish。不要把裸跑 `node toolchain/scripts/deploy/bin/check-root-publish.js` 当作发布前通过条件；缺少 `SERVO_INSTALLER_PUBLISH_APPROVED=1` 时它应拒绝，这是防发布保护。

5. 做 source-version docs freshness：若 release channel governance、testing/usage docs 或 root README 仍指向旧 source tuple，先更新 source version facts。此时不得把未发布 candidate 写成 npm registry published fact。

6. 提交版本号更新：

```bash
git diff -- package.json toolchain/scripts/deploy/package.json docs/project-maintenance/governance
git add package.json toolchain/scripts/deploy/package.json <source-version-docs>
git commit -m "chore: prepare servo-installer v<version> release tuple"
```

完成后再进入 Candidate Tuple 和本地 preflight。若后续 PR/release handoff 发现版本不一致，回到本节重新修正并重跑 preflight。

## 1. Candidate Tuple

Before approval, confirm:

| Field | Required check |
| --- | --- |
| package name | root `package.json` name is `servo-installer` |
| package version | valid semver, not `0.0.0-local`, not already published |
| git tag | exactly `v<package.version>` |
| npm dist-tag | matches the intended release channel |
| GitHub Release prerelease flag | matches the semver prerelease state |
| release body marker | includes `servo-installer-publish-approved: v<package.version>` |
| approval lock | `approvedVersion`, `approvedGitTag`, and `approvedChannel` match |
| CLI version | `node toolchain/scripts/deploy/bin/servo-installer.js --version` prints `servo-installer <package.version>` |
| PR release label | PR title/body version and intended channel match `package.json` |

stable lanes 使用默认 `servo-installer` selector；RC lanes 必须用 `servo-installer@next`，不用裸 `servo-installer`。

## 2. Packlist And Docs Freshness

```bash
npm pack --dry-run --json
```

确认 packlist 包含入口点、payload descriptor、canonical skill payload 与 docs，排除状态/缓存/临时证据；root `README.md` 和 governance/testing/usage docs 指向正确选择器；deploy docs 不变成 release policy、testing docs 不变成 approval pages。若 package version、approval lock、selector 或 CLI surface 变化，publish 前先调用 `worktrack-doc-catch-up-skill` 做 source version docs freshness 检查；此时只能同步 source version facts，不得写入尚未发布的 registry fact。

## 3. Required Local Preflight Evidence

保留以下通过证据：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
npm --prefix toolchain/scripts/deploy test --silent
npm pack --dry-run --json
npm run publish:dry-run --silent
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/closeout_acceptance_gate.py --json
```

证明 candidate surface 与 publish guard，不执行 publish。

在只读 home/cache 环境中运行 npm registry 或 pack 命令时，允许显式 pin cache，例如 `NPM_CONFIG_CACHE=/tmp/servo-npm-cache npm view ...`；这只改变本地缓存位置，不改变发布准入。

## 4. Local Package Smoke

完成 [npx Command Test Execution](../../testing/npx-command-test-execution.md) 定义的 local package smoke；证据要求属于本页，命令矩阵与 pass criteria 属 testing runbook。

## 5. Real Dogfood Gate

> 目的：确认已发布的 RC 候选包在真实 target repo 上通过 skills 更新、`.servo` reconcile 收敛和 Harness 入口语义的 dogfood 验证。local-source-root pass、unit test、fixture 和 pack dry-run 不能替代真实 registry-only package surface 证据。

### 5.1 为什么需要 Real Dogfood Gate

- **unit / fixture / deploy test** 在 source checkout 内运行，不经过 npm registry package surface → 不能证明已发布包在外部 repo 上的行为
- **local-source-root pass**（通过 `SERVO_HARNESS_REPO_ROOT` 指向 source checkout）是补充证据，不是 registry-only package proof；它证明当前 HEAD 的 reconcile helper/template 可以收敛，但不证明已发布的 npm tarball 含有相同版本的 helper/template
- **local `.tgz` smoke** 验证打包结构、命令入口与基本 install/verify 周期，但不验证跨 repo `.servo` reconcile 收敛
- **git diff/status** 需要 `.gitignore` 配合才能感知 `.skills`/`.agents`/`.claude`/`.servo` 的变化；当这些 managed surface 被 gitignore 屏蔽时，git status 为空的 repo 仍可能存在未审计的 managed surface 变更

因此，发布 RC 前必须收集以下真实 dogfood 证据。

### 5.2 COV-SKILLS：Skills 更新 Dogfood

在至少 3 个 disposable freeze repo workspace 上，对已发布 `servo-installer@<channel>` 跑 skills update → diagnose → verify 全周期：

- 覆盖 `agents` 和 `claude` 两个 backend
- 每 target 验证 marker 数量、skill 目录数量与预期一致
- 验证 `forbidden_surfaces_unchanged: true` 且 `safe_diff_passed: true`
- 证据锚点：`.test/execution/evidence/cov-skills-summary/` 下的 aggregate manifest

### 5.3 COV-SERVO：`.servo` Reconcile 收敛 Dogfood

在至少 3 个 disposable freeze repo workspace 上，对已发布 `servo-installer@<channel>` 跑 `.servo` reconcile 收敛周期：

```text
backup .servo → dry-run --json → apply --yes → second dry-run --json
```

**通过条件**：
- `second_dry_run_change_count == 0`（收敛）
- `blank_placeholder_ok == true`（无空白 placeholder field/section 追加）
- `safe_diff_passed == true` 且 diff 范围限于 `.servo/`
- `forbidden_surfaces_unchanged == true`
- freeze manifest digest 在 reconcile 前后不变

**证据锚点**：`.test/execution/evidence/cov-servo-summary/` 下的 aggregate manifest。

### 5.4 Registry-Only 与 Local-Source-Root 的区分

| 模式 | 设置方式 | 证明什么 | 不能证明什么 |
|------|---------|---------|-------------|
| **registry-only** | 不设置 `SERVO_HARNESS_REPO_ROOT`，纯 `npx --package servo-installer@<channel>` | 已发布 npm tarball 内的 helper/template 在外部 repo 上的行为 | N/A — 这是最接近 operator 真实使用路径的包面证据 |
| **local-source-root** | 设置 `SERVO_HARNESS_REPO_ROOT=<source-checkout-path>` | source checkout 内的最新 helper/template 可以收敛；用于回归已发现并修复的 bug | 不能证明已发布 tarball 的行为；不能证明 npm registry 上的包面质量 |

**发布前要求**：registry-only reconcile 收敛是必须项；local-source-root pass 是补充项，可以用来说明 "已知 bug 在 source HEAD 已修复"，但不能替代 registry-only 证据。

如果 registry-only lane 未收敛（如 rc.4 的 blank Task List append_field 非收敛），则该 RC 的包面行为不能通过此 gate。后续修复需要发布新的 RC（如 rc.5）后重新收集 registry-only 证据。此时 local-source-root pass 可以作为 "fix is in HEAD" 的辅助声明，但不得写成 "package surface is fixed"。

### 5.5 Managed Surface Audit

独立于 git status 审计以下 installer/runtime managed surfaces 的完整性：

- `.skills/`：skill payload 目录
- `.agents/`：agents backend 输出
- `.claude/`：claude backend 输出
- `.servo/`：runtime control-plane state

**要求**：
- 在 reconcile 前后的 workspace baseline 上各跑一次 managed surface audit
- 记录 content hash，检测 same-size content change（git status 无法感知的变化）
- 证明 managed surface 变更被完整捕获，不依赖目标 repo 的 `.gitignore` 配置
- 审计工具的证据能力是"future evidence"级别；本次 dogfood 收集的实际审计数据是"current evidence"级别

**证据锚点**：`.test/` 下的 managed surface audit helper 实现与对应 test coverage（10/10 pytest pass）；dogfood runner 在每次 reconcile 中集成的 `managed_surface_audit_refs`。

### 5.6 COV-HARNESS：Harness 入口语义 Dogfood

在至少 3 个 external freeze repo 上，用真实 agent runtime（Pi `/` Claude）调用 `harness-skill`，验证：

- skill 可被正确解析与加载
- Harness 控制回路入口可被进入（read-only planning/invocation）
- 不会误执行危险工具（no unapproved mutation）
- transcript 和 marker check 通过

**明确不覆盖**：
- 不证明 SubAgent 真实创建
- 不证明子代理分派成功
- 不证明 target repo 实现质量
- 不拆解模型能力与 Harness 框架贡献（当前归因模型标记为 non-identifiable）

**证据锚点**：`.test/execution/evidence/cov-harness-summary/` 下的 aggregate manifest。

### 5.7 Disposable Workspace 与 Evidence 要求

所有 dogfood 执行必须使用 disposable workspace（freeze repo 的临时副本），不得变更原始 repo 或 freeze specimen：

- 原始 repo：只读 observe only
- freeze specimen：作为 workspace baseline，reconcile 前后对比 digest
- disposable workspace：实际执行 reconcile → apply → second dry-run 的目标
- backup：apply 前备份 workspace `.servo`，用于 restore/convergence 验证

每行 dogfood 的 evidence manifest 必须记录：`protected_mutation`（freeze/remote/release 均未变更）、`stop_or_continue_signal`、`threshold_verdict` 和 `residual_risk`。

### 5.8 收集 Matrix 参考

当前 MS-20260615-003 已验证的 dogfood matrix（`servo-installer@next` → `0.6.1-rc.4`）：

| Coverage Family | Repos | Verdict | 关键 Caveat |
|----------------|-------|---------|------------|
| COV-SKILLS | repo-rating-function, minigame1, reqflow | pass | minigame1/reqflow 的 `.agents`/`.claude` 被 `.gitignore` 屏蔽，safe_diff 无路径变更；用 installer diagnose/verify logs 和 managed surface manifest 补充 |
| COV-SERVO | servo-source-current, repo-rating-function, minigame1, reqflow | pass | **local-source-root mode**（`npx-wrapper-with-local-servo-source-root`），不是 registry-only |
| COV-HARNESS | repo-rating-function, minigame1, reqflow | pass | Pi read-only invocation/planning only；support-only current-repo row 不计入 release coverage |

**rc.4 已知问题**：
- registry-only reconcile 在 rc.4 上不收敛（dry-run 84 changes，second dry-run 7 changes，含 27 个 blank Task List append_field）
- post-rc4 fix（commit `893f8c6` 和 `ddc7467`）在 local source HEAD（`122f6be`）修复了 blank placeholder 和 duplicate-field 收敛问题
- 但修复后的代码不在已发布的 rc.4 tarball 中；npm `gitHead` 和 remote tag 都指向 `09c3f5c`（rc.4 发布时的 commit）
- registry-only smoke 对 rc.4 的失败是"已发布包面失败"，不是"当前 HEAD 仍失败"
- 如需验证修复后的包面行为，需发布新 RC 后重跑 registry-only reconcile

## 6. Approval Lock

前述检查（含 Real Dogfood Gate）通过后才可设置 approval lock：

```json
{
  "realPublishApproval": "approved",
  "approvedVersion": "<package.version>",
  "approvedGitTag": "v<package.version>",
  "approvedChannel": "<latest|next|canary>"
}
```

本页只授权 tuple lock，不执行 release sequence。就绪后继续 [servo-installer Release Standard Flow](./servo-installer-release-standard-flow.md)。
