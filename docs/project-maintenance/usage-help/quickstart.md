---
title: "Harness Quickstart Tutorial"
status: active
updated: 2026-05-18
owner: aw-kernel
last_verified: 2026-05-18
---

# Harness Quickstart Tutorial

> 目标：让新 operator 在 10 分钟内完成 Harness 安装、初始化、第一个 Worktrack 闭环，并理解 handback 和显式 unlock 的边界。

## 前置条件

- Node.js >= 18（用于 `npx aw-installer`）
- 一个 Git 仓库（已有代码或空项目均可）
- 一个支持 slash command 的 Coding CLI（Codex 或 Claude Code）

## 第零步：诊断当前仓库状态

在安装前，先诊断目标仓库是否已安装过 Harness：

```bash
npx aw-installer diagnose --backend agents --json
```

输出示例：
```json
{"status":"not-installed","backend":"agents","target_root":"/path/to/repo"}
```

如果已安装，`diagnose` 会报告当前版本和 skill 清单。使用 `--backend claude` 检查 Claude Code 兼容路径。

## 第一步：安装 Harness Skills

在目标仓库根目录执行：

```bash
npx aw-installer install --backend agents
```

验证安装：

```bash
npx aw-installer verify --backend agents
```

`agents` 是当前主路径 backend。Claude Code 用户将 `--backend agents` 替换为 `--backend claude`。

## 第二步：初始化 Harness 控制面

在 Coding CLI 中调用：

```
/set-harness-goal-skill
```

这一步会创建 `.aw/` 目录并生成 Goal Charter（`repo goal/charter`），定义仓库的长期目标、工程节点类型和系统不变量。

初始化完成后，`.aw/` 下会生成：
- `control-state.md` — Harness 控制面状态
- `goal-charter.md` — 仓库目标与约束
- `repo/` — Repo 级快照和 backlog

## 第三步：启动 Harness 执行第一个 Worktrack

在 Coding CLI 中调用：

```
/harness-skill 请逐项推进MileStone的既定内容。
这一轮执行周期中我会给你批准30个连续执行任务的行动额度（Worktrack额度）。
```

**关键参数说明：**
- `Worktrack额度`：本轮允许 Harness 连续执行的 Worktrack 数量
- 权限声明：SubAgent 开关、低危险自动审批、连续工作、按需增加 Worktrack

Harness 收到指令后会按控制回路逐项推进：

1. **状态估计（Observe）**：读取当前 Scope、Milestone 和 git 基线
2. **初始化 Worktrack（Init）**：创建独立 Git 分支、Worktrack Contract、Plan/Task Queue
3. **分派执行（Dispatch）**：编码或文档变更，可由 SubAgent 或当前载体执行
4. **证据收集（Verify）**：运行治理检查三元组
5. **Gate 裁决（Judge）**：三个正交校验面（implementation + validation + policy）
6. **Closeout**：merge → refresh snapshot → cleanup → 回到 RepoScope
7. 选择下一个 Worktrack 或触发 Milestone handback

### 每个 Worktrack 的验证命令

Harness 在 Verify 阶段自动运行以下治理检查：

```bash
# 路径治理：检查文档链接可达性、book spine 覆盖、inline path 有效
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py

# 目录逻辑：检查根目录分层、hidden/state/mount 层合规
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py

# 语义治理：检查文档孤立、模板对齐、过期引用等
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py --json
```

所有检查通过（warnings 允许为 retained pre-existing）后，Gate 才会放行进入 Closeout。

### 安装验证命令速查

```bash
# 诊断安装状态
npx aw-installer diagnose --backend agents --json

# 验证安装完整性
npx aw-installer verify --backend agents

# 查看 CLI 帮助
npx aw-installer --help
```

### Backend 差异速查

| Backend | 安装命令 | 部署路径 | 说明 |
|---------|---------|---------|------|
| `agents` | `npx aw-installer install --backend agents` | `.agents/skills/` | 主路径，Codex 默认 |
| `claude` | `npx aw-installer install --backend claude` | `.claude/skills/` | Claude Code 兼容路径 |

两者共享同一套 Harness 合同和验证标准，差异仅在部署目标目录和 runtime 配置。

## 第四步：理解 Handback 和显式 Unlock 边界

### 什么是 Handback

Harness 在以下情况会停止并将控制权交还给 programmer：

- **Milestone 验收边界**：一个 Milestone 的所有 Worktrack 完成闭环后，Harness 停止等待 programmer 验收
- **审批门控**：目标变更、范围扩张或其他需要 programmer 决策的动作
- **证据门控**：所需证据缺失或矛盾，无法安全继续
- **路由阻塞**：Gate 裁决为失败或阻塞

### 什么是显式 Unlock

Handback 后，**裸"继续工作"或"继续"不构成有效的 unlock 信号**。Harness 要求 programmer 提供实质性新输入：

**有效的 unlock 信号示例：**
- 对 Milestone 的明确验收决定（"接受 MS-xxx"或"拒绝，原因：..."）
- 新的 Milestone brief 确认（"确认 Quickstart Tutorial 的 Milestone brief，请写入 pipeline"）
- 新指令加具体范围（"请初始化 WT-xxx，范围是..."）
- 权限变更声明（"批准 30 个 Worktrack 额度，允许 SubAgent"）

**无效的 unlock 信号（会被 Harness 拒绝）：**
- "继续工作"
- "继续"
- "重试"
- 对上一轮输出的纯文字摘要

### Handback 后的正确操作

```
程序员审阅 Milestone 完成状态
    ↓
验收通过？
    ├─ 是 → "接受 MS-xxx，激活下一个 Milestone"
    └─ 否 → "拒绝 MS-xxx，原因：xxx。追加 Worktrack：WT-xxx"
```

## 常见问题

### Q: Worktrack 额度用完了怎么办？

Harness 会在额度耗尽时停止并交还控制权。你可以用新的 `/harness-skill` 调用授予更多额度。

### Q: 如何查看当前 Milestone 进度？

Harness 在每轮控制回路中会自动报告 Milestone 进度。你也可以直接查看 `.aw/milestone/` 目录下的 Milestone artifact。

### Q: agents 和 claude backend 有什么区别？

`agents` 是主路径，部署到 `.agents/skills/`；`claude` 是兼容路径，部署到 `.claude/skills/`。两者共享同一套 Harness 合同和验证标准。

### Q: 如何修改仓库目标？

使用 `/repo-change-goal-skill` 或 `/repo-append-request-skill` 发起目标变更请求。目标变更需要 programmer 显式审批。

## 下一步

- 深入了解 Harness 控制回路：[docs/harness/README.md](../../harness/README.md)
- 按场景选择使用路径：[recommended-usage.md](./recommended-usage.md)
- 按 backend 查看差异：[codex.md](./codex.md) | [claude.md](./claude.md)
- 部署与安装详情：[deploy/README.md](../deploy/README.md)
