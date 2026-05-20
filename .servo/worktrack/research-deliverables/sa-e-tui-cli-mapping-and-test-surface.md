---
title: "SA-E: TUI/CLI Dual-Side Mapping and Test Surface Design (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-005
updated: 2026-05-07
owner: research-subagent
---

# SA-E: TUI/CLI Dual-Side Mapping and Test Surface Design (P0-071 Aggregate Backend)

> 本草案仅服务于 design phase：在 SA-A 推荐 `--backend bundle` enum 扩展、SA-B 推荐"hybrid pre-write all-or-nothing + write each-independent"事务语义的基础上，设计聚合 backend 在 TUI 与 CLI 两侧的等价映射，以及对应的测试 surface（仅设计清单与矩阵，不实施测试代码）。所有 SA-E 结论是 implementation phase 的输入，本身不修改 servo-installer.js、test_servo_installer.js 或任何真相层文档。

## 1. Executive Summary

**TUI 映射决定**：在主菜单的 `Backend: agents` 行升级为可切换的 backend 选择项（agents / claude / bundle 三选一），bundle 选择后所有现有菜单条目（diagnose / verify / dry-run / guided update / help / exit）走同一组流程，CLI 侧由 `--backend bundle` 参数携带；新增"显示当前 backend"行作为 mode-switch 入口（输入 `b` 切换 backend），不引入新的子菜单或独立的"bundle operations"层。这是 SA-A `--backend bundle` 决议在 TUI 侧的最小自然映射。

**Test Surface 决定**：既有 80 测试中 **24 个必须 mirror、19 个应该 mirror、37 个不应 mirror** 出 bundle 版本；此外新增 **22 个 multi-backend 专属测试用例**（dual-root 冲突扫描、partial-completion 暴露、prune 顺序、verify collect-then-report、TUI bundle equivalence、recovery hint 形态等）。最重要的 test-surface 决策：**partial-completion 暴露 stderr 的精确字面串契约**（如 `[aggregate] partial install: agents=ok, claude=failed`）必须以独立的字面串测试锁定，不能仅以 regex 包含校验，否则 implementation phase 的输出微小变化会让 operator-facing recovery 路径漂移。

**核心 rationale**：TUI 与 CLI 的等价是通过 **TUI 侧把 backend 选择具象化为字符串、再原样拼到 `runNodeOwned([verb, "--backend", currentBackend, ...])` 调用的 args 数组**实现的——这一拼接路径对 agents / claude / bundle 三值同形态有效，CLI 与 TUI 走完全相同的 dispatcher 入口，无需独立的"bundle code path in TUI"。这种"TUI 是 args 数组的 widget 化呈现"模型让等价证明退化为"args 数组相同 → 行为相同"的直接断言。

## 2. TUI Aggregate Operation Mapping

### 2.1 现状摘要（servo-installer.js TUI 锚点）

`runTui()` 当前形态（servo-installer.js 第 3457-3506 行）：
- 主菜单显示固定字符串 `Backend: agents`（第 3472 行）
- 6 个菜单项硬编码 `--backend agents`（第 3422 / 3437 / 3450 / 3486 / 3489 / 3492 行）
- 用户输入 1-6 触发对应分支：`runGuidedUpdateFlow` / diagnose JSON / verify / update dry-run / help / exit
- 所有动作经 `runNodeOwned([verb, "--backend", "agents", ...])` 进入与 CLI 共享的 dispatcher

TUI 没有独立的 backend handler；它是 CLI 的 args-array shaping widget。

### 2.2 推荐 TUI UX：mode-switch 单行 + 三选一

在现有 6 项菜单基础上：

**改动 1：主菜单 header 升级为可切换 backend 显示**

```
AW Installer
Backend: bundle  (press b to switch: agents / claude / bundle)

1. Guided update flow
2. Diagnose current install
3. Verify current install
4. Show update dry-run plan
5. Show CLI help
6. Exit
```

`Backend:` 行的值由会话内一个 `currentBackend` 变量持有，初值 `agents`（保持向后兼容——已有 operator 在 TTY 进入 TUI 后默认行为不变）。

**改动 2：新增 `b` 键作为 backend mode-switch 触发器**

输入 `b` / `B` 进入子 prompt：
```
Switch backend:
  1. agents (current)
  2. claude
  3. bundle (install both agents and claude)

Select backend (Enter to keep current):
```
用户选择后，`currentBackend` 更新，主菜单 header 同步反映；不影响其他状态。

**改动 3：所有菜单项的 args 数组动态拼接**

```
runNodeOwned(["diagnose", "--backend", currentBackend, "--json"])
runNodeOwned(["verify", "--backend", currentBackend])
runNodeOwned(["update", "--backend", currentBackend])
runNodeOwned(["update", "--backend", currentBackend, "--yes"])
```

这是 TUI 与 CLI 等价的关键：TUI 仅替换 `currentBackend` 字符串值，args 数组其余部分形态不变。

**改动 4：guided update flow 中显式标注 bundle 模式步骤**

`runGuidedUpdateFlow(rl)` 在 bundle 模式下输出步骤标题增加聚合提示：

```
Guided update flow (Backend: bundle)
Step 1: Diagnose current bundle (agents + claude).
[runNodeOwned(["diagnose", "--backend", "bundle", "--json"])]
Step 2: Review bundle update dry-run plan (both roots).
[runNodeOwned(["update", "--backend", "bundle"])]
Step 3: Type yes to apply bundle update via prune --all -> check_paths_exist -> install -> verify (each-independent across both roots):
[runNodeOwned(["update", "--backend", "bundle", "--yes"])]
```

注意：CLI 的事务语义（SA-B 决议的 hybrid 模型）由 dispatcher 透明承担；TUI 只在标题中显式提示"两根独立"，不重新发明事务执行流。

### 2.3 为什么不选其他映射形态

