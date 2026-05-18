---
title: "Claude Repo-local Usage Help"
status: active
updated: 2026-05-08
owner: aw-kernel
last_verified: 2026-05-08
---
# Claude Repo-local Usage Help

> 目的：保留 `claude` backend 的 runtime 侧差异（skill root、smoke verify、支持边界）。**新用户先读 [quickstart.md](./quickstart.md) 10 分钟快速入门**，再读本页了解 Claude backend 细节。

## 一、快速试用路径

`claude` 是 Claude Code compatibility lane。`aw-installer --backend claude` 承接完整 Harness skill lifecycle。

受管路径：

```bash
AW_HARNESS_TARGET_REPO_ROOT="$TARGET_REPO" aw-installer install --backend claude
AW_HARNESS_TARGET_REPO_ROOT="$TARGET_REPO" aw-installer verify --backend claude
```

Claude backend 的 deploy 入口为 `aw-installer --backend claude`（Node-only distribution）。冷启动 helper：`node product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.js install-claude-skill --deploy-path "$TARGET_REPO"`。Coding CLI 内部的 skill 调用示例以 [Skills 使用教程](./recommended-usage.md) 为准。

## 二、Backend 标识与常见路径

- backend 名：`claude`
- repo-local runtime root：`.claude/skills/`；user-home runtime root：`~/.claude/skills`

`claude` backend 准入完整 Harness skill set，target dirs 使用 `.claude/skills/<skill-name>/`；完整步骤见 [Claude Post-Deploy Behavior Tests](../testing/claude-post-deploy-behavior-tests.md)。

## 三、最小 trial smoke verify

显式调用 `.claude/skills/` 下的一个 skill entry 做最小读取确认，输出结构符合固定契约。这是 backend runtime 可读性确认，不替代 source/target 对齐检查。

## 四、和其他 backend 的区别

`claude` 承担完整 Harness skill payload 与 runtime skill entry 可读性 smoke；`agents` 是 deploy verify 与 Codex manual run 主路径。`claude` user-home runtime 为 `~/.claude/skills`，不依赖 `CODEX_HOME`。反馈标明 compatibility trial lane。

## 五、限制

`claude` 是 compatibility lane；package/local lifecycle 由 Node-owned `aw-installer --backend claude` 承接。本页只承接 Claude runtime 路径与兼容 payload 差异。

## 六、受控例外

`set-harness-goal-skill` 的 `scripts/deploy_aw.js` 可安装自身到 Claude 项目级 skill 目录：

```bash
node scripts/deploy_aw.js install-claude-skill --deploy-path "$DEPLOY_PATH"
node scripts/deploy_aw.js generate --deploy-path "$DEPLOY_PATH" --install-claude-skill
```

目标 `<deploy-path>/.claude/skills/aw-set-harness-goal-skill/`，默认不覆盖（需 `--force`）；`--claude-root` 仅限受控 trial 环境；目标目录不能是 symlink。

## 七、Source 变更后的 operator 决策

与 `agents` 一致：source of truth 在 `product/`，不改 `.claude/skills/` 已安装结果；重新对齐 source 回 [Deploy Runbook](../deploy/deploy-runbook.md) 走三步流程；source 命名/cleanup/contract 变化先修 source 再重装。
