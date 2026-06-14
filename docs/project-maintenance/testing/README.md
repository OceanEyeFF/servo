---
title: "Testing Runbooks"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Testing Runbooks

`docs/project-maintenance/testing/` 保存测试执行指南：可重复执行的验证命令、registry/package smoke、Codex/Claude 部署后行为检查。deploy 合同在 `../deploy/`，发布治理在 `../governance/`。

范围：Python 脚本/治理检查/closeout gate 运行方式、`npx servo-installer`/本地 `.tgz` smoke、Codex/Claude 部署后测试。不包含：deploy 主流程、canonical skill 真相、release approval、npm publish 授权。

## 测试分层（Test Lane Taxonomy）

当前测试体系按 5 个 in-gate lane + 5 个 independent lane 分层。完整 taxonomy 见 `.servo/worktrack/test-lane-taxonomy-report.md`。

### In-Gate Lanes（在 closeout gate 内运行）

| Lane | 用途 | Gate |
|------|------|------|
| **governance** | 文件夹分层、路径治理、语义治理检查 | spec_gate |
| **focused** | 单个 checker/tool 的 pytest 回归测试 | test_gate (pytest) |
| **deploy-unit** | servo-installer Node.js 部署包单元测试 | test_gate (npm test) |
| **package-smoke** | 本地 .tgz 包全生命周期 smoke | test_gate (tarball) |
| **release-gate** | 串联 6 个 sequential gate | 全部 gate |

### Independent Lanes（不在 closeout gate 内）

| Lane | 用途 | 触发方式 |
|------|------|---------|
| **dogfood** | Claude/Codex/Pi 真实 backend 行为测试 | Pre-release，Human 触发或规范化脚本 |
| **registry-smoke** | npm registry `npx` smoke | Release Milestone |
| **complexity-scan** | Repo 复杂度信号扫描（只读证据） | RepoScope 初始化 |
| **runtime-consistency** | milestone/backlog/control-state 一致性模拟 | 手动或 governance_semantic |
| **composite-acceptance** | Milestone final acceptance 多 lane 聚合 | Programmer judgment |

## Gate Profile 选择

`closeout_acceptance_gate.py` 支持 `--profile` 参数：

| Profile | 运行 Gates | 适用场景 |
|---------|-----------|---------|
| `lightweight` | scope_gate, spec_gate, static_gate, cache_gate | docs-only、配置修改、小范围 analysis WT |
| `full`（默认） | 全部 6 gate（含 test_gate, smoke_gate） | 默认行为；release、feature、代码修改 WT |

轻量 profile 跳过 test_gate（pytest/npm test/tarball smoke）和 smoke_gate。release-sensitive 变更必须用 `full`。

## 按问题进入

| 问题 | 先看哪里 | 说明 |
|---|---|---|
| 运行 Python 脚本/治理检查/closeout gate | [python-script-test-execution.md](./python-script-test-execution.md) | 固定 `PYTHONDONTWRITEBYTECODE=1 python3 ...` 口径 |
| 验证 `npx servo-installer`/registry package/本地 `.tgz` | [npx-command-test-execution.md](./npx-command-test-execution.md) | registry `npx` smoke、本地 package smoke、多临时 workdir |
| 回归 `servo-installer` CLI/TUI 全命令面 | `toolchain/scripts/test/servo_installer_cli/` 和 `servo_installer_tui/` | CLI 覆盖 agents/claude 命令生命周期；TUI 通过 PTY 覆盖菜单交互 |
| npm publish 前跑本地 `.tgz` package smoke | [npx-command-test-execution.md](./npx-command-test-execution.md) | 发布前 local package smoke 命令和最小通过证据 |
| 选择长期 dogfood / target-repo 验证对象 | [dogfood-target-repo-registry.md](./dogfood-target-repo-registry.md) | 固定 5 个长期 target repos，并约束原仓库只读/临时副本 mutation 策略 |
| 观察 Codex 部署后 Harness 行为 | [codex-post-deploy-behavior-tests.md](./codex-post-deploy-behavior-tests.md) | 临时 repo、隔离 `.agents/skills/`、无交互 Codex 多轮 |
| 观察 Claude Code 项目级 skill entry、冷启动和新功能真实 backend 行为 | [claude-post-deploy-behavior-tests.md](./claude-post-deploy-behavior-tests.md) | 临时 repo、`.claude/skills/` 项目级安装、Claude 非交互读取；影响用户实际操作路径的新功能默认补真实 Claude dogfood |

## 真实 Backend Dogfood

Mock、fixture 和单元测试只能覆盖可重复的回归验证；当新功能改变了 Harness、skill、adapter、CLI 或 runbook 的实际交互路径时，它们无法替代真实 Claude Code 环境中的行为验证。新功能只要影响 Harness / skill / adapter / CLI / operator runbook 等实际使用路径，closeout 前默认补 [Claude Post-Deploy Behavior Tests](./claude-post-deploy-behavior-tests.md) 证据。若不跑，closeout 必须说明不适用理由、环境阻塞或后续 Worktrack。

## 和 Deploy 文档的分工

- 通用 deploy 入口：[deploy/README.md](../deploy/README.md)
- destructive reinstall 主流程：[deploy-runbook.md](../../servo-installer/runbooks/deploy-runbook.md)
- source/payload/target 映射合同：[deploy-mapping-spec.md](../../servo-installer/contracts/deploy-mapping-spec.md)
- release channel 规则：[servo-installer Release Channel Governance](../governance/servo-installer/servo-installer-release-channel-governance.md)
- publish 前 tuple/packlist/docs freshness/approval lock：[servo-installer Pre-Publish Governance](../governance/servo-installer/servo-installer-pre-publish-governance.md)
- payload provenance 与 update trust boundary：[payload-provenance-trust-boundary.md](../../servo-installer/contracts/payload-provenance-trust-boundary.md)
