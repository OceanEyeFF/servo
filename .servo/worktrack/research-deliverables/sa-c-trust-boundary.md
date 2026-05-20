---
title: "SA-C: Dual-Root Trust Boundary Extension Draft (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-003
updated: 2026-05-07
owner: research-subagent
---

# SA-C: Dual-Root Trust Boundary Extension Draft

> 目的：为 P0-071 聚合 backend 模式（一次命令同时安装 `agents` + `claude` 两个分发）设计双目标根（dual-root）下的信任边界扩展规则。本草案不修改 `path_safety_policy.json`，不修改 `servo-installer.js`，不回写真相层文档；仅作为 design phase 决议材料。

> 上游依赖：本设计假设 SA-A 的命令面 protocol 决议存在（无论选择哪种语法形式，aggregate mode 在内部都解析为"两个独立 backend context 顺序执行"），并且 SA-B 的事务语义决议会处理 install/update 跨 backend 的失败回滚口径；本节只负责 trust boundary 维度。

---

## 1. Executive Summary

### 三项 top-level 决策

1. **双根冲突短路口径采取"`per-root invariant 必须各自闭合`"原则**：每个根独立地按照单 backend 信任边界进行扫描；只要任何一个根触发"既有 trust boundary 现行短路条件"（target root 缺失/类型异常、unrecognized-target-directory、wrong-target-entry-type、foreign-managed-directory、payload-contract-invalid 等），aggregate 操作必须停止，不允许"在 root A 上失败但在 root B 上继续"。在 install/update 路径上 aggregate 的 dual-root 短路是 fail-closed；在 prune/verify 路径上仍按下文具体规则区分。

2. **`prune --all` 在 aggregate 下采取 "顺序 + 收集，不跨根回滚"**：先对 `agents` 根执行（按 backend ASCII 排序：agents 在 claude 之前），完成后再对 `claude` 根执行；任一根 prune 命令在前置 `targetRootReadyIssuesForAction` 阶段失败，aggregate 立即停止，不进入第二根；删除阶段已经发生的删除是 idempotent（marker-gated），不做"撤销重建"。

3. **`verify` 在 aggregate 下采取 "collect-then-report，但 exit code fail-fast"**：两个根都执行 `verifyBackend`，所有 issues 一并汇报给 operator（不在第一个根失败时静默跳过第二根）；只要任一根有 issue，aggregate verify 退出码为 1。这维持了 `verify` 既有的"严格只读复验"语义，同时避免运维者只看到一半信息。

### 1-paragraph 决策依据

聚合 backend 的本质是 operator 便利层（charter 张力声明已说明），不重定义底层 trust boundary。因此 aggregate mode 必须不引入"任何单 backend 模式下不允许的写或删除"。两根之间是独立的 target root，分别由各自的 `marker.backend` 字段守护；既有"managed-only path deletion"和"root-path containment"约束在每根上仍逐根生效，没有"跨根托管"的概念。`path_safety_policy.json` 的字段含义（`exact_sensitive_target_repo_roots`、`recursive_sensitive_target_repo_roots`、`home_relative_recursive_sensitive_target_repo_roots`、`allowed_target_repo_root_prefixes`）都是描述 target repo root 的全局约束，不区分 backend，因此**无需新增 multi-root 字段**。aggregate mode 只在 caller 侧组合两次单 backend context，policy 文件保持不变；trust boundary 增量都落在 servo-installer.js 的 dispatcher 行为，不落在 policy schema。

---

## 2. Dual-Root Conflict Scan Rules

### 2.1 名词约定

- **agents 根**：默认 `<targetRepoRoot>/.agents/skills`（受 `--agents-root` override），单 backend 内部表示为 `targetRoot_agents`，下面用 R_a。
- **claude 根**：默认 `<targetRepoRoot>/.claude/skills`，受 `--claude-root` override，下面用 R_c。
- **同名 skill 双根并存场景**：对同一 `skill_id`，agents 端表现为 R_a/`aw-{skill_id}/`，claude 端表现为 R_c/`{skill_id}/`（来自 `deploy-mapping-spec.md` 的 target 命名约定）。这是合法形态，不是冲突。
- **冲突**：指 trust boundary 意义上的"必须短路或必须警告"的状态。下表的"合法/非法"指 aggregate 操作能否继续；"非法"等价于"aggregate 必须 throw 或 issue"。

