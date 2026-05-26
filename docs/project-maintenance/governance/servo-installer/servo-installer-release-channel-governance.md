---
title: "servo-installer Release Channel Governance"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# servo-installer Release Channel Governance

> 目的：定义 `servo-installer` 进入真实 npm release channel 前必须满足的发布准入规则，并记录当前 registry 事实。

本页属于 [Governance](./README.md) 路径簇。

管理 release channel/dist-tag 对应关系、publish 准入条件与当前 registry 事实。不管理 pre-publish tuple/packlist/doc freshness、smoke 执行、发布流程顺序与 wrapper/payload 边界。

## 当前 registry 事实

2026-05-26 已核对 npm registry：

- **版本号纠正**：`4.4.x` 系列（`v4.4.0`、`v4.4.0-rc.0`、`v4.4.1-rc.0`、`v4.4.1-rc.1`、`v4.4.1`）为错误发布的版本号，不进入 semver 主序列
- npm registry 真实状态：`latest` -> `0.5.7`；`next` 未设置；已发布版本：`0.5.3`、`0.5.4`、`0.5.5`、`0.5.6`、`0.5.7`
- GitHub Release `v0.5.7` 已发布，target commit `7be50a43bf635d3966294387df249ff307470b1b`；npm `servo-installer@0.5.7` 的 `gitHead` 同为 `7be50a43bf635d3966294387df249ff307470b1b`
- publish workflow run `26448942207` completed successfully for `v0.5.7`
- npm `servo-installer@0.5.7` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.5.7.tgz`

## 当前 source release tuple

2026-05-26，`v0.5.7` source tuple 已发布到 `latest` channel：

- root `package.json` version：`0.5.7`
- local scaffold `toolchain/scripts/deploy/package.json` version：`0.5.7`
- approval lock：`approvedVersion=0.5.7`、`approvedGitTag=v0.5.7`、`approvedChannel=latest`
- release scope：发布 Milestone Pipeline Intake & Backlog Hygiene 更新，包括 `append-milestone` request routing、milestone live backlog/history split，以及本地 `develop-aw` 上的近期 installer 修复。
- GitHub Release target、publish workflow run、dist-tag、gitHead 与 tarball URL 已同步到当前 registry 事实。

注意：`0.5.7` 是 stable release；默认 `servo-installer` 现在解析到 registry `latest` 的 `0.5.7`。当前 npm registry 未设置 `next` dist-tag。

npm dist-tag 由 publish workflow 写入，此页跟随 release commit 同步事实。`4.4.x` 相关 git tag 保留作为历史记录，不在 npm registry 中发布。

## Channel 对应关系

| channel | npm dist-tag | version form |
| --- | --- | --- |
| `latest` | `latest` | stable semver，例如 `1.2.3` |
| `next` | `next` | `alpha` / `beta` / `rc` prerelease |
| `canary` | `canary` | 含 `canary` 段的 prerelease |

stable operator-facing selector 使用默认 `servo-installer`；RC 试用 selector 必须显式使用 `servo-installer@next`。

## 真实 Publish 准入

必须同时满足：package name 为 `servo-installer`，version 是合法 semver（非 `-local`），tuple（`approvedVersion`/`approvedGitTag`/`approvedChannel`）一致，`SERVO_INSTALLER_RELEASE_GIT_TAG=v<version>`，GitHub Release body 含 `servo-installer-publish-approved: v<version>`，`CI=true`，`SERVO_INSTALLER_PUBLISH_APPROVED=1`，channel/dist-tag 一致（`latest`仅 stable，`next`仅 alpha/beta/rc，`canary`仅含 canary 的 prerelease）。`npm run publish:dry-run --silent` 不构成 publish 授权。

## 审批锁

publish 前 root `package.json` 必须绑定唯一 approval lock：

```json
{
  "realPublishApproval": "approved",
  "approvedVersion": "<package.version>",
  "approvedGitTag": "v<package.version>",
  "approvedChannel": "<latest|next|canary>"
}
```

approval lock 只能在显式 release-approval worktrack 中修改。

## 相关文档

- [servo-installer Release Standard Flow](./servo-installer-release-standard-flow.md)
- [servo-installer Release Operation Model](./servo-installer-release-operation-model.md)
- [servo-installer Pre-Publish Governance](./servo-installer-pre-publish-governance.md)
- [npx Command Test Execution](../../testing/npx-command-test-execution.md)
