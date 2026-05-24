---
title: "调整项目目标与追加需求"
status: active
updated: 2026-05-07
owner: servo-kernel
last_verified: 2026-05-07
---

# 调整项目目标与追加需求

> 项目进行中需要追加新功能、调整方向或变更已有目标时，按以下流程操作。

## 一、判断变更类型

### 1. 追加新功能（在现有目标内）

新需求在 Goal Charter 范围内：

- 通过 `$repo-append-request-skill` 提交追加请求
- 分类为 `new worktrack`，进入常规 worktrack 流程
- 不修改 Goal Charter

示例："在用户模块增加邮箱验证" -- 若已在用户模块范围内，直接创建新 worktrack。

### 2. 范围扩张（在活跃 worktrack 内）

当前有活跃 worktrack，新需求会改变其验收标准：

- 提交追加请求时说明"在 worktrack 中追加"
- Harness 分类为 `scope expansion`，需要审批
- 审批通过后更新 worktrack contract

### 3. 目标变更（超出 Goal Charter）

新需求改变了项目愿景、核心目标或系统不变量：

- 使用 `repo-change-goal-skill`
- 需要 programmer 明确审批
- 完成后系统重新进入 Observe

## 二、追加需求流程

```text
提出请求
  ↓
$repo-append-request-skill 分类路由
  ├─ goal change → repo-change-goal-skill（需审批）
  ├─ new worktrack → init-worktrack-skill
  ├─ scope expansion → 审批 → 更新 contract
  ├─ design-only → design worktrack
  └─ design-then-implementation → 两阶段 worktrack
```

### Coding CLI 示例

以 Codex 为例：

```txt
$repo-append-request-skill 追加请求：[描述需求]；边界：[希望包含什么，不包含什么]。
```

Harness 返回分类路由后，按建议路由继续。

## 三、修改 Goal Charter

需要修改 Goal Charter 时：

1. **备案当前状态**：确保活跃 worktrack 已 close 或 checkpoint
2. **发起目标变更**：使用 `$repo-change-goal-skill`
3. **说明变更内容**：什么变了、为什么变、新目标是什么
4. **等待审批**：目标变更需要 programmer 授权
5. **重新进入循环**：变更完成后，系统从 `RepoScope.Observe` 重新开始

### 需要修改 Goal Charter 的情况

- 项目方向发生重大变化
- 新增或删除 Engineering Node Map 中的节点类型
- 修改系统不变量
- 修改成功标准

### 不需要修改 Goal Charter 的情况

- 追加现有范围内的新 feature -- 用 `new worktrack`
- 修 bug -- 用 `bugfix` worktrack
- 更新文档 -- 用 `docs` worktrack

## 四、常见场景

| 场景 | 分类 | 流程 |
|------|------|------|
| 在现有范围内加一个功能 | new worktrack | 提交请求 -> init worktrack -> 执行 |
| 当前 sprint 想再多做一件事 | scope expansion | 提交请求 -> 审批 -> 更新 contract |
| 项目要换技术栈 | goal change | 备案 -> repo-change-goal-skill -> 审批 |
| 需要先调研再决定 | design-only | 提交 design 请求 -> design worktrack |
| 先设计方案再实现 | design-then-implementation | 两阶段 worktrack |

## 五、注意事项

- 不要用小需求绕过 goal change 审批
- scope expansion 显式暴露审批边界
- 所有变更更新相关文档（impacted docs）
- 已批准的 worktrack contract 在完成前不静默修改
