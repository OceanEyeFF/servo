---
title: "SA-B: Multi-Backend Transaction Semantics Decision Draft (P0-071 Aggregate Backend)"
artifact_type: "design-draft"
status: superseded
phase: design
worktrack: WT-20260507-aggregate-backend-design
task_id: WT-AB-002
updated: 2026-05-07
owner: research-subagent
---

# SA-B: 多 Backend 事务语义决议草案

> 仅 design phase 草案。不修改 `servo-installer.js`、不写真相层文档。SA-A 选定的命令面 protocol 在本草案中以"aggregate mode"作为通用代称；最终落地时由 SA-D 合并表达。

## 1. Executive Summary

**选定模型：每命令差异化的混合模型 (per-command hybrid)。**

总原则：

- **写前预扫描类**(`check_paths_exist`、`install`、`update --yes` 的预检阶段)：**all-or-nothing pre-write**。任一根的 source / target / conflict 检查失败时,在任何 backend 写入磁盘之前 fail-fast,零写入。
- **只读类**(`verify`、`diagnose`、`update --json` / `update` dry-run)：**collect-then-report each-independent**。两个 backend 都跑完,issues 合并汇报；exit code 在任一 backend 报告 issue 时非零。
- **写时执行类**(`install` 已开始 mkdirSync 后、`prune --all`、`update --yes` 的 apply 阶段)：**no-rollback each-independent with partial-completion surface**。一旦磁盘写入开始,跨 backend 不做回滚；先执行的 backend 即使最终被另一个 backend 失败拖累,其写入保留在磁盘上,operator 通过 `recovery hint` 明确知晓"哪个根成功、哪个根需重跑"。

**最强理由**：现有 single-backend 行为本身就**没有**为单一 backend 实现 install / update 的写后回滚——`installBackendPayloads`(2236-2310 行)mkdirSync 后失败抛错即留下半成品；`update --yes` 出错只打印 `recovery: the update may be partially applied` 提示(3076-3090 行)。在 aggregate mode 下凭空引入跨 backend 的全量回滚,需要**新增**一套 single-backend 从未承担过的语义合同(快照 + 反向操作),这违反 `distribution-entrypoint-contract.md` 中"wrapper 不能改变 deploy 语义"的硬约束。把 aggregate 设计成"两根独立、写前合并冲突扫描"是对现有合同的**最小扩展**,而把 aggregate 当成"双根原子事务"是引入了一条新合同。最小扩展胜出。

## 2. Transaction Model Choice

### 候选模型

- **Model 1 — All-or-nothing**：任一 backend 失败 → 整个 aggregate 操作回滚 → 磁盘不留半成品。
- **Model 2 — Each-independent**：backend 独立执行；部分成功被报告给 operator；不跨 backend 回滚。
- **Model 3 (混合) — Per-command hybrid**：写前预扫描合并、写时各自独立、只读独立收集。

### 决策依据

| 依据 | Model 1 (all-or-nothing) | Model 2 (each-independent) | Model 3 (混合，本草案选) |
| --- | --- | --- | --- |
| 与现有 single-backend 语义一致性 | 破坏 — single-backend 没有写后回滚合同 | 完整一致 | 完整一致 |
| 写前合并冲突短路是否可达 | 可 | 不直接可达；需在 each-independent 之上叠加 pre-scan | 显式纳入 |
| 实现复杂度（要新增什么） | 双根快照 + 反向写入 + 失败时反向重放（新合同） | 仅汇总错误 + 退出码合并（最低） | pre-scan 合并 + 错误汇总（中等） |
| operator 心智 | "全成或全失败" 简洁但与 single-backend 行为不一致 | "各根独立" 简洁且与 single-backend 一致 | "写前一起把关、写后各自承担" 清晰 |
| 失败暴露信号 | 仅 fail / success | fail / partial / success 三态 | fail / partial-with-clear-attribution / success |
| 安全性（避免误删） | 高（回滚保证）但回滚自身可能失败二次留垃圾 | 中（与现状相同） | 中（与现状相同） |
| 与 SA-C trust boundary 兼容 | 需 SA-C 设计反向回滚的 path safety | SA-C 仅需扩展双根 conflict scan | SA-C 仅需扩展双根 conflict scan |

### 选定：Model 3 (per-command hybrid)

混合模型对每条命令做差异化语义决策，全表见 §3。核心分界：

