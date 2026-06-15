---
title: "Test Lane Taxonomy"
status: active
updated: 2026-06-15
owner: servo-kernel
last_verified: 2026-06-15
---
# 测试分层定义

本文定义本仓库测试体系的完整分层结构。它是测试分层（Test Lane Taxonomy）的权威定义，替代 `.servo/worktrack/test-lane-taxonomy-report.md` 中运行时副本的权威地位。运行时副本保留为 WT-20260614-test-lane-taxonomy 的工作追踪证据，本文档为长期真相。

## 集成测试层（5 层）

| Lane | 用途 | 触发时机 | Entry Criteria | Exit Criteria |
|------|------|---------|----------------|---------------|
| **focused**（聚焦测试） | 针对单个 checker/tool 的回归测试 | 开发时、WT closeout 前 | 对应 checker 或 test 文件存在且有变更 | pytest 全部通过 |
| **governance**（治理检查） | Repo 级结构性检查（分层、路径、语义、模板、orphan） | 每次 WT closeout 的 spec_gate | spec_gate 触发 | folder/path/semantic checkers 通过 |
| **deploy-unit**（部署包测试） | servo-installer Node.js 部署包的单元测试 | 每次 WT closeout 的 test_gate | test_gate 触发 | `npm test`（当前 154/154）通过 |
| **package-smoke**（包体冒烟测试） | 本地 .tgz 包安装/诊断/升级/验证全生命周期 smoke | 每次 WT closeout 的 test_gate | test_gate 触发 | deploy pkg + root pkg tarball smoke 通过 |
| **release-gate**（发布门禁） | closeout 串联 gate（scope/spec/static/cache/test/smoke） | 每次 WT closeout | WT closeout 启动 | 全部 6 个 sequential gate 通过 |

## 独立验证层（5 层）

| Lane | 用途 | 触发时机 | Trigger |
|------|------|---------|---------|
| **dogfood**（真机验证） | Claude/Codex/Pi 真实 backend 行为测试 | Pre-release、skill 变更后 | 人工触发或规范化脚本 |
| **registry-smoke**（注册表烟测） | npm registry `npx` smoke | 发布前 | Release Milestone |
| **complexity-scan**（复杂度扫描） | Repo 复杂度信号扫描（只读证据） | RepoScope 初始化、复杂 Milestone 入口 | Complexity trigger |
| **runtime-consistency**（运行时一致性检查） | milestone/backlog/control-state 一致性模拟 | 治理检查、pipeline 修复后 | 手动或 governance_semantic |
| **composite-acceptance**（复合验收） | Milestone final acceptance 多 lane 聚合 | Milestone handback 前 | Programmer judgment |

## Closeout Gate 方案

`closeout_acceptance_gate.py` 支持 `--profile` 参数：

| 方案 | 执行的检查点 | 适用场景 |
|------|------------|---------|
| `lightweight`（轻量） | scope_gate, spec_gate, static_gate, cache_gate | 纯文档修改、配置调整、小范围分析任务 |
| `full`（完整，默认） | 全部 6 道检查点（含 test_gate, smoke_gate） | 默认行为；发布版本、功能开发、代码修改任务 |

轻量方案跳过 test_gate（含 pytest、npm test 和 tarball 烟测）以及 smoke_gate。涉及发布或代码修改的任务必须用完整方案。

## Checker 归属

### Governance Lane（spec_gate）

| Checker | 覆盖 |
|---------|-----|
| `folder_logic_check.py` | 根目录分层、白名单、hidden/mount layer 检查 |
| `path_governance_check.py` | markdown 链接、主入口完整性、frontmatter 检查 |
| `governance_semantic_check.py` | 模板存在性、回链、skill 自洽性、orphan、runtime consistency、maintenance checklist |
| `repo_analysis_contract_check.py` | Repo Analysis 模板 contract 检查 |
| `check_cross_layer_sync.py` | 跨层同步检查 |
| `harness_scope_gate.py` | Harness scope 边界校验 |
| `governance_assess.py` | 四维治理收口评估 |
| `repo_governance_eval.py` | 五维 repo maintainability 评估 |
| `recommend_verification.py` | 推荐验证动作 |

### Release-Gate Lane

| Checker | 覆盖 |
|---------|-----|
| `scope_gate_check.py` | 改动范围越界检查（scope_gate） |
| `closeout_acceptance_gate.py` | closeout 串联 gate（完整流水线） |
| `gate_status_backfill.py` | gate 结果回填到 closeout state |
| `cache_scan_policy.py` | 缓存扫描策略（常量定义） |

### Complexity-Scan Lane

| Checker | 覆盖 |
|---------|-----|
| `complexity_signal_scanner.py` | repo 复杂度信号扫描（只读证据） |

### Runtime-Consistency Lane

| Checker | 覆盖 |
|---------|-----|
| `runtime_artifact_consistency_simulation.py` | milestone/backlog/control-state 一致性模拟 |

## 相关文档

- 测试执行指南：[`testing/README.md`](./README.md)
- Python 脚本执行规范：[`testing/python-script-test-execution.md`](./python-script-test-execution.md)
- Package smoke 执行规范：[`testing/npx-command-test-execution.md`](./npx-command-test-execution.md)
- Dogfood target repo 注册表：[`testing/dogfood-target-repo-registry.md`](./dogfood-target-repo-registry.md)
- Claude post-deploy behavior tests：[`testing/claude-post-deploy-behavior-tests.md`](./claude-post-deploy-behavior-tests.md)
- Codex post-deploy behavior tests：[`testing/codex-post-deploy-behavior-tests.md`](./codex-post-deploy-behavior-tests.md)
- 运行时报告（工作追踪证据）：`.servo/worktrack/test-lane-taxonomy-report.md`
