from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance_semantic_check import (
    SemanticReport,
    check_agents_route_slimming_contract,
    check_append_request_contract_terms,
    check_adapter_wrappers_are_thin,
    check_artifact_skill_alignment,
    check_aw_residue_classification_contract,
    check_canonical_skill_packages_are_minimal,
    check_closeout_record_contract,
    check_complex_project_entry_gate_contract,
    check_complexity_signal_scanner_contract,
    check_debug_evidence_contract,
    check_decision_traceability_contract,
    check_docs_list_closeout_cache_roots,
    check_dispatch_context_contract,
    check_foundations_authority_shadows,
    check_orphan_docs,
    check_manual_runbook_agents_skill_count,
    check_init_milestone_intake_handoff_contract,
    check_outdated_placeholder_phrases,
    check_path_governance_docs_list_gitignore_entries,
    check_pre_milestone_intake_template_contract,
    check_pull_request_template_release_evidence,
    check_repo_python_commands_are_bytecode_free,
    check_repo_init_complex_gate_contract,
    check_repo_whats_next_overview_fallback_contract,
    check_retired_entrypoint_references,
    check_review_evidence_four_lane_contract,
    check_review_verify_docs_list_closeout_steps,
    check_root_tool_shims_disable_bytecode,
    check_runtime_artifact_consistency,
    check_runtime_dispatch_profile_contract,
    check_required_handoffs,
    check_subagent_dispatch_default_contract,
    check_weak_doc_temporary_understanding_contract,
    check_worktrack_intake_review_contract,
    is_bytecode_free_command_excluded,
)
from runtime_artifact_consistency_simulation import SCENARIOS, run_scenario


def write_doc(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_check_required_handoffs_flags_missing_link(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/README.md",
        "[harness](./harness/README.md)\n",
    )
    write_doc(
        tmp_path / "product/harness/README.md",
        "[docs](../../docs/harness/README.md)\n[skills](./skills/README.md)\n[adapters](./adapters/README.md)\n",
    )
    write_doc(tmp_path / "product/harness/skills/README.md", "# skills\n")
    write_doc(tmp_path / "product/harness/adapters/README.md", "# adapters\n")
    write_doc(
        tmp_path / "toolchain/toolchain-layering.md",
        "missing script handoff\n",
    )
    write_doc(tmp_path / "docs/harness/README.md", "")
    write_doc(tmp_path / "docs/harness/foundations/README.md", "")
    write_doc(tmp_path / "docs/harness/artifact/README.md", "")
    write_doc(
        tmp_path / "docs/harness/artifact/worktrack/README.md",
        "[contract](./contract.md)\n"
        "[queue](./plan-task-queue.md)\n"
        "[gate](./gate-evidence.md)\n"
        "[debug](./debug-evidence.md)\n",
    )
    write_doc(tmp_path / "docs/harness/artifact/worktrack/contract.md", "")
    write_doc(tmp_path / "docs/harness/artifact/worktrack/plan-task-queue.md", "")
    write_doc(tmp_path / "docs/harness/artifact/worktrack/gate-evidence.md", "")
    write_doc(tmp_path / "docs/harness/artifact/worktrack/debug-evidence.md", "")
    write_doc(tmp_path / "docs/harness/workflow-families/README.md", "")
    write_doc(tmp_path / "toolchain/scripts/README.md", "# scripts\n")

    report = SemanticReport()
    check_required_handoffs(tmp_path, report)

    assert any("toolchain-layering.md -> toolchain/scripts/README.md" in item for item in report.failures)


def test_check_pull_request_template_release_evidence_flags_missing_terms(tmp_path: Path) -> None:
    write_doc(tmp_path / ".github/pull_request_template.md", "## Verification\n")

    report = SemanticReport()
    check_pull_request_template_release_evidence(tmp_path, report)

    assert any("Release PR Evidence" in item for item in report.failures)


def test_check_pull_request_template_release_evidence_accepts_guard_terms(tmp_path: Path) -> None:
    write_doc(
        tmp_path / ".github/pull_request_template.md",
        "develop-main -> master\n"
        "## Release PR Evidence\n"
        "- PR head SHA:\n"
        "- Local release-readiness SHA:\n"
        "- source-version docs freshness:\n"
        "- candidate npm version/tag conflict check:\n"
        "- CI run/job URL:\n"
        "- skipped checks:\n"
        "- reviewDecision:\n",
    )

    report = SemanticReport()
    check_pull_request_template_release_evidence(tmp_path, report)

    assert report.failures == []


def test_check_foundations_authority_shadows_flags_prefixed_duplicate(tmp_path: Path) -> None:
    foundations_dir = tmp_path / "docs/project-maintenance/foundations"
    foundations_dir.mkdir(parents=True, exist_ok=True)
    write_doc(foundations_dir / "root-directory-layering.md", "# doc\n")
    write_doc(foundations_dir / "root-directory-layering-v2.md", "# shadow\n")

    report = SemanticReport()
    check_foundations_authority_shadows(tmp_path, report)

    assert any("root-directory-layering.md" in item for item in report.failures)


def test_check_outdated_placeholder_phrases_flags_stale_text(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "toolchain/scripts/README.md",
        "`research/`：预留给后续准入的最小研究脚本\n",
    )
    write_doc(tmp_path / "toolchain/toolchain-layering.md", "current wording\n")

    report = SemanticReport()
    check_outdated_placeholder_phrases(tmp_path, report)

    assert any("toolchain/scripts/README.md" in item for item in report.failures)


def test_check_retired_entrypoint_references_flags_retired_paths(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "AGENTS.md",
        "旧入口：`docs/harness/adjacent-systems/memory-side/overview.md`\n",
    )
    write_doc(tmp_path / "docs/README.md", "current\n")
    write_doc(tmp_path / "docs/harness/README.md", "current\n")
    write_doc(tmp_path / "docs/project-maintenance/governance/path-governance-checks.md", "current\n")

    report = SemanticReport()
    check_retired_entrypoint_references(tmp_path, report)

    assert any("AGENTS.md" in item for item in report.failures)


def test_check_retired_entrypoint_references_accepts_current_sources(tmp_path: Path) -> None:
    write_doc(tmp_path / "AGENTS.md", "current\n")
    write_doc(tmp_path / "docs/README.md", "current\n")
    write_doc(tmp_path / "docs/harness/README.md", "current\n")

    report = SemanticReport()
    check_retired_entrypoint_references(tmp_path, report)

    assert report.failures == []


def test_check_agents_route_slimming_contract_flags_fixed_read_first(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Read First",
                "1. `docs/README.md`",
                "## Route Contract",
                "- `do_not_read_yet`: `.agents/`",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_agents_route_slimming_contract(tmp_path, report)

    assert any("Read First" in item for item in report.failures)
    assert any("Default Boot" in item for item in report.failures)


def test_check_agents_route_slimming_contract_accepts_default_boot(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "AGENTS.md",
        "\n".join(
            [
                "# AGENTS.md",
                "## Default Boot",
                "默认启动只读 `AGENTS.md`、`INDEX.md` 和当前任务对应的一个局部入口。",
                "仅当任务命中对应边界时才扩读承接层文档。",
                "## Route Contract",
                "- `do_not_read_yet`: `.servo/`, `.agents/`, `.claude/`",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_agents_route_slimming_contract(tmp_path, report)

    assert report.failures == []


def _write_aw_residue_contract(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/servo-installer/contracts/aw-residue-classification-contract.md",
        "compatibility-allowed\nruntime-migration-contract\nmarker-identity-contract\n"
        "legacy-target-dir-contract\ntest-fixture-only\nhistorical-doc-only\n"
        "navigation-only\nremediation-required\nunclassified-aw-residue\n",
    )


def test_check_aw_residue_classification_contract_flags_canonical_marker(tmp_path: Path) -> None:
    _write_aw_residue_contract(tmp_path)
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/aw.marker",
        "",
    )
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/payload.json",
        '{"required_payload_files":["SKILL.md","payload.json","aw.marker"],"legacy_target_dirs":["aw-demo-skill"]}\n',
    )

    report = SemanticReport()
    check_aw_residue_classification_contract(tmp_path, report)

    assert any("canonical source" in item for item in report.failures)


def test_check_aw_residue_classification_contract_flags_payload_marker_drift(tmp_path: Path) -> None:
    _write_aw_residue_contract(tmp_path)
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/payload.json",
        '{"required_payload_files":["SKILL.md","payload.json"],"legacy_target_dirs":["aw-demo-skill"]}\n',
    )

    report = SemanticReport()
    check_aw_residue_classification_contract(tmp_path, report)

    assert any("required_payload_files" in item for item in report.failures)


def test_check_aw_residue_classification_contract_flags_unclassified_aw_target_dir(tmp_path: Path) -> None:
    _write_aw_residue_contract(tmp_path)
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/payload.json",
        '{"target_dir":"aw-demo-skill","required_payload_files":["SKILL.md","payload.json","aw.marker"],"legacy_target_dirs":[]}\n',
    )

    report = SemanticReport()
    check_aw_residue_classification_contract(tmp_path, report)

    assert any("legacy aw-* adapter value" in item for item in report.failures)


def test_check_aw_residue_classification_contract_accepts_adapter_compatibility_payload(tmp_path: Path) -> None:
    _write_aw_residue_contract(tmp_path)
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/payload.json",
        '{"target_dir":"servo-demo-skill","required_payload_files":["SKILL.md","payload.json","aw.marker"],"legacy_target_dirs":["demo-skill","aw-demo-skill"],"legacy_skill_ids":["aw-demo-skill"]}\n',
    )

    report = SemanticReport()
    check_aw_residue_classification_contract(tmp_path, report)

    assert report.failures == []


