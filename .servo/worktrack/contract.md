---
title: "Worktrack Contract: WT-20260520-servo-external-rename"
artifact_type: worktrack-contract
worktrack_id: WT-20260520-servo-external-rename
milestone_id: MS-20260520-002
baseline_branch: develop-aw
baseline_ref: develop-aw@94a570044eb651fa2f1aa9ecef3cdb119bc2f537
node_type: config
merge_required: yes
baseline_form: commit-on-config-branch
gate_criteria: validation + policy
if_interrupted_strategy: checkpoint-or-rollback
runtime_dispatch_mode: auto
derived_from_milestone: true
created: 2026-05-20T19:22:00+08:00
---

# Worktrack Contract

## Task Goal

将项目外部可见面从 `servo-installer` / `servo` 重命名为 `servo-installer` / `servo`。包括 GitHub repo rename、npm 新包发布、以及所有入口文档更新。

## Task Definition

1. **GitHub repo rename**: `servo` → `servo`
2. **npm 包准备**: 更新 `package.json` name 为 `servo-installer`，准备发布
3. **入口文档更新**: README.md、INDEX.md、docs/book.md、quickstart 等文件中将 `servo-installer` 引用替换为 `servo-installer`
4. **旧包兼容**: `servo-installer` npm 包标记 deprecated（告知用户迁移到 `servo-installer`）

## Acceptance Focus

- GitHub repo 名变为 `servo`
- npm 上 `servo-installer` 包可安装
- 入口文档中 `servo-installer` 引用清零（changelog 除外）
- 旧 `servo-installer` npm 包显示 deprecated 提示

## Non-Goals

- 不执行内部 `aw-` 前缀迁移（留给 WT-2）
- 不修改 `.servo/` 目录（留给 WT-3）
- 不改变 package version, release tag, dist-tag 或 release channel policy

## Scope

- `README.md` / `INDEX.md`
- `docs/book.md`
- `docs/README.md`
- `package.json` (root and deploy)
- `toolchain/scripts/deploy/package.json`
- All docs referencing `servo-installer` in operator-facing contexts
- `.servo/repo/*.md` (snapshot, backlog entries referencing old name)

## Constraints

- 不改 git history
- 不改 `.autoworkflow/`、`.spec-workflow/`
- 不改 `.agents/`、`.claude/` deploy targets
- changelog 中的历史版本号保持不变
