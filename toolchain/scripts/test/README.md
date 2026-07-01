# Governance Checks（治理检查）

`toolchain/scripts/test/` 保存轻量治理检查入口。

## Checker 入口清单（Checker Entry List）

| checker | 中文说明 | 英文关键词 |
|---------|---------|-----------|
| `folder_logic_check.py` | 根目录分层、白名单、hidden/mount layer 检查 | folder, layering, hidden, state, mount |
| `path_governance_check.py` | markdown 链接、主入口完整性、frontmatter 检查 | path, link, frontmatter, entry |
| `governance_semantic_check.py` | 模板存在性、知识页回链、skill 自洽性、orphan 检查 | template, handoff, authority, skill, orphan |
| `scope_gate_check.py` | 改动范围是否越界 | scope, in_scope, out_of_scope |
| `closeout_acceptance_gate.py` | 收尾门禁，依次执行 scope / spec / static / cache / test / smoke 六道检查点。支持 `--profile lightweight`（仅治理检查）和 `--profile full`（全部六道，默认） | closeout, gate, cache, smoke, profile |
| `complexity_signal_scanner.py` | repo 复杂度信号扫描（只读） | complexity, scanner, compose, service |
| `repo_analysis_contract_check.py` | Repo Analysis 模板 contract 检查 | analysis, contract, template |
| `runtime_artifact_consistency_simulation.py` | milestone/backlog/control-state 一致性模拟 | runtime, artifact, consistency, simulation |
| `governance_assess.py` | 四维治理收口评估（rule/folders/document/code） | governance, assess, rule, document |
| `repo_governance_eval.py` | 五维 repo maintainability 评估 | repo, maintainability, eval, score |
| `gate_status_backfill.py` | gate 结果回填到 closeout state | gate, backfill, closeout |
| `recommend_verification.py` | 推荐验证动作 | recommend, verification |
| `check_cross_layer_sync.py` | 跨层同步检查 | cross-layer, sync |
| `harness_scope_gate.py` | Harness scope 边界校验 | harness, scope, gate |
| `cache_scan_policy.py` | 缓存扫描策略 | cache, scan, policy |
| `pr_branch_guard.py` | 保护 `master` PR source，只允许同仓库 `develop -> master` | pull request, branch, guard, master, develop |
| `test_servo_cleanup_control_state_compact.py` | cleanup skill control-state 压缩 helper、模板字段和 backup 排除回归 | cleanup, control-state, compact, template |

## 英文关键词中英对照表（English-Chinese Keyword Mapping）

Checher 输出中使用的英文关键词及其对应的中文语义：

| 英文关键词 | 中文语义 |
|-----------|---------|
| passed / checks passed | 检查通过 |
| failed / FAIL | 检查失败 |
| error | 错误 |
| warning / warn | 警告 |
| info | 信息 |
| checked | 已检查 |
| missing | 缺失 |
| orphans / orphan | 孤立文件（无回链引用） |
| stale | 过期 |
| blocked | 阻断 |
| found | 发现 |
| verified | 已验证 |
| governance | 治理 |
| semantic | 语义 |
| artifacts / artifact | 产物 / 合同 |
| consistency | 一致性 |
| simulation | 模拟 |
| complexity | 复杂度 |
| scanner | 扫描器 |
| closeout | 收尾 |
| acceptance | 验收 |
| gate | 关卡 |

## 当前主线

### 门禁方案

`closeout_acceptance_gate.py` 支持两种 profile：

| 方案 | 执行的检查点 | 适用场景 | 耗时 |
|---------|-------|------|------|
| `lightweight`（轻量） | scope_gate, spec_gate, static_gate, cache_gate | 纯文档修改、配置调整、小范围分析任务 | 快（< 30s） |
| `full`（完整，默认） | scope_gate, spec_gate, static_gate, cache_gate, test_gate, smoke_gate | 默认行为；发布版本、功能开发、代码修改任务 | 慢（数分钟） |

轻量方案会跳过 test_gate（含 pytest、npm test 和 tarball 烟测）以及 smoke_gate。涉及发布或代码修改的任务必须用完整方案。

### 原有内容

