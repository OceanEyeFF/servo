---
name: worktrack-cleanup-skill
description: 当需要对 repo 执行限定范围的清理操作（stale backlog 条目归档、已完成 milestone/worktrack 的本地分支清理）时，使用这个技能。它是 repo 维护层面的清理 worker，不执行破坏性操作，不修改 remote，不删除未确认的 artifact。
---

# Servo Cleanup 技能

## 概览

本技能是 Harness 执行平面的 repo 清理 worker，在 Harness closeout pipeline 中定位为 `merge → refresh → cleanup` 的最后一环，由 `harness-skill` 在 Milestone final acceptance 后绑定调用。它负责执行以下安全的清理操作：

1. **backlog 过期引用清理**：将 worktrack-backlog 中已完成条目归档到 worktrack-history，保持 backlog 精简。
2. **已完成 milestone/worktrack 的本地分支清理**：删除已闭环的 `ms/*` 和 `wt/*` 本地分支。
3. **control-state 安全压缩**：在 dry-run、字段保留校验和恢复证据齐备时，压缩 `.servo/control-state.md` 中的重复历史行。
4. **runtime artifact 维护扫描**：报告 `.servo` stale refs、orphan artifact、rolling evidence reuse、临时 discovery 生命周期缺口和执行输出引用缺口，不执行清理。

本技能设计为低风险、可复核的清理操作；不执行 `git push --delete`、不修改 remote、不删除 `.servo/` artifact 文件、不触碰 protected 分支。

## 何时使用

当满足以下任一条件时使用：

- Worktrack-backlog 体量过大（如超过 100 条已完成条目），需要归档清理
- 本地分支过多（如超过 50 个 stale 分支），需要清理已完成 milestone/worktrack 的分支
- Milestone closeout 后，对应 `ms/*` 分支可安全删除
- `.servo/control-state.md` 中历史 handback、旧 checkpoint 或旧 closed-worktrack 记录过长，需要压缩到当前路由所需 footprint
- 需要在 milestone 结束清理或 repo cleanup 前生成 `.servo` runtime artifact maintenance sweep report
- 周期性 repo 维护

不适用于：

- 删除未完成或 active 状态的 worktrack 分支
- 删除 develop/master/main 等 protected 分支
- 删除 remote 分支（`git push --delete`）
- 删除 `.servo/milestone/` 或 `.servo/worktrack/` artifact 文件
- 使用 installer-generated backup/update artifacts 作为 control-state history source
- 在缺少 dry-run 或 hydration-critical 字段校验时重写 `.servo/control-state.md`
- 把 maintenance sweep finding 当作删除或移动授权

## 工作流

### 1. Backlog 清理

1. 读取 `.servo/repo/worktrack-backlog.md` 和 `.servo/repo/worktrack-history.md`。
2. 识别 backlog 中所有 `[done]`、`[resolved]` 状态的条目。
3. 对于 history 中已存在的条目（按 worktrack_id 匹配），从 backlog 中移除。
4. 对于 history 中不存在的条目，先在 history 中追加，再从 backlog 移除。
5. 清理后，backlog 中仅保留 `[active]`、`[blocked]`、`[deferred]` 条目及当前 active milestone 的 pending worktrack。
6. 若 backlog 清理后条目数为 0，active_worktrack 标记为 `N/A`。

### 2. 本地分支清理

1. 列出所有本地 `ms/*` 分支。
   - 检查对应 milestone 是否在 `.servo/repo/milestone-history.md` 中且状态为 `completed`。
   - 若已完成：删除本地分支（`git branch -d`）。
   - 若当前 active milestone（从 `.servo/control-state.md` 读取），跳过。

2. 列出所有本地 `wt/*` 分支。
   - 检查对应 worktrack 是否在 `.servo/repo/worktrack-history.md` 或清理后的 backlog 中标记为 `done`。
   - 若已完成：删除本地分支（`git branch -d`）。
   - 若当前 active worktrack，跳过。

3. 白名单保护：
   - `develop`、`master`、`main`、`develop-aw`、`develop-servo`、`develop-main` 永不可删除。
   - 当前 active milestone branch（从 control-state 读取）永不可删除。
   - 当前检出的分支永不可删除。
   - 所有 `origin/*` remote-tracking 分支不参与清理。

### 3. Control-state 压缩

输出结构化清理报告，至少包含：

1. 读取 `.servo/control-state.md`、当前 `.servo/worktrack/contract.md`、`.servo/worktrack/plan-task-queue.md`、`.servo/repo/worktrack-backlog.md` 和 `.servo/repo/milestone-backlog.md`。
2. 执行 dry-run，输出：
   - 必须保留的 hydration-critical 字段组
   - 将折叠的历史重复行
   - 将写入的 compaction history artifact
   - 停止条件命中情况
3. 优先使用随包分发的 helper 执行 dry-run：
   - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/control_state_compact.py --control-state .servo/control-state.md --dry-run --json`
   - 若 dry-run 结果被人工确认，才可执行 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/control_state_compact.py --control-state .servo/control-state.md --apply --json`
