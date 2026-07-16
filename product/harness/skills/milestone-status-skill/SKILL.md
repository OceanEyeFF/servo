---
name: milestone-status-skill
description: 当 Harness 处于 RepoScope 且需要分析当前活跃 Milestone 的进度、验收状态和是否触发 handback 边界时使用这个技能；它是 RepoScope.Observe 的传感器/分析器，不选择下一 Worktrack、不初始化 worktrack、不修改 version/release 状态。
---

# Milestone 状态技能

## 概览

把这个技能作为 `Codex` 中 `RepoScope` 下的 Milestone 聚合观测/验收分析器使用。

本技能实现 `RepoScope.Observe` 状态的 Milestone 维度传感器算子，对应 Harness 控制回路中状态估计阶段的 Milestone 专项分析。它通过读取当前活跃 Milestone、Worktrack backlog 中的 Candidate contribution、`finished-handback.yaml`、Repo snapshot 和独立 Milestone axis results，执行 `worktrack_list_finished + Milestone Gate + purpose_achieved` 判定链。

它的角色是分析 Milestone 状态。它产出的是经过聚合计算的 Milestone 观测结果，供 `RepoScope.Decide` 算子（如 repo-whats-next-skill）和 `harness-skill` 的 continuous execution 判断使用。

它的主要观测依据是 Milestone 级产物和工作追踪边界证据：

- 当前活跃 Milestone artifact（`.servo/milestone/{milestone_id}.md`）
- Worktrack backlog（`.servo/repo/worktrack-backlog.md`）
- Candidate finished handback refs and structured Close results recorded by Repo Refresh
- Milestone-owned independent axis reports and Gate result
- Repo snapshot（`.servo/repo/snapshot-status.md`）

本技能对 `.servo/worktrack/*` 的唯一合法行为是读取为边界证据；更新或重写 `.servo/worktrack/*` 的行为必须标记为超出本技能权限。本技能不对 Milestone artifact 执行写入操作 —— 进度计数器的更新应由上游调用方（如 harness-skill）在收到本技能输出后决策执行。

## 何时使用

当需要了解当前 Milestone 进展到哪一步、是否已达到验收边界时，使用这个技能：

- 在 `RepoScope.Observe` 阶段，harness-skill 需要 Milestone 级别的状态估计
- Worktrack closeout 后，repo-refresh 完成后需要检查 Milestone 进度是否推进
- Programmer 显式请求 Milestone 状态检查（如"Milestone X 完成了多少？"）
- Continuous execution 流程中需要判断是否触发 handback 边界
- 在 `repo-whats-next-skill` 决策前需要 Milestone 验收状态作为依据
- 需要聚合多个 worktrack 的 evidence 来判定 Milestone 目的是否达成

## 工作流