### 2.2 合法性真值表（per-operation × dual-root state）

下表的列含义：
- **legal under aggregate**：是否允许 aggregate 命令前进。
- **operation scope**：哪个命令（`install` / `update --yes` / `verify` / `prune --all` / `check_paths_exist` / `diagnose`）受影响。
- **operator-visible message strategy**：消息 payload 的结构。

#### 表 A：Install / `update --yes` / `check_paths_exist`（写入路径）

| # | R_a 状态 | R_c 状态 | 同 skill_id 是否在两根都存在 | content alignment | legal under aggregate? | strategy |
|---|----------|----------|--------------------------------|-------------------|------------------------|----------|
| A1 | clean (no managed dir for skill) | clean (no managed dir for skill) | n/a | n/a | legal | 正常 install/update plan：先 R_a，再 R_c；`check_paths_exist` 输出两根 `plannedTargetPaths` |
| A2 | managed dir 存在且 marker 与 source binding 一致 | managed dir 存在且 marker 与 source binding 一致 | yes | matches contract（marker 验过） | legal | install 在 update flow 下走"destructive reinstall"；非 update 直接 install 触发 `existing target path` conflict（既有逻辑），向 operator 提示走 update 路径 |
| A3 | managed dir 存在且 marker 一致 | managed dir 存在但 `marker.backend !== claude` 或 `marker.skill_id` 漂移 | yes | diverges | illegal | aggregate 在到达 R_c 之前就把 R_c 的 issue 列出（issue code 复用 `unrecognized-target-directory` 或 `foreign-managed-directory`）；`update --yes` 必须停在 R_c 的 update plan，不能只对 R_a 写入 |
| A4 | unrecognized-target-directory（已存在同名目录但无 marker） | clean | possibly | n/a | illegal | aggregate 在 R_a 触发 `unrecognized-target-directory`，立刻停止；R_c 不被触碰；message 复用单 backend 既有文案 + `[backend=agents]` 前缀 |
| A5 | clean | unrecognized-target-directory | possibly | n/a | illegal | 对称 A4：aggregate 在 R_c 触发 `unrecognized-target-directory`，立即停止；issue prefix `[backend=claude]` |
| A6 | wrong-target-root-type（路径是文件、broken symlink、symlink-to-dir） | clean | n/a | n/a | illegal | 在前置 `targetRootReadyIssuesForAction` 阶段失败；任一根的 wrong-target-root-type 导致 aggregate 不写入任何根（fail-closed） |
| A7 | clean | wrong-target-root-type | n/a | n/a | illegal | 对称 A6 |
| A8 | R_a 不存在（missing-target-root） | R_c 不存在 | n/a | n/a | legal（仅 install/update --yes） | install 路径会 `ensureInstallTargetRoot` 创建；missing-target-root 在 install 前置过滤后不视为短路，与单 backend 既有语义一致 |
| A9 | R_a outside `allowed_target_repo_root_prefixes`（override 错） | n/a | n/a | n/a | illegal | `validateTargetRepoRoot` 在 context 构造阶段就抛出；aggregate 永不进入两根遍历 |
| A10 | R_a inaccessible（EACCES/ENOENT mid-flight） | clean | n/a | n/a | illegal | aggregate 抛错短路；不允许"R_a 不可达就跳到 R_c"的回退行为；理由：如果一个根不可达，operator 必须显式排查后再次执行 |
| A11 | R_a clean | R_c inaccessible | n/a | n/a | illegal | 对称 A10 |
| A12 | R_a managed dir 存在且 ok | R_c 同 skill_id 目录存在但是 `wrong-target-entry-type`（symlink 等） | yes | n/a | illegal | 短路；issue 既有 code 直接复用，不引入新 code |

