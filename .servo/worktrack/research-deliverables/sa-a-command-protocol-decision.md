---
title: "SA-A: Command Protocol Decision Draft (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-001
updated: 2026-05-07
owner: research-subagent
---

# SA-A: Command Protocol Decision Draft (P0-071 Aggregate Backend)

> 本草案仅服务于 design phase：评估三种聚合 backend 命令面 protocol 候选并产出推荐。所有 SA-A 结论是后续 SA-B/C/D/E 与 implementation phase 的输入，本身不修改 servo-installer.js、不修改 distribution-entrypoint-contract.md，也不写入任何长期真相层。

## 1. Executive Summary

**推荐候选：A — `--backend bundle` enum 扩展**。

`--backend bundle` 在五个评估维度上获得最佳综合评分：它对既有 80 个测试中以 `--backend agents|claude` 为参数集的固定串近似零侵入（既有断言全部基于具体的 `agents` 与 `claude` 字符串，而非"backend 必须是单值"这一行为），它在 operator 心智模型中保持单一锚点（"backend 仍是一个枚举"），它对 servo-installer.js 中 9 个 parseNodeXxxArgs 与 backendAllowed gate 的修改面最小（在 `backendAllowed([...])` 与 `expectedPayloadVersions` / `targetRootForBackend` 的下游分支上以最小拓扑变化新增 bundle 节点即可），并且它在 TUI 维度上能直接复用现有的"Backend: agents"显示槽（替换为"Backend: bundle"），不破坏 CLI ↔ TUI 等价不变量。候选 B 的多值列表与候选 C 的子命令分别引入"逐项解析逻辑混入 backend 字段"和"命令面分叉"两类新风险，对当前以 `parseNodeBackendRootArgs(args, command, allowedBackends)` 为核心的 dispatcher 形态都带来本质性结构改造；A 是唯一可以"原地扩枚举值"通过的形态。

## 2. Candidate A Evaluation: `--backend bundle` enum 扩展

### 2.1 命令面 backward-compat

候选 A 将 `bundle` 加入 `backendAllowed` 的 allowed set 与 `expectedPayloadVersions` / `backendTargetRootConfig` 的下游分支映射。命令解析层面的 backward-compat 影响：

- 既有 9 个 `parseNodeXxxArgs` 函数（`parseNodeBackendRootArgs`、`parseNodeUpdateArgs`、`parseNodeDiagnoseJsonArgs`、`parseNodeDiagnoseArgs`、`parseNodeUpdateJsonArgs`、`parseNodeUpdateDryRunArgs`、`parseNodeUpdateYesArgs`、`parseNodeCheckPathsExistArgs`、`parseNodePruneArgs`）的 backend 字段读取与 `backendAllowed` 检查不需要重写，只需要在 allowed set 中加入 bundle。
- 既有的所有 `--backend agents` / `--backend claude` 测试期望（约 30+ 处具体串）均不变化：`agents` 与 `claude` 仍是 valid 单值，仍走单 backend 代码路径。
- `parseNodeBackendRootArgs(args, command, allowedBackends)` 的签名不变；仅在调用方传入的 allowedBackends 列表中追加 bundle。
- 已有的 `unsupported servo-installer command or options for Node-only distribution` fallback 路径仍然兜底未知 backend 与 unsupported 组合。

兼容风险：低。

### 2.2 Operator 心智模型直观度

`--backend bundle` 沿用 operator 已熟悉的"backend 是一个 flag"心智，bundle 显式表示"这是一个聚合分发对象"。Operator 在 `servo-installer install --backend bundle` 与 `servo-installer install --backend agents` 之间切换时，命令面拓扑保持一致：动词 + `--backend` + 标识符。Bundle 作为一个具名 backend 值，区别于 agents 与 claude 这两个具名 backend 值，三个值并列，semantic ladder 平。但 operator 必须理解"bundle 不是某个具体的 deploy target，而是逻辑聚合"——这一额外认知负担需要在 help 文本中显式说明，例如"--backend bundle: aggregate backend; installs both agents and claude in one transaction"。