| 候选 TUI 形态 | 拒绝理由 |
|---|---|
| **multi-checkbox**（让用户勾选多个 backend） | 与 SA-A 的 `--backend` 单值 enum 决议冲突；多选 widget 在 readline-based TUI 中不自然；最终退化为"agents only / claude only / bundle"三选一 |
| **独立 bundle 子菜单**（在主菜单加 7. Bundle operations 进入二级菜单） | 命令面分裂——bundle 与 agents/claude 不再 symmetric；二级菜单引入额外 navigation depth；TUI 与 CLI 不再 1:1 |
| **每个菜单项前增加 backend prefix**（如 1a/1b/1c） | menu key 空间膨胀；用户记忆负担增加；与 SA-A "backend 是 flag、不是命令族"语义不符 |
| **modeswitch 单行 + 三选一**（本草案推荐） | 直接复用现有"Backend:"slot；切换 backend 不影响菜单结构；CLI 与 TUI 通过 args 数组拼接强等价 |

### 2.4 显式取舍

- TUI 不引入"批量 verify both backends"作为独立菜单项——bundle 模式本身就是该语义；用户切换到 bundle 后选 verify 即可。
- TUI 不在 bundle 模式下隐藏单 backend 操作——用户随时可切回 agents 或 claude 跑单根操作；mode-switch 是会话状态，不强制持久化。
- TUI 不在 bundle 模式下引入 `--continue-on-failure` 之类未在 CLI 决议的 flag——TUI 表达力严格不大于 CLI 表达力。

## 3. CLI ↔ TUI Equivalence Proof

### 3.1 等价关系定义

**等价命题**：对每一个 verb v ∈ {diagnose, verify, install, update, prune, check_paths_exist} 和每一个 backend b ∈ {agents, claude, bundle}，TUI 中选择 b 后触发 v 的 menu action，与 CLI 中执行 `servo-installer v --backend b [其他 flags]` 必须产生**相同的 dispatcher 行为、相同的磁盘副作用、相同的 stdout/stderr 输出（在相同环境前置条件下）**。

形式化为：

```
∀ v ∈ verbs, ∀ b ∈ backends, ∀ env:
  TUI[currentBackend := b].invoke(v, env) ≡ CLI(["v", "--backend", b], env)
```

### 3.2 等价的实现机制（直接通路）

servo-installer.js 当前架构使等价证明退化为字面串等同：

1. **TUI 不持有 backend-specific 业务逻辑**：所有 `runTui()` / `runGuidedUpdateFlow()` 内的执行调用都是 `runNodeOwned(args)` 形式（servo-installer.js 第 3422 / 3437 / 3450 / 3486 / 3489 / 3492 行）。
2. **`runNodeOwned(args)` 是 CLI 与 TUI 的共享单入口**（第 3351-3406 行）：CLI 路径 `main()` → `runNodeOwned(args)` 与 TUI 路径 `runTui()` → `runNodeOwned(args)` 完全同一函数。
3. **bundle 模式扩展不破坏此结构**：implementation phase 在 TUI 中把 `"agents"` 字面串替换为 `currentBackend` 变量后，TUI 调用 `runNodeOwned(["diagnose", "--backend", currentBackend, "--json"])`；CLI 调用 `runNodeOwned(["diagnose", "--backend", "bundle", "--json"])`。当 `currentBackend === "bundle"` 时，两组 args 数组完全相同。
4. **dispatcher 内部 backend 路由对 bundle 透明**：SA-B 的 hybrid 事务语义由 `runNodeXxx → backendDispatch(parsed.backend)` 在 `parsed.backend === "bundle"` 分支统一承担；TUI 与 CLI 都不感知该分支具体走 single-backend 还是 aggregate 代码路径。

### 3.3 等价路径示意

```
CLI:  argv -> main() -> runNodeOwned(args)         -> dispatcher -> backend handler -> filesystem
                          ^                                          ^
                          |                                          |
                          | (相同 args 数组)                          | (相同 backend 路由)
                          |                                          |
TUI:  menu -> runTui() -> runNodeOwned(args)         -> dispatcher -> backend handler -> filesystem
```

### 3.4 等价不变量必须保持的硬约束

1. **TUI 不允许内联 backend handler**：所有 effectful 操作必须通过 `runNodeOwned(args)`，不允许 TUI 直接调用 `installBackendPayloads` / `verifyBackend` / `pruneBackendManagedInstalls`。
2. **TUI 的 args 数组拼接顺序必须可预测**：`["verb", "--backend", currentBackend, ...其他 flags]`；不允许 TUI 任意打乱 flag 顺序导致 CLI 与 TUI 输出有差异。
3. **TUI 不允许吞掉 stdout/stderr**：`runNodeOwned` 的 console.log / console.error 输出在 TUI 模式下必须直接打到终端（这是当前实现行为，bundle 模式必须保持）。
4. **bundle 模式下 TUI 不引入额外 flag**：CLI 的 `--source github` / `--yes` / `--json` / `--agents-root` / `--claude-root` 在 TUI bundle 模式下要么不出现（当前菜单不暴露这些 flag），要么通过 prompt 在拼接时透明加入；TUI 不能为 bundle 模式新创任何 CLI 不存在的 flag。

### 3.5 等价测试义务

为锁定等价不变量，新增测试用例（详见 §6）：
- TUI bundle 模式下 menu action 触发的 args 数组必须与 CLI bundle 命令字面等同（args 数组 deepEqual 测试）。
- TUI bundle 模式下的 stdout/stderr 必须与 CLI bundle 命令的输出在前缀、行序、错误前缀（如 `[aggregate]`）上完全一致。
- TUI mode-switch 后再切换回 agents 时，args 数组必须立刻退化为 agents 形态（mode-switch 状态正确性测试）。

## 4. Failure UX in TUI

### 4.1 SA-B 事务模型在 TUI 中的暴露要求

SA-B 决议的 hybrid 事务模型在三类失败路径产生 partial completion：

