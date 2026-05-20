---
title: "Repo Analysis Contract Check Slice"
artifact_type: "repo-analysis"
generated_from: "repo-whats-next-skill"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Analysis Contract Check Slice

## Control Signal

- analysis_status: fresh
- baseline_branch: develop-aw
- baseline_ref: dcedef59531a4bae4ec2e6f54716df660178cde0
- facts:
  - Programmer approved the 1 -> 2 -> 3 sequence and automatic continuation budget.
  - `WT-20260426-deploy-diagnose-command` closed and merged at `dcedef5`.
  - `Repo Analysis` is now documented and scaffolded, but its required fields are enforced only by prose and partial scaffold tests.
  - `product/.servo_template/repo/analysis.md` and `product/harness/skills/set-harness-goal-skill/assets/repo/analysis.md` are the reusable template sources.
- inferences:
  - Continuing directly into heavier install/update distribution behavior would be a larger behavior change.
  - The safer next step in the approved sequence is Repo Analysis capability productization through a machine-checkable contract.
  - A focused contract checker is a validation-hardening slice, not a new planning subsystem.
- unknowns:
  - Whether future analysis artifacts should carry richer schemas or remain markdown-first.
  - Whether the checker should later validate live `.servo/repo/analysis.md` in closeout gates.
- current_main_contradiction: Repo Analysis is a first-class artifact in docs and templates, but its required fields are not yet enforced by reusable tooling.
- main_aspect: missing contract validation, not missing more analysis prose.
- current_highest_priority: add a lightweight Repo Analysis contract checker for template sources.
- long_term_highest_priority: make Repo Analysis generation and consumption repeatable enough to guide future worktracks without ad hoc reinterpretation.
- do_not_do_now:
  - Do not build a full schema engine.
  - Do not make `.servo/` runtime analysis a tracked source truth.
  - Do not alter `repo-whats-next-skill` routing semantics in this slice.
- recommended_repo_action: enter-worktrack
- recommended_next_route: init-worktrack-skill
- suggested_node_type: test
- continuation_ready: true
- continuation_blockers: N/A
- writeback_eligibility: checker behavior and documented verification entrypoint are eligible for docs/toolchain writeback after gate.

## Supporting Detail

This slice follows the approved `1 -> 2 -> 3` direction by shifting from the first distribution productization bridge back to Repo Analysis capability productization. The implementation should stay narrow: validate required Control Signal fields in canonical template sources, add unit coverage, and document the new check.