直观度评级：中高。

### 2.3 Parser / dispatcher 实现复杂度

servo-installer.js 当前实现的 cli arg parser 是一组 9 个独立 parseNodeXxxArgs 函数，每个函数手工逐 token 扫描 args，识别 flag 与等号形式（`--backend value` 与 `--backend=value`），最后调用 `backendAllowed(parsed.backend, [agentsBackend, claudeBackend])` 做 allow-list 校验。候选 A 的实现复杂度：

- 新增常量 `bundleBackend = "bundle"` 与对应 `expectedPayloadVersions[bundleBackend]`（聚合 payload 的 version 由 SA-D 决议；本草案不预设）。
- 修改每个 parseNodeXxxArgs 末端的 `backendAllowed(parsed.backend, [agentsBackend, claudeBackend])` 调用，在允许 bundle 的命令面中加入 `bundleBackend`。
- `parsedBackendRoots(backend, agentsRoot, claudeRoot)` 已经有 backend === claudeBackend 的条件分支，扩展为对 bundle 同时携带 agentsRoot 与 claudeRoot：`backend === bundleBackend ? { backend, agentsRoot, claudeRoot } : ...`。
- `targetRootForBackend(backend, targetRepoRoot, options)` 新增 bundle 分支，返回双 root 结构（具体形态由 SA-C trust boundary 决议），dispatcher 层根据 bundle backend 走聚合代码路径。
- `runNodeOwned` 的命令分发函数链不需要拆分；每个 runNodeXxx（runNodeInstall / runNodePrune / runNodeVerify / runNodeDiagnose / runNodeCheckPathsExist / runNodeUpdate*）通过 backend === bundleBackend 分支进入聚合实现。
- 新增聚合执行路径函数（installBundle / verifyBundle / 等），由 SA-B 事务语义决议这些函数的内部行为。

dispatcher 拓扑变化：无（保持 9 parser → runNodeXxx → backend handler）。
parser 工作量：每个 parser 末端的 allowed list 扩展 + `parsedBackendRoots` 的 bundle 分支。
聚合代码路径：新增（不可避免，无论候选哪种都要）。

复杂度评级：低（parser 层）+ 中（聚合执行层；与候选 B/C 共用）。

### 2.4 Error message 设计空间

候选 A 在 error message 设计空间方面收益较高：

- **未知 backend 值**（如 `--backend unknown`）：当前实现走 `backendAllowed` → 返回 null → fallback 到 `unsupported servo-installer command or options for Node-only distribution`。bundle 加入后，错误消息形态保持一致。如需更友好的提示（"unknown backend: unknown; expected: agents | claude | bundle"），可以在 backendAllowed 失败时附加。
- **bundle 与不兼容选项的组合**：例如 `--backend bundle --source github`（github 源仅支持 agents 单 backend）。这类 cross-flag 冲突可以在 `parsedNodeUpdateResult` 等 finalizer 中显式 reject 并附加 error message："--backend bundle is not supported with --source github; bundle requires --source package"。
- **缺失双 root override 时的提示**：当 `--backend bundle` 携带 `--agents-root` 但缺失 `--claude-root` 时，可显式提示"--backend bundle with --agents-root must also provide --claude-root"。这种二维校验在单 backend 下不存在，是 bundle 引入的新错误维度。
- **混合错误聚合**：bundle 模式下 verify / install 失败可在 stderr 标注 `[bundle:agents]` 与 `[bundle:claude]` 前缀，operator 一眼看出哪一边失败，与 SA-B 的失败口径决议直接耦合。

设计空间评级：高。

### 2.5 TUI 映射友好度

TUI 当前在主菜单显示 `Backend: agents` 行（servo-installer.js 第 3472 行），所有 TUI 操作硬编码 `--backend agents`（第 3422 / 3437 / 3450 / 3486 / 3489 / 3492 行）。候选 A 的 TUI 映射：

