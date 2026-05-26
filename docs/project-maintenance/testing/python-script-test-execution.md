---
title: "Python Script Test Execution"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-05-08
---
# Python Script Test Execution

> 目的：固定本仓库运行 Python 验证、治理检查和 closeout gate 的 operator-facing 命令口径。

本页属于 [Testing Runbooks](./README.md)。deploy 主流程见 [Deploy Runbook](../../servo-installer/runbooks/deploy-runbook.md)，review/verify 口径见 [Review / Verify Handbook](../governance/review-verify-handbook.md)。

## Command Rule

所有 Python 命令使用 `PYTHONDONTWRITEBYTECODE=1 python3 ...`。

## Governance Checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
```

覆盖分层/缓存、入口/链接/导航、语义合同/同步。

## Deploy Regression Tests

涉及 `toolchain/scripts/deploy/` 或 wrapper 时：`node toolchain/scripts/deploy/bin/servo-installer.js verify --backend agents`；同时影响治理脚本/closeout 测试时补 `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test -q`。

## Closeout Gate

涉及 closeout/gate/package/doc/adapter 时：`PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/closeout_acceptance_gate.py --json`，聚合 scope/spec/static/cache/test/smoke gates 并检查缓存污染；gate backfill 默认写入 `/tmp/servo-closeout/<repo>/`，不在 repo 根生成 `.autoworkflow/` 运行态。

## Diff Hygiene

```bash
git diff --check
```

失败时修复空白问题，再重跑与改动面匹配的 Python 验证。

## Common Bundles

文档导航或治理文档改动：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
git diff --check
```

deploy/adapter/package wrapper 改动：

```bash
node toolchain/scripts/deploy/bin/servo-installer.js verify --backend agents
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/closeout_acceptance_gate.py --json
```
