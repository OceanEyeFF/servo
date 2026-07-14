---
name: worktrack-close-skill
description: 当上层 Orchestrator 已确认 Candidate Worktrack 处于 ready_to_close，需要执行 freshness、approval、合回原 active Milestone branch、finished handback 和 Repo Refresh 交接时，使用这个技能。
---

# Worktrack Close Skill

## Role

This Skill performs mechanical Close for the Candidate Worktrack aggregate. It
runs only after the upper Orchestrator accepts a fresh independent Review result
and marks the Worktrack `ready_to_close`.

Close does not consume a raw Review recommendation, normalize ingress
authority, re-judge acceptance, issue a Gate verdict, or decide Milestone
completion. It is self-contained and requires no source-repo docs.

## Inputs

- `worktrack_id` and `milestone_id`
- immutable initial requirement ref and readable content
- current lifecycle state, exactly `ready_to_close`
- accepted implementation checkpoint and acceptance summary/evidence refs
- current implementation checkpoint
- accepted residuals and stable evidence refs
- complete runtime round chain for counts and approved human adjustments
- Worktrack source branch and concrete close target branch
- approval, merge, and protected-branch legality facts
- Repo Refresh handoff target

The accepted implementation checkpoint and current implementation checkpoint
must be equal. Candidate Close does not accept `review_recommendation`, legacy
Gate authority fields, `close_entry_mode`, or any ingress selector.

## Mechanical Preconditions

- Worktrack state is `ready_to_close`.
- The initial requirement is present, create-only, readable, and matches the
  Worktrack identity.
- Acceptance covers every initial check exactly once and is fresh for the current
  implementation checkpoint.
- Residuals are concrete and already accepted by independent Review.
- Approval and branch facts are concrete. The close target equals the immutable
  requirement's `branch_source.branch`.
- Stable evidence does not consist only of `.servo/tmp` refs.
- No post-Review implementation change, mission-changing deviation, placeholder,
  branch mismatch, or unapproved Git change exists.

Failure returns `blocked` or `approval_required`; Close cannot repair, promote,
or reinterpret technical acceptance.

## Finished Handback

Close is the only producer of:

```text
.servo/worktrack/<worktrack-id>/finished-handback.yaml
```

The create-only handback contains:

```yaml
worktrack_id: string
milestone_id: string
outcome: completed
summary: string
initial_requirement_ref: string
accepted_checkpoint: string
closeout_checkpoint: string
acceptance_summary:
  - check_id: string
    status: pass | pass_with_residuals
    summary: string
    evidence_refs: [string]
initial_to_final_deviation:
  classification: none | clarification | execution_constraint_adjustment
  summary: string
  decision_refs: [string]
round_count: integer
redo_count: integer
human_adjustment_count: integer
human_adjustments:
  - round_id: string
    summary: string
    decision_ref: string
residuals:
  - residual_id: string
    summary: string
    evidence_refs: [string]
evidence_refs: [string]
merge_result:
  source_branch: string
  target_branch: string
  integration_checkpoint: string
repo_refresh_handoff:
  target_scope: RepoScope.Refresh
  target_branch: string
  required_updates: [string]
finished_at: string
created_by: string
```

`outcome` is only `completed`. Every initial acceptance check appears once.
Counts match the contiguous runtime chain. Human adjustments are limited to
mission-preserving clarifications or approved execution constraints. A major
objective, acceptance, or scope deviation prevents Close.

`evidence_refs` are unique, concrete, stable, and non-placeholder. Close copies
the minimum accepted technical result; it does not preserve Review prompts,
carrier identity, signatures, or the comment chain as a persistent audit system.

## Close Transaction

1. Confirm all mechanical preconditions, the Worktrack source branch, and the
   concrete target equal to the original active Milestone branch.
2. Merge the Worktrack branch into that Milestone branch under the approved
   branch and protected-branch authority.
3. Capture the resulting target HEAD as the pre-finalization
   `closeout_checkpoint`.
4. Read the immutable requirement, accepted Review result, and complete runtime
   chain only to copy accepted facts and calculate round/redo/human-adjustment
   counts. Do not produce a second technical judgment.
5. Require `finished-handback.yaml` to be absent. Create it once on the resolved
   close target and read back identity, accepted checkpoint, acceptance coverage,
   counts, merge result, and Repo Refresh handoff.
6. Classify Git visibility fail closed:
   - Git-visible mode requires exactly the expected handback change.
   - Git-ignored mode requires file existence/readback plus direct
     `git check-ignore` proof and no other unapproved change.
   - Missing content, overwrite, failed readback, ambiguous invisibility, or
     unexpected changes block.
7. In visible mode, stage only the handback and create one file-bearing CloseOut
   commit. In proven-ignored mode, do not use `git add -f` or change `.gitignore`;
   create one `git commit --allow-empty` CloseOut marker.
8. Confirm the final commit's only parent is `closeout_checkpoint`. The visible
   delta contains only the handback; the marker tree equals its parent. Require a
   clean index and non-ignored worktree.
9. Only after commit confirmation return `completed` with the final checkpoint
   commit and Repo Refresh handoff.

If finalization fails after creating the handback, Close may remove only its own
uncommitted handback attempt before returning blocked. It does not remove a
pre-existing file, rewrite a committed handback, or start generalized recovery.

The handback embeds the pre-finalization `closeout_checkpoint`; the later final
commit SHA is returned externally because a file cannot contain the SHA of the
commit that may contain it. An empty marker records only the lifecycle
checkpoint and does not claim cross-clone durability for ignored content.

## Technical And Legacy Exclusions

Close does not run Self-Review, Single-Acceptance, Closeout Gate, composite
technical lanes, implementation Review, or validation. It creates no legacy
Worktrack closeout Markdown, Gate artifact, or closeout-evidence bundle and does
not dual-write Candidate and legacy handoffs.

Legacy node policy may still use `merge/no-merge`, `merge_required: no`, or
`if_no_merge`; those are explicit exclusions outside Candidate Close and do not
create a Candidate no-merge mode.

Candidate output does not emit legacy `closeout_ref`,
`repo_refresh_handoff_ref`, `files_changed`, or `remaining_risks` fields. Those
names identify excluded legacy interfaces, not Candidate Close authority.
The upper Harness invokes this Skill only for the Candidate `ready_to_close`
route. The canonical path has no Candidate/legacy selector, legacy fallback, or
Gate-authority normalization for Close.

## Output

- `outcome`: `completed | blocked | approval_required`
- `summary`
- `finished_handback_ref` and `closeout_checkpoint_commit` only when completed
- `repo_refresh_handoff` only when completed
- `evidence_refs`
- conditional `request`

Blocked or approval-required Close creates no finished handback and advertises
no completion. This Skill stops after the mechanical handoff; it does not run
Repo Refresh, start another Worktrack, release, deploy/apply, mutate remote state,
or perform cleanup without separate authority.