def test_check_append_request_contract_terms_flags_drift(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/control/append-request.md",
        "append-feature\nappend-design\nappend-milestone\ngoal change\nnew milestone\nnew worktrack\nscope expansion\ndesign-only\ndesign-then-implementation\napproval_required\ncontinuation_ready\n",
    )
    write_doc(
        tmp_path / "docs/harness/workflow-families/repo-evolution/append-request-routing.md",
        "append-feature\nappend-design\nappend-milestone\ngoal change\nnew milestone\nnew worktrack\nscope expansion\ndesign-only\ndesign-then-implementation\napproval_required\ncontinuation_ready\ncontinuation_blockers\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/repo-append-request-skill/SKILL.md",
        "append-feature\nappend-design\nappend-milestone\ngoal change\nnew milestone\nnew worktrack\nscope expansion\ndesign-only\ndesign-then-implementation\napproval_required\ncontinuation_ready\ncontinuation_blockers\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/repo-append-request-skill/templates/append-request.template.md",
        "approval_required\ncontinuation_ready\ncontinuation_blockers\n",
    )

    report = SemanticReport()
    check_append_request_contract_terms(tmp_path, report)

    assert any("continuation_blockers" in item for item in report.failures)


def test_check_subagent_dispatch_default_contract_flags_missing_term(tmp_path: Path) -> None:
    for relative_path in (
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/dispatch-skills/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
        "product/.servo_template/control-state.md",
        "docs/harness/artifact/control/control-state.md",
        "docs/harness/artifact/worktrack/contract.md",
        "docs/harness/foundations/Harness运行协议.md",
        "docs/harness/catalog/worktrack.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "默认\nSubAgent\n权限边界\nDispatch Decision Policy\nsubagent_dispatch_mode\nsubagent_dispatch_mode_override_scope\nworktrack-contract-primary\nglobal-override\nruntime_dispatch_mode\nauto\ndelegated\ncurrent-carrier\nruntime fallback\n",
        )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/assets/worktrack/contract.md",
        "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "product/.servo_template/worktrack/contract.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "Execution Policy canonical semantics are not repeated here\n"
            "execution_policy_contract_ref\n"
            "docs/harness/artifact/worktrack/contract.md#execution-policy\n"
            "runtime_dispatch_mode\ndispatch_mode_source\nallowed_values\nfallback_reason_required\n",
        )

    report = SemanticReport()
    check_subagent_dispatch_default_contract(tmp_path, report)

    assert any("dispatch package unsafe" in item for item in report.failures)


def test_check_subagent_dispatch_default_contract_flags_template_prose_duplication(tmp_path: Path) -> None:
    for relative_path in (
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/dispatch-skills/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
        "product/.servo_template/control-state.md",
        "docs/harness/artifact/control/control-state.md",
        "docs/harness/artifact/worktrack/contract.md",
        "docs/harness/foundations/Harness运行协议.md",
        "docs/harness/catalog/worktrack.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "默认\nSubAgent\n权限边界\nDispatch Decision Policy\nsubagent_dispatch_mode\nsubagent_dispatch_mode_override_scope\nworktrack-contract-primary\nglobal-override\nruntime_dispatch_mode\nauto\ndelegated\ncurrent-carrier\nruntime fallback\ndispatch package unsafe\n",
        )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/assets/worktrack/contract.md",
        "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "product/.servo_template/worktrack/contract.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "Execution Policy canonical semantics are not repeated here\n"
            "execution_policy_contract_ref\n"
            "docs/harness/artifact/worktrack/contract.md#execution-policy\n"
            "runtime_dispatch_mode\ndispatch_mode_source\nallowed_values\nfallback_reason_required\n"
            "控制本 worktrack 的执行载体选择。`auto` 按 Dispatch Decision Policy\n",
        )

    report = SemanticReport()
    check_subagent_dispatch_default_contract(tmp_path, report)

    assert any("duplicates canonical prose" in item for item in report.failures)


def test_check_dispatch_context_contract_flags_missing_budget_term(tmp_path: Path) -> None:
    for relative_path in (
        "docs/harness/artifact/worktrack/dispatch-packet.md",
        "product/harness/skills/dispatch-skills/SKILL.md",
        "product/harness/skills/schedule-worktrack-skill/SKILL.md",
        "product/harness/skills/generic-worker-skill/SKILL.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "shared_fact_pack\ncontext_budget\nmust_read\nmay_read\n",
        )

    report = SemanticReport()
    check_dispatch_context_contract(tmp_path, report)

    assert any("do_not_read" in item for item in report.failures)


def _write_runtime_dispatch_profile_sources(tmp_path: Path, text: str) -> None:
    for relative_path in (
        "docs/harness/foundations/dispatch-decision-policy.md",
        "docs/harness/foundations/runtime-dispatch-contract.md",
        "docs/harness/artifact/worktrack/dispatch-packet.md",
        "docs/harness/artifact/control/control-state.md",
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/dispatch-skills/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
        "product/.servo_template/control-state.md",
    ):
        write_doc(tmp_path / relative_path, text)


def test_check_runtime_dispatch_profile_contract_flags_missing_field(tmp_path: Path) -> None:
    _write_runtime_dispatch_profile_sources(
        tmp_path,
        "runtime_dispatch_profile\nbackend_runtime\nmodel_family\n"
        "subagent_dispatch_shell\nruntime_supports_subagent\nsubagent_permission_state\n"
        "permission_allows_delegation\ndispatch_package_safety\n"
        "delegation_attempted\nattempted_carrier\ncarrier_decision\nfallback_reason\n"
        "ClaudeCodeCLI\nDeepseek\nruntime fallback\npermission blocked\n"
        "dispatch package unsafe\n",
    )
    write_doc(
        tmp_path / "docs/harness/artifact/worktrack/dispatch-packet.md",
        "runtime_dispatch_profile\nbackend_runtime\nmodel_family\n"
        "subagent_dispatch_shell\nruntime_supports_subagent\nsubagent_permission_state\n"
        "permission_allows_delegation\n"
        "delegation_attempted\nattempted_carrier\ncarrier_decision\nfallback_reason\n"
        "ClaudeCodeCLI\nDeepseek\nruntime fallback\npermission blocked\n"
        "dispatch package unsafe\n",
    )

    report = SemanticReport()
    check_runtime_dispatch_profile_contract(tmp_path, report)

    assert any("dispatch_package_safety" in item for item in report.failures)


