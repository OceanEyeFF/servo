#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: servo_installer_multi_temp_workdir_smoke.sh [--output-dir DIR] [--skip-remote]

Packs the current repository as a local servo-installer .tgz, then runs the
packaged installer against multiple isolated temporary target workdirs.

Default targets:
  - empty-local temporary git repo
  - temporary clone of https://github.com/OceanEyeFF/T1.AI
  - temporary clone of https://github.com/OceanEyeFF/novel-agents

Use --skip-remote to run only generated local temporary targets.
USAGE
}

output_dir=""
skip_remote="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      output_dir="${2:-}"
      if [[ -z "$output_dir" ]]; then
        usage
        exit 2
      fi
      shift 2
      ;;
    --skip-remote)
      skip_remote="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

repo_root="$(git rev-parse --show-toplevel)"
if [[ -z "$output_dir" ]]; then
  output_dir="$(mktemp -d)"
else
  mkdir -p "$output_dir"
  output_dir="$(cd "$output_dir" && pwd)"
fi

targets_root="$output_dir/targets"
evidence_root="$output_dir/evidence"
npm_state_root="$output_dir/npm-state"
mkdir -p "$targets_root" "$evidence_root" "$npm_state_root/cache" "$npm_state_root/tmp" "$npm_state_root/home"
printf 'audit=false\nfund=false\nupdate-notifier=false\n' > "$npm_state_root/npmrc"

package_path="$(
  cd "$repo_root"
  NPM_CONFIG_CACHE="$npm_state_root/cache" \
    NPM_CONFIG_TMP="$npm_state_root/tmp" \
    NPM_CONFIG_USERCONFIG="$npm_state_root/npmrc" \
    HOME="$npm_state_root/home" \
    "$repo_root/toolchain/scripts/test/npm_pack_tarball.sh" "$output_dir"
)"

node --version > "$output_dir/node.version"
npm --version > "$output_dir/npm.version"
git -C "$repo_root" rev-parse --abbrev-ref HEAD > "$output_dir/git.branch"
git -C "$repo_root" rev-parse HEAD > "$output_dir/git.commit"

target_specs=(
  "empty-local|"
)

if [[ "$skip_remote" != "true" ]]; then
  target_specs+=(
    "t1-ai|https://github.com/OceanEyeFF/T1.AI.git"
    "novel-agents|https://github.com/OceanEyeFF/novel-agents.git"
  )
else
  target_specs+=(
    "empty-beta|"
    "empty-gamma|"
  )
fi

run_aw() {
  local target_repo="$1"
  shift
  (
    cd "$target_repo"
    HOME="$npm_state_root/home" \
      NPM_CONFIG_CACHE="$npm_state_root/cache" \
      NPM_CONFIG_TMP="$npm_state_root/tmp" \
      NPM_CONFIG_USERCONFIG="$npm_state_root/npmrc" \
      SERVO_HARNESS_REPO_ROOT="" \
      SERVO_HARNESS_TARGET_REPO_ROOT="" \
      npm exec --yes --package "$package_path" -- servo-installer "$@"
  )
}

summary_tsv="$output_dir/summary.tsv"
printf 'target\turl\ttarget_repo\tresult\tpackage_path\n' > "$summary_tsv"

for spec in "${target_specs[@]}"; do
  IFS='|' read -r target_name target_url <<< "$spec"
  target_repo="$targets_root/$target_name"
  target_evidence="$evidence_root/$target_name"
  mkdir -p "$target_evidence"

  if [[ -n "$target_url" ]]; then
    git clone --depth 1 "$target_url" "$target_repo" > "$target_evidence/clone.out" 2> "$target_evidence/clone.err"
    git -C "$target_repo" remote set-url --push origin "DISABLED_BY_AW_TEMP_SMOKE_NO_PUSH" > "$target_evidence/remote-push-guard.out" 2> "$target_evidence/remote-push-guard.err"
    git -C "$target_repo" remote -v > "$target_evidence/remotes.after-guard.out"
  else
    mkdir -p "$target_repo"
    git -C "$target_repo" init > "$target_evidence/git-init.out" 2> "$target_evidence/git-init.err"
  fi

  run_aw "$target_repo" --help > "$target_evidence/help.out"
  run_aw "$target_repo" --version > "$target_evidence/version.out"

  if run_aw "$target_repo" tui > "$target_evidence/tui.out" 2> "$target_evidence/tui.err"; then
    echo "expected servo-installer tui to require an interactive terminal for $target_name" >&2
    exit 1
  fi
  test ! -s "$target_evidence/tui.out"
  grep -F "servo-installer tui requires an interactive terminal" "$target_evidence/tui.err" > "$target_evidence/tui.guard"

  run_aw "$target_repo" diagnose --backend agents --json > "$target_evidence/diagnose.before.json"
  run_aw "$target_repo" update --backend agents --json > "$target_evidence/update.dry-run.json"
  run_aw "$target_repo" install --backend agents > "$target_evidence/install.out"
  run_aw "$target_repo" verify --backend agents > "$target_evidence/verify.out"
  run_aw "$target_repo" update --backend agents --yes > "$target_evidence/update.apply.out"
  run_aw "$target_repo" diagnose --backend agents --json > "$target_evidence/diagnose.after.json"

  node - "$repo_root" "$target_repo" "$target_evidence/diagnose.before.json" "$target_evidence/update.dry-run.json" "$target_evidence/diagnose.after.json" <<'NODE'
