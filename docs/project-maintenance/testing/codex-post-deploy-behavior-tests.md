---
title: "Codex Post-Deploy Behavior Tests"
status: active
updated: 2026-05-10
owner: servo-kernel
last_verified: 2026-05-10
---
# Codex Post-Deploy Behavior Tests

> 目的：固定 Codex 部署后 Harness 行为观察的最小手动 runbook：临时 repo、隔离 `.agents/skills/`、无交互 `codex exec`、多轮观察。

本页属于 [Testing Runbooks](./README.md)。通用 deploy 主流程见 [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)。

## 一、适用范围

覆盖：初始化临时 repo、安装隔离 agents payload、启动无交互 Codex 轮次、监督执行链路。不承接 Harness doctrine、skill 单测、自动化 acceptance matrix 或评分。

## 二、固定题目

```text
Build a CLI Slay the Spire-lite in this temporary repo.
Reach a full core system with combat, cards, deck, map, and events.
```

验收约束：纯终端交互；子系统 combat/battle log/cards/deck/map/events；每子系统独立 worktrack，完成后 handback；提供运行入口与 `README.md`；repo 内提供 AI 游戏说明；每子系统完成后验证。测试 Harness 冷启动与多轮推进，非单个 skill。

## 三、初始化临时 repo

```bash
TMP_ROOT="$(mktemp -d /tmp/harness-spire-lite.XXXXXX)"
TMP_REPO="$TMP_ROOT/repo"
TMP_AGENTS_ROOT="$TMP_REPO/.agents/skills"
TMP_RUN_ROOT="$TMP_ROOT/run-artifacts"

mkdir -p "$TMP_REPO" "$TMP_RUN_ROOT"
git init "$TMP_REPO"
git -C "$TMP_REPO" branch -m main
printf 'TMP_ROOT=%s\n' "$TMP_ROOT"
```

固定条件：每次新临时目录，不预置 `.aw/`，不创建初始提交，`main` 为 baseline。

## 四、安装隔离 agents payload

```bash
node toolchain/scripts/deploy/bin/servo-installer.js prune --all --backend agents --agents-root "$TMP_AGENTS_ROOT"
node toolchain/scripts/deploy/bin/servo-installer.js check_paths_exist --backend agents --agents-root "$TMP_AGENTS_ROOT"
node toolchain/scripts/deploy/bin/servo-installer.js install --backend agents --agents-root "$TMP_AGENTS_ROOT"
node toolchain/scripts/deploy/bin/servo-installer.js verify --backend agents --agents-root "$TMP_AGENTS_ROOT"
```

当前 `agents` install 已包含全部 21 个 skills（RepoScope/WorktrackScope/验证/裁决/恢复/收尾/通用执行/Milestone）；`set-harness-goal-skill` 自带 `.aw/` 初始化资产。

## 五、选择观察策略

`OBSERVATION_PROFILE=strict-handback`（worktrack 完成后停在 handback boundary）或 `continuous-autonomy`（handback 后继续消费预算）；两种不混用。

## 六、round-000

```bash
mkdir -p "$TMP_RUN_ROOT/round-000"
```

写入 `init.prompt.md`：

```text
You are running inside a temporary repo used for Harness manual observation.
Use only `harness-skill` as the top-level control entry.
This is a cold-start scenario: the repo is empty and `.aw/` does not exist.
User requirement: Build a CLI Slay the Spire-lite in this temporary repo. Reach a full core system with combat, cards, deck, map, and events.
Working rules: non-interactive test, each subsystem separate Worktrack, complete only first bounded slice unless continuous autonomy, use real files/tests.
If `.aw/` is missing, `harness-skill` should route to `set-harness-goal-skill`.
```

```bash
codex exec --cd "$TMP_REPO" --skip-git-repo-check --output-last-message "$TMP_RUN_ROOT/round-000/final.txt" < "$TMP_RUN_ROOT/round-000/init.prompt.md" 2>&1 | tee "$TMP_RUN_ROOT/round-000/session.log"
```

保留：`session.log`、`final.txt`、`.aw/`、`git status --short`、`git diff --stat`。

## 七、后续轮次

```bash
mkdir -p "$TMP_RUN_ROOT/round-001"
cat > "$TMP_RUN_ROOT/round-001/continue.prompt.md" <<'EOF'
Continue via `harness-skill`.
Respect the current `.aw/control-state.md`, Worktrack artifacts, handback guard, and autonomy budget.
Do not unlock handback unless the control state already grants continuous autonomy.
EOF

codex exec --cd "$TMP_REPO" --skip-git-repo-check --output-last-message "$TMP_RUN_ROOT/round-001/final.txt" < "$TMP_RUN_ROOT/round-001/continue.prompt.md" 2>&1 | tee "$TMP_RUN_ROOT/round-001/session.log"
```

`round-0xx` 递增目录名；仅在诊断恢复行为时写长 prompt。

## 八、监督方式

读取每轮完整产物：`session.log`、`final.txt`、`.aw/control-state.md`、`.aw/repo/*`、`.aw/worktrack/*`、`git status --short`、`git diff --stat`、相关源码与测试结果。

观察点：是否从 `.aw/` 缺失进入 `set-harness-goal-skill`、建立 goal/snapshot/control state、进入 `RepoScope -> WorktrackScope`、只打开 bounded subsystem worktrack、使用 `dispatch-skills`、产生 review/test/rule-check/gate evidence、在 handback/continuous-autonomy 下表现一致。

## 九、继续与停止

继续条件：未 hit stop condition、control state 允许、有未完成 subsystem、证据充分。

停止条件：命中 handback boundary、gate fail/blocked、scope 切换已达目的、runtime dispatch gap 需人工判断、日志显示 Codex runtime 或环境问题而非 payload 问题。

## 十、相关文档

- [Testing Runbooks](./README.md)
- [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)
- [Skill Deployment 维护流](../../servo-installer/runbooks/skill-deployment-maintenance.md)
- [Harness 运行协议](../../harness/foundations/Harness运行协议.md)