| 失败类型 | SA-B 决议输出形态（CLI stderr） | TUI 必须呈现 |
|---|---|---|
| `install` 第一根写完、第二根失败 | `[aggregate] partial install: agents=ok, claude=failed` + claude 失败明细 + recovery hint | 完全相同的 stderr 文本到 TUI 终端，**不被 TUI 包装吞掉** |
| `update --yes` 第一根 apply 完、第二根 apply 失败 | `[aggregate] partial update: agents applied (verified), claude failed at <stage>` + recovery hint | 完全相同的 stderr 文本；guided update flow 在 step 4 后显式额外打印 "Step 4 result: partial completion detected; see stderr above" |
| `prune --all` 第一根删除若干后失败 | `[aggregate] partial prune: agents removed N dir(s) before failure, claude not started` + recovery hint | 完全相同的 stderr 文本到 TUI 终端 |

### 4.2 TUI 的 recovery hint 增强

在 partial completion 时，TUI 在 stderr 输出之后**额外打印**一行 TUI-only 操作引导（CLI 无此行，因为 CLI 不知道 operator 处于 TUI session 中）：

```
[aggregate] partial install: agents=ok, claude=failed
  ...claude 失败明细...
  recovery: servo-installer install --backend claude --claude-root /repo/.claude/skills

(TUI hint) Press Enter to return to the installer menu. You may switch backend to 'claude' (press b) and re-run install to recover the failed root.
```

这一 TUI-only hint 不破坏 §3 的等价不变量——它是 **TUI 终端的 idle prompt 文本**（在 `pause(rl)` 阶段输出），不是 `runNodeOwned` 的执行输出；CLI 不会输出这行（CLI 不调用 `pause`）。

### 4.3 TUI 界面状态机：partial completion 之后

partial completion 发生后，TUI 必须保持以下不变量：

1. **TUI 不自动重试失败的 backend**——operator 必须显式 mode-switch 到失败 backend 后手动 re-run。这避免 TUI 隐式发起 CLI 不会发起的副作用。
2. **TUI 不更改 currentBackend 状态**——partial completion 后 currentBackend 仍为 bundle，operator 可继续 verify / diagnose 看 bundle 状态，或主动按 `b` 切换。
3. **`pause(rl)` 后回到主菜单**——partial completion 不算崩溃，TUI 继续正常运行。

### 4.4 各 verb 的 TUI failure 显示形态

| verb | 失败时 TUI 显示 | TUI-only 增强 |
|---|---|---|
| diagnose (bundle) | 两 backend 的 issues 合并输出（SA-B each-independent collect-then-report）；exit code 体现在 TUI 不通过 `process.exit` 而是返回菜单 | 无额外 TUI hint（diagnose 不是写操作，不需要 recovery） |
| verify (bundle) | 两 backend 的 issues 按 backend 分组输出 | 无额外 TUI hint |
| install (bundle) | partial completion stderr 直接打印 | TUI hint 提示如何 mode-switch + recover failed backend |
| update --yes (bundle) | partial completion stderr 直接打印 | TUI hint 提示 recovery 命令；guided update flow 在 step 4 标注 partial 状态 |
| prune --all (bundle) | partial completion stderr 直接打印 | TUI hint 提示如何 re-run prune for failed backend |
| check_paths_exist (bundle) | 两根冲突合并输出 | 无额外 TUI hint（check 是只读，不会 partial） |

## 5. Existing 80 Test Mirroring Assessment

### 5.1 分类原则

每个既有测试归入以下三类：

- **Must mirror**：测试覆盖的 surface 在 bundle 模式下有独立的实现路径或合同条款；缺失 mirror 测试会让 bundle 模式的对应行为无人值守。
- **Should mirror**：测试覆盖的 surface 在 bundle 模式下行为预期等同于"两根分别独立 + 收敛报告"，mirror 测试提供额外回归保护但不暴露独立合同。
- **Should NOT mirror**：测试覆盖的 surface 是 single-backend 专属（如某个具体的 backend 字符串校验、Python fallback 行为、单根的 markdown frontmatter parity），bundle 模式 mirror 没有意义或会重复 must-mirror 的覆盖。

### 5.2 完整 80 测试分类清单

#### 5.2.1 Must mirror（24 个）

