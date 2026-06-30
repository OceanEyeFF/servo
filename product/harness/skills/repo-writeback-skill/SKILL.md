---
name: repo-writeback-skill
description: 当需要在 .servo/ artifact 中执行事务化写回时使用此技能。接收结构化写回指令，执行预校验→写入→后校验，替代 harness-skill 中分散的 ad-hoc 写回逻辑。
---

# .servo Writeback 技能

## 概览

本技能是通用 .servo artifact 写回算子，提供文件级事务保证：预校验字段合法性 → 一次性重写目标文件 → 提交后校验文件完整性。

它不承担业务逻辑（如 milestone completion 判定、pipeline advancement 计算），只执行经过验证的字段写入。业务逻辑仍由调用方（harness-skill、worktrack-close-skill 等）负责。

## 何时使用

当需要在 `.servo/` artifact 中执行结构化写回时使用：

- 更新 milestone artifact 的 progress_counter / status
- 更新 milestone-backlog 条目的 status / priority / depends_on
- 新增/更新 worktrack-backlog 条目
- 写入 control-state 的 checkpoint、active_milestone、pipeline_summary
- 更新 milestone-history（从 live backlog 迁移条目）
- 任何其他 .servo/ artifact 的结构化字段写入

## 事务模型

**文件级事务**：预校验 → 重写 → 后校验。

```text
writeback_instruction
    ↓
[预校验] 检查：文件存在、字段合法、值类型匹配
    ↓ (fail → return writeback_blocked)
[写入]   一次性重写目标文件（替换匹配的 YAML block）
    ↓
[后校验] 检查：文件可解析、字段值已更新、无意外修改
    ↓ (fail → return writeback_incomplete)
[完成]   返回 writeback_ok
```

### 为什么是文件级事务

- `.servo/` 文件在 worktrack 隔离 branch 上，无并发写
- 字段级 CAS 过度工程，增加实现复杂度
- 文件级事务保证多字段一致性，同时足够简单

## 写回指令格式

```yaml
writeback_instruction:
  target_file: ".servo/milestone/MS-20260623-002.md"
  operations:
    - action: "set"
      field_path: "progress_counter.completed"
      value: 2
    - action: "set"
      field_path: "updated"
      value: "2026-06-23T15:00:00+08:00"
  pre_validate:
    - check: "file_exists"
    - check: "field_type_match"
    - check: "no_destructive_operation"
  post_validate:
    - check: "file_parseable"
    - check: "field_value_equals"
    - check: "no_extra_fields_modified"
  evidence_passthrough:
    closeout_evidence_bundle_ref: string | N/A
    closeout_bundle_status: complete | incomplete | contaminated | historical_gap | missing | N/A
    dispatch_provenance:
      status: captured | linked | incomplete | missing | historical_gap | contaminated | N/A
      runtime_dispatch_record_ref: string | N/A
      subagent_dispatch_record_refs: []
      missing_dispatch_record_refs: []
      dispatch_result_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | N/A
      resolved_runtime_dispatch_status: delegated | current_carrier_fallback | permission_blocked | runtime_gap | dispatch_package_unsafe | blocked | historical_gap | incomplete | missing | contaminated | N/A
```

### 支持的操作

| action | 说明 | 适用场景 |
|--------|------|---------|
| `set` | 设置单个字段值 | 更新 progress_counter、status 等 |
| `upsert_entry` | 在 YAML list 中 upsert 条目（按 key 匹配） | 更新 milestone-backlog 条目 |
| `append_entry` | 在 YAML list 末尾追加条目 | 新增 worktrack-backlog 条目、追加 latest_closed_worktrack_commit |
| `move_entry` | 将条目从 source list 移动到 target list | milestone-backlog → milestone-history 迁移 |
| `set_section` | 替换整个 YAML section | 更新 pipeline_summary 等聚合字段 |

## 工作流

1. 接收调用方的结构化 `writeback_instruction`
2. 执行预校验：
   a. 目标文件存在（不存在则创建，或返回 blocked）
   b. 字段路径合法（在目标文件 schema 范围内）
   c. 值类型与目标字段匹配
   d. 非破坏性操作（不删除关键字段、不修改 protected sections）
   e. 若写入 closed worktrack / closeout evidence / milestone closeout refs，`evidence_passthrough` 必须携带 closeout handoff 中的 dispatch provenance 字段；缺失或不一致时返回 `writeback_blocked: evidence_passthrough_incomplete`
3. 执行写入：
   a. 读取目标文件全文
   b. 定位目标 YAML block
   c. 应用所有 operations（按顺序）
   d. 一次性写回文件（覆盖原文件）
