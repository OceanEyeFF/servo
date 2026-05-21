---
title: "Worktrack Contract: WT-20260520-servo-npm-release-prep"
artifact_type: worktrack-contract
worktrack_id: WT-20260520-servo-npm-release-prep
milestone_id: MS-20260520-002
baseline_branch: develop-aw
baseline_ref: develop-aw@b321349
node_type: config
merge_required: yes
baseline_form: commit-on-config-branch
gate_criteria: validation + policy
if_interrupted_strategy: checkpoint-or-rollback
runtime_dispatch_mode: current-carrier
derived_from_milestone: false
appended_to_milestone: true
created: 2026-05-20T23:00:00+08:00
---

# Worktrack Contract

## Task Goal

完成 servo-installer npm 首发准备与 GitHub Release 发布流水线收口：
- 版本号对齐（0.5.2 → 0.5.3，从 rc 跳正式版）
- 包描述修正（移除残留 "AW"）
- npm publish 权限修复（移除 private flag）
- 发布流水线 env var 全量迁移（AW_INSTALLER_/AW_HARNESS_ → SERVO_INSTALLER_/SERVO_HARNESS_）
- deploy_aw.js → deploy_servo.js 重命名
- package.json 元数据字段 awInstallerRelease → servoInstallerRelease

## Acceptance Focus

- servo-installer@0.5.3 可正常发布（24h CD 后）
- GitHub Release workflow (publish.yml + ci.yml) 中无 AW_ 前缀 env var 残留
- 所有治理检查通过

## Non-Goals

- 不实际执行 npm publish（24h CD 期间）
- 不修改 .claude/ 目录
- 不修改 release channel 策略
