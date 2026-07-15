---
name: worktrack-review-skill
description: 当 Candidate PlanWork 完成一个 round，需要由独立只读载体读取 immutable initial requirement、完整 round chain、实现和验证，并决定 ready_to_close 或 redo 时，使用这个技能。
---

# Worktrack Review Skill

## Role

This Skill owns technical acceptance for the Candidate Worktrack. It is
implementation-read-only and runs independently from the PlanWork carrier. It
does not implement findings, approve authority expansion, perform Close, issue a
legacy Gate verdict, or decide whether the Milestone is complete.

The upper Orchestrator selects and enforces the independent Review carrier before
dispatch. Carrier identity or provenance is not Review task input or output.
Programmer or Human Review observations may be supplied as evidence, but Review
independently checks and synthesizes them rather than treating them as a verdict.

It is self-contained and requires no source-repo docs. Its only write capability
is exactly one next-round Review comment under the current Worktrack's
`.servo/tmp` directory when redo is required.

## Required Input

- `worktrack_id`
- immutable
  `.servo/worktrack/<worktrack-id>/initial-requirement.yaml`
- `.servo/tmp/<worktrack-id>/worktrack-r000.yaml`
- every later lowercase review-comment/YAML pair in numeric order
- latest implementation checkpoint and Git diff
- fresh affected validation and evidence refs
- mutation and approval boundaries
- optional identity-free Human Review observations, either inline in the current
  invocation payload or through an opaque temporary payload ref under
  `.servo/tmp/<worktrack-id>/`

Missing or mutable initial authority, missing R000, a gapped chain, stale
checkpoint, or stale evidence is non-pass.

## Authority And Complete Chain

The immutable initial requirement is the original mission owner. Review checks
its Worktrack/Milestone identity, objective, every acceptance check, included and
excluded scope, approved write surface, constraints, branch source, and close
target.

Review then reads:

1. R000, whose start checkpoint is the confirmed Initial Entry commit.
2. For every rejected round, the matching next-round Review comment.
3. The YAML created from that comment.
4. Each referenced implementation commit/diff and affected validation.
5. The latest implementation and validation evidence referenced by the last YAML.

The chain is contiguous from R000. Runtime filenames are lowercase and internal
round IDs use `RNNN`. Review never treats a later runtime record as permission to
rewrite the immutable initial requirement.

The comment and YAML for a redo both use the next round index:

```text
worktrack-r000.yaml
-> worktrack-r001-review-comment.md
-> worktrack-r001.yaml

worktrack-r001.yaml
-> worktrack-r002-review-comment.md
-> worktrack-r002.yaml
```

The Review LLM owns semantic judgment. It applies the latest relevant
mission-preserving clarification or execution constraint when instructions
conflict. A later comment/YAML cannot reduce acceptance, replace the objective,
expand scope/write surface, or grant approval. Apparent mission change blocks for
Repo/Milestone and Programmer judgment.

Human observations are checked against the immutable mission, the complete
chain, and implementation facts. They may identify findings or clarify existing
acceptance, but they cannot approve objective, scope, write-surface, or
acceptance expansion. Mission-changing Human input produces `blocked` with an
upper approval request. Review records no Human, LLM, PlanWork, or Review carrier
identity and does not persist the raw observations as a fixed artifact.

## Review Work

1. Identify actual implementation and artifact changes from Git and evidence.
2. Confirm the latest round commit equals the implementation checkpoint under review.
3. Verify any Human observations against implementation facts and the unchanged authority.
4. Judge the original objective and every acceptance check against the complete chain.
5. Check scope, constraints, implementation quality, behavior preservation, and
   approval boundaries.
6. Assess whether affected validation is appropriate and fresh.
7. Separate blocking findings from accepted residuals and independently scoped
   follow-up-test needs.
8. Produce exactly one canonical signal.

## Signals

### `ready_to_close`

No blocker remains. Review writes no pass artifact. The result includes:

- `accepted_checkpoint`
- `acceptance_summary`, with every initial acceptance check exactly once
- `evidence_refs`
- optional concrete `residuals`

Stable evidence cannot consist only of `.servo/tmp` refs. A plain pass has no
residuals; accepted residuals require concrete evidence and cannot hide an unmet
acceptance condition or mission change.

### `redo`

The unchanged authority can correct the work. Review creates exactly one next
expected lowercase `worktrack-rNNN-review-comment.md`, containing:

```yaml
---
worktrack_id: <worktrack-id>
reviewed_round: R000
next_round: R001
---
```

The filename uses `next_round`. Its frontmatter contains only those three fields;
it records no Human, LLM, PlanWork, or Review carrier identity. The body contains:

- prior round reviewed
- blocking findings and why acceptance failed
- acceptance checks and validation to rerun
- evidence refs
- what the next PlanWork round must address
- any issue that appears to require upper approval

Review is the only writer of this comment. If the target exists, block rather
than overwrite or skip an index. The filename, `reviewed_round`, and `next_round`
must form the same contiguous relationship before Review returns `redo`.
Raw Human observations never occupy a canonical round filename; Review verifies
and rewrites applicable findings into its own comment.

### `blocked`

Repair requires missing stable evidence, an external dependency, an independent
Test Worktrack, unavailable shared state, or upper objective/scope/approval
judgment. Review does not convert those conditions into redo authority.

## Write Boundary

Review never writes implementation, the immutable requirement, round YAML,
canonical source/docs, control state, Gate evidence, finished handback, or legacy
closeout artifacts. It does not invoke PlanWork or Close and does not write upper
lifecycle state. It does not create a pass artifact or a persistent Human Review
report.

## Validation Boundary

- Static or mock evidence cannot replace runtime proof when acceptance requires behavior.
- Complex independent proof may block and recommend a separately approved Test Worktrack.
- Markdown phrase assertions do not prove LLM contract adherence.
- Whole-Skill orchestration behavior is accepted by later end-to-end validation.

## Output

- `signal`: `ready_to_close | redo | blocked`
- `summary`
- `findings`
- `evidence_refs`
- conditional `accepted_checkpoint`, `acceptance_summary`, and `residuals` for
  `ready_to_close`
- conditional `review_comment_ref` for `redo`
- conditional `request` or `follow_up_test_worktrack_brief` for `blocked`

The output returns to the upper Orchestrator. Only the Orchestrator changes the
Worktrack aggregate to `ready_to_close` or dispatches the next redo.
