---
title: "npx Command Test Execution"
status: active
updated: 2026-06-17
owner: servo-kernel
last_verified: 2026-06-17
---
# npx Command Test Execution

> Purpose: verify `servo-installer` npx/package behavior across isolated temporary targets (registry package, RC selector, local `.tgz` smoke). Does not authorize publish, stable release, repo mutation, PRs, or issue creation.

Release channel -> Channel Governance; publish readiness -> Pre-Publish Governance; deploy semantics -> Entrypoint Contract.

## Control Signal

- smoke_status: operator-runnable
- canonical_runner: `toolchain/scripts/test/servo_installer_registry_npx_smoke.js`
- local_tgz_runner: `toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh`
- supported_operator_shells: Windows PowerShell, Linux bash, macOS bash
- default_package_selector: `servo-installer`; rc_pin_selector: `servo-installer@next`
- default_target_count: 3
- feedback_log_artifact: `servo-installer-npx-run.log`
- remote_mutation_allowed: false; real_npm_publish_allowed: false
- last_registry_smoke: 2026-06-15 `servo-installer@next` (`0.6.1-rc.4`, `next`) passed with `--skip-remote`; `latest` remained `0.5.8`

## Boundary

Registry smoke uses published npm; `.tgz` smoke packs current checkout and exercises from temp targets. Neither publishes.

允许：从临时 target 运行 `npx`、pin RC selector、run `.tgz` 命令、clone approved 公开 target、仅临时目录内写 `.agents/skills/`、保留临时证据、附脱敏 log。

不允许：push、open issue/PR、mutate 非临时 checkout、将 `latest` 视为 stable release 批准、存私有标识/token/完整 log。

## Cross-Platform Runner

Node-based so same smoke logic runs under Windows PowerShell, Linux bash, and macOS bash:

```bash
# Linux/macOS bash
node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --skip-remote
node toolchain/scripts/test/servo_installer_registry_npx_smoke.js

# bash compatibility wrapper
toolchain/scripts/test/servo_installer_registry_npx_smoke.sh --skip-remote

# explicit output directory
node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --output-dir /tmp/servo-installer-registry-npx-smoke
```

```powershell
# Windows PowerShell
node .\toolchain\scripts\test\servo_installer_registry_npx_smoke.js --skip-remote
node .\toolchain\scripts\test\servo_installer_registry_npx_smoke.js --output-dir "$env:TEMP\servo-installer-registry-npx-smoke"
```

RC channel pin:

```bash
node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --package servo-installer@next --skip-remote
```

2026-06-15 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.1-rc.4` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-MVeICq/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.1-rc.4`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed by the smoke.

2026-06-14 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.1-rc.3` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-gdICWX/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.1-rc.3`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed by the smoke.

2026-06-07 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.1-rc.2` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-TB9nxQ/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.1-rc.2`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed by the smoke.

2026-06-05 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.1-rc.1` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-D8xdcW/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.1-rc.1`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed.

2026-06-05 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.1-rc.0` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-2LiL4S/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.1-rc.0`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed.

2026-06-03 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.0-rc.1` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-61LzvK/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.0-rc.1`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed.

2026-06-01 post-publish verification for `servo-installer@next` passed in `--skip-remote` mode after `0.6.0-rc.0` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-OtLlci/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `next -> 0.6.0-rc.0`, confirmed `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed.

2026-05-27 post-publish verification for `servo-installer@latest` passed in `--skip-remote` mode after `0.5.8` publication. Evidence was kept in `/tmp/servo-installer-registry-npx-smoke-knoopH/report.md` during release closeout, and only the selector/version outcome is retained here as long-term fact. The smoke used `latest -> 0.5.8`, temporary targets passed, and no remote mutation was performed.

## Local Package Smoke

用于 candidate 未发布时或发布前验证：

```bash
toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh
toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh --skip-remote
```

Local `.tgz` smoke 经 `npm_pack_tarball.sh` 打包，pins npm cache/tmp/HOME 到证据目录，创建空 git repo + clone approved targets（除非 `--skip-remote`），在每 target 跑 help/version/TUI guard/diagnose/update/install/verify/update apply/final diagnose，验证 paths 在 workdir 内、source root 不解析到 source checkout 或 target repo。

## Pre-Publish Local Package Smoke

作为 [Pre-Publish Governance](../governance/servo-installer/servo-installer-pre-publish-governance.md) 证据。approval 前最少跑 `--skip-remote`，全量在有网络时跑；保留全命令证据；确认 source root 来自 package payload、paths 在 workdir 内；涉及 Claude 或 GitHub-source lane 时补充对应证据。

## Two-Target Tarball Smoke

```bash
tmpdir="$(mktemp -d)"
npm pack --json --pack-destination "$tmpdir" > "$tmpdir/pack.json"
package_file="$(
  node -e "const fs = require('node:fs'); const payload = JSON.parse(fs.readFileSync(process.argv[1], 'utf8')); console.log(payload[0].filename);" "$tmpdir/pack.json"
)"
package_path="$tmpdir/$package_file"