| 行号 | 测试名 | bundle mirror 必要性 |
|---|---|---|
| L846 | `buildNodeBackendContext keeps backend target root defaults and override flags in parity` | bundle 引入双根 context（agentsRoot + claudeRoot 同时持有）—— mirror 验证 backend === "bundle" 时返回正确的双根结构 |
| L903 | `parseNodeDiagnoseJsonArgs accepts agents and claude JSON diagnose` | bundle 是新 enum 值；mirror 验证 `--backend bundle --json` 解析正确 |
| L924 | `parseNodeDiagnoseArgs accepts agents and claude human diagnose forms` | bundle 是新 enum 值；mirror 验证 `--backend bundle` 人类可读 diagnose 解析 |
| L940 | `parseNodeUpdateJsonArgs accepts agents and claude package JSON update dry-runs` | mirror 验证 `update --backend bundle --json` 解析正确 |
| L1022 | `parseNodeUpdateDryRunArgs accepts package and agents github human-readable update dry-runs` | mirror `update --backend bundle` package source 解析（github source 与 bundle 互斥，仍 reject） |
| L1066 | `parseNodeUpdateYesArgs accepts package and agents github update apply forms` | mirror `update --backend bundle --yes` package source 解析 |
| L1119 | `parseNodeUpdateArgs wrappers keep unsupported update forms rejected` | mirror `update --backend bundle --json --yes` / `update --backend bundle --source github` 必须仍被 reject |
| L1198 | `parseNodeCheckPathsExistArgs accepts agents and claude backend target override forms` | mirror `check_paths_exist --backend bundle --agents-root X --claude-root Y` 解析双根 override |
| L1229 | `parseNodeVerifyArgs accepts agents and claude package-local verify forms` | mirror `verify --backend bundle --agents-root X --claude-root Y` 解析双根 override |
| L1246 | `parseNodeInstallArgs accepts agents and claude package-local install forms` | mirror `install --backend bundle --agents-root X --claude-root Y` 解析双根 override |
| L1263 | `parseNodePruneArgs accepts agents and claude package-local prune all forms` | mirror `prune --all --backend bundle --agents-root X --claude-root Y` 解析双根 override |
| L1694 | `servo-installer check_paths_exist agents is node-owned without Python and honors agents-root` | mirror `check_paths_exist --backend bundle` 跑 dual-root 合并扫描 |
| L1712 | `servo-installer diagnose agents human and json agents-root are node-owned without Python` | mirror `diagnose --backend bundle` 输出双 backend section（SA-B each-independent collect-then-report） |
| L1740 | `servo-installer claude read-only lifecycle paths are node-owned without Python` | mirror `verify --backend bundle` / `diagnose --backend bundle` 在 read-only 路径上的 each-independent 行为 |
| L1817 | `servo-installer claude mutating lifecycle paths are node-owned without Python` | mirror `install --backend bundle` / `update --backend bundle --yes` / `prune --all --backend bundle` 在 mutating 路径上的 hybrid 事务行为 |
| L2082 | `servo-installer verify agents is node-owned without Python for success and drift` | mirror `verify --backend bundle` 双根 success / 双根 drift / 仅一根 drift 三态 |
| L2104 | `servo-installer verify agents is node-owned for missing and invalid target states` | mirror `verify --backend bundle` 一根 missing / 一根 invalid 的合并输出 |
| L2329 | `servo-installer install agents writes a clean target without Python and verifies` | mirror `install --backend bundle` 双根 clean install + double verify |
| L2413 | `servo-installer install agents blocks non-clean target conflicts without Python or writes` | mirror `install --backend bundle` 任一根 conflict → SA-B all-or-nothing pre-write 短路，零写入 |
| L2461 | `servo-installer install agents rejects source and target readiness failures without Python` | mirror `install --backend bundle` 一根 source 失败 / 一根 target 失败的 fail-fast |
| L2522 | `servo-installer prune agents removes only same-backend managed dirs without Python` | mirror `prune --all --backend bundle` 双根都只删自己的 marker dirs |
| L2580 | `servo-installer prune agents handles missing and invalid target roots without Python` | mirror `prune --all --backend bundle` 双根 missing / invalid 的 pre-check fail-fast |
| L2775 | `servo-installer rejects unsupported install variants without Python` | mirror `install --backend bundle --source github` / `install --backend bundle --yes` 仍被 reject |
| L2801 | `servo-installer rejects unsupported local agents variants without Python` | mirror `install --backend bundle --json` / `prune --backend bundle`（缺 `--all`）仍被 reject |

#### 5.2.2 Should mirror（19 个）

| 行号 | 测试名 | bundle mirror 价值 |
|---|---|---|
| L703 | `node-owned summary and context helpers are exported for unit coverage` | 验证 bundle 相关的 helper（如 `parsedBackendRoots` 的 bundle 分支）也被 export |
| L1143 | `unsupported agents package variants are classified without Python` | mirror unsupported bundle variants 的 classification（如 `parseNodeUnsupportedPruneMissingAllArgs` 在 bundle 模式下） |
| L1473 | `update planning helpers expose direct issue and blocking behavior` | mirror update planning 在 bundle 模式下的双根 issue 合并 |
| L1520 | `collectUpdateTargetEntryIssues covers non-directory, fallback children, wrong type, and foreign markers` | mirror bundle 模式下 collectUpdateTargetEntryIssues 在双根上的独立调用 |
| L1588 | `checkPathsExistSummary reports planned paths and no conflict without creating target root` | mirror bundle 模式下 checkPathsExistSummary 双根合并报告 |
| L1609 | `check path conflict helpers classify directories, files, broken symlinks, and legacy dirs` | mirror bundle 模式下 conflict helpers 在双根独立调用的分类一致性 |
| L1667 | `checkPathsExistSummary keeps same source validation and duplicate target_dir failures` | mirror bundle source validation 在双根都需 source 时的合并行为 |
| L1795 | `servo-installer verify claude honors frontmatter transform parity without Python` | mirror bundle 模式下 frontmatter parity 检查在 claude 子根的独立行为 |
| L1854 | `servo-installer install removes same-backend managed legacy directories without Python` | mirror bundle 模式下 legacy dir 删除的 each-independent |
| L1890 | `servo-installer install blocks legacy symlink markers without Python` | mirror bundle 模式下 legacy symlink block 在双根独立的 fail-fast |
| L1931 | `servo-installer agents install removes same-backend managed legacy directories without Python` | mirror bundle 模式下 same-backend legacy 删除的 each-independent |
| L1967 | `servo-installer check_paths_exist agents reports conflicts with Python-compatible stderr` | mirror bundle 模式下 conflict stderr 形态保持兼容（前缀 `[aggregate]` 加 `[agents]` / `[claude]` 子标记） |
| L1989 | `servo-installer check_paths_exist agents stays node-owned for source and duplicate failures` | mirror bundle 模式下 source / duplicate failure 的 fail-fast |
| L2018 | `servo-installer check_paths_exist agents reports target root readiness failures without Python` | mirror bundle 模式下双根 readiness 合并报告 |
| L2155 | `servo-installer verify agents covers broken symlink and foreign marker without Python` | mirror bundle 模式下双根 broken symlink / foreign marker 的合并 |
| L2361 | `servo-installer install agents writes an existing empty target without Python` | mirror bundle 模式下双根 empty target 的同时安装 |
| L2438 | `servo-installer install agents allows unrelated target content without Python` | mirror bundle 模式下双根 unrelated content 的 install |
| L2655 | `servo-installer prune agents matches Python scan failure output shape` | mirror bundle prune scan failure 的 stderr 形态（含 `[aggregate]` 前缀） |
| L2694 | `servo-installer prune agents retains malformed same-backend marker shapes` | mirror bundle 模式下双根 malformed marker 的 retention 行为 |

#### 5.2.3 Should NOT mirror（37 个）

