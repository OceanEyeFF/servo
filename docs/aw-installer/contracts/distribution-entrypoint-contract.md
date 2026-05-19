---
title: "Distribution Entrypoint Contract"
status: active
updated: 2026-05-08
owner: aw-kernel
last_verified: 2026-05-08
---
# Distribution Entrypoint Contract

> 目的：明确 `aw-installer` 作为 deploy 分发入口必须保持的 wrapper 语义。

本页管理 `aw-installer` 命令不变量、CLI/TUI 不分叉语义与 backend 暴露口径（含聚合 backend `bundle`）。release channel、trust boundary、mapping 见相邻文档。

## 当前 package/runtime surface

- bin surface 是 `aw-installer`，当前支持 `agents`、`claude` 与聚合值 `bundle`；未支持 backend 或命令变体显式失败
- `bundle` 是 `--backend` 枚举的第三个合法值；它不是新的 distribution，而是"在 `agents` 与 `claude` 两个 distribution 上同时执行同一 verb"的 dispatcher 别名
- CLI 是稳定脚本接口；TUI 只能是同一合同上的交互层

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

`update --yes` 的成功定义：两根都完整通过 `prune -> check_paths_exist -> install -> verify` 全 pipeline；任一根任一阶段失败即整体 partial。pre-check 阶段使用 union 视角短路（任一根 blocking_issue_count > 0 都不进入 apply），与 §"命令面合同" 表中 single backend `update --yes` 的 fail-closed 语义一致。

### Dual-Root Failure Short-Circuit

dual-root 失败短路是 aggregate mode 的"fail-closed on writes"硬合同，承接自 SA-C trust boundary 决议。规则如下：

1. **写前 fail-closed**：`install` / `update --yes` / `prune --all` 在 pre-check / pre-write 阶段，任一根失败 → 任何根都不进入实际写入或删除阶段；磁盘任何位置都不发生变更。
2. **写时 first-fail-stop**：写入或删除阶段按 ASCII 顺序 `agents` → `claude` 执行；前一根成功后才轮到后一根；前一根失败时第二根不开始。**已写入或已删除的内容保留**，不做反向回滚。
3. **跨根 path-disjoint 强制**：dispatcher 在 context 构造阶段拒绝 `--agents-root` 与 `--claude-root` 解析后指向同一物理目录的组合（不论是否 symlink 等价）；理由：双根 marker.backend 互斥保证由路径不重叠承担，重叠会让 prune 走错根的物理目录。
4. **错误归因前缀**：aggregate mode 下所有 stderr / stdout / `--json` 输出在每条信息上加 `[backend=<name>]` 前缀（`<name>` ∈ `{agents, claude, aggregate}`）；`aggregate` 前缀只用于双根汇总信息（如 partial 消息、final summary），单根错误必须用对应 backend 前缀；TUI 必须保留同前缀以维持 CLI/TUI 等价。
5. **partial-completion 必须显式表达**：任一 mutating verb 出现 partial 时，stderr 必须输出 `aggregate <verb> partial: agents=<state>, claude=<state>` 一行，并附与现有 `update --yes` recovery hint 同形态的修复路径建议；实施 phase 在 implementation 中以 single-backend 命令组合作为 recovery 路径（不引入 aggregate-only recovery verb）。
6. **`path_safety_policy.json` 不变更**：dual-root 不触发 policy schema 修订；每根独立通过 `validateTargetRepoRoot` 即满足；详见 SA-C §5。

## CLI / TUI 不变量

- TUI 不得拥有独立于 CLI 的 install/update 语义；所有 mutating TUI 动作必须映射到明确的 CLI mode（包括 `--backend bundle` 模式）
- 非交互环境不得隐式启动 TUI；`--json` 只属 CLI 机器输出，不得混入交互渲染
- `diagnose` 不是安装成功证明；严格失败信号只能来自 `verify`
- wrapper 不得把 deploy target 当成 source of truth
- aggregate 模式下所有 stderr/stdout 输出必须带 `[backend=<name>]` 前缀；TUI 必须保留同前缀，不得为 bundle 引入独立子菜单或独立事务执行流

## 停止线

问题已进入 release channel、payload source 设计、target root trust boundary 或 operator 执行步骤时，本页只提供链接，不展开。
