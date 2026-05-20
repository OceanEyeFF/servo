---
title: "SA-D: distribution-entrypoint-contract.md Revision Draft (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-004
updated: 2026-05-07
owner: research-subagent
---

# SA-D: distribution-entrypoint-contract.md 修订草案

> 本草案仅服务于 design phase。它**不修改** `docs/project-maintenance/deploy/distribution-entrypoint-contract.md` 真相层文件；目标是产出一份"可在 implementation phase 由 SA-D 整合者直接套用"的修订规格。本草案的 protocol、事务、信任边界口径完全承接自 SA-A / SA-B / SA-C：
>
> - SA-A 推荐：**`--backend bundle` enum 扩展**（不引入多值列表与子命令族）。
> - SA-B 推荐：**per-command hybrid**（写前预扫描 all-or-nothing；写时 each-independent，无跨 backend 回滚；只读 collect-then-report）。
> - SA-C 推荐：**dual-root fail-closed on writes；prune 顺序 agents→claude；verify collect-then-report；NO `path_safety_policy.json` 修订**。
>
> 修订原则（载入合同的硬约束）：
>
> 1. **既有单 backend 合同条款一字不改**——`agents` 与 `claude` 单值 backend 在所有命令面（diagnose / verify / prune --all / check_paths_exist / install / update）保持现行语义；本修订仅作 additive 扩展。
> 2. **聚合 mode 的合同条款单独成节**——避免在既有命令面合同表内塞入歧义脚注；用专门的"Aggregate Backend (`--backend bundle`)"小节集中表达。
> 3. **回滚策略显式标注**——合同明确"per-backend each-independent on writes; no cross-backend rollback"，operator 与下游 implementation 都不得假设跨根原子。
> 4. **错误信号双前缀化**——所有 aggregate 模式下的 stderr / stdout 输出在每条信息上加 `[backend=<name>]` 前缀（per SA-C §7），消除多端混合时的归因歧义；这条放进"CLI / TUI 不变量"段以保证 TUI 等价。

---

## 1. Revision Summary

修订涉及 6 个 section：

| section | 操作 | 落点 |
| --- | --- | --- |
| Frontmatter | update `updated` / `last_verified`（implementation phase 套用时填入正式日期） | YAML header |
| § 当前 package/runtime surface | 扩展 `agents` 与 `claude` 之外，补一句"`bundle` 作为聚合 enum 值，等价于在两个 distribution 上同时执行同一 verb" | 段落正文 |
| § 命令面合同 | **不动既有 6 行**；新增 7 行（每个既有 verb 在 aggregate 下的语义条款）以独立的"Aggregate Mode Clauses"小节出现 | 表格之后 |
| § Aggregate Backend (`--backend bundle`) — 新增 section | 完整新增；三段：dispatch surface / transaction semantics / dual-root failure short-circuit | 命令面合同与 CLI/TUI 不变量之间 |
| § CLI / TUI 不变量 | 新增 1 条不变量（aggregate stderr/stdout backend prefix；TUI 必须保留同前缀） | 列表追加 |
| § 停止线 | 不变 | — |

修订 **不** 改写："CLI 是稳定脚本接口"、"wrapper 不能改变 deploy 语义"、"TUI 不得拥有独立于 CLI 的 install/update 语义"、"`diagnose` 不是安装成功证明"、"wrapper 不得把 deploy target 当成 source of truth"。这些都是承接 P0-071 charter 张力声明（见 `sa-d-charter-tension-declaration.md`）的硬不变量；aggregate 是**便利层**，不会破坏它们。

---

## 2. Section-by-Section Revision (before/after diff blocks)

下面采用 unified-diff 风格描述每个 section 的变化。`-` 行表示删除，`+` 行表示新增，无前缀行表示不变（context）。每个 section 都给出 BEFORE 完整切片与 AFTER 完整切片，确保 implementation phase 能直接 copy/paste。

### 2.1 Frontmatter

**BEFORE**

```markdown
---
title: "Distribution Entrypoint Contract"
status: active
updated: 2026-05-06
owner: servo-kernel
last_verified: 2026-05-06
---
```

**AFTER**

