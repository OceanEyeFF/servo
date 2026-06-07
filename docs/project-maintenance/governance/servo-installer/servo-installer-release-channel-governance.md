---
title: "servo-installer Release Channel Governance"
status: active
updated: 2026-06-07
owner: servo-kernel
last_verified: 2026-06-07
---
# servo-installer Release Channel Governance

> 目的：定义 `servo-installer` 进入真实 npm release channel 前必须满足的发布准入规则，并记录当前 registry 事实。

本页属于 [Governance](./README.md) 路径簇。

管理 release channel/dist-tag 对应关系、publish 准入条件与当前 registry 事实。不管理 pre-publish tuple/packlist/doc freshness、smoke 执行、发布流程顺序与 wrapper/payload 边界。

## 当前 registry 事实

2026-06-07 已核对 npm registry：

- **版本号纠正**：`4.4.x` 系列（`v4.4.0`、`v4.4.0-rc.0`、`v4.4.1-rc.0`、`v4.4.1-rc.1`、`v4.4.1`）为错误发布的版本号，不进入 semver 主序列
- npm registry 真实状态：`latest` -> `0.5.8`；`next` -> `0.6.1-rc.2`；已发布版本：`0.5.3`、`0.5.4`、`0.5.5`、`0.5.6`、`0.5.7`、`0.5.8`、`0.6.0-rc.0`、`0.6.0-rc.1`、`0.6.1-rc.0`、`0.6.1-rc.1`、`0.6.1-rc.2`
- GitHub Release `v0.5.8` 已发布，target commit `ad363e818adc5da01049f1808db9376830c05d09`；npm `servo-installer@0.5.8` 的 `gitHead` 同为 `ad363e818adc5da01049f1808db9376830c05d09`
- publish workflow run `26509952967` completed successfully for `v0.5.8`
- npm `servo-installer@0.5.8` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.5.8.tgz`
- GitHub Release `v0.6.0-rc.0` 已发布为 prerelease，target commit `be5df6ec2a4d5fa9eed8503a6bd3ef1b43a3ceef`；npm `servo-installer@0.6.0-rc.0` 的 `gitHead` 同为 `be5df6ec2a4d5fa9eed8503a6bd3ef1b43a3ceef`
- publish workflow run `26733468086` completed successfully for `v0.6.0-rc.0`
- npm `servo-installer@0.6.0-rc.0` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.0-rc.0.tgz`
- GitHub Release `v0.6.0-rc.1` 已发布为 prerelease，target commit `8259ee4da572cdf92b2da345a7c53c0ed5de99c9`；npm `servo-installer@0.6.0-rc.1` 的 `gitHead` 同为 `8259ee4da572cdf92b2da345a7c53c0ed5de99c9`
- publish workflow run `26871159528` completed successfully for `v0.6.0-rc.1`
- npm `servo-installer@0.6.0-rc.1` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.0-rc.1.tgz`
- GitHub Release `v0.6.1-rc.0` 已发布为 prerelease，target commit `1fc5e27a00ce22bc3aca191e27b5f2dc5d43d022`；npm `servo-installer@0.6.1-rc.0` 的 `gitHead` 同为 `1fc5e27a00ce22bc3aca191e27b5f2dc5d43d022`
- publish workflow run `26968765353` completed successfully for `v0.6.1-rc.0`
- npm `servo-installer@0.6.1-rc.0` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.1-rc.0.tgz`
- GitHub Release `v0.6.1-rc.1` 已发布为 prerelease，target commit `85faf9b5a42a002959612008c9f227cf096eea34`；npm `servo-installer@0.6.1-rc.1` 的 `gitHead` 同为 `85faf9b5a42a002959612008c9f227cf096eea34`
- publish workflow run `27000370396` completed successfully for `v0.6.1-rc.1`
- npm `servo-installer@0.6.1-rc.1` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.1-rc.1.tgz`
- GitHub Release `v0.6.1-rc.2` 已发布为 prerelease，target commit `f11dd1f7e373d45fe4588b5d66aa67e822e5e149`；npm `servo-installer@0.6.1-rc.2` 的 `gitHead` 同为 `f11dd1f7e373d45fe4588b5d66aa67e822e5e149`
- publish workflow run `27082964685` completed successfully for `v0.6.1-rc.2`
- npm `servo-installer@0.6.1-rc.2` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.1-rc.2.tgz`

## 当前 source release tuple

2026-06-07，当前 source release tuple 已发布为 `v0.6.1-rc.2` next-channel RC prerelease；published registry facts reflect the completed `v0.6.1-rc.2` publish.

- root `package.json` version：`0.6.1-rc.2`
- local scaffold `toolchain/scripts/deploy/package.json` version：`0.6.1-rc.2`
- approval lock：`approvedVersion=0.6.1-rc.2`、`approvedGitTag=v0.6.1-rc.2`、`approvedChannel=next`
- release scope：发布 v0.6.1-rc.2 RC 测试版本，包含 `MS-20260606-001` 已验收的 Distributed Skill 自洽性、无包外软依赖治理、payload coverage 和 target install smoke 证据。
- publish status：published on npm `next`; GitHub Release `v0.6.1-rc.2` is a prerelease targeting `f11dd1f7e373d45fe4588b5d66aa67e822e5e149`; publish workflow `27082964685` completed successfully; npm `servo-installer@0.6.1-rc.2` gitHead is `f11dd1f7e373d45fe4588b5d66aa67e822e5e149`; `next` -> `0.6.1-rc.2`; `latest` 保持 `0.5.8`。

注意：`0.6.1-rc.2` 是 prerelease RC candidate；发布完成后的试用 selector 必须使用 `servo-installer@next`。默认 `servo-installer` 仍应解析到 `latest` 的 `0.5.8`，除非另有 stable release approval。

npm dist-tag 由 publish workflow 写入；此页只写已由 registry 和 GitHub 查询复核过的事实。`4.4.x` 相关 git tag 保留作为历史记录，不在 npm registry 中发布。

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