#### 表 B：`prune --all`（删除路径）

| # | R_a 状态 | R_c 状态 | legal under aggregate? | strategy |
|---|----------|----------|------------------------|----------|
| B1 | clean / 无 managed dir | clean / 无 managed dir | legal（no-op） | 两根都返回 `no managed skill dirs found at <root>` |
| B2 | 存在多个 managed dir，marker 一致 | 存在多个 managed dir，marker 一致 | legal | 顺序：先 R_a 全删，再 R_c 全删；每根独立计数；最终汇总 `removed_count.agents` 与 `removed_count.claude` |
| B3 | 存在 managed dir，但 dir 内不可写 | clean | illegal | R_a 删除阶段抛错，aggregate 立即终止；不进入 R_c；理由：保持"不跨根猜测下一步"（与单 backend 一致） |
| B4 | clean | 存在 managed dir，但 dir 内不可写 | illegal | aggregate 在 R_a no-op 之后进入 R_c，R_c 失败；R_a 不撤回（已经无操作） |
| B5 | unrecognized-target-directory（无 marker 占位） | clean | legal but warning | prune 既有语义不会删除无 marker 目录；aggregate 应同样不删，但在 stdout 警告 `[agents] X unrecognized directories preserved` |
| B6 | foreign-managed-directory（marker.backend === claude，但物理在 .agents/skills 下） | n/a | legal but warning | 这是 misplaced 安装；prune 不删（既有逻辑），aggregate 也不删；issue 加入 stderr 警告 |
| B7 | wrong-target-root-type（target root 本身是文件 / symlink） | clean | illegal | 在 `targetRootReadyIssuesForAction` 短路；R_a 失败导致 aggregate 不进入 R_c |
| B8 | clean | wrong-target-root-type | illegal | 对称 B7：R_a 完成 no-op 之后进入 R_c 失败；aggregate 整体退出非零 |

#### 表 C：`verify`（只读路径）

| # | R_a 状态 | R_c 状态 | legal under aggregate? | strategy |
|---|----------|----------|------------------------|----------|
| C1 | 无 issue | 无 issue | legal（exit 0） | 输出两根 verify summary，每根自带 backend prefix |
| C2 | 有 issue | 无 issue | legal but exit 1 | 两根的 issues 都被收集；aggregate 返回 exit code 1 |
| C3 | 无 issue | 有 issue | legal but exit 1 | 对称 C2 |
| C4 | 有 issue | 有 issue | legal but exit 1 | 收集两根所有 issues；不去重（不同 backend） |
| C5 | R_a missing-target-root | R_c missing-target-root | legal but exit 1 | 两根都报 missing-target-root；aggregate 返回 exit 1 |
| C6 | R_a inaccessible（IO 错误） | n/a | illegal（abort） | 对 IO 错误，verify 既有逻辑会抛 Error；aggregate 直接 abort，不掩盖；message 包含 backend prefix |

#### 表 D：`diagnose`（只读路径）

| # | R_a 状态 | R_c 状态 | legal under aggregate? | strategy |
|---|----------|----------|------------------------|----------|
| D1 | 任意状态 | 任意状态 | legal（始终 exit 0） | 与既有 `diagnose` 语义一致：发现 issue 仍可 exit 0；输出格式见 §7 |
| D2 | R_a IO 错误 | 任意 | illegal（abort with non-zero） | diagnose 不掩盖 IO 错误；aggregate abort |

### 2.3 关于"同 skill_id 双根 content diverges"的口径

aggregate 不引入"跨根一致性约束"。两根的 content 是不是同一 canonical source 的 deployment，由 source binding 自身保证（每根各自的 `verifySourceBinding`）；aggregate 不跨根做"agents 上的 marker.payload_version 是否等于 claude 上的 marker.payload_version"这种比较——这是 source binding 的责任，不是 trust boundary 的责任。但 aggregate 仍必须保证：每根各自的 source binding 都通过；任何一根失败就停止，避免出现"agents 已写新版本而 claude 仍是旧版本"的混合状态（具体回滚由 SA-B 决议）。

