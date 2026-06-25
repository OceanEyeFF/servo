---
title: "Version Marker Contract"
status: active
updated: 2026-05-19
owner: servo-kernel
last_verified: 2026-06-13
---
# Harness Version Marker Contract

> 目的：定义 Harness distribution payload 的版本标记文件位置、格式、语义和 operator 解读规则，确保 operator 始终从 canonical source 读取版本事实，不把 deploy target 当作版本真相。

本页管理版本标记的单一真相源地位。版本标记与 `package.json`、git tag、npm dist-tag、GitHub Release 的关系见下文 §"版本事实边界"。deploy target 的角色见 [deploy-mapping-spec.md](./deploy-mapping-spec.md)。

## 版本标记定义

| 属性 | 值 |
|------|-----|
| 文件路径 | `product/harness/skills/harness-skill/VERSION` |
| 格式 | 单行纯文本，不含换行或空白 |
| 内容 | semver 兼容的版本字符串（如 `0.5.1-rc.1`） |
| 更新者 | 发布流程在 canonical source 侧更新，由 `package.json` version 同步 |

版本标记文件是 Harness distribution payload 版本的**单一真相源**。它位于 canonical harness-skill 入口旁，确保版本事实与技能源码共享同一 truth boundary。

## 语义

### 版本标记代表什么

- Harness skill payload 在 canonical source 的当前版本
- servo-installer 打包时从此标记读取版本事实以构建 payload descriptor
- 与仓库根 `package.json` 的 `version` 字段保持同步（同步由发布流程保证）

### 版本标记不代表什么

- **不是 npm package version 的替代品**：`package.json` version 仍是 npm registry 的权威版本字段
- **不是 git tag 或 release tag**：git tag 是 VCS 维度的版本事实，与版本标记互补
- deploy target 中的文件不能替代 canonical source 版本和 `verify` 命令作为版本事实。
- **不是 channel 或 dist-tag**：`latest`/`next` 等发布频道语义不由版本标记定义

## 版本事实边界

| 版本事实 | 真相源 | 与 VERSION 标记的关系 |
|---------|--------|---------------------|
| Harness payload version | `product/harness/skills/harness-skill/VERSION` | **权威源** |
| npm package version | 根 `package.json` → `version` | 应同步；`package.json` 是 npm 维度的权威源 |
| git tag | `git tag` (VCS) | 与 VERSION 互补；tag 指向 commit，VERSION 指向 payload 版本 |
| npm dist-tag (`latest`/`next`) | npm registry | 由发布流程维护；VERSION 不定义频道路由 |
| GitHub Release | GitHub Releases API | 由发布流程维护；release tag 与 VERSION 可对应但独立管理 |
| deploy target version | 无独立版本 | deploy target 不是 source of truth；其内容派生自 canonical source |

## Operator 解读规则

1. **查看当前 payload 版本**：读取 `product/harness/skills/harness-skill/VERSION`（如在 repo 内）或通过 `servo-installer diagnose --json` 查看 installed payload descriptor 中的版本字段
2. **判断安装是否过期**：比较 installed payload descriptor 版本与 canonical VERSION（如可访问）或 registry dist-tag 版本
3. **不要把 deploy target 当成真相**：`.agents/skills/` 或 `.claude/skills/` 下的文件是安装产物，其内容反映的是安装时点的 canonical source 版本
4. **不要用 VERSION 文件的存在判断安装完整性**：使用 `servo-installer verify` 进行严格复验

## 与 servo-installer 的关系

- servo-installer 在打包时读取 VERSION 文件，将其值写入 payload descriptor
- `diagnose --json` 输出中包含 payload descriptor 的版本字段
- `install` 将 VERSION 文件随 skill payload 一同部署到 target root
- servo-installer 自身的行为不由此合同改变；此合同仅定义版本标记的语义

## 不变量

- canonical source (`product/harness/skills/harness-skill/`) 是版本真相的唯一存放位置
- deploy target 不产生、不持有、不修改版本事实
- VERSION 文件格式永远是单行纯文本
- 版本标记的语义变更必须在本文档中反映

## 停止线

问题进入 release channel、publish 流程、npm dist-tag 管理或 GitHub Release 创建时，本文档只提供链接，不展开。
