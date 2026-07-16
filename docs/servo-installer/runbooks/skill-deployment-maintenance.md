---
title: "Skill Deployment 维护流"
status: active
updated: 2026-06-22
owner: servo-kernel
last_verified: 2026-06-22
---
# Skill Deployment 维护流

> 目的：提供 deploy target 的只读诊断与恢复分流入口，管理"先观察什么、怎么判断、何时转回三步重装"。

首次安装/重装见 [Deploy Runbook](./deploy-runbook.md)；合同见 [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)。

## 推荐维护循环

`diagnose --json` -> `verify` -> 如需恢复则回 deploy runbook 三步重装 -> 重装后再跑 `diagnose`/`verify`。

## 源码侧维护检查清单（Source maintenance checklist）

> 独立入口见 [Distribution Maintenance Checklist](./distribution-maintenance-checklist.md)，该文档面向上游 governance checker 的英文术语验证。

当维护者新增、重命名或修改技能源码、适配器载荷、`.servo` 模板、Harness 合同或运维侧安装器行为时，必须在同一工作追踪内检查以下同步面。无法完成时，在收尾证据中写明理由。

| 变更面 | 同步要求 |
| --- | --- |
| canonical skill source（技能源码） | 更新 `product/harness/skills/README.md` 的技能索引和文档追溯链；确认技能包内不依赖包外的运行时文档；若技能名称容易误用，采用带控制域前缀的规范名称 |
| adapter payload（适配器载荷） | 同步 `agents` 和 `claude` 两个后端的 `payload.json`，核对 `skill_id`、`canonical_paths`、`required_payload_files`、`target_dir` 和 `legacy_*` 字段；重命名时旧名只能保留为旧版别名，不可作为推荐入口 |
| `.servo` template（`.servo` 模板与部署辅助） | 同步 `product/.servo_template/`、`repo-init-goal-skill/assets/`、`deploy_servo.js` 的生成和迁移路径，并补齐预览、执行和幂等性验证证据 |
| Harness / Skill contract | 跨模块思想同步唯一 Harness 指导思想；运行合同同步 owning `SKILL.md`、package assets 和 `.servo_template` |
| operator-facing installer behavior（运维侧安装器行为） | 同步 `docs/servo-installer/contracts/`、`docs/servo-installer/runbooks/`、`toolchain/scripts/deploy/README.md` 以及 CLI、TUI、包体烟测的命令说明 |
| package and release program（打包与发布流程） | 同步 npm 打包和发布预览、tarball 和 npx 烟测、发布通道不发版边界（no-publish boundary），以及必要的收尾证据 |

重构期间先执行 payload/package inventory、JSON/Node parse、disposable-target install/verify 和独立 source Review。旧 Python governance suite 的后续归属由 `MS-20260716-001` 决定。

以上检查清单面向源码侧维护者。运维侧日常使用只需下方 diagnose / verify 分流。

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

当 canonical skill payload 在源码层新增随包文件（例如 skill-private `scripts/` helper）后，尚未刷新 live target 的 `.agents/` / `.claude/` 上运行 `verify` 会报告 `missing-required-payload` 或 `target-payload-drift`。这是 source payload 已更新但 target install 尚未重装的正常诊断信号，不表示 target 目录可以反向作为 source truth。确认 source payload 通过 governance / adapter contract tests 后，再按 deploy runbook 的三步重装刷新目标。

已决定重装 -> [Deploy Runbook](./deploy-runbook.md)；字段/trust boundary -> [Mapping Spec](../contracts/deploy-mapping-spec.md) + [Payload Provenance](../contracts/payload-provenance-trust-boundary.md)；smoke/release -> [Testing](../../project-maintenance/testing/README.md) + [Governance](../../project-maintenance/governance/README.md)。

## Legacy `.aw/` runtime state

`.aw/` is legacy Harness runtime state, not installer-managed skill payload. `diagnose`, `verify`, `prune --all`, `install`, and ordinary `update` must not silently migrate or delete it. If a target repository still has `.aw/`, use [Legacy `.aw` Runtime Upgrade Runbook](./aw-runtime-upgrade-runbook.md) before planning any mutating action. The normative boundary remains [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md).
