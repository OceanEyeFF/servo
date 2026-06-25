---
title: "Skill 公共约束"
status: active
updated: "2026-05-09"
owner: "servo-kernel"
last_verified: 2026-06-13
---

# Skill 公共约束

本文档定义了所有 Harness Skills 必须遵守的公共约束。各 Skill 在其 `## 硬约束` 段中应引用本文档，只列出该 Skill 特有的约束。

---

## C-1: Scope 边界约束

每个 Skill 只能在其声明的 Scope/Function 算子内操作：
- **RepoScope 技能**不得执行 WorktrackScope 操作（如分派执行、验证证据、关卡判定）
- **WorktrackScope 技能**不得跨 Scope 执行 RepoScope 操作（如修改 Goal Charter、修改 Repo Snapshot）

越界行为必须返回 `blocked`，并路由到正确的控制算子。

## C-2: 控制状态约束

- 变更 `Harness Control State` 的行为仅在 `Close`（`worktrack-close-skill`、`repo-refresh-skill`）、`SetGoal`（`harness-set-goal-skill`）或 `ChangeGoal`（`repo-change-goal-skill`）阶段合法
- 其余所有 Skill 必须返回结构化输出供监督器（`harness-skill`）决策
- 状态更新的唯一合法依据是经过 Gate 裁决后的判定结果；子代理的返回结果不能直接作为状态更新依据

## C-3: 输出协议约束

所有 Skill 产出的 artifact 必须遵守：

1. **先生成完整报告，再提取 Control Signal 层**：先生成尽可能长且完整的原始内容；然后提取影响下一动作决策的关键结论到 `Control Signal` 层
2. **重复上下文使用引用**：已在其他 artifact 中记录的信息使用 `[文件路径#节]` 引用，禁止内联全文复制
3. **空字段使用 `N/A`**：无实质内容的字段使用 `N/A` 或省略；用占位符填充的行为必须返回 `blocked`
4. **`Supporting Detail` 保留完整内容**：只用于后续查阅，不纳入传递上下文

## C-4: 角色边界约束

| 阶段 | 算子 | 合法行为 | 禁止行为 |
|------|------|---------|---------|
| Observe | `repo-status-skill` / `worktrack-status-skill` / `milestone-status-skill` | 读取传感器数据，产出结构化状态估计 | 选择下一步动作、分派执行、输出 gate 判定 |
| Decide | `repo-whats-next-skill` / `worktrack-schedule-skill` | 基于状态估计选择算子，产出路由建议 | 执行选中动作、变更控制状态、输出 gate 判定 |
| Init | `worktrack-init-skill` | 创建分支、固定基准、构建约定、播种队列 | 实现、验证、关卡判定 |
| Dispatch | `worktrack-dispatch-skill` / `worktrack-generic-worker-skill` | 绑定技能、打包任务、分派执行 | 算子选择、裁决判定 |
| Verify | `worktrack-review-evidence-skill` / `worktrack-test-evidence-skill` / `worktrack-rule-check-skill` | 收集对应维度的证据 | 输出最终关卡判定 |
| Judge | `worktrack-gate-skill` | 基于证据做 gate 判定，输出 verdict | 执行修复、重跑实现、变更控制状态 |
| Recover | `worktrack-recover-skill` | 评估恢复路径、选择恢复策略 | 静默执行破坏性操作 |
| Close | `worktrack-close-skill` / `repo-refresh-skill` | 收尾处理、代码仓库刷新 | 重新打开实现、重排计划 |

## C-5: 上游产出物约束

- 验收标准、排除目标、恢复策略的唯一合法来源是已被批准的上游产物（`Goal Charter`、`Worktrack Contract`）
- 对上游产物的唯一合法操作是读取消费；改写上游产物的行为必须返回 `blocked`
- 凭空发明验收标准或验证要求的行为必须返回 `blocked`

## C-6: 缺失证据约束

- 缺失证据的唯一合法处理方式是显式暴露缺口
- 将缺失证据当成隐式成功的行为禁止发生
- 充分证据必须来自可复现的自动化检查、明确关联验收标准的测试结果或可验证的命令输出

## C-7: 范围收窄约束

- 当限定范围已足够时，传入完整代码仓库上下文的行为必须返回 `blocked`
- 当当前问题很狭窄时，扩展成完整重新发现的行为必须被阻断
- 唯一合法行为是保持限定范围内操作

## C-8: 分布式 Skill 自洽约束

`product/harness/skills/` 下每个 canonical skill package 必须作为可独立分发、可独立运行的执行单元自洽。安装到 `.agents/` 或 `.claude/` 后，skill 包不得依赖以下任何一项来执行其运行时语义：

- 源仓库中的 `docs/harness/`、`docs/project-maintenance/` 或其他 docs 路径
- 当前包外的 `.agents/`、`.claude/`、`.servo/`、`.nav/`、`.autoworkflow/` 或 `.spec-workflow/` 路径
- 父目录逃逸引用（`../`）
- 包外软链
- 仓库外绝对路径、本地机器路径或未发布合同

Trace link 到 docs 只能作为源侧 ownership 或 authoring 引用，不能作为安装后包的运行时权威来源。当 docs 合同在运行时确属必需时，应将最小稳定合同复制到 `SKILL.md` 或同包内的捆绑文件，并确保 adapter payload 描述符包含该文件。

完整规则见 [product/harness/skills/README.md](../../../product/harness/skills/README.md) 的 Distributed Skill Product Shape 节。

---

## 各 Skill 特有约束指引

引用本文档后，各 Skill 的 `## 硬约束` 段应仅包含：
1. 一句引用声明：`遵循 [docs/harness/foundations/skill-common-constraints.md] 中定义的公共约束 C-1 至 C-8`
2. 本 Skill 特有的约束（通常 3-8 条）