---

## 3. Dual-Root `prune --all` Boundary

### 3.1 顺序与失败短路

- **执行顺序**：固定为 `agents` → `claude`（按 backend 名 ASCII 字典序；这一选择有两个原因：(1) 减少非确定性，便于 operator 复现；(2) 与 cliFlags / backendTargetRootConfig 中 agents 已是 default backend 的语义一致）。
- **前置阶段失败短路**：每根的 `targetRootReadyIssuesForAction` 失败导致 aggregate 立即抛错，第二根不执行。前置阶段包括：target root 类型校验、broken symlink、wrong-target-root-type。
- **删除阶段失败短路**：当任一根的 `rmSync` 抛错（EACCES、EBUSY 等），aggregate 抛错，立即返回非零；第二根不再执行。
- **跨根回滚**：**不做任何跨根回滚**。理由：prune 删除的目标是 marker-gated 的受管目录，删除不可逆；尝试"撤销 R_a 的 prune"会反向把"实际不该出现的 deployment"重建出来，违反"deploy target 不是 source of truth"。

### 3.2 部分成功语义

- aggregate `prune --all` 在 R_a 成功 + R_c 失败的场景下，operator 看到的是"R_a 已 prune（且 marker 已被 invalidate），R_c 的失败原因清单"。这种部分成功必须以 stderr 明确说明，不能让 operator 误以为整体失败 = 完全无变更。
- 输出 schema（建议）：
  ```text
  [agents] removed managed skill dir <path>  (xN lines)
  [agents] prune complete: removed=N, unrecognized_preserved=M
  [claude] error: <message>
  aggregate prune partial: agents=ok, claude=failed
  ```

### 3.3 prune --all 的越界保护

- 既有 `pruneBackendManagedInstalls` 通过 `marker.backend === context.backend` 二次过滤，保证不删除 cross-backend 目录。aggregate 依次为两根传入正确的 backend context，保证仍然不会"用 claude context 删 agents 目录"。
- aggregate 不能引入"用一个 sweep 调用同时清扫两个根"的实现，必须严格分两次 context 构造、两次 `pruneBackendManagedInstalls`。

---

## 4. Dual-Root `verify` Short-Circuit

### 4.1 决议：collect-then-report，exit code fail-fast

- 两根都执行 `verifyBackend(context_agents)` 与 `verifyBackend(context_claude)`，结果合并为 `aggregate.results = [verify_a, verify_c]`。
- aggregate exit code 计算：`max(verify_a.exit, verify_c.exit)`，即任一根有 issue → exit 1。
- 输出顺序与 prune 一致：先 agents 后 claude；每根的 issue 列表独立打印，operator 一目了然。

### 4.2 与 fail-fast 的对比

| 选项 | 优点 | 缺点 | 决议 |
|------|------|------|------|
| fail-fast（R_a 失败立即停） | 输出量少 | operator 修完 R_a 后还得再 verify 才知道 R_c | 不采纳 |
| collect-then-report | operator 一次得到完整 issue 表 | 输出多一倍 | **采纳** |

理由：`verify` 是只读命令，不存在"半执行造成状态污染"的风险；让 operator 一次看到所有 backend 的 issue，是 aggregate 便利层的核心价值。

### 4.3 IO 错误作为例外

如前文 C6 所述：当 `verifyBackend` 自身抛 Error（例如 `Failed to scan ... at <root>: <message>`），aggregate 仍抛错并 abort。区别在于：abort 是 trust boundary 层面的决断（IO/policy 错误），不是 verify 业务上的 issue 收集。

---

## 5. `path_safety_policy.json` Revision Draft

### 5.1 决议：**no policy change required**

### 5.2 决议依据

