---
title: "servo-installer Pre-Publish Governance"
status: active
updated: 2026-05-11
owner: servo-kernel
last_verified: 2026-05-11
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
NPM_CONFIG_CACHE=/tmp/aw-npm-cache npm view servo-installer@<version> version --json
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
node toolchain/scripts/deploy/bin/check-root-publish.js
SERVO_INSTALLER_RELEASE_GIT_TAG="v<version>" \
  SERVO_INSTALLER_RELEASE_CHANNEL="<latest|next|canary>" \
  npm_config_tag="<latest|next|canary>" \
  SERVO_INSTALLER_PUBLISH_APPROVED=1 \
  CI=true \
  node toolchain/scripts/deploy/bin/check-root-publish.js
```

第一条必须输出 `servo-installer <version>`；第二条只验证 dry-run 前也必须成立的 package/scaffold 结构；第三条模拟真实 publish guard 的 tuple/channel 判断，不执行 publish。

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

确认 packlist 包含入口点、payload descriptor、canonical skill payload 与 docs，排除状态/缓存/临时证据；root `README.md` 和 governance/testing/usage docs 指向正确选择器；deploy docs 不变成 release policy、testing docs 不变成 approval pages。若 package version、approval lock、selector 或 CLI surface 变化，publish 前先调用 `doc-catch-up-worker-skill` 做 source version docs freshness 检查；此时只能同步 source version facts，不得写入尚未发布的 registry fact。

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

在只读 home/cache 环境中运行 npm registry 或 pack 命令时，允许显式 pin cache，例如 `NPM_CONFIG_CACHE=/tmp/aw-npm-cache npm view ...`；这只改变本地缓存位置，不改变发布准入。

## 4. Local Package Smoke

完成 [npx Command Test Execution](../../testing/npx-command-test-execution.md) 定义的 local package smoke；证据要求属于本页，命令矩阵与 pass criteria 属 testing runbook。

## 5. Approval Lock

前述检查通过后才可设置 approval lock：

```json
{
  "realPublishApproval": "approved",
  "approvedVersion": "<package.version>",
  "approvedGitTag": "v<package.version>",
  "approvedChannel": "<latest|next|canary>"
}
```

本页只授权 tuple lock，不执行 release sequence。就绪后继续 [servo-installer Release Standard Flow](./servo-installer-release-standard-flow.md)。
