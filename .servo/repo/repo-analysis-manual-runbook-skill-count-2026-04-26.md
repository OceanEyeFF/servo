---
title: "Repo Analysis Manual Runbook Skill Count"
artifact_type: "repo-analysis"
generated_from: "repo-whats-next-skill"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Analysis Manual Runbook Skill Count

## Control Signal

- analysis_status: fresh
- baseline_branch: develop-aw
- baseline_ref: 3daac1b98b12019354b994342e11158838465ddc
- facts:
  - Current `agents` adapter payload source contains 17 skill directories.
  - `adapter_deploy.py diagnose --backend agents --json` reported `binding_count: 17` and `managed_install_count: 17` on the current baseline.
  - `docs/project-maintenance/deploy/codex-harness-manual-runbook.md` still states that the current `agents` install contains 16 skills.
  - Existing governance checks do not currently catch this runbook count drift.
- inferences:
  - The runbook is stale relative to the verified deploy payload set.
  - A narrow docs plus semantic-governance check is enough to prevent this specific drift from recurring.
- unknowns:
  - Whether future backend counts should be documented as dynamic rather than numeric.
- current_main_contradiction: deploy payload count is machine-verifiable, but a manual runbook still carries a stale hard-coded count.
- main_aspect: missing semantic drift check, not missing deploy behavior.
- current_highest_priority: synchronize the manual runbook skill count and add a semantic governance check that derives the expected count from adapter payload source.
- long_term_highest_priority: keep operator-facing deploy/runbook claims mechanically tied to canonical payload source.
- do_not_do_now:
  - Do not change adapter deploy behavior.
  - Do not add new backend support.
  - Do not start package or npm/npx work in this slice.
- recommended_repo_action: enter-worktrack
- recommended_next_route: init-worktrack-skill
- suggested_node_type: test
- continuation_ready: true
- continuation_blockers: N/A
- writeback_eligibility: runbook correction and governance check are eligible for docs/toolchain writeback after gate.
