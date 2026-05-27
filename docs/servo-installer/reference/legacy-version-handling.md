---
title: "旧版本处理"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-05-27
---
# 旧版本处理

> 这是面向旧目标仓库的临时兼容说明：这些仓库仍可能保留 `.aw/` runtime state，或保留旧 installer-managed skill target dirs。预计在 `0.7.x` 系列、legacy migration window 关闭后移除此文档。

## 范围

本文记录当前对 legacy target 的兼容行为，覆盖 current `servo-*` agents target-dir 约定稳定前产生的旧状态。

覆盖范围：

- 根目录 `.aw/` Harness runtime state
- 旧 `.agents/skills/aw-*` managed skill target dirs
- 当 agents 和 claude 同时安装时，已有 `.claude/skills/*` targets 的处理
- `0.5.x` 与 `0.6.x` compatibility window 内的 packaged installer upgrade smoke 预期

本文不定义 release policy、npm dist-tags、package version approval 或未来移除机制。Release governance 仍归 `docs/project-maintenance/governance/servo-installer/` 承接。

## 移除窗口

本文是过渡期支持文档。

- 在 `0.5.x` 与 `0.6.x` compatibility window 内保留本文。
- 预计在 `0.7.x` 移除本文。
- 移除前必须确认 operator-facing runbooks 不再需要针对 `.aw/` runtime state 或旧 `aw-*` agents target dirs 的专门处理。
- 移除本文不能静默删除 runtime migration code；任何代码移除都需要独立 worktrack 和验证。

## Legacy 状态

| Legacy state | 当前处理 |
|---|---|
| 存在 `.aw/` 且不存在 `.servo/` | `servo-installer migrate-runtime --from aw --to servo --json` 报告 ready copy plan。带 `--yes` 时创建 `.servo/`，把迁移文本文件中的 `.aw` path references 改写为 `.servo`，并保留 `.aw/`。 |
| `.aw/` 与 `.servo/` 同时存在 | 默认阻断迁移，除非已有 prior migration sentinel 能证明目标已迁移。 |
| 存在 `.agents/skills/aw-*` managed dirs | `servo-installer update --backend agents --yes` 会把旧 managed target dirs 替换为当前 `servo-*` target dirs。 |
| 存在 `.agents/skills/servo-*` | 当前 agents target shape；按正常 verify / update 处理。 |
| 存在 `.claude/skills/<skill-id>` | 当前 claude target shape；按正常 verify / update 处理。 |
| `.agents` 与 `.claude` 同时存在 | 当两个 backend 都需要一起收敛时，使用 `--backend bundle` 做 aggregate verify / update / reinstall。 |

## Operator 路径

对于带 `.aw/` runtime state 的 legacy target：

```bash
servo-installer migrate-runtime --from aw --to servo --json
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents
rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  '(\.aw/|`\.aw`|\.aw control|\.aw 控制|write.*\.aw|写.*\.aw|sync.*\.aw|同步.*\.aw|\.servo/\.aw|\.aw/\.servo)' \
  docs .servo .agents .claude
servo-installer verify --backend agents
servo-installer diagnose --backend agents
```

如果需要上传诊断证据，CLI 可加 `--log-dir`：

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle --log-dir .logs/servo-installer
```

TUI 会默认写入目标仓库 `.logs/servo-installer/` 并打印具体日志文件路径。

对于同时有 agents 和 claude deploy targets 的目标：

```bash
servo-installer migrate-runtime --from aw --to servo --json
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  '(\.aw/|`\.aw`|\.aw control|\.aw 控制|write.*\.aw|写.*\.aw|sync.*\.aw|同步.*\.aw|\.servo/\.aw|\.aw/\.servo)' \
  docs .servo .agents .claude
servo-installer verify --backend bundle
servo-installer diagnose --backend bundle
```

对于 runtime state 已迁移、但仍保留旧 agents target dirs 的目标：

```bash
servo-installer update --backend agents --yes
servo-installer verify --backend agents
```

## 安全规则

- 普通 `install`、`update`、`verify`、`diagnose`、`check_paths_exist` 和 `prune --all` 不会静默把 `.aw/` 迁移到 `.servo/`。
- 成功迁移后，默认保留 `.aw/`。
- 清理 `.aw/` 是显式 operator decision，不属于默认升级路径。
- 迁移后应只读扫描目标仓库的 `docs/`、`.servo/`、`.agents/` 和 `.claude/`，找出仍要求写入、刷新或同步 `.aw/` control state 的当前指令。历史说明、branch names、legacy 复现文本和 `aw.marker` 不应被无差别替换。
- managed skill target dirs 内的 `aw.marker` 是 deploy identity metadata；它不等同于根目录 `.aw/` runtime state。
- agents 和 claude deploy targets 有不同的 canonical target naming：
  - agents：`.agents/skills/servo-<skill-id>`
  - claude：`.claude/skills/<skill-id>`
- Bundle mode 必须在各自 target root 内刷新每个 backend；不能把 claude targets 重命名为 agents naming，也不能把 agents targets 重命名为 claude naming。

## 已验证兼容证据

以下证据最初收集于 2026-05-23，使用从源码树生成的 packaged `servo-installer-0.5.3.tgz`。

2026-05-27 起，`toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh --skip-remote` 会从当前源码打包本地 `.tgz`，并在隔离临时 target 中回归以下 legacy migration 场景。

| 场景 | 结果 |
|---|---|
| `/tmp/repo-rating-function` 带 `.aw/` 和旧 `.agents/skills/aw-*` dirs | Packaged `migrate-runtime --yes --reinstall --backend agents` 将 `.aw` 复制到 `.servo`，改写 path references，将旧 managed agents dirs 替换为 21 个 `servo-*` dirs，并通过 verify / diagnose。 |
| 在 `/tmp/repo-rating-function` 上重复迁移 | Packaged JSON 返回 `state=already-migrated`、`verdict=already-migrated`、`sentinel_present=true`。 |
| `/tmp/servo-dual-backend-smoke.OZuLrQ` 带 `.aw/`、`.agents/skills/servo-*` 和 `.claude/skills/<skill-id>` | Packaged `migrate-runtime --yes --reinstall --backend bundle` 独立刷新两个 backend，并通过 bundle verify / diagnose。 |
| `legacy-aw-only-中文` 临时 target | Packaged `.tgz` 入口执行 `.aw -> .servo`，保留 `.aw/`，改写 `.servo/` 文本 path references，并证明 `develop-aw` 与 `aw/*` branch names 不被误改；重复执行返回 already-migrated no-op。 |
| `legacy-bundle` 临时 target | Packaged `.tgz` 入口执行 `migrate-runtime --yes --reinstall --backend bundle`，移除 managed legacy `aw-*` target dirs，收敛 agents `servo-*` 与 claude canonical target dirs，并通过 bundle verify / diagnose。 |
| `legacy-conflict` 临时 target | Packaged `.tgz` 入口在 `.aw/ + .servo/` 无 migration sentinel 时阻塞，返回 `destination-runtime-exists`，且不改写既有 `.servo/`。 |
| Runtime equivalence checks | 在排除 `.servo-installer-aw-migration.json` 后，两个 smoke targets 中 `.aw/` 与 `.servo/` 匹配。自 path reference rewriting（v0.5.6+）后，`.servo/` 文本文件内的 `.aw` path references 会改写为 `.servo`；不再要求 raw file equality。 |

## 相关文档

- [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md)
- [Legacy `.aw` Runtime Upgrade Runbook](../runbooks/aw-runtime-upgrade-runbook.md)
- [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)
- [Managed Files Ownership](./managed-files-ownership.md)
