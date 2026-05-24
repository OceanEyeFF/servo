---
title: "路径与文档治理检查运行说明"
status: active
updated: 2026-05-16
owner: servo-kernel
last_verified: 2026-05-16
---
# 路径与文档治理检查运行说明

> 目的：说明如何在本仓库本地执行"路径治理与文档治理"相关的最小回归检查，包括结构检查和少量高价值语义检查。

本页属于 [Governance](./README.md) 路径簇。

## 一、适用范围

本页覆盖轻量治理检查：markdown 相对链接可达性、关键入口文件存在性、AGENTS.md 回链、主线入口完整性、`docs/book.md` spine 可达性与显式阅读顺序覆盖、superseded 文档历史引用边界、canonical skill source 与 catalog 双向 traceability、.gitignore hidden layer 忽略、frontmatter 与 status 语义、status:suspended 误用、承接关系一致性、foundations 影子文件、已退役 placeholder 回流、product/harness/ 最小 executable root 骨架、workflow-families 文档真相定位。不替代人工审阅，不检查所有 anchor 片段。根兼容入口保留 `README.md`、`INDEX.md` 与 `AGENTS.md`；`docs/book.md` 是 `docs/` 书式章节 spine、全量阅读顺序和路径维护入口，并作为受控 docs 一级入口。已退役的 `GUIDE.md` 和 `ROADMAP.md` 不作为必需入口。

## 二、脚本入口

```bash
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py
PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py
```

## 三、脚本当前会检查什么

1. `folder_logic_check.py` — 根目录 object 是否在 allowlist（`product/`、`docs/`、`toolchain/`、`.codex/`、`.agents/`、`.claude/`、`.servo/`、`.autoworkflow/`、`.spec-workflow/`、`.nav/`、`tools/`、`.pytest_cache/`、入口/基础设施文件，包括 Claude Code 适配入口 `CLAUDE.md`）；裸 `.pyc`/`.pyo` 不允许
2. `product/`、`docs/`、`toolchain/` 一级子目录合规；错放内容拦截（product 无 runbook/缓存/state，docs 无可执行/缓存，toolchain 无业务源码/mount，tools 无 Python 缓存）
3. hidden/state/mount 层 tracked 状态受控：`.agents/`、`.claude/` tracked 即失败；`.codex/` 仅 `config.toml`+`rules/repo.rules`；`tools/` 仅显式 compat shim；`.pytest_cache/` tracked 即失败
4. `.nav/` 仅含 `README.md`、`@docs`、`@skills`；`@docs` 与 `@skills` 是 symlink 且解析到合法目标
5. `path_governance_check.py` — 根入口、`docs/book.md` 与主线入口存在且 markdown 相对链接可达；所有 `docs/` 下非 `README.md` 正文必须能从 `docs/book.md` 沿相对 markdown 链接到达，新增正文需挂到 book spine 或最近章节入口；除 `docs/book.md` 自身外的所有 `docs/**/*.md` 必须在 `docs/book.md` 的显式阅读顺序中有直接链接；`docs/book.md` 反引号中的具体路径必须指向当前 checkout 中存在的路径；`docs/book.md` 或章节 `README.md` 链接 `status: superseded` 文档时必须位于 `Retained Historical References` / `Historical References` 章节；每个 `product/harness/skills/*/SKILL.md` source 目录必须在 `product/harness/skills/README.md#Docs Owner Traceability` 的第一列有 docs owner 反链，并在 `docs/harness/catalog/README.md#Canonical Source Traceability` 的第二列有 canonical source 映射；traceability 链接不得指向 `.agents/` / `.claude/` deploy targets；`AGENTS.md` 被关键入口页引用；scope gate 中不带 `/` 的允许项按精确文件路径匹配，带 `/` 的允许项才按目录前缀匹配
6. `docs/harness/README.md` 及子入口存在，继续链接 foundations/scope/artifact/Skills/workflow-families
7. `docs/` 正文保留 frontmatter；`project-maintenance/` 与 `harness/` status 匹配语义；无 `status:suspended` 误用
8. `.gitignore` 忽略 `.servo/`、`.agents/`、`.claude/`、`.autoworkflow/`、`.spec-workflow/`、`**/__pycache__/`、`.pytest_cache/`、`*.pyc`、`*.pyo`
9. `governance_semantic_check.py` — 关键承接关系存在（toolchain-layering -> scripts、docs/harness -> 子入口、product/harness -> docs/harness、artifact/worktrack -> contract/queue/gate）
10. foundations 无同名前缀 shadow 文件；关键入口无已退役 placeholder 回流；根兼容入口不引用已退役 adjacent-systems
11. `product/harness/` 及子目录保持最小 executable root 骨架
12. `docs/harness/workflow-families/` 把 `docs/` 作 ontology 上游，不从 `product/harness/` 反向定义