const fs = require("node:fs");
const path = require("node:path");

const [repoRoot, targetRepo, beforePath, dryRunPath, afterPath] = process.argv.slice(2).map((value) => path.resolve(value));
const before = JSON.parse(fs.readFileSync(beforePath, "utf8"));
const dryRun = JSON.parse(fs.readFileSync(dryRunPath, "utf8"));
const after = JSON.parse(fs.readFileSync(afterPath, "utf8"));
const expectedBindingCount = before.binding_count;

function fail(message) {
  throw new Error(message);
}

function isInside(child, parent) {
  const relative = path.relative(parent, child);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

if (!Number.isInteger(expectedBindingCount) || expectedBindingCount <= 0) {
  fail(`diagnose before must report a positive binding_count, got ${expectedBindingCount}`);
}
if (Number.isInteger(after.binding_count) && after.binding_count !== expectedBindingCount) {
  fail(`expected final binding_count ${expectedBindingCount}, got ${after.binding_count}`);
}
if (after.managed_install_count !== expectedBindingCount) {
  fail(`expected ${expectedBindingCount} managed installs after install/update, got ${after.managed_install_count}`);
}
if (after.conflict_count !== 0 || after.unrecognized_count !== 0) {
  fail(`expected no conflicts/unrecognized entries after install/update, got conflicts=${after.conflict_count} unrecognized=${after.unrecognized_count}`);
}
if (!isInside(path.resolve(after.target_root), targetRepo)) {
  fail(`target_root ${after.target_root} is not inside target repo ${targetRepo}`);
}
if (isInside(path.resolve(after.source_root), repoRoot)) {
  fail(`source_root ${after.source_root} unexpectedly resolved inside source checkout ${repoRoot}`);
}
if (isInside(path.resolve(after.source_root), targetRepo)) {
  fail(`source_root ${after.source_root} unexpectedly resolved inside target repo ${targetRepo}`);
}
if (path.resolve(after.source_root) === path.resolve(after.target_root)) {
  fail(`source_root ${after.source_root} unexpectedly equals target_root ${after.target_root}`);
}
if (!Array.isArray(dryRun.planned_target_paths) || dryRun.planned_target_paths.length !== expectedBindingCount) {
  fail(`expected ${expectedBindingCount} dry-run planned target paths, got ${dryRun.planned_target_paths && dryRun.planned_target_paths.length}`);
}
for (const targetPath of dryRun.planned_target_paths) {
  if (!isInside(path.resolve(targetPath), targetRepo)) {
    fail(`planned target path ${targetPath} is not inside target repo ${targetRepo}`);
  }
}
if (!before.source_root || !after.source_root) {
  fail("diagnose output must include source_root before and after install");
}
NODE

  printf '%s\t%s\t%s\tpassed\t%s\n' "$target_name" "${target_url:-local-empty}" "$target_repo" "$package_path" >> "$summary_tsv"
done

{
  echo "# servo-installer Multi Temporary Workdir Smoke Report"
  echo
  echo "## Candidate"
  echo
  echo "- git branch: $(cat "$output_dir/git.branch")"
  echo "- git commit: $(cat "$output_dir/git.commit")"
  echo "- package path: $package_path"
  echo "- node version: $(cat "$output_dir/node.version")"
  echo "- npm version: $(cat "$output_dir/npm.version")"
  echo "- evidence dir: $output_dir"
  echo "- npm state dir: $npm_state_root"
  echo "- skip remote: $skip_remote"
  echo
  echo "## Target Summary"
  echo
  echo "| Target | Source | Target repo | Result |"
  echo "| --- | --- | --- | --- |"
  tail -n +2 "$summary_tsv" | while IFS=$'\t' read -r target_name target_url target_repo result _package; do
    echo "| $target_name | $target_url | $target_repo | $result |"
  done
  echo
  echo "## Verdict"
  echo
  echo "- result: passed"
  echo "- target_count: ${#target_specs[@]}"
  echo "- source_root_checkout_leakage: not observed"
  echo "- source_root_target_repo_leakage: not observed"
  echo "- target_root_cross_workdir_leakage: not observed"
  echo "- remote_mutation: not performed"
  echo "- remote_push_guard: remote clone push URLs set to DISABLED_BY_AW_TEMP_SMOKE_NO_PUSH"
  echo "- npm_publish_required: false"
} > "$output_dir/report.md"

echo "package_path=$package_path"
echo "evidence_dir=$output_dir"
echo "report=$output_dir/report.md"
