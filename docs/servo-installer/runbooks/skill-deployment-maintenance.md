---
title: "Skill Deployment 维护流"
status: active
updated: 2026-05-22
owner: servo-kernel
last_verified: 2026-05-22
---
# Skill Deployment 维护流

> 目的：提供 deploy target 的只读诊断与恢复分流入口，管理"先观察什么、怎么判断、何时转回三步重装"。

首次安装/重装见 [Deploy Runbook](./deploy-runbook.md)；合同见 [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md)。

## 推荐维护循环

`diagnose --json` -> `verify` -> 如需恢复则回 deploy runbook 三步重装 -> 重装后再跑 `diagnose`/`verify`。

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

已决定重装 -> [Deploy Runbook](./deploy-runbook.md)；字段/trust boundary -> [Mapping Spec](../contracts/deploy-mapping-spec.md) + [Payload Provenance](../contracts/payload-provenance-trust-boundary.md)；smoke/release -> [Testing](../../project-maintenance/testing/README.md) + [Governance](../../project-maintenance/governance/README.md)。

## Legacy `.aw/` runtime state

`.aw/` is legacy Harness runtime state, not installer-managed skill payload. `diagnose`, `verify`, `prune --all`, `install`, and ordinary `update` must not silently migrate or delete it. If a target repository still has `.aw/`, use [Legacy `.aw` Runtime Upgrade Runbook](./aw-runtime-upgrade-runbook.md) before planning any mutating action. The normative boundary remains [`.aw` Runtime Upgrade Contract](../contracts/aw-runtime-upgrade-contract.md).
