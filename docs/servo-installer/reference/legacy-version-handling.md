---
title: "旧版本处理"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-05-27
---
# 旧版本处理

> 本文是面向 v0.6.0 之前版本接入的仓库（下文统称「旧版仓库」）的临时兼容说明——这些仓库使用 autoworkflow 分发体系，仍保留 `.aw/` 目录（`.servo/` 的前身）及该时代的旧版 control state，或保留旧版 installer 管理的 skill target 目录。本文在 `0.5.x`–`0.6.x` 的旧版迁移窗口内有效，预计 `0.7.0` 起不再提供旧版迁移支持后移除此文档。

## 范围

本文记录对旧版仓库的兼容行为，覆盖 `servo-*` agent target 目录命名约定（`0.6.0` 起确立）稳定前产生的旧状态。

覆盖范围：

- `.aw/ → .servo/` 的运行时迁移（`migrate-runtime --from aw --to servo`）
- 对 `.agents/` 和 `.claude/` 下 skill target 目录的处理——仅安装一侧时按对应 backend 处理，两侧均安装时使用 `--backend bundle`
- 上述行为均有冒烟测试覆盖

本文不定义发布策略、npm dist-tags、版本审批或未来移除机制。发布治理规则仍由 `docs/project-maintenance/governance/servo-installer/` 承接。

> **本文术语**
>
> - `runtime state`：旧版 `.aw/` 下的控制状态（新版对应 `.servo/` control state）
> - `target 目录`：installer 在 `.agents/skills/` 或 `.claude/skills/` 下管理的 skill 安装目录
> - `backend`：installer 的部署目标类型（agents / claude / bundle）
> - `migration sentinel`：迁移完成后写入的标记文件，用于防止重复迁移
> - `bundle`：agents 与 claude 的聚合模式

## 移除窗口

本文是过渡期支持文档。

- 在 `0.5.x`–`0.6.x` 旧版迁移窗口内保留本文。
- 预计在 `0.7.0` 移除本文。
- 移除前必须确认面向 operator 的 runbook 不再需要针对 `.aw/` 旧版 control state 或旧 `aw-*` agent target 目录的专门处理。
- 移除本文不得静默删除运行时迁移代码；任何代码移除均需独立的 worktrack 与验证。

## Legacy 状态

| Legacy state | 当前处理 |
|---|---|
| 存在 `.aw/` 且不存在 `.servo/` | `servo-installer migrate-runtime --from aw --to servo --json` 输出待迁移文件清单。带 `--yes` 时创建 `.servo/`，将其中包含 `.aw` 路径引用的文本文件改为 `.servo` 路径，同时保留原有 `.aw/`。 |
| `.aw/` 与 `.servo/` 同时存在 | 默认阻断迁移，除非已有迁移标记（migration sentinel）能证明该仓库已完成迁移。 |
| 存在 `.agents/skills/aw-*` managed dirs | `servo-installer update --backend agents --yes` 会将旧 managed target 目录替换为当前 `servo-*` target 目录。 |
| 存在 `.agents/skills/servo-*` | 当前 agents target 形态；按正常 verify / update 流程处理。 |
| 存在 `.claude/skills/<skill-id>` | 当前 claude target 形态；按正常 verify / update 流程处理。 |
| `.agents` 与 `.claude` 同时存在 | 当两个 backend 均需同步收敛时，使用 `--backend bundle` 做聚合 verify / update / reinstall。 |

## Operator 路径

对于仍保留 `.aw/` 旧版 control state 的旧版仓库：

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

对于 agents 与 claude 均已部署的仓库：

```bash
servo-installer migrate-runtime --from aw --to servo --json
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  '(\.aw/|`\.aw`|\.aw control|\.aw 控制|write.*\.aw|写.*\.aw|sync.*\.aw|同步.*\.aw|\.servo/\.aw|\.aw/\.servo)' \
  docs .servo .agents .claude
servo-installer verify --backend bundle
servo-installer diagnose --backend bundle
```