- 在 TUI 主菜单的 `Backend: agents` 行扩展为 backend 选择项（agents / claude / bundle 三选一），bundle 选择后 guided flow 与单 backend 选择走同一组菜单项（diagnose / verify / dry-run / apply）。
- TUI menu 的 `runNodeOwned(["diagnose", "--backend", "agents", "--json"])` 调用替换为 `runNodeOwned(["diagnose", "--backend", currentBackend, "--json"])`，currentBackend 由用户在主菜单选择。
- bundle 模式下，TUI guided flow 的展示需要列出"Step 1: Diagnose agents → claude（双 root）" 等并行步骤，这是 TUI 表现的扩展点（CLI 用聚合 stderr 前缀表现；TUI 用阶段标题表现），与 CLI 等价。

TUI 等价友好度：高。

## 3. Candidate B Evaluation: `--backend agents,claude` 多值列表

### 3.1 命令面 backward-compat

候选 B 引入"`--backend` 接受逗号分隔多值"的解析行为。具体影响：

- 所有 9 个 parseNodeXxxArgs 函数的 backend 字段当前是 string。改为 string | string[] 或始终 list（单值时 length=1）。下游 `backendAllowed` 改为遍历 list 中每个 backend 都在 allowed set 中。
- 既有测试中 `{ backend: "agents", agentsRoot: undefined }` 这种 deepEqual 断言（包括 `parseNodeDiagnoseJsonArgs`、`parseNodeDiagnoseArgs`、`parseNodeUpdateJsonArgs`、`parseNodeUpdateDryRunArgs`、`parseNodeUpdateYesArgs`、`parseNodeCheckPathsExistArgs`、`parseNodeVerifyArgs`、`parseNodeInstallArgs`、`parseNodePruneArgs` 至少 9 个 test block，每个内部 3-6 个断言，合计 30+ 处）将不再 deepEqual 通过——除非保留 string 单值表示并仅在多值时才返回 list（即 backend 字段类型成为 union），这会让下游每一处 backend 比较都需要类型分支，dispatcher 复杂度上升。
- 即使采用"始终是 string、单值与多值在同一字符串里"的折中（例如 `agents` 与 `agents,claude` 都是 string），下游需要额外 split + dedup 步骤，且 string equal `"agents"` 的现有测试断言需要重新对齐 split 后的语义。

兼容风险：高。具体波及 `parseNode*Args accepts agents and claude` 系列 9 个测试 block 的 deepEqual 断言。

### 3.2 Operator 心智模型直观度

候选 B 的 operator 心智模型：`--backend agents,claude` 在 unix CLI 习惯里是常见多值表示（git log --pretty 的 format token 列表、ls --hide=pat1,pat2 等），operator 学习成本低；但同时引入一些隐含问题：

- `--backend agents,claude` 与 `--backend claude,agents` 是否等价？是否需要稳定执行顺序？（实际上需要，因为事务语义涉及失败短路顺序——SA-B / SA-C 决议依赖此顺序）
- `--backend agents,agents` 是否合法？需要 reject 还是 dedup？
- `--backend agents` 与 `--backend agents,` 是否等价？trailing comma 是否合法？
- 这些问题在单值或具名值（bundle）下都不存在。

直观度评级：中。

### 3.3 Parser / dispatcher 实现复杂度

候选 B 修改每个 parser：

- backend 字段从 string 改为 array（或 string union），需要在每个 parser 末端 split + dedup + 排序 + allowed list 校验，每个 parser 增加 5-10 行。
- `parsedBackendRoots(backend, agentsRoot, claudeRoot)` 的 backend === claudeBackend 分支条件改为"列表包含 claude"，需要解决"backend list 既有 agents 又有 claude 时双 root 都返回"的拓扑变化。
- `targetRootForBackend` 的语义需要扩展到 list 输入，可能需要 `targetRootsForBackends(backendList, ...)` 新函数。
- dispatcher（runNodeXxx）每个分支需要根据 backend list 长度走单 backend 还是聚合代码路径。

