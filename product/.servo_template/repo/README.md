# AW Template / Repo

`product/.servo_template/repo/` 承接 `.servo/repo/` 下的 repo 级管理文档模板。

当前入口：

- [discovery-input.md](./discovery-input.md)
- [temporary-understanding.md](./temporary-understanding.md)
- [complex-project-entry-gate.md](./complex-project-entry-gate.md)
- [analysis.md](./analysis.md)
- [snapshot-status.md](./snapshot-status.md)

`discovery-input.md` 只在 Existing Code Project Adoption 模式下生成到 `.servo/repo/discovery-input.md`，用于保存既有代码库的只读事实输入。它不是 goal truth；确认后的长期目标仍写入 `.servo/goal-charter.md`。

`temporary-understanding.md` 与 `complex-project-entry-gate.md` 只在弱文档或复杂项目入口命中时生成；它们记录临时理解、scanner evidence 和 Milestone-side blocking gate，不授予实现型 Worktrack 派生权限。