def test_check_runtime_dispatch_profile_contract_accepts_complete_sources(tmp_path: Path) -> None:
    _write_runtime_dispatch_profile_sources(
        tmp_path,
        "runtime_dispatch_profile\nbackend_runtime\nmodel_family\n"
        "subagent_dispatch_shell\nruntime_supports_subagent\nsubagent_permission_state\n"
        "permission_allows_delegation\ndispatch_package_safety\n"
        "delegation_attempted\nattempted_carrier\ncarrier_decision\nfallback_reason\n"
        "ClaudeCodeCLI\nDeepseek\nruntime fallback\npermission blocked\n"
        "dispatch package unsafe\n",
    )

    report = SemanticReport()
    check_runtime_dispatch_profile_contract(tmp_path, report)

    assert report.failures == []


def test_check_review_evidence_four_lane_contract_flags_missing_lane(tmp_path: Path) -> None:
    for relative_path in (
        "product/harness/skills/review-evidence-skill/SKILL.md",
        "docs/harness/catalog/worktrack.md",
        "product/harness/skills/set-harness-goal-skill/assets/worktrack/gate-evidence.md",
        "docs/harness/artifact/worktrack/gate-evidence.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "review_profile\nlight\nstandard\nrisky\ndeep\n并行\nSubAgent\nfallback\nstatic-semantic-review\ntest-review\nproject-security-review\n静态语义解释\n测试 review\nsecurity review\n代码复杂度和性能 review\n",
        )

    report = SemanticReport()
    check_review_evidence_four_lane_contract(tmp_path, report)

    assert any("complexity-performance-review" in item for item in report.failures)


def test_check_debug_evidence_contract_flags_missing_field(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/worktrack/debug-evidence.md",
        "source_logs\nsymptom\nreproduction_steps\nobserved_error\n"
        "root_cause_hypothesis\nconfirmed_facts\ndiscarded_hypotheses\n"
        "remaining_unknowns\nRaw Log Boundary\n",
    )

    report = SemanticReport()
    check_debug_evidence_contract(tmp_path, report)

    assert any("next_debug_action" in item for item in report.failures)


def test_check_decision_traceability_contract_flags_missing_decision_refs(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/repo/decision-log.md",
        "decision_id\ndate\nstatus\naccepted\nsuperseded\nrejected\ncontext\n"
        "decision\nalternatives_considered\nwhy_not_chosen\nconsequences\n"
        "affected_artifacts\nrelated_worktracks\nrelated_commits\nsupersedes\n",
    )
    write_doc(
        tmp_path / "docs/harness/artifact/repo/worktrack-backlog.md",
        "worktrack_id\nstatus\nvalidation\n",
    )

    report = SemanticReport()
    check_decision_traceability_contract(tmp_path, report)

    assert any("decision_refs" in item for item in report.failures)


def test_check_closeout_record_contract_flags_missing_field(tmp_path: Path) -> None:
    closeout_terms = (
        "closeout_record\nworktrack_id\nbranch\nbase_ref\nhead_ref\nmerge_commit\npr\n"
        "files_changed\nacceptance_result\ngate_verdict\nevidence_refs\ndecision_refs\n"
        "docs_updated\nsnapshot_refreshed\nbacklog_updated\ncleanup_done\nremaining_risks\n"
    )
    write_doc(tmp_path / "docs/harness/artifact/worktrack/README.md", closeout_terms)
    write_doc(tmp_path / "product/harness/skills/close-worktrack-skill/SKILL.md", closeout_terms)

    report = SemanticReport()
    check_closeout_record_contract(tmp_path, report)

    assert any("next_repo_scope_action" in item for item in report.failures)


def test_check_repo_whats_next_overview_fallback_contract_flags_missing_term(tmp_path: Path) -> None:
    for relative_path in (
        "product/harness/skills/repo-whats-next-skill/SKILL.md",
        "product/harness/skills/repo-whats-next-skill/references/overview-fallback-mode.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(
            tmp_path / relative_path,
            "overview fallback\nproject-dialectic-planning-skill\ncandidate_worktracks\ntop_candidate\nFacts / Inferences / Unknowns\n不创建工作追踪\n",
        )

    report = SemanticReport()
    check_repo_whats_next_overview_fallback_contract(tmp_path, report)

    assert any("不改变 Harness 控制状态" in item for item in report.failures)


def _write_worktrack_intake_review_sources(tmp_path: Path, text: str) -> None:
    for relative_path in (
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/repo-whats-next-skill/SKILL.md",
        "product/harness/skills/init-worktrack-skill/SKILL.md",
        "docs/harness/scope/repo-scope.md",
        "docs/harness/foundations/runtime-control-loop.md",
        "docs/harness/artifact/worktrack/contract.md",
        "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "product/harness/skills/set-harness-goal-skill/assets/worktrack/contract.md",
        "product/.servo_template/worktrack/contract.md",
    ):
        write_doc(tmp_path / relative_path, text)


def test_check_worktrack_intake_review_contract_flags_missing_field(tmp_path: Path) -> None:
    _write_worktrack_intake_review_sources(
        tmp_path,
        "worktrack_intake_review\nrepo_fundamentals\nsnapshot_freshness\n"
        "milestone_purpose_alignment\nhistorical_conflict_risk\n"
        "worktrack_adjustment_recommendations\nadd_remove_worktrack_recommendations\n"
        "intake_review_verdict\nready_for_worktrack_init\n"
        "ready_for_worktrack_init\nrefresh_required\nadjust_worktracks\nblocked\n",
    )
    write_doc(
        tmp_path / "docs/harness/artifact/worktrack/contract.md",
        "worktrack_intake_review\nrepo_fundamentals\n"
        "milestone_purpose_alignment\nhistorical_conflict_risk\n"
        "worktrack_adjustment_recommendations\nadd_remove_worktrack_recommendations\n"
        "intake_review_verdict\n"
        "ready_for_worktrack_init\nrefresh_required\nadjust_worktracks\nblocked\n",
    )

    report = SemanticReport()
    check_worktrack_intake_review_contract(tmp_path, report)

    assert any("snapshot_freshness" in item for item in report.failures)


def test_check_worktrack_intake_review_contract_accepts_complete_sources(tmp_path: Path) -> None:
    _write_worktrack_intake_review_sources(
        tmp_path,
        "worktrack_intake_review\nrepo_fundamentals\nsnapshot_freshness\n"
        "milestone_purpose_alignment\nhistorical_conflict_risk\n"
        "worktrack_adjustment_recommendations\nadd_remove_worktrack_recommendations\n"
        "intake_review_verdict\nready_for_worktrack_init\n"
        "refresh_required\nadjust_worktracks\nblocked\n",
    )

    report = SemanticReport()
    check_worktrack_intake_review_contract(tmp_path, report)

    assert report.failures == []


def test_check_adapter_wrappers_are_thin_ignores_absent_adapter_layer(tmp_path: Path) -> None:
    report = SemanticReport()
    check_adapter_wrappers_are_thin(tmp_path, report)
    assert report.failures == []


