# Governance Checks

`toolchain/scripts/test/` 保存轻量治理检查入口。

当前主线：

- `folder_logic_check.py`：检查根目录分层、一级目录白名单、hidden/state/mount layer 例外白名单，以及 `docs/` / `toolchain/` 下的错位内容
- `path_governance_check.py`：检查 markdown 相对链接、关键主入口、路径/文档治理回链、`docs/project-maintenance/` 与 `docs/harness/` 主线入口完整性、正文文档 frontmatter、目录状态约束和 `.gitignore` 中的关键 hidden-layer 忽略项
- `governance_semantic_check.py`：检查关键模板是否存在、关键知识页是否回链承接模板、canonical skill 包体是否保持最小 executable shape、adapter 层是否没有重新长出错误的 wrapper 真相、foundations 权威文档是否出现影子文件、已退役的占位口径是否回流，以及 `.gitignore`、dispatch/context/review/debug/decision/closeout 合同、cache roots、manual runbook skill count 等 operator-facing 文档是否与治理脚本或 adapter source 同步
- `repo_analysis_contract_check.py`：检查 canonical Repo Analysis 模板 sources 是否保留 required sections 与 keyed fields，避免 `Repo Analysis` artifact 合同只停留在 prose 中
- `scope_gate_check.py`：按 contract 中的 `in_scope` / `out_of_scope` 规则校验本轮改动是否越界
- `servo_installer_cli/`：覆盖 `servo-installer` CLI 命令面，包含 help/version/无参、agents 与 claude 的 diagnose / update dry-run / check_paths_exist / prune / install / verify / update apply，以及 GitHub source Node-owned / unsupported 边界和 TUI 非交互保护
- `servo_installer_tui/`：通过 PTY 驱动 `servo-installer tui`，覆盖菜单 1-6、guided update cancel/apply、diagnose、verify、update dry-run、help、未知输入和退出别名
- `closeout_acceptance_gate.py`：按 closeout 顺序聚合 scope/spec/static/cache/test/smoke gates；其中 cache gate 会拒绝 `docs/`、`product/`、`toolchain/` 和 `tools/` 下的 Python / pytest 运行缓存，test gate 会运行 closeout、folder、path、semantic、agents adapter、servo-installer CLI/TUI、deploy package Node unit、Repo Analysis contract 回归测试、本地 `servo-installer` npm deploy package与根 package envelope 的 packlist dry-run、根 package publish dry-run及其 `prepublishOnly` guard、临时 `.tgz` help/version/TUI non-interactive guard/diagnose/update dry-run/install/verify/update apply tarball smoke
- `gate_status_backfill.py`：把 gate 结果回填到 `.autoworkflow/state/` 和 closeout 摘要
- `governance_assess.py`：对 `rule / folders / document / code` 四维输入做最小治理收口评估
- `repo_governance_eval.py`：对五维 repo maintainability 输入做总分、评级和 AI compatibility 评估

适用场景：

- 文档入口刚调整过
- foundations 合同刚更新过
- 需要给 harness closeout 或 repo audit 生成结构化治理评估
- 想快速确认 AI 的默认读取主线没有被新改动破坏

不要把下面这些东西放进这里：

- CI 平台配置
- 重型 lint 框架
- 与路径治理无关的大型测试逻辑
