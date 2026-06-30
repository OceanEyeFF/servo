---
title: "Runtime Artifact 生命周期"
status: active
updated: 2026-06-30
owner: servo-kernel
last_verified: 2026-06-30
---
# Runtime Artifact 生命周期

本文定义 `.servo/` runtime artifact 的生命周期策略。它是 Harness artifact 合同，不是清理 runbook：它说明什么可以保留、归档、晋升、标记为候选项，或在后续单独批准后删除。

## 定位

`.servo/` 是当前仓库的运行时控制与证据层。它保存 control state、Milestone / Worktrack 运行记录、临时 discovery、执行证据、dispatch 记录和 closeout trace。

长期项目真相不能只留在 `.servo/`：

- Harness doctrine、workflow policy、artifact contract 晋升到 `docs/harness/`。
- 项目维护、deploy、governance、usage-help 真相晋升到 `docs/project-maintenance/`。
- 可执行实现合同落在 `product/` 或 `toolchain/`。

## Artifact 分类

| 类别 | 例子 | 生命周期 |
| --- | --- | --- |
| control-state | `.servo/control-state.md`、`.servo/control-state-repo.md`、`.servo/control-state-wt.md`、`.servo/operator-config.md` | 当前路由依赖的活动运行状态；向前压缩，不在当前路由仍引用时归档 |
| milestone runtime record | `.servo/milestone/MS-*.md`、Gate verdict、closeout record、axis report | 被 backlog、history、manual exception 或 Gate evidence 引用期间必须保留 |
| worktrack runtime record | `.servo/worktrack/contract.md`、`plan-task-queue.md`、`gate-evidence.md` | 当前 Worktrack 的滚动文件；历史引用依赖它们之前，必须生成 snapshot、closeout bundle 或归档副本 |
| worktrack evidence | Gate evidence、closeout evidence bundle、dispatch record、test output 摘要 | 支撑 Gate / closeout / Milestone Gate 的证据；默认保留，Milestone 结束后可归档但不能静默删除 |
| worktrack findings | review findings、Gate findings、blocking findings、remaining risks | 已验证且仍有行动价值的 finding 晋升为 backlog / append request / docs 真相；已解决或过期的 finding 进入 report-first cleanup 候选 |
| worktrack discovery | 临时理解、探索记录、命令摘要、scratch intake material | Worktrack closeout 前分类：晋升、并入 evidence、归档或标记 stale；Milestone 结束清理和 repo cleanup 再处理遗漏项 |
| repo runtime record | `.servo/repo/milestone-backlog.md`、`worktrack-backlog.md`、`snapshot-status.md`、intake review | 保留活跃 pipeline 记录；只有经过 report-first maintenance 才能压缩 stale 条目 |
| execution output | SubAgent raw output、command log、diagnostic output | 被引用为证据时保留；有参考价值但不是 canonical truth 时归档；只有报告和批准后才能过期删除 |

## 生命周期状态

| 状态 | 含义 | 允许转移 |
| --- | --- | --- |
| active | 当前控制路由或当前 Worktrack 正在消费 | 原地保留 |
| preserved | 审计、Gate、closeout、manual exception 或历史追溯仍需要 | 保持稳定路径，或归档并同步引用/redirect |
| promoted | 已验证事实已经晋升到 `docs/`、`product/` 或 `toolchain/` truth owner | runtime 来源可以归档，但不能静默删除 |
| superseded | 已被更新 runtime artifact 替代，不再是权威来源 | 作为归档候选进入 maintenance report |
| stale | 与当前 control state、git checkpoint 或 canonical docs 冲突 | 作为维护候选报告，行动前需要确认 |
| expired | 临时记录过了保留期，且没有 evidence 引用 | 删除仍需要显式 cleanup 批准 |

## Worktrack Evidence / Findings / Discovery

Worktrack 相关运行产物按用途分成三类处理：

- `Evidence`：用于证明 Worktrack 已完成、Gate 可判定或 closeout 可追溯的材料。包括 gate evidence、closeout evidence bundle、dispatch provenance、测试结果摘要、关键命令输出引用。
- `Findings`：审查、验证、Gate 或人工复核得到的发现。包括 blocking finding、remaining risk、known external debt、replan recommendation。
- `Discovery`：执行过程中的临时理解和探索材料。包括 scratch notes、命令观察、上下文梳理、候选方案和未验证假设。