def test_check_adapter_wrappers_are_thin_accepts_valid_wrapper(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "# Demo Adapter Wrapper",
                "## Canonical Source",
                "## Backend Notes",
                "## Deploy Target",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_adapter_wrappers_are_thin(tmp_path, report)

    assert report.failures == []


def test_check_adapter_wrappers_are_thin_flags_missing_heading_and_duplication(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "# Demo Adapter Wrapper",
                "## Canonical Source",
                "## Backend Notes",
                "## Execution Rules",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_adapter_wrappers_are_thin(tmp_path, report)

    assert any("Deploy Target" in item for item in report.failures)
    assert any("Execution Rules" in item for item in report.failures)


def test_check_adapter_wrappers_are_thin_ignores_code_fence_headings(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/adapters/agents/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "# Demo Adapter Wrapper",
                "## Canonical Source",
                "## Backend Notes",
                "## Deploy Target",
                "```md",
                "## Execution Rules",
                "```",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_adapter_wrappers_are_thin(tmp_path, report)

    assert report.failures == []


def test_check_canonical_skill_packages_are_minimal_accepts_valid_package(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "---",
                "name: demo-skill",
                "description: Demo.",
                "---",
                "# Demo Skill",
            ]
        )
        + "\n",
    )
    report = SemanticReport()
    check_canonical_skill_packages_are_minimal(tmp_path, report)

    assert report.failures == []


def test_check_canonical_skill_packages_are_minimal_flags_deprecated_entrypoint_reference(
    tmp_path: Path,
) -> None:
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "---",
                "name: demo-skill",
                "description: Demo.",
                "---",
                "# Demo Skill",
                "1. Read `references/entrypoints.md`.",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_canonical_skill_packages_are_minimal(tmp_path, report)

    assert any("deprecated references/entrypoints.md" in item for item in report.failures)


def test_check_canonical_skill_packages_are_minimal_flags_deprecated_entrypoint_file(
    tmp_path: Path,
) -> None:
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "---",
                "name: demo-skill",
                "description: Demo.",
                "---",
                "# Demo Skill",
            ]
        )
        + "\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/references/entrypoints.md",
        "# Demo references\n\n## Reading Policy\n",
    )

    report = SemanticReport()
    check_canonical_skill_packages_are_minimal(tmp_path, report)

    assert any("deprecated references/entrypoints.md file" in item for item in report.failures)


def test_check_canonical_skill_packages_are_minimal_flags_adapter_leakage(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "---",
                "name: demo-skill",
                "description: Demo.",
                "---",
                "# Demo Skill",
                "## Backend Notes",
            ]
        )
        + "\n",
    )
    report = SemanticReport()
    check_canonical_skill_packages_are_minimal(tmp_path, report)

    assert any("Backend Notes" in item for item in report.failures)


def test_check_canonical_skill_packages_are_minimal_ignores_code_fence_headings(
    tmp_path: Path,
) -> None:
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "\n".join(
            [
                "---",
                "name: demo-skill",
                "description: Demo.",
                "---",
                "# Demo Skill",
                "```md",
                "## Backend Notes",
                "```",
            ]
        )
        + "\n",
    )
    report = SemanticReport()
    check_canonical_skill_packages_are_minimal(tmp_path, report)

    assert report.failures == []


