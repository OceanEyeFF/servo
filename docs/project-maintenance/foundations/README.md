---
title: "Foundations"
status: active
updated: 2026-05-17
owner: servo-kernel
last_verified: 2026-06-13
---
# Foundations

`docs/project-maintenance/foundations/` 保存仓库最上层的结构合同，不重复维护已由其他 owner 定义的内容。

## 入口

| 文档 | 管理什么 | 权威来源 |
| --- | --- | --- |
| [root-directory-layering.md](./root-directory-layering.md) | 根目录分层、例外白名单、层级混合规则 | 本文件是唯一 authority |
| [toolchain/toolchain-layering.md](../../../toolchain/toolchain-layering.md) | 工具链脚本的分层结构、评测与部署组织 | toolchain/ 下的脚本实现 |
| [AGENTS.md](../../../AGENTS.md) | agent boot 路径路由与文档治理基线 | 根目录 AGENTS.md |

## 非本目录内容

| 内容 | 权威位置 |
|------|---------|
| Harness 跨模块指导思想 | [../../harness/foundations/Harness指导思想.md](../../harness/foundations/Harness指导思想.md) |
| 治理规则与检查 | [../governance/README.md](../governance/README.md) |
| Deploy runbook | [../deploy/README.md](../../servo-installer/README.md) |
| 测试执行 | [../testing/README.md](../testing/README.md) |
| 使用帮助 | [../usage-help/README.md](../usage-help/README.md) |

## 最小治理原则

foundations 不重复维护 `AGENTS.md` 已定义的流程与路由规则；模板、runbook、分区内部语义放回对应目录。新增根目录层级或结构合同时，先更新 `root-directory-layering.md`，再同步本页入口。
