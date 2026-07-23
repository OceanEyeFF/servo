# Harness Skills

`product/harness/skills/` is the canonical source root for distributed Harness Skill packages. Each immediate child directory containing `SKILL.md` is one package.

## Package Contract

- `SKILL.md` owns the package's complete operational contract.
- Runtime dependencies must be package-local under `scripts/`, `references/`, `templates/`, or `assets/` and listed by both adapter payloads.
- A distributed package must remain understandable and executable without source-repo `docs/`, `.servo`, `.agents`, or `.claude` content.
- `.agents/` and `.claude/` are deploy targets, never canonical source.
- Package inventory comes from these canonical directories and adapter discovery; there is no separate Skill catalog document.

## Canonical Inventory

### Supervisor

- `harness-skill`

### Repo And Milestone

- `repo-init-goal-skill`
- `repo-status-skill`
- `repo-whats-next-skill`
- `repo-append-request-skill`
- `repo-change-goal-skill`
- `repo-refresh-skill`
- `repo-writeback-skill`
- `milestone-init-skill`
- `milestone-cleanup-skill`
- `milestone-blackbox-check`
- `milestone-whitebox-check`
- `milestone-anticheat-check`
- `milestone-composite-check`
- `milestone-gate`

`milestone-init-skill` is the single Milestone create/amend capability:
stateless discussion-sufficiency admission, complete LLM-authored canonical
document/acceptance/TodoList output, exact approval, deterministic checking,
single-writer roll-forward persistence, and `init_not_ready` or
`milestone_ready` handoff. Harness answers ordinary Milestone status questions
by directly reading that canonical document and stable references with zero
writes; there is no separate Pre-intake or Status package.

### Candidate Worktrack Module

- `worktrack-plan-work-skill`
- `worktrack-review-skill`
- `worktrack-close-skill`

`worktrack-cleanup-skill` remains a Repo-owned maintenance package and is not a Candidate happy-path stage.

## Worktrack Boundary

The Candidate normal path is PlanWork, independent Review, mechanical Close, then Repo Refresh. PlanWork owns setup, branch creation, planning, implementation, affected validation, round commits, and redo. Review owns technical acceptance and canonical redo comments. Close only consumes `ready_to_close`, merges to the active Milestone branch, creates `finished-handback.yaml`, and returns the Repo Refresh handoff.

Candidate Worktrack packages只依赖 approved entry、per-id initial requirement、临时 round chain、structured Review result 与 finished handback。