1. 确认这是一轮 Milestone 状态分析轮次，不是工作追踪分派、下一步决策或直接执行。
2. 识别当前活跃 Milestone：从 Harness 控制状态或 repo snapshot 中获取当前 active milestone_id。
3. 读取 Milestone artifact（`.servo/milestone/{milestone_id}.md`），解析其字段结构（worktrack_list、completion_signals、acceptance_criteria、completion_threshold_pct、progress_counter、depends_on_milestones、milestone_review_gate 等）。若 `completion_threshold_pct` 缺失，按默认值 `100` 解释。
3a. 检查 Milestone Review Gate：goal-driven milestone 在调用 Candidate PlanWork normal entry 前必须存在至少一次有效复核。该复核来自 `pre_milestone_intake_review` 的 `milestone_review_gate_handoff`。只有 `milestone_review_count >= 1`、`latest_review_status = effective_pass`、`effective_review_pass = true` 且 `latest_review_checkpoint` 非空时才算通过。`skipped`、`questions_required`、`blocked`、`missing`、`stale`、`invalidated` 或字段不全必须返回 `proceed_blockers`，不得当成 review pass。若 `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化导致 `review_invalidated_by` 非空，必须要求 fresh `pre_milestone_intake_review`。旧 `.servo` artifact 缺少 additive review/backfill 字段时，执行 conservative runtime backfill：默认 `milestone_review_count = 0`、`latest_review_status = missing`、`effective_review_pass = false`、`latest_review_checkpoint = N/A`，状态为 `blocked` / `not ready`；backfill forward-only，preserve existing observed facts，must not grant permissions，must not infer programmer confirmation，must not increment counters，must not create `effective_pass`，must not enable PlanWork。
4. 读取 Worktrack backlog（`.servo/repo/worktrack-backlog.md`）：若文件不存在，视为空 backlog，`total` 仍取自 Milestone artifact 的 `worktrack_list`。若文件存在但不能解析为包含 `worktrack_id` 与 `status` 的条目，或状态不是 `done / blocked / deferred`，必须命中正式停止条件，不得使用部分解析结果。可解析时按 `worktrack_id` 去重并保留最新条目，Candidate progress 只做 `done → completed`、`blocked → blocked`、`deferred → deferred` 映射。
5. 读取并派生 Candidate contribution：以 active Milestone 的 `worktrack_list` 为 membership truth，按精确 `worktrack_id` 连接 backlog 中的最新条目。只有条目 `milestone_id` 与 active Milestone 一致、原始状态为 `done`，且具有 concrete `finished_handback_ref`、`accepted_checkpoint` 和 `closeout_checkpoint_commit` 时，才建立 completed contribution。解析 handback，仅确认 identity、`outcome: completed`、acceptance summary、residuals、merge result 和 stable evidence refs 可读。membership、identity 或必需 refs 不一致时阻塞；不得读取 `.servo/tmp` round chain，也不重放 Close transaction或重新判断 Worktrack acceptance。
6. 读取 repo snapshot（`.servo/repo/snapshot-status.md`），获取当前 repo 基准状态和治理信号。
7. 检查前置 Milestone 依赖：若 `depends_on_milestones` 非空，验证前置 Milestone 是否已完成。
8. 计算 Milestone 进度计数器：
   - 遍历 `worktrack_list`，按精确 `worktrack_id` 和匹配 `milestone_id` 对照 backlog，使用上述只读派生结果统计 total / completed / blocked / deferred 数量
   - 计算 `completion_pct`
9. 执行双重验收检查（受 `milestone_kind` 控制）：
   - 读取 Milestone artifact 的 `milestone_kind` 字段，默认值 `goal-driven`
   - **goal-driven**：执行完整双重验收
     - **worktrack_list_finished**：声明的 worktrack 列表是否全部处理（已完成 / 被明确移出 / 阻塞有决策）
     - **Milestone Gate**（`worktrack_list_finished == true` 时）：准备一份共同事实基础并请求顶层 Harness 分别执行四个互相不可见的 sibling axis carriers，再调用 `milestone-gate` 聚合显式 `axis_reports`。本技能不分派 SubAgent；`milestone-gate` 也不创建 axis carrier。Gate 必须在 `purpose_achieved` 判定前完成。
     - **purpose_achieved**：Milestone 原始目的是否经聚合 evidence 证明达成（对照 `completion_signals`、`acceptance_criteria` 和 `completion_threshold_pct`，按 `purpose_achieved 操作化判定` 章节逐条验证）
   - **work-collection**：执行单重验收
     - **worktrack_list_finished**：同上
     - **purpose_achieved**：显式声明跳过（恒为 true）。记录："work-collection milestone，验收下沉到各 Worktrack 独立 Review 与 Close"
   - `verification_model_used`：`dual`（goal-driven）或 `single`（work-collection）
10. 根据验收结果判定 `milestone_acceptance_verdict`：
    - `achieved`：
      - goal-driven：worktrack_list_finished 且 `milestone_gate_verdict == "pass"` 且 `signal_satisfaction_pct >= completion_threshold_pct` 且 `criteria_pass_pct >= completion_threshold_pct`
      - work-collection：worktrack_list_finished == true
    - `not_achieved`：worktrack 列表未处理完成，或（goal-driven）Milestone Gate 已通过但目的未达成
    - `blocked`：存在不可推进的阻塞项，或 goal-driven 的 `Milestone Gate` 未通过 / 证据不足 / 命中反作弊信号
    - `deferred`：存在被明确推迟的 worktrack 且不影响目的达成判定
11. 判断 `handback_required`：
    - goal-driven：当 `milestone_acceptance_verdict` 为 `achieved` 或 `blocked` 时，触发 Milestone 验收边界，handback 为 true；若 `worktrack_list_finished == true` 但 `purpose_achieved == false`，也应在 `recommendations` 中显式提示 handback 做 milestone 重新评估，避免静默 scope creep
    - work-collection：始终为 false（即使 achieved 也不触发 handback）
12. 给出 `release_version_consideration` hint：基于 Milestone 目的达成情况和 completion_signals 满足程度，给出对 version bump 或 release 的提示性建议（不接管 decision）。
13. 明确 `developer_decisions_needed`：列出必须由 developer 做出的决定（如"前置依赖未完成，是否跳过"、"purpose_achieved 存疑，是否手动判定"等）。
14. 生成 `recommendations`：对 `RepoScope.Decide` 的建议（如"建议 handback 让 developer 验收"、"建议推进到下一 Milestone"、"建议补充 evidence 后重新检查"）。
15. 向 Harness 返回结构化的 Milestone 状态报告。
16. 如果没有命中正式停止条件，允许监督器直接进入下一个合法判定。

当 goal-driven milestone 的 `worktrack_list_finished == true` 时，顶层 Harness 必须从共同事实基础分别创建 blackbox、whitebox、anticheat 和 composite 输入包。每个 axis 只看到自己的输入和允许读取的 repo/source/evidence，不能看到 sibling report、verdict、finding 或 conclusion。只有 `milestone-gate` 聚合四个独立 axis reports。

`milestone_acceptance_verdict == achieved` 要求 Milestone Gate pass，且不存在未解决的 veto、blocked axis、high-severity finding 或 programmer 尚未接受的 follow-up requirement。

### 文档 Freshness Warning（非阻断）

在 Milestone 验收分析中，文档不完善作为 **warning**（非 blocking）项处理，不影响 `milestone_acceptance_verdict` 的判定，但必须在 `doc_freshness_warning` 字段中显式暴露。

**检查维度**：

1. **Stale frontmatter**：检查 `docs/` 下正文文档的 `last_verified` 是否逾期（与当前日期相差超过 90 天，或与 milestone 涉及的内容域明显不匹配）。
2. **Broken cross-references**：检查 milestone scope 内涉及的文档是否存在死链（引用已被删除或重命名的文件/章节）。
3. **Missing required docs**：检查 milestone 涉及的 skill/adapter/contract 变更是否有匹配的文档记录。

**输出规则**：

- 若不存在文档问题：`doc_freshness_warning` 为 `N/A`
- 若存在 warning 级问题：在 `doc_freshness_warning` 中逐条列出，格式 `[文件路径] 问题描述`
- `doc_freshness_warning` 不得单独触发 `handback_required`，不得将 `milestone_acceptance_verdict` 从 `achieved` 降级，但应在 `recommendations` 中建议后续 worktrack 跟进
- 若存在严重文档问题（如关键 contract 文档缺失或内容与实际实现矛盾），应在 `developer_decisions_needed` 中暴露供 programmer 判断

## 正式停止条件

至少在以下任一条件成立时停止并返回控制权：

- 当前无活跃 Milestone（Milestone artifact 不存在或 status 非 active）
- Milestone artifact 关键字段缺失或损坏，无法执行有效分析
- Worktrack backlog 文件存在但损坏、不可读或不可按合同解析；包括无法提取 `worktrack_id` / `status`、状态值不在 `done / deferred / blocked`、frontmatter / markdown 结构损坏，或只能得到部分可信条目的情况
- Worktrack backlog 与 Milestone 声明的 worktrack_list 之间存在不可自动解决的矛盾
- 前置 Milestone 依赖未完成，且无法自动判定是否应阻塞当前 Milestone
- Milestone Review Gate 缺失、`milestone_review_count < 1`、`latest_review_status` 不是 `effective_pass`、`latest_review_checkpoint` 为空，或 intake 状态为 `skipped` / `questions_required` / `blocked` / `missing` / `stale` / `invalidated`
- Conservative runtime backfill 后仍为 missing/blocked/not ready 的 additive `.servo` 字段，或任何需要 approval、dispatch、review pass、effective pass 的字段缺少 verified evidence / programmer confirmation
- `worktrack_list`、`completion_signals`、`acceptance_criteria`、scope/non-goals 或 risk boundary 变化使 Milestone Review Gate checkpoint 失效
- `Milestone Gate` 所需的 black-box / white-box / anti-cheat / composite axis reports 缺失、过期、隔离被破坏或互相冲突，导致无法做出可信集成判定
- `Milestone Gate` 命中 `soft-fail` / `hard-fail` / `blocked` 或反作弊告警，且当前轮无合法自动恢复路径
- 双重验收检查中 `purpose_achieved` 的判断需要 developer 主观裁定，且无足够的自动判定依据
- 聚合 evidence 不足以支撑 purpose_achieved 判定，且无法通过限定范围探查补全
- Milestone 依赖的 artifact 跨域或以当前权限不可访问
- 观察依据缺失、过期或相互矛盾到足以让 Milestone 验收判定只能靠猜

## `milestone_input_checkpoint` 计算规则

`milestone_input_checkpoint` 是 Milestone Observe 的输入指纹，不是进度计数本身。它必须使用确定性算法生成，供下一轮 Observe 判断是否可以跳过重新计算 progress counter 和 purpose evidence 聚合。

- 哈希类型：使用 SHA-256；输出格式固定为 `sha256:<64 位小写 hex>`。
- **Fallback 策略**：如果运行环境不支持 SHA-256 哈希计算（如 AI 模型无法执行字节级哈希），使用以下 fallback：
  - 将输入指纹序列化为 JSON 字符串，标注 `hash_algorithm: "none"`
  - 标记 checkpoint 为 `unverifiable`（`checkpoint_verifiable: false`）
  - 不跳过 progress counter 和 purpose evidence 的完整重算（`skip_recalculation: false`）
  - 在 `milestone_input_checkpoint` 字段输出格式为 `unverifiable:<json_string_length>`，并附带完整序列化 JSON 字符串供人工比对
- 序列化格式：构造一个 JSON 对象，使用 UTF-8 编码、字典键按字典序排序、紧凑分隔符（无多余空白）序列化后取 SHA-256。所有 repo 内路径必须规范化为 repo-relative POSIX path；不得使用绝对路径。
- 顶层字段：`schema_version` 固定为 `milestone-input-checkpoint/v1`，并包含 `active_milestone_id`、`milestone_artifact`、`worktrack_backlog`、`worktrack_contributions`、`milestone_axis_reports`、`repo_snapshot`。
- `milestone_artifact` 输入字段：artifact path、`milestone_id`、`status`、`worktrack_list`（保持 Milestone 声明顺序）、`completion_signals`、`acceptance_criteria`、`completion_threshold_pct`、`depends_on_milestones`、Milestone-owned stable evidence refs。不得纳入由本技能或上游刷新产生的 `progress_counter`、前次 `milestone_input_checkpoint` 或分析时间戳。
- `worktrack_backlog` 输入字段：backlog path、`state`（`missing` / `present`）、以及按 `worktrack_id` 字典序排列的最新有效条目。文件缺失时写入 `state: missing` 与空 entries；文件存在时必须先完成解析、Candidate 状态分类和按 `worktrack_id` 去重，条目字段至少包括 `worktrack_id`、分类后的 `status`（completed / blocked / deferred）、`node_type`、`milestone_id`、`finished_handback_ref`、`accepted_checkpoint`、`closeout_checkpoint_commit` 和 Repo Refresh handoff summary。backlog 存在但损坏或不可解析时不得生成 partial checkpoint，必须停止并返回 `proceed_blockers`。
- `worktrack_contributions` 输入字段：它是从 active Milestone `worktrack_list` 与 matching-`milestone_id` backlog entry 只读派生的集合，不是 Milestone artifact 中的第二份状态。只纳入原始状态为 `done` 且通过 Candidate handback 检查的 Worktrack，按 Worktrack id 排序，包含 `finished_handback_ref`、`accepted_checkpoint`、`closeout_checkpoint_commit`、acceptance summary、residuals、merge result 和 stable evidence refs。`milestone_axis_reports` 仅在四个 sibling runs 完成后纳入各自 report ref、verdict、applicability 和 evidence refs；任一 contribution 或 axis report 变化都触发完整重算。
- `repo_snapshot` 输入字段：snapshot path、`baseline_branch`、`last_verified_checkpoint`、`checkpoint_type`、`checkpoint_ref`、当前 active milestone 指针（如有）、治理状态、已知问题与风险标识。不得纳入纯展示性更新时间、文件 mtime 或本轮分析时间。
- Markdown 解析规范：从 frontmatter、表格、列表和 keyed lines 中提取字段时，字段名应先规范化为小写 snake_case；字符串 trim 首尾空白；列表中本来有业务顺序的字段保持原顺序，其余 map/object 键排序；缺失可选字段用 `null`，不得省略同一 schema 下的键。
- 重算时机：每次 RepoScope.Observe 至少重新计算该输入指纹；若已存 `milestone_input_checkpoint` 与新指纹一致，且 `latest_observed_checkpoint` 与当前 `git rev-parse HEAD` 一致，才允许跳过 progress counter 和 purpose evidence 的完整重算。任一输入源的存在状态、路径集合、上述纳入字段、active milestone、schema_version 或 stored checkpoint 变化时，都必须完整重算并返回新的 checkpoint。

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。

- 不膨胀 harness-skill：harness-skill 继续只做 supervisor，本技能是独立的 Milestone 分析器，由 harness-skill 在需要时调用。
- Milestone 完成判定必须通过双重验收模型（worktrack_list_finished + purpose_achieved）：goal-driven milestone 两者缺一时不得自动判定完成。work-collection milestone 仅需 worktrack_list_finished，purpose_achieved 声明跳过，验收下沉到各 worktrack Gate。
- `Milestone Gate` 是所有 Worktrack 关闭后、`purpose_achieved` 前的独立集成验收层；它不能替代 Worktrack Review，也不能把上层集成失败回写成单个 Worktrack 的通过。
- Milestone 是 RepoScope 下的聚合观测变量，不是第三 Scope：不得创建独立 Scope、不得创建独立状态转移路径。
- `developer_decisions_needed` 中的项目不得由本技能自动判定；它们必须作为显式边界交还给 developer。
- 如果 `depends_on_milestones` 中的前置 Milestone 未完成，必须标记为 blocked 并在 `developer_decisions_needed` 中列出是否跳过前置依赖的决策。
- 仅当 `milestone_input_checkpoint` 已存在且与当前输入指纹一致、同时 `latest_observed_checkpoint` 与当前 `git rev-parse HEAD` 一致时，才可跳过 progress counter 重算。仅 git HEAD 一致不足以跳过（`.servo/` 下运行时 artifact 不受 git 追溯）；backlog present-but-damaged / unparseable 时不得产出 partial checkpoint。
- `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct` 任一发生变化，必须触发完整 milestone 重新评估；不得沿用旧的 `purpose_achieved`、`milestone_gate_verdict` 或 `milestone_input_checkpoint` 直接放行。
- 仅追加 worktrack 且 programmer 已确认其归属当前 milestone 时，可不因 append 动作本身触发 milestone 重新评估；但若 append 同时修改 `completion_signals`、`acceptance_criteria` 或 `completion_threshold_pct`，仍必须重新评估。

## 预期输出

使用这个技能时，产出一份至少包含以下章节的 Milestone 状态报告：

- `Milestone 基本信息`
- `进度计数`
- `双重验收检查`
- `验收判决`
- `Handback 判定`
- `Release/Version 提示`
- `Developer 决策边界`
- `建议`
- `交接给 Harness`

结果中至少应包含以下字段或等价表达：

- `milestone_id`
- `milestone_title`
- `milestone_kind`：goal-driven / work-collection
- `completion_threshold_pct`：integer，默认 `100`
- `verification_model_used`：dual / single
- `milestone_status`：planned / active / completed / superseded
- `milestone_review_gate_status`：effective_pass / questions_required / blocked / skipped / missing / stale / invalidated
- `milestone_review_count`：integer
- `latest_review_checkpoint`：string
- `effective_review_pass`：boolean
- `conservative_runtime_backfill`：若发生缺字段降级，记录 `false` / `unknown` / `missing` / `blocked` / `not ready` / `N/A` 默认值、gap 证据与未扩大权限结论
- `progress`：
  - `total`：声明的 worktrack 总数
  - `completed`：原始 backlog 状态为 `done` 且具有有效 Candidate handback 的 Worktrack 数
  - `blocked`：被阻塞的 worktrack 数
  - `deferred`：被明确推迟的 worktrack 数
  - `completion_pct`：完成百分比
- `worktrack_list_finished`：boolean
- `milestone_gate_verdict`：pass / soft-fail / hard-fail / blocked / skipped — 来自 `milestone-gate` 输出
- `milestone_gate_summary`：来自 `milestone-gate` 输出的聚合摘要
- `aggregation_rules_applied`：boolean — 来自 `milestone-gate` 输出
- `aggregation_rules_missing`：boolean — 来自 `milestone-gate` 输出
- `per_worktrack_weights`：array — 来自 `milestone-gate` 输出
- `contradiction_findings`：array — 来自 `milestone-gate` 输出
- `contradiction_blocked`：boolean — 来自 `milestone-gate` 输出
- `axis_reports`、`axis_report_status`、`axis_dispatch_profile`、`axis_satisfaction`：来自 `milestone-gate` 输出
- `degenerate_and_applied`：boolean — 来自 `milestone-gate` 输出
- `degenerate_and_reason`：string | N/A — 来自 `milestone-gate` 输出
- `gate_blockers`、`gate_evidence_refs`：来自 `milestone-gate` 输出
- `finished_handbacks_by_worktrack`：每个 `done` Candidate contribution 的 handback ref、`accepted_checkpoint`、`closeout_checkpoint_commit`、acceptance summary、residuals、merge result 和 stable evidence refs
- `milestone_gate_axis_dispatch_required`：boolean
- `required_axes`：固定为 blackbox / whitebox / anticheat / composite
- `common_axis_input`：Milestone objective/configuration、相关 initial requirement、finished handback、`accepted_checkpoint`、`closeout_checkpoint_commit`、stable evidence refs 和每轴允许的 repo/source read scope
- `purpose_achieved`：boolean
- `signal_satisfaction_pct`：number
- `criteria_pass_pct`：number
- `milestone_acceptance_verdict`：achieved / not_achieved / blocked / deferred
- `handback_required`：boolean
- `release_version_consideration`：string
- `developer_decisions_needed`：array of strings
- `doc_freshness_warning`：array of strings / N/A — 文档不完善 warning 项（非阻断），逐条列出 stale frontmatter、broken cross-references、missing required docs
- `recommendations`：array of strings
- `depends_on_status`：前置 Milestone 检查结果（如有）
- `aggregated_evidence_summary`：聚合 evidence 摘要
- `missing_finished_handback_refs`：状态为 `done` 但缺失或不可解析 Candidate handback 的 Worktrack 列表
- `analysis_timestamp`：分析时间戳
- `input_artifacts_used`：使用的输入 artifact 列表及各自的时效性
- `observation_ready`：当前观察是否足以支撑下游判定
- `can_proceed`：boolean
- `proceed_blockers`：阻止推进的因素列表
- `handoff_signal`：交接信号
- `requires_developer_decision`：boolean
- `milestone_input_checkpoint`：本次分析按 `milestone-input-checkpoint/v1` 算法计算出的 `sha256:<hex>` 输入指纹，供 harness-skill 写入 control-state 的 `Baseline Traceability.milestone_input_checkpoint`，下一轮 Observe 用于幂等性对比
- `pipeline_advancement`：若当前 milestone `achieved`，推荐激活的下一个 milestone_id（从 live milestone-backlog 中按 priority 选取满足前置条件的 planned milestone；前置依赖可由 milestone-history 中 completed/superseded 条目满足）
- `pipeline_state`：Pipeline aggregate 快照（planned/active 来自 live milestone-backlog，completed/superseded 来自 milestone-history）
- `writeback_required`：boolean — 是否需要 harness-skill 执行写回
- `writeback_instructions`：object — 包含 `milestone_artifact_updates`（需更新的 milestone artifact 字段）、`control_state_updates`（需写入 control-state 的字段）、`backlog_updates`（需 upsert 到 milestone-backlog 的条目）、`pipeline_advancement_action`（若有下一 milestone 待激活，包含激活指令）

## 资源

使用当前活跃 Milestone、Worktrack backlog、Candidate finished handbacks、Repo snapshot 和 Milestone-owned axis reports 作为主要输入。不得读取 `.servo/tmp` round chain或 sibling axis outputs 来准备另一个 axis 的输入。

结果应保持聚焦于 Milestone 级别的聚合分析，而不是扩张成单个 worktrack 的逐条审查或下一 worktrack 的选择规划。输出应可直接作为 `RepoScope.Decide` 和 `harness-skill` continuous execution 流程中的 handback 判断依据。

## `purpose_achieved` 操作化判定

`purpose_achieved` 不得依赖主观判断。按以下步骤逐条验证：

1. **逐 signal 验证**：对 `completion_signals` 中的每一项，从 `aggregated_evidence` 中寻找是否已有对应的肯定 evidence。每项 signal 给出 `satisfied` / `not_satisfied` / `insufficient_evidence`。
2. **逐 criterion 验证**：对 `acceptance_criteria` 中的每一项，判断是否满足。每项 criterion 给出 `met` / `not_met` / `cannot_determine`。
3. **计算覆盖率**：`signal_satisfaction_pct` = satisfied 数 / 总 signal 数；`criteria_pass_pct` = met 数 / 总 criteria 数。
4. **读取阈值**：`completion_threshold_pct` 缺失时按 `100` 处理。该阈值只影响 goal-driven milestone 的 `purpose_achieved` 判定。
5. **判定规则**：
   - `purpose_achieved = true` 要求：`signal_satisfaction_pct >= completion_threshold_pct` **且** `criteria_pass_pct >= completion_threshold_pct`
   - 任一低于 threshold → `purpose_achieved = false`
   - 若存在 `insufficient_evidence` 或 `cannot_determine` → `purpose_achieved = false`，追加 `developer_decisions_needed` 条目
   - 若本轮 `Milestone Gate` 未 `pass`，不得把 `purpose_achieved` 视为可用于 closeout 的完成信号
6. **记录明细**：在 `aggregated_evidence_summary` 中记录每条 signal/criterion 的判定结果、覆盖率、threshold 和依据，供 developer 复核。

## `Milestone Gate` 输入与聚合调用

`Milestone Gate` 是 goal-driven milestone 的上层集成验收，不替代各 Worktrack 的独立 Review。它只在 `worktrack_list_finished == true` 后生效。

**本技能不直接运行 Milestone Gate，也不分派四个 axis carrier**。当 `worktrack_list_finished == true` 时，本技能负责：

1. 准备 common factual base：`milestone_id`、objective/configuration、target-type hints、`aggregation_rules`，以及每个由 `worktrack_list` 和 matching-`milestone_id` backlog entry 只读派生、原始状态为 `done` 且通过 Candidate handback 检查的 completed contribution 的 initial requirement ref、`finished_handback_ref`、`accepted_checkpoint`、`closeout_checkpoint_commit`、stable evidence refs 和必要 repo/source read scope。
2. 对每个 contribution 执行最小 identity/completion/ref 可读性检查。不得重放 Worktrack Review、merge 或 Close transaction。
3. 向 Harness 暴露 `milestone_gate_axis_dispatch_required: true`，并列出四个 required axes：blackbox / whitebox / anticheat / composite。
4. 等 Harness 顶层为每个 axis 构建独立输入包并分别分派 sibling carriers。每份包只含共同事实基础和该 axis 允许读取的 source/evidence categories，不含 sibling report、verdict、finding 或 conclusion。
5. 等四个 carriers 产出 `axis_reports` 和 `axis_dispatch_profile`。Axis carrier 和本技能都不得继续派生 SubAgent。
6. **调用或消费** `milestone-gate` 聚合结果。Gate 输入只包含 closed contribution facts、四份独立 `axis_reports`、`axis_dispatch_profile`、`aggregation_rules` 和 `target_type_rules`。
7. **消费** gate skill 返回的 `milestone_gate_verdict` 和聚合状态字段。
8. 将 gate verdict 纳入 `purpose_achieved` 判定和 milestone 状态报告。

`milestone-gate` skill 只运行 aggregator。若 Harness 无法提供四个可信 axis reports，`milestone-gate` 必须保留 blocked / non-pass verdict；programmer manual exception 只能出现在 final acceptance override 中，不能把 gate verdict 改写为 pass。

**阻断语义**：`milestone_gate_verdict != "pass"` 时，必须阻断 milestone closeout，返回 `milestone_acceptance_verdict = "blocked"`，设置 `handback_required = true`。

### Gate 相关字段

以下字段由 `milestone-gate` skill 产出，本技能透传到 milestone 状态报告中：

- `milestone_gate_verdict`、`milestone_gate_summary`、`milestone_gate_execution_model`
- `axis_reports`、`axis_report_status`、`axis_dispatch_profile`、`axis_satisfaction`
- `aggregation_rules_applied`、`aggregation_rules_missing`、`per_worktrack_weights`
- `contradiction_findings`、`contradiction_blocked`、`degenerate_and_applied`
- `blockers`、`evidence_refs`、`manual_exception`、`accepted_gate_verdict_preserved_as`、`anti_cheat_findings_preserved`、`manual_exception_followup_ref`

以上字段列表是本技能消费 `milestone-gate` 输出时的运行态最低合同；不得依赖 source-repo 路径读取额外格式定义。

## Writeback 指令

本技能不直接写入 milestone artifact 或 control-state。产出中包含 `writeback_instructions` 对象，`harness-skill` 在收到本技能输出后**必须**按指令执行以下写回：

- **Milestone Artifact**（`.servo/milestone/{milestone_id}.md`）：
  - 将 `progress_counter` 更新为本技能计算的当前值
  - 仅当 `milestone_acceptance_verdict == "achieved"` 且 `milestone_gate_verdict == "pass"` 时：将 `status` 更新为 `completed`
  - 更新 `updated` 时间戳
  - 写入 `milestone_gate_verdict` 和 `milestone_gate_summary`（来自 `milestone-gate` 输出）
  - 若 `aggregation_rules_applied == true`：透传 `milestone-gate` 输出的聚合状态字段到 milestone artifact
  - 若存在 programmer final acceptance override：透传 `accepted_gate_verdict_preserved_as`、`anti_cheat_findings_preserved`、`manual_exception_followup_ref`，不得只写 `manual_exception` 而丢失原始 Gate/anticheat 证据保真字段
- **Control State**（`.servo/control-state.md`）：
  - 写入 `milestone_input_checkpoint` 到 `Baseline Traceability`
  - 更新 `milestone_status`（若发生变化）
  - 写入 `milestone_gate_verdict` 和关键聚合字段（来自 `milestone-gate` 输出）到 control state 的 milestone gate 段
- **Milestone Backlog / History**（`.servo/repo/milestone-backlog.md` / `.servo/repo/milestone-history.md`）：
  - live backlog 只保留 `planned` / `active` 条目
  - completed / superseded 条目应写入 milestone-history
  - 按 milestone_id upsert，更新 status 和 updated
- **Pipeline Advancement**（仅在 `milestone_acceptance_verdict == "achieved"` 时）：
  - 读取本技能输出的 `pipeline_advancement`
  - 若存在下一候选 milestone：更新其 status 为 `active`，更新 control-state 的 `active_milestone`
  - 若不存在：清空 control-state 的 `active_milestone`

`harness-skill` 不得跳过以上写回步骤。若本技能输出标记 `writeback_required: false`，可跳过。若标记 `writeback_required: true` 但 `harness-skill` 无法安全执行全部写回（如文件写入失败），必须作为 `proceed_blockers` 返回。

对于 goal-driven milestone，本技能输出的 `achieved` 是 programmer final acceptance 的前置信号，不等于已获得最终验收。programmer final acceptance 发生后，`harness-skill` 必须把 acceptance writeback 当作一个逻辑事务执行：milestone artifact、live milestone-backlog、milestone-history、control-state、handback guard、baseline traceability 和相关 worktrack 状态必须一起校验、写入并提交后复核。若任何写入失败或提交后出现 completed/accepted history milestone 仍含 `(planned)` / `(active)` worktrack、control-state pipeline summary 与 live+history aggregate 计数不一致、或 active pointer 不一致，必须返回 `writeback_incomplete` / `milestone_pipeline_stale` 阻塞项，而不是继续推进。
