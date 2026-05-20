---
title: "Deploy Runbook"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-05-08
---
# Deploy Runbook

> 目的：定义首次安装、完整重装和 destructive reinstall 的 operator 主流程。

本页管理三步执行路径和停止线。诊断、mapping、wrapper 语义见相邻文档。

## 阅读时机

首次安装、按当前 source 完整重装、或只想确认三步主流程时。

## 主流程

package/local operator 主路径使用 `servo-installer`：

```bash
servo-installer prune --all --backend agents
servo-installer check_paths_exist --backend agents
servo-installer install --backend agents
```

Python reference/parity 命令已随 P0-067 Python cleanup 移除。`adapter_deploy.py`、`harness_deploy.py` 等 Python deploy 文件不再存在于 repo 中，当前 deploy runtime 入口仅 `servo-installer`（Node-only distribution）。

backend-specific target root override 见 [Codex Usage Help](../../project-maintenance/usage-help/codex.md) 和 [Claude Usage Help](../../project-maintenance/usage-help/claude.md)。package/local `servo-installer` 必须保持同一 deploy 语义；包装层命令面由 [Distribution Entrypoint Contract](../contracts/distribution-entrypoint-contract.md) 管理。

## 三步停止线

| 步骤 | 管什么 | 停止线 |
| --- | --- | --- |
| `prune --all` | 只删除当前 backend 可识别、带有效 `aw.marker` 的受管目录 | 无 marker、marker 不可识别、foreign 或用户目录不碰 |
| `check_paths_exist` | 基于当前 live bindings 做写入前冲突扫描 | 任一路径已存在就失败；不写业务文件，也不替 operator 判断是否覆盖 |
| `install --backend <backend>` | 只写当前 source 声明的 live payload | source contract 非法、重复 `target_dir` 或冲突未清理时，写入前失败 |

## 常见恢复口径

| 现象 | 处理口径 |
| --- | --- |
| `check_paths_exist` 报冲突 | 先手工清理冲突目录，再从 `prune --all` 重跑 |
| `install` 在写入前失败 | 先修 source contract，再从 `prune --all` 重跑 |
| 想确认重装后是否干净 | 转到 [Skill Deployment 维护流](./skill-deployment-maintenance.md) 跑 `diagnose` 或 `verify` |

drift/conflict/unrecognized 见 [Skill Deployment 维护流](./skill-deployment-maintenance.md)；字段合同见 [Mapping Spec](../contracts/deploy-mapping-spec.md)；trust boundary 见 [Payload Provenance](../contracts/payload-provenance-trust-boundary.md)；pack/smoke/release 见 [Testing](../../project-maintenance/testing/README.md) 和 [Governance](../../project-maintenance/governance/README.md)。
