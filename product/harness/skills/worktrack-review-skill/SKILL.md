---
name: worktrack-review-skill
description: 当 PlanWork 已完成一个 Worktrack round，需要由独立只读载体核查完整 round chain、实现、验收和验证，并决定 ready_to_close 或 redo 时，使用这个技能。
---

# Worktrack Review Skill

## Role

This Skill owns technical acceptance for the candidate Worktrack. It is implementation-read-only and runs independently from the PlanWork carrier. It does not implement findings, approve authority expansion, perform Close, issue a legacy Gate verdict, or decide whether the Milestone as a whole is complete.

It is self-contained and does not require source-repo docs. Its only write capability is one next-round Review comment under the current Worktrack's `.servo/tmp` directory when redo is required.

## Required Input

- `worktrack_id`
- accepted Worktrack Contract or initial Milestone contribution authority
- `.servo/tmp/<worktrack-id>/worktrack-r000.yaml`
- every later lowercase review-comment/YAML pair in numeric order
- current implementation checkpoint and diff
- affected validation and evidence refs
- mutation and approval boundaries
- concrete PlanWork and independent Review carrier provenance

Missing R000, a gapped pair, stale commit/evidence, or unproven independence is non-pass.

## Complete Chain

Review reads:

1. R000 as the initial objective, acceptance, scope, constraints, and first implementation checkpoint.
2. For each rejected round, the matching next-round review comment.
3. The YAML created from that comment.
4. The current implementation and validation evidence referenced by the latest YAML.

The chain begins at R000 and is contiguous. Runtime filenames are lowercase; internal `round_id` values are `RNNN`.

The Review LLM owns semantic judgment. It combines initial acceptance with later correction requirements and applies the latest relevant correction when work instructions conflict. A later comment or YAML cannot expand objective, acceptance authority, scope, mutation surface, or approval. Apparent expansion blocks and returns upward.

## Review Work

1. Identify the actual implementation/artifact changes from Git and evidence.
2. Confirm the latest round commit matches the implementation checkpoint being reviewed.
3. Judge the objective and every applicable acceptance condition against the complete chain.
4. Check scope, constraints, implementation quality, behavior preservation, and approval boundaries.
5. Assess whether affected validation is appropriate and fresh.
6. Separate blockers from accepted residuals and independently scoped follow-up test needs.
7. Produce exactly one local signal.

## Signals

- `ready_to_close`: no blocker remains; includes acceptance evidence refs and optional accepted residuals. Review writes no runtime file on pass.
- `redo`: current authority can correct the work. Review writes exactly one next expected lowercase `worktrack-rNNN-review-comment.md`.
- `blocked`: repair requires missing evidence, an external dependency, an independent Test Worktrack, or upper-level authority/scope judgment.

Queue changes inside unchanged authority are handled by the next PlanWork redo; Review exposes no second planning route.

## Review Comment

For redo, the comment states:

- the prior round reviewed;
- blocking findings and why acceptance failed;
- checks and validations to rerun;
- evidence refs;
- what the next PlanWork round must address;
- any issue that appears to require upper-level approval.

Review is the only writer of that comment. It never writes implementation, round YAML, canonical docs, control state, Close evidence, or closeout records. If the expected comment already exists, stop as blocked rather than overwrite or skip an index.

## Validation Boundary

- Static or mock evidence cannot replace runtime proof when acceptance requires behavior.
- Complex independent proof may block and recommend a separately approved Test Worktrack.
- Markdown phrase assertions do not prove that an LLM followed a Skill contract.
- Whole-Skill orchestration behavior remains proof/dogfood.

## Output

- `signal`: `ready_to_close | redo | blocked`
- `summary`
- `findings`
- `evidence_refs`
- conditional `review_comment_ref` for redo
- conditional `residuals` or `follow_up_test_worktrack_brief`

This output returns to the upper Orchestrator. Review does not invoke PlanWork or Close and does not write upper lifecycle state.