`path_safety_policy.json` 当前包含 4 个字段：
1. `exact_sensitive_target_repo_roots` — 黑名单：精确匹配的敏感系统根
2. `recursive_sensitive_target_repo_roots` — 黑名单：递归匹配的敏感系统根
3. `home_relative_recursive_sensitive_target_repo_roots` — 黑名单：HOME 下的敏感目录
4. `allowed_target_repo_root_prefixes` — 白名单 token：`$cwd / $source_root / $home`

逐字段判断 aggregate 模式是否需要新增内容：

| 字段 | aggregate mode 下是否需要扩展 | 判断依据 |
|------|-------------------------------|----------|
| `exact_sensitive_target_repo_roots` | **否** | 这是绝对路径黑名单，不区分 backend；aggregate 在两次构造 context 时都会调用 `validateTargetRepoRoot`，已自动复用 |
| `recursive_sensitive_target_repo_roots` | **否** | 同上，绝对路径黑名单 |
| `home_relative_recursive_sensitive_target_repo_roots` | **否** | HOME-relative 黑名单与 backend 无关 |
| `allowed_target_repo_root_prefixes` | **否** | 白名单 token 由 caller 在 context 构造时解析；aggregate 复用同一 token map，不引入新 token |

为何不新增 `multi-root: true` 之类字段：
- 该字段在 policy 文件里没有可作用对象——policy 是路径级约束，不是命令级约束。
- aggregate 是 dispatcher 行为，应当在 servo-installer.js 的命令解析与 context 编排层实现，不应将"是否允许多根并行"挂载到 policy schema。
- 添加无作用对象的字段会降低 policy 文件的合同清晰度。

为何不新增 dual-root predicate / aggregate-mode allowlist：
- 任何"R_a 允许 + R_c 允许"的组合都已经被现有 `validateTargetRepoRoot` 各自检查；不存在"R_a 单独合法但 (R_a, R_c) 组合不合法"的真实场景。理由：两根分别是 `<repo>/.agents/skills` 和 `<repo>/.claude/skills`，两个路径都在同一 target repo root 下，token expansion 完全相同；不可能出现一个合法另一个非法。
- 即便操作者通过 `--agents-root <X>` 与 `--claude-root <Y>` 显式指定不同 path 前缀，二者也仍然各自走 `validateTargetRepoRoot`，policy schema 无需额外约束。

### 5.3 与 SA-B 事务语义的接口

如果 SA-B 后续决议要求 aggregate install/update 必须 atomic（all-or-nothing），那么 atomic 行为是 servo-installer.js dispatcher 的责任，不影响 policy schema。policy 文件依然保持 4 字段。

### 5.4 边界情况：未来若 backend 数目扩展（多于 2 个）

预留观察：当前 `backendTargetRootConfig` 是 frozen 的两键映射；未来若新增 backend（例如 `gemini`、`continue`），policy 仍无需变化，因为新 backend 的 root 会沿用同一组 token expansion 与黑名单。aggregate dispatcher 只需扩展可参与 aggregate 的 backend 列表。

---

## 6. Compatibility Analysis

### 6.1 与 managed-only path deletion 的交互

**既有约束**：`pruneBackendManagedInstalls` 只删除 `marker.backend === context.backend && marker !== null` 的目录；update 只在 update plan 出现 `unrecognized-target-directory` 且该路径已被 `managedDeletePaths` 收纳时才允许移除（见 `isUpdateBlockingIssue`）。

**aggregate mode 的行为**：
- aggregate `prune --all` 顺序处理两根；每根的 marker.backend 检查仍然生效（agents context 不会删 claude 的 marker，反之亦然）。
- aggregate **不会**引入"跨根托管删除"——例如不会因为 R_c 上有同 skill_id 的 managed dir 就同时清理 R_a 上某个 unrecognized 目录。
- aggregate **不会**让 unrecognized-target-directory 被自动删除：unrecognized 在两根都仅做 stderr 警告，operator 必须人工确认（与单 backend 一致）。

