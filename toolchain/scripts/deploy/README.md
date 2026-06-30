# Deploy Scripts

本目录保存部署和安装入口。

当前主线：

- `path_safety_policy.json`：deploy 入口共享的 target/source root 安全策略配置
- `package.json` + `bin/servo-installer.js`：本地 npm-style package scaffold；`servo-installer` 是唯一 package runtime bin，直接承接 help/version、`agents` package/local 的 diagnose、update dry-run、check_paths_exist、verify、install、prune --all、update --yes composition 与 selected invalid-variant failures；当前 checkout/local package 还直接承接 `claude` package/local 的 diagnose human/JSON、update dry-run human/JSON、check_paths_exist、verify、install、prune --all、update --yes，并支持 `--claude-root`；`agents` 的显式 GitHub-source update JSON/human dry-run 与 `--yes` apply（`update --backend agents --source github ...`）也由 Node-owned 路径承接；`migrate-runtime --from aw --to servo` 与 `reconcile-servo` 也由 Node-owned wrapper 承接。unsupported deploy modes fail in Node with an explicit unsupported-command error
- `product/harness/adapters/agents/skills/`：`agents` canonical-copy payload descriptor source，由 `install --backend agents` 消费
- `product/harness/adapters/claude/skills/`：`claude` compatibility payload descriptor source，当前承接受控的完整 Harness skill payload set

最小维护流：

1. 如需机器可读状态摘要，先跑 `diagnose --backend agents --json`
2. `prune --all --backend agents`
3. `check_paths_exist --backend agents`
4. `install --backend agents`
5. 如需只读复验，再跑 `diagnose --backend agents --json` 或 `verify --backend agents`

`.servo_template` legacy scaffold profile 相关说明：

`first-wave-minimal` 是 legacy profile，生成 `control-state.md`、`goal-charter.md`、`repo/analysis.md`、`repo/snapshot-status.md`、`worktrack/contract.md` 和 `worktrack/plan-task-queue.md`。`worktrack/gate-evidence.md` 可通过单独 template 生成。

生成结果会写入 provenance frontmatter 与非空 placeholder；`control-state.md` 链接字段在同一轮生成目标存在时写相对路径，否则保留 placeholder。模板结构校验不替代 `docs/harness/artifact/` 的 canonical artifact contract。

额外说明：

