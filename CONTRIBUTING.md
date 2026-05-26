---
title: "贡献指南"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# 贡献指南

本仓库是 repo-side contract layer。贡献应保持范围收敛、意图明确，并与治理规则对齐。

## 默认工作流

1. 为当前变更创建独立分支。
2. 使用 Pull Request 完成审查和合并。
3. 在请求 review 前运行最小治理检查。

## 必需本地检查

请求 review 前运行以下命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_folder_logic_check.py toolchain/scripts/test/test_closeout_gate_tools.py toolchain/scripts/test/test_agents_adapter_contract.py
```

## Review 预期

- 遵循 `docs/project-maintenance/governance/review-verify-handbook.md`。
- 如果修改治理规则，同一个 PR 中必须同步更新对应文档和检查脚本。
- 如果新增根目录对象，必须同步更新 `docs/project-maintenance/foundations/root-directory-layering.md` 和 folder logic checks。

## PR / 分支规则

分支模型、PR 要求和 CI 预期见 `docs/project-maintenance/governance/branch-pr-governance.md`。
