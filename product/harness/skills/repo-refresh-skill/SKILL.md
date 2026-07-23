---
name: repo-refresh-skill
description: 当 Candidate Worktrack 已完成机械 Close，需要把 finished handback 写回 Repo backlog 并刷新对应 Repo 控制事实时，使用这个技能。
---

# Repo Refresh Skill

## Role

This Skill is the RepoScope consumer of a completed Candidate Worktrack. It
records the Close-owned result and refreshes Repo control facts. The resulting
backlog entry is the only Worktrack completion truth consumed by Milestone
Status. This Skill
does not reopen Worktrack execution, repeat Review, or audit the Close Git
transaction.

Candidate completion has one ingress. Missing or malformed input blocks.

## Candidate Input

The upper Harness supplies a structured Close result:

```yaml
worktrack_close_result:
  worktrack_id: string
  outcome: completed
  finished_handback_ref: string
  closeout_checkpoint_commit: string
  repo_refresh_handoff: object
  evidence_refs: [string]
```

The referenced `finished-handback.yaml` is the sole persistent Worktrack
completion handoff. It carries the Milestone id, `accepted_checkpoint`,
acceptance summary, residuals, merge result, pre-finalization
`closeout_checkpoint`, and stable evidence refs. The structured Close result
carries the final `closeout_checkpoint_commit`.

## Minimal Consumer Checks

Before writeback:

1. Parse the Close result and resolve `finished_handback_ref`.
2. Require non-placeholder `worktrack_id`, `finished_handback_ref`,
   `closeout_checkpoint_commit`, `repo_refresh_handoff`, and `evidence_refs`.
3. Require result and handback Worktrack ids to match.
4. Require a concrete handback `milestone_id`; require it to match the
   Candidate writeback instruction and the Worktrack's existing registered
   Milestone owner.
5. Require the selected Worktrack backlog entry to identify that exact
   Worktrack and its existing registered Milestone owner.
6. Reject any `repo_refresh_handoff` field that attempts to supply or override
   Worktrack identity, Milestone identity, backlog ownership, target files,
   field paths, or write operations.
7. Require `outcome: completed` in both the result and handback.
8. Require all referenced persistent evidence to be resolvable. Stable evidence
   must not consist only of `.servo/tmp/` paths.

Failure blocks Repo Refresh; no alternate ingress is inferred.

These checks establish that the Close result is consumable. They do not replay
Git parent/tree/path checks, recompute merge correctness, re-run Worktrack
Review, or reinterpret acceptance and residuals.

## Candidate Write Capability Boundary

`repo_refresh_handoff` carries values to record; it is not write authority.
Candidate completion permits exactly two capabilities:

1. Upsert the current `worktrack_id` entry in
   `.servo/repo/worktrack-backlog.md` to `status: done`, with the accepted
   handback, checkpoint, merge, residual, evidence, and Refresh facts.
2. Refresh only Repo snapshot/control pointers directly associated with this
   completed handback.

Every other target or operation is blocked. Candidate completion cannot write
Milestone Gate verdicts, axis reports/findings, Milestone history, another
Worktrack backlog entry, any Milestone contribution state, or another Worktrack completion artifact.
It cannot use paths or operations embedded in the handoff to expand this
boundary.

## Writeback

After the minimal checks pass:

1. Ask `repo-writeback-skill` to run the Candidate completion transaction.
2. Pass the identity facts already checked above; the handoff cannot replace
   the registered `milestone_id` or select a different backlog entry.
3. Upsert `.servo/repo/worktrack-backlog.md` for `worktrack_id` with:
   - `status: done`;
   - Milestone id and node type when present;
   - `finished_handback_ref`;
   - `accepted_checkpoint` and `closeout_checkpoint_commit`;
   - merge result, residual summary, and stable evidence refs;
   - Repo Refresh handoff.
4. Refresh only the Repo snapshot/control pointers allowed by the Candidate
   capability boundary.
5. Return the concrete writeback result to the upper Harness.

Repo Refresh is not an additional Worktrack stage. It is the RepoScope
writeback consumer after Close.

## Output

```yaml
repo_refresh_result:
  outcome: completed | blocked
  worktrack_id: string
  finished_handback_ref: string | null
  closeout_checkpoint_commit: string | null
  backlog_updated: boolean
  milestone_contribution_exposed: boolean
  repo_refresh_handoff: object | null
  evidence_refs: [string]
  blockers: [string]
```

`completed` requires successful readback of every declared write target.
`blocked` preserves the original Close result and reports the exact missing or
invalid input; it does not synthesize completion.

`milestone_contribution_exposed` means the completed backlog entry now contains
the concrete ownership and handback facts that Harness can compare with the
canonical Milestone TodoList before any separately authorized result_ref
registration. It does not mean Repo Refresh wrote contribution state to the
Milestone document.

## Boundaries

- Do not modify `initial-requirement.yaml`, `finished-handback.yaml`, or
  `.servo/tmp/<worktrack-id>/`.
- Do not perform technical Review, acceptance judgment, merge verification, or
  CloseOut transaction repair.
- Do not dispatch Milestone axis carriers. The upper Harness directly reads the
  canonical TodoList and accepted stable refs, prepares common facts, and owns
  sibling dispatch.
- Do not create a second Worktrack completion authority.
- Do not modify Milestone final status/acceptance, `purpose_achieved`, Gate or
  axis evidence, Milestone history, or any Milestone contribution state.
- Do not infer values from current branch names or prose summaries.

## Resources

Use the structured Close result, its `finished_handback_ref`, and current Repo,
Worktrack ownership, and Milestone control references. The fixed Candidate
capability boundary selects the write targets; `repo_refresh_handoff` supplies
recorded values only. Harness may later accept and register the stable result
through a separate Milestone transaction; Repo Refresh does not write it or
derive canonical completion. This Skill has no runtime dependency on
source-repo Harness documentation.
