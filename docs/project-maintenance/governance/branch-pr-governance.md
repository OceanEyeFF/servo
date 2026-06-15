---
title: "Branch / PR 治理规则"
status: active
updated: 2026-06-14
owner: servo-kernel
last_verified: 2026-06-14
---
# Branch / PR 治理规则

Decision time: 2026-04-25

> 目的：明确本仓库的分支与 PR 约束，为 review 与治理检查提供可重复的入口。

本页属于 [Governance](./README.md) 路径簇。

## 一、适用范围

适用于 `product/`、`docs/`、`toolchain/` 及根目录治理变更，以及引入或修改执行型治理对象（如 `.codex/`、review/verify 规则）。

## 二、分支约定

- `baseline branch`：由 `origin/HEAD` 动态解析的远端默认分支（当前为 `origin/HEAD -> master`），是 Worktrack 默认比较基准与 PR target 来源
- `protected baseline`：被远端保护规则覆盖的 baseline 分支，只允许 PR 合并
- `worktrack branch`：围绕单个 Worktrack 的限定范围工作分支，不替代或改写 baseline
- `current branch`：当前本地分支，需显式确认角色，不自动等同 baseline 或 worktrack
- Worktrack Contract 的 `baseline_branch` 是 PR target/merge target/checkpoint 判定的权威字段，不在 skill/hook/runbook 中写死
- 推荐分支命名：`work/<topic>`、`fix/<topic>`、`docs/<topic>`

## 三、PR 规则

变更必须通过 PR 提交，target 由 Worktrack Contract 的 `baseline_branch` 决定（合同缺失时，用 `origin/HEAD` 解析结果补齐或阻断 closeout）；PR 必须包含变更摘要、验证结果与风险说明，默认遵循 `.github/pull_request_template.md`。

发布开发分支到 `master` 的 release PR 只承接已完成 candidate 的合并，不在 PR 合并后继续改 candidate tuple。当前 `v0.6.1-rc.4` 发布周期使用 `develop -> master`。发布型 PR 打开或更新前必须确认：

- root `package.json`、`toolchain/scripts/deploy/package.json`、approval lock、CLI `--version` 和 PR 标题/正文中的版本一致
- `v<package.version>` tag 不存在，npm registry 中 `servo-installer@<package.version>` 不存在
- RC PR 明确使用 `next` channel；stable PR 明确使用 `latest` channel
- PR head SHA 与本地 release-readiness 验证所用 SHA 一致
- PR 正文必须区分本地已跑证据、远端 CI 证据、pending/skipped/not-run 项；未运行或被跳过的检查不得写成 passed
- source-version 文档 freshness 同步已完成或已明确说明不适用；若 release channel governance、testing/usage docs 或 root README 仍指向旧 source tuple，PR 必须保持 draft

## 四、Review 规则

`CODEOWNERS` 生效时以远端规则集为准；参考 `docs/project-maintenance/governance/review-verify-handbook.md`。

本仓库当前按单人维护模式运行：PR author 无需等待外部 reviewer 即可合并。GitHub 仍不允许 PR author approve 自己的 PR，因此 self-approval 不作为本仓库治理要求；owner/admin 可在 CI 通过、PR 内容与本地验证证据一致、release tuple 无冲突时直接 self-merge。release PR 的 handoff 需记录已通过检查、PR head SHA、merge commit SHA 和后续 release/tag/publish 动作。

`reviewDecision` 为空不等于审核失败；draft 状态、required check failure、pending check、skipped required check 或 release-readiness 证据缺失才是 release PR 的阻断信号。任何阻断信号存在时，不能把 PR 标成 ready for review，不能 merge，也不能创建 release tag。

## 五、CI 最小检查链

PR 阶段必须通过：`folder_logic_check.py` + `path_governance_check.py` + `governance_semantic_check.py` + pytest（folder_logic + closeout_gate + agents_adapter_contract）。

## 六、远端保护规则

必须启用 GitHub Branch Protection Ruleset：仅允许 PR 合并到 protected baseline，必须通过 CI 最小检查链，不允许 force push 与删除。单人维护模式下不要求 CODEOWNERS 外部 review；规则集匹配 `origin/HEAD` 当前 baseline（当前为 `master`）；`origin/HEAD` 迁移时同步更新 ruleset、Worktrack `baseline_branch` 与本文 `last_verified`。

## 七、本地 pre-push hook

```bash
git config core.hooksPath toolchain/scripts/git-hooks
chmod +x toolchain/scripts/git-hooks/pre-push
```

hook 通过 `origin/HEAD` 动态解析 baseline（当前解析为 `origin/master`）；无法解析时保守阻断 `main`/`master`。本地 hook 作为额外保障，不替代远端规则集。

## 八、例外与特批

- 若需跳过上述检查，须在 PR 中说明原因并获得显式批准。
- 禁止为"过关"降低检查标准或替换证据。
- release PR 若使用 owner/admin self-merge 或 ruleset bypass，PR 评论或 release handoff 必须记录：已通过检查、PR head SHA、merge commit SHA、后续发布是否继续；只有绕过失败检查时才需要额外记录 bypass 原因。

## 九、发布后分支同步

发布后若 `doc-catch-up-worker-skill` 写回 registry facts，应通过单独的 docs PR 合入 `master`，不要修改已发布 tag target。该 docs PR 合并后，把发布开发分支 fast-forward 到 `origin/master` 并推回远端，使下一轮开发基线与发布后文档事实一致。

## 十、相关文档

- `AGENTS.md`
- `docs/project-maintenance/governance/review-verify-handbook.md`
- `docs/project-maintenance/governance/path-governance-checks.md`
- `docs/project-maintenance/governance/servo-installer/servo-installer-release-standard-flow.md`