**新增 edge case**：
- E1：**"双根 cross-marker 误置"**——例如 R_a 上的目录 `R_a/some-dir/aw.marker` 内的 `marker.backend === "claude"`（marker 误写）。aggregate 在 agents context 走到 R_a 时，`pruneBackendManagedInstalls` 因 backend 不匹配会跳过；进入 claude context 处理 R_c 时也不会走到 R_a/some-dir（因为 R_c 的 children 不含 R_a）。结果：该误置目录在两次 prune 中都不删。这是**期望行为**——不让 aggregate 因为"看到 claude marker"就误删 agents 根下的目录。**但**：单 backend 下 verify --backend agents 已经把这种目录标记为 `foreign-managed-directory` issue；aggregate verify 同样会捕获，并在两根上各报一次（一边是 wrong-marker，一边是 missing-from-expected——见 verifyBackend 的 unexpectedManagedTargetDirs 分支）。

### 6.2 与 root-path containment 的交互

**既有约束**：`validateTargetRepoRoot` 强制 resolved target root 必须在 `$cwd / $source_root / $home` 之一前缀下，且不在 sensitive root 列表中。

**aggregate mode 的行为**：
- aggregate 构造两次 context，每次都调用 `validateTargetRepoRoot`（在 `targetRootForBackend` 中）。
- 两根默认都是 `<targetRepoRoot>/.agents/skills` 与 `<targetRepoRoot>/.claude/skills`，自然在 targetRepoRoot 下；override 路径也分别校验。
- aggregate **不会**计算"两根的 LCA"或"跨根的 walk"——每根独立校验，不存在跨根遍历。

**新增 edge case**：
- E2：**"两根 override 跨 prefix"**——operator 同时 `--agents-root /tmp/a/ag` 与 `--claude-root $HOME/cl`。两根分别校验；只要各自都在 allowed prefix 下，policy 都允许。但这会让 aggregate 出现"跨同一项目目录树之外的双根布局"，使得 verify 报告的 backend prefix 在不同物理位置。**期望行为**：允许（policy 没有"两根必须共享同一 targetRepoRoot"的约束）；但 aggregate 在 stdout 输出时必须显示完整 absolute 路径，不能简化为相对路径，以免 operator 误判。
- E3：**"R_a override 至 sensitive root"**——例如 `--agents-root /etc/skills`。`validateTargetRepoRoot` 抛错，aggregate 在 context 构造阶段就失败，不进入两根遍历；R_c 不会被处理。这与单 backend 行为一致，但 aggregate 必须保证 error message 标注 `[backend=agents]`，避免 operator 困惑。

### 6.3 与 payload-rooted enforcement 的交互

**既有约束**：`validateSourceRepoRoot` 强制 source root 必须包含 `product/harness/adapters/agents/skills`、`product/harness/adapters/claude/skills`、`product/harness/skills`（三者缺一不可）。

**aggregate mode 的行为**：
- aggregate 共用同一 `sourceRoot`（两个 context 都来自同一 `resolveSourceRoot()` 或同一 `--source` override）；source root 不分裂。
- 既有 source root 校验同时要求 agents 与 claude 两个 adapter skills 目录都存在；这意味着 source root 已经隐含支持双 backend payload 的能力，aggregate 不需要额外检查。

**新增 edge case**：
- E4：**"adapter skills 目录之一为空"**——source root 通过 `validateSourceRepoRoot` 校验（目录存在），但例如 `adapters/agents/skills` 为空目录。aggregate `install` 进入 agents context 时 `collectSkillBindings` 返回空，触发 `missing-backend-payload-source` issue；aggregate **必须停止**，不能"agents 没有 binding 就只做 claude"。理由：aggregate 的契约是"两端都装上"；如果 agents adapter 没有 payload，operator 必须显式选择"只装 claude"（即不使用 aggregate），不能由 aggregate 隐式忽略一端。

### 6.4 双根并存对既有 unrecognized 处理的影响

**既有行为**：单 backend update 在 plan 阶段如果发现 unrecognized 目录，且该目录是 `managedDeletePaths` 之一，可以越过 unrecognized 但要求 marker 后续重写；否则 update 被 unrecognized 阻断。

