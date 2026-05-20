---
title: "Repo Analysis Baseline"
artifact_type: "repo-analysis-report"
generated_from: "WT-20260426-repo-analysis-baseline"
updated: "2026-04-26"
owner: "servo-kernel"
---
# Repo Analysis Baseline

## Control Signal

- repo: servo
- baseline_branch: develop-aw
- baseline_ref: 8520f4a80bd7a3c0551b316924b175d30a5c5444
- worktrack_id: WT-20260426-repo-analysis-baseline
- analysis_mode: project-dialectic-planning + RepoScope priority reframe
- status: research report
- writeback_status: not admitted to truth layer

## 1. Core Conclusion

- Project goal: build a Codex-first AI coding Harness platform and distribute it as a reusable repo-side contract layer across projects.
- Current stage: post-doctrine / post-governance consolidation; entering capability-productization and analysis-loop hardening.
- Overall judgment: the repo has an unusually strong internal governance baseline for an AI coding harness, but its repo-level analysis capability is still implicit and scattered across control prompts, governance scoring scripts, and ad hoc Harness decisions.
- Current main contradiction: the repo needs high-quality strategic repo analysis to choose the right next worktracks, but repo analysis is not yet a first-class, repeatable Harness artifact or workflow.
- Main aspect of the contradiction: analysis output exists as reasoning in conversations or scripts, not as a stable contract with evidence inputs, output schema, gate/readiness rules, and writeback policy.
- Current highest priority: build a bounded, repeatable repo analysis baseline workflow before starting another implementation-heavy phase.
- Long-term highest priority: make Harness itself a reusable closed-loop control product, where repo analysis, bounded execution, verification, gate, and writeback form a portable capability.

## 2. Data Sufficiency Overview

| Dimension | Sufficiency | Known Facts | Key Gaps | Confidence |
| --- | --- | --- | --- | --- |
| Demand basis | medium | README states the project targets Codex-first AI coding harness and cross-repo contract-layer distribution. User explicitly prioritized repo analysis in this worktrack. | No external user interviews, adoption metrics, or cross-repo usage data in current artifacts. | medium |
| Structural opening | medium | Current repo has Harness doctrine, executable skills, adapters, deploy scripts, governance checks, and `.aw` control artifacts. Few repos have this explicit control-plane vocabulary. | Competitive landscape and alternative tooling comparison are not documented. | medium |
| Trend window | low | AI coding control, verification, and repo-side contracts are clearly relevant to current tool usage; current date and repo activity show active iteration. | No market/channel timing evidence is present in repo. | low |
| Delivery capability | high | `docs/`, `product/`, and `toolchain/` are cleanly separated; 17 canonical skill sources and matching agents payload descriptors exist; governance/test scripts exist. | Packaging/distribution beyond repo-local agents deploy is not verified. | high |
| Organization capability | medium | Harness control state, worktrack contracts, gate evidence, and review/verify handbook provide strong self-governance. | Human/operator decision cadence and external collaborator model are not documented. | medium |
| Time/resources | low | User approved 20 automatic budget units and one research worktrack; current worktree is clean. | No calendar deadline, release target, staffing, or external delivery date is defined. | low |

## 3. Project Fundamentals

### 3.1 Demand Basis

Facts:

- The root README defines the project as a Codex-first AI coding harness platform and reusable repo-side contract layer.
- The repo contains Harness doctrine, scope, artifacts, workflow families, adjacent-system contracts, executable skills, adapters, deploy tooling, and governance checks.
- The user explicitly redirected the next stage toward repo analysis.

Inference:

- The immediate internal demand is not "more rules" or "more deploy commands"; it is better repo-level judgment so the Harness can choose the next worktrack without local loops becoming busywork.
- The external demand remains plausible but unverified: other repos may need AI coding control layers, but this repo does not yet contain adoption evidence.

Unknowns:

- Who the first external consumers are.
- What minimum install/use workflow those consumers would accept.
- Whether repo analysis is primarily for this repo's supervisor loop, or also a distributable capability for other repos.

