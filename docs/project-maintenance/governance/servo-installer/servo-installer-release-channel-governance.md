---
title: "servo-installer Release Channel Governance"
status: active
updated: 2026-06-17
owner: servo-kernel
last_verified: 2026-06-17
---
# servo-installer Release Channel Governance

> 目的：定义 `servo-installer` 进入真实 npm release channel 前必须满足的发布准入规则，并记录当前 registry 事实。

本页属于 [Governance](./README.md) 路径簇。

管理 release channel/dist-tag 对应关系、publish 准入条件与当前 registry 事实。不管理 pre-publish tuple/packlist/doc freshness、smoke 执行、发布流程顺序与 wrapper/payload 边界。

## 当前 registry 事实

2026-06-15 已核对 npm registry：

- **版本号纠正**：`4.4.x` 系列（`v4.4.0`、`v4.4.0-rc.0`、`v4.4.1-rc.0`、`v4.4.1-rc.1`、`v4.4.1`）为错误发布的版本号，不进入 semver 主序列
- npm registry 真实状态：`latest` -> `0.5.8`；`next` -> `0.6.1-rc.4`；已发布版本：`0.5.3`、`0.5.4`、`0.5.5`、`0.5.6`、`0.5.7`、`0.5.8`、`0.6.0-rc.0`、`0.6.0-rc.1`、`0.6.1-rc.0`、`0.6.1-rc.1`、`0.6.1-rc.2`、`0.6.1-rc.3`、`0.6.1-rc.4`
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
- GitHub Release `v0.6.1-rc.3` 已发布为 prerelease，target commit `0d50babc52bd3b951f32f1085a569ded593d58bf`；npm `servo-installer@0.6.1-rc.3` 的 `gitHead` 同为 `0d50babc52bd3b951f32f1085a569ded593d58bf`
- publish workflow run `27488618986` completed successfully for `v0.6.1-rc.3`
- npm `servo-installer@0.6.1-rc.3` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.1-rc.3.tgz`
- GitHub Release `v0.6.1-rc.4` 已发布为 prerelease，target commit `09c3f5cad18262dcb0e5b2e0a68aae187ec0a722`；npm `servo-installer@0.6.1-rc.4` 的 `gitHead` 同为 `09c3f5cad18262dcb0e5b2e0a68aae187ec0a722`
- publish workflow run `27519370229` completed successfully for `v0.6.1-rc.4`
- npm `servo-installer@0.6.1-rc.4` tarball URL：`https://registry.npmjs.org/servo-installer/-/servo-installer-0.6.1-rc.4.tgz`

## 当前 source release tuple

2026-06-15，当前 source release tuple 已发布为 `v0.6.1-rc.4` next-channel RC prerelease。

- root `package.json` version：`0.6.1-rc.4`
- local scaffold `toolchain/scripts/deploy/package.json` version：`0.6.1-rc.4`
- approval lock：`approvedVersion=0.6.1-rc.4`、`approvedGitTag=v0.6.1-rc.4`、`approvedChannel=next`
- release scope：发布 v0.6.1-rc.4 RC 测试版本，包含 `MS-20260614-001`、`MS-20260614-002`、`MS-20260614-003` 与 `MS-20260615-001` 已合入 develop 的 installer reconcile、dogfood、测试分层与维护治理改动。
- publish status：GitHub Release `v0.6.1-rc.4` 已创建为 prerelease；publish workflow run `27519370229` 已完成；npm `servo-installer@0.6.1-rc.4` 已发布；`next` dist-tag 已指向 `0.6.1-rc.4`；`latest` 保持 `0.5.8`。

注意：`0.6.1-rc.4` 是 prerelease RC；试用 selector 必须使用 `servo-installer@next`。默认 `servo-installer` 仍应解析到 `latest` 的 `0.5.8`，除非另有 stable release approval。

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

## 当前 Known Issues

### rc.4 (0.6.1-rc.4) Registry-Only Reconcile 非收敛

`servo-installer@next`（`0.6.1-rc.4`）在 registry-only 模式下 `.servo` reconcile 不收敛：

- **现象**：apply 后的 second dry-run 仍有 7 changes，其中含 repeated blank Task List `append_field`（`task_id`、`status`、`priority`、`assigned`、`description`、`depends_on`、`acceptance`、`risk_level`、`stop_condition` 等字段均为空值）
- **影响**：rc.4 的已发布包面在外部 repo 上不能通过 reconcile 收敛验证
- **根因**：reconcile helper/template 在写入 runtime artifact 时对已有 blank placeholder field 继续追加，而非 skip
- **修复状态**：post-rc4 fix（commit `893f8c6` blank placeholder idempotency fix + `ddc7467` duplicate field convergence fix）已在 local source HEAD（`122f6be7f0396639f4ab80d3c40ff5ee1484902f`）中，但不在已发布的 rc.4 tarball 内
- **npm registry 事实**：`servo-installer@0.6.1-rc.4` 的 `gitHead` 为 `09c3f5cad18262dcb0e5b2e0a68aae187ec0a722`；remote tag `v0.6.1-rc.4` 也指向同一 commit
- **修复包面验证**：需发布新 RC 后重跑 registry-only reconcile smoke；local-source-root pass 可以声明 "fix in HEAD"，但不能替代 registry-only 包面证据
- **证据**：`.test/execution/evidence/registry-repro/att-registry-repro-20260617t011911-p0800-a01/manifest.json`；`.test/execution/evidence/light-runtime-smoke-rating-registry/att-light-runtime-smoke-rating-registry-20260617t145310-p0800-a03/manifest.json`

### 发布前 Real Dogfood Gate

自 MS-20260615-003 起，发布 RC 前必须收集真实 dogfood 证据。详细准入要求见 [servo-installer Pre-Publish Governance](./servo-installer-pre-publish-governance.md#5-real-dogfood-gate)。覆盖：

- COV-SKILLS：skills update/diagnose/verify dogfood
- COV-SERVO：`.servo` reconcile dry-run/apply/second-dry-run 收敛（registry-only 必须项 + local-source-root 补充项）
- COV-HARNESS：harness-skill 入口语义 read-only invocation
- Managed Surface Audit：独立于 git status 的 `.skills`/`.agents`/`.claude`/`.servo` hash 审计
- Disposable workspace 方法论：所有 dogfood 在 freeze repo 临时副本上执行，不变更原始 repo

Dogfood evidence 存放于 `.test/execution/evidence/`；长期参考见 [Testing Runbooks](../../testing/README.md#真实-backend-dogfood)。
