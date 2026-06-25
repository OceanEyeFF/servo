---
title: "根目录分层"
status: active
updated: 2026-06-15
owner: servo-kernel
last_verified: 2026-06-13
---
# 根目录分层

> 目的：固定根目录分层与例外白名单，防止业务源码、文档真相、工具脚本与运行状态混杂。

## 一、正式内容区

根目录三块正式内容区：`product/`（业务代码）、`docs/`（文档真相）、`toolchain/`（脚本/评测/测试/打包/部署）。

## 二、根目录层级模型

| 层级 | 根目录对象 | 职责 | 不应承载 |
|---|---|---|---|
| Entry Layer | `README.md` `INDEX.md` `AGENTS.md` `CLAUDE.md` | 导航与入口；`CLAUDE.md` 是 Claude Code 专用适配入口，通用 agent-facing 规则仍以 `AGENTS.md` 为准 | 长期规则正文、repo-local 细节 |
| Product Layer | `product/` | 业务源码 | 真相正文、运行状态 |
| Truth Layer | `docs/` | 知识与治理文档 | deploy 结果、mount/state |
| Toolchain Layer | `toolchain/` | 脚本与评测工具 | 业务源码真相 |
| Distribution Manifest Layer | `package.json` | npm/npx 分发包络元数据 | 业务源码真相、运行状态 |
| Repo-local Install / Mount Layer | `.claude/` `.agents/` | repo-local 安装载荷、挂载与 deploy target | 主线真相、业务源码 |
| Repo-local State Layer | `.servo/` `.autoworkflow/` `.spec-workflow/` | 运行状态、Harness 控制面运行产物；`.autoworkflow/` 与 `.spec-workflow/` 仅保留 legacy / compatibility state 语义 | 主线入口、业务源码、长期真相 |
| Repo-local Test Execution State Layer | `.test/` | 本地 dogfood / freeze specimen / testcase execution state；用于 ignored 的测试标本、规则草案、测试用例草案和派生执行工作区 | 主线入口、业务源码、长期真相、canonical Harness runtime |
| Repo-local Execution Config Layer | `.codex/` | repo-local 执行配置 | 长期真相正文、运行产物 |
| Compatibility Navigation Layer | `.nav/` | 兼容导航 | 结构定义与规则正文 |
| Compatibility Shim Layer | `tools/` | 兼容入口 shim | canonical 逻辑实现 |
| Local Ephemeral Cache Layer | `.pytest_cache/` | 本地测试缓存 | tracked 主线内容 |
| Repo Infra Layer | `.github/` `.git/` `.gitignore` `.gitattributes` `.claudeignore` `LICENSE` `CONTRIBUTING.md` | 仓库基础设施 | 业务规则正文 |

## 三、受控例外与白名单

### 0. Repo-local deploy targets

`.agents/skills/`、`.claude/skills/` 只承接 repo-local deploy 结果与 operator runtime 挂载。它们必须 ignored，不得入库；canonical truth 与业务源码的正式存放位置在 `product/`、`toolchain/` 中。Fresh checkout 不携带其镜像；需要分发或回归验证的 skill 内容从 `product/`、`toolchain/` 或正式文档入口承接。

### 1. `tools/`

Compatibility shim，非 `toolchain/` 的第二源码层。只允许：`tools/closeout_acceptance_gate.py`、`tools/gate_status_backfill.py`、`tools/scope_gate_check.py`；真逻辑在 `toolchain/scripts/test/`。

### 2. `.codex/`

Repo-local execution config。允许 tracked：`.codex/config.toml`、`.codex/rules/repo.rules`。

### 3. `.nav/`

只允许 `README.md`、`@docs`、`@skills`；`@docs` 与 `@skills` 是 symlink，分别解析到 `docs/` 和 `product/harness/skills/`。

### 4. `.pytest_cache/`

可存在于根目录，不得有 tracked 内容。

### 5. `.servo/`

Repo-local Harness runtime control-plane state，可被治理检查识别为合法根目录对象，但必须保持 ignored。运行合同、队列和 evidence 仅用于控制回路，不替代 `docs/`、`product/`、`toolchain/` 中的正式真相与源码。

### 6. `package.json`

只承接 `servo-installer` 的 npm/npx 分发包络元数据，可从根目录打包 `product/` 中的 canonical Harness payload 和 `toolchain/scripts/deploy/` 中的 wrapper 工具，不得把业务源码真相迁出 `product/`。发布动作由 deploy/release 合同控制。

### 7. `.test/`

Repo-local dogfood test execution state。允许作为 ignored 根目录对象存在，用于本地 freeze repo specimen、规则草案、测试用例草案和后续派生执行工作区；不得入库，不得承接长期真相、canonical source、发布产物或远程副作用凭据。需要长期化的规则、流程或结论必须回写到 `docs/project-maintenance/`、`docs/harness/`、`product/` 或 `toolchain/` 的正式承接层。

## 四、新增根目录对象规则

新增前回答：是业务代码、仓库真相文档、辅助工具、本地挂载点/运行状态、还是兼容导航/基础设施？只有稳定落在某一层才应放到根目录。

## 五、文档域补充

当前 `docs/` 一级文档域：`book.md`、`project-maintenance/`、`harness/`。`book.md` 是 docs 书式章节 spine，只承接当前阅读顺序、章节边界和新增文档放置判断；长期规则正文仍进入最近的 `project-maintenance/` 或 `harness/` 承接文档。`product/` 一级源码根：`harness/`；`product/` 下允许 `.servo_template/`（repo-local execution template layer，非 artifact 模板长期 owner）。

## 六、相关文档

- [AGENTS.md](../../../AGENTS.md)
- [Toolchain 分层](../../../toolchain/toolchain-layering.md)
