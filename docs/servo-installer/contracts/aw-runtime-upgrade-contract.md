---
title: ".aw Runtime 升级合同"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# .aw Runtime 升级合同

> 目的：定义目标仓库仍保留 legacy `.aw/` Harness runtime state、且需要收敛到 `.servo/` 时的安全升级边界。

本合同承接 `.aw/` runtime state migration 的 operator-visible 与 implementation-facing 规则。它不定义 skill payload install semantics、release policy 或 package versioning。

## 所有权边界

`.aw/` 和 `.servo/` 是目标仓库中的 Harness runtime state directories。它们不是 servo-installer skill payload，也不是 deploy targets。

installer 可以提供显式 upgrade command 或 flow，把 runtime state 从 `.aw/` 复制或迁移到 `.servo/`；但普通 `install`、`update`、`verify`、`diagnose`、`check_paths_exist` 和 `prune --all` 绝不能静默把 `.aw/` 改写成 `.servo/`。

Installer-managed skill payload 仍位于 backend target roots 下：

- `agents`: `<targetRepoRoot>/.agents/skills/aw-{skill_id}/`
- `claude`: `<targetRepoRoot>/.claude/skills/{skill_id}/`

这些目录继续使用 runtime-generated `aw.marker` 文件标识 managed payload identity。marker 名称是兼容合同，不应被解释为 `.aw/` runtime state 仍然是当前状态的证据。

## 显式入口

升级路径必须是 opt-in。有效 entrypoint 必须在 mutation 前让目标状态、计划动作、destructive 或 overwrite 风险可见。

Canonical command shape：

```text
servo-installer migrate-runtime --from aw --to servo [--json] [--yes] [--backend agents|claude|bundle] [--reinstall]
```

确切命令名只有在替代命令仍保持相同显式 `from aw` / `to servo` 语义、并在同一 worktrack 更新本合同的情况下，才可以在实现过程中调整。

最小命令语义：

- default mode：只 dry-run 或 preview
- mutating mode：要求显式确认 flag，例如 `--yes`
- `--json` 只读，且与 `--yes` 互斥
- target root：使用现有 installer commands 相同的 target root resolution rules
- backend：只有 reinstall / update 部分可以是 `agents`、`claude` 或 `bundle`；runtime state migration 本身是 backend-neutral
- `--reinstall` 控制 runtime state migration 后是否计划运行现有 reinstall / update 链；没有该参数时，命令只处理 runtime state

entrypoint 至少必须报告：

- 检测到的 `.aw/` state
- 检测到的 `.servo/` state
- migration 是否被阻断
- 计划 copy 或 restore source
- legacy `.aw/` 的 backup 或 retention path
- state migration 后是否运行 reinstall / update
- blocked 时的 recovery guidance

Exit semantics：

- `0`：dry-run / JSON 已完成且无 blocking issue，或 `--yes` 已完成全部计划 mutation 和 post-checks
- `1`：blocked、validation failed、partial copy failed、reinstall / update failed，或 arguments 不安全
- 无 partial-success exit code：partial completion 通过 structured output 和 stderr 表达

JSON output 必须包含稳定 top-level fields：`target_root`、`source_runtime_path`、`destination_runtime_path`、`state`、`verdict`、`planned_actions`、`backup_policy`、`reinstall_plan`、`blocking_issues`、`recovery_hints` 和 `mutation_performed`。实现也可以暴露 compatibility / detail fields，例如 `target_repo_root`、`action`、`mutation_allowed`、`sentinel_path`、`sentinel_present`、`issue_count` 和 `issues`。

## 状态矩阵

