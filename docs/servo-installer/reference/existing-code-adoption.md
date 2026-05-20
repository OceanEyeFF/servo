---
title: "Existing Code Project Adoption"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-05-08
---
# Existing Code Project Adoption

> 目的：定义把已有代码库接入 Harness 初始化流程时，operator-facing 的 `.servo/repo/discovery-input.md` 生成边界。

本页属于 [Deploy Runbooks](../../project-maintenance/README.md)，覆盖 adoption 生成边界。artifact 正文见 [Repo Discovery Input](../../harness/artifact/repo/discovery-input.md)；skill workflow 与可执行资产见 [`set-harness-goal-skill`](../../../product/harness/skills/set-harness-goal-skill/SKILL.md)。

## 适用场景

目标 repo 已有代码但无 Harness `.servo/` 控制面接入时使用。权威边界：canonical artifact definition 在 `docs/harness/artifact/repo/discovery-input.md`，skill-owned 模板在 `set-harness-goal-skill/assets/`，runtime target 在 `.servo/repo/discovery-input.md`。

## Operator 命令

```bash
node product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.js generate \
  --deploy-path "$TARGET_REPO" \
  --baseline-branch "$BASELINE_BRANCH" \
  --adoption-mode existing-code-adoption
```

默认/profile 生成自动包含 `repo-discovery-input`；显式 `--template` 选择仍以调用方为准。

## 不变量

`.servo/repo/discovery-input.md` 是只读事实输入，非 goal truth；确认后长期目标只写 `.servo/goal-charter.md`；`repo/snapshot-status.md` 可引用但不复制 discovery；`control-state.md` 不提升 discovery 为控制指令；baseline branch 来自显式参数/可验证 ref，不回退 `init.defaultBranch` 或写死 `main`；不覆盖已有 `.servo/goal-charter.md`；adoption 不是 deploy target install；adapter payload source 不能成为 artifact truth。

## 验证入口

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_set_harness_goal_deploy_aw_node.py
```

改变 discovery artifact、skill asset、baseline branch 解析或 goal overwrite policy 时，必须同步更新 artifact 文档、skill 入口和对应测试。
