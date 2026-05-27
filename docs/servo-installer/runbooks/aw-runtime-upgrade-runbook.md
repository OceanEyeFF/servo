---
title: "Legacy .aw Runtime 升级手册"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-05-27
---
# Legacy .aw Runtime 升级手册

> 目的：给 operator 一条明确路径，用于把 legacy `.aw/` Harness runtime state 显式迁移到 `.servo/`，同时不删除 `.aw/`，也不静默覆盖已有 `.servo/`。

规范行为由 [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md) 定义。本手册只承接 procedural operator path。

## 何时使用

当目标仓库保留来自旧 Harness 安装的 `.aw/` runtime state，并且你希望把该 runtime state 移到 `.servo/` 时，使用本手册。

不要用普通 `install`、`update`、`verify`、`diagnose`、`check_paths_exist` 或 `prune --all` 迁移 runtime state。这些命令管理的是 installed skill payloads，不是根目录 runtime directories。

## 只读预览

先从 dry-run preview 开始：

```bash
servo-installer migrate-runtime --from aw --to servo
```

用于 CI 或结构化日志：

```bash
servo-installer migrate-runtime --from aw --to servo --json
```

两种形式都是只读的。`--json` 与 `--yes` 互斥。

## 执行 Runtime 迁移

当预览报告只有 `.aw/` 且没有 blocking issues 时，执行复制：

```bash
servo-installer migrate-runtime --from aw --to servo --yes
```

该命令把 `.aw/` 复制到 `.servo/`，在迁移后的文本文件（`.md`、`.json`、`.txt`）中把 `.aw` path references 改写为 `.servo`，并在 `.servo/` 下写入 migration sentinel。Branch names（`develop-aw`、`aw/demo-*`）和 `aw.marker` 保持不变。命令会原地保留 `.aw/`。清理 `.aw/` 是独立 operator decision，不属于本手册的默认流程。

成功迁移后重复运行是安全的：sentinel 会让命令报告 `already-migrated`，而不是覆盖 `.servo/`。

复制路径使用 installer-owned recursive file copying，而不是 Node 原生 `fs.cpSync`，因此 installer migration path 支持包含非 ASCII 字符的 Windows target paths。

## 扫描旧 `.aw` 写回指令

Runtime 迁移只能处理 `.aw/` 复制到 `.servo/` 过程中的文本 path references。它不会、也不应该自动重写目标仓库里由用户维护的设计文档、运行记录或历史 handback。迁移完成后，operator 应在目标仓库执行一次只读扫描，确认当前文档和运行产物不会继续引导 agent 或人工同步 `.aw/`。

建议从目标仓库根目录运行：

```bash
rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  '(\.aw/|`\.aw`|\.aw control|\.aw 控制|write.*\.aw|写.*\.aw|sync.*\.aw|同步.*\.aw|\.servo/\.aw|\.aw/\.servo)' \
  docs .servo .agents .claude
```

如果目标仓库仍保留 `.aw/` 作为迁移源或历史归档，可单独扫描它作为参考；不要把 `.aw/` 里的旧文字当作迁移后的当前控制指令。

扫描结果需要区分：

- 可保留的历史说明、兼容性说明、复现记录、branch name（例如 `develop-aw`、`aw/demo-*`）和 installer deploy metadata（例如 `aw.marker`）。
- 需要修正的当前指令：要求写入、刷新、同步或验收 `.aw/` control state 的文字。
- 需要修正的迁移后 runtime 产物：`.servo/` 下仍写着 `.aw/.servo` 双写、同步 `.aw`、或把 `.aw` 当作当前 Harness 控制面的记录。

修正时只替换当前控制面语义：把“写入/同步 `.aw/`”改成“写入/同步 `.servo/`”。不要对所有 `aw` 字符串做无差别替换，因为 branch names、legacy history 和 `aw.marker` 仍可能是正确内容。若需要留存证据，可把 `migrate-runtime` 或 TUI 的 `--log-dir .logs/servo-installer` 输出与扫描结果一起附到 issue。

## 执行迁移并刷新已安装 Skills

如果还希望 installed skill payloads 收敛到当前 source metadata，运行：

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend agents
```

对于 Claude：

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend claude
```

对于两个 backend：

```bash
servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
```

`--reinstall` 会先计算现有 update plan。如果 update preflight 有 blocking conflicts，命令会在复制 `.aw/` 到 `.servo/` 前停止。如果 runtime migration 安全且 update preflight 清晰，它会复用现有 `update --yes` 链：`prune --all -> check_paths_exist -> install -> verify`。

对于 `agents`，reinstall / update 链也会把 installer-managed legacy `aw-*` skill target dirs 替换为当前 `servo-*` target dirs。`diagnose` 和 `update` 会在 mutating run 前把这一点作为 upgrade guidance 暴露出来。

`aw.marker` 仍是 installer-managed payload identity。它不是 `.aw/` runtime state 的证据。

## 状态矩阵

| Target state | 结果 |
| --- | --- |
| 无 `.aw/` 且无 `.servo/` | no-op；不创建任何内容 |
| 只有 `.aw/` | ready；`--yes` 可复制 runtime state |
| 只有 `.servo/` | no-op；已经在 `.servo/` 上 |
| `.aw/` 与 `.servo/` 同时存在且无 migration sentinel | blocked；不合并、不覆盖 |
| `.aw/` 是文件、symlink、不可读或 malformed | blocked |
| `.servo/` 是文件、symlink、不可读或 malformed | blocked |
| 已存在 previous migration sentinel | idempotent no-op |

## 恢复

如果命令阻断：

- 保留 `.aw/`
- 检查报告中的 path 和 issue code
- 只有在决定哪个 runtime state 应获胜后，才 relocate 或 repair existing `.servo/`
- 应用 mutation 前重新运行 dry-run
- 遇到 reinstall / update 问题后，运行 backend-specific `diagnose` 和 `verify`

不要把删除 `.aw/` 当作默认 cleanup step。

## Smoke 证据

installer test suite 使用 `/tmp` target repositories 验证升级路径，而不是使用本源码仓库。当前覆盖的用例：

- 无 `.aw/` 且无 `.servo/`
- `.aw/` only dry-run
- `.aw/` only `--yes`
- path reference rewriting（`.aw/` -> `.servo/`，branch names 保持不变）
- successful rerun idempotence
- `.aw/` 与 `.servo/` 同时存在
- malformed `.aw` path
- `.servo/` only
- Windows / non-ASCII target path copy
- agents `--reinstall` marker refresh 和 payload fingerprint convergence
- update conflict 在 runtime copy 前阻断
- bundle `--reinstall` 安装两个 backend payloads

当前 deploy regression file 定义 148 个 subtests；closeout evidence 应记录用于 release 或 handoff 的那次 verification run 的准确 passing count。