**aggregate update 的行为**：
- aggregate update 必须为两根分别构造 update plan；任一根的 plan 阻断会让 aggregate 整体阻断（不允许"agents 一端 unrecognized 阻断而 claude 一端继续"，否则将出现混合版本）。
- 这一行为是 SA-B 事务语义的具体体现，本节只承接边界：trust boundary 不为 aggregate 引入 update 的"宽松 unrecognized 跨根回收"特例。

### 6.5 边界总结

| 现有 trust boundary 维度 | aggregate 是否引入 bypass | 新 edge case |
|---------------------------|---------------------------|--------------|
| managed-only path deletion | 否 | E1（cross-marker 误置） |
| root-path containment | 否 | E2（双 override 跨 prefix）、E3（override 至 sensitive root） |
| payload-rooted enforcement | 否 | E4（一端 adapter skills 为空） |

---

## 7. Operator-Facing Error Messages

下面给出 dispatcher 应输出的消息文本（草案；实现 phase 可微调）。所有 message 都加 `[backend=<name>]` 前缀以消除歧义。

### 7.1 Dual-root conflict 消息（来自 §2.2 表 A）

| 场景 ID | 消息文本（stderr） | exit code |
|---------|---------------------|-----------|
| A3 | `[backend=claude] error: managed marker mismatch at <path>: marker.backend=<X> expected=claude. aggregate install/update aborted; agents was not modified.` | 1 |
| A4 | `[backend=agents] error: unrecognized target directory at <path>: existing directory has no recognized aw.marker. aggregate refuses to overwrite. resolve manually before retrying.` | 1 |
| A5 | `[backend=claude] error: unrecognized target directory at <path>: existing directory has no recognized aw.marker. aggregate refuses to overwrite. resolve manually before retrying.` | 1 |
| A6 | `[backend=agents] error: target root is not a real directory at <path>: <reason>. aggregate aborted before any write; claude not modified.` | 1 |
| A7 | `[backend=claude] error: target root is not a real directory at <path>: <reason>. aggregate aborted; agents not modified.` | 1 |
| A9 | `[backend=agents] error: Target repo root <path> is outside allowed paths: <prefixes>. aggregate aborted.` | 1 |
| A10 | `[backend=agents] error: target root inaccessible at <path>: <io-error>. aggregate aborted; claude not modified.` | 1 |
| A11 | `[backend=claude] error: target root inaccessible at <path>: <io-error>. aggregate aborted; agents <state>.` | 1 |
| A12 | `[backend=claude] error: <existing-target-issue at path>. aggregate aborted; agents not modified.` | 1 |

### 7.2 `prune --all` 消息（来自 §3）

| 场景 | 输出 |
|------|------|
| 正常完成（B2） | `[agents] removed managed skill dir <path>` × N，`[agents] prune complete: removed=N`；之后 `[claude] removed managed skill dir <path>` × M，`[claude] prune complete: removed=M`；最后 `aggregate prune complete: agents=N, claude=M` |
| B3（R_a 失败） | `[agents] error: failed to remove managed skill dir <path>: <io-msg>. aggregate prune aborted before claude.` exit 1 |
| B4（R_c 失败） | 先 `[agents] no managed skill dirs found at <root>`，然后 `[claude] error: failed to remove managed skill dir <path>: <io-msg>. aggregate prune partial: agents=ok (no-op), claude=failed.` exit 1 |
| B5/B6（unrecognized/foreign warning） | `[agents] preserved <N> unrecognized directories (no marker); resolve manually. they were not removed.` exit 0（如果其他都正常） |
| B7（R_a target root type） | `[agents] error: target root is not a real directory at <path>: <reason>. aggregate prune aborted.` exit 1 |
| B8（R_c target root type） | 先 `[agents] no managed skill dirs found at <root>`，然后 `[claude] error: target root is not a real directory at <path>: <reason>. aggregate prune partial.` exit 1 |

