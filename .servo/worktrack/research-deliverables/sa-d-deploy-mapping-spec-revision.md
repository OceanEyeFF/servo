---
title: "SA-D: deploy-mapping-spec.md Revision Draft (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-004
updated: 2026-05-07
owner: research-subagent
---

# SA-D: deploy-mapping-spec.md 修订草案

> 本草案仅服务于 design phase。它**不修改** `docs/project-maintenance/deploy/deploy-mapping-spec.md` 真相层文件；目标是产出一份"可在 implementation phase 由 SA-D 整合者直接套用"的修订规格。本草案的 mapping 关系完全承接自 SA-A / SA-C：
>
> - SA-A 推荐：**`--backend bundle` enum 扩展**——bundle 是 `--backend` 枚举的第三个合法值。
> - SA-C 推荐：**dual-root mapping 是两组完全独立的 mapping 行的并集**，agents 行与 claude 行各自保持单 backend 语义；不引入"跨根 mapping"或"跨根 target_dir 唯一性约束"。
>
> 修订原则：
>
> 1. **既有两行 target 命名约定一字不改**——`agents → aw-{skill_id}` 与 `claude → {skill_id}` 保持现行表达。
> 2. **bundle 不是新映射，是双映射的同时呈现**——dispatcher 在 aggregate mode 下同时构造 agents 与 claude 两组 binding，每组 binding 各自走既有 mapping 路径；mapping 表新增一行 `bundle` 显式说明此关系，避免读者从 "bundle = agents + claude" 的常识中错误推断。
> 3. **`target_dir` 唯一性是"per-root"而非"跨根"**——即 `target_dir` 在 agents 根内唯一，claude 根内独立唯一；agents 根的 `aw-foo` 与 claude 根的 `foo` 不冲突，因为它们位于物理不重叠的两个 target root。这是 SA-C §2.3 的 trust boundary 决议。
> 4. **canonical source 不分裂**——aggregate mode 仍然只有一个 canonical source（`product/harness/skills/`）；agents 与 claude 共享同一 canonical 但通过各自 adapter（`product/harness/adapters/agents/skills/` 与 `product/harness/adapters/claude/skills/`）派生出各自的 backend payload source。bundle 在此层不引入第三套 source。

---

## 1. Revision Summary

修订涉及 5 个 section：

| section | 操作 | 落点 |
| --- | --- | --- |
| Frontmatter | update `updated` / `last_verified`（implementation phase 套用时填入正式日期） | YAML header |
| § 段首引文 | 不变 | — |
| § 映射链路 | 段尾追加一句"aggregate mode 在同一命令中同时实例化 agents 与 claude 两组 mapping 链路；canonical source 共享，backend payload source、payload descriptor、target entry 各自独立" | 段落 |
| § 最小字段 | 不变（字段表保留；唯一性条款补一段"per-root"澄清） | 表格之后 |
| § 当前稳定 target 命名 | **不删既有 2 行**；新增 1 行 `bundle` 显式表达"`aw-{skill_id}` 在 agents 根 + `{skill_id}` 在 claude 根" | 表格 |
| § 命令读取面 | 段尾追加一段"aggregate mode 下命令读取面是两组单 backend 读取面的合集（per backend），不引入跨根读取" | 段落 |
| § 不变量 | 段尾追加一句"aggregate mode 不放宽 `target_dir` 唯一性条款；唯一性是 per-root，不跨根" | 段落 |

修订**不**改写：`canonical_dir` / `skill_id` / `target_dir` / `target_entry_name` / `required_payload_files` / policy fields 的最小要求；映射链路的 `canonical source -> backend payload source -> payload descriptor -> target entry -> verify` 拓扑；"target entry 与 runtime payload 不是 source of truth" 不变量。

---

## 2. Section-by-Section Revision (before/after diff blocks)

### 2.1 Frontmatter

**BEFORE**

```markdown
---
title: "Deploy Mapping Spec"
status: active
updated: 2026-05-06
owner: servo-kernel
last_verified: 2026-05-06
---
```

**AFTER**

```markdown
---
title: "Deploy Mapping Spec"
status: active
updated: <implementation-phase-date>
owner: servo-kernel
last_verified: <implementation-phase-date>
---
```

**Diff**

```diff
 ---
 title: "Deploy Mapping Spec"
 status: active
-updated: 2026-05-06
+updated: <implementation-phase-date>
 owner: servo-kernel
-last_verified: 2026-05-06
+last_verified: <implementation-phase-date>
 ---
```

