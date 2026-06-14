---
title: "Dogfood Target Repo Registry"
status: active
updated: 2026-06-05
owner: servo-kernel
last_verified: 2026-06-13
---
# Dogfood Target Repo Registry

This registry fixes the long-term target repositories used for Servo dogfood and target-repo validation. It is not a one-off Worktrack list. Replace or add entries only through an explicit milestone/worktrack decision, and record why the old target no longer carries the needed evidence.

## Policy

- Use these repos as the default approved target set for installer, Harness behavior, and Milestone branch model dogfood.
- Prefer read-only `diagnose`, `verify`, scanner, and `update --json` on original repos.
- Run mutating `install`, `update --yes`, migration, branch simulation, or cleanup in temporary local copies unless the programmer explicitly approves mutation of the original repo.
- Disable push URLs or avoid remote operations in temporary copies.
- Record each target repo's pre-run `git status --short --branch`; existing dirty state is not a Servo failure unless the test mutates it.
- Never use third-party `external/` upstream mirrors as the default long-term set. They can be read-only comparison fixtures only.
- Do not count the Servo source checkout itself as a target repo for package/source-root smoke, because source and target roots must stay independent.

## Fixed Long-Term Targets

| Alias | Path | Default branch observed | Current suitability | Why it stays in the set |
|---|---|---|---|---|
| `repo-rating-function` | `/mnt/e/repos/personal/repo-rating-function` | `develop-servo` | clean status observed on 2026-06-05 | Small TypeScript/npm repo with existing Servo-oriented branch history; good for fast installer and Harness regression. |
| `t1-ai` | `/mnt/e/repos/wsl/personal/T1.AI` | `develop` tracking `origin/develop` | clean status observed on 2026-06-05 | Larger Python/AI repo with conda/pyproject shape; good for complex existing-code adoption and scan behavior. |
| `medical-data-marker` | `/mnt/e/repos/personal/medical_data_marker` | `develop` tracking `origin/develop` | clean status observed on 2026-06-05 | Electron/Vite/TypeScript app; good for multi-package frontend tooling and richer project structure. |
| `personal-knowledge-vault` | `/mnt/e/repos/personal/personal-knowledge-vault` | `claude-main` tracking `origin/claude-main` | clean status observed on 2026-06-05 | Documentation/knowledge repo with Claude-oriented files; good for docs-heavy and Claude payload behavior. |
| `reqflow` | `/mnt/e/repos/personal/reqflow` | `develop` tracking `origin/develop`, ahead 106 | dirty status observed on 2026-06-05 | Public Servo usage-flow example and larger Next.js/TypeScript app. Because it currently has local changes, original-repo runs are read-only/dry-run only; mutating dogfood must use a temporary copy or separate approval. |

## Previously Rejected Defaults

| Path | Reason |
|---|---|
| `/mnt/e/repos/wsl/personal/vibecoding_autoworkflow` | Source checkout for Servo; not a target repo for package/source-root independence. |
| `/mnt/e/repos/personal/MemoTui` | Large existing deletion status in `.agents/skills`; not a stable default target. |
| `/mnt/e/repos/personal/blog_maintainance` | Existing dirty docs/config state; keep as manual candidate only. |
| `/mnt/e/repos/personal/Scalable-MPMC-Queue-cpp` | Existing local `.serena` change and untracked content. |
| `/mnt/e/repos/personal/trae-agents-prompt` | Existing local `.serena` change and untracked `nul`. |
| `/mnt/e/repos/personal/20250216` | Clean but very large data-heavy repo; use only when the test specifically needs data-heavy behavior. |
| `/mnt/e/repos/personal/libgo` | Clean but status checks are slow; keep as C++ backup, not default. |
| `/mnt/e/repos/external/*` | Third-party upstream mirrors or dirty external checkouts; read-only comparison fixtures only. |

## Evidence History

- 2026-06-01: The five fixed targets above were used for `WT-20260601-autonomy-governance-tests`, with read-only original-repo diagnose/verify/update dry-run and temporary-copy install/update verification. Original target repos were not mutated.
- 2026-06-05: Paths were re-scanned under `/mnt/e/repos/wsl/personal/` and `/mnt/e/repos/*/`; the same five targets remain the default set, with the explicit `reqflow` read-only/dry-run caveat.