```markdown
---
title: "Distribution Entrypoint Contract"
status: active
updated: <implementation-phase-date>
owner: servo-kernel
last_verified: <implementation-phase-date>
---
```

**Diff**

```diff
 ---
 title: "Distribution Entrypoint Contract"
 status: active
-updated: 2026-05-06
+updated: <implementation-phase-date>
 owner: servo-kernel
-last_verified: 2026-05-06
+last_verified: <implementation-phase-date>
 ---
```

**Notes**：日期不在 design phase 决定；implementation phase 套用本草案时用 `servo-installer` aggregate backend 实装合并日填入。

---

### 2.2 段首引文（"目的"段）

**BEFORE**

```markdown
> 目的：明确 `servo-installer` 作为 deploy 分发入口必须保持的 wrapper 语义。

本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径；release channel、trust boundary、mapping 见相邻文档。
```

**AFTER**

```markdown
> 目的：明确 `servo-installer` 作为 deploy 分发入口必须保持的 wrapper 语义。

本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径（含聚合 backend `bundle`）；release channel、trust boundary、mapping 见相邻文档。
```

**Diff**

```diff
 > 目的：明确 `servo-installer` 作为 deploy 分发入口必须保持的 wrapper 语义。

-本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径；release channel、trust boundary、mapping 见相邻文档。
+本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径（含聚合 backend `bundle`）；release channel、trust boundary、mapping 见相邻文档。
```

**Notes**：仅在范围声明里追加 "（含聚合 backend `bundle`）" 以预告下文有 aggregate 小节；不改变本页与 trust boundary / mapping 文档的边界划分。

---

### 2.3 §"当前 package/runtime surface"

**BEFORE**

```markdown
## 当前 package/runtime surface

- bin surface 是 `servo-installer`，当前支持 `agents` 与 `claude`；未支持 backend 或命令变体显式失败
- CLI 是稳定脚本接口；TUI 只能是同一合同上的交互层
```

**AFTER**

```markdown
## 当前 package/runtime surface

- bin surface 是 `servo-installer`，当前支持 `agents`、`claude` 与聚合值 `bundle`；未支持 backend 或命令变体显式失败
- `bundle` 是 `--backend` 枚举的第三个合法值；它不是新的 distribution，而是"在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb"的 dispatcher 别名
- CLI 是稳定脚本接口；TUI 只能是同一合同上的交互层
```

**Diff**

```diff
 ## 当前 package/runtime surface

-- bin surface 是 `servo-installer`，当前支持 `agents` 与 `claude`；未支持 backend 或命令变体显式失败
+- bin surface 是 `servo-installer`，当前支持 `agents`、`claude` 与聚合值 `bundle`；未支持 backend 或命令变体显式失败
+- `bundle` 是 `--backend` 枚举的第三个合法值；它不是新的 distribution，而是"在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb"的 dispatcher 别名
 - CLI 是稳定脚本接口；TUI 只能是同一合同上的交互层
```

**Notes**：以 enum 第三值的口径登记 `bundle`（per SA-A 候选 A），同时显式写出"非新 distribution"以承接 charter 张力声明。

---

### 2.4 §"命令面合同"

**BEFORE**

```markdown
## 命令面合同

| mode | 必须保持的语义 |
| --- | --- |
| `diagnose` | 只读状态摘要；可返回 `0` 并报告 issue |
| `verify` | 只读严格复验；发现 issue 时失败 |
| `prune --all` | 只删除当前 backend 可识别的受管目录 |
| `check_paths_exist` | 写入前全量冲突扫描；失败时零业务写入 |
| `install` | 只写当前 source 声明的 live payload |
| `update` | 默认只输出 dry-run plan；`--yes` 才执行 `prune -> check_paths_exist -> install -> verify` |

wrapper 可以改变启动方式，不能改变这些 deploy 语义。
```

**AFTER**

