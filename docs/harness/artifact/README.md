---
title: "Harness Artifact"
status: active
updated: 2026-06-13
owner: servo-kernel
last_verified: 2026-06-13
---
# Harness Artifact

`docs/harness/artifact/` 固定 Harness 依赖的正式对象，并按控制层次收成 3 个子域。

当前入口：

- [repo/README.md](./repo/README.md)：`RepoScope` 的长期基线对象
- [worktrack/README.md](./worktrack/README.md)：`WorktrackScope` 的局部转移对象，包含 contract、queue、dispatch、gate 与 debug evidence
- [control/README.md](./control/README.md)：Harness supervisor 自身依赖的控制对象
- [standard-fields.md](./standard-fields.md)：所有 Skill 结构化输出的标准字段词汇表
