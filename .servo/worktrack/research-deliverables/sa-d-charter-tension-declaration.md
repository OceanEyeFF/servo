---
title: "SA-D: Charter Tension Declaration (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-004
updated: 2026-05-07
owner: research-subagent
---

# SA-D: Charter 张力声明草案（P0-071 聚合 Backend）

> 本草案仅服务于 design phase。它**不修改** `.servo/goal-charter.md` 真相层；目标是产出一份"声明文本"，让未来的 reviewer 在追问「P0-071 的设计是否尊重 charter」时能给出明确答案——本声明是 reviewer 的查阅入口。
>
> 任务核心承诺：**`.servo/goal-charter.md` 不需要任何修订**。本草案就是为这个承诺提供论据的文档。

---

## 1. 一句话声明

**聚合 backend (`--backend bundle`) 是 `servo-installer` 在 operator 视角的便利层；它不重定义 mainline lane 与 compatibility lane 的关系、不引入新的 Engineering Node Map 节点类，也不改变 `agents` 与 `claude` 在真相层的分发分离。**

---

## 2. 三段式承诺

### 2.1 它是什么

聚合 backend 是 `servo-installer` 的 **dispatcher control-plane 行为**：当 operator 传 `--backend bundle` 时，dispatcher 在同一命令调用中同时驱动 agents 与 claude 两条既有的、独立的 mapping 链路（详见 D-2 §2.2）。它的唯一价值是把"运维者要分别敲两次单 backend 命令"这个工序合并为"敲一次 aggregate 命令"——即 `npx servo-installer install --backend bundle` 等价于先 `npx servo-installer install --backend agents` 再 `npx servo-installer install --backend claude`，但带 fail-closed 写前预扫描与统一 stderr 归因前缀。

它的实现层面是：
- `--backend` 枚举的第三个合法值（per SA-A 候选 A）
- dispatcher 内部的双 context 顺序编排（per SA-B 混合事务模型 + SA-C dual-root trust boundary）
- TUI 主菜单的第三个 backend 选项
- 不引入新 distribution、不引入新 adapter、不引入新 source 路径、不引入新 payload descriptor

### 2.2 它不是什么

**它不是一种新的 distribution lane**。Charter 第 3 段（"Core Product Goals"）和第 4 段（"Technical Direction"）已经明确两条 lane：
- **mainline lane**：Node/npm/npx 分发，以 `agents` backend 作为 P0 consumer，承担"凭借 `npx servo-installer` 实现 install/update/verify/diagnostic"的近期主要分发形状
- **compatibility lane**：Claude skills 分发，作为 slower compatibility lane，docs / smoke / runbook 与 mainline 保持共贯但允许节奏滞后

`bundle` 不在这两条 lane 之外形成第三条 lane。它的实质是 mainline 与 compatibility 的**操作合并视图**：mainline 写 `.agents/skills/aw-{skill_id}/`，compatibility 写 `.claude/skills/{skill_id}/`，两个分发的物理位置、payload 路径、verify 路径都不变；bundle 只让一次命令同时触发两条 lane 的写入。

**它不是 Engineering Node Map 的新节点类**。Charter 的 Engineering Node Map 节点类型注册表当前包含 7 类：`feature` / `refactor` / `research` / `bugfix` / `docs` / `config` / `test`。P0-071 实施 phase 落地时，aggregate backend 的实现 worktrack 会以现有 `feature` 节点类（merge_required: yes、baseline_form: commit-on-feature-branch、gate_criteria: implementation + validation + policy）承担；不会引入"`bundle-feature`"或"`aggregate-config`"之类新节点类。

**它不改变 `agents` 与 `claude` 在真相层的分发分离**。Charter 第 5 段（"System Invariants"）明确："`.agents/`、`.claude/`、`.opencode/` 是 repo-local deploy targets，不是 source 或 truth layers"。`bundle` 写入的两个目标根 `<targetRepoRoot>/.agents/skills/` 与 `<targetRepoRoot>/.claude/skills/` 仍然分别属于这两个独立的 deploy target；bundle 不让它们融合为单一 target，也不引入"双根混合 marker"或"跨根 owner 转移"。两个 distribution 在 marker.backend、source binding、verify boundary、prune boundary 上仍然独立（per SA-C §6.1 / §6.2 / §6.3）。