**Notes**：日期占位符同 D-1。

---

### 2.2 §"映射链路"

**BEFORE**

```markdown
## 映射链路

`canonical source -> backend payload source -> payload descriptor -> target entry -> verify`；canonical source 是唯一 truth（`product/harness/skills/`），backend payload source 是分发载体（`adapters/<backend>/skills/`），payload descriptor 只描述分发所需信息，target entry 是 live install 落点且不回写 source。
```

**AFTER**

```markdown
## 映射链路

`canonical source -> backend payload source -> payload descriptor -> target entry -> verify`；canonical source 是唯一 truth（`product/harness/skills/`），backend payload source 是分发载体（`adapters/<backend>/skills/`），payload descriptor 只描述分发所需信息，target entry 是 live install 落点且不回写 source。

聚合 backend (`--backend bundle`) 在同一命令调用中同时实例化 agents 与 claude 两组 mapping 链路。canonical source 共享（一个 canonical source 同时驱动两组 backend payload source），但 `backend payload source -> payload descriptor -> target entry -> verify` 这一段在两个 backend 上各自独立运行，互不交叉：
- agents 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/agents/skills/{skill_id}/` -> agents payload descriptor -> `<targetRepoRoot>/.agents/skills/aw-{skill_id}/` -> agents verify
- claude 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/claude/skills/{skill_id}/` -> claude payload descriptor -> `<targetRepoRoot>/.claude/skills/{skill_id}/` -> claude verify

bundle 不创建第三条链路；它只是 dispatcher 决定"同时驱动这两条链路"的 control-plane 行为。
```

**Diff**

```diff
 ## 映射链路

 `canonical source -> backend payload source -> payload descriptor -> target entry -> verify`；canonical source 是唯一 truth（`product/harness/skills/`），backend payload source 是分发载体（`adapters/<backend>/skills/`），payload descriptor 只描述分发所需信息，target entry 是 live install 落点且不回写 source。
+
+聚合 backend (`--backend bundle`) 在同一命令调用中同时实例化 agents 与 claude 两组 mapping 链路。canonical source 共享（一个 canonical source 同时驱动两组 backend payload source），但 `backend payload source -> payload descriptor -> target entry -> verify` 这一段在两个 backend 上各自独立运行，互不交叉：
+- agents 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/agents/skills/{skill_id}/` -> agents payload descriptor -> `<targetRepoRoot>/.agents/skills/aw-{skill_id}/` -> agents verify
+- claude 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/claude/skills/{skill_id}/` -> claude payload descriptor -> `<targetRepoRoot>/.claude/skills/{skill_id}/` -> claude verify
+
+bundle 不创建第三条链路；它只是 dispatcher 决定"同时驱动这两条链路"的 control-plane 行为。
```

**Notes**：本段是修订草案的关键澄清——把 bundle 的本质（"同时驱动两条独立链路"）显式写出，避免下游读者错误推断"bundle 是新链路 / 新 source / 新 descriptor"。两条链路的展开**完整列出每个阶段的物理路径**（含 `aw-{skill_id}` 与 `{skill_id}` 的 target_dir 差异），方便 implementation phase 直接对照。

---

### 2.3 §"最小字段"

**BEFORE**

```markdown
## 最小字段

| 字段 | 最小要求 |
| --- | --- |
| `canonical_dir` | 相对 repo root 的安全路径，唯一定位 canonical source |
| `skill_id` | 在 canonical source、payload descriptor、target entry 间保持稳定身份 |
| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一 |
| `target_entry_name` | 唯一标识运行时入口 |
| `required_payload_files` | 显式列出严格复验所需的最小文件 |
| policy fields | 显式声明 copy/frontmatter transform/legacy cleanup 等策略 |

`canonical_dir`、`target_dir`、`target_entry_name`、`required_payload_files` 都必须是安全相对路径，不跳出各自根目录。
```

**AFTER**