复杂度评级：中高（每个 parser + 每个 backend-driven helper 都需要 list 化）。

### 3.4 Error message 设计空间

候选 B 的 error message 设计：

- **多值中含未知**（`--backend agents,unknown`）：需要选择策略——整体 reject 还是仅 reject 未知项？前者一致性好，后者用户体验好但隐含错误传播。
- **重复值**（`--backend agents,agents`）：需要明确策略；如果 dedup，operator 体验好；如果 reject，error message 简单。
- **顺序敏感性**（`--backend claude,agents` vs `agents,claude`）：如果 SA-B 决议事务语义依赖顺序（例如 agents 先写、claude 后写），需要在 error / log 中明确执行顺序，否则 operator 可能误以为 list 顺序与执行顺序无关。
- **`--source github` 与多 backend 冲突**：currently github source 仅支持 agents；多 backend 时如果含 github，需要 reject 或自动降级，error message 比 bundle 单标识符更复杂。

设计空间评级：中。

### 3.5 TUI 映射友好度

TUI 中难以直接表达"多选 backend list"——按钮 / 单选项映射到多选项需要 multi-select widget（checkbox group）才能等价。当前 TUI 是行号选择 menu，最自然的映射是把"agents only / claude only / agents + claude"作为三个并列菜单项，但这又退化回 bundle 的具名概念。如果坚持多值 list 在 TUI 表达，需要:

- 增加多选 prompt（"Select backends (comma-separated): agents,claude"）—— operator 在 TUI 里手动输入逗号分隔字符串，这与 TUI 的"按数字选项"传统割裂。
- 或者 TUI 显示三个 menu item："1. agents", "2. claude", "3. agents + claude"，第三项实际上又是 bundle 的命名。

TUI 友好度评级：低。

## 4. Candidate C Evaluation: 新增 `bundle` 子命令

### 4.1 命令面 backward-compat

候选 C 在顶层 dispatch 路径（runNodeOwned）首先 dispatch `bundle` 子命令，剩余路径不变。具体兼容影响：

- 既有所有 `--backend agents | claude` 解析路径完全不动；既有 80 个测试断言全部不变。
- 但新增 `bundle install` / `bundle update` / `bundle verify` / `bundle prune` / `bundle diagnose` / `bundle check_paths_exist` 6 个子命令，每个都是新的解析函数（parseBundleInstallArgs / parseBundleUpdateArgs / 等），dispatcher 顶层增加新分支。
- 现有测试不被破坏，但需要新增 6 类新 parser 测试。

兼容风险：低（仅 additive）；但实现工作量在 dispatcher / parser 层重复最高。

### 4.2 Operator 心智模型直观度

候选 C 的 operator 心智模型分歧最大：

- 当前命令面是 `servo-installer <verb> --backend <name>`（动词在前、backend 是参数）。
- 候选 C 引入 `servo-installer bundle <verb>`（聚合对象在前、动词在后）。这与 git porcelain（`git stash push` / `git stash pop` 等）的子命令族风格一致，但与现有 servo-installer 的"动词 + flag"形态异构。
- Operator 学习两套语法：单 backend 是 `verb --backend name`；聚合 backend 是 `bundle verb`。这种命令面分裂是 SA-A 评估的最大反向信号。

直观度评级：低（命令面分裂违反"统一命令族"原则）。

### 4.3 Parser / dispatcher 实现复杂度

候选 C 在 dispatcher 层引入新分支：