这些产物的生命周期分三段：

1. Worktrack closeout：
   - `Evidence` 必须被写入稳定 closeout record、bundle 或 snapshot，避免后续 `.servo/worktrack/*` 滚动文件覆盖后丢失历史证据。
   - `Findings` 必须分流：仍需行动的 finding 写入 backlog、append request、follow-up Worktrack 或 remaining risks；已经解决的 finding 跟随 closeout record 保留。
   - `Discovery` 必须分类：已验证事实晋升到 docs/product/toolchain；只支撑本轮判断的 discovery 归档或并入 evidence；未验证假设不得写成长期真相。
2. Milestone 结束清理：
   - 已关闭 Worktrack 的 evidence / findings / discovery 按 milestone 聚合检查。
   - Milestone Gate、axis report、final acceptance、manual exception、closeout record 和被引用 evidence 默认保留。
   - 已晋升事实的临时 discovery、已解决 finding、重复命令输出可列入归档候选。
   - 仍影响后续工作的 finding 必须转成新 Milestone、append request、backlog 条目或 docs 中的明确风险说明。
3. Repo cleanup：
   - Repo 级 cleanup 只处理跨 Milestone 的 stale、orphan、superseded、expired 候选。
   - cleanup 先生成 sweep report，列出 source path、引用链、建议动作和风险；不能直接删除。
   - 删除、批量移动或破坏性清理必须单独获得批准。

## 归档路径

归档路径应保留足够身份信息，使历史引用仍可读：

```text
.servo/archive/
  milestone/<milestone_id>/
  worktrack/<worktrack_id>/
  discovery/<YYYYMMDD>/<slug>/
  subagent/<worktrack_id>/<carrier_id>/
  command-output/<YYYYMMDD>/<slug>/
```

移动 artifact 到 archive 是生命周期状态转移。必须记录 source path、destination path、原因、时间戳，以及哪些引用已更新或被明确保留不改。

## 保留规则

以下 artifact 默认不得删除：

- Milestone Gate verdict、axis report、closeout record、manual exception record、final acceptance record。
- Gate 或 closeout 使用过的 Worktrack contract、gate evidence、closeout evidence bundle、dispatch record、SubAgent record。
- 仍被当前 milestone status、milestone history 或 control state 引用的 repo backlog / history 条目。
- 被 docs truth、governance check、release note 或 manual exception follow-up record 引用的 evidence。

`.servo/worktrack/gate-evidence.md` 这类滚动文件不能直接当作历史证明使用，除非 closeout record、bundle 或 archive snapshot 保留了该 Worktrack 当时使用的版本。

## 维护周期

维护周期在已验证 closeout 之后，或显式 repo maintenance pass 中运行：

1. 观察 runtime artifact inventory 和引用链。
2. 将候选项分类为 preserve、promote、archive、stale、superseded、expired 或 unknown。
3. 在改动前产出 maintenance sweep report。
4. 将已验证长期事实晋升到正确 docs 或 implementation owner。
5. 只有保留 traceability 时才归档。
6. 删除或破坏性 cleanup 前请求单独批准。

Report-first maintenance 可以识别删除候选，但不执行删除。cleanup execution 是单独审批边界。

## 检查项

维护检查应能发现：

- 滚动 evidence 未 snapshot / bundle 就被历史引用。
- 指向缺失 Milestone / Worktrack artifact 的 stale reference。
- 无法从 backlog / history / control-state 追溯的 orphan artifact。
- 从未晋升或退役的临时 discovery。
- 仅被 prose summary 引用的 SubAgent 或 command-output evidence。
- 已归档 artifact 的 source reference 没有更新，也没有显式说明保留原因。

这些检查只提供 cleanup 决策证据；检查本身不授权 cleanup。

## 边界

本策略不授权 release、publish、tag、remote push、deploy、protected branch mutation、secret handling、database migration、external side effect 或 destructive cleanup。

当 runtime artifact 含有已验证长期事实时，必须先把事实晋升到合适的 truth owner，才能把 runtime artifact 视为 stale 或 expired。