- **写前(pre-write)** 都跑 all-or-nothing：写前任一根失败,**任何根都不开始写**。
- **写后(in-write / write-completed)** 都跑 each-independent：第二根失败不撤销第一根。
- **只读** 跑 collect-then-report：两根都跑完再合并报告。

### 为什么不是纯 each-independent

如果完全采用 Model 2,会让 aggregate `install` 的两根独立执行：agents 检查冲突后立即写入,然后才轮到 claude 检查冲突。这会导致：

1. **claude 根冲突在 agents 写完后才暴露**—— operator 已被迫面对"agents 已部署、claude 阻塞"的两根不一致状态,而这本可以在所有写入前预知;
2. **失去"写前合并预扫描"的机会**—— 现有 single-backend `install` 本就先跑 `collectPathConflicts` 再 mkdirSync(2225-2233 行),这是已有的 pre-write fail-fast 模式;aggregate 应当对**两根 union** 做同样的 pre-write 检查,否则就**降级**了现有合同。

因此 pre-write 阶段必须是 all-or-nothing(union of both roots),write 阶段才退化为 each-independent。

### 为什么不是纯 all-or-nothing

如果完全采用 Model 1,aggregate `install` 在 claude 写到一半时,需要**回滚 agents 已写完的目录**——这要求实现：

1. 双根写前快照(目录结构 + content hash);
2. 反向写入路径(把 agents 已写的目录删掉);
3. 反向写入失败时的二级 recovery(回滚的回滚)。

这套合同 single-backend 从未有过;servo-installer 当前 `update --yes` 在自身失败时甚至不回滚 prune 已删掉的目录,只是打印 `recovery: the update may be partially applied`。如果 aggregate 引入完整回滚,会让"aggregate 比 single-backend 更可靠"——但这违反 `distribution-entrypoint-contract.md` 中"wrapper 必须保持同一 deploy 语义"的约束,也会让维护双语义负担。

## 3. Per-Command Failure Semantics Table

下表覆盖 6 个命令在 aggregate mode 下的事务模型、短路策略、回滚策略与 partial-completion 暴露面。

| command | transaction_model | short_circuit_policy | rollback_strategy | partial_completion_surface |
| --- | --- | --- | --- | --- |
| `install` | hybrid (pre-write all-or-nothing；write each-independent) | 预扫描阶段 fail-fast：两根任一冲突 → 立即抛错,**零写入** ▸ 写入阶段 first-fail-stop：第一个 backend 抛错后停止第二个 backend 的写入,但已写入的内容**不回滚** | agents 写成功 / claude 写失败 → claude 留半成品(可能空目录或部分文件)；agents 已写入的目录、文件、marker 全部保留;反向：claude 先 / agents 后同理 | 退出码 1；stderr 包含 `[aggregate] partial install: agents=ok, claude=failed`,后跟 claude 失败明细 + recovery hint |
| `update` (dry-run) | each-independent collect-then-report (只读) | 不短路：两 backend 都跑 plan,合并 issues 后输出 | N/A (只读) | 退出码 = 任一 backend `blocking_issue_count > 0` 即 1；输出包含两根的完整 plan |
| `update --yes` | hybrid (pre-write all-or-nothing；apply each-independent) | 预检阶段 fail-fast：任一 backend `blocking_issue_count > 0` → 任何 backend 都不进入 apply ▸ Apply 阶段 first-fail-stop：先跑的 backend 完成 prune→check→install→verify 全程后才轮到第二个,任一阶段失败立刻停止整个 aggregate,但**不回滚已成功 backend** | agents update 成功 / claude update apply 失败 → agents 的新版已 verify 通过,claude 的状态依赖于失败发生在哪一阶段(prune 已删 / install 半写 / verify 失败但 install 已完成);agents 一切保持新版,**不回退** | 退出码 1；stderr 含 `[aggregate] partial update: agents applied (verified), claude failed at <stage>`,附 single-backend recovery hint：`servo-installer update --backend claude --yes ...` |
| `verify` | each-independent collect-then-report | 不短路：两 backend 都跑 verify,合并 issues 后输出 | N/A (只读) | 退出码 = 任一 backend `issues.length > 0` 即 1；按 backend 分组输出,每根一段 issue list |
| `prune --all` | hybrid (pre-check all-or-nothing；delete each-independent) | 预检阶段 fail-fast：任一根 `targetRootReadyIssuesForAction` 失败 → 不开始任何根的删除 ▸ 删除阶段 first-fail-stop：第一个根删除中失败立刻 throw,第二个根**不开始删除** | agents prune 删除若干 dir 后 throw → 已删除的 dir **不恢复**;claude 根**完全未触动**(因为是顺序执行,claude 在 agents 之后,agents 失败前 claude 已经过 pre-check) | 退出码 1；stderr 含 `[aggregate] partial prune: agents removed N dir(s) before failure, claude not started`;operator 须依赖现有 single-backend prune 重跑收尾 |
| `check_paths_exist` | all-or-nothing pre-scan (合并双根) | 不短路：两根都跑预扫描收集 conflicts,合并报告;但这是只读检查,本身就是"短路 install/update 的判据" | N/A (只读) | 退出码 = 任一根有冲突即 1;输出 `[aggregate] found N conflicting target path(s) across roots`,按 backend 分组列出 |
| `diagnose` | each-independent collect-then-report | 不短路：两 backend 都跑 diagnose,合并 summary 输出 | N/A (只读) | 退出码 0(diagnose 不以 issue 失败);JSON 输出含 `agents` / `claude` 两个 backend section |