```markdown
## 命令面合同

| mode | 必须保持的语义 |
| --- | --- |
| `diagnose` | 只读状态摘要；可返回 `0` 并报告 issue |
| `verify` | 只读严格复验；发现 issue 时失败 |
| `prune --all` | 只删除当前 backend 可识别的受管目录 |
| `check_paths_exist` | 写入前全量冲突扫描；失败时零业务写入 |
| `install` | 只写当前 source 声明的 live payload |
| `update` | 默认只输出 dry-run plan；`--yes` 才执行 `prune -> check_paths_exist -> install -> verify` |

wrapper 可以改变启动方式，不能改变这些 deploy 语义。

> 上表的语义条款是 backend-invariant，单 backend (`agents` / `claude`) 与聚合 backend (`bundle`) 都必须满足。聚合 backend 在每条 verb 上的额外编排合同见下文 "Aggregate Backend (`--backend bundle`)" 小节；该小节不放宽上表任何一条，只在双 distribution 维度上展开 dispatch / 事务 / 短路细则。
```

**Diff**

```diff
 ## 命令面合同

 | mode | 必须保持的语义 |
 | --- | --- |
 | `diagnose` | 只读状态摘要；可返回 `0` 并报告 issue |
 | `verify` | 只读严格复验；发现 issue 时失败 |
 | `prune --all` | 只删除当前 backend 可识别的受管目录 |
 | `check_paths_exist` | 写入前全量冲突扫描；失败时零业务写入 |
 | `install` | 只写当前 source 声明的 live payload |
 | `update` | 默认只输出 dry-run plan；`--yes` 才执行 `prune -> check_paths_exist -> install -> verify` |

 wrapper 可以改变启动方式，不能改变这些 deploy 语义。
+
+> 上表的语义条款是 backend-invariant，单 backend (`agents` / `claude`) 与聚合 backend (`bundle`) 都必须满足。聚合 backend 在每条 verb 上的额外编排合同见下文 "Aggregate Backend (`--backend bundle`)" 小节；该小节不放宽上表任何一条，只在双 distribution 维度上展开 dispatch / 事务 / 短路细则。
```

**Notes**：表格 6 行**完全保留**（这是单 backend 合同的稳定承诺）。表后追加 1 段过渡注释，把 invariant 与 aggregate 编排合同分层关系绑死。

---

### 2.5 §"Aggregate Backend (`--backend bundle`)" — 新增 section

**BEFORE**

（无此 section，本节为整段新增，插入位置位于 §"命令面合同" 与 §"CLI / TUI 不变量" 之间。）

**AFTER**