- runNodeOwned 顶层增加 `if (args[0] === "bundle") return runBundleOwned(args.slice(1))`。
- runBundleOwned 内部复刻 runNodeOwned 的 9 parser → runNodeXxx 链：需要 6 个新的 parseBundleInstallArgs / parseBundleUpdateArgs 系列与对应 runBundleInstall / runBundleUpdate 系列。每个新 parser 与现有 parseNodeXxxArgs 高度相似但 args[0] 检查不同（"install" vs "bundle install" 的 args.slice(1)[0] 检查）。
- 实际可以让 bundle 子命令在 args.slice(1) 后复用现有 parseNodeXxxArgs（args[0] 仍是 verb），但需要在每个 parser 中放宽对单 backend 的 allowed set；这变相把候选 C 退化成候选 A——bundle 只是一个语义触发器，下游仍然是 agents+claude 的聚合。

复杂度评级：中（parser 复用率取决于实现选择；如果不复用，dispatcher 工作量翻倍）。

### 4.4 Error message 设计空间

候选 C 的 error message：

- **未知子命令**（`servo-installer bundle frobnicate`）：clean error message，与 unknown verb 同一形态。
- **bundle 与 backend flag 冲突**（`servo-installer bundle install --backend agents`）：需要明确 reject——bundle 子命令下 `--backend` 应该是 illegal，与候选 A 的 `--backend bundle --backend agents` 同源问题。
- **sub-verb 必需**（`servo-installer bundle` 无 sub-verb）：需要新 error message"bundle requires a sub-verb: install | update | verify | prune | diagnose | check_paths_exist"。
- **help 系统**：需要为 bundle 子命令族新增专属 help section。

设计空间评级：中（设计可能性多但需要新增多类 error message）。

### 4.5 TUI 映射友好度

TUI 中 bundle 映射可走两条路：

- 把 bundle 作为 TUI 主菜单的"Mode"选择项之一（agents / claude / bundle 三 mode），与 candidate A 的 TUI 映射等价但语义在子命令层而非 flag 层。
- 或保留单 backend TUI menu，新增 "Bundle operations" 子菜单进入 bundle 子命令族，类似 git stash 的子菜单。

CLI ↔ TUI 等价性：候选 C 的子命令在 CLI 是 `bundle <verb>`，TUI 中对应 menu navigation；但 CLI 的 `--backend bundle` 路径会出现在 `--help` 中两套语法（verb 一套、bundle 一套），增加 operator 比对负担。

TUI 友好度评级：中。

## 5. Trade-off Comparison Table

| 维度 | 候选 A: `--backend bundle` | 候选 B: `--backend agents,claude` | 候选 C: `bundle` 子命令 |
|---|---|---|---|
| **命令面 backward-compat** | 高（既有 `--backend agents|claude` 测试零侵入；只在 allowed set 加入 bundle） | 低（backend 字段类型变化波及 9 个 parseNode\*Args 测试 block 与 30+ deepEqual 断言） | 高（纯 additive；既有路径不动） |
| **Operator 心智模型直观度** | 中高（单一 flag 锚点；bundle 是新具名值需 help 注释） | 中（多值习惯熟悉但引入顺序/重复/trailing 等隐含问题） | 低（命令面分裂：单 backend 走 verb-flag、聚合走子命令） |
| **Parser/dispatcher 实现复杂度** | 低（每个 parser 末端 allowed list + `parsedBackendRoots` bundle 分支；dispatcher 拓扑零变化） | 中高（每 parser list 化 + `targetRootForBackend` list 化 + dispatcher 长度判断） | 中（如果 sub-parser 不复用则翻倍；如果复用则退化为候选 A） |
| **Error message 设计空间** | 高（bundle 是单标识符；cross-flag 冲突 / 缺失 root / 双前缀 stderr 都直接） | 中（多值未知 / 重复 / 顺序 / github 冲突 4 类边界场景） | 中（bundle 子命令族需要新 help / sub-verb 错误 / flag 冲突） |
| **TUI 映射友好度** | 高（直接复用现有"Backend:"slot；agents/claude/bundle 三选一） | 低（多选与 TUI menu 选项映射困难；最终退化为命名三选一） | 中（CLI 双语法反映到 TUI 也需双导航） |

