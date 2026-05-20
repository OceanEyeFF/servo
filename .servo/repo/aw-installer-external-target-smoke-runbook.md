---
title: "servo-installer External Target Tarball Smoke Runbook"
artifact_type: "worktrack-supporting-runbook"
generated_from: "harness-skill"
updated: "2026-04-27"
owner: "servo-kernel"
---
# servo-installer External Target Tarball Smoke Runbook

## Control Signal

- worktrack: `P0-006` / `WT-20260427-external-target-tarball-smoke`
- purpose: prove the root package tarball can install and verify the `agents` payload in isolated target repositories without relying on the source checkout as target root.
- must_not_do:
  - Do not run real `npm publish`.
  - Do not point `AW_HARNESS_TARGET_REPO_ROOT` at a production repository unless that repository is explicitly approved for mutation.
  - Do not test remote fetch, channel resolution, self-update, signing, or automatic rollback.
- report_template: `.servo/repo/servo-installer-external-target-smoke-report.md`

## Preconditions

- Run from the repository root on branch `develop-aw` or the release-candidate branch under review.
- Node.js must satisfy the root `package.json` engine requirement.
- The working tree should be clean except `.servo/` runtime artifacts.
- The candidate package must still be local/pre-release unless a separate real publish approval exists.

## One-Shot Smoke Script

Run this block from the repository root. It creates two isolated target repositories under a temporary directory, packs the current checkout, then exercises the packaged `servo-installer` entrypoint from the `.tgz`.

```bash
set -eu

repo_root="$(pwd)"
tmpdir="$(mktemp -d)"
echo "tmpdir=$tmpdir"

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
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer --help
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer --version

    if AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer tui > "$tmpdir/$target_name.tui.out" 2> "$tmpdir/$target_name.tui.err"; then
      echo "expected servo-installer tui to require an interactive terminal for $target_name" >&2
      exit 1
    fi
    test ! -s "$tmpdir/$target_name.tui.out"
    grep -F "servo-installer tui requires an interactive terminal" "$tmpdir/$target_name.tui.err"

    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer diagnose --backend agents --json > "$tmpdir/$target_name.diagnose.before.json"
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer update --backend agents --json > "$tmpdir/$target_name.update.dry-run.json"
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer install --backend agents
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer verify --backend agents
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer update --backend agents --yes
    AW_HARNESS_REPO_ROOT="" AW_HARNESS_TARGET_REPO_ROOT="" npm exec --yes --package "$package_path" -- servo-installer diagnose --backend agents --json > "$tmpdir/$target_name.diagnose.after.json"
  )
done

echo "package_path=$package_path"
echo "target_alpha=$tmpdir/target-alpha"
echo "target_beta=$tmpdir/target-beta"
echo "evidence_dir=$tmpdir"
```

## Evidence To Preserve

Copy these values into the report template:

- `package_path`
- package filename and package version from `servo-installer --version`
- `target-alpha` and `target-beta` paths
- verdict for help/version/TUI guard/diagnose/update dry-run/install/verify/update apply
- before/after issue counts from `*.diagnose.*.json`
- any failure command, stderr excerpt, and recovery action

## Pass Criteria

- Both target repos complete the full command sequence.
- `tui` fails in non-interactive mode with the expected guard message.
- `diagnose` and `update --json` run before mutation and write JSON evidence.
- `install`, `verify`, and `update --yes` succeed in each target repo.
- The target repo root is the temporary target directory, not the source checkout.

## Fail Handling

- If `npm pack` fails, stop and route back to `P0-005` release-candidate prep.
- If one target fails and the other passes, preserve both evidence sets and mark the smoke as partial.
- If both targets fail for the same reason, do not continue to release readiness review; create a bugfix or test worktrack from the shared failure.
- If a command would mutate a non-temporary target, stop and request explicit approval.
