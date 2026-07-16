# CLAUDE.md

> 这是当前仓库的 Claude Code 入口文件。`AGENTS.md` 是通用规则入口，本文件是 Claude Code 专用适配层；Skill 运行合同以 canonical `SKILL.md` 为准。

## 项目定位

本项目的核心目标是构建一个 `Codex-first` 的 AI coding harness 平台，并将其作为 repo-side contract layer 分发到多个项目中使用。这里的 `Codex-first` 指平台目标、默认验证路径和首要分发对象；Claude Code 是兼容执行入口，应遵循同一 repo-side contract layer，而不是重新定义 Harness 真相。

- `docs/` = truth boundary（文档真相层）
- `product/` = canonical skills 与 adapters（业务源码根）
- `toolchain/` = 部署、评测与治理脚本
- `Harness` 是一级认知与文档域，遵循分层闭环控制协议

## 目录分层

| 目录 | 性质 |
|------|------|
| `docs/` | 跨模块文档层：project-maintenance 与最小 Harness doctrine |
| `product/` | 业务代码唯一源码根：harness skills + adapters |
| `toolchain/` | 脚本、评测、测试、打包、部署工具 |
| `.servo/` | runtime control-plane state（非长期真相层） |
| `.agents/` `.claude/` | deploy target（非源码层） |
| `.autoworkflow/` `.spec-workflow/` | repo-local state layer |
| `.nav/` | compatibility navigation layer（非真实结构定义） |

## 阅读路由

1. `docs/README.md`
2. `docs/project-maintenance/README.md`
3. `docs/project-maintenance/foundations/README.md`
4. `docs/project-maintenance/foundations/root-directory-layering.md`
5. `docs/project-maintenance/governance/review-verify-handbook.md`
6. `toolchain/toolchain-layering.md`
7. `docs/harness/foundations/Harness指导思想.md`
8. `product/harness/skills/README.md`
9. 当前任务对应的 canonical `SKILL.md`

`do_not_read_yet`：`.agents/` `.claude/` `.autoworkflow/` `.spec-workflow/` `.nav/`

## 默认工作流

1. `plan`：固定目标、范围、非目标、验收、风险和验证要求
2. `implement`：只做当前任务，不顺手扩边界
3. `verify`：先跑与改动面匹配的检查和测试
4. `review`：把 diff、计划和验收标准对齐
5. `writeback`：项目治理写回 `docs/project-maintenance/`；Skill 运行事实写回 canonical package；Harness docs 只接收稳定 doctrine

## 验证命令

```bash
# 分层与路径治理
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py

# closeout / gate
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/closeout_acceptance_gate.py --json

# adapter / deploy
node --test toolchain/scripts/deploy/test_servo_installer.js
```

Python 命令默认使用 `PYTHONDONTWRITEBYTECODE=1 python3 ...`，避免生成 `__pycache__` 和 `.pyc` 缓存。

## 强制同步规则

- 根目录分层、一级子目录、hidden/state/mount 层或 `.nav/` 规则变化 → 必须同步更新 foundations 文档和对应治理检查
- `AGENTS.md`、review/verify 流程或退出标准变化 → 必须同步更新 `review-verify-handbook.md`
- deployment / adapter 行为变化 → 必须同步更新相关 `deploy/` 文档和 verify 命令
- Harness doctrine 变化 → 同步唯一 doctrine 文件；canonical Skill 入口或运行合同变化 → 同步 package inventory、对应 `SKILL.md` 与治理检查
- 只有已验证结果才可以回写为长期真相

## 文档治理基线

- `docs/` 下除 `README.md` 外的正文文档必须有 frontmatter：`title / status / updated / owner / last_verified`
- `status`：`active | draft | superseded`
- 研究结论准入后必须升格到承接层（项目维护 → `docs/project-maintenance/`，Harness → `docs/harness/`，实现 → `product/` 或 `toolchain/`）
- 新增或接管文档作用域时，必须同步更新最近入口页并清理旧入口

## 硬约束

- 不要把 Harness 当成直接写代码的执行者；它是分层闭环控制系统
- `product/` 是业务代码唯一源码根；`.agents/` `.claude/` 只是 deploy target
- `.servo/` 是 runtime control-plane artifact 目录；不替代 `docs/` `product/` `toolchain/` 中的正式真相
- 不要把 deploy target、`.agents/` `.claude/` 或 `.servo/` 写成源码真相
- 不要把未验证结论写回长期 truth layer
- 不要在普通 Decide 中修改 repo 目标；目标变更必须走 ChangeGoal
- Worktrack 技术判断由独立 Review 承担，Close 只做机械关闭与 Repo Refresh handoff
- PR 不是闭环终点；Candidate Worktrack 完成以 merge、finished handback 和 Repo Refresh 为准
- 修复类任务不得只压住当前症状；必须检查相邻状态、恢复路径和 operator-facing 语义

## 外部参考

- Harness 控制面入口：`product/harness/skills/harness-skill/SKILL.md`
- Review/Verify 治理：`docs/project-maintenance/governance/review-verify-handbook.md`
- 部署治理：`docs/project-maintenance/deploy/`
- Toolchain 分层：`toolchain/toolchain-layering.md`