## 4. Rollback Strategy Detail

> 关键场景：aggregate `install` 时 agents 写入成功、claude 写入失败。

### 4.1 关键场景一：aggregate `install`,agents 已写完,claude 写到一半失败

**回滚什么**：
- 无。**任何已写入磁盘的内容均不回滚**。

**保留什么**(agents 根)：
- `${agentsRoot}/aw-{skill_id}/SKILL.md`、`payload.json`、`runtime-marker` 等所有 install plan 写入的文件,完整保留;
- 已删除的 legacy dir(install 阶段会顺手清理 same-backend legacy)也**不恢复**——legacy 已被 single-backend `install` 在 cleanup 阶段处理(2236-2266 行),恢复 legacy 既不安全也违反现有合同。

**保留什么**(claude 根 — 失败方)：
- 已 mkdirSync 的目标目录(可能为空或包含部分文件)**保留**——不调用 `rmSync` 反向清理,因为：
  1. 反向清理本身可能失败(权限、被外部进程占用),引入二次失败;
  2. claude 半成品目录会被下次 `install` 的 conflict scan 拒绝,operator 必须显式 `prune --backend claude` 才能恢复,这是**显式 operator 路径**而非隐式回滚。

**理由**：与 single-backend `install` 行为完全一致——`installBackendPayloads` 在第二个 binding 失败时,第一个 binding 已写入的内容**也不回滚**。aggregate 不应建立比 single-backend 更强的合同。

**operator 路径**：
1. 看到 stderr 中的 `[aggregate] partial install: agents=ok, claude=failed`;
2. 先 `servo-installer verify --backend agents` 确认 agents 已就绪;
3. 用 `servo-installer prune --backend claude --all` 清理半成品;
4. 解决根因(权限、磁盘等)后,用 `servo-installer install --backend claude` 单根重试;
5. 最后 `servo-installer verify` (aggregate) 确认双根一致。

### 4.2 关键场景二：aggregate `update --yes` 在 claude apply 阶段失败

**回滚什么**：
- 无。

**保留什么**(agents 根)：
- 新版 install 完整生效,verify 通过的状态。**不回退到 update 前的旧版**——回退需要 update 前的快照,这是 single-backend 合同从未承担过的。

**保留什么**(claude 根)：
- 取决于失败发生在哪一阶段：
  - **prune 阶段失败**：claude 根缺失部分旧版 dir(已删的不恢复),其余旧版保留;
  - **check_paths_exist 阶段失败**：claude 根的旧版 prune 已完成,无 install 写入,根本身可能为空或残留 unrecognized dir;
  - **install 阶段失败**：claude 根有部分新版 dir(已 mkdirSync 的),无 marker 或 marker 写入到一半;
  - **verify 阶段失败**：claude 根的新版 install 已完成,但 verify 报告 issue(说明 install 写入与 source 不匹配,通常是 source binding 异常)。

**operator 路径**:
1. stderr 显示 `[aggregate] partial update: agents applied (verified), claude failed at <stage>`;
2. 立刻 `servo-installer diagnose --backend claude` 看 claude 根当前状态;
3. 失败阶段决定恢复路径：
   - prune/check_paths_exist 失败 → `servo-installer update --backend claude --yes` 重跑;
   - install 失败 → `servo-installer prune --backend claude --all` 后再 `update --yes`;
   - verify 失败 → 检查 source binding,定位是新版 source 问题还是 install 写入异常。