4. 执行后校验：
   a. 文件可解析（YAML 语法正确）
   b. 所有 operations 的 field_value_equals 验证通过
   c. 未被操作的字段未发生意外修改
5. 返回结构化结果

## 预校验规则

### 文件存在性

- `file_exists`: 目标文件必须存在（`.servo/` 内路径）
- 若不存在且调用方标记 `create_if_missing: true`，创建空文件并填入 frontmatter + 基础结构
- 若不存在且未标记 create，返回 `writeback_blocked: file_not_found`

### 字段合法性

- `field_type_match`: 值的类型必须匹配目标字段的预期类型
- 已知类型映射（从 contract artifacts）：
  - `progress_counter.*`: integer
  - `status`: string (planned/active/completed/superseded)
  - `updated`: ISO8601 timestamp string
  - `completed/blocked/deferred`: integer
  - `pipeline_summary`: string pattern `planned=N / active=N / completed=N / superseded=N`
  - `latest_closed_worktrack_commit`: string
  - `closeout_evidence_bundle_ref`: string
  - `closeout_bundle_status`: string enum (`complete` / `incomplete` / `contaminated` / `historical_gap` / `missing`)
  - `dispatch_provenance.status`: string enum (`captured` / `linked` / `incomplete` / `missing` / `historical_gap` / `contaminated`)
  - `runtime_dispatch_record_ref`: string
  - `subagent_dispatch_record_refs`: list
  - `missing_dispatch_record_refs`: list
  - `dispatch_result_status`: string enum (`delegated` / `current_carrier_fallback` / `permission_blocked` / `runtime_gap` / `dispatch_package_unsafe` / `blocked` / `historical_gap` / `N/A`)
  - `resolved_runtime_dispatch_status`: string enum (`delegated` / `current_carrier_fallback` / `permission_blocked` / `runtime_gap` / `dispatch_package_unsafe` / `blocked` / `historical_gap` / `incomplete` / `missing` / `contaminated`)

### 非破坏性操作

- 不得删除以下字段：`milestone_id`、`title`、`created_by`、`created_at`
- 不得修改 `status: completed` → `status: planned`（不可逆状态变更需 programmer 审批）
- 不得删除或降级 closeout handoff 中已有的 `closeout_evidence_bundle_ref`、`closeout_bundle_status`、`dispatch_provenance.status`、`runtime_dispatch_record_ref`、`subagent_dispatch_record_refs`、`missing_dispatch_record_refs`、`dispatch_result_status`、`resolved_runtime_dispatch_status`。
- 若调用方只提供 prose closeout summary 或 carrier 自述，writeback 必须返回 `writeback_blocked: dispatch_provenance_missing` 或保留上游明确的 `historical_gap`；不得合成 `delegated`、`current_carrier_fallback`、`permission_blocked`、`runtime_gap`、`dispatch_package_unsafe` 或 `blocked`。

## 后校验规则

### 文件可解析性

- 写入后的文件必须是合法 YAML（至少 frontmatter 段可解析）
- 若解析失败，返回 `writeback_incomplete: file_corrupted`

### 字段值验证

- 对每个 operation，读取写入后的字段值，与预期值比较
- 不匹配时返回 `writeback_incomplete: field_value_mismatch`，列出具体不匹配字段

### 无意外修改

- 对比写入前后的文件 diff
- 只有 operations 中声明的字段应发生变化
- 若发现意外修改，返回 `writeback_incomplete: unexpected_modification`

## 事务写入集合规范

harness-skill §10.7.6 定义的 acceptance writeback 事务最小写入集合：

| 写入目标 | 操作 | 说明 |
|---------|------|------|
| `.servo/milestone/{id}.md` | set progress_counter, status, updated | 核心 milestone 状态 |
| `.servo/repo/milestone-backlog.md` | upsert_entry + move_entry | live backlog 条目更新 + 迁移到 history |
| `.servo/repo/milestone-history.md` | append_entry | 已完成的 milestone 归档 |
| `.servo/control-state.md` | set active_milestone, milestone_status, pipeline_summary | 控制面状态 |
| `.servo/repo/worktrack-backlog.md` | set status (planned/active → done/deferred/blocked) | worktrack 状态归一化 |

事务执行顺序：先写入 milestone artifact → 更新 backlog → 迁移 history → 更新 control-state → 归一化 worktrack-backlog。

任一步骤 fail，标记 `writeback_incomplete`，不继续后续步骤。

## 与 worktrack-cleanup-skill 的边界