| Target State | Default Verdict | Required Behavior |
| --- | --- | --- |
| 无 `.aw/`，无 `.servo/` | no-op | 报告不存在 legacy runtime state。不要在本升级流程中创建 `.servo/`。 |
| 只有 `.aw/` | ready | Dry-run 报告计划执行 `.aw/` 到 `.servo/` 的 copy 和 retention behavior。Mutating mode 可以创建 `.servo/`。 |
| 只有 `.servo/` | no-op | 报告已经在 `.servo/` 上。不要触碰 `.aw/`。 |
| `.aw/` 与 `.servo/` 同时存在 | blocked | 默认 fail closed。提供 recovery options；不要自动 merge 或 overwrite。 |
| `.aw/` 不可读或 malformed | blocked | 不要猜测。报告 unreadable path 并保留内容。 |
| `.servo/` 不可读或 malformed | blocked | 不要覆盖。报告 recovery options。 |
| 存在 previous successful migration marker | idempotent | 重复运行必须安全，不能重复 backup 或降低 `.servo/` 状态。 |

实现可以使用额外 sentinel metadata 让 idempotence 可观察，但 sentinel 不能成为 Harness state 的 source of truth。

在本合同中，malformed 包括：path 存在但不是目录、需要真实目录的位置出现 symlink、目录不可读、broken symlink、当命令被要求保留等价 runtime state 时缺少 expected baseline files，或 artifact text 无效导致无法 faithful copy。Malformed 不授权通过猜测进行修复。

## 复制和保留规则

默认 mutating action 是 copy，不是 move。

必需行为：

- 默认保留 user-owned `.aw/` contents
- 除非 operator 显式请求 cleanup，否则绝不删除 `.aw/`
- 如果使用 backup，应放在 active `.servo/` 之外、名称清晰的路径下
- 在本地文件系统允许范围内，尽量忠实保留 file content 和 relative paths
- 在平台支持时保留 normal file modes
- 避免使用已知会在 supported target paths 上崩溃的 platform-native bulk copy APIs；installer copy implementation 必须能处理包含非 ASCII 字符的 Windows paths
- 只有 symlink resolve 后仍位于 source runtime tree 内时才复制 symlinks；否则 block 并给出 recovery hint
- 当 `.servo/` 已存在时，在 partial overwrite 前 fail
- 如果 partial copy 失败，报告 source 和 destination state，并保留 recovery guidance
- 绝不静默清理 partial destination data
- **成功 copy 后，递归扫描 `.servo/` 下的文本文件（`.md`、`.json`、`.txt`），把 `.aw` path references 改写为 `.servo`**，使迁移后的 Harness artifacts（control-state、milestone、worktrack）引用当前 runtime directory，而不是 legacy directory；rewrite 必须保持 branch names（`develop-aw`、`aw/demo-*`）和 `aw.marker` references 不变

清理 `.aw/` 是独立 operator decision。它不能被捆绑进默认 successful migration path。

如果引入 idempotence sentinel，它应位于 `.servo/` 下，并且只记录 migration metadata，例如 source path、timestamp、source hash summary、installer version 和 rewritten file count。它不能替代 `control-state.md`、`goal-charter.md` 或其他 Harness runtime artifacts 作为 truth。

## Reinstall / Update 耦合

runtime state migration 之后，installer 可以运行现有 destructive reinstall / update 链，让 installed skills 收敛到当前 naming 和 payload descriptors。

已实现 command shape：

```text
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents|claude|bundle
```

`--reinstall` 不是独立 migration mode。它会向 `migrate-runtime` 添加 update preflight；当 update plan 有 blocking issues 时，命令必须在复制 `.aw/` 到 `.servo/` 前停止。当 runtime migration 安全且 update plan 清晰时，命令会为选定 backend 运行现有 `update --yes` 链。Bundle mode 使用与 `servo-installer update --backend bundle --yes` 相同的 aggregate update composition。

reinstall / update 部分必须复用现有机制：

- `aw.marker` 标识 installer-managed payload directories
- `legacy_target_dirs` 和 `legacy_skill_ids` 驱动旧 skill target names 的 managed cleanup
- `payload_fingerprint` 证明 live target payload 与 current source 对齐
- `update --yes` 保持现有 `prune -> check_paths_exist -> install -> verify` 形状

runtime migration step 绝不能把 `aw.marker` 重新解释为 `.aw/` runtime marker。`aw.marker` 只属于 skill payload target directories。

## 冲突和恢复规则

