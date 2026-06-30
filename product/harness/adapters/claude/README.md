# Claude Adapter

`product/harness/adapters/claude/` 承接 Claude backend 的 Harness skill payload descriptor source。

当前 payload model：

- payload source: `product/harness/adapters/claude/skills/<skill>/payload.json`
- canonical source: `product/harness/skills/<skill>/`
- target root: `<target_repo>/.claude/skills`
- target dir: `<skill_id>`
- legacy target dir: `aw-<skill_id>` for managed cleanup during migration
- payload policy: `canonical-copy`
- payload version: `claude-skill-payload.v1`
- side-effecting skill protection: payload descriptors may request Claude frontmatter overrides such as `disable-model-invocation: true`

当前成熟度边界：

- `claude` payload 当前覆盖 `product/harness/skills/` 下的完整 Harness skill set，不再是 startup-only 分发。
- 当前 checkout/local package 的 Node-owned `servo-installer --backend claude` 已承接 package/local diagnose、check_paths_exist、verify、update dry-run、install、prune --all 和 update --yes lifecycle。
- 该成熟度只表示 Claude compatibility lane 已可按完整 payload 处理；它不自动升级为 `agents` 主线替代、默认 backend、stable/latest release claim、TUI 一等选择或 registry public smoke 结论。
- 后续若改变 payload set、target dir policy、frontmatter policy、legacy cleanup 或 marker 语义，必须同步更新本页、deploy 合同页和对应测试。

当前稳定边界：

- canonical truth 仍在 `product/harness/skills/<skill>/`
- payload source 固定在 `product/harness/adapters/claude/skills/<skill>/payload.json`
- `required_payload_files` 必须等于 `canonical_paths` 对应文件，再加上 `payload.json` 与 runtime-generated `aw.marker`
- install 写入 `.claude/skills/<skill>/payload.json` 时会生成 package-local runtime descriptor；安装态 descriptor 只列包内 `package_dir: "."` / `package_paths`，不保留 `canonical_dir`、`canonical_paths`、`product/harness/*` source path 或 parent-directory escape
- `aw.marker` 不存在于 adapter source 中，只在 install 写入 target 时生成
- `update --backend claude --yes` 只包装 `prune --all -> check_paths_exist -> install -> verify`
- `claude_frontmatter.disable-model-invocation: true` 这类字段只影响 target 写入结果，不回写 canonical source
- repo-local `.claude/skills/` 是 deploy target，不是 source truth

这里不承接 repo-local `.claude/skills/` 安装结果。
