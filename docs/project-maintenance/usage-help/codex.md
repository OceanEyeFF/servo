---
title: "Codex Usage Help"
status: active
updated: 2026-05-07
owner: servo-kernel
last_verified: 2026-05-07
---
# Codex Usage Help

> 目的：保留 `agents` backend 的 target root 解析、参数传递、三步主流程与 Harness manual run 入口。先读通用 deploy 文档，再读本页。

## 一、快速试用路径

**新用户先读 [quickstart.md](./quickstart.md) 10 分钟快速入门**，再回到本页了解 `agents` backend 细节。

public/stable 主路径是 `agents`，推荐 `servo-installer` selector：

```bash
AW_INSTALLER_PACKAGE="servo-installer"
AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npx --yes --package "$AW_INSTALLER_PACKAGE" -- servo-installer diagnose --backend agents --json
AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npx --yes --package "$AW_INSTALLER_PACKAGE" -- servo-installer update --backend agents --yes
AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npx --yes --package "$AW_INSTALLER_PACKAGE" -- servo-installer verify --backend agents
```

然后在目标仓库用 Codex `set-harness-goal-skill` 初始化 `.aw/`。

## 二、Backend 标识与 target root

backend 名 `agents`，默认 target root `.agents/skills/`，覆盖参数 `--agents-root`（只指向受控 `.agents/skills` 或临时技能目录）。外部试用从目标仓库根目录清空环境变量运行；有工作内容的仓库先 `diagnose`/dry-run 再 `update --yes`。

## 三、Deploy verify 与 Harness 观察

`agents` 的最小 deploy 验证是 destructive reinstall 加只读 `verify`，证明 payload source、target root 与 live install 对齐。

Node-owned package/local 路径：

```bash
servo-installer diagnose --backend agents --json
servo-installer update --backend agents --json
servo-installer update --backend agents --yes
servo-installer verify --backend agents
```

`update --yes` 按 `prune --all -> check_paths_exist -> install -> verify` 执行。`diagnose --json` 和 `update --json` 是只读路径；已有内容的 target 先看这两步再 `update --yes`。

需观察真实 Harness 行为时使用 [Codex Post-Deploy Behavior Tests](../testing/codex-post-deploy-behavior-tests.md)，在临时 repo 隔离 `.agents/skills/`，用无交互 `codex exec` 调用 `harness-skill`。

判断边界：
- `servo-installer verify --backend agents` 是 deploy target 对齐证明
- `codex-post-deploy-behavior-tests.md` 是 operator-facing 的 Harness runtime 观察入口
- skills mock/contract smoke 不作主线验证入口

## 四、和其他 backend 的区别

- `agents` 默认使用 repo-local `.agents/skills/`
- 如需改 root 显式传 `--agents-root`
- 和其他 backend 共享同一套 destructive reinstall 模型
- backend 名仍是 `agents`

## 五、命令差异

主要差异在 target root 参数：

```bash
servo-installer diagnose --backend agents --json --agents-root "$PWD/.agents/skills"
servo-installer update --backend agents --json --agents-root "$PWD/.agents/skills"
servo-installer update --backend agents --yes --agents-root "$PWD/.agents/skills"
servo-installer verify --backend agents --agents-root "$PWD/.agents/skills"
```

`update --backend agents --yes` 即 destructive reinstall 主流程；部署到默认 repo-local target 时可省略 `--agents-root`；不把 `--agents-root` 指向敏感目录。外部试用反馈使用 [trial feedback issue template](../../../.github/ISSUE_TEMPLATE/servo-installer-trial-feedback.yml) 或 [bug/blocker issue template](../../../.github/ISSUE_TEMPLATE/servo-installer-bug.yml)。本地 `diagnose`/`update`/`check_paths_exist`/`verify`/`install`/`prune` 为 Node-owned 路径；selected GitHub-source update 与 selected Claude package/local lifecycle 也由 Node-owned `servo-installer` 路径承接。unsupported variants 在 Node 层失败，不 fallback 到 Python；Python deploy scripts 仅作 repo-local reference/parity/governance tooling。

## 六、Source 变更后的 operator 决策

- source of truth 在 `product/`，不改 `.agents/skills/` 已安装结果
- 重新对齐 source 回 [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md) 走三步主流程
- source 出现重复 `target_dir`、改名、移除或 target naming 变化时先修 source contract 再重装
