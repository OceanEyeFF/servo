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

1. Validate setup legality, authority, branch/checkpoint, mutation boundary, and validation requirements.
2. Derive `.servo/tmp/<worktrack-id>/worktrack-r000.yaml` with `round_id: R000`.
3. If R000 already exists, stop as blocked; never overwrite it.
4. Create R000 before implementation mutation. Record the initial task, acceptance conditions, scope/constraints, start checkpoint, and the round plan.
5. Read back Worktrack identity, round identity, and start checkpoint.
6. Plan and perform only approved Work.
7. Run affected validation against the implementation to be finalized.
8. Execute the round finalization contract below.

## Redo Round

1. Read R000 and every later review-comment/YAML pair in numeric order.
2. Require a contiguous completed chain and a Review comment for the latest rejected round.
3. Derive the next round as `max(complete round number) + 1`.
4. If the derived YAML exists, or the chain is missing/gapped, stop as blocked; never overwrite or skip an index.
5. Create the matching lowercase YAML before mutation. Record the previous round, Review comment ref, blocking findings, checks to rerun, start checkpoint, and new round plan.
6. Re-plan inside the unchanged objective, acceptance, scope, mutation, and approval boundaries.
7. Perform Work, affected validation, and the same finalization used by a normal round.

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
- branch/checkpoint mismatch, validation failure, or out-of-surface change
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
