---
title: "Deploy Mapping Spec"
status: active
updated: 2026-05-08
owner: aw-kernel
last_verified: 2026-05-08
---
# Deploy Mapping Spec

> 目的：定义 destructive reinstall model 下 `canonical source -> backend payload source -> target entry -> verify` 的最小映射合同。

本页管理映射链路、payload descriptor 最小字段及命令依赖。operator 步骤、wrapper 语义、trust boundary 见相邻文档。

## 映射链路

`canonical source -> backend payload source -> payload descriptor -> target entry -> verify`；canonical source 是唯一 truth（`product/harness/skills/`），backend payload source 是分发载体（`adapters/<backend>/skills/`），payload descriptor 只描述分发所需信息，target entry 是 live install 落点且不回写 source。

聚合 backend (`--backend bundle`) 在同一命令调用中同时实例化 agents 与 claude 两组 mapping 链路。canonical source 共享（一个 canonical source 同时驱动两组 backend payload source），但 `backend payload source -> payload descriptor -> target entry -> verify` 这一段在两个 backend 上各自独立运行，互不交叉：
- agents 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/agents/skills/{skill_id}/` -> agents payload descriptor -> `<targetRepoRoot>/.agents/skills/aw-{skill_id}/` -> agents verify
- claude 端：`product/harness/skills/{skill_id}/` -> `product/harness/adapters/claude/skills/{skill_id}/` -> claude payload descriptor -> `<targetRepoRoot>/.claude/skills/{skill_id}/` -> claude verify

bundle 不创建第三条链路；它只是 dispatcher 决定"同时驱动这两条链路"的 control-plane 行为。

## 最小字段

| 字段 | 最小要求 |
| --- | --- |
| `canonical_dir` | 相对 repo root 的安全路径，唯一定位 canonical source |
| `skill_id` | 在 canonical source、payload descriptor、target entry 间保持稳定身份 |
| `target_dir` | 相对 target root 的安全路径；live bindings 内必须唯一（per-root：`agents` 根内唯一、`claude` 根内独立唯一） |
| `target_entry_name` | 唯一标识运行时入口 |
| `required_payload_files` | 显式列出严格复验所需的最小文件 |
| policy fields | 显式声明 copy/frontmatter transform/legacy cleanup 等策略 |

`canonical_dir`、`target_dir`、`target_entry_name`、`required_payload_files` 都必须是安全相对路径，不跳出各自根目录。

聚合 backend (`--backend bundle`) 不引入新的字段。每个字段的"最小要求"不变，仅 `target_dir` 唯一性以 per-root 视角解读：agents 根内的 `aw-{skill_id}` 与 claude 根内的 `{skill_id}` 因物理位于不同 target root，**不构成跨根唯一性冲突**。

## 当前稳定 target 命名

| backend | 当前稳定 `target_dir` 约定 |
| --- | --- |
| `agents` | `aw-{skill_id}` |
| `claude` | `{skill_id}` |
| `bundle` | 同时实例化两组：agents 端 = `aw-{skill_id}`（在 `<targetRepoRoot>/.agents/skills/` 下），claude 端 = `{skill_id}`（在 `<targetRepoRoot>/.claude/skills/` 下） |

`bundle` 行的 `target_dir` 不是单一字符串，而是 dispatcher 同时构造的双 binding 集合；每条 binding 仍各自满足前两行的稳定约定。`bundle` 不引入新的 target 命名规则，仅显式声明"两个 distribution 的 binding 在同一命令中同时存在"。

> 双根 path-disjoint 不变量：bundle 模式下，`<targetRepoRoot>/.agents/skills/` 与 `<targetRepoRoot>/.claude/skills/` 必须解析为物理不重叠的目录（dispatcher 在 context 构造阶段 reject `--agents-root` 与 `--claude-root` 解析后指向同一目录的组合）；详见 `distribution-entrypoint-contract.md` § "Aggregate Backend (`--backend bundle`)" § "Dual-Root Failure Short-Circuit" 第 3 条与 `payload-provenance-trust-boundary.md`。

## 命令读取面

- `check_paths_exist` 只读取当前 source 声明的目标路径，用于写入前冲突扫描
- `diagnose` 与 `verify` 读取同一映射信息，退出语义不同
- `install` 只写当前 descriptor 声明的 live payload

最小读取项：source 是否合法（无重复 `target_dir`）、target entry 与 `required_payload_files` 存在且类型正确、payload descriptor 身份字段与当前 binding 一致、live install 与当前 source 对齐。

聚合 backend (`--backend bundle`) 模式下，命令读取面是两组单 backend 读取面的并集：
- agents 端按既有单 backend 读取面执行（读 `adapters/agents/skills/` source 与 `<targetRepoRoot>/.agents/skills/` target）
- claude 端按既有单 backend 读取面执行（读 `adapters/claude/skills/` source 与 `<targetRepoRoot>/.claude/skills/` target）

不引入跨根读取（例如不存在"以 agents source 读取 claude target"的混合读取）。`check_paths_exist` 在 bundle 模式下做 union 视角的 fail-closed 短路（任一根有冲突即整体 fail-closed），但**冲突扫描自身仍是 per-root 独立**——两根的 plannedTargetPaths 集合各自独立计算，最终在 dispatcher 层做 union 报告。

## 不变量

target entry 与 runtime payload 不是 source of truth。`target_dir` 必须唯一（per-root：在每个 backend 各自的 target root 内唯一，跨根的同名 skill 通过两套独立的 `target_dir` 约定区分）。映射合同只服务 destructive reinstall，不承接 archive/release channel。backend-specific 细节在 adapter 附码说明。聚合 backend (`--backend bundle`) 不放宽 `target_dir` 唯一性条款，唯一性是 per-root 不跨根。
