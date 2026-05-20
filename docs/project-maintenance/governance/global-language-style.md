---
title: "全局语言风格"
status: active
updated: 2026-04-19
owner: servo-kernel
last_verified: 2026-04-19
---
# 全局语言风格

> 目的：固定跨任务的人读输出默认口径，优先服务判断、执行和收口，而不是背景铺垫。

## 一、默认原则

先给结论；前 20% 明确最终判断与可执行性；推理与背景后置且无决策价值时可省略。

## 二、默认结构

默认按下面结构组织：

```text
【TL;DR】
一句话结论 + 是否可执行

【Key Points】
- 最多 3 条关键点

【Action】
- 最多 3 条可执行动作

【Optional Reasoning】
- 可选；不影响理解与执行
```

## 三、使用约束

`TL;DR` 必须独立可判；`Key Points` 只留决策信息；`Action` 只写当前动作，无动作时写明不可执行；`Optional Reasoning` 只含推理与证据。

## 四、判断标准

读者开头即知结论与可执行性，不需先读背景。推理后置，主结论仍完整。

## 五、相关文档

- [Review / Verify 治理入口](./review-verify-handbook.md)
- [Branch / PR 治理规则](./branch-pr-governance.md)
