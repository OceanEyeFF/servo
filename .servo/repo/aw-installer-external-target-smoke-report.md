---
title: "servo-installer External Target Tarball Smoke Report"
artifact_type: "worktrack-supporting-report"
generated_from: "test-evidence-skill"
updated: "2026-04-27"
owner: "servo-kernel"
---
# servo-installer External Target Tarball Smoke Report

## Control Signal

- worktrack: `P0-006` / `WT-20260427-external-target-tarball-smoke`
- runbook: `.servo/repo/servo-installer-external-target-smoke-runbook.md`
- report_status: completed
- final_verdict: passed
- release_candidate_ready: yes, for local `.tgz` / dry-run evidence; real npm publish still requires separate approval.
- blocking_issues: none

## Candidate Identity

| Field | Value |
| --- | --- |
| git branch | `test-external-target-tarball-smoke` |
| git commit | `9938a89016a556e56cc06822c3da39ef42d79b99` |
| package file | `/tmp/tmp.ZTIXRZgh4X/servo-installer-0.0.0-local.tgz` |
| package version | `servo-installer 0.0.0-local` |
| node version | `v20.20.2` |
| npm version | `10.8.2` |
| run date | `2026-04-27T14:45:00+08:00` |
| operator | Codex Harness |

## Target Summary

| Target | Path | Target Type | Result | Notes |
| --- | --- | --- | --- | --- |
| target-alpha | `/tmp/tmp.ZTIXRZgh4X/target-alpha` | isolated temporary repo | passed | before diagnose reported missing target root; after install/update verify reported healthy target root |
| target-beta | `/tmp/tmp.ZTIXRZgh4X/target-beta` | isolated temporary repo | passed | before diagnose reported missing target root; after install/update verify reported healthy target root |

## Command Matrix

| Target | help | version | tui guard | diagnose before | update dry-run | install | verify | update --yes | diagnose after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target-alpha | passed | passed | passed | passed | passed | passed | passed | passed | passed |
| target-beta | passed | passed | passed | passed | passed | passed | passed | passed | passed |

## Diagnose Evidence

| Target | before issue_count | after issue_count | managed installs after | unrecognized after | conflict after |
| --- | ---: | ---: | ---: | --- | --- |
| target-alpha | 1 | 0 | 17 | 0 | 0 |
| target-beta | 1 | 0 | 17 | 0 | 0 |

## Source / Target Separation Check

- `AW_HARNESS_REPO_ROOT` cleared: yes
- `AW_HARNESS_TARGET_REPO_ROOT` cleared: yes
- package payload used instead of checkout payload: yes
- target root resolved to temporary target repo: yes
- observed package source root: `/home/oceaneye/.npm/_npx/ff1cc073ec6cb395/node_modules/servo-installer`
- observed target roots:
  - `/tmp/tmp.ZTIXRZgh4X/target-alpha/.agents/skills`
  - `/tmp/tmp.ZTIXRZgh4X/target-beta/.agents/skills`
- evidence paths:
  - target-alpha diagnose before: `/tmp/tmp.ZTIXRZgh4X/target-alpha.diagnose.before.json`
  - target-alpha diagnose after: `/tmp/tmp.ZTIXRZgh4X/target-alpha.diagnose.after.json`
  - target-beta diagnose before: `/tmp/tmp.ZTIXRZgh4X/target-beta.diagnose.before.json`
  - target-beta diagnose after: `/tmp/tmp.ZTIXRZgh4X/target-beta.diagnose.after.json`

## Failures And Recovery

| Target | Failed Command | Symptom | Recovery Attempted | Final State |
| --- | --- | --- | --- | --- |
| N/A | N/A | N/A | N/A | N/A |

## Release Readiness Assessment

- passed_targets: 2
- failed_targets: 0
- repeated_failure_pattern: none
- release_candidate_ready: yes, for local `.tgz` / dry-run evidence.
- required_follow_up_worktrack: none for local smoke; real publish still needs explicit approval and non-local package version work.
- real_npm_publish_approval_required: true

## Operator Summary

The packaged `servo-installer@0.0.0-local` tarball completed the full smoke matrix in two isolated temporary target repositories. Both runs cleared source and target override environment variables, resolved source payload from the package installed by `npm exec`, wrote only to temporary target repo `.agents/skills`, installed 17 managed skills, verified successfully, and completed `update --yes`.

## Supporting Detail

- raw evidence directory: `/tmp/tmp.ZTIXRZgh4X`
- expected non-interactive TUI guard: `servo-installer tui requires an interactive terminal.`
- notes: this report is runtime evidence for `P0-006`; it does not authorize real npm publish.
