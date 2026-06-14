---
title: "Skill Deployment 维护流"
status: active
updated: 2026-06-14
owner: servo-kernel
last_verified: 2026-06-14
---
# Skill Deployment 维护流

> 目的：提供 deploy target 的只读诊断与恢复分流入口，管理"先观察什么、怎么判断、何时转回三步重装"。

首次安装/重装见 [Deploy Runbook](./deploy-runbook.md)；合同见 [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)。

## 推荐维护循环

`diagnose --json` -> `verify` -> 如需恢复则回 deploy runbook 三步重装 -> 重装后再跑 `diagnose`/`verify`。

## Source maintenance checklist

当维护者新增、重命名或改变 canonical skill、adapter payload、`.servo` template、Harness artifact contract 或 operator-facing installer 行为时，必须在同一 Worktrack 内检查以下同步面；不能完成时要在 closeout evidence 中写明不适用理由。

| 变更面 | 必查同步 |
| --- | --- |
| canonical skill source | 更新 `product/harness/skills/README.md` 的 source index 和 docs traceability；确认 skill 包内不依赖 package-external runtime-only docs；若 skill 名称容易被误用，使用带控制域前缀的 canonical name |
| adapter payload | 同步 `product/harness/adapters/agents/skills/*/payload.json` 与 `product/harness/adapters/claude/skills/*/payload.json` 的 `skill_id`、`canonical_paths`、`required_payload_files`、`target_dir` 和 `legacy_*` 字段；重命名时旧名只能保留为 legacy alias，不再作为推荐入口 |
| `.servo` template / deploy helper | 同步 `product/.servo_template/`、`product/harness/skills/set-harness-goal-skill/assets/`、`deploy_servo.js` 相关生成/迁移路径，并补 dry-run/apply/idempotency 证据 |
| Harness artifact contract | 同步 `docs/harness/artifact/` canonical contract、skill template、`.servo_template` template 和对应 governance semantic check |
| operator-facing installer behavior | 同步 `docs/servo-installer/contracts/`、`docs/servo-installer/runbooks/`、`toolchain/scripts/deploy/README.md` 和 CLI/TUI/package smoke 命令说明 |
| package and release program | 同步 npm pack/publish dry-run、tarball/npx-style smoke、release-channel no-publish boundary，以及必要的 closeout evidence |

最小本地检查：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
npm test --prefix toolchain/scripts/deploy
```

这个 checklist 是 source-side 维护入口；operator 只需要下方 diagnose/verify 分流。

## 只读命令角色

| 命令 | 职责 | 退出语义 |
| --- | --- | --- |
| `diagnose --json` | 输出 backend、target root、issue code、conflict/unrecognized 摘要 | 发现 issue 时仍可 `0` 退出 |
| `verify` | 严格复验 source 合法性、target root、live install 对齐、conflict/unrecognized/drift | 发现 issue 时非零退出 |

```bash
servo-installer diagnose --backend agents --json
servo-installer verify --backend agents
```

repo-local Python reference/parity commands remain available for adapter maintenance and comparison tests, but they are not the package/local operator runtime path.

backend-specific target root override 见 [Codex Usage Help](../../project-maintenance/usage-help/codex.md) 和 [Claude Usage Help](../../project-maintenance/usage-help/claude.md)。

## 信号分流

| 信号或症状 | 优先处理方式 |
| --- | --- |
| `missing-target-root` | 直接回 deploy runbook 三步重装 |
| `wrong-target-root-type` | 先修正 target root 形态，再三步重装 |
| `broken-target-root-symlink` | 删除坏链路后三步重装 |
| `duplicate target_dir` | 先修 source，不在 target 侧硬修 |
| `payload-contract-invalid`/`missing-canonical-source`/`missing-backend-payload-source` | 回 source 层修合同或缺件，再三步重装 |
| `check_paths_exist` 冲突清单 | 先手工清理占位目录，再三步重装 |
| `unrecognized-target-directory` | 不让脚本猜测；人工确认保留、改名或删除 |
| `target-payload-drift`/`missing-target-entry`/`missing-required-payload` | 默认完整重装，除非确认是更上游 source 问题 |
| legacy `.aw/` runtime state exists | 不走 `prune --all`；先看 [Legacy `.aw` Runtime Upgrade Runbook](./aw-runtime-upgrade-runbook.md) |
| `.servo/` runtime 缺少新模板 section/file | 先运行 `servo-installer reconcile-servo --json` 预览；确认后运行 `servo-installer reconcile-servo --yes`，再跑第二次 `--json` 验证 `changes` 为空 |

已决定重装 -> [Deploy Runbook](./deploy-runbook.md)；字段/trust boundary -> [Mapping Spec](../contracts/deploy-mapping-spec.md) + [Payload Provenance](../contracts/payload-provenance-trust-boundary.md)；smoke/release -> [Testing](../../project-maintenance/testing/README.md) + [Governance](../../project-maintenance/governance/README.md)。

## Legacy `.aw/` runtime state

`.aw/` is legacy Harness runtime state, not installer-managed skill payload. `diagnose`, `verify`, `prune --all`, `install`, and ordinary `update` must not silently migrate or delete it. If a target repository still has `.aw/`, use [Legacy `.aw` Runtime Upgrade Runbook](./aw-runtime-upgrade-runbook.md) before planning any mutating action. The normative boundary remains [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md).
