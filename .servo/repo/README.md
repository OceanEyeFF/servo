# Harness Init Assets / Repo

这里承接 `set-harness-goal-skill` 自带的 `.servo/repo/` repo 级初始化模板。

当前入口：

- [discovery-input.md](./discovery-input.md)
- [snapshot-status.md](./snapshot-status.md)

`discovery-input.md` 只在 Existing Code Project Adoption 模式下生成到 `.servo/repo/discovery-input.md`，用于保存既有代码库的只读事实输入。它不是 goal truth；确认后的长期目标仍写入 `.servo/goal-charter.md`，初始化后的 repo 慢变量状态仍写入 `.servo/repo/snapshot-status.md`。
