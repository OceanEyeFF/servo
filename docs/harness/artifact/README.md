---
title: "Harness Artifact"
status: active
updated: 2026-06-30
owner: servo-kernel
last_verified: 2026-06-30
---
# Harness Artifact

`docs/harness/artifact/` 固定 Harness 依赖的正式对象，并按控制层次收成 3 个子域。

当前入口：

- [repo/README.md](./repo/README.md)：`RepoScope` 的长期基线对象
- `worktrack/`：当前 legacy consumer 仍使用的具体 contract、queue、dispatch、gate、debug 与 closeout evidence；按需直接进入 [contract.md](./worktrack/contract.md)、[plan-task-queue.md](./worktrack/plan-task-queue.md) 或 [gate-evidence.md](./worktrack/gate-evidence.md)
- [control/README.md](./control/README.md)：Harness supervisor 自身依赖的控制对象
- [runtime-artifact-lifecycle.md](./runtime-artifact-lifecycle.md)：`.servo/` runtime artifact 的保留、归档、晋升、维护周期与 report-first cleanup 合同
- [standard-fields.md](./standard-fields.md)：所有 Skill 结构化输出的标准字段词汇表
