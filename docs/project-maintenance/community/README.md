---
title: "Community 社区推广材料"
status: active
updated: 2026-06-19
owner: servo-kernel
last_verified: 2026-06-19
---
# Community

> 外部社区推广与发布公告材料的存放目录。本文只做入口导航。

## 目录定位

`community/` 承接 Servo 对外技术叙事、适用场景说明和社区平台文案样例。它的读者是外部社区读者、潜在试用者和维护对外文案的 contributor。

本目录不承接 release truth、publish flow、Harness doctrine 或 artifact contract。版本、安装、发布和 runtime 事实变化时，先回到对应 owner 文档校准，再同步到本目录的对外表达。

## 推荐阅读顺序

| 文件 | 说明 |
|------|------|
| [external-positioning.md](./external-positioning.md) | 先读：Servo 对外技术定位、适用场景、安装试用入口和基础表达边界 |
| [external-technical-architecture.md](./external-technical-architecture.md) | 再读：系统工程方法、快慢 tick 架构、分层验收和平台适配骨架 |
| [对外发布整理/linuxdo-release-post-v061_context-version.md](./对外发布整理/linuxdo-release-post-v061_context-version.md) | 管理上下文：Linux Do v0.6.1 发布帖的存放安排、hash guard、派生规则和授权记录 |
| [对外发布整理/linuxdo-release-post-v061.md](./对外发布整理/linuxdo-release-post-v061.md) | 样例：Linux Do v0.6.1 发布版仓内正文副本，受 hash guard 保护 |

## 文件角色

- `external-positioning.md` 是对外定位入口，回答 Servo 是什么、解决什么问题、适合谁用、不适合谁用，以及试用时链接到哪里。
- `external-technical-architecture.md` 是技术和架构骨架，回答为什么用系统工程约束 LLM、为什么拆 Repo / Milestone / Worktrack、以及不同平台如何改写叙事节奏。
- `对外发布整理/linuxdo-release-post-v061_context-version.md` 是 Linux Do 发布帖的仓内管理上下文，承接元数据、事实校准来源、派生规则、正文 hash guard 和修改授权记录。
- `对外发布整理/linuxdo-release-post-v061.md` 是已发布平台文案的仓内正文副本。它保留 Linux Do 平台语气，不作为全平台模板，也不反向定义 release 或 Harness truth；没有明确授权不得修改正文。

## 平台派生路径

后续写知乎、小红书、Reddit 或其他平台版本时，按这个顺序取材：

1. 先用 `external-technical-architecture.md` 固定需求侧、技术侧和架构侧骨架。
2. 再用 `external-positioning.md` 校准适用场景、安装入口和基础边界。
3. 最后参考 Linux Do 样例的语气和案例，但按目标平台重写标题、节奏、例子密度和互动方式。

平台正文草案可以新增到本目录；新增前先在目标文档 frontmatter 中明确平台、状态、owner、事实校准来源和是否已经发布。已发布平台正文如果需要保持可复制原文，可以把仓内管理信息放到同名 sidecar 管理文档，并用 hash guard 保护正文。不要把某个平台的正文当成全平台模板。具体取材边界见 [external-technical-architecture.md](./external-technical-architecture.md) 和 [对外发布整理/linuxdo-release-post-v061_context-version.md](./对外发布整理/linuxdo-release-post-v061_context-version.md)。

## 边界

- 本目录只承载外部社区推广文案、对外技术叙事和发布公告草案
- 不承载 release channel、publish flow 或 pre-publish governance（这些归 `../governance/servo-installer/`）
- 不承载 Harness doctrine、artifact contract 或 workflow policy（这些归 `../../harness/`）
- 帖子正文以社区实际发布版本为准；仓内副本作为维护参考
- 平台派生文案应复用技术/架构骨架，再按平台重写表达；不要把某个平台的正文当成全平台模板