### 2.3 它如何与 charter 共存

聚合 backend 对 charter 的关系符号化表达：

```
charter:
  mainline lane     = Node/npx, agents distribution, P0 consumer
  compatibility lane = Claude skills distribution, slower lane

aggregate (bundle) = mainline.write() ⊕ compatibility.write()
                     where ⊕ is "同时调度并保留各自合同"
                     not "merge into one lane"
                     not "redefine lane class"
                     not "shift compatibility lane to P0"
```

`⊕` 算子的关键是**保留**两 lane 的独立合同，而不是把 compatibility lane "提拔"到 mainline。具体而言：

- `bundle` 的成功**不**意味着 compatibility lane 与 mainline 在 charter 维度上获得相同优先级；charter 仍然把 mainline 视为 P0、compatibility 视为 slower lane。
- `bundle` 的存在**不**意味着 Claude-specific packaging 失败可以阻塞 mainline；compatibility lane 自身的 docs / smoke / runbook 节奏仍然独立（charter 第 6 行第 2 句）。
- `bundle` 的 partial-completion 模式（per SA-B §3 与 D-1 §2.5）允许"agents 成功 + claude 失败"或反向，operator 仍可用单 backend 路径完成清理；这正是 charter 中两 lane 节奏分离的运行时体现。

---

## 3. 与 Charter 关键段落的对照

下表把 charter 中可能被 P0-071 触动的段落逐条列出，并给出"是否被本设计触动"的判定。

### 3.1 Project Vision

> Build a Codex-first AI coding harness platform and distribute it as a reusable repo-side contract layer across projects. The platform should make AI coding work controllable through explicit goals, bounded context, execution contracts, verification evidence, gate decisions, and verified writeback.

**判定**：未触动。Codex-first 与 repo-side contract layer 的语义都在 docs / product / toolchain 层面；`bundle` 是 deploy 层面的 dispatcher 别名，不影响 vision。

### 3.2 Core Product Goals（节选与 P0-071 直接相关的 4 条）

> Make Node/npm/npx the primary near-term distribution shape for Harness deploy tooling, with the user-facing entrypoint converging on `npx servo-installer` for install, update, verify, and diagnostic workflows.

**判定**：未触动且**强化承接**。`bundle` 是 `npx servo-installer` 命令面的扩展，仍以 `npx servo-installer` 为 user-facing entrypoint。

> Design `servo-installer` as a dual-mode TUI + CLI tool: CLI remains the stable scriptable contract, while TUI provides the operator-facing interactive path for guided install, diagnosis, update planning, and backend selection.

**判定**：未触动且**强化承接**。`bundle` 在 CLI（`--backend bundle`）与 TUI（主菜单第三选项）保持等价，charter 的 dual-mode 承诺被严格遵守（per SA-A §2.5 与 D-1 §2.6）。

> Treat Claude skills distribution as a slower compatibility lane: keep docs, smoke/runbook evidence, and future adapter room, but do not let Claude-specific packaging block the Node/npx mainline.

**判定**：未触动且**严格保护**。`bundle` partial-completion 允许"agents 成功、claude 失败"（per SA-B §3 与 D-1 §2.5），实际上正是 charter "do not let Claude-specific packaging block the Node/npx mainline" 在运行时层面的表达：claude 失败不回滚 agents，operator 可显式选择"只装 mainline"（不使用 aggregate）。

> Maintain backend adapter source under `product/harness/adapters/`, with the current `agents` backend as the first concrete distribution target and near-term P0 consumer for the Node/npx distribution lane.

**判定**：未触动。`bundle` 不在 `product/harness/adapters/` 下新建 `bundle/` 子目录；source 仍然是 `adapters/agents/skills/` 与 `adapters/claude/skills/` 两个，driver 共享同一 canonical（per D-2 §2.2 双链路图）。

### 3.3 Technical Direction（节选）

> `toolchain/scripts/deploy/` owns deploy, install, update, verify, and distribution helper behavior; deploy scripts should remain diagnosable, contract-driven, and evolve toward a Node/npm-packaged `servo-installer` command surface.