4. helper 内置最小 preservation contract；安装后的技能运行时不得依赖源码仓库 `docs/` 路径。必须保留的字段组至少覆盖 current scope/function、active worktrack、active milestone、branch guard、review gate、approval boundary、continuation authority、handback guard、baseline traceability 和 autonomy ledger。
5. 可折叠内容仅限旧 `latest_closed_worktrack_commit`、旧 `verified_at`、旧 `last_stop_reason`、旧 handback note、旧 closeout 摘要和非当前路由所需的重复 checkpoint 叙述。
6. 若需要 externalized history，必须由本次 compact 操作生成 compaction history artifact，并记录 source checkpoint、created_at、preserved field summary 和 externalized sections。
7. 不得把 installer-generated backup/update artifacts 当作 history source、模板默认值、清理输入或 `handback_history_ref` 的默认目标。
8. 写入后重新读取 compacted control-state，验证 hydration-critical 字段可解析；验证失败时保留原文件并返回 blocked / recover 建议。

### 4. Runtime artifact 维护扫描

维护扫描是 report-first 流程，只观察 `.servo` runtime artifact inventory 和引用链，不删除、不移动、不归档。

1. 读取 `.servo` 下的 control-state、repo、milestone、worktrack、archive 和 history 文本 artifact。
2. 使用随包分发的 helper 生成 JSON 报告：
   - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/runtime_maintenance_sweep.py --servo-root .servo --json`
3. 报告至少覆盖：
   - 指向缺失 `.servo` artifact 的 stale reference
   - 已关闭 Worktrack 仍引用 rolling `.servo/worktrack/gate-evidence.md` 且缺少 stable closeout / bundle / snapshot / archive ref
   - 不在已知 `.servo` 层级且没有引用链的 orphan artifact
   - 未晋升、未退役、未归档、未保留且无人引用的 temporary discovery / evidence
   - 只有 prose summary、没有具体 SubAgent 或 command-output runtime artifact ref 的执行证据
4. helper 默认即使发现 findings 也返回 0，因为 findings 是 cleanup 决策证据，不是 cleanup 执行结果。只有显式传入 `--fail-on-findings` 时才把 findings 转成非零退出码。
5. 报告输出必须包含 `cleanup_executed: false`。任何 archive、move 或 delete action 都需要后续单独 approval 和专门 cleanup 流程。

### 5. 生成清理报告

输出结构化清理报告，至少包含：

- 清理前 backlog 条目数 / 清理后 backlog 条目数
- 已归档到 history 的条目列表
- 已删除的本地分支列表
- 被白名单保护的跳过分支列表
- control-state compaction dry-run/apply 状态和 post-verify verdict
- runtime artifact maintenance sweep finding counts and report ref
- 未处理的条目（如有）

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。

- **不删除 remote 分支**：本技能只操作本地分支（`git branch -d`），不执行 `git push --delete`。
- **不删除 artifact 文件**：`.servo/milestone/` 和 `.servo/worktrack/` 下的文件永不删除。
- **不删除 protected 分支**：develop、master、main 及 active milestone branch 永不可删除。
- **不删除未确认条目**：backlog 中 `active`、`blocked`、`deferred` 条目不参与清理。
- **`git branch -d` 而非 `-D`**：使用 safe delete，如果分支未完全合并则跳过并报告。
- **操作前必须 dry-run**：先输出将要执行的操作列表，等待确认后再执行。在非交互模式下，low-risk 清理（仅 backlog 清理）可自动执行。
- **操作后必须验证**：执行后重新读取 backlog 和 branch list，确认清理结果与预期一致。
- **control-state compact 不得改变权限语义**：压缩不得改变 approval、autonomy、dispatch、review gate、branch guard、protected branch 或 milestone/worktrack routing 语义。
- **history source 必须由 compact 操作生成**：installer-generated backup/update artifacts 只能作为排除对象或恢复线索，不能作为 canonical history reference。
- **active worktrack 场景更严格**：存在 active worktrack 时，Worktrack Contract、Plan / Task Queue 和当前 branch guard 必须可读；否则 compact 返回 blocked。
- **maintenance sweep 不授权 cleanup**：stale、orphan、expired、rolling evidence reuse 等 finding 只能进入报告；删除、移动或归档必须另走 approval。

## 预期输出

- `cleanup_type`：backlog_only / branches_only / control_state_compact / runtime_maintenance_sweep / full
- `backlog_before_count` / `backlog_after_count`
- `archived_entries`：已归档的 worktrack_id 列表
- `deleted_branches`：已删除的本地分支列表
- `skipped_branches`：被白名单保护的跳过分支
- `control_state_compaction`：dry-run/apply 状态、preserved fields、externalized sections、history artifact ref、post-verify verdict
- `runtime_maintenance_sweep`：cleanup_executed、artifact_count、finding_count、counts_by_type、counts_by_severity、findings、recommendations
- `errors`：清理过程中的错误
- `recommendations`：建议的后续动作
