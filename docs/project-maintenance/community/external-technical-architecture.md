---
title: "Servo 对外技术与架构叙事"
status: active
updated: 2026-06-19
owner: servo-kernel
last_verified: 2026-06-19
---
# Servo 对外技术与架构叙事

本文用于整理 Servo 面向外部读者时的技术侧和架构侧表达。它不是安装 runbook，也不是 release governance；它回答的是：为什么 AI coding 需要一个 harness，Servo 用什么技术思路降低大模型工作的偏差、错误和幻觉，以及为什么要把工作拆成不同速度的控制层级。

项目定位、适用场景、安装试用入口和基础表达边界见 [Servo 对外技术定位与适用场景](./external-positioning.md)。本文只承接技术和架构骨架。

## 需求侧问题

大模型已经能完成大量 coding 工作，但它不是稳定的软件工程组件。实际使用中，问题往往不出在“模型完全不会写”，而出在工作过程缺少控制：

- 上下文越来越长后，模型注意力变散，开始遗忘早期约束。
- 需求没有收紧时，模型会按自己的理解扩大范围。
- 单次输出可能出现错误、遗漏、幻觉或把未验证结论写成事实。
- 长任务结束后，缺少结构化证据说明“做了什么、怎么验证、下一步是什么”。
- 人想要自动化推进，但又不希望 AI 无边界地修改代码、发布版本或做高风险操作。

Servo 的核心目标不是替换程序员，也不是让模型“更聪明”。它的目标是把 AI coding 放进一个可观测、可验证、可恢复的工程控制系统里，让模型能力通过外部结构变得更可用。

## 技术侧：用系统工程约束不稳定组件

Servo 把 LLM 当成一个能力很强但不完全稳定的执行组件。系统工程处理这类组件时，通常不会假设单个组件永远正确，而是通过冗余、反馈、边界和恢复路径，让整体系统更可靠。

对应到 AI coding，Servo 采用几类约束：

| 工程手段 | 在 Servo 中的体现 | 解决的问题 |
|----------|------------------|------------|
| 明确输入边界 | Goal、Milestone、Worktrack contract | 防止模型把模糊需求直接扩写成大范围改动 |
| 状态估计 | Repo / Worktrack observe | 先看当前仓库、分支、backlog 和证据，再决定下一步 |
| 任务分解 | Milestone / Worktrack / task queue | 把长任务压成可验证的小窗口 |
| 反馈回路 | Verify / Judge / Recover | 输出后必须回到检查、裁决和恢复路径 |
| 证据记录 | gate evidence、review evidence、test evidence | 避免“模型说完成了”直接等于完成 |
| 权限边界 | handback、approval、policy gate | 高风险动作必须显式授权 |

这套设计的重点是：不要把可靠性交给一次 prompt，也不要把长任务塞进一个无限扩张的上下文。每一段工作都要有边界、产物、证据和退出条件。

## 架构侧：快慢管理 Tick

Servo 的架构核心是快慢变量分层。不同层级的状态变化速度不同，因此不能放在同一个上下文里用同一种 Review 方式处理。

| 层级 | 变量速度 | 关注对象 | 典型问题 |
|------|----------|----------|----------|
| Repo | 慢 | 长期目标、系统不变量、Milestone pipeline、治理状态 | 这个仓库接下来应该推进什么？当前目标是否还成立？ |
| Milestone | 中 | 阶段目标、完成信号、验收标准、多个 Worktrack 的组合 | 这个阶段是否完成？是否满足使用者最终验收？ |
| Worktrack | 快 | 单个受控执行单元、分支、任务队列、局部证据 | 当前小任务是否实现、验证并能合入？ |

这种分层的意义，是让不同粒度的问题在不同控制 tick 上处理：

- Repo tick 不应该陷入某个小函数怎么改。
- Worktrack tick 不应该重新定义整个项目目标。
- Milestone tick 不应该只看某个文件 diff，而应该看多个 Worktrack 汇总后是否达成阶段目标。

每层都有自己的 Observe / Decide / Init / Dispatch / Verify / Judge / Recover / Close 行为。Scope 决定当前在哪一层控制，Function 决定此刻做什么，Artifact 决定依据哪些正式对象判断。

## 为什么这样能降低偏差

### 1. 收紧上下文，避免注意力过散

长上下文会稀释注意力，也会让早期约束更容易被遗漏。Servo 用 Worktrack 把任务压缩成局部窗口：当前分支、当前 contract、当前 task queue、当前 evidence。模型不需要同时记住整个项目的所有目标，只需要在限定范围内完成一个受控切片。

### 2. 多层验收更科学

不同层级的验收对象不同：

- Worktrack 验收局部实现是否满足 contract。
- Milestone 验收多个 Worktrack 合起来是否满足阶段目标。
- Repo 刷新验收慢变量是否需要更新，比如 backlog、snapshot、下一步路线。

这样可以避免两个常见错误：一是小任务过度 Review，成本太高；二是大阶段只看局部 diff，验收太轻。

### 3. Review 成本和风险匹配

Servo 的 Review 不追求所有任务都用同一强度。小任务可以用轻量 Review 和局部检查；合并到 Milestone、涉及 release、治理、部署或高风险变更时，再使用更完整的 Review / Gate。

这带来一个更合理的成本结构：

- 低风险文档或小修补：轻量检查、快速闭环。
- 普通 Worktrack：implementation / validation / policy 三面 gate。
- Milestone 汇总：看完成信号、验收标准和跨 Worktrack 证据。
- Release / publish / deploy：需要更强的准入、真实 smoke、dogfood 或人工审批。

## Artifact 是控制系统的状态面

Servo 不是只靠对话推进。它把控制状态写成 repo-side artifacts，让下一轮模型、另一个 runtime，或者人类 reviewer 都能看到同一组事实。

典型 artifact 包括：

- Goal Charter：仓库长期目标和非目标。
- Milestone Backlog：当前 pipeline 中 planned / active / completed 的阶段。
- Worktrack Contract：当前执行单元的目标、范围、分支和验收标准。
- Plan / Task Queue：当前局部任务窗口。
- Gate Evidence：实现、验证和策略层面的证据。
- Control State：当前控制回路处于哪一层、哪一步、下一步是什么。

这些 artifact 的价值在于降低隐式上下文依赖。即使换窗口、换模型或经历 handback，控制系统仍然有可追踪的状态。

## 平台适配

[Linux Do v0.6.1 发布推广帖](./linuxdo-release-post-v061.md) 已经包含较完整的需求侧引入、控制论解释和三层控制对象描述。后续切换到知乎、小红书、Reddit 等平台时，不需要照搬 Linux Do 的语气，也不需要套一份固定的“推荐/避免表达”清单；更重要的是保留本文的技术骨架，再按平台调整叙事节奏、例子密度和语言风格。

- 需求侧：AI coding 过程失控、上下文污染、自动化与安全边界矛盾。
- 技术侧：系统工程方法、反馈回路、证据与恢复路径。
- 架构侧：Repo / Milestone / Worktrack 的快慢 tick 和分层验收。
- 平台侧：Linux Do 可以偏经验分享和开源推广；知乎可以偏技术论证；小红书可以偏短场景和痛点；Reddit 可以偏问题陈述、设计取舍和可复现实验。