```markdown
## 最小字段

| 字段 | 最小要求 |
| --- | --- |
| `canonical_dir` | 相对 repo root 的安全路径，唯一定位 canonical source |
| `skill_id` | 在 canonical source、payload descriptor、target entry 间保持稳定身份 |
| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一（per-root：`agents` 根内唯一、`claude` 根内独立唯一） |
| `target_entry_name` | 唯一标识运行时入口 |
| `required_payload_files` | 显式列出严格复验所需的最小文件 |
| policy fields | 显式声明 copy/frontmatter transform/legacy cleanup 等策略 |

`canonical_dir`、`target_dir`、`target_entry_name`、`required_payload_files` 都必须是安全相对路径，不跳出各自根目录。

聚合 backend (`--backend bundle`) 不引入新的字段。每个字段的"最小要求"不变，仅 `target_dir` 唯一性以 per-root 视角解读：agents 根内的 `aw-{skill_id}` 与 claude 根内的 `{skill_id}` 因物理位于不同 target root，**不构成跨根唯一性冲突**。
```

**Diff**

```diff
 ## 最小字段

 | 字段 | 最小要求 |
 | --- | --- |
 | `canonical_dir` | 相对 repo root 的安全路径，唯一定位 canonical source |
 | `skill_id` | 在 canonical source、payload descriptor、target entry 间保持稳定身份 |
-| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一 |
+| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一（per-root：`agents` 根内唯一、`claude` 根内独立唯一） |
 | `target_entry_name` | 唯一标识运行时入口 |
 | `required_payload_files` | 显式列出严格复验所需的最小文件 |
 | policy fields | 显式声明 copy/frontmatter transform/legacy cleanup 等策略 |

 `canonical_dir`、`target_dir`、`target_entry_name`、`required_payload_files` 都必须是安全相对路径，不跳出各自根目录。
+
+聚合 backend (`--backend bundle`) 不引入新的字段。每个字段的"最小要求"不变，仅 `target_dir` 唯一性以 per-root 视角解读：agents 根内的 `aw-{skill_id}` 与 claude 根内的 `{skill_id}` 因物理位于不同 target root，**不构成跨根唯一性冲突**。
```

**Notes**：表格 6 行**完全保留**，仅 `target_dir` 行末尾追加 per-root 括号澄清。表后追加段落显式表达"bundle 不引入新字段"，避免实施 phase 误以为需要在 mapping schema 引入 `bundle_target_dir` 之类。

---

### 2.4 §"当前稳定 target 命名"

**BEFORE**

```markdown
## 当前稳定 target 命名

| backend | 当前稳定 `target_dir` 约定 |
| --- | --- |
| `agents` | `aw-{skill_id}` |
| `claude` | `{skill_id}` |
```

**AFTER**

```markdown
## 当前稳定 target 命名

| backend | 当前稳定 `target_dir` 约定 |
| --- | --- |
| `agents` | `aw-{skill_id}` |
| `claude` | `{skill_id}` |
| `bundle` | 同时实例化两组：agents 端 = `aw-{skill_id}`（在 `<targetRepoRoot>/.agents/skills/` 下），claude 端 = `{skill_id}`（在 `<targetRepoRoot>/.claude/skills/` 下） |

`bundle` 行的 `target_dir` 不是单一字符串，而是 dispatcher 同时构造的双 binding 集合；每条 binding 仍各自满足前两行的稳定约定。`bundle` 不引入新的 target 命名规则，仅显式声明"两个 distribution 的 binding 在同一命令中同时存在"。

> 双根 path-disjoint 不变量：bundle 模式下，`<targetRepoRoot>/.agents/skills/` 与 `<targetRepoRoot>/.claude/skills/` 必须解析为物理不重叠的目录（dispatcher 在 context 构造阶段 reject `--agents-root` 与 `--claude-root` 解析后指向同一目录的组合）；详见 `distribution-entrypoint-contract.md` § "Aggregate Backend (`--backend bundle`)" § "Dual-Root Failure Short-Circuit" 第 3 条与 `payload-provenance-trust-boundary.md`。
```

**Diff**

```diff
 ## 当前稳定 target 命名

 | backend | 当前稳定 `target_dir` 约定 |
 | --- | --- |
 | `agents` | `aw-{skill_id}` |
 | `claude` | `{skill_id}` |
+| `bundle` | 同时实例化两组：agents 端 = `aw-{skill_id}`（在 `<targetRepoRoot>/.agents/skills/` 下），claude 端 = `{skill_id}`（在 `<targetRepoRoot>/.claude/skills/` 下） |
+
+`bundle` 行的 `target_dir` 不是单一字符串，而是 dispatcher 同时构造的双 binding 集合；每条 binding 仍各自满足前两行的稳定约定。`bundle` 不引入新的 target 命名规则，仅显式声明"两个 distribution 的 binding 在同一命令中同时存在"。
+
+> 双根 path-disjoint 不变量：bundle 模式下，`<targetRepoRoot>/.agents/skills/` 与 `<targetRepoRoot>/.claude/skills/` 必须解析为物理不重叠的目录（dispatcher 在 context 构造阶段 reject `--agents-root` 与 `--claude-root` 解析后指向同一目录的组合）；详见 `distribution-entrypoint-contract.md` § "Aggregate Backend (`--backend bundle`)" § "Dual-Root Failure Short-Circuit" 第 3 条与 `payload-provenance-trust-boundary.md`。
```