**判定**：未触动且**强化承接**。`bundle` 是 `servo-installer` 命令面的 contract-driven 扩展，所有合同条款（事务、信任边界、错误归因）在 D-1 / D-2 两份草案中以 contract 文档形式落地。

> The current local `servo-harness-deploy` package scaffold is an interim proof and package-facing wrapper for deploy semantics, not the final user-facing product name.

**判定**：未触动。`bundle` 不影响 package name 或 scaffold。

> Backend differences may affect adapter metadata, install paths, and CLI wrapping, but must not redefine shared Harness truth.

**判定**：未触动且**严格遵守**。`bundle` 仅是 CLI wrapping 维度的扩展（dispatcher 别名）；不影响 adapter metadata（adapter 不变）、不引入新的 install path（仍是 `.agents/skills/aw-{skill_id}/` 与 `.claude/skills/{skill_id}/`）、不重定义 Harness truth（canonical source 仍唯一）。

### 3.4 Engineering Node Map

> | type | merge_required | baseline_form | gate_criteria | if_interrupted_strategy | Description |
> |------|---------------|---------------|---------------|-------------------------|-------------|
> | `feature` | yes | commit-on-feature-branch | implementation + validation + policy | checkpoint-or-recover | New Harness, adapter, scaffold, or distribution capability |

**判定**：未触动。Engineering Node Map 的 7 类节点类型注册表中：

- P0-071 的 design phase（本 worktrack）以 `research` 节点类执行（baseline_form: annotated-tag-or-report; gate_criteria: review-only），与 charter 一致。
- P0-071 的 implementation phase 落地时以 `feature` 节点类执行（New distribution capability：在 `servo-installer` 命令面新增 aggregate dispatcher）。`bundle` 完全落入既有 `feature` 节点类的 description"New Harness, adapter, scaffold, or distribution capability"。
- 不需要新增 `bundle-feature` / `aggregate-config` / `multi-backend-feature` 之类的新节点类。

### 3.5 System Invariants

> - `product/` is the only business source root.
> - `docs/` is the truth layer for project maintenance, Harness doctrine, and adjacent-system contracts.
> - `toolchain/` only contains scripts, tests, evaluation, deployment, packaging, and governance tooling.
> - `.agents/`, `.claude/`, and `.opencode/` are repo-local deploy targets, not source or truth layers.
> - `.servo/`, `.autoworkflow/`, and `.spec-workflow/` are runtime or state layers, not long-term truth layers.
> - `.nav/` is only a compatibility navigation layer.
> - Harness is a layered closed-loop control system, not the coding executor itself.
> - Goal changes are reference-signal changes and must be handled through explicit change control, not by ordinary loop decisions.
> - Evidence and Gate remain separate: evidence proves state, gate decides whether the state may advance.
> - Only verified facts may be written into long-term truth documents.

**判定**：未触动。逐条对照：

| invariant | 是否被触动 | 备注 |
| --- | --- | --- |
| `product/` only business source root | 否 | bundle 不在 product 外引入 source |
| `docs/` truth layer | 否 | bundle 的合同变更走 D-1 / D-2 修订草案，最终回写在 `docs/project-maintenance/deploy/` 既有路径 |
| `toolchain/` scripts only | 否 | bundle 实施落在 `toolchain/scripts/deploy/bin/servo-installer.js` 既有路径 |
| `.agents/` `.claude/` `.opencode/` deploy targets | 否 | bundle 写入的两根仍然分别属于 `.agents/skills/` 与 `.claude/skills/`，没有融合 |
| `.servo/` runtime state | 否 | design phase 草案落 `.servo/worktrack/research-deliverables/`，符合 runtime/state 分类 |
| `.nav/` compatibility navigation | 否 | bundle 不触动导航层 |
| Harness layered closed-loop | 否 | aggregate 是单层 dispatcher 行为，未引入新控制层 |
| Goal changes via explicit change control | 否 | **关键：bundle 不是 goal 变更**，所以本 worktrack 不需要走 ChangeGoal；本声明就是用来证明这一点的 |
| Evidence and Gate separation | 否 | design phase 评估与 Gate review 分开 |
| Only verified facts written back | 否 | 本草案明确 design phase 不回写真相层 |

