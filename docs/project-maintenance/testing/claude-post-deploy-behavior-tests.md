---
title: "Claude Post-Deploy Behavior Tests"
status: active
updated: 2026-06-02
owner: servo-kernel
last_verified: 2026-06-02
---
# Claude Post-Deploy Behavior Tests

> 目的：固定用于观察 Claude Code 部署后 Harness 行为的最小手动操作手册：临时 repo、隔离 `.claude/skills/`、无交互 `claude --bare -p`、多轮观察。

本页属于 [Testing Runbooks](./README.md)。通用 deploy 主流程见 [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)，Claude 使用入口见 [Claude Repo-local Usage Help](../usage-help/claude.md)。

## 一、适用范围

覆盖：初始化临时 repo、安装隔离 Claude skill payload、启动无交互 Claude Code 轮次、用 Codex 监督执行链路。不承接 Harness doctrine、skill 单测、automated acceptance、评分或 Claude 产品定位。

## 二、2026-06-02 CLI 基线

当前已验证 Claude Code `2.1.119`：

- `claude --help` 未提供旧版 runbook 曾使用的 `--cwd`；测试命令必须从目标 repo 当前工作目录执行，或使用当前 CLI 支持的显式上下文参数。
- `--bare` 不读取 OAuth/keychain，认证只能来自 `ANTHROPIC_API_KEY` 或 `--settings` 中的 `apiKeyHelper` 等显式配置。不要把复制认证文件当作 `--bare` 的可靠认证方式。
- `--tools ""` 可以验证真实模型 backend，但不会验证 `/skill-name` skill invocation。
- 要验证 `/harness-skill` 这类 skill invocation，同时禁止文件读取和执行动作，使用 `--tools default` 并通过 `--disallowedTools` 禁用 `Read,Grep,Glob,LS,Bash,Edit,Write,MultiEdit,NotebookEdit`。
- `servo-installer` target repo root 受 path safety 约束；临时 target 默认放在 `$HOME/tmp`。直接使用 `/tmp` 作为 target repo root 可能被拒绝。

最小真实 backend smoke：

```bash
claude --bare --no-session-persistence --max-budget-usd 0.03 \
  --tools "" --permission-mode dontAsk --output-format json \
  -p 'This is a tiny backend smoke test. Return exactly: CLAUDE_REAL_BACKEND_OK'
```

最小 skill invocation smoke：

```bash
(
  cd "$TMP_REPO"
  claude --bare --no-session-persistence --max-budget-usd 0.08 \
    --tools default \
    --disallowedTools "Read,Grep,Glob,LS,Bash,Edit,Write,MultiEdit,NotebookEdit" \
    --permission-mode dontAsk --output-format json \
    -p '/harness-skill

Skill resolution probe. Do not call tools. Return compact JSON only with keys skill_invoked, harness_role, not_direct_executor.'
)
```

## 三、固定题目

与 Codex runbook 一致：

```text
Build a CLI Slay the Spire-lite in this temporary repo.
Reach a full core system with combat, cards, deck, map, and events.
```

验收约束：纯终端交互；子系统 combat/battle log/cards/deck/map/events；每子系统独立 worktrack，完成后 handback；提供运行入口、`README.md`、AI 游戏说明；每子系统完成后验证。

## 四、初始化临时 repo

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

默认临时根 `$HOME/tmp`；`.claude/` 用 `.git/info/exclude` 排除；不预置 `.servo/`，不创建初始提交；`NPM_CONFIG_CACHE` 指向本轮临时目录。`--bare` 认证必须来自显式 API key / settings helper；对外分享日志前，确认不包含认证凭据、私有路径或仓库内容。

## 五、安装隔离 Claude payload

验证本地 candidate 时优先用 `.tgz`：

```bash
PACKAGE_TGZ="/path/to/servo-installer-<version>.tgz"
(
  cd "$TMP_REPO"
  SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" \
    npx --yes --package "$PACKAGE_TGZ" -- servo-installer install --backend claude
  SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" \
    npx --yes --package "$PACKAGE_TGZ" -- servo-installer verify --backend claude
)
```

`claude` install 包含全部 22 个 skills（含 Milestone 观测器与 pre-milestone intake）；cold-start helper 以 `scripts/deploy_servo.js` 随 payload 分发。

## 六、选择观察策略

`OBSERVATION_PROFILE=strict-handback`（停在 handback boundary）或 `continuous-autonomy`（handback 后继续消费预算）；两种不混用。

## 七、round-000

```bash
mkdir -p "$TMP_RUN_ROOT/round-000"
```

写入 `init.prompt.md`：

```text
Use only `harness-skill` as the top-level control entry.
This is a cold-start scenario: the repo is empty and `.servo/` does not exist.
User requirement: Build a CLI Slay the Spire-lite. Reach full core system with combat, cards, deck, map, and events.
Working rules: non-interactive test, each subsystem separate Worktrack, complete only first bounded slice unless continuous autonomy, use real files/tests.
If `.servo/` is missing, `harness-skill` should route to `set-harness-goal-skill`.
```

```bash
(
  cd "$TMP_REPO"
  NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" claude --bare --no-session-persistence \
    --max-budget-usd "${CLAUDE_MAX_BUDGET_USD:-0.25}" \
    --tools default \
    --permission-mode dontAsk \
    -p "$(cat "$TMP_RUN_ROOT/round-000/init.prompt.md")" \
    2>&1 | tee "$TMP_RUN_ROOT/round-000/session.log"
)
```