## 6. Backward-Compat Impact Checklist

**评估方法**：以 grep 与测试名识别测试类别，对每个候选标注影响范围。

### 6.1 候选 A 影响清单

| 类别 | 既有测试样例（test block 名 / 行号） | 影响 |
|---|---|---|
| `parseNode*Args` 单值 backend deepEqual 断言 | `parseNodeDiagnoseJsonArgs`(L903) / `parseNodeDiagnoseArgs`(L924) / `parseNodeUpdateJsonArgs`(L940) / `parseNodeUpdateDryRunArgs`(L1022) / `parseNodeUpdateYesArgs`(L1066) / `parseNodeCheckPathsExistArgs`(L1198) / `parseNodeVerifyArgs`(L1229) / `parseNodeInstallArgs`(L1246) / `parseNodePruneArgs`(L1263) | 不变（`{ backend: "agents", ... }` / `{ backend: "claude", ... }` 形态保持） |
| 子进程 invoke `--backend agents` 与 `--backend claude` 集成测试（如 `servo-installer check_paths_exist agents is node-owned`(L1694)、`servo-installer install agents writes a clean target`(L2329)、`servo-installer verify agents is node-owned`(L2082)、`servo-installer prune agents removes only same-backend`(L2522)、`servo-installer claude read-only lifecycle`(L1740)、`servo-installer claude mutating lifecycle`(L1817) 等约 30+ 个集成测试） | 不变（`--backend agents` / `--backend claude` 字面参数仍 valid） |
| Unsupported variants 测试（`servo-installer rejects unsupported install variants`(L2775)、`servo-installer rejects unsupported local agents variants`(L2801)、`parseNodeUpdateArgs wrappers keep unsupported update forms rejected`(L1119)、`unsupported agents package variants are classified without Python`(L1143)） | 不变（unsupported error fallback 路径仍在；bundle 是 valid 新值不进入 unsupported） |
| `buildNodeBackendContext keeps backend target root defaults`(L846) backend 参数化测试 | 需要新增 bundle case（不破坏现有 agents/claude/unsupported 三组断言） |
| `parsedBackendRoots` 隐式集成（无独立测试，通过 parser 测试覆盖） | 仅当增加 bundle 分支时新增覆盖断言，对现有断言无破坏 |

**结论**：候选 A 对既有测试的破坏面 ≈ 0；新增 bundle 测试为纯 additive。

### 6.2 候选 B 影响清单

| 类别 | 既有测试样例 | 影响 |
|---|---|---|
| `parseNode*Args` 单值 backend deepEqual 断言（同 6.1 9 个 test block） | 同 6.1 9 个 block | **全部需要重写**：`{ backend: "agents", ... }` 在新方案下应是 `{ backend: ["agents"], ... }`（或保留 string + 增加 list union），30+ deepEqual 断言每个都需要修改；如果走 union 方案，每个 dispatcher 调用点也要类型分支 |
| 子进程 invoke `--backend agents` 集成测试 | 同 6.1 30+ 个集成测试 | 子进程 args 不变（仍是 `--backend agents`），但 stdout/stderr 中如有 backend 字段输出（如 `[agents] drift:` 第 3300 行），格式可能因 list 化变化（`[agents]` vs `[["agents"]]` vs `[agents,claude]`），需要逐一审视 |
| Unsupported variants 测试 | 同 6.1 4 个 block | unsupported error fallback 不变，但新增多值与不兼容 source/yes/json 的组合需要新 unsupported 用例（候选 B 新增 4-6 类不兼容组合） |
| `buildNodeBackendContext`（L846） | backend 参数处理需 list 化或 union，测试 case 增多 |

**结论**：候选 B 至少波及 9 个 parseNode 测试 block 的 30+ deepEqual 断言；可能波及 30+ 集成测试的 stdout 断言（取决于实现选择）；增加 4-6 类新 unsupported 测试。