**关键不变量**：第 8 条"Goal changes are reference-signal changes and must be handled through explicit change control, not by ordinary loop decisions"。本声明正面回答："P0-071 不是 goal 变更"——它没有引入新的 product goal、没有改变 lane 优先级、没有改变 success criteria 中任何一条；它只是 charter 已声明的"`servo-installer` 命令面"的一次合同扩展。因此**不**需要 ChangeGoal 流程。

### 3.6 Success Criteria（节选）

> - Deploy tooling can install, verify, diagnose, and update through a Node/npm/npx distribution path centered on `npx servo-installer`, without requiring target repositories to understand this repository's internal source layout.
> - `servo-installer` supports a dual working mode: machine-readable CLI commands for scripts/CI and an interactive TUI for human operators, with both modes sharing the same deploy contracts and verification semantics.
> - Claude skills distribution can lag the Node/npx mainline as long as Claude-facing docs and smoke/runbook evidence stay coherent with the shared Harness contracts.
> - Backend-specific prompts, payloads, and install paths do not redefine shared project truth.

**判定**：未触动且**强化承接**。bundle 的引入让 `servo-installer` 的命令面既保持 dual-mode（CLI + TUI）等价、又保持 mainline 与 compatibility 的节奏分离（partial-completion 允许 mainline 独立成功）。

---

## 4. 本声明对未来 reviewer 的约束

未来 reviewer 在追问 "P0-071 是否尊重 charter？" 时，引用本声明。下表为可能问题与对应回答：

| reviewer 问题 | 对应回答位置 |
| --- | --- |
| "bundle 是否引入新 distribution lane？" | §2.2 "它不是一种新的 distribution lane"段落 |
| "bundle 是否需要修订 Engineering Node Map？" | §2.2 "它不是 Engineering Node Map 的新节点类"段落 + §3.4 |
| "bundle 是否破坏 .agents 与 .claude 的 deploy target 独立性？" | §2.2 "它不改变 agents 与 claude 在真相层的分发分离"段落 + §3.5 |
| "bundle 是否改变 mainline / compatibility lane 的关系？" | §2.3 "它如何与 charter 共存" 与 §3.2 |
| "bundle 是否触发 ChangeGoal 流程？" | §3.5 关键不变量段落（"P0-071 不是 goal 变更"） |
| "bundle 是否影响 dual-mode TUI/CLI 承诺？" | §3.2 "Design `servo-installer` as a dual-mode TUI + CLI tool" 段落判定 |
| "bundle 失败回滚是否违反 Claude lane 'slower compatibility lane' 定位？" | §3.2 "Treat Claude skills distribution as a slower compatibility lane" 段落判定 |
| "bundle 是否引入新的 source / adapter？" | §2.1 "它的实现层面" + D-2 §2.2 双链路图 |
| "P0-071 是否需要修订 .servo/goal-charter.md？" | §1（一句话声明）+ §5（结论） |

---

## 5. 结论

`.servo/goal-charter.md` **不需要任何修订**。

理由：

1. P0-071 没有引入新的 product goal、没有改变 lane 优先级、没有改变 success criteria。
2. P0-071 的实现 phase 完全落入 charter 既有 `feature` 节点类的 description（"New ... distribution capability"）。
3. P0-071 的所有 system invariants 触点都通过对照证明未被触动（§3.5）。
4. P0-071 的合同变更落点是 `docs/project-maintenance/deploy/` 既有真相层文档（D-1 / D-2 修订），不需要回写 charter。

如果未来 reviewer 在 D-1 / D-2 修订套用后仍质疑本设计与 charter 的一致性，应优先重新阅读本声明的 §3.5 关键不变量段落（"P0-071 不是 goal 变更"），并与 D-1 §"Aggregate Backend (`--backend bundle`)" 小节交叉对照。

---

## 6. 边界声明

- 本草案**不修改** `.servo/goal-charter.md` 真相层文件
- 本草案**不修改** `servo-installer.js`
- 本草案**不修改** 其他真相层文档
- 本草案**不执行** `servo-installer` 或运行任何测试
- 本草案**不**触发 ChangeGoal 流程；本声明的存在恰恰是为了证明 ChangeGoal 不需要被触发
- 本草案产出供 P0-071 design Gate review 与未来 reviewer 查阅；implementation phase 套用 D-1 / D-2 修订前必须经新一轮 programmer 批准
