---
title: "npx Command Test Execution"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
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
- last_registry_smoke: 2026-06-05 `servo-installer@next` (`0.6.1-rc.1`, `next`) passed with `--skip-remote`; `latest` remained `0.5.8`

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

Claude commands 在临时 target repo 中通过 Node-owned compatibility lane 执行 package payload。`servo-installer` 不包含 Python fallback；Python deploy scripts 仅作 repo-local reference/parity/governance。

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