### 6.3 候选 C 影响清单

| 类别 | 既有测试样例 | 影响 |
|---|---|---|
| `parseNode*Args` 单值 backend deepEqual 断言（同 6.1 9 个 block） | 同 6.1 9 个 block | 不变（候选 C 子命令不影响现有 verb-flag parser） |
| 子进程 invoke `--backend agents` 集成测试 | 同 6.1 30+ 个集成测试 | 不变 |
| Unsupported variants 测试 | 同 6.1 4 个 block | 不变；但需要新增"`bundle <unknown-sub-verb>` rejected"、"`bundle install --backend agents` rejected"等 4-6 类新 unsupported 测试 |
| 子命令族新测试 | N/A | 新增 6 类 parseBundleXxxArgs 测试 + 6 类 runBundleXxx 集成测试，工作量约 12-20 个新测试 block |

**结论**：候选 C 对既有测试零破坏；但新增测试工作量最大（6 parser + 6 runtime + 6 unsupported variants）。

## 7. Recommended Protocol Decision

**推荐：候选 A — `--backend bundle` enum 扩展**。

**决策依据（按 SA-A 五个评估维度排序）**：

1. **Backward-compat（决定性 dimension）**：候选 A 对既有 9 个 parseNode\*Args 测试 block 的 30+ deepEqual 断言、以及 30+ 个 `--backend agents|claude` 集成测试的影响为零。bundle 是 valid 新枚举值，agents 与 claude 仍是 valid 单值，unsupported fallback 路径仍兜底未识别值。这与 P0-071 design phase 边界中"不修改 servo-installer.js"的硬约束直接对齐——本草案所需的扩展面最小，implementation phase 只需在 backendAllowed allowed list、`expectedPayloadVersions`、`backendTargetRootConfig`、`parsedBackendRoots`、`targetRootForBackend` 五个点上 additive 补丁，dispatcher 与 parser 的拓扑不变。
2. **Operator 心智模型**：候选 A 用单一 flag 锚点（`--backend`）+ 单一新具名值（bundle）扩展，operator 仍按"verb + flag"心智操作，bundle 的语义（聚合 agents+claude）在 help 文本中说明即可。候选 B 的多值列表带来顺序、trailing comma、重复 dedup 等 4 类隐含问题；候选 C 引入"verb-flag vs subcommand"的命令面分裂，是最强反向信号。
3. **Parser/dispatcher 复杂度**：候选 A 的 parser 修改面最小（每个 parser 末端 allowed list 加项；`parsedBackendRoots` 加 bundle 分支），dispatcher 拓扑不变（runNodeOwned 的 9 parser → runNodeXxx 链不需要重写，仅 backend === bundleBackend 时分流到聚合执行函数）。候选 B 需要 list 化 backend 字段并下游全部分支，候选 C 需要新建 6 套 parseBundleXxxArgs / runBundleXxx 函数。
4. **Error message 空间**：候选 A 的 bundle 是单标识符，cross-flag 冲突（如 `--backend bundle --source github`）、缺失 root override、stderr 双前缀输出（`[bundle:agents]` / `[bundle:claude]`）都能直接表达；候选 B 因多值需要处理 4 类边界，候选 C 需要新增子命令族 help / sub-verb 错误。
5. **TUI 映射友好度**：候选 A 直接复用 TUI 现有 `Backend:` slot，三选一菜单（agents / claude / bundle）与现有 menu pattern 一致，CLI ↔ TUI 等价不变量自然保持。候选 B 多选 widget 与 TUI 单选 menu 模式不匹配，最终退化为具名三选一（实际上等价于 candidate A）；候选 C 需要 TUI 双导航。

**额外的非维度论据**：候选 A 与 P0-071 charter 张力声明（"聚合 backend 是 operator 便利层，不重定义 mainline / compatibility lane"）天然一致——bundle 作为 backend 枚举的一员，只是把"两个分发同时安装"作为一种 operator 视角的便利打包，不重定义 backend 概念本身。候选 C 的子命令族风格暗示"bundle 是一类独立操作"，在 charter 维度上与"便利层"语义不如候选 A 自然契合。