```markdown
## Aggregate Backend (`--backend bundle`)

`bundle` 是 `--backend` 枚举的第三个合法值。它不是新的 distribution，而是 dispatcher 触发器：在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb，编排服从下面三条专属合同。`bundle` 不在合同条款层放宽 §"命令面合同" 任意一条 backend-invariant 条款。

### Dispatch Surface

- 合法 verb：`diagnose` / `verify` / `prune --all` / `check_paths_exist` / `install` / `update`（与单 backend 完全相同；no extra verb, no missing verb）
- 解析口径：`--backend bundle` 在所有 9 条 `parseNodeXxxArgs` 函数中均为合法值；`agents` 与 `claude` 单值仍合法且语义不变
- 双根解析：`bundle` 同时携带 agents 根与 claude 根；CLI 接受 `--agents-root` 与 `--claude-root` 两个 override；任一 override 缺失时退回该 backend 的默认根（`<targetRepoRoot>/.agents/skills` 与 `<targetRepoRoot>/.claude/skills`）
- 不兼容组合：
  - `--backend bundle --source github`：不合法（github source 仅支持 agents 单 backend），dispatcher 在 parser finalizer 阶段 reject，stderr 提示"`--backend bundle` is not supported with `--source github`; bundle requires `--source package`"
  - `--backend bundle` 同时使用 `--agents-root <X>` 而 `<X>` 解析失败：fail at context construction with `[backend=agents]` 前缀；`claude` 根不进入构造
  - `--agents-root` 与 `--claude-root` 在 path-resolve 后指向同一物理目录：dispatcher 必须 reject（双根 path-disjoint 是 trust boundary 不变量；详见 `payload-provenance-trust-boundary.md` 与 `sa-c-trust-boundary.md` §6.2）
- TUI 等价：TUI 主菜单允许 backend 切换为 `bundle`；guided flow 与单 backend menu 拓扑一致；所有 TUI mutating 操作仍必须映射到合法 CLI verb（不得引入 TUI 专属 aggregate verb）

### Transaction Semantics (per-command hybrid)

下表给出每个 verb 在 aggregate mode 下的事务模型与失败口径。所有"写"路径都是 each-independent on writes；所有"只读"路径都是 collect-then-report；只在写前预扫描阶段做 union all-or-nothing。**no cross-backend rollback** 是 aggregate 模式的硬不变量。

| verb | transaction model | short-circuit policy | rollback strategy | partial-completion surface |
| --- | --- | --- | --- | --- |
| `diagnose` | each-independent collect-then-report (read-only) | none | n/a | exit 0 with `aggregate.backends.{agents,claude}` JSON sections（与既有 `diagnose --json` 兼容） |
| `verify` | each-independent collect-then-report (read-only) | none（两根都跑完） | n/a | exit 1 if any root has issue；stderr 按 backend 分组 issue list |
| `prune --all` | hybrid (pre-check union all-or-nothing → delete each-independent) | pre-check 任一根失败 → 不开始任何根的删除；删除阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none | exit 1；stderr 标注 `aggregate prune partial: agents=<state>, claude=<state>` |
| `check_paths_exist` | union all-or-nothing pre-scan (read-only)；保护下游 install/update 的 fail-closed gate | none（两根都跑完冲突收集） | n/a | exit 1 if any root has conflict；stderr 按 backend 分组 conflict list |
| `install` | hybrid (pre-write union all-or-nothing → write each-independent) | pre-write 任一根失败 → 任何根都不写入；写入阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none（已写入内容保留；operator 须用单 backend `prune` + `install` 显式收尾） | exit 1；stderr 标注 `aggregate partial install: agents=<state>, claude=<state>` 并附 recovery hint |
| `update` (dry-run) | each-independent collect-then-report (read-only plan) | none | n/a | exit 1 if any root has blocking issue；stdout 含两根 plan |
| `update --yes` | hybrid (pre-check union all-or-nothing → apply each-independent) | pre-check 任一根 blocking_issue_count > 0 → 任何根都不进入 apply；apply 阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none（成功 backend 不回退；失败 backend 留半成品） | exit 1；stderr 标注 `aggregate partial update: agents applied (verified), claude failed at <stage>` 并附 single-backend recovery hint |

`update --yes` 的成功定义：两根都完整通过 `prune -> check_paths_exist -> install -> verify` 全 pipeline；任一根任一阶段失败即整体 partial。pre-check 阶段使用 union 视角短路（任一根 blocking_issue_count > 0 都不进入 apply），与 §2.4 表中 single backend `update --yes` 的 fail-closed 语义一致。

### Dual-Root Failure Short-Circuit

dual-root 失败短路是 aggregate mode 的"fail-closed on writes"硬合同，承接自 SA-C trust boundary 决议。规则如下：

1. **写前 fail-closed**：`install` / `update --yes` / `prune --all` 在 pre-check / pre-write 阶段，任一根失败 → 任何根都不进入实际写入或删除阶段；磁盘任何位置都不发生变更。
2. **写时 first-fail-stop**：写入或删除阶段按 ASCII 顺序 `agents` → `claude` 执行；前一根成功后才轮到后一根；前一根失败时第二根不开始。**已写入或已删除的内容保留**，不做反向回滚。
3. **跨根 path-disjoint 强制**：dispatcher 在 context 构造阶段拒绝 `--agents-root` 与 `--claude-root` 解析后指向同一物理目录的组合（不论是否 symlink 等价）；理由：双根 marker.backend 互斥保证由路径不重叠承担，重叠会让 prune 走错根的物理目录。
4. **错误归因前缀**：aggregate mode 下所有 stderr / stdout / `--json` 输出在每条信息上加 `[backend=<name>]` 前缀（`<name>` ∈ `{agents, claude, aggregate}`）；`aggregate` 前缀只用于双根汇总信息（如 partial 消息、final summary），单根错误必须用对应 backend 前缀；TUI 必须保留同前缀以维持 CLI/TUI 等价。
5. **partial-completion 必须显式表达**：任一 mutating verb 出现 partial 时，stderr 必须输出 `aggregate <verb> partial: agents=<state>, claude=<state>` 一行，并附与现有 `update --yes` recovery hint 同形态的修复路径建议；实施 phase 在 implementation 中以 single-backend 命令组合作为 recovery 路径（不引入 aggregate-only recovery verb）。
6. **`path_safety_policy.json` 不变更**：dual-root 不触发 policy schema 修订；每根独立通过 `validateTargetRepoRoot` 即满足；详见 SA-C §5。
```