保留：`session.log`、Claude 最终输出、`.servo/`、`git status --short`、`git diff --stat`。

## 八、后续轮次

```bash
mkdir -p "$TMP_RUN_ROOT/round-001"
cat > "$TMP_RUN_ROOT/round-001/continue.prompt.md" <<'EOF'
Continue via `harness-skill`.
Respect the current `.servo/control-state.md`, Worktrack artifacts, handback guard, and autonomy budget.
Do not unlock handback unless the control state already grants continuous autonomy.
EOF

(
  cd "$TMP_REPO"
  NPM_CONFIG_CACHE="$NPM_CONFIG_CACHE" claude --bare --no-session-persistence \
    --max-budget-usd "${CLAUDE_MAX_BUDGET_USD:-0.25}" \
    --tools default \
    --permission-mode dontAsk \
    -p "$(cat "$TMP_RUN_ROOT/round-001/continue.prompt.md")" \
    2>&1 | tee "$TMP_RUN_ROOT/round-001/session.log"
)
```

`round-0xx` 递增目录名；仅在诊断恢复行为时写长 prompt。

## 九、复杂门禁自测场景

当目标是观察复杂项目门禁行为，而不是让 Claude 修改 repo：

1. 先用 `complexity_signal_scanner.py --repo "$TARGET_REPO" --json` 生成 evidence。
2. 在 prompt 中明确区分：
   - `fixed_heavy_mode`：所有 repo 或所有复杂-looking repo 都默认进入永久 heavy workflow。
   - `risk_triggered_gate`：仅当前 repo/scenario 因 observed evidence 加上安全/理解缺口而阻断实现派生。
3. 用 `--tools default` 保留 `/harness-skill` 解析；用 `--disallowedTools` 禁止文件读取、Bash 和写入工具。
4. 要求 Claude 基于已给 scanner evidence 输出结构化 verdict，不要调用工具。

2026-06-02 real dogfood 观察（证据摘要）：

- Evidence refs: `.servo/worktrack/gate-evidence.md` and `.servo/worktrack/closeout-record.md` for `WT-20260602-claude-real-dogfood-gate-validation`; formal docs commit `d8a47ff6ea9b8ee67a462fe25c4a658221685592`.
- Claude Code version: `2.1.119`.
- Backend smoke: `claude --bare --no-session-persistence --max-budget-usd 0.03 --tools "" --permission-mode dontAsk --output-format json -p ...` returned `CLAUDE_REAL_BACKEND_OK`, cost `$0.00275`, with no permission denials.
- Skill invocation: `/harness-skill` invocation required `--tools default` with file/execution tools disallowed; `--tools ""`, `--tools Skill`, and `--tools SlashCommand` were not sufficient for this probe.
- Target fixtures: copied real repos under `$HOME/tmp/servo-claude-real-dogfood.U90uyS/targets/`, not source repos; `NeteaseCloudMusicFlac` represented low-risk evidence and `MuMuAINovel` represented complex-signal evidence.
- Safety boundary: no source repo mutation, service start, docker/database/migration/deploy/network execution, destructive cleanup, release/package mutation, push, or final Milestone acceptance; complex repo `.env` / `.env.example` inputs were redacted before file-tool attempts.
- 低风险 repo evidence-only run 正确输出 `fixed_heavy_mode=false`、`risk_triggered_gate=false`、`scanner_evidence_is_final_verdict=false`。
- 复杂 repo 首轮 evidence-only run 正确要求 blocking gate / safety policy / reinforcement route，但误把 `fixed_heavy_mode` 标为 true。
- 加入上述定义复核后，复杂 repo 输出 `fixed_heavy_mode=false`、`risk_triggered_gate=true`、`scanner_evidence_is_final_verdict=false`、`operator_safety_policy_required=true`、`reinforcement_milestone_recommendation=true`。
- Residual risk: full file-tool complex repo dogfood exceeded the small budget cap and was not accepted as verdict evidence; evidence-only prompts were more controlled for gate semantics.

结论：真实 Claude 行为测试必须显式定义 `fixed_heavy_mode` 和 `risk_triggered_gate`；否则术语可能被误判。

## 十、监督方式

读取每轮完整产物：`session.log`、Claude 最终输出、`.servo/control-state.md`、`.servo/repo/*`、`.servo/worktrack/*`、`git status --short`、`git diff --stat`、源码与测试结果。

观察点：是否从 `.servo/` 缺失进入 `set-harness-goal-skill`、建立 goal/snapshot/control state、进入 `RepoScope -> WorktrackScope`、只打开 bounded subsystem worktrack、使用 `dispatch-skills`、产生 review/test/rule-check/gate evidence、策略表现一致。

## 十一、继续与停止

继续条件：未 hit stop condition、control state 允许、有未完成 subsystem、证据充分。

停止条件：命中 handback boundary、gate fail/blocked、scope 切换已达目的、dispatch gap 需人工判断、Claude Bash tool 因 `$HOME/.claude/session-env` 只读失败（应切 `CLAUDE_TEST_HOME` 重跑，不归因 payload）。

## 十二、相关文档

- [Testing Runbooks](./README.md)
- [Codex Post-Deploy Behavior Tests](./codex-post-deploy-behavior-tests.md)
- [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)
- [Claude Repo-local Usage Help](../usage-help/claude.md)
- [Harness 运行协议](../../harness/foundations/Harness运行协议.md)
