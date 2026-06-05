---
title: "servo-installer Release Standard Flow"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-05
---
# servo-installer Release Standard Flow

> 目的：定义已批准 release candidate 经过 merge PR、GitHub Release、publish workflow 与 post-publish verification 的 operator-facing 顺序。

本页属于 [Governance](./README.md)。

Manages branch/merge sequence, GitHub Release creation, publish workflow observation and post-publish verification. For pre-publish readiness see Pre-Publish Governance, for channel policy see Release Channel Governance, for carrier model see Release Operation Model.

## Preconditions

Only start after passing Pre-Publish Governance, tuple still satisfies Channel Governance, root `package.json` has approved version+lock, and release notes are ready. If the release requires a version change, complete [Prepare Candidate Version](./servo-installer-pre-publish-governance.md#0-prepare-candidate-version) before opening or updating the release PR.

For release PRs from the approved release development branch to `master`, confirm the PR title/body version, root package version, local scaffold version, approval lock, CLI `--version`, intended channel, and release marker all describe the same candidate. If they do not, stop before approval or merge, fix the tuple on the release development branch, rerun preflight, and push the correction to the PR. The current v0.6.1-rc.1 release cycle uses `develop` as the release development branch.

## 1. Refresh Local State

```bash
git status --short --branch
git fetch --no-tags origin master <release-development-branch> --prune
git fetch --no-tags origin refs/tags/v<package.version>:refs/tags/v<package.version>
gh release view v<package.version> --json tagName,url,isPrerelease,isDraft,name,targetCommitish,publishedAt
npm view servo-installer@<package.version> version --json
```

If tag or published version exists, stop and resolve conflict before continuing.

If npm fails because the default cache path is not writable, retry the registry queries with an explicit cache outside the source tree, for example `NPM_CONFIG_CACHE=/tmp/servo-npm-cache npm view ...`.

## 2. Push And Open The Merge PR

If the approved candidate currently lives on a development integration branch such as `develop-servo` or a worktrack branch, first merge or fast-forward that candidate into the approved release development branch through the approved local integration path, rerun the release-prep validation that changed or depends on the merge, and confirm the release development branch now contains the candidate tuple commit. Do not open the release PR from a stale release development branch that lacks the candidate.

```bash
git push origin <release-development-branch>
```

```bash
gh pr create \
  --draft \
  --base master \
  --head <release-development-branch> \
  --title "Release servo-installer v<package.version>" \
  --body "<summary, impact, and validation>"
```

```bash
gh pr checks <pr-number> --watch --interval 10 --fail-fast
gh pr view <pr-number> --json number,url,isDraft,mergeable,reviewDecision,state,headRefName,baseRefName,headRefOid,statusCheckRollup
```

If the authenticated GitHub account is also the PR author, do not attempt to self-approve. GitHub rejects author approvals even for repo owners. Record release readiness as a PR comment, then wait for an external review or an explicit owner/admin merge decision.

## 3. Merge To `master`

Merge only after PR is not draft, checks pass, and review gates are satisfied.

```bash
gh pr view <pr-number> --json state,mergedAt,mergeCommit,url,baseRefName,headRefName
git fetch --no-tags origin master
git rev-parse origin/master
```

The GitHub Release must target the merge commit on `master`.

Do not target the release development branch head commit if GitHub created a separate merge commit. Record the PR merge commit SHA and use that exact SHA in the release command.

## 4. Create The GitHub Release

The tag must exactly match `v<package.version>`, and the body must include `servo-installer-publish-approved: v<package.version>`:

```bash
gh release create v<package.version> \
  --target <master-merge-commit-sha> \
  --title "servo-installer v<package.version>" \
  --notes $'servo-installer-publish-approved: v<package.version>\n\n<version-specific release notes>'
```

Use GitHub prerelease only for prerelease semver channels (`next` / `canary`). Stable `latest` releases must be created without `--prerelease`; the publish workflow rejects GitHub prerelease releases that would publish to `latest`.

## 5. Watch The Publish Workflow

```bash
gh run list --workflow publish.yml --limit 5 --json databaseId,displayTitle,event,headBranch,headSha,status,conclusion,url,createdAt
gh run watch <run-id> --exit-status
```

If the workflow blocks on the `npm` environment or Trusted Publishing authentication, treat that as an external operator/configuration issue.

## 6. Verify Published State

```bash
gh release view v<package.version> --json tagName,url,isPrerelease,isDraft,name,targetCommitish,publishedAt
gh run view <run-id> --json databaseId,status,conclusion,url,headSha,displayTitle,event,createdAt,updatedAt
npm view servo-installer@<package.version> version dist-tags --json
npm view servo-installer dist-tags --json
npm view servo-installer@latest version gitHead dist.tarball --json
npm view servo-installer@next version gitHead dist.tarball --json
```

For RC releases on `next`, verify that `next` moved and `latest` stayed unchanged unless this was an explicitly approved stable release.

## 7. Registry Smoke

After publish, run registry `npx` smoke through [npx Command Test Execution](../../testing/npx-command-test-execution.md). For RC releases, pin the selector:

```bash
node toolchain/scripts/test/servo_installer_registry_npx_smoke.js --package servo-installer@next --skip-remote
```

Use full remote mode when the release window requires cross-target evidence; `--skip-remote` is sufficient for immediate post-publish package/selector verification.

## 8. Sync Version Facts

After registry verification and before final release handback, invoke [doc-catch-up-worker-skill](../../../../product/harness/skills/doc-catch-up-worker-skill/SKILL.md) in `version fact sync` mode.

The handoff must include:

- source version facts: root `package.json`, approval lock, CLI `--version`, GitHub Release tag
- VCS tracking facts: git branch, commit SHA, tag and remote ref; SVN URL/revision/branch path only when the target is an SVN working copy
- published version facts: npm dist-tags, published versions, `gitHead`, tarball URLs
- release evidence: GitHub Release view, publish workflow run, registry query output, registry npx smoke report
- doc update decision: documents updated and documents intentionally left unchanged

At minimum, review [Release Channel Governance](./servo-installer-release-channel-governance.md), [Pre-Publish Governance](./servo-installer-pre-publish-governance.md), [npx Command Test Execution](../../testing/npx-command-test-execution.md), backend usage-help pages, and root `README.md`. Update only pages whose facts changed or whose freshness is being verified in this release closeout.

Post-publish registry facts must not be written into the release tag target retroactively. Commit docs fact sync on the release development branch, open a narrow docs PR to `master`, wait for checks, then merge it.

## 9. Resync Release Development Branch

After the post-publish docs PR is merged, fast-forward the release development branch to `origin/master` and push it so the next release starts from the published repository truth:

```bash
git fetch --no-tags origin master <release-development-branch> --prune
git merge --ff-only origin/master
git push origin <release-development-branch>
git status --short --branch
```

Final handback must report the release tag, publish workflow run, npm dist-tags, registry smoke result, docs PR, and final release development branch / `master` SHAs.