- `folder_logic_check.py`：检查根目录分层、一级目录白名单、hidden/state/mount layer 例外白名单，以及 `docs/` / `toolchain/` 下的错位内容
- `path_governance_check.py`：检查 markdown 相对链接、关键主入口、路径/文档治理回链、`docs/project-maintenance/` 与 `docs/harness/` 主线入口完整性、正文文档 frontmatter、目录状态约束和 `.gitignore` 中的关键 hidden-layer 忽略项
- `governance_semantic_check.py`：检查关键模板是否存在、关键知识页是否回链承接模板、canonical skill 包体是否保持最小 executable shape、distributed skill package 是否自洽且 adapter payload 完整覆盖包内 runtime 文件、adapter 层是否没有重新长出错误的 wrapper 真相、foundations 权威文档是否出现影子文件、已退役的占位口径是否回流，`.aw` residue 是否能按分类合同归入 marker identity / legacy target dir / migration 兼容范围，以及 `.gitignore`、dispatch/context/review/debug/decision/closeout 合同、cache roots、manual runbook skill count 等 operator-facing 文档是否与治理脚本或 adapter source 同步
- `runtime_artifact_consistency_simulation.py`：在临时目录模拟 milestone/backlog/control-state 的一致与不一致状态，展示 `governance_semantic_check.py` 中 runtime artifact consistency 逻辑会放行或报出的具体 failure 文本
- `repo_analysis_contract_check.py`：检查 canonical Repo Analysis 模板 sources 是否保留 required sections 与 keyed fields，避免 `Repo Analysis` artifact 合同只停留在 prose 中
- `complexity_signal_scanner.py`：只读扫描 repo 复杂度信号，输出 JSON evidence、thresholds 和 `complexity_signals`，覆盖 compose / service / package / CI / deploy / migration / debt / code signals，供 `complex_project_entry_gate` / LLM / Gate 消费；scanner output is evidence, not verdict，不访问网络、不启动服务、不执行 docker/database/deploy、不做破坏性写入；它跳过 secret-like 路径且不输出文件内容，但会对非 secret-like 文本/代码文件做 bounded read 以生成聚合信号
- `test_repo_init_goal_e2e_fixture.py`：用临时 fixture repo 验证 existing-code adoption 的低风险默认路径不会固定进入 heavy / full gate，同时验证 weak-doc onboarding 与 explicit complex gate 会生成对应 runtime evidence
- `scope_gate_check.py`：按 contract 中的 `in_scope` / `out_of_scope` 规则校验本轮改动是否越界
- `servo_installer_cli/`：覆盖 `servo-installer` CLI 命令面，包含 help/version/无参、agents 与 claude 的 diagnose / update dry-run / check_paths_exist / prune / install / verify / update apply，以及 GitHub source Node-owned / unsupported 边界和 TUI 非交互保护
- `servo_installer_tui/`：通过 PTY 驱动 `servo-installer tui`，覆盖菜单 1-6、guided update cancel/apply、diagnose、verify、update dry-run、help、未知输入和退出别名
- `test_servo_cleanup_control_state_compact.py`：覆盖 `milestone-cleanup-skill` 的 control-state compact dry-run/apply、split control-state profile 校验、generated history ref、`.servo/backup(s)` 排除，以及 `product/.servo_template/control-state.md` / `repo-init-goal-skill/assets/control-state.md` 对 compact preserved-field contract 的模板兼容性
- `closeout_acceptance_gate.py`：按 closeout 顺序聚合 scope/spec/static/cache/test/smoke gates；其中 cache gate 会拒绝 `docs/`、`product/`、`toolchain/` 和 `tools/` 下的 Python / pytest 运行缓存，test gate 会运行 closeout、folder、path、semantic、complexity signal scanner、repo-init-goal e2e fixture、agents adapter、servo-installer CLI/TUI、deploy package Node unit、Repo Analysis contract 回归测试、本地 `servo-installer` npm deploy package与根 package envelope 的 packlist dry-run、根 package publish dry-run及其 `prepublishOnly` guard、临时 `.tgz` help/version/TUI non-interactive guard/diagnose/update dry-run/install/verify/update apply tarball smoke
- `gate_status_backfill.py`：默认把 gate 结果回填到 `/tmp/servo-closeout/<repo>/state/` 和 closeout 摘要；可用 `--state-file` / `--closeout-root` 显式覆盖
- `governance_assess.py`：对 `rule / folders / document / code` 四维输入做最小治理收口评估
- `repo_governance_eval.py`：对五维 repo maintainability 输入做总分、评级和 AI compatibility 评估

适用场景：

- 文档入口刚调整过
- foundations 合同刚更新过
- 需要给 harness closeout 或 repo audit 生成结构化治理评估
- 想快速确认 AI 的默认读取主线没有被新改动破坏

`.servo` footprint / control-state compact 相关变更的最小复验入口：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_servo_cleanup_control_state_compact.py toolchain/scripts/test/test_agents_adapter_contract.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_governance_semantic_check.py toolchain/scripts/test/test_check_cross_layer_sync.py -q
```

全量 `governance_semantic_check.py` 仍是长期治理入口；若被受保护 community copy hash mismatch 阻断，应在 gate/closeout 证据中记录具体文件和 expected/actual hash，而不是修改无关受保护草稿。

不要把下面这些东西放进这里：

- CI 平台配置
- 重型 lint 框架
- 与路径治理无关的大型测试逻辑