def test_check_repo_python_commands_are_bytecode_free_flags_bare_repo_command(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "Run `python3 toolchain/scripts/test/folder_logic_check.py`.\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert any("review-verify-handbook.md:1" in item for item in report.failures)


def test_check_repo_python_commands_are_bytecode_free_flags_bare_python_repo_command(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/branch-pr-governance.md",
        "Run `python toolchain/scripts/test/folder_logic_check.py`.\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert any("branch-pr-governance.md:1" in item for item in report.failures)


def test_check_repo_python_commands_are_bytecode_free_flags_bare_python_module_command(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/branch-pr-governance.md",
        "Run `python -m pytest toolchain/scripts/test/test_folder_logic_check.py`.\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert any("branch-pr-governance.md:1" in item for item in report.failures)


def test_check_repo_python_commands_are_bytecode_free_accepts_prefixed_repo_command(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "Run `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`.\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert report.failures == []


def test_check_repo_python_commands_are_bytecode_free_flags_bare_tools_command(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "Run `python3 tools/closeout_acceptance_gate.py --json`.\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert any("review-verify-handbook.md:1" in item for item in report.failures)


def test_check_repo_python_commands_are_bytecode_free_checks_each_occurrence(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "toolchain/scripts/deploy/README.md",
        "`PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/deploy/aw_scaffold.py list` and "
        "`python3 -m pytest toolchain/scripts/test/test_folder_logic_check.py`\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert len(report.failures) == 1


def test_check_repo_python_commands_are_bytecode_free_skips_historical_log(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/testing/codex-harness-manual-run-continuous-2026-05-01.md",
        "`python3 -m unittest discover -s tests -v`\n",
    )

    report = SemanticReport()
    check_repo_python_commands_are_bytecode_free(tmp_path, report)

    assert report.failures == []
    assert is_bytecode_free_command_excluded(
        "docs/project-maintenance/testing/codex-harness-manual-run-continuous-2026-05-01.md"
    )
    assert not is_bytecode_free_command_excluded(
        "docs/project-maintenance/testing/codex-harness-manual-run-continuous-latest.md"
    )


def test_check_manual_runbook_agents_skill_count_accepts_matching_count(tmp_path: Path) -> None:
    for skill_id in ("harness-skill", "repo-status-skill"):
        write_doc(
            tmp_path / f"product/harness/adapters/agents/skills/{skill_id}/payload.json",
            "{}\n",
        )
    write_doc(
        tmp_path / "docs/project-maintenance/testing/codex-post-deploy-behavior-tests.md",
        "- 当前 `agents` install 已包含全部 2 个 skills，覆盖完整 Harness 控制回路\n",
    )

    report = SemanticReport()
    check_manual_runbook_agents_skill_count(tmp_path, report)

    assert report.failures == []


def test_check_manual_runbook_agents_skill_count_flags_mismatch(tmp_path: Path) -> None:
    for skill_id in ("harness-skill", "repo-status-skill", "repo-whats-next-skill"):
        write_doc(
            tmp_path / f"product/harness/adapters/agents/skills/{skill_id}/payload.json",
            "{}\n",
        )
    write_doc(
        tmp_path / "docs/project-maintenance/testing/codex-post-deploy-behavior-tests.md",
        "- 当前 `agents` install 已包含全部 2 个 skills，覆盖完整 Harness 控制回路\n",
    )

    report = SemanticReport()
    check_manual_runbook_agents_skill_count(tmp_path, report)

    assert any("documents 2, adapter payload source has 3" in item for item in report.failures)


def test_check_pre_milestone_intake_template_contract_accepts_required_terms_and_payloads(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "observed_facts",
            "inferred_assumptions",
            "unknowns",
            "programmer_decisions_required",
            "risk_flags",
            "open_questions",
            "why_it_matters",
            "recommended_answer",
            "tradeoff",
            "recommended_answers",
            "scope_boundary",
            "out_of_scope",
            "non_goals",
            "acceptance_signals",
            "suggested_milestone_brief",
            "confirmation_required",
            "programmer_confirmed",
            "ready_for_init_milestone",
            "intake_skipped",
            "skip_reason",
            "accepted_risk",
            "handoff_to_init_milestone",
            "template_contract_ref",
        ]
    )
    for relative_path in (
        "product/harness/skills/pre-milestone-intake-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    payload = {
        "canonical_paths": [
            "product/harness/skills/pre-milestone-intake-skill/SKILL.md",
            "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md",
        ],
        "required_payload_files": [
            "SKILL.md",
            "templates/pre-milestone-intake-review.template.md",
            "payload.json",
            "aw.marker",
        ],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/pre-milestone-intake-skill/payload.json",
        "product/harness/adapters/claude/skills/pre-milestone-intake-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_pre_milestone_intake_template_contract(tmp_path, report)

    assert report.failures == []


def test_check_pre_milestone_intake_template_contract_flags_payload_gap(tmp_path: Path) -> None:
    required_text = "\n".join(
        [
            "observed_facts",
            "inferred_assumptions",
            "unknowns",
            "programmer_decisions_required",
            "risk_flags",
            "open_questions",
            "why_it_matters",
            "recommended_answer",
            "tradeoff",
            "recommended_answers",
            "scope_boundary",
            "out_of_scope",
            "non_goals",
            "acceptance_signals",
            "suggested_milestone_brief",
            "confirmation_required",
            "programmer_confirmed",
            "ready_for_init_milestone",
            "intake_skipped",
            "skip_reason",
            "accepted_risk",
            "handoff_to_init_milestone",
            "template_contract_ref",
        ]
    )
    for relative_path in (
        "product/harness/skills/pre-milestone-intake-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, required_text)
    payload = {
        "canonical_paths": ["product/harness/skills/pre-milestone-intake-skill/SKILL.md"],
        "required_payload_files": ["SKILL.md", "payload.json", "aw.marker"],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/pre-milestone-intake-skill/payload.json",
        "product/harness/adapters/claude/skills/pre-milestone-intake-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_pre_milestone_intake_template_contract(tmp_path, report)

    assert any("missing canonical template path" in item for item in report.failures)
    assert any("missing required template file" in item for item in report.failures)


def test_check_init_milestone_intake_handoff_contract_accepts_required_terms(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "observed_facts",
            "inferred_assumptions",
            "unknowns",
            "programmer_decisions_required",
            "risk_flags",
            "open_questions",
            "why_it_matters",
            "recommended_answer",
            "tradeoff",
            "recommended_answers",
            "scope_boundary",
            "out_of_scope",
            "non_goals",
            "acceptance_signals",
            "suggested_milestone_brief",
            "confirmation_required",
            "programmer_confirmed",
            "ready_for_init_milestone",
            "intake_skipped",
            "skip_reason",
            "accepted_risk",
            "handoff_to_init_milestone",
            "template_contract_ref",
            "pre_milestone_intake_review",
            "intake_status",
            "request_summary",
            "ready",
            "skipped",
            "questions_required",
            "blocked",
            "missing",
            "handback",
            "approval",
            "不自动 create",
            "状态矛盾",
            "不得把薄弱的 milestone brief 伪装成已确认",
        ]
    )
    for relative_path in (
        "product/harness/skills/init-milestone-skill/SKILL.md",
        "docs/harness/catalog/milestone/init-milestone-skill.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    report = SemanticReport()
    check_init_milestone_intake_handoff_contract(tmp_path, report)

    assert report.failures == []


def test_check_init_milestone_intake_handoff_contract_flags_missing_state_semantics(
    tmp_path: Path,
) -> None:
    incomplete_text = "\n".join(
        [
            "observed_facts",
            "inferred_assumptions",
            "unknowns",
            "programmer_decisions_required",
            "risk_flags",
            "open_questions",
            "why_it_matters",
            "recommended_answer",
            "tradeoff",
            "recommended_answers",
            "scope_boundary",
            "out_of_scope",
            "non_goals",
            "acceptance_signals",
            "suggested_milestone_brief",
            "confirmation_required",
            "programmer_confirmed",
            "ready_for_init_milestone",
            "intake_skipped",
            "skip_reason",
            "accepted_risk",
            "handoff_to_init_milestone",
            "template_contract_ref",
            "pre_milestone_intake_review",
            "intake_status",
            "request_summary",
            "ready",
        ]
    )
    for relative_path in (
        "product/harness/skills/init-milestone-skill/SKILL.md",
        "docs/harness/catalog/milestone/init-milestone-skill.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, incomplete_text)

    report = SemanticReport()
    check_init_milestone_intake_handoff_contract(tmp_path, report)

    assert any("questions_required" in item for item in report.failures)
    assert any("不得把薄弱的 milestone brief 伪装成已确认" in item for item in report.failures)


def test_check_complex_project_entry_gate_contract_accepts_required_terms(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "complex_project_entry_gate",
            "scanner_evidence_ref",
            "complexity_signals",
            "operator_safety_policy",
            "dialog_review_questions",
            "milestone_blocking_decision",
            "reinforcement_milestone_recommendation",
            "Milestone-side blocking gate",
            "not fixed heavy mode",
            "scanner output is evidence",
            "normal",
            "autoreview",
            "yolo",
        ]
    )
    for relative_path in (
        "docs/harness/artifact/repo/complex-project-entry-gate.md",
        "docs/harness/artifact/control/milestone.md",
        "docs/harness/foundations/runtime-control-loop.md",
        "docs/harness/scope/repo-scope.md",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
        "docs/harness/catalog/repo.md",
        "docs/harness/catalog/milestone/init-milestone-skill.md",
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md",
        "product/harness/skills/init-milestone-skill/SKILL.md",
        "product/harness/skills/repo-whats-next-skill/SKILL.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    report = SemanticReport()
    check_complex_project_entry_gate_contract(tmp_path, report)

    assert report.failures == []


def test_check_complex_project_entry_gate_contract_flags_missing_safety_terms(
    tmp_path: Path,
) -> None:
    incomplete_text = "\n".join(
        [
            "complex_project_entry_gate",
            "scanner_evidence_ref",
            "complexity_signals",
            "operator_safety_policy",
            "Milestone-side blocking gate",
            "scanner output is evidence",
            "normal",
        ]
    )
    for relative_path in (
        "docs/harness/artifact/repo/complex-project-entry-gate.md",
        "docs/harness/artifact/control/milestone.md",
        "docs/harness/foundations/runtime-control-loop.md",
        "docs/harness/scope/repo-scope.md",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
        "docs/harness/catalog/repo.md",
        "docs/harness/catalog/milestone/init-milestone-skill.md",
        "product/harness/skills/harness-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/SKILL.md",
        "product/harness/skills/pre-milestone-intake-skill/templates/pre-milestone-intake-review.template.md",
        "product/harness/skills/init-milestone-skill/SKILL.md",
        "product/harness/skills/repo-whats-next-skill/SKILL.md",
    ):
        write_doc(tmp_path / relative_path, incomplete_text)

    report = SemanticReport()
    check_complex_project_entry_gate_contract(tmp_path, report)

    assert any("dialog_review_questions" in item for item in report.failures)
    assert any("reinforcement_milestone_recommendation" in item for item in report.failures)
    assert any("not fixed heavy mode" in item for item in report.failures)


def test_check_complexity_signal_scanner_contract_accepts_required_terms(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "complexity_signal_scanner.py",
            "scanner output is evidence",
            "thresholds",
            "complexity_signals",
            "compose",
            "service",
            "package",
            "CI",
            "deploy",
            "migration",
            "debt",
            "code",
            "no_network",
            "no_service_start",
            "secret_content_read",
        ]
    )
    for relative_path in (
        "toolchain/scripts/test/complexity_signal_scanner.py",
        "toolchain/scripts/test/test_complexity_signal_scanner.py",
        "toolchain/scripts/test/README.md",
        "docs/harness/artifact/repo/complex-project-entry-gate.md",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    report = SemanticReport()
    check_complexity_signal_scanner_contract(tmp_path, report)

    assert report.failures == []


def test_check_complexity_signal_scanner_contract_flags_missing_safety_terms(
    tmp_path: Path,
) -> None:
    required_without_safety = "\n".join(
        [
            "complexity_signal_scanner.py",
            "scanner output is evidence",
            "thresholds",
            "complexity_signals",
            "compose",
            "service",
            "package",
            "CI",
            "deploy",
            "migration",
            "debt",
            "code",
        ]
    )
    for relative_path in (
        "toolchain/scripts/test/complexity_signal_scanner.py",
        "toolchain/scripts/test/test_complexity_signal_scanner.py",
        "toolchain/scripts/test/README.md",
        "docs/harness/artifact/repo/complex-project-entry-gate.md",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
    ):
        write_doc(tmp_path / relative_path, required_without_safety)

    report = SemanticReport()
    check_complexity_signal_scanner_contract(tmp_path, report)

    assert any("no_network" in item for item in report.failures)
    assert any("no_service_start" in item for item in report.failures)
    assert any("secret_content_read" in item for item in report.failures)


def test_check_weak_doc_temporary_understanding_contract_accepts_required_terms_and_payloads(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "temporary-understanding.md",
            "temporary_understanding",
            "lightweight",
            "full",
            "token_budget_note",
            "token-cost tradeoff",
            "observed_facts",
            "inferred_purpose",
            "operational_purpose",
            "known_risks",
            "unknowns",
            "confirmation_questions",
            "programmer_decisions_required",
            "promotion_plan",
            "truth_boundary",
            "programmer confirmation",
            "verified evidence",
            "not Goal Charter truth",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    payload = {
        "canonical_paths": [
            "product/harness/skills/set-harness-goal-skill/SKILL.md",
            "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md",
        ],
        "required_payload_files": [
            "SKILL.md",
            "assets/repo/temporary-understanding.md",
            "payload.json",
            "aw.marker",
        ],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_weak_doc_temporary_understanding_contract(tmp_path, report)

    assert report.failures == []


def test_check_weak_doc_temporary_understanding_contract_flags_payload_gap(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "temporary-understanding.md",
            "temporary_understanding",
            "lightweight",
            "full",
            "token_budget_note",
            "token-cost tradeoff",
            "observed_facts",
            "inferred_purpose",
            "operational_purpose",
            "known_risks",
            "unknowns",
            "confirmation_questions",
            "programmer_decisions_required",
            "promotion_plan",
            "truth_boundary",
            "programmer confirmation",
            "verified evidence",
            "not Goal Charter truth",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, required_text)

    payload = {
        "canonical_paths": ["product/harness/skills/set-harness-goal-skill/SKILL.md"],
        "required_payload_files": ["SKILL.md", "payload.json", "aw.marker"],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_weak_doc_temporary_understanding_contract(tmp_path, report)

    assert any("missing canonical template path" in item for item in report.failures)
    assert any("missing required template file" in item for item in report.failures)


def test_check_weak_doc_temporary_understanding_contract_flags_truth_boundary_gap(
    tmp_path: Path,
) -> None:
    incomplete_text = "\n".join(
        [
            "temporary-understanding.md",
            "temporary_understanding",
            "lightweight",
            "full",
            "token_budget_note",
            "token-cost tradeoff",
            "observed_facts",
            "inferred_purpose",
            "operational_purpose",
            "known_risks",
            "unknowns",
            "confirmation_questions",
            "programmer_decisions_required",
            "promotion_plan",
            "programmer confirmation",
            "verified evidence",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
        "docs/harness/workflow-families/large-undocumented-repo-onboarding.md",
        "docs/harness/catalog/repo.md",
    ):
        write_doc(tmp_path / relative_path, incomplete_text)
    payload = {
        "canonical_paths": [
            "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md"
        ],
        "required_payload_files": ["assets/repo/temporary-understanding.md"],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_weak_doc_temporary_understanding_contract(tmp_path, report)

    assert any("truth_boundary" in item for item in report.failures)
    assert any("not Goal Charter truth" in item for item in report.failures)


def test_check_repo_init_complex_gate_contract_accepts_required_terms_and_payloads(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "complex-project-entry-gate.md",
            "complex_project_entry_gate",
            "scanner_evidence_ref",
            "complexity_signals",
            "operator_safety_policy",
            "dialog_review_questions",
            "milestone_blocking_decision",
            "reinforcement_milestone_recommendation",
            "repo-init",
            "Milestone-side blocking gate",
            "not fixed heavy mode",
            "scanner output is evidence",
            "weak-doc",
            "trigger_conditions: pending_observed_signal_review",
            "Record only observed signals in trigger_conditions",
            "allowed_high_risk_command_modes: pending_programmer_confirmation",
            "entry_verdict: blocked",
            "milestone_blocking_decision: block_derive_worktrack",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/README.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/README.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/complex-project-entry-gate.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
    ):
        write_doc(tmp_path / relative_path, required_text)

    payload = {
        "canonical_paths": [
            "product/harness/skills/set-harness-goal-skill/assets/repo/complex-project-entry-gate.md",
        ],
        "required_payload_files": [
            "assets/repo/complex-project-entry-gate.md",
        ],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_repo_init_complex_gate_contract(tmp_path, report)

    assert report.failures == []


def test_check_repo_init_complex_gate_contract_flags_payload_gap(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "complex-project-entry-gate.md",
            "complex_project_entry_gate",
            "scanner_evidence_ref",
            "complexity_signals",
            "operator_safety_policy",
            "dialog_review_questions",
            "milestone_blocking_decision",
            "reinforcement_milestone_recommendation",
            "repo-init",
            "Milestone-side blocking gate",
            "not fixed heavy mode",
            "scanner output is evidence",
            "weak-doc",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/README.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/README.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/complex-project-entry-gate.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
    ):
        write_doc(tmp_path / relative_path, required_text)

    payload = {
        "canonical_paths": ["product/harness/skills/set-harness-goal-skill/SKILL.md"],
        "required_payload_files": ["SKILL.md"],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_repo_init_complex_gate_contract(tmp_path, report)

    assert any("missing canonical template path" in item for item in report.failures)
    assert any("missing required template file" in item for item in report.failures)


def test_check_repo_init_complex_gate_contract_flags_unsafe_template_defaults(
    tmp_path: Path,
) -> None:
    required_text = "\n".join(
        [
            "complex-project-entry-gate.md",
            "complex_project_entry_gate",
            "scanner_evidence_ref",
            "complexity_signals",
            "operator_safety_policy",
            "dialog_review_questions",
            "milestone_blocking_decision",
            "reinforcement_milestone_recommendation",
            "repo-init",
            "Milestone-side blocking gate",
            "not fixed heavy mode",
            "scanner output is evidence",
            "weak-doc",
        ]
    )
    safe_text = "\n".join(
        [
            required_text,
            "trigger_conditions: pending_observed_signal_review",
            "Record only observed signals in trigger_conditions",
            "allowed_high_risk_command_modes: pending_programmer_confirmation",
            "entry_verdict: blocked",
            "milestone_blocking_decision: block_derive_worktrack",
        ]
    )
    for relative_path in (
        "product/harness/skills/set-harness-goal-skill/SKILL.md",
        "product/harness/skills/set-harness-goal-skill/assets/README.md",
        "product/harness/skills/set-harness-goal-skill/assets/repo/README.md",
        "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js",
    ):
        write_doc(tmp_path / relative_path, safe_text)

    unsafe_template = "\n".join(
        [
            required_text,
            "trigger_conditions:",
            "    - normal",
            "    - autoreview",
            "    - yolo",
            "entry_verdict:",
        ]
    )
    write_doc(
        tmp_path
        / "product/harness/skills/set-harness-goal-skill/assets/repo/complex-project-entry-gate.md",
        unsafe_template,
    )

    payload = {
        "canonical_paths": [
            "product/harness/skills/set-harness-goal-skill/assets/repo/complex-project-entry-gate.md",
        ],
        "required_payload_files": [
            "assets/repo/complex-project-entry-gate.md",
        ],
    }
    for relative_path in (
        "product/harness/adapters/agents/skills/set-harness-goal-skill/payload.json",
        "product/harness/adapters/claude/skills/set-harness-goal-skill/payload.json",
    ):
        write_doc(tmp_path / relative_path, f"{json.dumps(payload)}\n")

    report = SemanticReport()
    check_repo_init_complex_gate_contract(tmp_path, report)

    assert any("missing safe default" in item for item in report.failures)
    assert any("must not pre-authorize" in item for item in report.failures)


def test_governance_semantic_cli_disables_bytecode_before_local_import(tmp_path: Path) -> None:
    source_script = Path(__file__).resolve().parent / "governance_semantic_check.py"
    write_doc(tmp_path / "governance_semantic_check.py", source_script.read_text(encoding="utf-8"))
    write_doc(
        tmp_path / "path_governance_check.py",
        "\n".join(
            [
                "def iter_relative_markdown_targets(text):",
                "    return []",
                "",
                "def resolve_markdown_target(markdown_file, repo_root, target):",
                "    return repo_root / target",
            ]
        )
        + "\n",
    )

    env = os.environ.copy()
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
        [sys.executable, str(tmp_path / "governance_semantic_check.py"), "--repo-root", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 1
    assert not list(tmp_path.rglob("__pycache__"))
    assert not list(tmp_path.rglob("*.pyc"))


def test_check_root_tool_shims_disable_bytecode_flags_late_guard(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "tools/scope_gate_check.py",
        "\n".join(
            [
                "import sys",
                "from toolchain.scripts.test.scope_gate_check import main",
                "sys.dont_write_bytecode = True",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_root_tool_shims_disable_bytecode(tmp_path, report)

    assert any("tools/scope_gate_check.py" in item for item in report.failures)


def test_check_root_tool_shims_disable_bytecode_accepts_guard_before_import(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "tools/scope_gate_check.py",
        "\n".join(
            [
                "import sys",
                "sys.dont_write_bytecode = True",
                "from toolchain.scripts.test.scope_gate_check import main",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_root_tool_shims_disable_bytecode(tmp_path, report)

    assert report.failures == []


def test_check_path_governance_docs_list_gitignore_entries_flags_missing_entry(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/path-governance-checks.md",
        "` .servo/ `\n",
    )

    report = SemanticReport()
    check_path_governance_docs_list_gitignore_entries(tmp_path, report)

    assert any(".agents/" in item for item in report.failures)


def test_check_path_governance_docs_list_gitignore_entries_accepts_complete_list(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/path-governance-checks.md",
        "\n".join(
            [
                "`.servo/`",
                "`.agents/`",
                "`.claude/`",
                "`.autoworkflow/`",
                "`.spec-workflow/`",
                "`.logs/`",
                "`**/__pycache__/`",
                "`.pytest_cache/`",
                "`*.pyc`",
                "`*.pyo`",
            ]
        )
        + "\n",
    )

    report = SemanticReport()
    check_path_governance_docs_list_gitignore_entries(tmp_path, report)

    assert report.failures == []


def test_check_review_verify_docs_list_closeout_steps_flags_missing_step(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "scope_gate -> spec_gate -> static_gate -> test_gate -> smoke_gate\n",
    )

    report = SemanticReport()
    check_review_verify_docs_list_closeout_steps(tmp_path, report)

    assert any("cache_gate" in item for item in report.failures)


def test_check_review_verify_docs_list_closeout_steps_accepts_complete_sequence(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "scope_gate -> spec_gate -> static_gate -> cache_gate -> test_gate -> smoke_gate\n",
    )

    report = SemanticReport()
    check_review_verify_docs_list_closeout_steps(tmp_path, report)

    assert report.failures == []


def test_check_docs_list_closeout_cache_roots_flags_missing_root(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md",
        "`docs/` `product/` `toolchain/`\n",
    )
    write_doc(
        tmp_path / "toolchain/scripts/test/README.md",
        "`docs/` `product/` `toolchain/` `tools/`\n",
    )

    report = SemanticReport()
    check_docs_list_closeout_cache_roots(tmp_path, report)

    assert any("tools" in item for item in report.failures)


def test_check_docs_list_closeout_cache_roots_accepts_complete_roots(tmp_path: Path) -> None:
    roots = "`docs/` `product/` `toolchain/` `tools/`\n"
    write_doc(tmp_path / "docs/project-maintenance/governance/review-verify-handbook.md", roots)
    write_doc(tmp_path / "toolchain/scripts/test/README.md", roots)

    report = SemanticReport()
    check_docs_list_closeout_cache_roots(tmp_path, report)

    assert report.failures == []


def test_check_orphan_docs_accepts_canonical_skill_only_reference(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/repo/goal-charter.md",
        "# Goal Charter\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/demo-skill/SKILL.md",
        "[goal charter](../../../../docs/harness/artifact/repo/goal-charter.md)\n",
    )

    report = SemanticReport()
    check_orphan_docs(tmp_path, report)

    assert report.failures == []


def test_check_artifact_skill_alignment_all_fields_pass(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/skills/gate-skill/SKILL.md",
        "\n".join([
            "# Gate Skill",
            "",
            "verdict: pass or fail",
            "review_dimensions: correctness completeness consistency",
            "",
        ]) + "\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "\n".join([
            "# Contract Template",
            "",
            "node_type: feature",
            "baseline_form: commit-on-feature-branch",
            "merge_required: true",
            "gate_criteria: standard",
            "if_interrupted_strategy: stop",
            "runtime_dispatch_mode: auto",
            "",
        ]) + "\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/schedule-worktrack-skill/SKILL.md",
        "\n".join([
            "# Schedule Worktrack Skill",
            "",
            "task_id: T-001",
            "status: pending",
            "priority: high",
            "depends_on: []",
            "acceptance: all tests pass",
            "",
        ]) + "\n",
    )

    report = SemanticReport()
    check_artifact_skill_alignment(tmp_path, report)

    assert report.failures == []


def test_check_artifact_skill_alignment_missing_skill_file(tmp_path: Path) -> None:
    report = SemanticReport()
    check_artifact_skill_alignment(tmp_path, report)

    assert len(report.failures) > 0
    assert any("missing skill file" in f for f in report.failures)


def _write_runtime_artifacts(
    tmp_path: Path,
    *,
    active_milestone: str = "MS-001",
    active_worktrack: str = "none",
    milestone_status: str = "active",
    summary: str = "planned=0 / active=1 / completed=1 / superseded=0",
    backlog_entries: str | None = None,
    history_entries: str | None = None,
    milestone_artifact_status: str = "active",
    milestone_artifact_completed: int = 0,
    milestone_artifact_total: int = 1,
    milestone_artifact_worktrack_status: str = "planned",
    milestone_artifact_worktrack_status_key: str = "status",
) -> None:
    write_doc(
        tmp_path / ".servo/control-state.md",
        "\n".join(
            [
                "# Harness Control State",
                "",
                "## Active Worktrack",
                f"- active_worktrack: {active_worktrack}",
                "- latest_closed_worktrack: none",
                "",
                "## Milestone Pipeline",
                f"- active_milestone: {active_milestone}",
                f"- milestone_status: {milestone_status}",
                f"- milestone_pipeline_summary: {summary}",
                "",
            ]
        ),
    )
    if backlog_entries is None:
        backlog_entries = "\n".join(
            [
                "- milestone_id: MS-001",
                "  - status: active",
                "  - worktrack_list:",
                "    - WT-001 (planned)",
                "",
            ]
        )
    if history_entries is None:
        history_entries = "\n".join(
            [
                "- milestone_id: MS-000",
                "  - status: completed",
                "  - acceptance:",
                "    - verdict: accepted",
                "  - worktrack_list:",
                "    - WT-000 (done)",
                "",
            ]
        )
    write_doc(
        tmp_path / ".servo/repo/milestone-backlog.md",
        "# Repo Milestone Backlog\n\n## Pipeline Entries\n\n" + backlog_entries,
    )
    write_doc(
        tmp_path / ".servo/repo/milestone-history.md",
        "# Repo Milestone History\n\n## History Entries\n\n" + history_entries,
    )
    write_doc(
        tmp_path / ".servo/milestone/MS-001.md",
        "\n".join(
            [
                "# Test Milestone",
                "",
                "## milestone_id",
                'milestone_id: "MS-001"',
                "",
                "## status",
                f'status: "{milestone_artifact_status}"',
                "",
                "## worktrack_list",
                "worktrack_list:",
                '  - worktrack_id: "WT-001"',
                f'    {milestone_artifact_worktrack_status_key}: "{milestone_artifact_worktrack_status}"',
                "",
                "## progress_counter",
                "progress_counter:",
                f"  total: {milestone_artifact_total}",
                f"  completed: {milestone_artifact_completed}",
                "  blocked: 0",
                "  deferred: 0",
                "",
            ]
        ),
    )
    write_doc(
        tmp_path / ".servo/milestone/MS-000.md",
        "\n".join(
            [
                "# Completed Test Milestone",
                "",
                "## milestone_id",
                'milestone_id: "MS-000"',
                "",
                "## status",
                'status: "completed"',
                "",
                "## worktrack_list",
                "worktrack_list:",
                '  - worktrack_id: "WT-000"',
                '    status: "completed"',
                "",
                "## progress_counter",
                "progress_counter:",
                "  total: 1",
                "  completed: 1",
                "  blocked: 0",
                "  deferred: 0",
                "",
            ]
        ),
    )


def test_check_runtime_artifact_consistency_noops_without_servo(tmp_path: Path) -> None:
    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert report.failures == []
    assert any(".servo/ directory missing" in item for item in report.infos)


def test_check_runtime_artifact_consistency_accepts_consistent_state(tmp_path: Path) -> None:
    _write_runtime_artifacts(tmp_path)

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert report.failures == []


def test_check_runtime_artifact_consistency_flags_missing_active_pointer(tmp_path: Path) -> None:
    _write_runtime_artifacts(tmp_path, active_milestone="MS-MISSING")

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("active_milestone MS-MISSING is missing" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_summary_mismatch(tmp_path: Path) -> None:
    _write_runtime_artifacts(tmp_path, summary="planned=1 / active=0 / completed=1 / superseded=0")

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("milestone_pipeline_summary mismatch" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_multiple_active_milestones(tmp_path: Path) -> None:
    _write_runtime_artifacts(
        tmp_path,
        summary="planned=0 / active=2 / completed=0 / superseded=0",
        backlog_entries="\n".join(
            [
                "- milestone_id: MS-001",
                "  - status: active",
                "  - worktrack_list:",
                "    - WT-001 (planned)",
                "",
                "- milestone_id: MS-002",
                "  - status: active",
                "  - worktrack_list:",
                "    - WT-002 (planned)",
                "",
            ]
        ),
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("multiple active milestones" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_completed_milestone_planned_worktrack(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_milestone="none",
        milestone_status="none",
        summary="planned=0 / active=0 / completed=1 / superseded=0",
        backlog_entries="",
        history_entries="\n".join(
            [
                "- milestone_id: MS-001",
                "  - status: completed",
                "  - acceptance:",
                "    - verdict: accepted",
                "  - worktrack_list:",
                "    - WT-001 (planned)",
                "",
            ]
        ),
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("unfinished worktrack markers" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_history_status_in_live_backlog(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_milestone="none",
        milestone_status="none",
        summary="planned=0 / active=0 / completed=1 / superseded=0",
        backlog_entries="\n".join(
            [
                "- milestone_id: MS-001",
                "  - status: completed",
                "  - worktrack_list:",
                "    - WT-001 (done)",
                "",
            ]
        ),
        history_entries="",
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("live milestone backlog contains history status" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_completed_artifact_still_live(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        milestone_artifact_status="completed",
        milestone_artifact_completed=1,
        milestone_artifact_worktrack_status="completed",
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("completed/superseded milestone artifact MS-001 remains live" in item for item in report.failures)
    assert any("active_milestone MS-001 points to completed/superseded" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_active_worktrack_closed(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_worktrack="WT-001",
        milestone_artifact_worktrack_status="completed",
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("active_worktrack WT-001 points to closed worktrack" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_active_worktrack_closed_expected_status(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_worktrack="WT-001",
        milestone_artifact_status="completed",
        milestone_artifact_worktrack_status="completed",
        milestone_artifact_worktrack_status_key="expected_status",
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("active_worktrack WT-001 points to closed worktrack" in item for item in report.failures)


def test_check_runtime_artifact_consistency_allows_active_expected_status_completed(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_worktrack="WT-001",
        milestone_artifact_status="active",
        milestone_artifact_worktrack_status="completed",
        milestone_artifact_worktrack_status_key="expected_status",
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert report.failures == []


def test_check_runtime_artifact_consistency_flags_completed_artifact_incomplete_progress(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        active_milestone="none",
        milestone_status="none",
        summary="planned=0 / active=0 / completed=1 / superseded=0",
        backlog_entries="",
        history_entries="\n".join(
            [
                "- milestone_id: MS-001",
                "  - status: completed",
                "  - acceptance:",
                "    - verdict: accepted",
                "  - worktrack_list:",
                "    - WT-001 (done)",
                "",
            ]
        ),
        milestone_artifact_status="completed",
        milestone_artifact_completed=0,
        milestone_artifact_total=1,
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("completed milestone artifact MS-001 has incomplete progress 0/1" in item for item in report.failures)


def test_check_runtime_artifact_consistency_allows_legacy_completed_artifact_not_in_history(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        milestone_artifact_status="active",
    )
    write_doc(
        tmp_path / ".servo/milestone/MS-LEGACY.md",
        "\n".join(
            [
                "# Legacy Completed Milestone",
                "",
                "## milestone_id",
                'milestone_id: "MS-LEGACY"',
                "",
                "## status",
                'status: "completed"',
                "",
                "## worktrack_list",
                "worktrack_list:",
                '  - worktrack_id: "WT-LEGACY"',
                '    expected_status: "done"',
                "",
                "## progress_counter",
                "progress_counter:",
                "  total: 1",
                "  completed: 1",
                "  blocked: 0",
                "  deferred: 0",
                "",
            ]
        ),
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert report.failures == []


def test_runtime_artifact_consistency_simulation_matches_expected_outcomes() -> None:
    results = [run_scenario(scenario) for scenario in SCENARIOS]

    assert all(result["expected_pass"] == result["actual_pass"] for result in results)
    failures_by_id = {
        str(result["scenario_id"]): list(result["failures"])
        for result in results
    }
    assert failures_by_id["consistent-active"] == []
    assert any("remains live as status 'active'" in item for item in failures_by_id["completed-artifact-still-live"])
    assert any("active_worktrack WT-001 points to closed worktrack" in item for item in failures_by_id["active-worktrack-closed"])
    assert any("incomplete progress 0/1" in item for item in failures_by_id["completed-artifact-incomplete-progress"])
    assert failures_by_id["active-expected-status-completed"] == []


def test_check_runtime_artifact_consistency_flags_live_status_in_history(
    tmp_path: Path,
) -> None:
    _write_runtime_artifacts(
        tmp_path,
        summary="planned=0 / active=1 / completed=0 / superseded=0",
        history_entries="\n".join(
            [
                "- milestone_id: MS-002",
                "  - status: planned",
                "  - worktrack_list:",
                "    - WT-002 (planned)",
                "",
            ]
        ),
    )

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("milestone-history contains live status" in item for item in report.failures)


def test_check_runtime_artifact_consistency_flags_malformed_summary(tmp_path: Path) -> None:
    _write_runtime_artifacts(tmp_path, summary="active milestone only")

    report = SemanticReport()
    check_runtime_artifact_consistency(tmp_path, report)

    assert any("milestone_pipeline_summary is missing or malformed" in item for item in report.failures)
