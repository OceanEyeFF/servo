---
title: "Deploy Runbook"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-06-13
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

## .servo 模板同步

`servo-installer reconcile-servo` 对比已有 `.servo/` 运行时目录与当前包中的 `.servo` 模板，自动补齐缺失的节和字段。底层调用 `deploy_servo.js migrate`，是运维侧的首选入口。

### 原则

- **只追加，不覆盖**：已有运行时字段的值保持不变
- **幂等**：重复执行结果一致
- **无版本依赖**：仅基于节和字段名称匹配

### 预览（dry-run）

```bash
servo-installer reconcile-servo
```

输出 JSON：

```bash
servo-installer reconcile-servo --json
```

### 执行同步

```bash
servo-installer reconcile-servo --yes
```

### 幂等性验证

执行后再次运行 `servo-installer reconcile-servo --json`，`changes` 应为空。TUI 中对应菜单项流程相同：先 dry-run → 要求显式确认 → apply → 自动再次 dry-run 以验证幂等。

### 故障恢复

| 现象 | 处理 |
|---|---|
| 同步中断后文件不完整 | 重新运行 `reconcile-servo`，幂等特性会自动补齐缺失内容 |
| 误覆盖了用户数据 | `reconcile-servo` 只追加不覆盖，正常情况不会发生。如发生，检查模板是否新增了与已有字段同名的节或字段 |
| 模板文件缺失 | 辅助程序跳过该文件并输出警告，不影响其他文件的同步 |
| `.servo/` 目录不存在 | 先完成 Harness 初始化创建目录结构，再执行同步 |

`reconcile-servo` 不处理 `.aw/` 旧版运行时数据。如果目标仓库仍有 `.aw/` 目录，先阅读 [旧版 `.aw` 运行时升级手册](./aw-runtime-upgrade-runbook.md)，再使用 `migrate-runtime --from aw --to servo` 完成迁移。

诊断命令和故障分流见 [Skill 部署维护流](./skill-deployment-maintenance.md)；字段映射规则见 [映射规格](../contracts/deploy-mapping-spec.md)；载荷来源的信任边界见 [载荷信任边界](../contracts/payload-provenance-trust-boundary.md)；打包、烟测和发布流程见 [测试手册](../../project-maintenance/testing/README.md) 与 [发布治理](../../project-maintenance/governance/README.md)。
