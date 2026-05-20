---
title: "Repo Analysis Pilot"
artifact_type: "repo-analysis"
generated_from: "repo-whats-next-skill"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Analysis Pilot

## Control Signal

- analysis_status: fresh
- baseline_branch: develop-aw
- baseline_ref: 81d6a398a8c9114b66ef6a3ac705fed121305eca
- facts:
  - `Repo Analysis` is now documented at `docs/harness/artifact/repo/repo-analysis.md`.
  - `repo-whats-next-skill` can consume a fresh `Repo Analysis` artifact as optional structured input.
  - `.aw` scaffold template sources currently include `repo/snapshot-status.md` but not `repo/analysis.md`.
  - `set-harness-goal-skill` initialization assets currently include `repo/discovery-input.md` and `repo/snapshot-status.md` but not `repo/analysis.md`.
  - Current control state has 18 automatic budget units remaining.
- inferences:
  - The repo analysis contract is now true at the docs and skill-boundary layer, but not yet available in generated runtime `.servo/` state.
  - Without scaffold/init asset support, future repositories may not get a concrete repo analysis artifact even though RepoScope decision logic can consume one.
- unknowns:
  - Whether future packaging should expose repo analysis as a separate command.
  - Whether repo analysis should eventually have a machine-readable JSON form.
- current_main_contradiction: `Repo Analysis` has become a formal RepoScope artifact, but runtime initialization/scaffold paths do not yet generate it.
- main_aspect: missing template and generator support, not missing doctrine.
- current_highest_priority: add `repo/analysis.md` to `.aw` scaffold and `set-harness-goal` initialization assets with focused validation.
- long_term_highest_priority: make RepoScope analysis a reusable part of the Harness loop across initialized repositories.
- do_not_do_now:
  - Do not add a new repo-analysis skill.
  - Do not add a parser or scoring engine.
  - Do not start npx/package distribution before runtime artifact support exists.
- recommended_repo_action: enter-worktrack
- recommended_next_route: init-worktrack-skill
- suggested_node_type: feature
- continuation_ready: true
- continuation_blockers: N/A
- writeback_eligibility: pilot conclusion is eligible to initialize a bounded implementation worktrack; external packaging claims remain ineligible.

## Supporting Detail

This pilot consumes the newly merged `Repo Analysis` artifact contract and checks whether the repo can actually produce such an artifact during initialization. The immediate gap is mechanical but important: the artifact exists in truth docs and decision skill boundaries, while scaffold/bootstrap output still lacks the corresponding `.servo/repo/analysis.md` sample.

The next worktrack should be narrow:

- Add template files for `repo/analysis.md` in both `.servo_template` and `set-harness-goal-skill` assets.
- Teach `aw_scaffold.py` and `deploy_aw.py` their template specs.
- Update focused tests and README entries.
- Run scaffold/deploy helper tests plus path/semantic/folder governance checks.
