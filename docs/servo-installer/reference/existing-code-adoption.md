---
title: "Existing Code Project Adoption"
status: active
updated: 2026-05-08
owner: servo-kernel
last_verified: 2026-06-13
---
# Existing Code Project Adoption

> 目的：说明 `discovery-input.md` 的定位与生成约束——该文件是已有代码库接入 Harness 前，由 `repo-init-goal-skill` 自动采集的只读事实快照，仅供起草 Goal Charter 参考，不承载目标或决策。

本页属于 [Deploy Runbooks](../../project-maintenance/README.md)，聚焦已有代码接入的发现输入环节。artifact 正文见 [Repo Discovery Input](../../harness/artifact/repo/discovery-input.md)；skill 工作流与配套脚本见 [`repo-init-goal-skill`](../../../product/harness/skills/repo-init-goal-skill/SKILL.md)。

> **本文术语**：`discovery-input.md` 指由 `repo-init-goal-skill` 自动采集的只读事实快照；`goal-charter.md` 指用户确认后的长期目标文件；`snapshot-status.md` 指仓库慢变量观测面；`control-state.md` 指 Harness 运行时控制状态；canonical artifact 指 `docs/harness/artifact/` 下的权威定义；adapter payload 指 skill 下发的脚本与模板；deploy target install 指向目标仓库安装 servo 的操作。

## 适用场景

目标 repo 已有代码但无 Harness `.servo/` 控制面接入时使用。权威边界：canonical artifact 定义见 `docs/harness/artifact/repo/discovery-input.md`，skill 所属模板见 `repo-init-goal-skill/assets/`，runtime target 见 `.servo/repo/discovery-input.md`。

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
- adapter payload 源码不可升格为 artifact 真相——artifact 的定义权威在 `docs/harness/artifact/` 而非下发脚本中

## 验证入口

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_repo_init_goal_deploy_aw_node.py
```

改变 discovery artifact 定义、skill asset 内容、baseline branch 解析逻辑或 goal overwrite 策略时，必须同步更新 artifact 文档、skill 入口和对应测试。