for target_name in target-alpha target-beta; do
  target_repo="$tmpdir/$target_name"
  mkdir -p "$target_repo"
  (
    cd "$target_repo"
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer --help
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer --version
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer diagnose --backend agents --json
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer update --backend agents --json
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer install --backend agents
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer verify --backend agents
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer update --backend agents --yes
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer install --backend claude
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer verify --backend claude
    SERVO_HARNESS_REPO_ROOT="" SERVO_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer update --backend claude --yes
  )
done
```

Claude 命令在临时 target repo 中通过 Node 兼容层执行 package payload。`servo-installer` 不包含 Python fallback；Python deploy scripts 仅作 repo-local reference/parity/governance。

## What The Registry Runner Does

Record Node/npm 版本、git branch/ref、dist-tags；创建空 git repo + existing-work fixture（`README.md`/`package.json`/`src/index.js`）；clone approved targets（除非 `--skip-remote`）并禁用 push URL；通过 npx 跑全命令集；pin npm cache/tmp/HOME；验证 target paths 在 workdir 内、source root 不在 source checkout 或 target repo、`diagnose` 返回 `missing-target-root` 且 `update --json` 视为 non-blocking；输出 `summary.tsv`/`report.md`/每 target 的 `servo-installer-npx-run.log`。

## Feedback Log

每 target 证据目录含 `evidence/<alias>/servo-installer-npx-run.log`，含脱敏 alias、package selector、Node/npm 版本、dist-tags、每命令 stdout/stderr/exit status。附加到 GitHub 前移除私有路径/名称/token/credential。

## Pass Criteria

- local-only mode 通过空 target + existing-work target；default mode 再加 approved target clones
- install 前 `diagnose` 报 `missing-target-root`，`update --json` 视为 non-blocking
- existing-work fixture 在 install/update 后不变
- 最终 diagnose：managed installs = binding_count，0 conflicts + 0 unrecognized
- dry-run planned paths 在各自 workdir 内
- source root 不在 AW source checkout、不在 target repo、不等同 target root
- npm state pinned 在 smoke evidence 目录下
- 无 push/PR/issue/remote mutation
- 每 target 有可脱敏反馈的 `servo-installer-npx-run.log`
- 长期回写只复制脱敏摘要，不存私有路径/token/credential

## `.servo` Reconcile 收敛验证

`.servo` reconcile 的完整收敛周期是 release gate 的核心证据之一。单次 dry-run 通过不代表幂等性。

### 收敛命令序列

```bash
# 在 disposable workspace 中执行：

# 1. 备份当前 .servo
cp -r .servo .servo.backup

# 2. 首次 dry-run（发现变更）
npx --yes --package servo-installer@<channel> -- servo-installer reconcile-servo --json

# 3. 应用变更
npx --yes --package servo-installer@<channel> -- servo-installer reconcile-servo --yes

