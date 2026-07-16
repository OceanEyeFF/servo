---
title: "Existing Code Project Adoption"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-06-13
---
# Existing Code Project Adoption

> 目的：说明 `discovery-input.md` 的定位与生成约束——该文件是已有代码库接入 Harness 前，由 `repo-init-goal-skill` 自动采集的只读事实快照，仅供起草 Goal Charter 参考，不承载目标或决策。

本页聚焦已有代码接入的发现输入环节；运行合同与配套脚本见 [`repo-init-goal-skill`](../../../product/harness/skills/repo-init-goal-skill/SKILL.md)。

> **本文术语**：`discovery-input.md` 指由 `repo-init-goal-skill` 自动采集的只读事实快照；`goal-charter.md` 指用户确认后的长期目标文件；`snapshot-status.md` 指仓库慢变量观测面；`control-state.md` 指 Harness 运行时控制状态；adapter payload 指 Skill 下发的脚本与模板。

## 适用场景

目标 repo 已有代码但无 Harness `.servo/` 控制面接入时使用。Skill 所属模板见 `repo-init-goal-skill/assets/`，runtime target 为 `.servo/repo/discovery-input.md`。

## Operator 命令

```bash
node product/harness/skills/repo-init-goal-skill/scripts/deploy_servo.js generate \
  --deploy-path "$TARGET_REPO" \
  --baseline-branch "$BASELINE_BRANCH" \
  --adoption-mode existing-code-adoption
```

adoption 模式下，默认生成与 `--profile` 生成均自动包含 `repo-discovery-input`；若显式传入 `--template`，则以传入模板为准，不再自动注入。

## 不变量

- `.servo/repo/discovery-input.md` 是只读事实输入，不承载已确认的项目目标——确认后的长期目标只写入 `goal-charter.md`
- `repo/snapshot-status.md` 可引用 discovery 作为来源，但不直接复制
- `control-state.md` 不将 discovery 字段提升为控制指令
- baseline branch 来自显式参数或可验证 ref，不回退到 `init.defaultBranch`，不写死 `main`
- 不覆盖已有的 `.servo/goal-charter.md`
- adoption 不等同于 deploy target install——前者只采集事实输入，后者涉及部署变更
- adapter payload 与 package-local assets 是分发实现；长期目标仍由用户确认后的 Goal Charter 承接

## 验证入口

改变 discovery input、Skill asset、baseline branch 解析或 goal overwrite 策略时，必须同步 canonical Skill 与 deploy package，并在 disposable target 中核对生成结果；旧 Python 测试树的重建由 `MS-20260716-001` 承接。
