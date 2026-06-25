---
title: "Distribution Maintenance Checklist"
status: active
updated: 2026-06-15
owner: servo-kernel
last_verified: 2026-06-15
---
# Distribution Maintenance Checklist

> 当维护者新增、重命名或修改技能源码、适配器载荷、`.servo` 模板、Harness 合同或运维侧安装器行为时，必须在同一工作追踪内检查以下同步面。无法完成时，在收尾证据中写明理由。

本清单是 `skill-deployment-maintenance.md` 中源码侧维护检查清单的独立入口。skill-deployment-maintenance.md 中的中文版本面向运维阅读；本文档面向上游 governance checker 的英文术语验证。

## Source maintenance checklist

| 变更面 | 同步要求 |
| ------ | -------- |
| canonical skill source | 更新 `product/harness/skills/README.md` 的技能索引和文档追溯链；确认技能包内不依赖包外的运行时文档；若技能名称容易误用，采用带控制域前缀的规范名称 |
| adapter payload | 同步 `agents` 和 `claude` 两个后端的 `payload.json`，核对 `skill_id`、`canonical_paths`、`required_payload_files`、`target_dir` 和 `legacy_*` 字段；重命名时旧名只能保留为旧版别名，不可作为推荐入口 |
| `.servo` template | 同步 `product/.servo_template/`、`harness-set-goal-skill/assets/`、`deploy_servo.js` 的生成和迁移路径，并补齐预览、执行和幂等性验证证据 |
| Harness artifact contract | 同步 `docs/harness/artifact/` 规范合同、技能模板、`.servo_template` 模板和对应的治理检查 |
| operator-facing installer behavior | 同步 `docs/servo-installer/contracts/`、`docs/servo-installer/runbooks/`、`toolchain/scripts/deploy/README.md` 以及 CLI、TUI、包体烟测的命令说明 |
| package and release program | 同步 npm 打包和发布预览、tarball 和 npx 烟测、发布通道不发版边界，以及必要的收尾证据 |
| governance checks | 跑 `governance_semantic_check.py`、`path_governance_check.py`、`npm test --prefix toolchain/scripts/deploy` |

## no-publish boundary

本文档中的检查清单不授权任何 npm publish、GitHub Release、git tag、dist-tag mutation、或外部 repo mutation。所有发布操作需要独立的 Release Milestone 授权。

## 最小本地检查

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
npm test --prefix toolchain/scripts/deploy
```

## 相关文档

- [Skill Deployment 维护流](./skill-deployment-maintenance.md) — 面向运维侧的中文维护指南
- [Deploy Runbook](./deploy-runbook.md) — 安装与重装流程
- [Deploy Mapping Spec](../contracts/deploy-mapping-spec.md) — source/payload/target 映射合同
- [servo-installer Release Channel Governance](../../project-maintenance/governance/servo-installer/servo-installer-release-channel-governance.md)
- [servo-installer Pre-Publish Governance](../../project-maintenance/governance/servo-installer/servo-installer-pre-publish-governance.md)
