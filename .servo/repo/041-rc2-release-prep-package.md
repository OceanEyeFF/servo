---
title: "0.4.1 rc2 Release Preparation Package"
artifact_type: "release-preparation-package"
generated_from: "WT-20260429-041-rc2-release-prep"
updated: "2026-04-30"
owner: "servo-kernel"
---
# 0.4.1 rc2 Release Preparation Package

## Control Signal

- package_name: `servo-installer`
- candidate_version: `0.4.1-rc.2`
- candidate_git_tag: `v0.4.1-rc.2`
- intended_channel: `next`
- approval_lock: root `package.json` matches `0.4.1-rc.2` / `v0.4.1-rc.2` / `next`
- registry_current_latest: `0.4.0-rc.1`
- registry_current_next: `0.4.1-rc.2`
- registry_rc2_git_head: `7f7536a`
- current_local_checkpoint: `b0b8250`
- release_preparation_status: published-next-observed-and-post-publish-smoke-passed
- real_publish_allowed: no-repeat-publish-for-this-version
- github_master_source_ready: no
- blocking_before_publish: N/A for `0.4.1-rc.2`; registry already contains this immutable npm version on `next`. Future publish requires a new version and separate approval.

## Candidate Tuple

- root_package_name: `servo-installer`
- root_package_version: `0.4.1-rc.2`
- cli_version: `servo-installer 0.4.1-rc.2`
- approved_version: `0.4.1-rc.2`
- approved_git_tag: `v0.4.1-rc.2`
- approved_channel: `next`
- real_publish_approval_metadata: `approved`
- release_channel_policy: prerelease RC maps to npm `next`; stable/latest remains unapproved.

## Registry Facts

- command: `npm view servo-installer version dist-tags --json`
- observed_version: `0.4.0-rc.1`
- observed_latest: `0.4.0-rc.1`
- observed_next: `0.4.1-rc.2`
- observed_git_head: `7f7536a`
- interpretation: published RC trial users should use `servo-installer@next`; this selector now resolves to the `0.4.1-rc.2` registry artifact built from `gitHead=7f7536a`. Current local `b0b8250` includes post-publish changes and needs a new version before any future publish.

## GitHub Source Readiness

- local_candidate_ref: `config-041-rc2-release-prep` / `develop-aw@2e9f49f`
- local_candidate_contains_required_payload: yes
- local_origin_master_ref: `origin/master@e7e3ec4`
- local_master_ref: `master@c0fcbea`
- github_master_archive_check: failed
- failing_command: `servo-installer update --backend agents --source github --github-repo OceanEyeFF/servo --github-ref master --json`
- failure: GitHub `master` archive is missing `product/harness/adapters/claude/skills`
- develop_aw_archive_check: failed with HTTP 404, because `develop-aw` is not available as a GitHub source archive ref in the checked remote state
- publish_implication: `0.4.1-rc.2` should not be published as the GitHub-source-ready candidate until the selected GitHub ref contains current required payload sources, or the release explicitly selects a different proven source ref.

## Release Notes Draft

- Prepared `servo-installer@0.4.1-rc.2` as the local checkout candidate.
- Records that `servo-installer@next` registry users now receive the already published `0.4.1-rc.2` artifact.
- Clarifies that current local post-publish changes are not part of the already published `0.4.1-rc.2` artifact.
- Clarifies GitHub-source updates must use a ref containing current payload sources; current GitHub `master` is not ready for the `0.4.1-rc.2` payload.
- Keeps Claude support bounded to the `set-harness-goal-skill` compatibility payload.
- Keeps agents backend as the primary distribution path.
- Includes current canonical Harness skills, agents adapter payload descriptors, Claude compatibility payload descriptor, and deploy wrapper files in the package dry-run packlist.

## Rollback And Repair Notes

- If a future publish uses the wrong dist-tag, correct the npm dist-tag before external trial handoff.
- If a future package tarball is missing required files, do not try to mutate the published tarball; deprecate or supersede with a replacement version.
- If GitHub-source update fails after publish, pause GitHub-source instructions and use package-local `servo-installer@next` payload until a proven GitHub ref exists.
- Stable/latest promotion remains separate and is not authorized by this package.

## Validation Evidence

- package tuple check: passed.
- `npm view servo-installer version dist-tags --json`: passed; observed `latest=0.4.0-rc.1`, `next=0.4.1-rc.2`.
- `node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --package servo-installer@next --skip-remote`: passed; report `/tmp/servo-installer-registry-npx-smoke-GI75vS/report.md`.
- `node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --package servo-installer@next`: passed; report `/tmp/servo-installer-registry-npx-smoke-anIm0J/report.md`.
- `node toolchain/scripts/deploy/bin/servo-installer.js --version`: passed; `servo-installer 0.4.1-rc.2`.
- `node --check toolchain/scripts/deploy/bin/servo-installer.js`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s toolchain/scripts/deploy -p 'test_*.py'`: passed, 129 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_agents_adapter_contract.py toolchain/scripts/test/test_closeout_gate_tools.py`: passed, 39 tests.
- `npm pack --dry-run --json`: passed for `servo-installer@0.4.1-rc.2`, 79 files.
- `npm run publish:dry-run --silent`: passed for `servo-installer@0.4.1-rc.2`, 79 files.
- `toolchain/scripts/test/servo_installer_multi_temp_workdir_smoke.sh --skip-remote`: passed; package path `/tmp/tmp.fZlovruVZ7/servo-installer-0.4.1-rc.2.tgz`.
- focused Claude dry-run: passed for `diagnose --backend claude --json` and `update --backend claude --json`; missing target root is non-blocking in update dry-run.
- focused GitHub `master` source dry-run: failed as expected; missing `product/harness/adapters/claude/skills`.
- `git diff --check`: passed.

## Publish Approval Boundary

- real npm publish: not performed here; do not repeat publish `0.4.1-rc.2`.
- npm dist-tag mutation: not approved here.
- GitHub Release publication: not approved here.
- direct GitHub `master` mutation: not approved here.
- remote branch push: not approved here.
- external repository mutation: not performed.
