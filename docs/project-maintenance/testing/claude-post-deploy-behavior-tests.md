---
title: "Claude Post-Deploy Behavior Tests"
status: active
updated: 2026-05-05
owner: servo-kernel
last_verified: 2026-05-05
---
# Claude Post-Deploy Behavior Tests

> 目的：固定 Claude Code 部署后 Harness 行为观察的最小手动 runbook：临时 repo、隔离 `.claude/skills/`、无交互 `claude --bare -p`、多轮观察。

本页属于 [Testing Runbooks](./README.md)。通用 deploy 主流程见 [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)，Claude 使用入口见 [Claude Repo-local Usage Help](../usage-help/claude.md)。

## 一、适用范围

覆盖：初始化临时 repo、安装隔离 Claude skill payload、启动无交互 Claude Code 轮次、用 Codex 监督执行链路。不承接 Harness doctrine、skill 单测、automated acceptance、评分或 Claude 产品定位。

## 二、固定题目

与 Codex runbook 一致：

```text
Build a CLI Slay the Spire-lite in this temporary repo.
Reach a full core system with combat, cards, deck, map, and events.
```

验收约束：纯终端交互；子系统 combat/battle log/cards/deck/map/events；每子系统独立 worktrack，完成后 handback；提供运行入口、`README.md`、AI 游戏说明；每子系统完成后验证。

## 三、初始化临时 repo

```bash
TMP_PARENT="${TMP_PARENT:-$HOME/tmp}"
mkdir -p "$TMP_PARENT"
TMP_ROOT="$(mktemp -d "$TMP_PARENT/harness-claude-spire-lite.XXXXXX")"
TMP_REPO="$TMP_ROOT/repo"
TMP_CLAUDE_ROOT="$TMP_REPO/.claude/skills"
TMP_RUN_ROOT="$TMP_ROOT/run-artifacts"
CLAUDE_TEST_HOME="$TMP_ROOT/claude-home"
NPM_CONFIG_CACHE="$TMP_ROOT/npm-cache"

mkdir -p "$TMP_REPO" "$TMP_RUN_ROOT"
git init "$TMP_REPO"
git -C "$TMP_REPO" branch -m main
printf '.claude/\n' >> "$TMP_REPO/.git/info/exclude"
printf 'TMP_ROOT=%s\n' "$TMP_ROOT"
```

默认临时根 `$HOME/tmp`；`.claude/` 用 `.git/info/exclude` 排除；不预置 `.aw/`，不创建初始提交；`NPM_CONFIG_CACHE` 指向本轮临时目录。宿主 `$HOME/.claude` 不可写时用临时 Claude home，只复制登录状态；外发日志前确认不泄露认证文件。

## 四、安装隔离 Claude payload

验证本地 candidate 时优先用 `.tgz`：

```bash
PACKAGE_TGZ="/path/to/servo-installer-<version>.tgz"
(
  cd "$TMP_REPO"
  AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" \
    npx --yes --package "$PACKAGE_TGZ" -- servo-installer install --backend claude
  AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" \
    npx --yes --package "$PACKAGE_TGZ" -- servo-installer verify --backend claude
)
```

`claude` install 包含全部 20 个 skills（含 Milestone 观测器）；cold-start helper 以 `scripts/deploy_aw.js` 随 payload 分发。

## 五、选择观察策略

`OBSERVATION_PROFILE=strict-handback`（停在 handback boundary）或 `continuous-autonomy`（handback 后继续消费预算）；两种不混用。

## 六、round-000

```bash
mkdir -p "$TMP_RUN_ROOT/round-000"
```

写入 `init.prompt.md`：

```text
Use only `harness-skill` as the top-level control entry.
This is a cold-start scenario: the repo is empty and `.aw/` does not exist.
User requirement: Build a CLI Slay the Spire-lite. Reach full core system with combat, cards, deck, map, and events.
Working rules: non-interactive test, each subsystem separate Worktrack, complete only first bounded slice unless continuous autonomy, use real files/tests.
If `.aw/` is missing, `harness-skill` should route to `set-harness-goal-skill`.
```

```bash
HOME="$CLAUDE_TEST_HOME" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" claude --bare -p "$(cat "$TMP_RUN_ROOT/round-000/init.prompt.md")" --cwd "$TMP_REPO" 2>&1 | tee "$TMP_RUN_ROOT/round-000/session.log"
```

保留：`session.log`、Claude 最终输出、`.aw/`、`git status --short`、`git diff --stat`。

## 七、后续轮次

```bash
mkdir -p "$TMP_RUN_ROOT/round-001"
cat > "$TMP_RUN_ROOT/round-001/continue.prompt.md" <<'EOF'
Continue via `harness-skill`.
Respect the current `.aw/control-state.md`, Worktrack artifacts, handback guard, and autonomy budget.
Do not unlock handback unless the control state already grants continuous autonomy.
EOF

HOME="$CLAUDE_TEST_HOME" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" claude --bare -p "$(cat "$TMP_RUN_ROOT/round-001/continue.prompt.md")" --cwd "$TMP_REPO" 2>&1 | tee "$TMP_RUN_ROOT/round-001/session.log"
```

`round-0xx` 递增目录名；仅在诊断恢复行为时写长 prompt。

## 八、监督方式

读取每轮完整产物：`session.log`、Claude 最终输出、`.aw/control-state.md`、`.aw/repo/*`、`.aw/worktrack/*`、`git status --short`、`git diff --stat`、源码与测试结果。

观察点：是否从 `.aw/` 缺失进入 `set-harness-goal-skill`、建立 goal/snapshot/control state、进入 `RepoScope -> WorktrackScope`、只打开 bounded subsystem worktrack、使用 `dispatch-skills`、产生 review/test/rule-check/gate evidence、策略表现一致。

## 九、继续与停止

继续条件：未 hit stop condition、control state 允许、有未完成 subsystem、证据充分。

停止条件：命中 handback boundary、gate fail/blocked、scope 切换已达目的、dispatch gap 需人工判断、Claude Bash tool 因 `$HOME/.claude/session-env` 只读失败（应切 `CLAUDE_TEST_HOME` 重跑，不归因 payload）。

## 十、相关文档

- [Testing Runbooks](./README.md)
- [Codex Post-Deploy Behavior Tests](./codex-post-deploy-behavior-tests.md)
- [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)
- [Claude Repo-local Usage Help](../usage-help/claude.md)
- [Harness 运行协议](../../harness/foundations/Harness运行协议.md)