**Notes**：bundle 行**显式**声明"agents 端 + claude 端 同时实例化"，且把两端的 target root 物理路径前缀（`.agents/skills/` 与 `.claude/skills/`）写入合同——这是任务要求"使 dual mapping explicit 而不是从 'bundle = agents + claude' 推断"的关键落点。表后追加 path-disjoint 不变量，引用 D-1 草案对应章节，与 SA-C 决议保持一致。

---

### 2.5 §"命令读取面"

**BEFORE**

```markdown
## 命令读取面

- `check_paths_exist` 只读取当前 source 声明的目标路径，用于写入前冲突扫描
- `diagnose` 与 `verify` 读取同一映射信息，退出语义不同
- `install` 只写当前 descriptor 声明的 live payload

最小读取项：source 是否合法（无重复 `target_dir`）、target entry 与 `required_payload_files` 存在且类型正确、payload descriptor 身份字段与当前 binding 一致、live install 与当前 source 对齐。
```

**AFTER**

```markdown
## 命令读取面

- `check_paths_exist` 只读取当前 source 声明的目标路径，用于写入前冲突扫描
- `diagnose` 与 `verify` 读取同一映射信息，退出语义不同
- `install` 只写当前 descriptor 声明的 live payload

最小读取项：source 是否合法（无重复 `target_dir`）、target entry 与 `required_payload_files` 存在且类型正确、payload descriptor 身份字段与当前 binding 一致、live install 与当前 source 对齐。

聚合 backend (`--backend bundle`) 模式下，命令读取面是两组单 backend 读取面的并集：
- agents 端按既有单 backend 读取面执行（读 `adapters/agents/skills/` source 与 `<targetRepoRoot>/.agents/skills/` target）
- claude 端按既有单 backend 读取面执行（读 `adapters/claude/skills/` source 与 `<targetRepoRoot>/.claude/skills/` target）

不引入跨根读取（例如不存在"以 agents source 读取 claude target"的混合读取）。`check_paths_exist` 在 bundle 模式下做 union 视角的 fail-closed 短路（任一根有冲突即整体 fail-closed），但**冲突扫描自身仍是 per-root 独立**——两根的 plannedTargetPaths 集合各自独立计算，最终在 dispatcher 层做 union 报告。
```

**Diff**

```diff
 ## 命令读取面

 - `check_paths_exist` 只读取当前 source 声明的目标路径，用于写入前冲突扫描
 - `diagnose` 与 `verify` 读取同一映射信息，退出语义不同
 - `install` 只写当前 descriptor 声明的 live payload

 最小读取项：source 是否合法（无重复 `target_dir`）、target entry 与 `required_payload_files` 存在且类型正确、payload descriptor 身份字段与当前 binding 一致、live install 与当前 source 对齐。
+
+聚合 backend (`--backend bundle`) 模式下，命令读取面是两组单 backend 读取面的并集：
+- agents 端按既有单 backend 读取面执行（读 `adapters/agents/skills/` source 与 `<targetRepoRoot>/.agents/skills/` target）
+- claude 端按既有单 backend 读取面执行（读 `adapters/claude/skills/` source 与 `<targetRepoRoot>/.claude/skills/` target）
+
+不引入跨根读取（例如不存在"以 agents source 读取 claude target"的混合读取）。`check_paths_exist` 在 bundle 模式下做 union 视角的 fail-closed 短路（任一根有冲突即整体 fail-closed），但**冲突扫描自身仍是 per-root 独立**——两根的 plannedTargetPaths 集合各自独立计算，最终在 dispatcher 层做 union 报告。
```

**Notes**：把 SA-B §3 / SA-C §2.2 表 A 的 `check_paths_exist` 双根 union 短路语义沉到 mapping spec 这一层（mapping spec 描述读取面，所以 union 在 mapping 层的体现是"读取计算独立 + 报告 union"）。

---

