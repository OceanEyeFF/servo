---
name: worktrack-plan-work-skill
description: 当已批准的 Candidate Worktrack 需要创建分支和 immutable initial requirement，并在一次调用中完成 Plan、Work、affected validation 与单轮提交，或消费 Review comment 执行 redo 时，使用这个技能。
---

# Worktrack Plan and Work Skill

## Role

This Skill owns Candidate Worktrack setup and implementation rounds. A normal
invocation creates the Worktrack branch, persists the approved initial
requirement, confirms the Initial Entry checkpoint, then carries Plan, Work,
affected validation, and one implementation round to `review_requested`,
`blocked`, or `approval_required`. A redo invocation repeats Plan/Work inside the
unchanged initial mission.

It is self-contained and does not require source-repo docs. It does not invoke
Review or Close, spawn a descendant SubAgent, judge technical acceptance, or
change Repo/Milestone state.

## Candidate Authority

Normal entry receives:

- `worktrack_id`
- approved initial requirement data from Repo/Milestone orchestration
- accepted mutation and approval boundaries
- affected validation requirements
- deterministic `worktrack_setup_check.py` result
- current implementation checkpoint

The approved initial requirement contains:

```yaml
worktrack_id: string
milestone_id: string
objective: string
acceptance_checks:
  - check_id: string
    requirement: string
    evidence_kinds:
      - implementation | validation | governance | runtime | artifact
scope:
  included_surfaces: [string]
  excluded_surfaces: [string]
  approved_write_surface: [string]
constraints:
  - constraint_id: string
    rule: string
    on_violation: blocked | approval_required
branch_source:
  branch: string
  checkpoint: string
close_target:
  branch: string
created_at: string
created_by: string
```

Required strings are concrete and non-placeholder. Acceptance checks, included
surfaces, and approved write surfaces are non-empty. Excluded paths are not
writable. The close target branch is concrete and equals `branch_source.branch`.
The source checkpoint is a full Git commit hash, and `worktrack_id` derives a
legal `wt/<worktrack-id>` ref.

PlanWork validates and materializes this data without rewriting, expanding, or
reinterpreting objective, acceptance, scope, constraints, branch source, or
close target. Missing, stale, contradictory, or expanded authority stops before
mutation.

Redo receives the immutable initial requirement, the complete lowercase runtime
chain, the latest expected Review comment, unchanged mutation/approval/validation
boundaries, and the rejected implementation checkpoint.

Setup output is legality evidence only. The checker never creates a branch,
artifact, plan, runtime round, or commit.

## Runtime And Persistence

- Persistent Candidate authority:
  `.servo/worktrack/<worktrack-id>/initial-requirement.yaml`.
- Temporary round handoff: `.servo/tmp/<worktrack-id>/`.
- Runtime filenames are lowercase ASCII; YAML `round_id` values use `RNNN`.
- The upper Orchestrator dispatches one role at a time. At most one PlanWork
  carrier writes the requirement or round YAML files.
- PlanWork and Review return to the Orchestrator and never invoke each other.
- Round YAML and Review comments do not record Human, LLM, PlanWork, or Review
  carrier identity.
- Unexpected concurrency or unavailable shared workspace blocks. No locks,
  replay protocol, workflow engine, or multi-writer recovery is added.

Candidate PlanWork does not create rolling Worktrack Contract, queue, dispatch,
Gate, report, recovery, closeout Markdown, or closeout-evidence-bundle artifacts.

## Normal Entry And Initial Entry

1. While on `branch_source.branch`, validate setup legality, initial requirement,
   mutation boundary, approval boundary, and affected validation requirements.
2. Require `can_setup: true`, no setup approval stop, the derived
   `expected_branch`, and a clean non-ignored worktree and index.
3. Confirm the current branch and `HEAD` equal the approved source branch and
   full checkpoint. Recheck HEAD immediately before branch creation.
4. Require `expected_branch` to be absent. An existing branch blocks for an
   explicit upper recovery decision; normal entry does not infer resume authority.
5. Create and switch to `expected_branch` from the exact source checkpoint. Read
   back branch and HEAD. Branch creation, switch, or readback failure blocks
   before persistent/runtime file creation or implementation mutation.
6. Require
   `.servo/worktrack/<worktrack-id>/initial-requirement.yaml` to be absent. Create
   it once from the approved input, then read back its identity and every
   authority-bearing field. Never overwrite or force-update it.
7. Classify Git visibility fail closed:
   - Git-visible mode requires exactly the expected new requirement path and no
     other tracked/untracked change.
   - Git-ignored mode requires the file to exist and pass readback, direct
     `git check-ignore` proof, no unexplained status, and no other unapproved
     tracked/untracked change.
   - Missing content, ambiguous invisibility, failed readback, or extra change
     blocks.