**Diff**

```diff
+## Aggregate Backend (`--backend bundle`)
+
+`bundle` 是 `--backend` 枚举的第三个合法值。它不是新的 distribution，而是 dispatcher 触发器：在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb，编排服从下面三条专属合同。`bundle` 不在合同条款层放宽 §"命令面合同" 任意一条 backend-invariant 条款。
+
+### Dispatch Surface
+
+- 合法 verb：`diagnose` / `verify` / `prune --all` / `check_paths_exist` / `install` / `update`（与单 backend 完全相同；no extra verb, no missing verb）
+- 解析口径：`--backend bundle` 在所有 9 条 `parseNodeXxxArgs` 函数中均为合法值；`agents` 与 `claude` 单值仍合法且语义不变
+- 双根解析：`bundle` 同时携带 agents 根与 claude 根；CLI 接受 `--agents-root` 与 `--claude-root` 两个 override；任一 override 缺失时退回该 backend 的默认根（`<targetRepoRoot>/.agents/skills` 与 `<targetRepoRoot>/.claude/skills`）
+- 不兼容组合：
+  - `--backend bundle --source github`：不合法（github source 仅支持 agents 单 backend），dispatcher 在 parser finalizer 阶段 reject，stderr 提示"`--backend bundle` is not supported with `--source github`; bundle requires `--source package`"
+  - `--backend bundle` 同时使用 `--agents-root <X>` 而 `<X>` 解析失败：fail at context construction with `[backend=agents]` 前缀；`claude` 根不进入构造
+  - `--agents-root` 与 `--claude-root` 在 path-resolve 后指向同一物理目录：dispatcher 必须 reject（双根 path-disjoint 是 trust boundary 不变量；详见 `payload-provenance-trust-boundary.md` 与 `sa-c-trust-boundary.md` §6.2）
+- TUI 等价：TUI 主菜单允许 backend 切换为 `bundle`；guided flow 与单 backend menu 拓扑一致；所有 TUI mutating 操作仍必须映射到合法 CLI verb（不得引入 TUI 专属 aggregate verb）
+
+### Transaction Semantics (per-command hybrid)
+
+下表给出每个 verb 在 aggregate mode 下的事务模型与失败口径。所有"写"路径都是 each-independent on writes；所有"只读"路径都是 collect-then-report；只在写前预扫描阶段做 union all-or-nothing。**no cross-backend rollback** 是 aggregate 模式的硬不变量。
+
+| verb | transaction model | short-circuit policy | rollback strategy | partial-completion surface |
+| --- | --- | --- | --- | --- |
+| `diagnose` | each-independent collect-then-report (read-only) | none | n/a | exit 0 with `aggregate.backends.{agents,claude}` JSON sections（与既有 `diagnose --json` 兼容） |
+| `verify` | each-independent collect-then-report (read-only) | none（两根都跑完） | n/a | exit 1 if any root has issue；stderr 按 backend 分组 issue list |
+| `prune --all` | hybrid (pre-check union all-or-nothing → delete each-independent) | pre-check 任一根失败 → 不开始任何根的删除；删除阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none | exit 1；stderr 标注 `aggregate prune partial: agents=<state>, claude=<state>` |
+| `check_paths_exist` | union all-or-nothing pre-scan (read-only)；保护下游 install/update 的 fail-closed gate | none（两根都跑完冲突收集） | n/a | exit 1 if any root has conflict；stderr 按 backend 分组 conflict list |
+| `install` | hybrid (pre-write union all-or-nothing → write each-independent) | pre-write 任一根失败 → 任何根都不写入；写入阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none（已写入内容保留；operator 须用单 backend `prune` + `install` 显式收尾） | exit 1；stderr 标注 `aggregate partial install: agents=<state>, claude=<state>` 并附 recovery hint |
+| `update` (dry-run) | each-independent collect-then-report (read-only plan) | none | n/a | exit 1 if any root has blocking issue；stdout 含两根 plan |
+| `update --yes` | hybrid (pre-check union all-or-nothing → apply each-independent) | pre-check 任一根 blocking_issue_count > 0 → 任何根都不进入 apply；apply 阶段按 ASCII 顺序 `agents` → `claude`，前者失败立即停，后者不开始 | none（成功 backend 不回退；失败 backend 留半成品） | exit 1；stderr 标注 `aggregate partial update: agents applied (verified), claude failed at <stage>` 并附 single-backend recovery hint |
+
+`update --yes` 的成功定义：两根都完整通过 `prune -> check_paths_exist -> install -> verify` 全 pipeline；任一根任一阶段失败即整体 partial。pre-check 阶段使用 union 视角短路（任一根 blocking_issue_count > 0 都不进入 apply），与 §2.4 表中 single backend `update --yes` 的 fail-closed 语义一致。
+
+### Dual-Root Failure Short-Circuit
+
+dual-root 失败短路是 aggregate mode 的"fail-closed on writes"硬合同，承接自 SA-C trust boundary 决议。规则如下：
+
+1. **写前 fail-closed**：`install` / `update --yes` / `prune --all` 在 pre-check / pre-write 阶段，任一根失败 → 任何根都不进入实际写入或删除阶段；磁盘任何位置都不发生变更。
+2. **写时 first-fail-stop**：写入或删除阶段按 ASCII 顺序 `agents` → `claude` 执行；前一根成功后才轮到后一根；前一根失败时第二根不开始。**已写入或已删除的内容保留**，不做反向回滚。
+3. **跨根 path-disjoint 强制**：dispatcher 在 context 构造阶段拒绝 `--agents-root` 与 `--claude-root` 解析后指向同一物理目录的组合（不论是否 symlink 等价）；理由：双根 marker.backend 互斥保证由路径不重叠承担，重叠会让 prune 走错根的物理目录。
+4. **错误归因前缀**：aggregate mode 下所有 stderr / stdout / `--json` 输出在每条信息上加 `[backend=<name>]` 前缀（`<name>` ∈ `{agents, claude, aggregate}`）；`aggregate` 前缀只用于双根汇总信息（如 partial 消息、final summary），单根错误必须用对应 backend 前缀；TUI 必须保留同前缀以维持 CLI/TUI 等价。
+5. **partial-completion 必须显式表达**：任一 mutating verb 出现 partial 时，stderr 必须输出 `aggregate <verb> partial: agents=<state>, claude=<state>` 一行，并附与现有 `update --yes` recovery hint 同形态的修复路径建议；实施 phase 在 implementation 中以 single-backend 命令组合作为 recovery 路径（不引入 aggregate-only recovery verb）。
+6. **`path_safety_policy.json` 不变更**：dual-root 不触发 policy schema 修订；每根独立通过 `validateTargetRepoRoot` 即满足；详见 SA-C §5。
+
```

**Notes**：本节是修订草案的核心新增。表格行数（7 行 verb + 标题行 = 8 行）覆盖 `diagnose / verify / prune --all / check_paths_exist / install / update / update --yes` 全部命令面（其中 `update` 与 `update --yes` 分行以显式表达 dry-run 与 apply 路径的事务差异）。Dual-Root Failure Short-Circuit 6 条规则与 SA-C §2-§7 一一对应。

---

### 2.6 §"CLI / TUI 不变量"

**BEFORE**

```markdown
## CLI / TUI 不变量

- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode
- 非交互环境不得隐式启动 TUI；`--json` 只属 CLI 机器输出，不得混入交互渲染
- `diagnose` 不是安装成功证明；严格失败信号只能来自 `verify`
- wrapper 不得把 deploy target 当成 source of truth
```

**AFTER**

```markdown
## CLI / TUI 不变量

- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode（包括 `--backend bundle` 模式）
- 非交互环境不得隐式启动 TUI；`--json` 只属 CLI 机器输出，不得混入交互渲染
- `diagnose` 不是安装成功证明；严格失败信号只能来自 `verify`
- wrapper 不得把 deploy target 当成 source of truth
- aggregate (`--backend bundle`) 模式下，所有 stderr / stdout / `--json` 输出必须使用 `[backend=<name>]` 前缀对每条 backend-attributable 信息归因；TUI 渲染必须保留同前缀以维持 CLI/TUI 等价
```