### 2.6 §"不变量"

**BEFORE**

```markdown
## 不变量

target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明。
```

**AFTER**

```markdown
## 不变量

target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一（per-root：在每个 backend 各自的 target root 内唯一，跨根的同名 skill 通过两套独立的 `target_dir` 约定区分）；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明；聚合 backend (`--backend bundle`) 不放宽 `target_dir` 唯一性条款，唯一性是 per-root 不跨根。
```

**Diff**

```diff
 ## 不变量

-target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明。
+target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一（per-root：在每个 backend 各自的 target root 内唯一，跨根的同名 skill 通过两套独立的 `target_dir` 约定区分）；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明；聚合 backend (`--backend bundle`) 不放宽 `target_dir` 唯一性条款，唯一性是 per-root 不跨根。
```

**Notes**：把"`target_dir` 唯一性 = per-root"显式写进不变量段；这与 §2.3 的最小字段表追加一致，闭合 per-root 唯一性论述。

---

## 3. Net Diff Summary

```diff
@@ frontmatter @@
-updated: 2026-05-06
+updated: <implementation-phase-date>
-last_verified: 2026-05-06
+last_verified: <implementation-phase-date>

@@ section: 映射链路 @@
 `canonical source -> backend payload source -> payload descriptor -> target entry -> verify`；canonical source 是唯一 truth（`product/harness/skills/`），backend payload source 是分发载体（`adapters/<backend>/skills/`），payload descriptor 只描述分发所需信息，target entry 是 live install 落点且不回写 source。
+
+聚合 backend (`--backend bundle`) 在同一命令调用中同时实例化 agents 与 claude 两组 mapping 链路。...
+(详见 §2.2 完整正文)

@@ section: 最小字段 @@
-| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一 |
+| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一（per-root：`agents` 根内唯一、`claude` 根内独立唯一） |
+
+聚合 backend (`--backend bundle`) 不引入新的字段。...

@@ section: 当前稳定 target 命名 @@
+| `bundle` | 同时实例化两组：agents 端 = `aw-{skill_id}`（在 `<targetRepoRoot>/.agents/skills/` 下），claude 端 = `{skill_id}`（在 `<targetRepoRoot>/.claude/skills/` 下） |
+
+`bundle` 行的 `target_dir` 不是单一字符串...
+(详见 §2.4 完整正文)

@@ section: 命令读取面 @@
 最小读取项：source 是否合法（无重复 `target_dir`）、target entry 与 `required_payload_files` 存在且类型正确、payload descriptor 身份字段与当前 binding 一致、live install 与当前 source 对齐。
+
+聚合 backend (`--backend bundle`) 模式下，命令读取面是两组单 backend 读取面的并集：
+(详见 §2.5 完整正文)

@@ section: 不变量 @@
-target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明。
+target entry 与 runtime payload 不是 source of truth；`target_dir` 必须唯一（per-root：...）；映射合同只服务 destructive reinstall，不承接 archive/release channel；backend-specific 细节在 adapter 附码说明；聚合 backend (`--backend bundle`) 不放宽 `target_dir` 唯一性条款，唯一性是 per-root 不跨根。
```

---

## 4. Mapping Visualization

为方便 implementation phase 读者一眼看懂 dual mapping，下面给一份 ASCII 视图（不进入正式合同，只作 design phase 辅助）：

```
                           canonical source (single truth)
                           product/harness/skills/{skill_id}/
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                                             ▼
   product/harness/adapters/                 product/harness/adapters/
   agents/skills/{skill_id}/                 claude/skills/{skill_id}/
                │                                             │
                ▼                                             ▼
   agents payload descriptor                claude payload descriptor
                │                                             │
                ▼                                             ▼
   <targetRepoRoot>/.agents/skills/         <targetRepoRoot>/.claude/skills/
                aw-{skill_id}/                          {skill_id}/
                │                                             │
                ▼                                             ▼
        agents verify                                 claude verify

bundle dispatcher 视角：在同一命令中同时驱动两条链路；不创建第三条。
canonical 共享，descriptor / target entry / verify 各自独立。
```

---

## 5. Backward-Compat Compliance

