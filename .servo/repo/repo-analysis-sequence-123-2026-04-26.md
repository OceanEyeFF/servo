---
title: "Repo Analysis Sequence 1-2-3"
artifact_type: "repo-analysis"
generated_from: "harness-skill"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Analysis Sequence 1-2-3

## Control Signal

- analysis_status: fresh
- baseline_branch: develop-aw
- baseline_ref: a74b0fd892cf420c527953d95b54ec3f9cf85e2a
- facts:
  - Programmer confirmed the sequence: 1. Repo Analysis pilot consumption, 2. distribution productization, 3. Repo Analysis capability productization.
  - Repo Analysis artifact, runtime scaffold support, and Control State `repo_analysis` pointer are already merged.
  - `adapter_deploy.py` currently exposes `prune`, `check_paths_exist`, `install`, and `verify`.
  - Deploy runbook treats `verify` as a read-only auxiliary command and destructive reinstall as a three-step operator flow.
- inferences:
  - Sequence step 1 is complete enough to drive the next route.
  - Step 2 should start with a low-risk diagnostic/readiness surface before adding one-shot install/update behavior.
  - A read-only `diagnose` command is a productization-friendly bridge from internal verify logic to future reusable install/update/diagnostic entrypoints.
- unknowns:
  - Future packaging channel and CLI binary name.
  - Whether diagnostics should later become JSON-only or human-first with JSON option.
- current_main_contradiction: deploy functionality exists, but product-facing diagnostics are still spread across `verify` output and runbook prose.
- main_aspect: missing structured diagnostic command surface, not missing install mechanics.
- current_highest_priority: add a read-only deploy diagnostic command for the current `agents` backend.
- long_term_highest_priority: evolve deploy tooling into reusable install/update/verify/diagnose distribution entrypoints.
- do_not_do_now:
  - Do not implement npm/npx packaging in this first slice.
  - Do not collapse destructive reinstall into a one-shot mutating command yet.
  - Do not add `claude` or `opencode` backend support.
- recommended_repo_action: enter-worktrack
- recommended_next_route: init-worktrack-skill
- suggested_node_type: feature
- continuation_ready: true
- continuation_blockers: N/A
- writeback_eligibility: diagnostic command contract and verified behavior are eligible for docs/toolchain writeback after gate.

## Supporting Detail

This analysis consumes the completed Repo Analysis infrastructure and chooses a first distribution-productization slice. The preferred first slice is read-only because it improves operator/product ergonomics without changing install semantics or backend support scope.
