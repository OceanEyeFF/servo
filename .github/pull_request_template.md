## Summary

## Changes

## PR Type
- [ ] Normal worktrack / feature / fix
- [ ] `develop-main -> master` release PR
- [ ] Post-publish docs fact sync PR

## Verification
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py`
- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test`
- [ ] `npm --prefix toolchain/scripts/deploy test --silent`

For any checked item, include the local command result or the CI run/job URL. Do not mark skipped, pending, or not-run checks as passed.

## Release PR Evidence

Complete this section for `develop-main -> master` release PRs; write `N/A` otherwise.

- Candidate version:
- Candidate tag:
- Candidate channel:
- PR head SHA:
- Local release-readiness SHA:
- CLI version output:
- `check-root-publish.js` result:
- simulated publish guard result:
- source-version docs freshness:
- candidate npm version/tag conflict check:
- CI run/job URL:
- release readiness comment URL:

Release PRs stay draft and must not merge while any required check is failing, pending, skipped, or missing. In single-maintainer mode, an empty `reviewDecision` is acceptable only when CI is green and the release-readiness evidence above is recorded.

## Risks

## Docs / Runbooks
- [ ] `docs/project-maintenance/governance/review-verify-handbook.md` updated when execution flow changes
- [ ] `docs/project-maintenance/foundations/root-directory-layering.md` updated when root-level layout changes