| 维度 | .repo-writeback-skill | worktrack-cleanup-skill |
|------|----------------------|---------------------|
| **操作对象** | `.servo/` artifact 文件内容（字段值） | 本地 git 分支 + backlog 条目归档 + control-state 压缩 |
| **操作性质** | 字段级内容变更（写、改、迁移） | 文件系统/分支清理（删、归档、压缩） |
| **典型动作** | 更新 progress_counter、追加 commit hash、迁移 backlog 条目 | 删除已合并 worktrack/milestone 分支、归档 history、压缩滚动日志 |
| **事务保证** | 文件级事务（预校验→重写→后校验） | 安全守卫（不碰 remote、不删未合并分支、不删 baseline） |
| **触发时机** | 每次 worktrack closeout / milestone acceptance / checkpoint 更新 | Milestone final acceptance 后（merge → refresh → cleanup 第三阶段） |
| **副作用** | 仅修改 `.servo/` 文件内容 | 删除本地分支、修改 backlog 条目归属、compact control-state |

**关键区分**：writeback 改"文件里写了什么"，cleanup 改"磁盘上有什么分支"。两者不同时执行，但可能在同一 closeout 链中先后调用。

## .servo/ 跟踪模式

`.servo/` 目录的 git 跟踪策略因仓库而异：

| 模式 | 说明 | writeback 行为 |
|------|------|---------------|
| **untracked（默认）** | `.servo/` 在 `.gitignore` 中，不进入 git 历史 | 仅文件级事务，不执行 `git add` |
| **tracked** | `.servo/` 被 git 跟踪，作为 repo 正式 history 的一部分 | 文件级事务 + 写入后 `git add` 目标文件 |

跟踪模式从调用方的 control-state 或 repo 配置中读取（`servo_tracking_mode: untracked | tracked`）。本 skill 不决定跟踪策略，只根据模式调整写入后的 git 行为。

> 当前仓库默认 `untracked`。若切换到 `tracked`，writeback 事务的第三步（后校验）需扩展到包含 `git diff --check`。

## 内置 .servo 操作模式

本 skill 内置以下常见 .servo artifact 操作模式，调用方可直接使用模式名称，无需手写完整 instruction。

### M1: worktrack-closeout-progress

更新 milestone progress_counter 并追加 latest_closed_worktrack_commit。

```yaml
writeback_instruction:
  mode: "worktrack-closeout-progress"
  params:
    milestone_id: "MS-20260623-002"
    worktrack_id: "WT-xxx"
    commit_ref: "wt-xxx@abc1234"
    merge_target: "ms/MS-20260623-002-worktrack-lifecycle-complete"
    closeout_evidence_bundle_ref: ".servo/...#closeout-evidence-bundle"
    closeout_bundle_status: "complete"
    dispatch_provenance:
      status: "linked"
      runtime_dispatch_record_ref: ".servo/...#runtime-dispatch-WT-xxx"
      subagent_dispatch_record_refs: []
      missing_dispatch_record_refs: []
      dispatch_result_status: "delegated"
      resolved_runtime_dispatch_status: "delegated"
```

自动执行：

- milestone artifact: `progress_counter.completed += 1`, `updated = now`
- control-state: 追加 `latest_closed_worktrack_commit`, 更新 `active_milestone_progress`
- worktrack-backlog: upsert 条目 status = `done`；若写入 evidence refs，同步保留 `closeout_evidence_bundle_ref`、`closeout_bundle_status` 与完整 `dispatch_provenance` passthrough 字段

### M2: worktrack-init-register

注册新 worktrack 到 control-state 和 worktrack-backlog。

```yaml
writeback_instruction:
  mode: "worktrack-init-register"
  params:
    worktrack_id: "WT-xxx"
    milestone_id: "MS-xxx"
    node_type: "docs"
    branch: "wt-xxx"
    status: "active"
```

### M3: worktrack-closeout-clean

Worktrack closeout 后清理 control-state 中的 active worktrack 指针。

```yaml
writeback_instruction:
  mode: "worktrack-closeout-clean"
  params:
    worktrack_id: "WT-xxx"
    next_function: "RepoScope.Observe"
```

自动执行：

- control-state: `active_worktrack = none`, `worktrack_scope = closed`, `current_function = next_function`

### M4: milestone-backlog-upsert

更新或插入 milestone-backlog 条目。

```yaml
writeback_instruction:
  mode: "milestone-backlog-upsert"
  params:
    milestone_id: "MS-xxx"
    updates:
      status: "active"
      priority: 42
```

### M5: milestone-activation-switch

激活 milestone（设置 active，更新 pipeline 上下文）。

```yaml
writeback_instruction:
  mode: "milestone-activation-switch"
  params:
    milestone_id: "MS-xxx"
    previous_active: null  # 或上一个 active milestone_id
```

自动执行：