### 4.3 关键场景三：aggregate `prune --all` 在 agents 删除中途失败

**回滚什么**：
- 无。

**保留什么**(agents 根)：
- 已删除的 managed dir **不恢复**(即使保存快照也不可靠：无法恢复硬链接、文件权限、xattr 等);
- 未删除的 managed dir 保留。

**保留什么**(claude 根)：
- **完全未动**——aggregate `prune --all` 是顺序执行 agents → claude,agents 失败前 claude 还未开始删除。

**operator 路径**：
1. stderr 显示 `[aggregate] partial prune: agents removed N dir(s) before failure, claude not started`;
2. 解决 agents 失败根因后,可以单根重跑 `servo-installer prune --backend agents --all`;
3. claude 根用 `servo-installer prune --backend claude --all` 完成清理。

## 5. `check_paths_exist` Pre-Scan Semantics

### 5.1 双根冲突合并扫描

aggregate `check_paths_exist`：
1. 为 agents 根构建 install plan,跑 `collectPathConflicts` + `collectLegacyPathConflicts`;
2. 为 claude 根构建 install plan,跑同样的两组扫描;
3. **合并**(union)两组 conflicts,按 backend tag 分组输出;
4. 任一根有 conflict → 退出码 1。

**关键不变量**：本命令**只读**,自身不会进行任何写入。它的 all-or-nothing 语义是体现在被它**保护的下游**——`install` / `update --yes` 在跑 check_paths_exist 阶段失败时,**任何 backend 都不会进入写入阶段**。

### 5.2 双根冲突报告结构

```
error: [aggregate] found 3 conflicting target path(s) across roots

[agents] target path conflicts:
- demo-skill: /repo/.agents/skills/aw-demo-skill (existing target path is a directory)

[claude] target path conflicts:
- demo-skill: /repo/.claude/skills/demo-skill (existing target path is a directory)
- helper-skill: /repo/.claude/skills/helper-skill (existing target path is a file)
```

### 5.3 跨根冲突的特殊情形

aggregate mode 下两根**不可能**互相成为对方的 conflict——`agents` 根写入 `${root}/.agents/skills/aw-{id}`,`claude` 根写入 `${root}/.claude/skills/{id}`。两者不共享路径。但要求 SA-C trust boundary 显式确认这一点,并对边界情况(如 operator 把两根用 `--agents-root` / `--claude-root` 指向**同一物理目录**的极端用法)给出明确的拒绝合同。

### 5.4 报告时机

aggregate `install` / `update --yes` 内部调用 check_paths_exist 时,合并报告必须**先完成两根扫描再抛错**,而不是 agents 报错就立刻 throw。这保证 operator 一次拿到两根的全部冲突清单,而不是修一个再发现下一个的串行体验。

## 6. `verify` Short-Circuit Logic

### 6.1 决策：collect-then-report (不 fail-fast)

aggregate `verify` 在两 backend 间**不短路**:agents 失败时**继续**跑 claude verify,最终合并 issues 输出。

### 6.2 理由

1. **现有 verify 自身就是 collect-then-report 模型**：`verifyBackend`(1847-1896 行)对单一 backend 内的所有 bindings 跑 verify 后**收集**全部 issues 一次性返回。aggregate 应对 backend 维度**继承**这一模式,而非引入新的"backend-level fail-fast"。
2. **operator 调试体验**：verify 是诊断工具。operator 想一次知道**两根**的全部 drift,而不是修一个根的 issue 后再次运行才发现另一根也有问题。fail-fast 会让验证轮次倍增。
3. **verify 不写磁盘**：fail-fast 主要的价值是"防止破坏",但 verify 是只读的,没有需要保护的下游。
4. **退出码语义清晰**：`exit_code = (agents.issues.length > 0 || claude.issues.length > 0) ? 1 : 0`,operator 一眼能区分"双根都干净"vs"至少一根有 drift"。

### 6.3 输出结构

```
[agents] drift: 2 issue(s) in target root at /repo/.agents/skills
  - drifted-payload: /repo/.agents/skills/aw-foo/payload.json (fingerprint mismatch)
  - missing-marker: /repo/.agents/skills/aw-bar (managed-skill marker missing)
[claude] ok: target root is ready at /repo/.claude/skills
```

