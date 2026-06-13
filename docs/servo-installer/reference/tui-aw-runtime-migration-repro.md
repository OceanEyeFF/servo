---
title: "TUI .aw Runtime Migration Repro"
status: active
updated: 2026-05-27
owner: servo-kernel
last_verified: 2026-06-13
---
# TUI .aw Runtime Migration Repro

This note records the verified `servo-installer v0.5.7` gap where the TUI first menu option updates skill payloads but does not run legacy `.aw/` runtime migration.

## Current Finding

`servo-installer tui` option 1 is labeled `Guided install/update`, but its mutation stage runs the install path:

- TUI menu option 1 calls `runGuidedFullFlow` in `toolchain/scripts/deploy/bin/servo-installer.js`.
- The install stage calls `install --backend <backend>`.
- Runtime migration is only wired through the explicit `migrate-runtime --from aw --to servo` CLI path.

For a target that has `.aw/` and no `.servo/`, option 1 can install or refresh `.agents/` and `.claude/` skills while leaving `.servo/` absent.

## Closest Automated Fixture

Native Windows PowerShell execution is not available in the current verification carrier. The closest automated fixture uses a non-ASCII temporary path on Linux/WSL:

```bash
target="$(mktemp -d "/tmp/中文 servo repro.XXXXXX")"
mkdir -p "$target/.aw/worktrack"
printf 'state references `.aw/control-state.md`\n' > "$target/.aw/control-state.md"

cd "$target"
npx --yes --package servo-installer -- servo-installer tui
```

In the TUI:

1. Keep the default `bundle` backend.
2. Select `Guided install/update`.
3. Continue past diagnose.
4. Confirm with `yes`.

Observed v0.5.7 result:

- `.agents/skills/servo-*` and `.claude/skills/*` are installed or refreshed.
- `.servo/` is not created.
- `.aw/` remains the only runtime control-plane directory.

Expected future result:

- The TUI detects `.aw/` present and `.servo/` absent.
- The operator sees an explicit migration choice.
- The mutating action maps to `migrate-runtime --from aw --to servo --yes --reinstall --backend bundle` or the selected backend equivalent.

## Explicit Migration Comparison

The explicit CLI migration path is the current working path:

```bash
npx --yes --package servo-installer -- \
  servo-installer migrate-runtime --from aw --to servo --yes --reinstall --backend bundle
```

Expected result:

- `.aw/` is retained.
- `.servo/` is created.
- Migrated text files rewrite `.aw` path references to `.servo`.
- Backend skill payloads are reinstalled through the existing update chain.

## Windows PowerShell Manual Repro

Use this when a native Windows PowerShell terminal is available:

```powershell
$target = Join-Path $env:TEMP "中文 servo repro"
Remove-Item -Recurse -Force $target -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "$target\.aw\worktrack" | Out-Null
Set-Content -Encoding UTF8 -Path "$target\.aw\control-state.md" -Value 'state references `.aw/control-state.md`'
Set-Location $target
npx --yes --package servo-installer -- servo-installer tui
```

Then select the first TUI option and confirm. Record whether `.servo\control-state.md` exists after completion.

## Related Legacy Content Risk

Migration can succeed technically while old repo-local documentation still tells operators or agents to keep `.aw/` synchronized. This is not caused by current deployed skills when those skills no longer contain literal `.aw` writeback instructions; it can come from active project documents or runtime artifacts in the target repository.

Operator-facing guidance after migration should therefore recommend a target-local scan for stale `.aw` control-plane instructions. A safe first pass is:

```bash
rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' \
  '(\.aw/|`\.aw`|\.aw control|\.aw 控制|write.*\.aw|写.*\.aw|sync.*\.aw|同步.*\.aw|\.servo/\.aw|\.aw/\.servo)' \
  docs .servo .agents .claude
```

The scan should distinguish:

- legacy history or compatibility explanation that may remain;
- active instructions that tell the operator to write or synchronize `.aw/`;
- migrated `.servo/` runtime artifacts that still mention `.aw/.servo` dual-write semantics;
- deploy identity metadata such as `aw.marker`, which is not the same as root `.aw/` runtime state.

Follow-up product work should make this scan visible after runtime migration, preferably as a reminder or optional diagnostic rather than an automatic destructive rewrite of user-owned docs.

## Regression Coverage

`toolchain/scripts/test/servo_installer_tui/test_tui_interactions.py` now contains passing regression coverage for the repaired TUI migration flow:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  toolchain/scripts/test/servo_installer_tui/test_tui_interactions.py \
  -q
```

The suite covers the guided install/update path creating `.servo/` from `.aw/` when migration is safe, and blocking `.aw/ + .servo/` conflicts without installing skills.