**Diff**

```diff
 ## CLI / TUI 不变量

-- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode
+- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode（包括 `--backend bundle` 模式）
 - 非交互环境不得隐式启动 TUI；`--json` 只属 CLI 机器输出，不得混入交互渲染
 - `diagnose` 不是安装成功证明；严格失败信号只能来自 `verify`
 - wrapper 不得把 deploy target 当成 source of truth
+- aggregate (`--backend bundle`) 模式下，所有 stderr / stdout / `--json` 输出必须使用 `[backend=<name>]` 前缀对每条 backend-attributable 信息归因；TUI 渲染必须保留同前缀以维持 CLI/TUI 等价
```

**Notes**：第 1 条不变量原文照旧但补充括号说明，确认 `bundle` mode 不会让 TUI 引入旁路 mutating verb。新增第 5 条不变量是 SA-C §7 文本前缀方案上升为合同条款；放进 CLI/TUI 不变量段以保证 implementation phase 在 TUI 层不能省略前缀。

---

### 2.7 §"停止线"

**BEFORE**

```markdown
## 停止线

如果问题已进入 release channel、payload source 设计、target root trust boundary 或 operator 执行步骤，本页只提供链接，不继续展开。
```

**AFTER**

```markdown
## 停止线

如果问题已进入 release channel、payload source 设计、target root trust boundary 或 operator 执行步骤，本页只提供链接，不继续展开。
```

**Diff**

```diff
 ## 停止线

 如果问题已进入 release channel、payload source 设计、target root trust boundary 或 operator 执行步骤，本页只提供链接，不继续展开。
```

**Notes**：停止线**不动**——本节内容保持"本页边界声明"角色；aggregate 的 trust boundary 细节已在 SA-C 文档与 `sa-c-trust-boundary.md` 中独立表达，本页面通过 §"Aggregate Backend (`--backend bundle`)" §"Dual-Root Failure Short-Circuit" 第 6 条引用即足。

---

## 3. Net Diff Summary

把所有修订合并为一份 unified-diff 摘要，便于 implementation phase 一次套用：

```diff
@@ frontmatter @@
-updated: 2026-05-06
+updated: <implementation-phase-date>
-last_verified: 2026-05-06
+last_verified: <implementation-phase-date>

@@ section: 段首引文 @@
-本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径；release channel、trust boundary、mapping 见相邻文档。
+本页只管理 `servo-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径（含聚合 backend `bundle`）；release channel、trust boundary、mapping 见相邻文档。

@@ section: 当前 package/runtime surface @@
-- bin surface 是 `servo-installer`，当前支持 `agents` 与 `claude`；未支持 backend 或命令变体显式失败
+- bin surface 是 `servo-installer`，当前支持 `agents`、`claude` 与聚合值 `bundle`；未支持 backend 或命令变体显式失败
+- `bundle` 是 `--backend` 枚举的第三个合法值；它不是新的 distribution，而是"在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb"的 dispatcher 别名

@@ section: 命令面合同（表后追加注释，表本身不动） @@
 wrapper 可以改变启动方式，不能改变这些 deploy 语义。
+
+> 上表的语义条款是 backend-invariant，单 backend (`agents` / `claude`) 与聚合 backend (`bundle`) 都必须满足。聚合 backend 在每条 verb 上的额外编排合同见下文 "Aggregate Backend (`--backend bundle`)" 小节；该小节不放宽上表任何一条，只在双 distribution 维度上展开 dispatch / 事务 / 短路细则。

@@ section: Aggregate Backend (`--backend bundle`) — 整段新增 @@
+## Aggregate Backend (`--backend bundle`)
+
+`bundle` 是 `--backend` 枚举的第三个合法值。...
+(详见 §2.5 完整正文)

