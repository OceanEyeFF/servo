---
title: "路径与文档治理边界"
status: active
updated: 2026-07-16
owner: servo-kernel
last_verified: 2026-07-16
---
# 路径与文档治理边界

本页记录重构期间仍有效的路径原则，不把旧 Python checker 的实现细节写成当前架构权威。

## 当前原则

- 根入口保持 `README.md`、`INDEX.md`、`AGENTS.md` 和 `CLAUDE.md`。
- `product/` 是 canonical source，`docs/` 是跨模块 truth，`toolchain/` 是工具实现。
- `.agents/`、`.claude/` 是 ignored deploy target；`.servo/` 是 ignored runtime control plane。
- `docs/harness/` 只保留 `foundations/Harness指导思想.md`。
- Skill inventory 和 operational contract 由 `product/harness/skills/README.md` 与对应 `SKILL.md` 承接。
- `docs/book.md` 只链接实际存在的文档；删除文档时必须同步最近入口和所有 active backlink。
- distributed Skill package 不得把 source-repo docs 或父目录路径当作运行时依赖。

## 重构期验证

当前 `toolchain/scripts/test/` 的旧治理脚本编码了重构前的 Harness 文档和 Worktrack artifact 拓扑，不作为本轮重构的 passing authority。当前变更使用：

1. 批准路径集合与 `git diff --name-status` containment。
2. 对被删除路径、Skill id 和 rolling artifact 名称的 active consumer scan。
3. Markdown 相对链接与 package/payload inventory 的直接检查。
4. 独立 source/content Review。

外围治理工具和最小确定性检查将在 `MS-20260716-001` 中基于稳定后的接口重建。在此之前，不得通过修改文档去假装旧 checker 已适配新架构。
