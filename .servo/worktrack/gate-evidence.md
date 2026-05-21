---
title: "Gate Evidence: WT-20260520-servo-npm-release-prep"
artifact_type: gate-evidence
worktrack_id: WT-20260520-servo-npm-release-prep
updated: 2026-05-20T23:00:00+08:00
---

# Gate Evidence

## implementation-gate

- **Verdict**: pass
- commits: `25797bc` (version bump), `cdfef9e` (remove private), `f8e3aaa` (description + 0.5.3), `f8076d1` (env vars + deploy_aw rename)
- All targeted; no scope creep; changes limited to deploy package.json, workflow ymls, deploy scripts, and docs

## validation-gate

- **Verdict**: blocked
- `path_governance_check.py`: passed
- `folder_logic_check.py`: passed
- `git diff --check`: passed
- `governance_semantic_check.py --json`: blocked until runtime state is reconciled
- `closeout_acceptance_gate.py --json`: blocked until scope gate accepts .servo runtime untracking and registry publish evidence exists
- npm registry lookup: E404, package unpublished on 2026-05-20T14:23:17.959Z
- npm publish attempted: E403 24h cooldown; `servo-installer@0.5.3` cannot be republished until the npm cooldown expires
- npm publish dry-run / pack: passed for `servo-installer@0.5.3` using `/tmp/servo-npm-cache`

## policy-gate

- **Verdict**: blocked
- No package version regression (0.5.2 → 0.5.3)
- No release channel mutation
- No deploy target modification (.claude/ preserved)
- All AW_ env vars migrated to SERVO_ prefix
- No git history rewrite
- Milestone acceptance cannot proceed until registry publish and npx smoke evidence exist

## Deferred Items

- `npm publish servo-installer@0.5.3`: 24h CD until ~2026-05-21 14:30 UTC
- aw-installer deprecation: programmer handled on web