- control-state: `active_milestone = milestone_id`, `milestone_status = active`
- milestone-backlog: 条目 status = `active`
- milestone artifact: status = `active`
- 若 previous_active 非空：其 status → `completed`（goal-driven）或 `superseded`（work-collection）

### M6: baseline-checkpoint-update

更新 control-state 的 Baseline Traceability checkpoint。

```yaml
writeback_instruction:
  mode: "baseline-checkpoint-update"
  params:
    checkpoint_type: "latest_observed_checkpoint" | "last_doc_catch_up_checkpoint" | "milestone_input_checkpoint"
    hash: "abc1234"
    verified_at: "2026-06-23T16:00:00+08:00"
```

### M7: pipeline-summary-recalc

重新计算并写入 milestone_pipeline_summary。

```yaml
writeback_instruction:
  mode: "pipeline-summary-recalc"
  params:
    planned: 3
    active: 1
    completed: 61
    superseded: 0
```

### M8: milestone-history-archive

将 milestone 条目从 live backlog 迁移到 history。

```yaml
writeback_instruction:
  mode: "milestone-history-archive"
  params:
    milestone_id: "MS-xxx"
    final_status: "completed" | "superseded"
    accepted_at: "2026-06-23T16:00:00+08:00"
    accepted_by: "programmer"
```

自动执行：

- milestone-backlog: 移除 live 条目
- milestone-history: 追加 archived 条目
- milestone artifact: status = final_status

### M9: control-state-route-update

更新 control-state 的路由和当前动作字段。

```yaml
writeback_instruction:
  mode: "control-state-route-update"
  params:
    current_function: "RepoScope.Observe"
    recommended_next_route: "RepoScope.Decide"
    current_next_action: "milestone 3/6; next WT: contract-checklist"
```

### M10: handback-history-append

追加 handback 历史记录到 control-state。

```yaml
writeback_instruction:
  mode: "handback-history-append"
  params:
    status: "milestone-activated" | "worktrack-initialized" | "worktrack-closed" | "repo-scope-ready"
    detail: "WT-xxx completed and merged"
```

## 手动写回模式（高级）

当内置模式不覆盖时，使用原始 instruction 格式：

### 模式 A: Worktrack closeout 后更新 progress

```yaml
writeback_instruction:
  target_file: ".servo/milestone/MS-20260623-002.md"
  operations:
    - action: "set"
      field_path: "progress_counter.completed"
      value: 2
    - action: "set"
      field_path: "updated"
      value: "2026-06-23T15:00:00+08:00"
```

### 模式 B: 追加 latest_closed_worktrack_commit

```yaml
writeback_instruction:
  target_file: ".servo/control-state.md"
  operations:
    - action: "append_entry"
      list_path: "Active Worktrack.latest_closed_worktrack_commit"
      value: "wt-xxx@abc1234 (merged to ms/MS-xxx)"
```

### 模式 C: Milestone completion 事务

```yaml
writeback_instruction:
  transaction_id: "txn-MS-20260623-002-acceptance"
  steps:
    - target_file: ".servo/milestone/MS-20260623-002.md"
      operations:
        - action: "set"
          field_path: "status"
          value: "completed"
    - target_file: ".servo/repo/milestone-backlog.md"
      operations:
        - action: "move_entry"
          entry_key: "milestone_id"
          entry_value: "MS-20260623-002"
          from_list: "live_entries"
          to_list: "completed_entries"
    # ... more steps
```

## 输出格式

```yaml
writeback_result:
  transaction_id: "txn-xxx"
  status: "writeback_ok" | "writeback_blocked" | "writeback_incomplete"
  steps_completed: 3
  steps_total: 3
  pre_validation:
    passed: true | false
    failures: []
  post_validation:
    passed: true | false
    failures: []
  affected_files:
    - ".servo/milestone/MS-xxx.md"
    - ".servo/repo/milestone-backlog.md"
  proceed_blockers: []
  recommendation: "continue" | "handback" | "retry"
```

## 硬约束

- 本技能不承担业务逻辑判定（如 milestone completion 条件、pipeline advancement 规则）。只执行经过调用方验证的字段写入。
- 文件不存在且未授权 create 时，必须返回 blocked，不得猜测内容。
- 事务中任一步骤失败，不得继续后续步骤，必须标记 writeback_incomplete。
- 不得静默修改未被声明的字段。
- 写回失败不得伪装成成功；writeback_incomplete 必须暴露具体失败字段和原因。
- 不得跳过预校验或后校验。
- writeback 不 dereference 或合成 dispatch records。它只能验证调用方传入的 provenance payload 结构完整并原样写入目标字段；需要 dereference 时返回调用方补证。

## 资源

- 写回指令格式与字段定义已详述于本技能 §Writeback Instruction Format
- 事务模型已详述于本技能 §事务模型
