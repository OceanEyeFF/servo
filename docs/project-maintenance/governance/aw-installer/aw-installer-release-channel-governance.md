---
title: "aw-installer Release Channel Governance"
status: active
updated: 2026-05-20
owner: aw-kernel
last_verified: 2026-05-20
---
# aw-installer Release Channel Governance

> 目的：定义 `aw-installer` 进入真实 npm release channel 前必须满足的发布准入规则，并记录当前 registry 事实。

本页属于 [Governance](./README.md) 路径簇。

管理 release channel/dist-tag 对应关系、publish 准入条件与当前 registry 事实。不管理 pre-publish tuple/packlist/doc freshness、smoke 执行、发布流程顺序与 wrapper/payload 边界。

## 当前 registry 事实

2026-05-20 已核对 npm registry：

- **版本号纠正**：`4.4.x` 系列（`v4.4.0`、`v4.4.0-rc.0`、`v4.4.1-rc.0`、`v4.4.1-rc.1`、`v4.4.1`）为错误发布的版本号，不进入 semver 主序列
- npm registry 真实状态：`latest` -> `0.5.1`，`next` -> `0.5.2-rc.3`，历史已发布版本 `0.4.0-rc.1` ~ `0.5.2-rc.3`
- GitHub Release `v0.4.5` 已发布，target commit `c7f9a31a184602c8500038998c41565dce8d4972`；npm `aw-installer@0.4.5` 的 `gitHead` 同为 `c7f9a31a184602c8500038998c41565dce8d4972`
- GitHub Release `v0.5.0-rc.0` 已发布，target commit `c7683fc9767cb66b123fb4ba493ea539791392d7`；npm `aw-installer@0.5.0-rc.0` 的 `gitHead` 同为 `c7683fc9767cb66b123fb4ba493ea539791392d7`
- GitHub Release `v0.5.0-rc.1` 已发布，target commit `f7728bb9c0f463376a85585e18812f931087531b`；npm `aw-installer@0.5.0-rc.1` 的 `gitHead` 同为 `f7728bb9c0f463376a85585e18812f931087531b`
- GitHub Release `v0.5.1-rc.0` 已发布，target commit `039301689a2fb74922fc67edc86b0a194633628a`；npm `aw-installer@0.5.1-rc.0` 的 `gitHead` 同为 `039301689a2fb74922fc67edc86b0a194633628a`
- GitHub Release `v0.5.1-rc.1` 已发布，target commit `d2b6fd53b69f3f9bdbe10b547872eca942ad723a`；npm `aw-installer@0.5.1-rc.1` 的 `gitHead` 同为 `d2b6fd53b69f3f9bdbe10b547872eca942ad723a`
- GitHub Release `v0.5.1-rc.2` 已发布，target commit `e5c774eb5763faee8b6c658f02d3b4f59d3ce0c9`；npm `aw-installer@0.5.1-rc.2` 的 `gitHead` 同为 `e5c774eb5763faee8b6c658f02d3b4f59d3ce0c9`
- GitHub Release `v0.5.1` 已发布，target commit `8215db89dbc7a75e14a8570d7745781de7a78d47`；npm `aw-installer@0.5.1` 的 `gitHead` 同为 `8215db89dbc7a75e14a8570d7745781de7a78d47`
- GitHub Release `v0.5.2-rc.0` 已发布，target commit `dd4094ce5dc9e7a76ba2e49db5cccdb3110aa875`；npm `aw-installer@0.5.2-rc.0` 的 `gitHead` 同为 `dd4094ce5dc9e7a76ba2e49db5cccdb3110aa875`
- GitHub Release `v0.5.2-rc.1` 已发布，target commit `34b07d93fad1b03423e36881ba7f269e55a1cceb`；npm `aw-installer@0.5.2-rc.1` 的 `gitHead` 同为 `34b07d93fad1b03423e36881ba7f269e55a1cceb`
- GitHub Release `v0.5.2-rc.2` 已发布，target commit `df2167139849d02c4d89f09a1b013856bbd1c9b2`；npm `aw-installer@0.5.2-rc.2` 的 `gitHead` 同为 `df2167139849d02c4d89f09a1b013856bbd1c9b2`；tarball URL：`https://registry.npmjs.org/aw-installer/-/aw-installer-0.5.2-rc.2.tgz`
- GitHub Release `v0.5.2-rc.3` 已发布，target commit `3bb60b3414a99c18fcc7cfcb6d833d30fddf9352`；npm `aw-installer@0.5.2-rc.3` 的 `gitHead` 同为 `3bb60b3414a99c18fcc7cfcb6d833d30fddf9352`；tarball URL：`https://registry.npmjs.org/aw-installer/-/aw-installer-0.5.2-rc.3.tgz`

## 当前 source release tuple

2026-05-20，source tuple 已发布为 `v0.5.2-rc.3` 的 `next` channel release candidate：

- root `package.json` version：`0.5.2-rc.3`
- local scaffold `toolchain/scripts/deploy/package.json` version：`0.5.2-rc.3`
- Harness payload `product/harness/skills/harness-skill/VERSION`：`0.5.2-rc.3`
- approval lock：`approvedVersion=0.5.2-rc.3`、`approvedGitTag=v0.5.2-rc.3`、`approvedChannel=next`
- CLI `--version` 输出：`aw-installer 0.5.2-rc.3`
- GitHub Release `v0.5.2-rc.3`：prerelease，target commit `3bb60b3414a99c18fcc7cfcb6d833d30fddf9352`
- publish workflow run：`26148178721`，conclusion `success`
- npm `aw-installer@0.5.2-rc.3`：已发布到 `next` dist-tag，`gitHead=3bb60b3414a99c18fcc7cfcb6d833d30fddf9352`

注意：`0.5.2-rc.3` 是 prerelease，不改变 stable selector；默认 `aw-installer` 仍解析到 `latest` 的 `0.5.1`。RC 试用必须显式使用 `aw-installer@next`，当前解析到 `0.5.2-rc.3`。

npm dist-tag 由 publish workflow 写入，此页跟随 release commit 同步事实。`4.4.x` 相关 git tag 保留作为历史记录，不在 npm registry 中发布。

## Channel 对应关系

| channel | npm dist-tag | version form |
| --- | --- | --- |
| `latest` | `latest` | stable semver，例如 `1.2.3` |
| `next` | `next` | `alpha` / `beta` / `rc` prerelease |
| `canary` | `canary` | 含 `canary` 段的 prerelease |

stable operator-facing selector 使用默认 `aw-installer`；RC 试用 selector 必须显式使用 `aw-installer@next`。

## 真实 Publish 准入

必须同时满足：package name 为 `aw-installer`，version 是合法 semver（非 `-local`），tuple（`approvedVersion`/`approvedGitTag`/`approvedChannel`）一致，`AW_INSTALLER_RELEASE_GIT_TAG=v<version>`，GitHub Release body 含 `aw-installer-publish-approved: v<version>`，`CI=true`，`AW_INSTALLER_PUBLISH_APPROVED=1`，channel/dist-tag 一致（`latest`仅 stable，`next`仅 alpha/beta/rc，`canary`仅含 canary 的 prerelease）。`npm run publish:dry-run --silent` 不构成 publish 授权。

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

- [aw-installer Release Standard Flow](./aw-installer-release-standard-flow.md)
- [aw-installer Release Operation Model](./aw-installer-release-operation-model.md)
- [aw-installer Pre-Publish Governance](./aw-installer-pre-publish-governance.md)
- [npx Command Test Execution](../../testing/npx-command-test-execution.md)
