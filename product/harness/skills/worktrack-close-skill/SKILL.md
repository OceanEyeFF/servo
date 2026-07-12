---
name: worktrack-close-skill
description: 当上层 Orchestrator 已确认 Worktrack 处于 ready_to_close，需要执行 freshness、approval、merge-or-no-merge、closeout/writeback 和 Repo Refresh 交接时，使用这个技能。
---

# Worktrack Close Skill

## Role

This Skill performs mechanical Close for the candidate Worktrack aggregate. It does not consume a raw Review recommendation, normalize candidate/legacy authority fields, read every round to re-judge acceptance, issue a Gate verdict, or decide whether the Milestone purpose is complete.

It is self-contained and runs only after the upper Orchestrator has accepted a fresh independent Review signal and marked the Worktrack `ready_to_close`.

## Inputs

- `worktrack_id` and accepted Worktrack reference
- current lifecycle state, which must be `ready_to_close`
- accepted implementation checkpoint and acceptance evidence refs
- current implementation checkpoint
- close target and branch facts
- approval, merge/no-merge, and protected-branch legality facts
- closeout/writeback and Repo Refresh handoff targets

Candidate Close does not accept `review_recommendation`, `authority_kind`, `authority_value`, `authority_ref`, `residual_acceptance_ref`, `close_entry_mode`, or a candidate/legacy selector.

The still-default legacy route remains outside this candidate ingress and continues to use its exact legacy Gate contract until the separately approved orchestration activation and retirement work. Candidate malformed input never falls back to legacy through field inference.

## Mechanical Close

1. Require lifecycle state `ready_to_close`.
2. Confirm the accepted checkpoint equals the current implementation checkpoint.
3. Confirm acceptance evidence, approval, branch source, close target, and merge/no-merge authority are concrete and fresh.
4. Reject placeholders, post-Review implementation changes, branch mismatch, or missing authority.
5. Perform only the approved no-merge closeout, merge handoff, or merge action.
6. Write closeout and control/backlog facts through the repository writeback path.
7. Return a bounded Repo Refresh handoff.

Close does not run Self-Review, Single-Acceptance, Closeout Gate, composite technical lanes, implementation Review, or validation. A freshness failure returns to Review/PlanWork through the upper Orchestrator.

## Mechanical Legality

- Worktrack state must be `ready_to_close`.
- Acceptance and implementation checkpoints must match.
- Merge, protected-branch mutation, cleanup, release, deploy, remote side effects, and destructive actions require separate authority.
- A no-merge/report-only Worktrack closes only when its accepted close target permits it.
- Close cannot repair, promote, or reinterpret technical acceptance.

## Output

- `outcome`: `closed | blocked | approval_required`
- `summary`
- `closeout_ref` and `repo_refresh_handoff_ref` only when closed
- `evidence_refs`
- conditional `request`

The closeout record preserves Worktrack/branch/checkpoint facts, merge-or-no-merge result, accepted evidence refs, `files_changed`, docs/backlog state, cleanup state, `remaining_risks`, and the next Repo action. Technical Review remains at its original evidence refs.

This Skill stops after mechanical close and handoff. It does not run Repo Refresh or start another Worktrack.