### 3.2 Structural Opening

Facts:

- `docs/harness/` is the upstream truth layer for Harness doctrine, artifacts, workflow families, skills catalog, and adjacent systems.
- `product/harness/skills/` contains 17 canonical skill sources.
- `product/harness/adapters/agents/skills/` contains matching agents payload descriptors for the same 17 skills.
- `toolchain/scripts/test/` contains folder, path, semantic, closeout, adapter contract, and governance evaluation tools.
- RepoScope catalog already says repo-level analysis can exist as a bounded mode inside `repo-whats-next-skill`, without adding unbounded skill layers.

Inference:

- The repo has already built much of the control-plane substrate. The opening now is to turn that substrate into sharper decision quality.
- There is a risk of over-optimizing governance tests while postponing the question "what is the repo actually trying to improve next?"

Unknowns:

- Whether repo analysis should remain a mode in `repo-whats-next-skill`, become a formal artifact, or become a new workflow family pattern.

### 3.3 Trend Window

Facts:

- The repository is actively adapting AI coding workflows to Codex, skills, adapters, and verification.
- The Harness doctrine has already separated control plane, execution plane, evidence, and gate.

Inference:

- The timing favors building practical control loops over static documentation alone.
- A repeatable repo analysis workflow could become an important differentiator because it improves what work is selected, not only how work is verified after selection.

Unknowns:

- External distribution timing and packaging channel.
- Whether "npx-style" distribution is still the next external milestone or should wait until repo analysis is stabilized.

### 3.4 Delivery Capability

Facts:

- Formal content roots are clear: `docs/`, `product/`, `toolchain/`.
- There are 176 files under `docs product toolchain tools`, including 130 Markdown files and 28 Python files.
- Governance scripts and tests have been repeatedly strengthened.
- Review/verify handbook defines validation commands and writeback rules.
- Current worktree was clean at the start of this worktrack; branch `research-repo-analysis-baseline` was created from `develop-aw` at `8520f4a`.

Inference:

- The repo can deliver narrow, verified changes reliably.
- The next delivery bottleneck is not local correctness; it is priority selection and scope conversion from analysis to worktracks.

Unknowns:

- Whether analysis outputs should be machine-readable, human-readable, or both.
- What minimum schema downstream Harness skills need to consume analysis without reinterpreting prose.

### 3.5 Organization Capability

Facts:

- Harness control state tracks scope, function, budget, handoff, baseline, and active worktrack.
- Worktracks use contracts, plans, evidence, gate, closeout, and repo refresh.
- The user can explicitly approve budgets and redirect priority.

Inference:

- The repo has a working governance culture for agentic development.
- Current operator bottleneck is deciding the right level of abstraction for the next stage, not merely granting execution permission.

Unknowns:

- Whether future operators will understand or tolerate the current `.aw` state model.
- Whether repo analysis should simplify operator handoff language.

### 3.6 Time And Resources

Facts:

- The user approved one repo analysis research worktrack and 20 budget units.
- This worktrack consumed 1 unit, leaving 19 in the current ledger.
- No external release deadline is encoded in repo artifacts.

Inference:

- The available budget is enough for a short analysis-to-capability sequence, but not for unbounded strategic exploration.
- The next 1-2 worktracks should convert this analysis into a repeatable structure, then stop and reassess.

Unknowns:

- Calendar deadline.
- External stakeholder expectations.

## 4. Contradiction Analysis

All key contradictions:

- Strategic analysis need vs. lack of first-class repo analysis artifact.
- Reusable Harness platform goal vs. current repo-local deploy/productization maturity.
- Strong governance surface vs. risk of governance micro-hardening loops.
- Rich doctrine and skill catalog vs. limited proof that the full loop is easy for another repo to adopt.
- Research/analysis outputs vs. verified truth-layer writeback discipline.

Current main contradiction:

- The repo needs high-quality strategic repo analysis to choose the right next worktracks, but repo analysis is not yet a first-class, repeatable Harness artifact or workflow.

Main aspect:

- The missing contract/output surface for repo analysis. The reasoning can be performed, but it is not yet stable enough to be rerun, reviewed, gated, or consumed by the Harness loop without conversational inference.

Why this outranks distribution productization right now:

- Distribution work will multiply whatever control assumptions already exist. If repo-level analysis remains ad hoc, productization may package an incomplete decision loop.
- The user explicitly prioritized repo analysis, making this the current operator-facing demand.
- A small analysis workflow can directly improve future worktrack selection, including whether distribution should be next.

Secondary contradictions and conversion conditions:

- Distribution maturity becomes primary after repo analysis has a stable output schema and says distribution is the top priority.
- Governance micro-hardening becomes primary only when a concrete failing check, stale docs boundary, or rule drift blocks execution.
- Adjacent-system implementation becomes primary only when analysis shows Memory Side or Task Interface is the bottleneck for Harness adoption.

Consequence if unresolved:

- The Harness loop may continue opening locally valid but strategically low-leverage worktracks.
- Future automatic budgets may be consumed by micro-fixes rather than capability jumps.
- Repo truth may remain clean while project direction becomes under-specified.

## 5. Catch-Up Analysis

| Indicator / Goal | Current Value | Target Value | Gap | Remaining Time | Current Speed | Required Speed | Reachable |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| Canonical skill source coverage | 17 skills | Stable first-wave Harness loop | small for current scope | unknown | high | maintain | yes |
| Agents payload coverage | 17 payloads | Match canonical skill set | small for agents | unknown | high | maintain | yes |
| Governance baseline | folder/path/semantic/closeout checks exist | Verified closeout for narrow changes | small | unknown | high | maintain | yes |
| Repo analysis workflow | ad hoc reasoning + eval scripts | stable analysis artifact/workflow | material | 1-2 worktracks recommended | low | focused | yes |
| Cross-repo distribution | repo-local agents deploy | reusable install/update/diagnose path | material | unknown | medium | staged | likely, after analysis |

Catch-up judgment:

- The project is not behind on internal governance; it is behind on making repo-level analysis explicit enough to steer future work.
- The required lever is path and scope discipline: define the analysis artifact/workflow before more implementation.

This-stage qualitative threshold:

- A repo analysis output can be produced from standard artifacts.
- It names facts/inferences/unknowns separately.
- It names one main contradiction and one top priority.
- It maps the priority to a legal Harness next route.
- It states whether conclusions are writeback-ready or research-only.

## 6. Priority Judgment

### Current Highest Priority

- Work item: define and validate a repeatable repo analysis workflow/artifact for Harness.
- Direct mechanism: converts operator preference and repo facts into a structured decision input for `RepoScope.Decide`.
- Why first: it improves what the Harness chooses next; distribution, adapters, docs, and governance all depend on correct priority selection.
- Cost of not doing it: future worktracks may be locally correct but strategically weak.
- Expected change: within 1-2 worktracks, Harness can produce a stable repo analysis report and use it to initialize the next worktrack without redoing ad hoc reasoning.

### Long-Term Highest Priority

- Work item: build Harness as a reusable closed-loop control product.
- Why it decides long-term success: the product value is not a single skill or script; it is the controlled loop from goal to bounded execution, evidence, gate, closeout, refresh, and writeback.
- Required assets: stable artifacts, canonical skills, adapters, deploy tooling, repo analysis workflow, verification gates, and operator-facing runbooks.
- Relation to current priority: aligned. Repo analysis improves the decision quality of the closed loop.

## 7. Short And Mid-Term Tasks

### Short Term: 7-14 Days / 1-2 Worktracks

