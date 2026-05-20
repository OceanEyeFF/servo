# Product

`product/` 是当前仓库第一块正式内容区，也是业务代码唯一源码根；这里承接 `Harness` 平台搭建与分发相关的业务源码。

当前主线包括：

- [harness/README.md](./harness/README.md)：`Harness` 的最小可执行源码根，承接后续 `operator -> skill -> subagent` 实现层

受控辅助层：

- [.aw_template/README.md](./.servo_template/README.md)：repo-local execution template layer，承接 `.aw/` 运行目录的 scaffold 模板，不承接 canonical truth

`docs/harness/` 继续承接 Harness doctrine 与运行协议真相层。
`product/harness/` 只承接 Harness executable source。
`memory-side`、`task-interface` 与 `docs/harness/adjacent-systems/` 已退役，不再保留 repo 内独立源码根或合同层。

规则：

- 业务源码只改这里，不直接改 `.claude/` 或 `.agents/`
- `.claude/` 与 `.agents/` 只作为 repo-local deploy target
- package/local operator 部署主路径走 `servo-installer`（Node-only distribution）
- 新的 Harness ontology 仍落在 `docs/harness/`
- 新的 Harness executable source 应进入 `product/harness/`
- `.aw_template/` 只承接 `.aw/` scaffold templates，不是第四个源码根，也不是 artifact 模板的长期 owner
