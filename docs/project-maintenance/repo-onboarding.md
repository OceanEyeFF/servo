---
title: "Repository Onboarding"
status: active
updated: 2026-05-07
owner: servo-kernel
last_verified: 2026-05-07
---

# Repository Onboarding

> 面向需要理解此仓库内部结构和运行方式的维护者。外部试用者先看 [README.md](../../README.md)。

## 仓库定位

构建 Codex-first 的 AI coding harness 平台，作为 repo-side contract layer 分发到多个项目。

这是一套可复用和迭代的能力系统：

- 统一的任务进入和收束方式
- 统一的上下文路由与执行边界
- 可分发到多仓库的 harness 形态

## 目录分层

| 目录 | 性质 |
|------|------|
| `docs/` | 真相层：project-maintenance / harness / analysis / ideas / archive |
| `product/` | 业务源码根：harness skills + adapters |
| `toolchain/` | 脚本/评测/测试/打包/部署工具 |
| `.aw/` | runtime control-plane state（非长期真相层） |
| `.agents/` `.claude/` | deploy target（非源码层） |
| `.autoworkflow/` `.spec-workflow/` | repo-local state layer |
| `.nav/` | compatibility navigation layer（非真实结构定义） |

### 核心定位

- `docs/`：文档真相、能力合同与治理规则
- `product/`：业务代码唯一源码根
- `toolchain/`：部署/治理检查/测试/research 工具

这三块之外：

- `.agents/`、`.claude/` 是 repo-local deploy target
- `.autoworkflow/`、`.spec-workflow/` 是 repo-local state/config
- `.nav/` 是 compatibility navigation

更完整的分层定义见 [`根目录分层`](./foundations/root-directory-layering.md)。

## 入口分工

| 文件 | 职责 |
|------|------|
| `README.md` | 对外使用入口：skills 使用说明、安装方法、快速试用路径 |
| `INDEX.md` | 按任务目标导向正确入口 |
| `AGENTS.md` | agent-facing 最小工作规则入口；若冲突，以 `docs/project-maintenance/` + `docs/harness/` 为准 |

## 典型工作链路

```text
目标 / 需求
  ↓
Worktrack Contract
  ↓
Plan / Task Queue
  ↓
AI 执行
  ↓
Review / Verify / Writeback
  ↓
验证与回灌
```

含义：

- 先收束已批准输入为正式工作追踪边界
- 展开工作追踪约定为可调度队列
- 只把已验证结果写回真相层
- backend-specific prompt 和 deploy wrapper 不反向定义主线真相

## 从哪里进入

1. [`AGENTS.md`](../../AGENTS.md)
2. [`INDEX.md`](../../INDEX.md)
3. 按任务进入：
   - Harness 主线与 artifact 合同：[`docs/harness/README.md`](../harness/README.md)
   - 业务源码：[`product/README.md`](../../product/README.md)
   - 工具层：[`toolchain/README.md`](../../toolchain/README.md)
4. 仅当任务命中分层、治理或 Harness artifact 边界时，再扩读 [`docs/README.md`](../README.md)、[`docs/project-maintenance/README.md`](README.md) 或 [`root-directory-layering.md`](foundations/root-directory-layering.md)。

## 非目标

- 不是单个 agent 的完整 runtime
- 不是模型私有的 prompt 仓库
- 不是一次性脚手架
- 不把 deploy target 当成 source of truth
- 不让首页充当完整操作手册

## 提醒

- `.agents/`、`.claude/` 是 deploy target，非源码层或真相层
- `.autoworkflow/`、`.spec-workflow/` 是 repo-local state/config，非默认阅读主线
- `.nav/` 是 compatibility navigation，非结构定义层
- 后端 prompt/wrapper 不替代跨后端共享 truth