> 这些测试覆盖的 surface 与 bundle 模式无独立合同，mirror 没有边际价值或会重复 must-mirror 覆盖。

**5.2.3.1 单元工具测试（与 backend 无关，9 个）**

| 行号 | 测试名 | 不 mirror 理由 |
|---|---|---|
| L232 | `captureConsoleLog restores console.log for sync throw` | console.log capture 工具，与 backend 无关 |
| L246 | `captureConsoleLog restores console.log for async resolve` | 同上 |
| L259 | `captureConsoleLog restores console.log for async reject` | 同上 |
| L273 | `captureConsoleLog restores console.log for throwing thenables` | 同上 |
| L734 | `path safety policy is loaded from the shared deploy JSON` | path safety policy 与 bundle 无独立合同（SA-C 决议 path policy 不需要 bundle 字段） |
| L743 | `normalizeRelativePath rejects traversal and keeps clean relative paths` | 路径工具，无 backend 维度 |
| L758 | `payloadTargetMetadata normalizes required target metadata` | payload metadata 工具 |
| L779 | `loadBindingPayloads rejects oversized JSON before parsing` | payload 加载工具 |
| L794 | `computePayloadFingerprint matches the Python payload contract order` | fingerprint 工具，与 Python 兼容性无关 bundle |

**5.2.3.2 single-backend 专属语义测试（10 个）**

| 行号 | 测试名 | 不 mirror 理由 |
|---|---|---|
| L1281 | `target dir helpers share duplicate checks and keep legacy dirs only in known set` | target dir helper 是单 backend 内部 helper，bundle 模式下分别在双根调用（已被 must-mirror L2522 / L1854 间接覆盖） |
| L1345 | `buildInstallPlan can reuse cached payload text instead of rereading payload.json` | install plan caching 是单 backend 内部行为，bundle 模式分别独立 cache |
| L1401 | `verifyAgentsBackend passes cached payload text into deployed skill verification` | agents 专属 verify 内部细节 |
| L2196 | `servo-installer verify agents matches Python reference output for success and drift` | Python reference parity 是 single-backend 历史合同；bundle 模式无 Python reference |
| L2390 | `servo-installer install agents matches Python reference on clean target output shape` | 同上 |
| L2040 | `servo-installer check_paths_exist agents matches Python reference output for success and conflict` | 同上 |
| L2730 | `managed directory identity guard refuses replacement during pruning` | 内部 guard，bundle 模式自动继承 |
| L2752 | `servo-installer prune agents matches Python reference output shape` | Python reference parity |
| L2845 | `updatePlanSummary reports a nonblocking dry-run plan for missing target root` | update plan 内部 helper，bundle 模式分别在双根独立调用 |
| L3364 | `servo-installer update agents human-readable dry-run matches Python reference output shape` | Python reference parity |

**5.2.3.3 github source 测试（与 bundle 互斥，13 个）**

> SA-A 决议中 `--backend bundle` 仅支持 package source（github source 是 agents 专属）；以下测试在 bundle 模式下应 reject 而非 mirror。

| 行号 | 测试名 | 不 mirror 理由 |
|---|---|---|
| L2887 | `github source archive context feeds update JSON planning with target/source separation` | github source agents only |
| L2931 | `servo-installer github source human-readable dry-run is node-owned with mocked archive` | 同上 |
| L2972 | `servo-installer github source yes applies update through Node-owned composition with mocked archive` | 同上 |
| L3015 | `downloadGithubArchive enforces content length and streamed size limits` | github archive 下载工具 |
| L3048 | `downloadGithubArchive retries retryable failures and does not retry non-retryable responses` | 同上 |
| L3092 | `servo-installer github source recovery hint preserves source arguments after apply failure` | github source recovery |
| L3140 | `github source context cleans extracted temp dir when target context fails` | github archive cleanup |
| L3182 | `github source archive validation rejects unsafe members and sha mismatch` | github archive 校验 |
| L3248 | `github source archive extraction enforces uncompressed size limits` | github archive 解压限制 |
| L3299 | `servo-installer github source update paths reject invalid local inputs without Python` | github source 解析 |
| L3341 | `servo-installer update agents human-readable dry-run is node-owned without Python` | 单根 agents update（bundle 由 must-mirror L1817 间接覆盖） |
| L3386 | `servo-installer update agents human-readable dry-run reports blocking preflight without applying` | 单根 agents preflight |
| L3573 | `servo-installer update claude recovery hint preserves claude-root override after apply failure` | 单根 claude recovery hint（bundle recovery hint 是新合同，由 §6 新增用例覆盖） |

**5.2.3.4 既有 update 单根测试（5 个）**

| 行号 | 测试名 | 不 mirror 理由 |
|---|---|---|
| L3426 | `servo-installer update agents yes installs and verifies from missing root without Python` | 单根 update apply（bundle 由 must-mirror L1817 间接覆盖 + §6 新增 partial-completion 覆盖） |
| L3463 | `servo-installer update agents yes matches Python reference output shape` | Python reference parity |
| L3485 | `servo-installer update agents yes refreshes drifted and stale managed installs without Python` | 单根 drift refresh |
| L3517 | `servo-installer update agents yes blocks preflight issues without applying` | 单根 preflight block |
| L3544 | `servo-installer update agents yes prints recovery hint after apply failure` | 单根 recovery hint |

### 5.3 分类汇总

| 类别 | 数量 | 占比 |
|---|---|---|
| Must mirror | 24 | 30% |
| Should mirror | 19 | 24% |
| Should NOT mirror | 37 | 46% |
| **合计** | **80** | **100%** |

## 6. New Multi-Backend Test Cases Checklist

> 以下 22 个测试用例是 bundle 模式专属，无单 backend 等价；每条用例附"Acceptance question"作为 implementation phase 验收锚点。**不实施测试代码**，仅清单 + 描述。

### 6.1 Parser-level（5 个）

