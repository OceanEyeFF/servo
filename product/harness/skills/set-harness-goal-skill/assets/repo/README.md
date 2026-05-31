# Harness Init Assets / Repo

这里承接 `set-harness-goal-skill` 自带的 `.servo/repo/` repo 级初始化模板。

当前入口：

- [analysis.md](./analysis.md)
- [discovery-input.md](./discovery-input.md)
- [snapshot-status.md](./snapshot-status.md)
- [temporary-understanding.md](./temporary-understanding.md)

`discovery-input.md` 只在 Existing Code Project Adoption 模式下生成到 `.servo/repo/discovery-input.md`，用于保存既有代码库的只读事实输入。它不是 goal truth；确认后的长期目标仍写入 `.servo/goal-charter.md`，初始化后的 repo 慢变量状态仍写入 `.servo/repo/snapshot-status.md`。

`temporary-understanding.md` 只在弱文档 adoption / onboarding 场景下生成到 `.servo/repo/temporary-understanding.md`；使用 deploy helper 时需显式传入 `--weak-doc-onboarding`。它用于记录 lightweight / full 发现模式、token-cost tradeoff、观察事实、推断目的、运行目的、风险、未知项、确认问题和 truth boundary。它是 runtime evidence，不是 goal truth；未经 programmer confirmation 或 verified evidence 的 inferred purpose 不得写入 Goal Charter 或 docs truth layer。

`analysis.md` 是 RepoScope 的阶段性决策支撑 artifact，用于事实 / 推断 / 未知项、主要矛盾、优先级与路由投影；它不是 goal truth，也不是 worktrack queue。