# 4. 第二次 dry-run（验证收敛）
npx --yes --package servo-installer@<channel> -- servo-installer reconcile-servo --json
# 期望输出: {"changes": [], "errors": [], "filesProcessed": N}
```

### 收敛判定标准

- `second_dry_run_change_count == 0`：apply 后第二次 dry-run 无变更
- `blank_placeholder_ok == true`：无 blank value 的 placeholder 追加行为（如空 Task List append_field）
- `safe_diff_passed == true`：diff 范围限于 `.servo/` 目录
- `forbidden_surfaces_unchanged == true`：非 `.servo` 文件未被修改
- `freeze_manifest_digest_unchanged == true`：freeze specimen 在 reconcile 前后不变

### 非收敛示例（rc.4 已知问题）

`servo-installer@next`（`0.6.1-rc.4`）在 registry-only 模式下不收敛：
- 首次 dry-run：84 changes，含 60 个 blank value field、27 个 blank Task List append_field
- apply 后第二次 dry-run：7 changes（仍有 blank Task List append_field）
- 这表明 rc.4 的 reconcile helper/template 在已发布 tarball 中存在非幂等 bug
- post-rc4 修复（commit `893f8c6`、`ddc7467`）已在 local source HEAD（`122f6be`）修复，但不在已发布的 rc.4 包内

## Registry-Only 与 Local-Source-Root 的区分

`servo-installer` 在运行 reconcile 时有两种 source-root 解析模式，它们证明不同的事情：

| 维度 | Registry-Only | Local-Source-Root |
|------|-------------|-------------------|
| **环境设置** | 不设 `SERVO_HARNESS_REPO_ROOT` | `SERVO_HARNESS_REPO_ROOT=<source-checkout-path>` |
| **helper/template 来源** | npm tarball 内的 `deploy_servo.js` 和 template specs | source checkout 内的最新文件 |
| **证明什么** | 已发布 npm 包在外部 repo 上的真实行为 | source checkout 内最新代码可以收敛 |
| **不能证明什么** | N/A — 最接近 operator 真实使用路径 | 不能证明 npm tarball 内的 helper/template 版本相同 |
| **发布 gate 角色** | **必须项**：证明已发布包面质量 | **补充项**：说明已知 bug 在 source HEAD 是否已修复 |

**关键规则**：
- 不要用 local-source-root pass 声称 "registry package surface 无问题"
- 如果 registry-only lane 失败，说明已发布包面有问题，需要修复后发布新 RC 再验证
- local-source-root pass 可以写成 "fix is in HEAD"，但必须同时说明 "published package still carries the bug"

## Managed Surface Audit

`servo-installer` 管理的 skill 和 control-plane surface（`.skills`、`.agents`、`.claude`、`.servo`）通常被目标 repo 的 `.gitignore` 屏蔽，因此 `git diff` / `git status` 无法感知这些路径的变更。

### 为什么 Git Status 不够

- 目标 repo 的 `.gitignore` 是 repo owner 控制的，installer 不应假设 `.gitignore` 对 managed surface 可见
- 即使 git status 干净，`.skills`/`.agents`/`.claude`/`.servo` 仍可能已被 installer 修改
- same-size content change（内容变化但文件大小不变）在 path-level diff 中可能被忽略

### Audit 要求

- 在 reconcile 前后的 workspace 上各跑一次 managed surface audit
- 记录 content hash per file，检测 same-size content change
- 覆盖 `.skills/`、`.agents/`、`.claude/`、`.servo/` 四个 managed surface
- 不依赖目标 repo 的 `.gitignore` 配置
- audit 工具和 runner 集成位于 `.test/`（gitignored local test assets）

### 与 safe_diff 的关系

- `safe_diff`（path-level diff + forbidden-surface check）：对 tracked 和 git-aware 路径有效
- `managed_surface_audit`：对 gitignored managed surface 补充独立 hash-level 证据
- 两者组合形成完整的 reconcile 前后 surface 审计

## Disposable Workspace 方法论

所有 dogfood 和 reconcile 验证必须使用 disposable workspace，不得变更原始 repo：

### 工作流

1. **Freeze specimen**：从 freeze repo 复制一份作为 workspace baseline（不修改 freeze repo 原始文件）
2. **Create disposable workspace**：从 freeze specimen 创建独立的工作副本
3. **Record baseline**：记录 workspace 的 `.servo` manifest、git status、freeze manifest digest
4. **Execute**：在 workspace 内运行 reconcile / skills update 等命令
5. **Collect evidence**：记录 dry-run JSON、apply stdout、second dry-run JSON、safe_diff、managed surface audit
6. **Verify boundary**：确认 freeze specimen 未被修改、原始 repo 未被修改、无 remote/release mutation
7. **Retain or cleanup**：保留证据目录（`.test/execution/evidence/`），清理 disposable workspace

### 反模式

- 直接在原始 repo 上跑 reconcile apply（除非 operator 明确批准）
- 修改 `.gitignore` 使 managed surface 对 git 可见（这会改变目标 repo 的配置）
- 用 `git add -f` 强制追踪 gitignored 文件（同样改变 repo 状态）