1. **`parseNodeXxxArgs accepts --backend bundle for all 6 commands`**
   - 描述：`parseNodeDiagnoseArgs` / `parseNodeDiagnoseJsonArgs` / `parseNodeVerifyArgs` / `parseNodeInstallArgs` / `parseNodeUpdateDryRunArgs` / `parseNodeUpdateJsonArgs` / `parseNodeUpdateYesArgs` / `parseNodePruneArgs` / `parseNodeCheckPathsExistArgs` 接受 `--backend bundle` 并返回 `{ backend: "bundle", agentsRoot: undefined, claudeRoot: undefined }`（或同时包含 override 时双 root 都体现）。
   - Acceptance question：`--backend bundle` 是否被所有 9 个 parser 接受为合法 enum 值？返回的 backend 字段是字符串 `"bundle"` 而非 list 或其他形态？

2. **`parseNodeXxxArgs accepts dual-root override with --backend bundle`**
   - 描述：在 bundle 模式下同时指定 `--agents-root /a --claude-root /c`，所有 parser 返回 `{ backend: "bundle", agentsRoot: "/a", claudeRoot: "/c" }`。
   - Acceptance question：bundle 模式 parser 是否同时保留 agentsRoot 与 claudeRoot 两个字段？单 backend 模式是否仍保持只有相关 root 字段？

3. **`parseNodeXxxArgs rejects --backend bundle with --source github`**
   - 描述：`update --backend bundle --source github --github-repo X --github-ref Y --github-archive-sha256 Z` 应被所有 update parser reject（github source 与 bundle 互斥）。
   - Acceptance question：bundle + github source 的 cross-flag 冲突是否在 parser 层 fail-fast 而非 dispatcher 层 fail-fast？

4. **`parseNodeXxxArgs rejects --backend bundle with single-root override`**
   - 描述：`install --backend bundle --agents-root /a`（缺 `--claude-root`）的语义边界——是隐含 claude 用默认 root，还是强制要求双根成对出现？由 SA-C 决议；测试需锁定决议结果。
   - Acceptance question：bundle 模式下单 root override 的行为是 implicit-default-other-root 还是 require-both-roots？parser 报错形态是什么？

5. **`backendAllowed includes bundle for all 6 commands but not for unsupported variants`**
   - 描述：所有 6 命令的 `backendAllowed([agentsBackend, claudeBackend, bundleBackend])` allowlist 中应包含 bundle；unsupported variants（如 `parseNodeUnsupportedPruneMissingAllArgs`）的 allowlist 应明确决定是否纳入 bundle。
   - Acceptance question：bundle 是否被所有 6 个主命令接受？unsupported variants 的 bundle 处理是否一致？

### 6.2 Dual-root 冲突扫描（3 个）

6. **`check_paths_exist --backend bundle merges conflicts from both roots`**
   - 描述：seed agentsRoot 有 `aw-skill-A` 冲突、claudeRoot 有 `skill-B` 冲突，运行 `check_paths_exist --backend bundle` 应在 stderr 中合并报告两根冲突，按 backend 分组显示。
   - Acceptance question：合并报告的格式是否清晰区分两根来源？退出码是否在任一根有冲突时为 1？

7. **`install --backend bundle pre-write all-or-nothing on dual-root conflict`**
   - 描述：seed agentsRoot clean、claudeRoot 有 conflict，运行 `install --backend bundle` 应：(1) 退出码 1，(2) **零写入**——agentsRoot 与 claudeRoot 都没有 newly created skill dir。
   - Acceptance question：SA-B 的 pre-write all-or-nothing 是否在 bundle install 中得到正确实现？agents 根是否真的零副作用？

8. **`update --yes --backend bundle pre-check fail-fast on either root blocking issue`**
   - 描述：seed agentsRoot 有 blocking preflight issue、claudeRoot clean，运行 `update --backend bundle --yes` 应在 apply 阶段开始前 fail-fast，两根都不进入 apply。
   - Acceptance question：bundle update 的 pre-check fail-fast 是否覆盖任一根的 blocking issue？两根的 prune / install / verify 是否都没有发生？

### 6.3 Partial-completion 暴露（4 个）

9. **`install --backend bundle prints partial completion stderr on second-root failure`**
   - 描述：模拟 agents 写成功 + claude 写失败（如 claude root 临时无写权限），运行 `install --backend bundle` 应：(1) 退出码 1，(2) stderr 包含字面串 `[aggregate] partial install: agents=ok, claude=failed`，(3) stderr 含 claude 失败明细，(4) stderr 含 single-backend recovery hint `servo-installer install --backend claude --claude-root <path>`。
   - Acceptance question：partial completion stderr 的精确字面串是否锁定？recovery hint 是否引导 operator 调用 single-backend 命令？agents 已写入的 skill dir 是否保留？

10. **`update --yes --backend bundle prints partial completion stderr on stage failure`**
    - 描述：模拟 agents update apply 成功 verify 通过 + claude update apply 在 install 阶段失败，stderr 应包含 `[aggregate] partial update: agents applied (verified), claude failed at install`。
    - Acceptance question：stage 标签（prune / install / verify）是否在 partial update 中明确？agents 的新版是否保留？

11. **`prune --all --backend bundle prints partial completion stderr on first-root delete failure`**
    - 描述：模拟 agents prune 删除若干 dir 后 throw（如某 dir 删除时被外部进程占用），运行 `prune --all --backend bundle` 应：(1) 退出码 1，(2) stderr 含 `[aggregate] partial prune: agents removed N dir(s) before failure, claude not started`，(3) claude root 完全未触动。
    - Acceptance question：prune 顺序是否固定（agents 先 / claude 后）？partial prune stderr 是否锁定？

12. **`verify --backend bundle collect-then-report on dual-root drift`**
    - 描述：seed 两根都有 drift，运行 `verify --backend bundle` 应：(1) 退出码 1，(2) stdout / stderr 包含两根的完整 drift list（按 backend 分组），(3) 不在第一根 drift 时短路。
    - Acceptance question：verify bundle 的 collect-then-report 是否真的 visit 了两根？输出顺序是否固定？