或两根都失败：

```
[agents] drift: 1 issue(s) in target root at /repo/.agents/skills
  - drifted-payload: ...
[claude] drift: 1 issue(s) in target root at /repo/.claude/skills
  - foreign-managed-directory: ...
```

退出码 1。

## 7. Operator-Visible Failure Messages

### 7.1 Full success (双根全部成功)

```
[agents] installed skill demo-skill -> /repo/.agents/skills/aw-demo-skill
[claude] installed skill demo-skill -> /repo/.claude/skills/demo-skill
[aggregate] ok: install completed for both backends
```

退出码 0。

### 7.2 Pre-write full failure (写前 fail-fast)

```
error: [aggregate] install blocked by 2 existing target path(s) across roots

[agents] target path conflicts:
- demo-skill: /repo/.agents/skills/aw-demo-skill (existing target path is a directory)

[claude] target path conflicts:
- demo-skill: /repo/.claude/skills/demo-skill (existing target path is a directory)
```

退出码 1。**关键不变量：磁盘任何位置都没有发生写入。**

### 7.3 Partial completion (写后 first-fail-stop)

```
[agents] installed skill demo-skill -> /repo/.agents/skills/aw-demo-skill
[agents] installed skill helper-skill -> /repo/.agents/skills/aw-helper-skill
error: [claude] install failed: EACCES: permission denied, mkdir '/repo/.claude/skills/demo-skill'

[aggregate] partial install: agents=ok, claude=failed
recovery: agents is fully deployed at /repo/.agents/skills.
         claude is in a partial state at /repo/.claude/skills.
         After fixing the reported error, run:
           servo-installer prune --backend claude --all
           servo-installer install --backend claude
           servo-installer verify
```

退出码 1。

### 7.4 Aggregate `update --yes` partial completion

```
[agents] update plan for /repo/.agents/skills
[agents] applying update
[agents] removed managed skill dir ...
[agents] installed skill ... 
[agents] ok: target root is ready at /repo/.agents/skills
[agents] update complete

[claude] update plan for /repo/.claude/skills
[claude] applying update
[claude] removed managed skill dir ...
error: Failed to remove managed skill dir /repo/.claude/skills/demo-skill: EACCES

[aggregate] partial update: agents applied (verified), claude failed at prune
recovery: claude may be partially applied at /repo/.claude/skills.
         After fixing the reported error, run:
           servo-installer diagnose --backend claude
           servo-installer update --backend claude --yes
```

退出码 1。

### 7.5 Verify drift on either or both roots

按 §6.3 输出。退出码 1。

### 7.6 Diagnose 双根 (collect-then-report,exit 0)

```json
{
  "aggregate": true,
  "backends": {
    "agents": {
      "backend": "agents",
      "target_root": "/repo/.agents/skills",
      "managed_install_count": 2,
      "issue_count": 0,
      "issues": []
    },
    "claude": {
      "backend": "claude",
      "target_root": "/repo/.claude/skills",
      "managed_install_count": 0,
      "issue_count": 1,
      "issues": [{"code": "missing-target-root", "path": "/repo/.claude/skills", "detail": "..."}]
    }
  }
}
```

退出码 0(diagnose 即使报告 issue 也返回 0,与 single-backend 行为一致)。

## 8. Trade-off Discussion

### 8.1 拒绝的替代方案 1：纯 all-or-nothing with full rollback

**形态**：aggregate `install` 在 agents 写完、claude 写到一半失败时,自动反向写入,把 agents 已写入的内容全部删除,恢复到 install 前状态。

**拒绝理由**：
1. **新增合同**：single-backend `install` 没有写后回滚行为,aggregate 不应承担更强合同;
2. **回滚的回滚**：反向清理本身可能失败(权限、被占用、被 verify 锁定),引入"二级 partial state",failure mode 增多而非减少;
3. **快照成本**：完整回滚需要 install 前的全部 state 快照(目录列表 + content hash),这套基础设施 servo-installer 当前不存在;
4. **operator 误判风险**：operator 看到 `install` 失败后期待"什么都没改",却发现 agents 根的 legacy dir 已被 install 阶段顺手清理(2236-2266 行)——legacy cleanup 是 install 的副作用,无法回滚。"假性 all-or-nothing"比 each-independent 更危险。