| Priority | Task | Served Contradiction | Goal | Owner Role | Dependencies | Done Standard |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Repo analysis artifact/workflow spec | Analysis need vs. missing first-class artifact | Define schema, required inputs, output fields, review gate, and writeback policy | Harness maintainer | This report, RepoScope catalog | A doc or product contract names the artifact/workflow and its boundaries |
| P0 | Repo analysis pilot run | Analysis workflow unproven | Re-run this analysis using the new structure and compare output quality | Harness supervisor/operator | Artifact/workflow spec | Pilot produces a decision-ready route without conversational inference |
| P1 | Integrate with `repo-whats-next-skill` boundary | Decision skill lacks durable analysis input | Make repo analysis consumable without adding unbounded skill sprawl | Harness maintainer | Spec/pilot | Skill docs or executable source reference the analysis contract |
| P1 | Define writeback admission rule | Research output vs. truth-layer discipline | Decide what analysis conclusions can become project-maintenance or Harness truth | Maintainer/reviewer | Review/verify handbook | Writeback criteria are documented and reviewable |

### Mid Term: 30-60 Days

| Priority | Task | Served Contradiction | Goal | Owner Role | Dependencies | Done Standard |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Use repo analysis to choose next productization slice | Analysis vs. execution | Pick distribution, adapter, Memory Side, Task Interface, or other next slice based on evidence | Harness supervisor | Analysis workflow | One worktrack opens from analysis output and closes cleanly |
| P1 | Package analysis as a reusable Harness pattern | Reusable platform vs. repo-local practice | Make analysis usable in other repos | Harness maintainer | At least one successful pilot | Pattern has docs, skill boundary, examples, and verification path |
| P2 | Add structured evaluator only if needed | Script sprawl vs. decision quality | Automate scoring only after schema stabilizes | Toolchain maintainer | Stable schema | Tool is small, testable, and does not replace human judgment |

## 8. Do Not Do Now

- Do not continue Python cache / governance micro-hardening without a fresh failure signal.
  - It would optimize an already-strong surface and avoid the current analysis bottleneck.
- Do not start full distribution or npx-style packaging before the analysis workflow can justify that route.
  - Packaging before decision quality risks freezing weak assumptions.
- Do not create a permanent `docs/analysis/` truth scope from this report alone.
  - Research output must first pass writeback admission; otherwise `docs/` gains a new orphan line.

## 9. Practice Loop

Next check cycle:

- After one analysis-spec worktrack or one pilot run, whichever comes first.

Signals this judgment is correct:

- The next worktrack can be selected from structured analysis fields rather than conversational summary.
- The report exposes useful unknowns without blocking all action.
- The resulting worktrack has narrower scope and clearer acceptance criteria.

Signals this judgment is wrong:

- Analysis produces generic statements that do not change routing.
- The schema becomes heavier than the decisions it supports.
- A concrete deploy/productization blocker appears and makes analysis work secondary.

Re-sort priority when:

- A repo analysis pilot closes.
- A user changes the goal or deadline.
- A real distribution/adoption opportunity appears.
- Governance or deploy failure blocks ordinary worktrack closure.

## 10. Writeback Eligibility

Eligible for future writeback after review:

- The statement that repo analysis should remain bounded and evidence-based.
- The need to separate facts, inferences, unknowns, main contradiction, current priority, and writeback eligibility.
- The proposal that repo analysis should feed `RepoScope.Decide` without becoming unbounded strategy prose.

Not eligible yet:

- Any external market or adoption claim.
- Any claim about packaging priority beyond this repo's current internal state.
- Any permanent `docs/analysis/` scope decision.

## Supporting Detail

Observed evidence:

- `git status --short --branch` before initialization: clean on `develop-aw`.
- Branch created: `research-repo-analysis-baseline`.
- Baseline ref: `8520f4a80bd7a3c0551b316924b175d30a5c5444`.
- Entrypoints read: `README.md`, `docs/README.md`, `product/README.md`, `toolchain/README.md`, `docs/harness/README.md`.
- Skill catalog read: `docs/harness/catalog/repo.md`, `docs/harness/catalog/worktrack.md`.
- Governance entry read: `docs/project-maintenance/governance/review-verify-handbook.md`.
- Tooling observed: `repo_governance_eval.py`, `governance_assess.py`, and test README entries.
- Count observations: 17 canonical skill sources, 17 agents payload descriptors, 176 files under `docs product toolchain tools`, 130 Markdown files, 28 Python files.