### 6.4 Dispatcher / runtime 等价（3 个）

13. **`runNodeOwned dispatches --backend bundle to bundle handler for all 6 commands`**
    - 描述：mock `installBackendPayloads` / `verifyBackend` / `pruneBackendManagedInstalls` / 等下游函数，断言 `runNodeOwned(["install", "--backend", "bundle"])` 触发 bundle handler 而非 single-backend handler；其他 5 命令同理。
    - Acceptance question：dispatcher 是否在 backend === "bundle" 时正确分流？是否有任何 verb 漏掉 bundle 分支？

14. **`buildNodeBackendContext for bundle returns dual-root context`**
    - 描述：`buildNodeBackendContext({ backend: "bundle", agentsRoot: "/a", claudeRoot: "/c" })` 返回的 context 同时包含 agents 与 claude 两个 sub-context（具体形态由 SA-C 决议）。
    - Acceptance question：bundle context 的形态是否可被下游 each-independent 调用？两个 sub-context 是否相互不干扰？

15. **`expectedPayloadVersions includes bundle entry`**
    - 描述：`expectedPayloadVersions["bundle"]` 应被定义（具体值由 SA-D 决议；可能是 union 或新版本号）。
    - Acceptance question：bundle 的 payload version 合同是什么？是否与 agents / claude 各自的 version 都兼容？

### 6.5 TUI ↔ CLI 等价（4 个）

16. **`TUI menu items invoke runNodeOwned with currentBackend variable`**
    - 描述：mock `runNodeOwned`，模拟 TUI 主菜单输入：先按 `b` 选择 bundle、再按 `2` 触发 diagnose，断言 `runNodeOwned` 被调用一次且 args === `["diagnose", "--backend", "bundle", "--json"]`。
    - Acceptance question：TUI 是否真的把 currentBackend 字符串拼入 args 数组？是否有任何菜单项硬编码 `"agents"` 或 `"claude"`？

17. **`TUI mode-switch updates currentBackend and reflects in subsequent menu actions`**
    - 描述：TUI 输入序列 `b → 2 → 2 → b → 1 → 2`（切换到 bundle、运行 verify、切换到 agents、运行 verify）。断言 `runNodeOwned` 被调用两次：第一次 args 含 `"--backend", "bundle"`，第二次 args 含 `"--backend", "agents"`。
    - Acceptance question：mode-switch 状态是否在会话内正确持久？切换是否影响下一个 action 而非当前 action？

18. **`TUI guided update flow uses bundle backend in all three steps`**
    - 描述：TUI 切换到 bundle 后选 `1` 进入 guided update flow。断言三个 `runNodeOwned` 调用的 args 数组均含 `"--backend", "bundle"`，且 step 标题在 stdout 中标注 `(Backend: bundle)`。
    - Acceptance question：guided flow 是否在 bundle 模式下正确传播 currentBackend？step 标题是否提示用户当前是 bundle？

19. **`TUI displays partial-completion stderr without truncation in bundle mode`**
    - 描述：TUI 触发 install bundle 时模拟 partial completion，断言 TUI 终端输出包含完整的 SA-B partial completion stderr 字面串 + TUI-only "Press Enter..." hint。
    - Acceptance question：TUI 是否吞掉任何 stderr？TUI-only hint 是否在 stderr 之后单独打印？

### 6.6 Recovery hint 形态（2 个）

20. **`bundle install partial completion recovery hint format`**
    - 描述：partial install 失败时 stderr 的 recovery hint 必须是 single-backend 格式（`servo-installer install --backend claude --claude-root <path>`），不是 bundle 格式（不应建议 `servo-installer install --backend bundle ...`，因为重跑 bundle 会让 agents 已成功的根重新走一遍 install 路径）。
    - Acceptance question：recovery hint 是否引导到 single-backend 命令？hint 是否包含正确的失败 backend root path？

21. **`bundle update --yes partial completion recovery hint format`**
    - 描述：partial update apply 失败时 stderr 的 recovery hint 必须是 `servo-installer update --backend <failed_backend> --yes [其他保留 flags]`；不应建议重跑 bundle update。
    - Acceptance question：recovery hint 是否携带原 update 的 source / root override flags（按 SA-B 决议保留传入参数）？

### 6.7 治理与边界（1 个）

22. **`unsupported servo-installer fallback covers --backend bundle invalid combinations`**
    - 描述：构造一组无效的 bundle 组合（`prune --backend bundle`（缺 `--all`）/ `install --backend bundle --json` / `verify --backend bundle --yes` / `--backend bundle --source github`），断言所有组合走 `unsupported servo-installer command or options for Node-only distribution` fallback 路径，stderr 提示 helpful message。
    - Acceptance question：bundle 模式下 invalid 组合是否一致 reject？fallback message 是否提示 operator 正确的 bundle 用法？

## 7. Test Coverage Matrix

> 行 = 6 个 verb；列 = 3 个 backend 模式（agents / claude / bundle）；每个 cell 列出该 verb × backend 组合需要覆盖的 test category 标签。
>
> Categories：
> - **P** = parser（解析层；含 deepEqual / null reject）
> - **D** = dispatch（dispatcher 路由 / context build）
> - **S** = success path（happy path 端到端）
> - **F** = failure path（包含 partial completion / fail-fast / drift / conflict 等）

| verb \ backend | agents | claude | bundle |
|---|---|---|---|
| **install** | P / D / S / F | P / D / S / F | P / D / S / F (含 dual-root pre-write all-or-nothing 短路 + partial completion stderr 锁定 + recovery hint 形态) |
| **update** | P / D / S / F | P / D / S / F | P / D / S / F (含 pre-check fail-fast + apply partial completion + stage 标签 + recovery hint 形态；github source 与 bundle 互斥应在 P 层 reject) |
| **verify** | P / D / S / F | P / D / S / F | P / D / S / F (含 collect-then-report each-independent + 双根 drift 合并报告 + 按 backend 分组) |
| **prune --all** | P / D / S / F | P / D / S / F | P / D / S / F (含 pre-check fail-fast + delete first-fail-stop + partial prune stderr 锁定 + claude 未触动断言) |
| **check_paths_exist** | P / D / S / F | P / D / S / F | P / D / S / F (含 dual-root conflict 合并扫描 + 按 backend 分组 + 退出码合并) |
| **diagnose** | P / D / S / F | P / D / S / F | P / D / S / F (含 collect-then-report + JSON 输出含 agents / claude 两 section + 退出码 0) |