| 维度 | 修订前合同 | 修订后合同 | 兼容性 |
| --- | --- | --- | --- |
| `agents` 单 backend mapping 链路 | `canonical -> adapters/agents -> agents descriptor -> .agents/skills/aw-{skill_id} -> verify` | **不变** | 完全兼容 |
| `claude` 单 backend mapping 链路 | `canonical -> adapters/claude -> claude descriptor -> .claude/skills/{skill_id} -> verify` | **不变** | 完全兼容 |
| `agents` 行 target_dir 命名 | `aw-{skill_id}` | **不变** | 完全兼容 |
| `claude` 行 target_dir 命名 | `{skill_id}` | **不变** | 完全兼容 |
| 6 字段最小要求 | 各字段含义不变 | **不变**（仅 `target_dir` 行末尾括号澄清为 per-root 唯一性） | 完全兼容 |
| 4 不变量 | 4 项不变量 | 1 项 unchanged + 3 项 unchanged + 1 项追加（per-root 唯一性 + bundle 声明），原文逻辑保持 | 完全兼容 |
| `target_dir` 跨根冲突 | 无定义（既有合同隐含单 backend 视角） | 显式定义"per-root 唯一性，跨根不冲突" | additive；不冲突现有 single-backend 测试 |

---

## 6. Cross-document Consistency

本草案套用后必须与下列文档保持一致：

- `docs/project-maintenance/deploy/distribution-entrypoint-contract.md`：套用 D-1 草案（`sa-d-distribution-entrypoint-contract-revision.md`）的 § "Aggregate Backend (`--backend bundle`)" 与 CLI/TUI 不变量第 5 条
- `docs/project-maintenance/deploy/payload-provenance-trust-boundary.md`：补一句"aggregate mode 不引入新的写入边界，只组合两个 backend 各自的现有边界"（per SA-C §8）
- `.servo/goal-charter.md`：**不需要修订**（per `sa-d-charter-tension-declaration.md` D-3 草案）
- `product/harness/adapters/agents/skills/` 与 `product/harness/adapters/claude/skills/`：source 结构**不动**（aggregate 不引入第三套 adapter）

---

## 7. Implementation Phase Application Notes

implementation phase 套用本草案时：

1. **不要拆分修订**——5 个 section 修订必须在同一个 commit 内套用；
2. **frontmatter 日期**——`updated` 与 `last_verified` 用 `servo-installer` aggregate backend 实装合并日填入；不可早于 implementation phase 的 design Gate 通过日；
3. **mapping 表新增行的渲染**——`bundle` 行的 `target_dir` 列建议在长格内换行展示（Markdown 表格本身允许 `<br>` 或 `\n` 视渲染器而定）；如果渲染器对长单元格不友好，可以把 `bundle` 行内容拆成两个子行（"agents 端"与"claude 端"），但**不**改变内容；
4. **path-disjoint 引用**——本节通过 `>` 引用块引用 D-1 草案章节；implementation phase 套用时 D-1 必须先套用（章节才存在），或者在套用 D-2 时一并套用 D-1（推荐方案：D-1 与 D-2 同 commit 套用）。

---

## 8. Open Questions Surfaced for Implementation Phase

下列条目是本修订草案明确**留给 implementation phase**的问题；本草案不替它们回答：

- **Q1**：mapping 表的 `bundle` 行长度可能溢出狭长视图。implementation phase 决定具体渲染：保持单行 vs 拆为两子行；design phase 仅约束语义内容（"两组 binding 同时存在 + 两组 target_dir 各自满足前两行约定"）。
- **Q2**：未来若新增第三个 backend（例如 `gemini`、`continue`），bundle 是否扩容为"三 distribution 同时安装"？design phase 对此**不预设**；当前 bundle 严格定义为 agents + claude 两 distribution，第三 backend 的扩容由后续 worktrack 重新评估。
- **Q3**：`bundle` 行的 `target_dir` 是否应在 mapping registry / payload descriptor 中以"双 binding 数组"显式落库？design phase 不预设；implementation phase 决定具体数据结构（dispatcher 内部状态 vs 持久化 schema）。

---

## 9. 边界声明

- 本草案**不修改** `docs/project-maintenance/deploy/deploy-mapping-spec.md` 真相层文件
- 本草案**不修改** `servo-installer.js`
- 本草案**不修改** `path_safety_policy.json`
- 本草案**不修改** `product/harness/adapters/` 下任何 source
- 本草案**不修改** `.servo/goal-charter.md`
- 本草案**不执行** `servo-installer` 或运行任何测试
- 本草案产出供 P0-071 design Gate review 与 implementation phase 整合者直接套用的修订规格；implementation phase 套用必须经新一轮 programmer 批准