## 四、什么时候运行

调整主入口/foundations、新增入口页、清理 `.nav/`/hidden-layer、调整根目录分类/tracked 白名单后，或准备复用入口体系前。

## 五、Docs 路径维护规则

`docs/book.md` 是全量阅读顺序和路径维护入口，不是规则正文的替代品。对 `docs/` 下 markdown 文件执行新增、移动、重命名、删除或 owner 迁移时，必须同步维护三层关系：

1. 最近章节 `README.md`：保持局部入口、owner 和迁移说明正确。
2. `docs/book.md`：保持 Full Reading Order 中有直接有序链接；除 `docs/book.md` 自身外，当前 docs markdown 文件都必须在这里出现，反引号中的路径也必须指向当前存在的路径。
3. 旧路径引用：同步修复或替换正文、入口页和治理文档里的旧链接。

如果一个文档只是从最近章节 README 间接可达，但没有出现在 `docs/book.md` 的显式阅读顺序中，`path_governance_check.py` 必须失败。这条规则保证读者拿到 `docs/book.md` 后可以按顺序逐个点开文档，而不是靠搜索或目录遍历补全阅读路线。

`docs/book.md` 和章节入口只描述当前版本中已经存在的文档拓扑、owner 和维护规则。只为未来迁移、后续 Worktrack 或尚未落地重构切片服务的计划，不应作为 `docs/` 长期 truth surface 保留；这类后续动作应留在 Harness runtime/backlog 记录中，等实际内容存在后再同步进 book 和最近章节入口。

`status: superseded` 文档可以保留在 `docs/` 中作为历史引用，但不能作为当前 truth owner 或主线阅读步骤。`docs/book.md` 和章节 `README.md` 若需要链接它们，必须放在 `Retained Historical References` 或 `Historical References` 章节下，并在周边文字说明当前 owner 或接管路径。若 superseded 文档不再需要历史追溯，应移出 `docs/` 或删除；大批量删除仍需单独审批。

Canonical skill source traceability 使用两端索引：`docs/harness/catalog/README.md#Canonical Source Traceability` 从 catalog surface 指向 `product/harness/skills/` source root，canonical source 必须位于表格第二列；`product/harness/skills/README.md#Docs Owner Traceability` 从每个 source 目录反链到 docs/catalog owner，canonical source 必须位于表格第一列。新增、重命名或退役 skill source 时必须同步这两端索引。`.agents/` 与 `.claude/` 只能作为 deploy target / consumer，不得出现在 canonical source traceability 中。

## 六、如何理解结果

返回码 `0` 通过；非 `0` 表示违规/坏链/缺失入口/`.gitignore` 回退。失败时脚本列出具体问题。`folder_logic_check.py` 输出 issue code 便于 gate 锁定。

## 七、当前限制

不检查 markdown anchor、完整语义自洽性、`.nav/` 目标语义正确性；只做固定规则的最小语义检查。显式阅读顺序检查确认 `docs/book.md` 直接链接了每个 docs markdown 文件，但不判断人工编排顺序是否最优。