**矩阵汇总**：
- 6 verbs × 3 backends = 18 cells
- 每个 cell 需覆盖 P / D / S / F 4 类测试
- 既有 80 测试已覆盖 agents 与 claude 两列共 12 cells（每个 cell 由 must / should mirror 候选共 5-7 个测试组成）
- bundle 列 6 cells 由 §6 的 22 个新增测试 + §5 的 24 个 must-mirror 共同覆盖

## 8. Implementation Phase Hand-off Notes

### 8.1 必须解决的 design-phase 未决项

implementation phase 启动前必须确认的合同条款（依赖 SA-C / SA-D 决议）：

1. **bundle 模式下单根 override 的语义**（影响 §6.1 用例 4）：`install --backend bundle --agents-root /a`（缺 `--claude-root`）是 implicit-default-other-root 还是 require-both-roots？SA-C 决议必须在 implementation 前给出。
2. **`expectedPayloadVersions["bundle"]` 的具体值**（影响 §6.4 用例 15）：bundle 是否引入新的 payload version 字符串，还是 union 现有两个 version？SA-D 决议必须在 implementation 前给出。
3. **bundle context 的形态**（影响 §6.4 用例 14）：`buildNodeBackendContext({ backend: "bundle", ... })` 返回的对象是 `{ subContexts: [agentsCtx, claudeCtx] }` 还是 `{ agents: ctx, claude: ctx }` 还是 list？SA-C 决议必须给出具体形态。
4. **partial-completion 顺序合同**（影响 §6.3 用例 11）：bundle 模式下 install / update / prune 的执行顺序是 agents-first 固定，还是 claude-first 固定，还是某种字典序？SA-B 已决议 first-fail-stop，但具体顺序应在 implementation 前锁定为不变量。

### 8.2 implementation phase 必须遵守的合同

1. **TUI 不引入 backend-specific business logic**：所有 effectful 操作通过 `runNodeOwned(args)`，TUI 仅负责 args 数组拼接与 readline 交互。
2. **partial completion stderr 的字面串严格锁定**：`[aggregate] partial install: agents=ok, claude=failed` 等格式必须以独立的字面串测试断言（assert.match 或 assert.equal），不能仅用 regex 包含。Implementation phase 不得在 stderr 中夹入任何会破坏字面串的额外内容（如时间戳、ANSI color codes）。
3. **TUI mode-switch 的状态边界**：currentBackend 是 `runTui()` 函数内的 local variable，不持久化到磁盘；TUI 重启回到默认 agents。
4. **bundle 模式不实施全量回滚**：SA-B 决议 each-independent write 阶段不回滚；implementation 不得在 bundle handler 中引入快照 / 反向操作 / commit-prepare-rollback 三阶段事务。
5. **CLI 与 TUI 等价不变量**：每个新增 multi-backend 测试用例应同时被 CLI 与 TUI 入口验证（detail：用例 16-19 已专门覆盖 TUI 侧）。

### 8.3 测试实施推荐顺序

1. **第 1 批（解析层）**：用例 1-5（5 个），不依赖任何 dispatcher 实现，可在 parser 实现完成后立即跑通。
2. **第 2 批（dispatcher 等价）**：用例 13-15（3 个），依赖 dispatcher 路由完成。
3. **第 3 批（pre-write 短路）**：用例 6-8（3 个），依赖 pre-write all-or-nothing 实现。
4. **第 4 批（partial completion）**：用例 9-12（4 个），依赖 partial completion stderr 实现 + recovery hint 实现。
5. **第 5 批（recovery hint）**：用例 20-21（2 个）。
6. **第 6 批（TUI 等价）**：用例 16-19（4 个），依赖 TUI mode-switch 实现。
7. **第 7 批（边界 / fallback）**：用例 22（1 个）。

### 8.4 既有 80 测试的 mirror 实施顺序

implementation phase 的 mirror 测试推荐顺序：

1. **Must mirror 优先**：24 个 must-mirror 测试覆盖 bundle 模式的核心合同 surface，应与新增 22 用例同步实施。
2. **Should mirror 后置**：19 个 should-mirror 测试在 must-mirror 全部 green 后追加，提供回归保护。
3. **Should NOT mirror 不实施**：37 个 should-not mirror 测试明确不写 bundle 版本；implementation review 时若发现有人误写，应作为 over-engineering 移除。

### 8.5 验收 checklist（implementation phase Gate）

- [ ] 所有 22 个新增多 backend 测试用例 green
- [ ] 24 个 must-mirror 测试 green
- [ ] 19 个 should-mirror 测试 green
- [ ] 6×3 = 18 cells 测试矩阵每 cell 覆盖 P / D / S / F 4 类
- [ ] CLI ↔ TUI 等价不变量（§3.4）通过用例 16-19 锁定
- [ ] partial completion stderr 字面串通过用例 9-11 / 20-21 锁定
- [ ] 既有 80 测试零退化
- [ ] TUI 不引入 backend-specific business logic（review 时 grep TUI 函数体确认）

---

**草案落点**：`.servo/worktrack/research-deliverables/sa-e-tui-cli-mapping-and-test-surface.md`

**下游依赖**：
- T-INTEGRATE 整合本草案 §2 / §3 / §4 到统一 design phase research report 的"7. TUI / CLI 双面映射 + 测试 surface"章节。
- implementation phase 在拿到 SA-C / SA-D 的最终合同形态后，按本草案 §8 的实施顺序展开测试编写与 TUI 改造。