对于已迁移旧版 control state、但仍保留旧 agent target 目录的仓库：

```bash
servo-installer update --backend agents --yes
servo-installer verify --backend agents
```

## 安全规则

- 普通 `install`、`update`、`verify`、`diagnose`、`check_paths_exist` 和 `prune --all` 不会静默将 `.aw/` 迁移为 `.servo/`。
- 成功迁移后，默认保留 `.aw/`。
- 清理 `.aw/` 是 operator 的显式决策，不属于默认升级路径。
- 迁移后应只读扫描目标仓库的 `docs/`、`.servo/`、`.agents/` 和 `.claude/`，找出仍引用 `.aw/` 旧版 control state 的残留指令。历史说明、分支名、旧版复现文本和 `aw.marker` 不应被无差别替换。
- managed skill target 目录下的 `aw.marker` 是部署身份标记（deploy identity metadata），不等同于根目录的 `.aw/` 旧版 control state。
- agents 与 claude 的 deploy target 使用不同的 target 命名规范：
  - agents：`.agents/skills/servo-<skill-id>`
  - claude：`.claude/skills/<skill-id>`
- bundle 模式在各自 target root 内独立刷新每个 backend，不得将 claude target 重命名为 agents 命名规范，反之亦然。

## 已验证兼容证据

以下证据最初收集于 2026-05-23，使用从源码树生成的 packaged `servo-installer-0.5.3.tgz`。

2026-05-27 起，`toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh --skip-remote` 会从当前源码打包本地 `.tgz`，并在隔离临时 target 中回归以下 legacy migration 场景。

| 场景 | 结果 |
|---|---|
| `/tmp/repo-rating-function` 带 `.aw/` 和旧 `.agents/skills/aw-*` 目录 | Packaged `migrate-runtime --yes --reinstall --backend agents` 将 `.aw` 复制到 `.servo`，改写路径引用，将旧 managed agents 目录替换为 21 个 `servo-*` 目录，并通过 verify / diagnose。 |
| 在 `/tmp/repo-rating-function` 上重复迁移 | Packaged JSON 返回 `state=already-migrated`、`verdict=already-migrated`、`sentinel_present=true`。 |
| `/tmp/servo-dual-backend-smoke.OZuLrQ` 带 `.aw/`、`.agents/skills/servo-*` 和 `.claude/skills/<skill-id>` | Packaged `migrate-runtime --yes --reinstall --backend bundle` 独立刷新两个 backend，并通过 bundle verify / diagnose。 |
| `legacy-aw-only-中文` 临时 target | Packaged `.tgz` 入口执行 `.aw -> .servo`，保留 `.aw/`，改写 `.servo/` 文本路径引用，并证明 `develop-aw` 与 `aw/*` 分支名不被误改；重复执行返回 already-migrated no-op。 |
| `legacy-bundle` 临时 target | Packaged `.tgz` 入口执行 `migrate-runtime --yes --reinstall --backend bundle`，移除 managed legacy `aw-*` target 目录，收敛 agents `servo-*` 与 claude canonical target 目录，并通过 bundle verify / diagnose。 |
| `legacy-conflict` 临时 target | Packaged `.tgz` 入口在 `.aw/ + .servo/` 无 migration sentinel 时阻塞，返回 `destination-runtime-exists`，且不改写既有 `.servo/`。 |
| Runtime equivalence checks | 在排除 `.servo-installer-aw-migration.json` 后，两个 smoke targets 中 `.aw/` 与 `.servo/` 匹配。自 path reference rewriting（v0.5.6+）后，`.servo/` 文本文件内的 `.aw` path references 会改写为 `.servo`；不再要求 raw file equality。 |

## 相关文档

- [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md)
- [Legacy `.aw` Runtime Upgrade Runbook](../runbooks/aw-runtime-upgrade-runbook.md)
- [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)
- [Managed Files Ownership](./managed-files-ownership.md)