升级路径采用 fail-closed。只要无法证明目标状态安全，就必须在 mutation 前 block。

Blocking cases 包括：

- `.aw/` 同时存在时，目标已有 `.servo/`
- source 或 destination runtime directories 不可读
- destination path 是文件或 symlink，而该位置需要目录
- target root safety validation failed
- requested cleanup 会在没有 explicit cleanup approval 的情况下删除 `.aw/`
- reinstall / update preflight 报告 blocking target path conflicts

Recovery guidance 必须区分：

- 保留 `.servo/` 并放弃 `.aw/`
- 手动 archive `.aw/` 后重新运行
- remove 或 relocate broken destination state 后重新运行
- reinstall / update 问题后运行 backend-specific `verify` / `diagnose`

在显式 successful migration 和任何独立 cleanup approval 之前，根 `.aw/` 仍是允许存在的 compatibility state。Governance checks 不应把仅仅存在 `.aw/` 解释为删除要求。一旦明确请求 cleanup，cleanup 仍必须保留 backup 或 operator-confirmed deletion evidence。

## Dry-Run 要求

Dry-run output 必须足够具体，便于 operator 或 CI log 审计。

最小字段：

- target root
- source runtime path
- destination runtime path
- 来自 state matrix 的 state classification
- planned filesystem actions
- backup 或 retention policy
- reinstall / update plan（如果启用）
- blocking issues
- recovery hints

Dry-run 绝不能创建、修改、移动、删除或 chmod 目标仓库文件。

`--json` 永远只读，并与 `--yes` 互斥。Human output 可以包含简短 `reinstall status` 和 `reinstall blocking issues` 摘要；JSON 在 `reinstall_plan.status` 和 `reinstall_plan.blocking_issue_count` 下暴露相同信息。

TUI 可以把 legacy `.aw/` 作为 warning 或 upgrade prompt 展示，但 mutating behavior 必须路由回显式 CLI-equivalent command shape。TUI `.servo` health checks 不能 auto-migrate `.aw/`；missing `.servo/` 且 present `.aw/` 应报告为 "legacy runtime state present"，而不是普通 generic uninitialized state。

## 测试面

实现 worktracks 至少必须包含以下 `/tmp` target repository smoke tests：

- 只有 `.aw/`
- 存在 `.servo/`
- `.aw/` 与 `.servo/` 同时存在
- `.aw/` path malformed
- `.servo/` path malformed
- dry-run 报告 planned actions 且不 mutation
- successful migration idempotent
- failed copy 暴露 recovery guidance
- Windows / non-ASCII target path migration 成功，且不依赖 `fs.cpSync`
- reinstall / update 通过现有 installer path 刷新 managed skill markers 和 payload fingerprints
- **path reference rewriting：`.aw/` -> `.servo/`，`` `.aw` `` -> `` `.servo` ``，`aw-set-harness-goal-skill` -> `servo-set-harness-goal-skill` in migrated text files；branch names（`develop-aw`、`aw/demo-*`）和 `aw.marker` 不能被改写**

当前已验证测试覆盖还包括：update preflight 在 runtime copy 前阻断，以及 bundle reinstall 安装两个 backend payloads。

测试不能在本源码仓库下创建 runtime state。

## 非目标

- 不变更 package version、npm dist-tag、release tag、publish state 或 release channel
- 不默认删除 `.aw/`
- 不静默覆盖 `.servo/`
- 不把 `.agents/` 或 `.claude/` deploy targets 用作 source truth
- 不迁移 `.autoworkflow/` 或 `.spec-workflow/`
- 不在本合同中改变 `aw.marker` 文件名

## 相关文档

- [Deploy Mapping Spec](./deploy-mapping-spec.md)
- [Distribution Entrypoint Contract](./distribution-entrypoint-contract.md)
- [Payload Provenance Trust Boundary](./payload-provenance-trust-boundary.md)
- [Managed Files Ownership](../reference/managed-files-ownership.md)
- [Skill Deployment Maintenance](../runbooks/skill-deployment-maintenance.md)