@@ section: CLI / TUI 不变量 @@
-- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode
+- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode（包括 `--backend bundle` 模式）
+- aggregate (`--backend bundle`) 模式下，所有 stderr / stdout / `--json` 输出必须使用 `[backend=<name>]` 前缀对每条 backend-attributable 信息归因；TUI 渲染必须保留同前缀以维持 CLI/TUI 等价

@@ section: 停止线 @@
（保持不变）
```

---

## 4. Backward-Compat Compliance

把修订映射回 charter / 既有合同 / 既有测试 surface：

| 维度 | 修订前合同 | 修订后合同 | 兼容性 |
| --- | --- | --- | --- |
| `--backend agents` 单值 | 合法且走单 distribution 流程 | **合法且语义不变** | 完全兼容 |
| `--backend claude` 单值 | 合法且走单 distribution 流程 | **合法且语义不变** | 完全兼容 |
| 既有 6 行命令面合同表 | 6 行 backend-invariant 条款 | 6 行**逐字保留** | 完全兼容 |
| 既有 4 行 CLI/TUI 不变量 | 4 行不变量 | 第 1 条补充括号说明（语义不变）；其余 3 行**逐字保留** | 完全兼容 |
| `--source github` + agents | github source 走 agents 路径 | **保持**；新增 `--backend bundle --source github` 不合法的拒绝 | additive |
| 既有 80 个测试中以 `--backend agents|claude` 为参数集的固定串 | 全部以单值 backend 走 single-distribution path | **全部保留**；bundle 是新增 path | 完全兼容（per SA-A §6.1） |
| `path_safety_policy.json` 字段 | 4 字段不变 | **不变** | 完全兼容（per SA-C §5） |

---

## 5. Implementation Phase Application Notes

implementation phase 套用本草案时：

1. **不要拆分修订**——所有 6 个 section 修订必须在同一个 commit 内套用，避免 partial state（半套用文档自相矛盾）；
2. **frontmatter 日期**——`updated` 与 `last_verified` 用 `servo-installer` aggregate backend 实装合并日填入；不可早于 implementation phase 的 design Gate 通过日；
3. **Cross-document 检查**——套用本修订后必须同步检查：
   - `docs/project-maintenance/deploy/deploy-mapping-spec.md`：套用 `sa-d-deploy-mapping-spec-revision.md`（D-2 草案）的 dual-root mapping 修订
   - `docs/project-maintenance/deploy/payload-provenance-trust-boundary.md`：补一句"aggregate mode 不引入新的写入边界，只组合两个 backend 各自的现有边界"（per SA-C §8）
   - `.servo/goal-charter.md`：**不需要修订**（per `sa-d-charter-tension-declaration.md` D-3 草案）
4. **测试 surface**——本修订引入的合同条款由 SA-E 设计的 multi-backend 测试用例清单负责证据落地；本草案不规定测试形态。

---

## 6. Open Questions Surfaced for Implementation Phase

下列条目是本修订草案明确**留给 implementation phase**的问题；本草案不替它们回答：

- **Q1**：`--backend bundle` 在 `--source github` 之外还有哪些 source flag 不兼容？（design phase 已识别 `--source github`；其他可能的 flag 由 implementation phase parser finalizer 列出。）
- **Q2**：dual-root path-disjoint 检查的实现位置（context 构造阶段 vs verify 阶段）由 implementation phase 决定；design phase 仅约束"必须在写入磁盘前完成"。
- **Q3**：`aggregate <verb> partial: agents=<state>, claude=<state>` 中 `<state>` 的 enum 值集合（`ok / failed / not-started / partial / no-op`）由 implementation phase 在 stderr 实现时确定；design phase 仅约束语义（必须能让 operator 一眼区分 4 种状态）。

---

## 7. 边界声明

- 本草案**不修改** `docs/project-maintenance/deploy/distribution-entrypoint-contract.md` 真相层文件
- 本草案**不修改** `servo-installer.js`
- 本草案**不修改** `path_safety_policy.json`
- 本草案**不修改** `.servo/goal-charter.md`
- 本草案**不执行** `servo-installer` 或运行任何测试
- 本草案产出供 P0-071 design Gate review 与 implementation phase 整合者直接套用的修订规格；implementation phase 套用必须经新一轮 programmer 批准
