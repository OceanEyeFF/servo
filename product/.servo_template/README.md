# AW Template

`product/.aw_template/` 是 repo-local execution template layer（本地执行模板层）。

这里存放的是 `.aw/` 运行目录的模板来源，用来在 deploy 后或初始化时生成 `.aw/` 目录结构，以及少量直接属于 Harness 运行管理面的文档；它不是 canonical truth（规范真相），也不是新的源码根。具体边界见 [Deploy Runbooks / 模板消费](../../docs/project-maintenance/deploy/README.md#模板消费)。

当前入口：

- [control-state.md](./control-state.md)
- [goal-charter.md](./goal-charter.md)
- [repo/README.md](./repo/README.md)
- [worktrack/README.md](./worktrack/README.md)
- [template/README.md](./template/README.md)

规则：

- 这里优先承接 `.aw/` 目录结构，以及直接属于 `.aw/` 运行管理面的文档模板
- 当前建议通过 `toolchain/scripts/deploy/aw_scaffold.py` 生成 `.aw/` 样例，而不是手工复制这些文件
- 明显属于某个 skill 产物的模板，应优先归到 owning skill，而不是长期留在这里
- goal 修正文档不进入 `.aw/` 路径，只作为 Codex 对话回答流模板存在
- 这里可以暂时保留待迁移模板，但当前所在位置不代表最终 owner
- 不要把 doctrine、运行协议或 backend wrapper 写到这里
- 不要把模板层误当成 deploy source 或 docs truth
- 真正的定义以上游 `docs/harness/` 为准