### 7.3 `verify` 消息（来自 §4）

| 场景 | 输出 |
|------|------|
| C1（无 issue） | `[agents] verify ok: 0 issue(s)`，`[claude] verify ok: 0 issue(s)`，`aggregate verify ok` exit 0 |
| C2/C3/C4（任一 issue） | 每根独立列出 issue：`[<backend>] drift: <count> issue(s) in target root at <path>` 然后 `  - <code>: <path> (<detail>)` 逐行；最后 `aggregate verify failed: agents=<n_a> issue(s), claude=<n_c> issue(s)` exit 1 |
| C5（两根都 missing） | `[agents] missing-target-root: <path>`、`[claude] missing-target-root: <path>`、`aggregate verify failed: both target roots missing` exit 1 |
| C6（IO 错误） | `[agents] servo-installer failed: <io-message>` 立即抛错；exit 1 |

### 7.4 `diagnose` 消息（来自 §2.2 表 D）

- 与既有 `diagnose --json` 兼容：JSON 输出新增顶层 `aggregate` 字段，内部包含 `agents` 与 `claude` 两个子结果对象，每个保持既有 `diagnose` schema。
- 文本输出：与 verify 类似，每根独立段落 + `[backend=...]` 前缀；exit code 仍为 0（即便有 issue）。

---

## 8. 与其他 SubAgent 决议的接口

- **SA-A（命令面 protocol）**：本设计不依赖具体语法（`--backend bundle` / 多值列表 / 子命令），只依赖 dispatcher 内部能"为两个 backend 分别构造 context 并按 §3/§4 规则编排"。任何选项最终都映射到这一执行模型。
- **SA-B（事务语义）**：本设计在 install/update 路径上的"任一根失败即 aggregate 短路"是 trust boundary 的最小约束；SA-B 进一步决议是否做"R_a 已写入但 R_c 失败时 R_a 的回滚"。trust boundary 提供下限：不会因 aggregate 而放宽任何单 backend 信任检查。
- **SA-D（合同修订）**：建议把本节 §2 的真值表与 §7 的消息策略，编入 `distribution-entrypoint-contract.md` 的"命令面合同"扩展段（aggregate 子表）；`payload-provenance-trust-boundary.md` 增补"aggregate mode 不引入新的写入边界，只组合两个 backend 各自的现有边界"一句即足。
- **SA-E（TUI/CLI 双面映射）**：TUI 在表达 aggregate 时必须复现 §7 的消息结构（含 backend prefix），不能省略前缀以保持与 CLI 的等价性。

---

## 9. 验收对照

| 验收条件 | 本草案位置 |
|---------|------------|
| 双根冲突短路规则明确 | §2.2 表 A/B/C/D |
| 双根 prune 边界收敛清晰 | §3.1 / §3.2 / §3.3 |
| `path_safety_policy.json` 修订需求显式标记 | §5.1（明确 no change required，§5.2 给出依据） |
| 兼容性分析覆盖现有约束 | §6.1（managed-only）/§6.2（root containment）/§6.3（payload-rooted） |
| 每个现有 trust boundary 至少一个新 edge case | §6.5 总表（E1 / E2-E3 / E4） |

---

## 10. 实现 phase 提示（不在本 worktrack 实施）

- aggregate dispatcher 应放在 `runNodeOwned`（或对应新入口）外层，不修改 `pruneBackendManagedInstalls`/`verifyBackend`/`installBackendPayloads` 等核心函数的签名。
- 消息前缀 `[backend=...]` 应在 dispatcher 层注入，避免污染单 backend 既有输出（保持单 backend exit / message 与现状一致）。
- 测试 surface（详 SA-E）应至少为表 A/B/C/D 的 illegal 行各加一例集成测试，确保短路顺序与 message 前缀稳定。

---

## 11. 边界声明

本草案不修改任何文件、不执行 servo-installer、不写入真相层。本草案为 design phase 研究输出，等待 SA-D 整合与 design Gate review。

