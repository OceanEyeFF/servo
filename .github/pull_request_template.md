## Summary

## Changes

## Verification
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test`
- [ ] `npm --prefix toolchain/scripts/deploy test --silent`

## Risks

## Docs / Runbooks
- [ ] `docs/project-maintenance/governance/review-verify-handbook.md` updated when execution flow changes
- [ ] `docs/project-maintenance/foundations/root-directory-layering.md` updated when root-level layout changes

## Release PR Evidence
> 仅 `develop-main -> master` release PR 需填写本节。
- PR head SHA:
- Local release-readiness SHA:
- source-version docs freshness:
- candidate npm version/tag conflict check:
- CI run/job URL:
- skipped checks:
- reviewDecision:
