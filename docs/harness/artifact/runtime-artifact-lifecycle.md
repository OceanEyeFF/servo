---
title: "Runtime Artifact 生命周期"
status: active
updated: 2026-06-30
owner: servo-kernel
last_verified: 2026-06-30
---
# Runtime Artifact 生命周期

本文定义 `.servo/` 生命周期内产生的文档、工作记录、临时发现、证据和运行记录如何被收容、固化、归档、标记为清理候选，或在后续单独批准后删除。它是 `.servo` 管理规则，不是通用仓库分层规则，也不是清理 runbook。

## 定位

`.servo/` 是当前仓库的运行时控制与证据层。它保存 control state、Milestone / Worktrack 运行记录、临时文档、临时 discovery、执行证据、dispatch 记录和 closeout trace。

`.servo` 里的内容默认不是正式文档。只有经过验证、确有必要被后续人或 agent 直接阅读的内容，才从 `.servo` 整理成正式文档；其余运行记录继续留在 `.servo` 的当前、历史或归档位置。本文不定义正式文档、源码或测试脚本自身的生命周期。

## 层级绑定

`.servo` 产物的生命周期必须先和 `.servo` 内部层级绑定，不能只按“临时文件”粗暴处理：

| 层级 | 承接内容 | 生命周期责任 |
| --- | --- | --- |
| `.servo/worktrack/` | 当前 Worktrack 的滚动 contract、queue、gate evidence | Worktrack closeout 前必须把会被历史引用的 evidence / findings / discovery 固化到 closeout record、bundle、snapshot 或 archive |
| `.servo/milestone/` | 单个 Milestone 的定义、progress、Gate verdict、axis report、closeout records、manual exception | Milestone 结束清理时聚合并保留最终验收链；不再活动但仍被 history / docs / follow-up 引用的文件进入 preserved 或 archive |
| `.servo/repo/` | milestone backlog、worktrack backlog、snapshot、intake review、append request | Repo cleanup 负责清理跨 Milestone 的 stale/orphan/superseded 候选；live pipeline 文件只保留当前可行动视图 |
| `.servo/archive/` | 已归档的 milestone、worktrack、discovery、SubAgent output、command-output | 只保存带来源、目标、时间、原因和引用处理记录的归档项；不是垃圾桶 |
| 正式文档层 | 从 `.servo` 中整理出的必要内容 | 只接收已验证且需要长期呈现的内容；不能直接引用未固化的 rolling evidence 当历史证明 |

临时文件的默认路径也要遵守层级：Worktrack 临时文档和 discovery 先归当前 Worktrack；Milestone 级聚合发现归当前 Milestone；跨 Milestone 或 pipeline 级判断归 `.servo/repo/`。只有完成分类后，才进入 `.servo/archive/`，或被整理成必要的正式文档。

## Artifact 分类

| 类别 | 例子 | 生命周期 |
| --- | --- | --- |
| control-state | `.servo/control-state.md`、`.servo/control-state-repo.md`、`.servo/control-state-wt.md`、`.servo/operator-config.md` | 当前路由依赖的活动运行状态；向前压缩，不在当前路由仍引用时归档 |
| milestone runtime record | `.servo/milestone/MS-*.md`、Gate verdict、closeout record、axis report、manual exception | 被 backlog、history、manual exception、follow-up milestone 或 Gate evidence 引用期间必须保留 |
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
| promoted | `.servo` 中的已验证内容已经被整理成必要的正式文档 | runtime 来源可以归档，但不能静默删除 |
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
   - `Discovery` 必须分类：确有长期呈现价值的内容整理成正式文档；只支撑本轮判断的 discovery 归档或并入 evidence；未验证假设不得写成正式文档。
2. Milestone 结束清理：
   - 已关闭 Worktrack 的 evidence / findings / discovery 按 milestone 聚合检查。
   - Milestone Gate、axis report、final acceptance、manual exception、closeout record 和被引用 evidence 默认保留。
   - 已晋升事实的临时 discovery、已解决 finding、重复命令输出可列入归档候选。
   - 仍影响后续工作的 finding 必须转成新 Milestone、append request、backlog 条目或 docs 中的明确风险说明。
3. Repo cleanup：
   - Repo 级 cleanup 只处理跨 Milestone 的 stale、orphan、superseded、expired 候选。
   - cleanup 先生成 sweep report，列出 source path、引用链、建议动作和风险；不能直接删除。
   - 删除、批量移动或破坏性清理必须单独获得批准。

## Milestone 文件生命周期

Milestone 相关文件不只是一份 `MS-*.md`。它们共同构成 Milestone 级验收链：

| 文件类型 | 例子 | 生命周期说明 |
| --- | --- | --- |
| Milestone 主文件 | `.servo/milestone/MS-20260630-002.md` | active 期间作为 progress 与 completion signals 的控制事实；final acceptance 后转为 preserved，并由 milestone history / closeout record 引用 |
| Closeout records | `.servo/milestone/MS-*-closeout-records.md` | 保存每个已关闭 Worktrack 的合并、验证、证据与 remaining risks；Milestone 结束后默认保留 |
| Gate verdict | `.servo/milestone/MS-*-gate-verdict.md` | 保存 Milestone Gate 聚合判定；即使 final acceptance 采用 manual exception，也不能改写或删除原 verdict |
| Axis reports | `.servo/milestone/MS-*-blackbox-report.md` 等 | 保存 sibling axis 的独立检查结果；被 Gate verdict 引用期间必须保留，可在 Milestone 结束后按 milestone 目录归档 |
| Dispatch profile | `.servo/milestone/MS-*-axis-dispatch-profile.md` | 保存 Gate 轴分派和 carrier isolation 事实；与 axis reports / Gate verdict 同生命周期 |
| Intake / append / follow-up refs | `.servo/repo/pre-milestone-intake-*.md`、`.servo/repo/append-request-*.md` | 若只用于创建该 Milestone，Milestone 结束后可作为 preserved evidence 或 archive 候选；若影响后续 Milestone，必须留在 repo 层可追溯位置 |

Milestone final acceptance 后，清理顺序是：

1. 将 live milestone backlog 条目移入 milestone history，或确认 history 已有完整条目。
2. 确认 Worktrack closeout records 覆盖所有已决 Worktrack。
3. 确认 Gate verdict、axis reports、dispatch profile、manual exception 和 final acceptance record 被稳定引用。
4. 将已整理成正式文档的临时 discovery、重复命令输出、过期 scratch material 写入 maintenance sweep report。
5. 只在引用链完整、风险已说明、且获得 cleanup approval 后，才执行删除或批量移动。

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
4. 将确有必要长期呈现的内容整理成正式文档。
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

当 runtime artifact 含有仍需要长期呈现的内容时，必须先整理成正式文档，才能把原 runtime artifact 视为 stale 或 expired。
