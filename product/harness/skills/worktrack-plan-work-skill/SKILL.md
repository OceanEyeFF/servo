---
name: worktrack-plan-work-skill
description: 当已批准的 Worktrack 需要在一次调用中完成 setup synthesis、Plan、Work、affected validation 和单轮提交，或消费 Review comment 执行 redo 时，使用这个技能。
---

# Worktrack Plan and Work Skill

## Role

This Skill owns the candidate Worktrack execution round. A normal invocation carries setup synthesis, Plan, Work, affected validation, and round finalization to `review_requested`, `blocked`, or `approval_required`. A redo invocation repeats that work inside the unchanged Worktrack authority.

It is self-contained and does not require `docs/harness/` or `docs/project-maintenance/` pre-reading. It does not invoke Review or Close, spawn a descendant SubAgent, judge technical acceptance, or change upper-layer lifecycle state.

## Authority

Normal entry receives:

- `worktrack_id`
- Milestone contribution: objective, acceptance checks, scope, constraints, branch source, and close target
- accepted mutation and approval boundaries
- affected validation requirements
- deterministic `worktrack_setup_check.py` result
- current implementation checkpoint

The contribution must provide a concrete `branch_source.branch`, full
`branch_source.checkpoint`, and `close_target`. The setup result must provide the
derived `expected_branch`; it is evidence for PlanWork to act on, not an action
performed by the checker.

Redo entry receives:

- the accepted Worktrack Contract reference
- the complete existing lowercase round chain
- the latest expected Review comment
- unchanged mutation, approval, and validation boundaries
- current implementation checkpoint

Missing, stale, contradictory, or expanded authority stops before mutation. Setup checker output is legality evidence only; the checker never creates a branch, artifact, plan, round file, or commit.

## Serialized Runtime Model

- The upper Orchestrator dispatches one Worktrack role at a time.
- At most one PlanWork carrier writes round YAML files.
- PlanWork and Review return to the Orchestrator and never invoke each other.
- `.servo/tmp/<worktrack-id>/` is ignored temporary handoff, not project truth or a fixed `.servo/worktrack` artifact.
- Unexpected concurrency, an existing derived target, or unavailable shared workspace blocks. This Skill does not add locks, replay, recovery, or multi-writer coordination.

All runtime filenames are lowercase ASCII. YAML `round_id` values use uppercase `RNNN`.

## Normal Round

1. Validate setup legality, authority, mutation boundary, and validation requirements while still on `branch_source.branch`.
2. Require `can_setup: true`, no setup approval stop, a concrete derived `expected_branch`, and a clean non-ignored worktree and index.
3. Confirm the current branch equals `branch_source.branch` and `HEAD` equals the full `branch_source.checkpoint`. Recheck HEAD immediately before branch creation.
4. Require `expected_branch` to be absent. An existing branch blocks and returns upward for an explicit recovery decision; normal entry does not infer resume authority or repair it.
5. Create and switch to `expected_branch` from the exact source checkpoint. Read back the current branch and HEAD, and require them to equal `expected_branch` and `branch_source.checkpoint`.
6. If branch creation, switch, or readback fails, return `blocked` before creating R000 or making any implementation change. The setup checker, Review, Close, and upper Orchestrator do not create or repair this branch.
7. Derive `.servo/tmp/<worktrack-id>/worktrack-r000.yaml` with `round_id: R000`. If it already exists, stop as blocked; never overwrite it.
8. Before implementation mutation, create R000 with:
   - Worktrack identity, `round_id: R000`, initial task, and objective;
   - acceptance checks;
   - included/excluded scope and the approved write surface;
   - constraints and approval boundaries;
   - source branch, source checkpoint, current start checkpoint, and expected Worktrack branch;
   - close target and the concrete plan for this round;
   - `commit_sha: null` until confirmed finalization.
9. Read back Worktrack identity, round identity, start checkpoint, and expected branch.
10. Plan and perform only approved Work.
11. Run affected validation against the implementation to be finalized.
12. Execute the round finalization contract below.

## Redo Round

1. Read R000 and every later review-comment/YAML pair in numeric order.
2. Require a contiguous completed chain and a Review comment for the latest rejected round.
3. Derive the next round as `max(complete round number) + 1`.
4. If the derived YAML exists, or the chain is missing/gapped, stop as blocked; never overwrite or skip an index.
5. Confirm the current branch is the established Worktrack branch and `HEAD` equals the rejected round commit used as this round's start checkpoint. Redo validates this existing-branch premise; it does not recreate or repair the branch.
6. Create the matching lowercase YAML before mutation. Record:
   - Worktrack identity, derived round ID, previous round, and Review comment ref;
   - blocking findings and the acceptance checks/validation to rerun;
   - unchanged Worktrack authority/contract ref and approved write surface;
   - current start checkpoint and the concrete plan for this round;
   - `commit_sha: null` until confirmed finalization.
7. Read back the round identity, previous-round relation, Review comment ref, and start checkpoint.
8. Re-plan inside the unchanged objective, acceptance, scope, mutation, and approval boundaries.
9. Perform Work, affected validation, and the same finalization used by a normal round.

Queue recomposition inside existing authority is ordinary redo planning. Objective, acceptance, scope, write-surface, or approval expansion returns upward; redo is the only Review handback entry.

## Round Finalization

Only a successful, non-no-op round creates an implementation commit. Blocked, approval-required, failed-validation, and genuine no-op rounds do not.

Before commit, PlanWork must confirm:

1. `HEAD` equals the round start checkpoint.
2. Affected validation succeeded against the current implementation.
3. Every non-ignored change is approved and every validation-only path is unchanged.
4. Only intended implementation changes are staged; `.servo/tmp` is not staged.
5. The index is nonempty and covers all intended round changes.
6. No non-ignored unstaged or untracked implementation file remains.
7. A final immediate HEAD check still matches the start checkpoint.
8. `expected_tree` records the final staged index tree.

Any failure stops before commit. Do not create a partial, empty, amend, reset, repair, or history-rewrite commit.

Create exactly one local commit, then confirm:

- `HEAD` is the captured round commit;
- its only parent is the round start checkpoint;
- its tree equals `expected_tree`;
- its complete path delta remains in the approved surface, including both sides of a rename;
- the non-ignored worktree and index are clean.

Only after confirmation, supplement the current round YAML with the full commit SHA. Do not intentionally rewrite other fields. Read back `worktrack_id`, `round_id`, and the full SHA. A failed write/readback remains inside finalization and may retry only this update against the same confirmed commit; it creates no second round or commit.

The first approved reconciliation round uses R000 and the same transaction. Its only special premise is that the accumulated preexisting dirty set must exactly equal the separately approved mutation/addition/deletion surfaces before staging.

## Stops

- source mutation, deletion, runtime round, or commit without explicit authority
- branch/checkpoint mismatch, an existing normal-entry target branch, branch creation/switch/readback failure, validation failure, or out-of-surface change
- changed validation-only path or incomplete staging
- malformed/incomplete round chain or existing derived round target
- scope/objective/acceptance expansion
- request to Review, Close, merge, activate a default route, release, deploy, modify remote state, or rewrite the Goal Charter

## Output

- `signal`: `review_requested | blocked | approval_required`
- `summary`
- `evidence_refs`, including the current round YAML and confirmed commit when Review is requested
- conditional `request` for blocked or approval-required results

The output does not contain a Review recommendation, Gate verdict, closeout record, or Repo Refresh result.