## 8. Rejected-Alternatives Trade-off Analysis

### 8.1 候选 B 拒绝分析

**核心拒绝理由**：候选 B 把 backend 字段从 string 变成 string union 或 array，这一类型变化会波及 9 个 parseNode\*Args 测试 block 的 30+ deepEqual 断言，违反 P0-071 design phase 的"backward-compat 影响最小化"原则。即使采用"始终 string"的折中方案（`agents,claude` 作为 string），下游 split + dedup 也需要每个 dispatcher 分支增加分支判断，运行时复杂度上升。

**次要拒绝理由**：

- **顺序敏感性陷阱**：`--backend agents,claude` 与 `--backend claude,agents` 的事务执行顺序如果不一致，operator 会困惑；如果一致（按字典序或固定顺序），多值表达就退化为 candidate A 的具名 bundle 但带来更多隐含规则。
- **TUI 映射结构性不匹配**：TUI 当前是行号选择 menu，多选 widget 不在现有 TUI 词汇中；最终会退化为"agents only / claude only / both"的具名三选一，等价于 candidate A。
- **error message 边界增多**：`--backend agents,unknown` / `--backend agents,agents` / `--backend agents,` 等四类边界需要每一个明确策略与 error message，是 candidate A 不存在的复杂度。

**潜在收益**：候选 B 的唯一收益是 unix CLI 多值习惯熟悉度——但这一收益不足以抵消 backward-compat、TUI、error 三维度的明显劣势。

### 8.2 候选 C 拒绝分析

**核心拒绝理由**：候选 C 引入 verb-flag 与 subcommand 两套并存命令面（`install --backend agents` vs `bundle install`），违反 servo-installer 当前命令族的"动词 + flag"统一拓扑。Operator 学习两套语法、help 文本需要双 section、TUI 需要双导航，所有维度都引入命令面分裂。

**次要拒绝理由**：

- **实现工作量翻倍**：候选 C 如果 sub-parser 不复用现有 parseNodeXxxArgs，需要新建 6 套 parseBundleXxxArgs；如果复用，bundle 子命令实际只是一个语义触发器，等价于 candidate A 但语法层面更冗余（`bundle install` 是 `install --backend bundle` 的别名）。
- **CLI ↔ TUI 等价证明负担**：CLI 双语法在 TUI 必须有等价表达，而 TUI 的 menu 拓扑是单 hierarchy，bundle 子菜单与单 backend menu 并存会让 TUI 增加一层导航深度，operator 在 TUI 与 CLI 之间切换时心智模型不再 1:1。
- **charter 张力反信号**：bundle 子命令族的命名暗示"bundle 是一类独立操作族"，与 charter 中"聚合 backend 是 operator 便利层"的语义有微小张力——便利层应是现有命令的一个新参数，不是新命令族。

**潜在收益**：候选 C 对既有测试的破坏面与 candidate A 同样为零（甚至更小，因为完全 additive），且 bundle 子命令族的命名空间隔离让聚合相关 flag（如未来可能加入的 --partial、--continue-on-failure）有专属 namespace。但这些收益是后期扩展性收益，不抵销当前命令面分裂的近期成本。

---

**草案落点**：`.servo/worktrack/research-deliverables/sa-a-command-protocol-decision.md`

**下游依赖**：
- SA-D 的 distribution-entrypoint-contract.md 修订草案应在"命令面合同"表中加入 bundle 行（依赖本草案的 §7 决议）。
- SA-B 的事务语义决议、SA-C 的 trust boundary 决议在本草案的"bundle backend"基础上展开。
- SA-E 的 TUI/CLI 双面映射方案需要把本草案 §2.5 / §3.5 / §4.5 的 TUI 评估展开为完整映射方案。