- `prune --all` 只删除带可识别、且属于当前 backend 的受管 `aw.marker` 目录
- `check_paths_exist` 基于当前 source 声明的 live bindings 全量列出冲突路径；命令失败时不允许有业务写入
- `install --backend agents` 只写当前 source 声明的 live payload；若存在重复 `target_dir`、planned target path 冲突或其他 source 非法情形，必须在写入前失败且不调用 Python；无关用户内容不属于 planned path conflict
- install 写入 target package 时，`payload.json` 由 installer 生成 package-local runtime descriptor（`package_dir: "."` / `package_paths`），不复制 source descriptor 原文，也不在安装态保留 `canonical_dir`、`canonical_paths` 或 `product/harness/*` source path
- `diagnose` 用于输出 backend、target root、受管安装数量、issue code 与 unrecognized / conflict 摘要；发现 issue 时仍返回 0。`agents` package/local human/JSON 支持 `--agents-root`，`claude` package/local human/JSON 支持 `--claude-root`，这些当前 checkout/local package 路径均由 Node-owned wrapper 直接承接
- `verify` 用于检查 source 合法性、target root 状态、live install 对齐，以及 conflict / unrecognized 情形。`agents` 与 `claude` package/local read-only verify 当前由 Node-owned wrapper 直接承接；TUI agents verify action 也复用对应 Node-owned路径
- 当 source payload 新增随包文件、runtime descriptor shape 变化，或 live `.agents/` / `.claude/` 尚未重装时，`verify` 报 `missing-required-payload` 或 `target-payload-drift` 是预期 target drift 信号。先确认 source payload / adapter contract tests 通过，再按 `prune --all -> check_paths_exist -> install -> verify` 刷新目标；不要从 deploy target 反向生成 source truth
- `reconcile-servo` 用于已有 `.servo/` runtime 与当前模板调和：默认 dry-run，`--json` 输出机器摘要，`--yes` apply，apply 后应再次 `--json` 确认 `changes` 为空。它不同于 legacy `.aw -> .servo` 的 `migrate-runtime`
- 根目录 `package.json` 是 self-contained `servo-installer` package envelope，本地 package scaffold 只暴露 `servo-installer` bin，但不表示 npm release channel 已发布
- 目标分发入口是 `npx servo-installer`，并应支持 CLI + TUI 双模式；当前提供 root package envelope、CLI surface 和 TUI guided flow。TUI `.servo` template reconcile action 必须先 dry-run、显式确认、apply、再二次 dry-run 验证，且只能作为同一 CLI 合同的交互式表达
- `update --backend agents --json` 与 `update --backend claude --json` 在 package/local source dry-run 场景下由 Node-owned 路径输出 plan；`update --backend agents --source github` 在显式 GitHub source archive 场景下也由 Node-owned 路径承接 JSON/human dry-run 和 `--yes` apply，并保留 `backend`、`source_kind`、`source_ref`、`source_root`、`target_root`、`operation_sequence`、`managed_installs_to_delete`、`planned_target_paths`、`issues` 与 `blocking_issues` 等字段。human-readable `update --backend agents|claude` 是 package/local 只读 dry-run。`update --backend agents|claude --yes` 在 package/local source 场景下由 Node-owned 路径执行同一 `prune --all -> check_paths_exist -> install -> verify` composition；GitHub-source apply 也保持同一 destructive reinstall composition、blocking preflight、post-apply verify 和 recovery hint 语义
- `npm --prefix toolchain/scripts/deploy run smoke --silent` 只验证本地 package scaffold 的 bin 能打开当前 help，不发布或安装 package；`servo-installer --version` 是同一 Node wrapper 上的非交互 package metadata probe
- 如需检查目标 package envelope，在仓库根目录运行 `npm pack --dry-run --json`；本地 scaffold packlist 仍在 `toolchain/scripts/deploy/` 目录内运行；根 `.tgz` smoke 应在临时 target repo 中覆盖 help/version/TUI non-interactive guard/diagnose/update dry-run/install/verify/update apply，以及 `reconcile-servo` dry-run/apply/second dry-run
- 如需检查发布前包面，在仓库根目录运行 `npm run publish:dry-run --silent`；这只验证 npmjs publish dry-run，不上传 package；root package 的 `prepublishOnly` guard 会拒绝不满足 release-channel 准入的真实 publish，包括 local version、缺少 CI/审批信号、channel 与 dist-tag 不匹配或缺少匹配 git tag
- 从根 package `.tgz` 执行非 help 命令时，不设置 `SERVO_HARNESS_REPO_ROOT` 即可从 package 内读取 source payload，并把当前工作目录作为 target repo root；`SERVO_HARNESS_REPO_ROOT` 仍保留为 source checkout override，`SERVO_HARNESS_TARGET_REPO_ROOT` 可显式覆盖 target repo root。当前 `update` 只使用该 package、checkout source payload，或显式 GitHub source archive；不做 channel 解析、自升级、验签或自动回滚；完整边界见 `docs/project-maintenance/deploy/payload-provenance-trust-boundary.md`
- 当前接口实现 `agents` 主路径，并提供受控的完整 Harness skill set `claude` compatibility backend；不要把 `claude` 写成阻塞 `agents` 主线的稳定/默认分发路径
- 不再承接 `local/global` deploy modes、`prune --outdated`、archive/history、增量修复或旧版本保活
- Claude skills 分发当前仍是慢车道兼容项，不阻塞 `servo-installer` 主线

回归测试入口：

```bash
npm --prefix toolchain/scripts/deploy test --silent
```

GitHub CI 的 `Governance Checks` workflow 也会运行同一组 deploy regression tests，避免 deploy 工具回归只停留在本地验证。

相关回归应覆盖：

- `prune --all` 只删除带 marker 的受管目录，不删除 foreign / unrecognized 目录
- `check_paths_exist` 在多个冲突路径同时存在时全量列出并非零退出
- `install --backend agents` 在干净 target root 上成功写入 live payload
- `install --backend agents` 在重复 `target_dir` 或既有冲突路径下写入前失败
- `diagnose --backend agents --json` 在发现 issue 时仍以 0 退出，并输出结构化摘要
- `verify` 的 missing / broken symlink / wrong root type 结构错误
- `verify` 的 source drift、missing payload files、target payload drift 与 conflict / unrecognized 目录
- `.servo_template` 到 `.servo/` 的 legacy scaffold profile 生成
- `.servo_template` 的最小结构校验与 overwrite guard
- `.servo_template` 的 `Engineering Node Map` / `Node Type` 字段漂移校验