8. In visible mode, stage only the requirement and create one file-bearing
   Initial Entry commit. In proven-ignored mode, do not use `git add -f` or change
   `.gitignore`; create one `git commit --allow-empty` Initial Entry marker.
9. Confirm the new commit's only parent is `branch_source.checkpoint`. The visible
   delta contains only the requirement path; the marker tree equals its parent.
   Require a clean index and non-ignored worktree.
10. Only after commit confirmation, create
    `.servo/tmp/<worktrack-id>/worktrack-r000.yaml`. If it exists, block without
    overwrite.
11. R000 records Worktrack/round identity, the Initial Entry commit as
    `start_checkpoint`, objective, acceptance, scope/write surface, constraints,
    close target, this round's plan, and `commit_sha: null`.
12. Read back round identity and checkpoint, then perform Plan, approved Work,
    affected validation, and round finalization.

The Initial Entry commit is a lifecycle checkpoint, not an implementation round.
Its marker does not claim to preserve ignored content across clones.

## Redo Round

The Review comment and YAML for the next attempt both use the next round index:

```text
worktrack-r000.yaml
-> worktrack-r001-review-comment.md
-> worktrack-r001.yaml

worktrack-r001.yaml
-> worktrack-r002-review-comment.md
-> worktrack-r002.yaml
```

The next Review comment has frontmatter containing only `worktrack_id`,
`reviewed_round`, and `next_round`. For example, the comment after R000 identifies
`reviewed_round: R000` and `next_round: R001`.

1. Read the immutable initial requirement, R000, every completed later
   review-comment/YAML pair, and the comment for the latest rejected round in
   numeric order.
2. Derive the next index as the rejected round plus one. Require the comment
   filename, Worktrack identity, `reviewed_round`, and `next_round` to match that
   relationship before creating the next YAML.
3. If the next YAML exists or the chain is missing, gapped, duplicated, or
   identity-mismatched, block; never overwrite or skip an index.
4. Confirm the established Worktrack branch and require `HEAD` to equal the
   rejected round commit. Redo does not recreate or repair the branch.
5. Before implementation mutation, create the next lowercase YAML with Worktrack
   identity, prior round/comment, blocking findings, acceptance checks and
   validation to rerun, unchanged authority/write surface, start checkpoint,
   this round's plan, and `commit_sha: null`. Do not record carrier identity.
6. Read back identity, previous-round relation, comment ref, and checkpoint.
7. Re-plan and work inside the immutable mission, then run affected validation
   and the same round finalization.

Review findings that show implementation misses existing acceptance use redo.
Mission-preserving Programmer clarification may be represented in the temporary
chain. Objective, acceptance, scope, write-surface, or approval expansion returns
upward and never mutates `initial-requirement.yaml`.

## Implementation Round Finalization

Only a successful, non-no-op round creates an implementation commit. Blocked,
approval-required, failed-validation, and genuine no-op rounds do not.

Before commit, confirm:

1. `HEAD` equals the round start checkpoint.
2. Affected validation succeeded against the current implementation.
3. Every non-ignored change is approved and every validation-only path is unchanged.
4. Only intended implementation changes are staged; `.servo/tmp` and the
   immutable requirement are not staged.
5. The index is non-empty and covers all intended round changes.
6. No non-ignored unstaged or untracked implementation file remains.
7. A final immediate HEAD check still matches the start checkpoint.
8. `expected_tree` records the final staged index tree.

Any failure stops before commit. An implementation round never uses
`--allow-empty`, amend, reset, repair, or history rewrite.

Create exactly one local commit, then confirm HEAD, its sole parent, its tree,
the complete approved path delta including both rename sides, and clean
non-ignored worktree/index. Only then write the full commit SHA into the current
round YAML and read back `worktrack_id`, `round_id`, and SHA. A failed YAML update
may retry against the same confirmed commit but creates no new round or commit.

## Stops

- source/runtime/artifact mutation or commit without explicit authority
- branch/checkpoint mismatch, existing normal-entry branch or target file,
  ambiguous Git visibility, failed readback, or unexpected changes
- validation failure, empty implementation delta, changed validation-only path,
  or incomplete staging
- malformed runtime chain or existing next-round target
- objective, acceptance, scope, mutation, or approval expansion
- request to Review, Close, merge beyond authority, activate a route, release,
  deploy/apply, modify remote state, or rewrite the Goal Charter

## Output

- `signal`: `review_requested | blocked | approval_required`
- `summary`
- `evidence_refs`, including the immutable requirement, current round YAML, and
  confirmed checkpoints when Review is requested
- conditional `request`

The output does not contain a Review decision, Gate verdict, close result, or
Repo Refresh result.
