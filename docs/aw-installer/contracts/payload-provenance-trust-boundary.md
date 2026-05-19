---
title: "aw-installer Payload Provenance And Update Trust Boundary"
status: active
updated: 2026-05-06
owner: aw-kernel
last_verified: 2026-05-06
---
# aw-installer Payload Provenance And Update Trust Boundary

> 目的：明确 `aw-installer` 的 payload 来源、命令写入目标、可信 source override 与当前已准入的远程更新能力。

本页管理 source kind、source/target root 分离与 `update` 远程输入。wrapper 语义、payload 字段、release channel 见相邻文档。

## 当前允许的 payload 来源

只允许 package-local、checkout-local 与显式 `--source github`。不包含 registry/dist-tag 自动解析 remote payload、任意 HTTP URL、target root 反向生成 source truth、隐式 self-update/自动回滚/增量 patch。`.aw/`、`.agents/`、`.claude/`、`.autoworkflow/` 都不是 package payload。

## Source Root 与 Target Root

- 未设 `AW_HARNESS_REPO_ROOT` 时 source root 来自 package 解压根或当前 checkout；设置时显式指向该 checkout
- 未设 `AW_HARNESS_TARGET_REPO_ROOT` 时 target repo root 默认为当前工作目录；设置时显式指向该目录
- `--agents-root`/`--claude-root` 只覆盖对应 backend 的 target root，不改 source root

必须保持：source/target root 分离；target root 不是 source of truth；package/`.tgz` smoke 须证明 package payload 与临时 target repo 分离。

## 命令写入边界

| 命令 | 写入边界 |
| --- | --- |
| `diagnose`/`verify`/`check_paths_exist`/`update --json` | 只读，不写入 |
| `install` | 只写 resolved target root 下的当前 source live payload |
| `update --yes` | 只执行显式 destructive reinstall |
| `prune --all` | 只删除当前 backend 可识别受管目录 |

`aw.marker` 只证明"这是当前 backend 的受管 live install 目录"，非 source truth 或远程 provenance 证明。

## GitHub Source 准入

```bash
aw-installer update --backend agents --source github --github-repo OWNER/REPO --github-ref REF --json
aw-installer update --backend agents --source github --github-repo OWNER/REPO --github-ref REF --yes
```

只支持 `OWNER/REPO + ref`，不支持任意 URL；archive 必须包含当前 required Harness payload source；GitHub source root 只在本次命令生效，不变成长期 source truth；target root 仍来自当前工作目录、环境变量或 backend root override；dry-run 必须暴露 `source_kind=github` 与 `source_ref`；`--yes` 只执行同一条 destructive reinstall 链路；selected ref 缺少 required payload source 时命令必须失败，不回退 package-local source。

## 不承接的能力

当前 `aw-installer` 不实现 channel-based remote update、registry 或 GitHub Release 自动选包、signature provenance chain、自动回滚、target-to-source 反向同步。未来加入须先补独立合同与验证证据。