### 8.2 拒绝的替代方案 2：纯 each-independent (无写前合并扫描)

**形态**：aggregate `install` 顺序执行 agents → claude,各自独立跑完整 single-backend pipeline,互相不知道对方。

**拒绝理由**：
1. **降级了现有合同**：single-backend `install` 本就先合并冲突扫描再写入,是 pre-write fail-fast。aggregate 顺序独立等于把 single-backend 的写前保护**降级**为"agents 先写,claude 后才知道自己冲突";
2. **operator 体验劣化**：claude 根的 conflict 在 agents 已部署后才暴露,operator 被迫面对"两根不一致"状态,而这本可在零写入时预知;
3. **失去 aggregate 的便利价值**：aggregate mode 的存在意义就是"一次看到双根的整体视图",纯 each-independent 等于把 aggregate 退化成"两次 single-backend 调用",没有合并价值。

### 8.3 拒绝的替代方案 3：跨命令统一 all-or-nothing(verify/prune/install 全部 fail-fast)

**形态**：把 fail-fast 应用到 verify(任一根 verify 失败立即停)、prune(任一根 prune 失败立即停)。

**拒绝理由**：
1. **verify 是诊断工具**:fail-fast 让 operator 修一次看一次,串行轮次增加;
2. **prune 已经是事实上的"first-fail-stop"** —— 因为顺序执行,前一根失败后一根就不会开始,这与"声明 fail-fast"等价,但**不需要**额外的合同;关键是不强制"agents 失败回滚 claude"——claude 还没开始就不需要回滚;
3. **混合模型已经覆盖了这个直觉**：写前合并 fail-fast,写时 first-fail-stop,只读 collect-then-report。这就是混合模型的核心,统一 fail-fast 没有新增价值。

### 8.4 风险与对策

| 风险 | 对策 |
| --- | --- |
| operator 误以为 aggregate 是事务保护 | help 文档与 stderr partial-completion 消息明确说明 "no cross-backend rollback";现有 `update --yes` recovery hint 模式提供 precedent |
| aggregate `install` 跨根 conflict scan 遗漏边界(operator 把两根指向同一目录) | SA-C trust boundary 设计中显式拒绝:agentsRoot 与 claudeRoot 必须 path-disjoint |
| aggregate `update --yes` 在 agents 已 verify 后 claude 失败,operator 怀疑 agents 是否被污染 | partial-completion 消息明确包含 `agents applied (verified)`,与 `agents partially applied` 区分 |
| collect-then-report verify 在双根都失败时输出过长 | 与现有 verify 行为一致:按 backend 分组,issue list 完整呈现;不引入 verbosity 降级 |

---

## Appendix A: 参考文件

- `toolchain/scripts/deploy/bin/servo-installer.js`
  - `installBackendPayloads` (2209-2311 行) — install pre-write conflict scan + 写入阶段
  - `applyUpdateContext` (3034-3057 行) — update --yes 顺序与无回滚行为
  - `updateFailureRecoveryHint` (3076-3090 行) — partial-completion 消息模板
  - `pruneBackendManagedInstalls` (1954-1994 行) — prune 顺序删除、首次失败 throw
  - `verifyBackend` (1847-1896 行) — collect-then-report 模型
  - `checkPathsExistSummary` (2165-2192 行) — 写前预扫描
- `docs/project-maintenance/deploy/distribution-entrypoint-contract.md` — 命令面合同表(行 24-29)
- `toolchain/scripts/deploy/test_servo_installer.js`
  - `servo-installer update agents yes prints recovery hint after apply failure` (3544 行)
  - `servo-installer install agents blocks non-clean target conflicts without Python or writes` (2413 行)
  - `servo-installer install agents rejects source and target readiness failures without Python` (2461 行)

## Appendix B: 与 SA-A / SA-C / SA-D 的接口

- **SA-A** (命令面 protocol)：本草案的"aggregate mode"在 CLI 落地形式(候选 A/B/C 之一)由 SA-A 决定,本草案语义独立于具体选择。
- **SA-C** (trust boundary)：本草案声明 agentsRoot 与 claudeRoot 必须 path-disjoint,具体的 disjoint 检查规则与 path_safety_policy.json 影响由 SA-C 给出。
- **SA-D** (合同草案):本草案的事务语义需要被纳入 distribution-entrypoint-contract.md 的命令面合同表,具体合同条款修订由 SA-D 撰写。
