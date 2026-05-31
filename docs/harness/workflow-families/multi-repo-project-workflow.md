---
title: "Multi-Repo Project Workflow"
status: active
updated: 2026-05-31
owner: servo-kernel
last_verified: 2026-05-31
---
# Multi-Repo Project Workflow

> Purpose: define the Harness workflow policy for one product/project whose implementation is split across multiple repositories, such as separated frontend and backend repos.

This page belongs to [Workflow Families](./README.md). It defines workflow policy only. It does not create a third Harness scope, replace repo-local artifact contracts, or define installer/deploy behavior.

## Core Rule

Do not silently treat multiple repositories as one repo.

Each repository keeps its own repo-local Harness control state, local truth boundary, branch baseline, Worktrack contracts, evidence, gate, closeout, and repo refresh. Cross-repo coordination is represented by a project-level coordination surface and explicit integration worktracks, not by sharing one `.servo/` directory across repos.

## Control Model

Use three layers when a project spans multiple repos:

| Layer | Owns | Does not own |
| --- | --- | --- |
| Project coordination surface | project-level purpose, participating repos, cross-repo milestone intent, integration acceptance, dependency order | repo-local source truth, repo-local branch state, per-repo evidence |
| Repo-local Harness | one repo's Goal Charter, Snapshot, Milestone/Worktrack runtime state, local docs/source/toolchain changes | other repos' branches, unverified external repo facts, project-wide acceptance by itself |
| Integration worktrack | cross-repo compatibility evidence, API/contract alignment, end-to-end acceptance report | direct mutation of multiple repos without separate repo-local gates |

The project coordination surface may live in one of these places:

- a dedicated coordination repo when the project already has one;
- a clearly named coordination directory in a parent repo when that parent is a real project owner;
- a documented handoff packet when the operator intentionally runs Servo in one repo at a time.

It must not be hidden inside one application repo as if that repo owned the other repos' truth.

## Repo Binding Patterns

### Single-Repo Worktrack

Use a normal Worktrack when the change affects one repo only.

Examples:

- frontend UI copy, route, component, or build config;
- backend endpoint, schema, migration, or service behavior;
- repo-local docs, tests, or tooling.

The Worktrack Contract records one `baseline_branch`, one `baseline_ref`, one branch, one gate, and one closeout path.

### Coordinated Parallel Worktracks

Use multiple repo-local worktracks when the project goal requires changes in more than one repo but each repo can be verified independently before integration.

Each repo gets its own worktrack with:

- a repo-local branch and baseline;
- repo-local acceptance criteria;
- repo-local gate evidence;
- repo-local closeout and refresh.

The project coordination surface records the dependency relation, for example "backend contract first, frontend consumer second", but it does not replace either repo's local gate.

### Integration Worktrack

Use an integration worktrack after the needed repo-local changes exist, or when the primary deliverable is compatibility evidence rather than source changes.

An integration worktrack may verify:

- frontend and backend API compatibility;
- generated client/server contract agreement;
- end-to-end smoke against compatible commits;
- release readiness across repos.

An integration worktrack must cite the exact repo commits or released artifacts it verifies. It must not claim success from branch names alone.

## Milestone Policy

A cross-repo milestone should describe the project-level outcome, but it should not erase repo boundaries.

Recommended structure:

- project milestone: states the product outcome and cross-repo acceptance;
- repo-local worktracks: implement or document changes in each repo;
- integration worktrack: proves that the selected repo-local outcomes work together.

Completion requires both:

- all required repo-local worktracks have passed their repo-local gates; and
- integration acceptance has verified the compatible set of repo refs or releases.

If only one repo has completed, the project milestone is not complete; it is partially satisfied.

## Truth Boundary

Facts belong at the narrowest layer that can verify them.

| Fact | Write it to |
| --- | --- |
| Frontend source behavior | frontend repo truth/docs/evidence |
| Backend source behavior | backend repo truth/docs/evidence |
| API contract shared by both repos | project coordination surface or an agreed contract repo/file, with links from each repo |
| End-to-end compatibility of selected refs | integration worktrack evidence |
| Project-level product purpose | project coordination surface |
| Repo-local maintenance rules | the owning repo's docs or Harness artifacts |

Do not copy long-lived truths into multiple repos unless each copy has a clear owner and sync rule. Prefer one owner plus links or references.

## Intake Questions

Before initializing a multi-repo milestone or worktrack, the Harness should resolve these questions:

1. Which repos participate, and which one is the current execution repo?
2. Is the requested work frontend-only, backend-only, coordinated, or integration-only?
3. Which repo owns the source truth for each changed behavior?
4. What is the project-level acceptance signal?
5. Which exact refs, releases, environments, or API contracts must be cited for integration evidence?
6. Can the current carrier access the other repos, or must cross-repo facts be provided by the programmer?

If these answers are missing and materially affect scope, initialize a discovery or intake worktrack before implementation. Do not guess repo ownership.

## Failure Modes

Avoid these patterns:

- one repo's `.servo/` claims to be the runtime state for another repo;
- a frontend worktrack silently edits backend code, or the reverse;
- integration success is inferred from "latest branch" instead of exact refs;
- a project-level milestone closes before integration evidence exists;
- duplicated docs drift because no repo is declared owner;
- one repo's release/version changes are made as a side effect of another repo's worktrack.

## Skill Impact

Current policy is docs-first. Existing skills can support this model if they preserve explicit repo binding:

- `init-milestone-skill`: milestone purpose may be project-level, but worktracks need repo binding in their contract.
- `repo-whats-next-skill`: intake review should classify the candidate as frontend-only, backend-only, coordinated, or integration-only when multi-repo signals appear.
- `init-worktrack-skill`: Worktrack Contract should identify the current execution repo and treat other repos as external dependencies unless a project coordination surface authorizes broader access.
- `test-evidence-skill`: integration evidence must cite exact refs/releases/environments.

If future work needs first-class project coordination artifacts, add them explicitly instead of overloading repo-local `.servo/`.
