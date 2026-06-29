#!/usr/bin/env python3
"""
Milestone Gate 聚合治理测试

覆盖：
- 聚合器 4-step 逻辑（weight/contradiction/composite_lane/degenerate）
- 轴 skill 结构验证（isolation_guarantee, SubAgent fallback）
- 分拆路由验证（sensor→gate skill 引用, harness conditional binding）

用法：PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/test_milestone_gate_aggregation.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = REPO_ROOT / "product" / "harness" / "skills"
FAILURES: list[str] = []


# ---------- helpers ----------


def fail(msg: str) -> None:
    FAILURES.append(msg)


def read_skill(path: str) -> str:
    full = SKILLS_DIR / path / "SKILL.md"
    if not full.exists():
        fail(f"missing SKILL.md: {path}")
        return ""
    return full.read_text(encoding="utf-8")


def read_repo_file(path: str) -> str:
    full = REPO_ROOT / path
    if not full.exists():
        fail(f"missing file: {path}")
        return ""
    return full.read_text(encoding="utf-8")


# ---------- 1. Aggregator logic tests ----------


def simulate_weight_calc(
    worktracks: list[dict],
    overrides: list[dict] | None = None,
) -> list[dict]:
    """Simulate Step 1: weight_rules."""
    default_weights = {
        "critical": 5,
        "feature": 4,
        "release": 4,
        "config": 3,
        "test": 3,
        "docs": 2,
        "demo": 1,
    }
    results = []
    override_map = {}
    if overrides:
        for o in overrides:
            override_map[o["worktrack_id"]] = o

    for wt in worktracks:
        node = wt.get("node_type", "unknown")
        base = default_weights.get(node, 2)
        final = base
        overridden = False
        reason = None
        if wt["worktrack_id"] in override_map:
            ov = override_map[wt["worktrack_id"]]
            final = ov["weight"]
            overridden = True
            reason = ov.get("reason", "")
        results.append(
            {
                "worktrack_id": wt["worktrack_id"],
                "node_type": node,
                "base_weight": base,
                "final_weight": final,
                "overridden": overridden,
                "override_reason": reason,
            }
        )
    return results


def detect_contradictions(
    weighted: list[dict],
    verdicts: dict[str, str],
    threshold: int = 3,
) -> tuple[list[dict], bool]:
    """Simulate Step 2: contradiction_rules."""
    findings = []
    blocked = False
    mismatch_pairs = {
        ("pass", "hard_fail"),
        ("pass", "blocked"),
        ("hard_fail", "pass"),
        ("blocked", "pass"),
    }

    for i, a in enumerate(weighted):
        for b in weighted[i + 1 :]:
            if a["final_weight"] >= threshold and b["final_weight"] >= threshold:
                va = verdicts[a["worktrack_id"]]
                vb = verdicts[b["worktrack_id"]]
                if (va, vb) in mismatch_pairs:
                    findings.append(
                        {
                            "wt_a_id": a["worktrack_id"],
                            "verdict_a": va,
                            "wt_b_id": b["worktrack_id"],
                            "verdict_b": vb,
                            "severity": "high",
                            "recommended_resolution": "new_verification_worktrack",
                        }
                    )
                    blocked = True
    return findings, blocked


def check_degenerate_conditions(
    contradiction_blocked: bool,
    anticheat_high: bool,
    axis_verdicts: dict[str, str],
    verdicts: dict[str, str],
    overrides_applied: bool,
    weighted: list[dict],
) -> tuple[bool, str]:
    """Simulate Step 4: degenerate_and_rules."""
    all_critical_pass = all(
        w["final_weight"] < 4 or verdicts.get(w["worktrack_id"]) == "pass"
        for w in weighted
    )
    lanes_consistent = (
        len(set(axis_verdicts.values())) == 1 and "pass" in axis_verdicts.values()
    )

    if (
        not contradiction_blocked
        and not anticheat_high
        and lanes_consistent
        and not overrides_applied
        and all_critical_pass
    ):
        return (
            True,
            "Degenerate AND: no contradiction, no anti-cheat high, all lanes consistent, all critical WTs pass",
        )
    return False, "N/A"


def compute_verdict(
    weighted: list[dict],
    verdicts: dict[str, str],
    axis_verdicts: dict[str, str],
    contradiction_blocked: bool,
    degenerate_applied: bool,
) -> str:
    """Simulate final verdict (priority order from aggregation contract)."""
    # Priority 1: veto-power axes
    for axis in ("blackbox", "whitebox", "anticheat"):
        if axis_verdicts.get(axis) in ("hard_fail", "blocked"):
            return "blocked"
    # Priority 2: contradiction
    if contradiction_blocked:
        return "blocked"
    # Priority 3: per-WT
    critical_fails = [
        w
        for w in weighted
        if w["final_weight"] >= 4 and verdicts.get(w["worktrack_id"]) == "hard_fail"
    ]
    heavy_fails = [
        w
        for w in weighted
        if w["final_weight"] >= 3 and verdicts.get(w["worktrack_id"]) == "hard_fail"
    ]
    if critical_fails:
        return "hard_fail"
    if heavy_fails:
        return "soft_fail"
    # Priority 4: degenerate
    if degenerate_applied:
        return "pass"
    return "pass"


# ---------- 2. Axis report schema validation ----------

CANONICAL_AXIS_IDS = {"blackbox", "whitebox", "anticheat", "composite"}
LEGACY_AXIS_IDS = {"black_box", "white_box", "anti_cheat"}
VALID_AXIS_APPLICABILITY_STATES = {
    "applicable",
    "not_applicable",
    "substituted",
    "split",
    "blocked",
}
VALID_DISPATCH_MODELS = {
    "sibling_delegated",
    "mixed",
    "current_carrier_fallback",
    "missing",
}
REQUIRED_AXIS_REPORT_FIELDS = {
    "axis",
    "verdict",
    "severity",
    "checklist_results",
    "carrier",
    "isolation_guarantee",
    "carrier_isolation_broken",
    "report_ref",
    "observed_git_hash",
    "target_type",
    "axis_applicability_state",
    "axis_applicability_reason",
    "expected_method",
    "runtime_dispatch_profile",
    "missing_evidence",
}
REQUIRED_SUBSTITUTED_AXIS_REPORT_FIELDS = {
    "substitute_method",
    "substitution_evidence_ref",
    "substitute_verdict",
    "evidence_covers_completion_signal",
}
REQUIRED_AXIS_RUNTIME_DISPATCH_PROFILE_FIELDS = {
    "backend_runtime",
    "model_family",
    "subagent_dispatch_shell",
    "runtime_supports_subagent",
    "subagent_permission_state",
    "permission_allows_delegation",
    "dispatch_package_safety",
    "delegation_attempted",
    "attempted_carrier",
    "carrier_decision",
    "fallback_reason",
}
REQUIRED_AXIS_DISPATCH_PROFILE_FIELDS = {
    "dispatch_owner",
    "dispatch_model",
    "required_axes",
    "completed_axes",
    "missing_axes",
    "delegation_attempted_by_axis",
    "same_carrier_cross_axis",
    "carrier_isolation_broken_any",
    "dispatch_gap_reason",
    "per_axis_runtime_dispatch_profile",
    "nested_axis_dispatch_attempted",
}
VALID_AXIS_REPORT_STATUSES = {
    "complete",
    "missing",
    "contaminated",
    "isolation_broken",
    "blocked_axis",
}
VALID_AXIS_REPORT_STATUS_BY_AXIS = {
    "present",
    "missing",
    "stale",
    "contaminated",
    "blocked",
}
MANUAL_EXCEPTION_PRESERVATION_FIELDS = {
    "accepted_gate_verdict_preserved_as",
    "anti_cheat_findings_preserved",
    "historical_gap_preserved",
    "manual_exception_followup_ref",
}
ANTICHEAT_SEVERITY_DEFAULTS = {
    "A1": "high",
    "A2": "high",
    "A3": "high",
    "A4": "high",
    "A5": "high",
    "A6": "medium",
    "A7": "high",
}
ANTICHEAT_SEVERITY_REQUIRED_FIELDS = {
    "default_severity",
    "soft_fail_triggers",
    "hard_fail_triggers",
    "blocking_triggers",
    "aggregation_impact",
}
ANTICHEAT_HISTORICAL_GAP_REQUIRED_TERMS = [
    "historical_gap is visible non-positive evidence",
    "distinct from missing, incomplete, and contaminated",
    "not a waiver",
    "not a pass",
    "manual exception",
    "historical_gap_preserved",
]
CONTRACT_SCHEMA_FILES = [
    "product/harness/skills/milestone-gate/SKILL.md",
    "product/harness/skills/milestone-status-skill/SKILL.md",
    "product/harness/skills/harness-skill/SKILL.md",
    "docs/harness/artifact/standard-fields.md",
    "docs/harness/artifact/control/milestone.md",
    "docs/harness/artifact/control/milestone-gate-aggregation.md",
]
FORBIDDEN_SCHEMA_TOKENS = {
    "gate_axis_reports",
    "gate_axis_dispatch_profile",
    "gate_axis_applicability",
    "black_box",
    "white_box",
    "sibling_axis_carriers",
}
FORBIDDEN_SCHEMA_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9_])axis_verdict(?![A-Za-z0-9_])"),
]

CLOSEOUT_EVIDENCE_BUNDLE_TOP_LEVEL_FIELDS = {
    "schema_version",
    "worktrack_id",
    "milestone_id",
    "node_type",
    "branch_policy",
    "self_review_record",
    "single_acceptance_verdict",
    "worktrack_gate_evidence",
    "closeout_gate_evidence",
    "dispatch_provenance",
    "composite_lane_records",
    "repo_refresh_checkpoint",
    "bundle_completeness",
}
BRANCH_POLICY_FIELDS = {
    "baseline_branch",
    "branch_source_ref",
    "worktrack_branch",
    "integration_target_ref",
    "closeout_target_ref",
    "checkpoint_base_ref",
    "final_baseline_branch",
}
SELF_REVIEW_RECORD_FIELDS = {"status", "record_ref", "verdict"}
SINGLE_ACCEPTANCE_VERDICT_FIELDS = {
    "status",
    "verdict_ref",
    "verdict",
    "critical_failure",
}
WORKTRACK_GATE_EVIDENCE_FIELDS = {
    "status",
    "evidence_ref",
    "gate_verdict",
    "implementation_gate",
    "validation_gate",
    "policy_gate",
}
CLOSEOUT_GATE_EVIDENCE_FIELDS = {"status", "evidence_ref", "verdict"}
REPO_REFRESH_CHECKPOINT_FIELDS = {
    "status",
    "checkpoint_ref",
    "latest_observed_checkpoint",
}
BUNDLE_COMPLETENESS_FIELDS = {
    "status",
    "missing_required_fields",
    "historical_gap_fields",
    "contaminated_fields",
    "residual_risks",
}
DISPATCH_PROVENANCE_FIELDS = {
    "status",
    "runtime_dispatch_record_ref",
    "subagent_dispatch_record_refs",
    "missing_dispatch_record_refs",
    "dispatch_result_status",
    "resolved_runtime_dispatch_status",
    "implementer_carrier",
    "reviewer_carrier_refs",
    "gate_judge_carrier_ref",
    "independence_summary",
}
COMPOSITE_LANE_LINK_FIELDS = {
    "status",
    "record_ref",
    "lane_id",
    "validation_ref",
    "producer_ref",
    "missing_required_fields",
    "contaminated_reason",
    "not_applicable_reason",
}
COMPOSITE_LANE_KEYS = {
    "code_review": "code-review",
    "feature_completeness": "feature-completeness",
    "related_influence": "related-influence",
    "intent_completeness": "intent-completeness",
    "operator_simulation": "operator-simulation",
    "professional_review": "professional-review",
}
VISIBLE_EVIDENCE_STATES = {
    "captured",
    "linked",
    "incomplete",
    "missing",
    "historical_gap",
    "contaminated",
    "not_applicable",
}
VALID_OPTIONAL_EVIDENCE_STATES = {
    "captured",
    "linked",
    "missing",
    "historical_gap",
    "not_applicable",
}
VALID_WORKTRACK_GATE_EVIDENCE_STATES = {
    "captured",
    "linked",
    "missing",
    "historical_gap",
}
VALID_DISPATCH_PROVENANCE_STATES = {
    "captured",
    "linked",
    "incomplete",
    "missing",
    "historical_gap",
    "contaminated",
}
VALID_DISPATCH_RESULT_STATUSES = {
    "delegated",
    "current_carrier_fallback",
    "permission_blocked",
    "runtime_gap",
    "dispatch_package_unsafe",
    "blocked",
    "historical_gap",
    "N/A",
}
VALID_RESOLVED_RUNTIME_DISPATCH_STATUSES = {
    "delegated",
    "current_carrier_fallback",
    "permission_blocked",
    "runtime_gap",
    "dispatch_package_unsafe",
    "blocked",
    "historical_gap",
    "incomplete",
    "missing",
    "contaminated",
}
VALID_INDEPENDENCE_SUMMARIES = {
    "independent",
    "same_carrier",
    "unknown",
    "historical_gap",
}
VALID_BUNDLE_COMPLETENESS_STATUSES = {
    "complete",
    "incomplete",
    "contaminated",
    "historical_gap",
}


def _add_missing_fields(
    errors: list[str],
    value: dict,
    required_fields: set[str],
    path: str,
) -> None:
    missing = sorted(required_fields - set(value))
    if missing:
        errors.append(f"{path}: missing fields {missing}")


def _require_object(errors: list[str], value: object, path: str) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path}: must be an object")
        return False
    return True


def _require_list(errors: list[str], value: object, path: str) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: must be a list")


def _validate_status(
    errors: list[str],
    value: object,
    allowed: set[str],
    path: str,
) -> None:
    if value not in allowed:
        errors.append(f"{path}: invalid status {value!r}")


def validate_axis_report_bundle(payload: dict) -> list[str]:
    errors: list[str] = []
    reports = payload.get("axis_reports")
    if not isinstance(reports, dict):
        return ["axis_reports must be an object"]

    report_keys = set(reports)
    legacy_keys = sorted(report_keys & LEGACY_AXIS_IDS)
    if legacy_keys:
        errors.append(f"legacy axis ids present: {legacy_keys}")

    missing_axes = sorted(CANONICAL_AXIS_IDS - report_keys)
    if missing_axes:
        errors.append(f"missing canonical axis reports: {missing_axes}")

    unexpected_axes = sorted(report_keys - CANONICAL_AXIS_IDS - LEGACY_AXIS_IDS)
    if unexpected_axes:
        errors.append(f"unexpected axis report keys: {unexpected_axes}")

    for axis, report in reports.items():
        if not isinstance(report, dict):
            errors.append(f"{axis}: report must be an object")
            continue
        if axis in CANONICAL_AXIS_IDS and report.get("axis") != axis:
            errors.append(f"{axis}: axis field must equal report key")
        if report.get("axis") in LEGACY_AXIS_IDS:
            errors.append(f"{axis}: legacy axis value {report.get('axis')!r}")
        if "axis_verdict" in report:
            errors.append(f"{axis}: use verdict, not axis_verdict")
        if "axis_applicability" in report:
            errors.append(f"{axis}: report uses axis_applicability instead of axis_applicability_state")
        missing_fields = sorted(REQUIRED_AXIS_REPORT_FIELDS - set(report))
        if axis in CANONICAL_AXIS_IDS and missing_fields:
            errors.append(f"{axis}: missing fields {missing_fields}")
        state = report.get("axis_applicability_state")
        if state is not None and state not in VALID_AXIS_APPLICABILITY_STATES:
            errors.append(f"{axis}: invalid axis_applicability_state {state!r}")
        if axis in CANONICAL_AXIS_IDS and state == "substituted":
            substituted_missing = sorted(
                REQUIRED_SUBSTITUTED_AXIS_REPORT_FIELDS - set(report)
            )
            if substituted_missing:
                errors.append(
                    f"{axis}: substituted axis missing fields {substituted_missing}"
                )
        runtime_profile = report.get("runtime_dispatch_profile")
        if axis in CANONICAL_AXIS_IDS and _require_object(
            errors, runtime_profile, f"{axis}.runtime_dispatch_profile"
        ):
            _add_missing_fields(
                errors,
                runtime_profile,
                REQUIRED_AXIS_RUNTIME_DISPATCH_PROFILE_FIELDS,
                f"{axis}.runtime_dispatch_profile",
            )
        if "missing_evidence" in report:
            _require_list(errors, report["missing_evidence"], f"{axis}.missing_evidence")

    profile = payload.get("axis_dispatch_profile", {})
    if not isinstance(profile, dict):
        errors.append("axis_dispatch_profile must be an object")
    else:
        _add_missing_fields(
            errors,
            profile,
            REQUIRED_AXIS_DISPATCH_PROFILE_FIELDS,
            "axis_dispatch_profile",
        )
        dispatch_model = profile.get("dispatch_model")
        if dispatch_model == "sibling_axis_carriers":
            errors.append("dispatch_model uses legacy sibling_axis_carriers")
        if dispatch_model not in VALID_DISPATCH_MODELS:
            errors.append(f"invalid dispatch_model {dispatch_model!r}")
        delegation_attempted = profile.get("delegation_attempted_by_axis", {})
        if _require_object(
            errors,
            delegation_attempted,
            "axis_dispatch_profile.delegation_attempted_by_axis",
        ):
            missing_delegation_axes = sorted(
                CANONICAL_AXIS_IDS - set(delegation_attempted)
            )
            if missing_delegation_axes:
                errors.append(
                    "axis_dispatch_profile.delegation_attempted_by_axis: "
                    f"missing axes {missing_delegation_axes}"
                )
            for axis, attempted in delegation_attempted.items():
                if attempted not in {True, False}:
                    errors.append(
                        "axis_dispatch_profile.delegation_attempted_by_axis."
                        f"{axis}: must be a boolean"
                    )
        per_axis_profile = profile.get("per_axis_runtime_dispatch_profile", {})
        if _require_object(
            errors,
            per_axis_profile,
            "axis_dispatch_profile.per_axis_runtime_dispatch_profile",
        ):
            missing_profile_axes = sorted(CANONICAL_AXIS_IDS - set(per_axis_profile))
            if missing_profile_axes:
                errors.append(
                    "axis_dispatch_profile.per_axis_runtime_dispatch_profile: "
                    f"missing axes {missing_profile_axes}"
                )
            for axis in sorted(CANONICAL_AXIS_IDS):
                runtime_profile = per_axis_profile.get(axis)
                if _require_object(
                    errors,
                    runtime_profile,
                    "axis_dispatch_profile.per_axis_runtime_dispatch_profile."
                    f"{axis}",
                ):
                    _add_missing_fields(
                        errors,
                        runtime_profile,
                        REQUIRED_AXIS_RUNTIME_DISPATCH_PROFILE_FIELDS,
                        "axis_dispatch_profile.per_axis_runtime_dispatch_profile."
                        f"{axis}",
                    )

    axis_report_status = payload.get("axis_report_status")
    _validate_status(
        errors,
        axis_report_status,
        VALID_AXIS_REPORT_STATUSES,
        "axis_report_status",
    )
    status_by_axis = payload.get("axis_report_status_by_axis")
    if _require_object(errors, status_by_axis, "axis_report_status_by_axis"):
        missing_status_axes = sorted(CANONICAL_AXIS_IDS - set(status_by_axis))
        if missing_status_axes:
            errors.append(
                f"axis_report_status_by_axis: missing axes {missing_status_axes}"
            )
        for axis, status in status_by_axis.items():
            _validate_status(
                errors,
                status,
                VALID_AXIS_REPORT_STATUS_BY_AXIS,
                f"axis_report_status_by_axis.{axis}",
            )

    manual_exception = payload.get("manual_exception", {})
    if isinstance(manual_exception, dict) and manual_exception.get("present") is True:
        missing_preservation = [
            field
            for field in sorted(MANUAL_EXCEPTION_PRESERVATION_FIELDS)
            if field not in payload and field not in manual_exception
        ]
        if missing_preservation:
            errors.append(
                f"manual exception missing preservation fields {missing_preservation}"
            )
        preserved = payload.get(
            "anti_cheat_findings_preserved",
            manual_exception.get("anti_cheat_findings_preserved"),
        )
        if preserved is not True:
            errors.append("manual exception must preserve anti-cheat findings")
        historical_gap_preserved = payload.get(
            "historical_gap_preserved",
            manual_exception.get("historical_gap_preserved"),
        )
        if historical_gap_preserved is not True:
            errors.append("manual exception must preserve historical_gap fields")

    return errors


def validate_closeout_evidence_bundle(payload: dict) -> list[str]:
    errors: list[str] = []
    bundle = payload.get("closeout_evidence_bundle")
    if not _require_object(errors, bundle, "closeout_evidence_bundle"):
        return errors

    _add_missing_fields(
        errors,
        bundle,
        CLOSEOUT_EVIDENCE_BUNDLE_TOP_LEVEL_FIELDS,
        "closeout_evidence_bundle",
    )
    if bundle.get("schema_version") != "worktrack-closeout-evidence-bundle/v1":
        errors.append("closeout_evidence_bundle.schema_version: invalid value")

    branch_policy = bundle.get("branch_policy")
    if _require_object(errors, branch_policy, "closeout_evidence_bundle.branch_policy"):
        _add_missing_fields(
            errors,
            branch_policy,
            BRANCH_POLICY_FIELDS,
            "closeout_evidence_bundle.branch_policy",
        )

    section_specs = {
        "self_review_record": (
            SELF_REVIEW_RECORD_FIELDS,
            VALID_OPTIONAL_EVIDENCE_STATES,
        ),
        "single_acceptance_verdict": (
            SINGLE_ACCEPTANCE_VERDICT_FIELDS,
            VALID_OPTIONAL_EVIDENCE_STATES,
        ),
        "worktrack_gate_evidence": (
            WORKTRACK_GATE_EVIDENCE_FIELDS,
            VALID_WORKTRACK_GATE_EVIDENCE_STATES,
        ),
        "closeout_gate_evidence": (
            CLOSEOUT_GATE_EVIDENCE_FIELDS,
            VALID_OPTIONAL_EVIDENCE_STATES,
        ),
        "repo_refresh_checkpoint": (
            REPO_REFRESH_CHECKPOINT_FIELDS,
            VALID_OPTIONAL_EVIDENCE_STATES,
        ),
        "bundle_completeness": (
            BUNDLE_COMPLETENESS_FIELDS,
            VALID_BUNDLE_COMPLETENESS_STATUSES,
        ),
    }
    for section, (required_fields, allowed_states) in section_specs.items():
        value = bundle.get(section)
        section_path = f"closeout_evidence_bundle.{section}"
        if _require_object(errors, value, section_path):
            _add_missing_fields(errors, value, required_fields, section_path)
            if "status" in value:
                _validate_status(
                    errors,
                    value.get("status"),
                    allowed_states,
                    section_path,
                )

    completeness = bundle.get("bundle_completeness", {})
    if isinstance(completeness, dict):
        for field in (
            "missing_required_fields",
            "historical_gap_fields",
            "contaminated_fields",
            "residual_risks",
        ):
            if field in completeness:
                _require_list(
                    errors,
                    completeness[field],
                    f"closeout_evidence_bundle.bundle_completeness.{field}",
                )

    _validate_dispatch_provenance(errors, bundle.get("dispatch_provenance"))
    _validate_composite_lane_links(errors, bundle.get("composite_lane_records"))
    return errors


def _validate_dispatch_provenance(errors: list[str], value: object) -> None:
    path = "closeout_evidence_bundle.dispatch_provenance"
    if not _require_object(errors, value, path):
        return
    _add_missing_fields(errors, value, DISPATCH_PROVENANCE_FIELDS, path)
    _validate_status(
        errors,
        value.get("status"),
        VALID_DISPATCH_PROVENANCE_STATES,
        path,
    )
    for field in (
        "subagent_dispatch_record_refs",
        "missing_dispatch_record_refs",
        "reviewer_carrier_refs",
    ):
        if field in value:
            _require_list(errors, value[field], f"{path}.{field}")

    raw_status = value.get("dispatch_result_status")
    resolved_status = value.get("resolved_runtime_dispatch_status")
    _validate_status(
        errors,
        raw_status,
        VALID_DISPATCH_RESULT_STATUSES,
        f"{path}.dispatch_result_status",
    )
    _validate_status(
        errors,
        resolved_status,
        VALID_RESOLVED_RUNTIME_DISPATCH_STATUSES,
        f"{path}.resolved_runtime_dispatch_status",
    )
    _validate_status(
        errors,
        value.get("independence_summary"),
        VALID_INDEPENDENCE_SUMMARIES,
        f"{path}.independence_summary",
    )

    if raw_status != "N/A" and value.get("status") in {"captured", "linked"}:
        if resolved_status != raw_status:
            errors.append(
                f"{path}: resolved_runtime_dispatch_status must preserve "
                "dispatch_result_status"
            )
    if raw_status == "N/A" and resolved_status not in {
        "incomplete",
        "missing",
        "historical_gap",
        "contaminated",
    }:
        errors.append(f"{path}: N/A raw status requires visible non-pass resolution")
    if raw_status == "delegated" and not value.get("subagent_dispatch_record_refs"):
        errors.append(f"{path}: delegated dispatch requires subagent refs")
    if value.get("status") in {"captured", "linked"}:
        if value.get("runtime_dispatch_record_ref") in {None, "N/A"}:
            errors.append(f"{path}: captured/linked dispatch requires runtime ref")


def _validate_composite_lane_links(errors: list[str], value: object) -> None:
    path = "closeout_evidence_bundle.composite_lane_records"
    if not _require_object(errors, value, path):
        return
    missing_lanes = sorted(set(COMPOSITE_LANE_KEYS) - set(value))
    if missing_lanes:
        errors.append(f"{path}: missing lanes {missing_lanes}")
    for lane_key, lane_id in COMPOSITE_LANE_KEYS.items():
        lane = value.get(lane_key)
        lane_path = f"{path}.{lane_key}"
        if not _require_object(errors, lane, lane_path):
            continue
        _add_missing_fields(errors, lane, COMPOSITE_LANE_LINK_FIELDS, lane_path)
        _validate_status(errors, lane.get("status"), VISIBLE_EVIDENCE_STATES, lane_path)
        if lane.get("lane_id") != lane_id:
            errors.append(f"{lane_path}: lane_id must be {lane_id!r}")
        if "missing_required_fields" in lane:
            _require_list(
                errors,
                lane["missing_required_fields"],
                f"{lane_path}.missing_required_fields",
            )
        if lane.get("status") == "incomplete" and not lane.get(
            "missing_required_fields"
        ):
            errors.append(f"{lane_path}: incomplete lane must list missing fields")
        if lane.get("status") == "contaminated" and lane.get(
            "contaminated_reason"
        ) in {None, "N/A"}:
            errors.append(f"{lane_path}: contaminated lane requires reason")
        if lane.get("status") == "not_applicable" and lane.get(
            "not_applicable_reason"
        ) in {None, "N/A"}:
            errors.append(f"{lane_path}: not_applicable lane requires reason")


def make_axis_runtime_dispatch_profile() -> dict:
    return {
        "backend_runtime": "codex-cli",
        "model_family": "gpt",
        "subagent_dispatch_shell": "available",
        "runtime_supports_subagent": "yes",
        "subagent_permission_state": "allowed",
        "permission_allows_delegation": "yes",
        "dispatch_package_safety": "safe",
        "delegation_attempted": "yes",
        "attempted_carrier": "SubAgent",
        "carrier_decision": "delegated_subagent",
        "fallback_reason": "N/A",
    }


def make_axis_report_bundle() -> dict:
    reports = {}
    for axis in sorted(CANONICAL_AXIS_IDS):
        reports[axis] = {
            "axis": axis,
            "verdict": "pass",
            "severity": "low",
            "checklist_results": [],
            "carrier": "subagent",
            "isolation_guarantee": True,
            "carrier_isolation_broken": False,
            "report_ref": f".servo/milestone/MS-xxx.md#{axis}",
            "observed_git_hash": "abc1234",
            "target_type": "program_code",
            "axis_applicability_state": "applicable",
            "axis_applicability_reason": "program_code target",
            "expected_method": "standard axis method",
            "runtime_dispatch_profile": make_axis_runtime_dispatch_profile(),
            "missing_evidence": [],
        }
    return {
        "axis_reports": reports,
        "axis_report_status": "complete",
        "axis_report_status_by_axis": {
            axis: "present" for axis in sorted(CANONICAL_AXIS_IDS)
        },
        "axis_dispatch_profile": {
            "dispatch_owner": "top_level_harness",
            "dispatch_model": "sibling_delegated",
            "required_axes": sorted(CANONICAL_AXIS_IDS),
            "completed_axes": sorted(CANONICAL_AXIS_IDS),
            "missing_axes": [],
            "delegation_attempted_by_axis": {
                axis: True for axis in sorted(CANONICAL_AXIS_IDS)
            },
            "same_carrier_cross_axis": False,
            "carrier_isolation_broken_any": False,
            "dispatch_gap_reason": "N/A",
            "per_axis_runtime_dispatch_profile": {
                axis: make_axis_runtime_dispatch_profile()
                for axis in sorted(CANONICAL_AXIS_IDS)
            },
            "nested_axis_dispatch_attempted": False,
        },
        "manual_exception": {"present": False},
        "accepted_gate_verdict_preserved_as": "N/A",
        "anti_cheat_findings_preserved": "N/A",
        "manual_exception_followup_ref": "N/A",
    }


def make_composite_lane_link(lane_key: str, status: str = "linked") -> dict:
    reason = f"{lane_key} documented exception"
    return {
        "status": status,
        "record_ref": f".servo/milestone/MS-xxx.md#{lane_key}",
        "lane_id": COMPOSITE_LANE_KEYS[lane_key],
        "validation_ref": f".servo/milestone/MS-xxx.md#{lane_key}-validation",
        "producer_ref": f".servo/worktrack/WT-xxx.md#{lane_key}-producer",
        "missing_required_fields": ["record_ref"] if status == "incomplete" else [],
        "contaminated_reason": reason if status == "contaminated" else "N/A",
        "not_applicable_reason": reason if status == "not_applicable" else "N/A",
    }


def make_closeout_evidence_bundle(
    dispatch_status: str = "delegated",
    resolved_dispatch_status: str | None = None,
    dispatch_provenance_status: str = "linked",
    lane_statuses: dict[str, str] | None = None,
) -> dict:
    if resolved_dispatch_status is None:
        resolved_dispatch_status = dispatch_status
    lane_statuses = lane_statuses or {}
    subagent_refs = (
        [".servo/worktrack/WT-xxx.md#subagent-dispatch-WT-xxx-implement"]
        if dispatch_status == "delegated"
        else []
    )
    runtime_ref = (
        ".servo/worktrack/WT-xxx.md#runtime-dispatch-WT-xxx"
        if dispatch_provenance_status in {"captured", "linked"}
        else "N/A"
    )
    return {
        "closeout_evidence_bundle": {
            "schema_version": "worktrack-closeout-evidence-bundle/v1",
            "worktrack_id": "WT-xxx",
            "milestone_id": "MS-xxx",
            "node_type": "test",
            "branch_policy": {
                "baseline_branch": "develop-servo",
                "branch_source_ref": "abc1234",
                "worktrack_branch": "wt/WT-xxx",
                "integration_target_ref": "ms/MS-xxx",
                "closeout_target_ref": "ms/MS-xxx",
                "checkpoint_base_ref": "abc1234",
                "final_baseline_branch": "develop-servo",
            },
            "self_review_record": {
                "status": "linked",
                "record_ref": ".servo/worktrack/WT-xxx.md#self-review",
                "verdict": "pass",
            },
            "single_acceptance_verdict": {
                "status": "linked",
                "verdict_ref": ".servo/worktrack/WT-xxx.md#single-acceptance",
                "verdict": "accepted",
                "critical_failure": False,
            },
            "worktrack_gate_evidence": {
                "status": "linked",
                "evidence_ref": ".servo/worktrack/WT-xxx.md#gate-evidence",
                "gate_verdict": "pass",
                "implementation_gate": "pass",
                "validation_gate": "pass",
                "policy_gate": "pass",
            },
            "closeout_gate_evidence": {
                "status": "linked",
                "evidence_ref": ".servo/worktrack/WT-xxx.md#closeout-gate",
                "verdict": "pass",
            },
            "dispatch_provenance": {
                "status": dispatch_provenance_status,
                "runtime_dispatch_record_ref": runtime_ref,
                "subagent_dispatch_record_refs": subagent_refs,
                "missing_dispatch_record_refs": [],
                "dispatch_result_status": dispatch_status,
                "resolved_runtime_dispatch_status": resolved_dispatch_status,
                "implementer_carrier": "SubAgent",
                "reviewer_carrier_refs": [
                    ".servo/worktrack/WT-xxx.md#reviewer-carrier"
                ],
                "gate_judge_carrier_ref": ".servo/worktrack/WT-xxx.md#gate-judge",
                "independence_summary": "independent",
            },
            "composite_lane_records": {
                lane_key: make_composite_lane_link(
                    lane_key, lane_statuses.get(lane_key, "linked")
                )
                for lane_key in COMPOSITE_LANE_KEYS
            },
            "repo_refresh_checkpoint": {
                "status": "linked",
                "checkpoint_ref": ".servo/repo/refresh.md#WT-xxx",
                "latest_observed_checkpoint": "abc1234",
            },
            "bundle_completeness": {
                "status": "complete",
                "missing_required_fields": [],
                "historical_gap_fields": [],
                "contaminated_fields": [],
                "residual_risks": [],
            },
        }
    }


def test_closeout_evidence_bundle_schema_complete_bundle():
    payload = make_closeout_evidence_bundle()
    errors = validate_closeout_evidence_bundle(payload)
    assert not errors, f"expected valid closeout bundle, got {errors}"
    print("  PASS: closeout_evidence_bundle_complete_bundle")


def test_closeout_evidence_bundle_rejects_missing_core_section():
    payload = make_closeout_evidence_bundle()
    del payload["closeout_evidence_bundle"]["dispatch_provenance"]
    errors = validate_closeout_evidence_bundle(payload)
    assert any("missing fields ['dispatch_provenance']" in e for e in errors), errors
    print("  PASS: closeout_evidence_bundle_missing_core_section")


def test_closeout_evidence_bundle_rejects_missing_nested_field():
    payload = make_closeout_evidence_bundle()
    del payload["closeout_evidence_bundle"]["branch_policy"]["checkpoint_base_ref"]
    errors = validate_closeout_evidence_bundle(payload)
    assert any("checkpoint_base_ref" in e for e in errors), errors
    print("  PASS: closeout_evidence_bundle_missing_nested_field")


def test_dispatch_provenance_requires_linked_runtime_fields():
    payload = make_closeout_evidence_bundle()
    provenance = payload["closeout_evidence_bundle"]["dispatch_provenance"]
    del provenance["runtime_dispatch_record_ref"]
    del provenance["resolved_runtime_dispatch_status"]
    errors = validate_closeout_evidence_bundle(payload)
    assert any("runtime_dispatch_record_ref" in e for e in errors), errors
    assert any("resolved_runtime_dispatch_status" in e for e in errors), errors
    print("  PASS: dispatch_provenance_requires_linked_runtime_fields")


def test_dispatch_provenance_preserves_distinct_runtime_statuses():
    distinct_statuses = [
        "delegated",
        "current_carrier_fallback",
        "permission_blocked",
        "runtime_gap",
        "dispatch_package_unsafe",
        "blocked",
        "historical_gap",
    ]
    for status in distinct_statuses:
        payload = make_closeout_evidence_bundle(status)
        errors = validate_closeout_evidence_bundle(payload)
        assert not errors, f"{status}: expected valid dispatch status, got {errors}"

    payload = make_closeout_evidence_bundle(
        "runtime_gap",
        resolved_dispatch_status="missing",
    )
    errors = validate_closeout_evidence_bundle(payload)
    assert any("must preserve dispatch_result_status" in e for e in errors), errors
    print("  PASS: dispatch_provenance_preserves_distinct_runtime_statuses")


def test_composite_lane_records_require_all_six_link_entries():
    payload = make_closeout_evidence_bundle()
    lanes = payload["closeout_evidence_bundle"]["composite_lane_records"]
    del lanes["professional_review"]
    del lanes["code_review"]["producer_ref"]
    errors = validate_closeout_evidence_bundle(payload)
    assert any("missing lanes ['professional_review']" in e for e in errors), errors
    assert any("producer_ref" in e for e in errors), errors
    print("  PASS: composite_lane_records_require_all_six_link_entries")


def test_closeout_schema_preserves_visible_non_pass_states():
    lane_statuses = {
        "code_review": "incomplete",
        "feature_completeness": "missing",
        "related_influence": "historical_gap",
        "intent_completeness": "contaminated",
        "operator_simulation": "not_applicable",
        "professional_review": "linked",
    }
    payload = make_closeout_evidence_bundle(
        "N/A",
        resolved_dispatch_status="contaminated",
        dispatch_provenance_status="contaminated",
        lane_statuses=lane_statuses,
    )
    bundle = payload["closeout_evidence_bundle"]
    bundle["bundle_completeness"]["status"] = "contaminated"
    bundle["bundle_completeness"]["contaminated_fields"] = [
        "dispatch_provenance"
    ]
    errors = validate_closeout_evidence_bundle(payload)
    assert not errors, f"expected visible non-pass states to validate, got {errors}"

    bundle["composite_lane_records"]["feature_completeness"]["status"] = "pass"
    errors = validate_closeout_evidence_bundle(payload)
    assert any("invalid status 'pass'" in e for e in errors), errors
    print("  PASS: closeout_schema_preserves_visible_non_pass_states")


def test_axis_report_schema_complete_bundle():
    payload = make_axis_report_bundle()
    errors = validate_axis_report_bundle(payload)
    assert not errors, f"expected valid bundle, got {errors}"
    print("  PASS: axis_report_schema_complete_bundle")


def test_axis_report_schema_rejects_missing_axis():
    payload = make_axis_report_bundle()
    del payload["axis_reports"]["anticheat"]
    errors = validate_axis_report_bundle(payload)
    assert any("missing canonical axis reports" in e for e in errors), errors
    print("  PASS: axis_report_schema_missing_axis")


def test_axis_report_schema_rejects_legacy_aliases():
    payload = make_axis_report_bundle()
    legacy = payload["axis_reports"].pop("blackbox")
    legacy["axis"] = "black_box"
    legacy["axis_verdict"] = legacy.pop("verdict")
    payload["axis_reports"]["black_box"] = legacy
    payload["axis_dispatch_profile"]["dispatch_model"] = "sibling_axis_carriers"
    errors = validate_axis_report_bundle(payload)
    assert any("legacy axis ids present" in e for e in errors), errors
    assert any("legacy axis value" in e for e in errors), errors
    assert any("axis_verdict" in e for e in errors), errors
    assert any("legacy sibling_axis_carriers" in e for e in errors), errors
    print("  PASS: axis_report_schema_legacy_aliases")


def test_axis_report_schema_requires_runtime_dispatch_profile():
    payload = make_axis_report_bundle()
    del payload["axis_reports"]["blackbox"]["runtime_dispatch_profile"]
    del payload["axis_dispatch_profile"]["per_axis_runtime_dispatch_profile"]
    errors = validate_axis_report_bundle(payload)
    assert any("runtime_dispatch_profile" in e for e in errors), errors
    assert any("per_axis_runtime_dispatch_profile" in e for e in errors), errors
    print("  PASS: axis_report_schema_runtime_dispatch_profile")


def test_axis_report_schema_requires_substituted_axis_fields():
    payload = make_axis_report_bundle()
    report = payload["axis_reports"]["blackbox"]
    report["target_type"] = "non_program_artifact"
    report["axis_applicability_state"] = "substituted"
    errors = validate_axis_report_bundle(payload)
    assert any("substituted axis missing fields" in e for e in errors), errors

    report["substitute_method"] = "artifact_acceptance_review"
    report["substitution_evidence_ref"] = (
        "docs/harness/artifact/control/milestone-gate-aggregation.md#target_type_rules"
    )
    report["substitute_verdict"] = "pass"
    report["evidence_covers_completion_signal"] = True
    errors = validate_axis_report_bundle(payload)
    assert not errors, f"expected valid substituted axis report, got {errors}"
    print("  PASS: axis_report_schema_substituted_axis_fields")


def test_axis_report_schema_requires_dispatch_profile_axis_maps():
    payload = make_axis_report_bundle()
    dispatch_profile = payload["axis_dispatch_profile"]
    del dispatch_profile["delegation_attempted_by_axis"]["anticheat"]
    dispatch_profile["delegation_attempted_by_axis"]["blackbox"] = "yes"
    dispatch_profile["per_axis_runtime_dispatch_profile"]["blackbox"] = {}
    del dispatch_profile["per_axis_runtime_dispatch_profile"]["whitebox"][
        "carrier_decision"
    ]
    errors = validate_axis_report_bundle(payload)
    assert any("delegation_attempted_by_axis" in e for e in errors), errors
    assert any("delegation_attempted_by_axis.blackbox" in e for e in errors), errors
    assert any(
        "per_axis_runtime_dispatch_profile.blackbox" in e
        and "backend_runtime" in e
        for e in errors
    ), errors
    assert any(
        "per_axis_runtime_dispatch_profile.whitebox" in e
        and "carrier_decision" in e
        for e in errors
    ), errors
    print("  PASS: axis_report_schema_dispatch_profile_axis_maps")


def test_axis_report_schema_requires_status_and_report_fields():
    payload = make_axis_report_bundle()
    del payload["axis_report_status_by_axis"]["composite"]
    del payload["axis_reports"]["whitebox"]["missing_evidence"]
    del payload["axis_reports"]["whitebox"]["expected_method"]
    errors = validate_axis_report_bundle(payload)
    assert any("axis_report_status_by_axis: missing axes" in e for e in errors), errors
    assert any("missing_evidence" in e for e in errors), errors
    assert any("expected_method" in e for e in errors), errors
    print("  PASS: axis_report_schema_status_and_report_fields")


def test_axis_report_schema_requires_manual_exception_preservation():
    payload = make_axis_report_bundle()
    payload["manual_exception"] = {
        "present": True,
        "exception_type": "programmer_acceptance_override",
        "reason": "manual acceptance after blocked gate",
    }
    for field in MANUAL_EXCEPTION_PRESERVATION_FIELDS:
        payload.pop(field, None)
    errors = validate_axis_report_bundle(payload)
    assert any("missing preservation fields" in e for e in errors), errors
    assert any("must preserve anti-cheat findings" in e for e in errors), errors

    payload["accepted_gate_verdict_preserved_as"] = "blocked"
    payload["anti_cheat_findings_preserved"] = True
    payload["historical_gap_preserved"] = True
    payload["manual_exception_followup_ref"] = "WT-followup"
    errors = validate_axis_report_bundle(payload)
    assert not errors, f"expected valid manual exception preservation, got {errors}"
    print("  PASS: axis_report_schema_manual_exception_preservation")


def _extract_anticheat_severity_config(text: str) -> str:
    match = re.search(
        r"```yaml\nanticheat_severity_config:\n(?P<body>.*?)\n```",
        text,
        re.S,
    )
    assert match, "missing anticheat_severity_config yaml block"
    return "anticheat_severity_config:\n" + match.group("body")


def _extract_check_config(config: str, check_id: str) -> str:
    match = re.search(
        rf"    {check_id}:\n(?P<body>.*?)(?=\n    A[1-7]:|\n```|\Z)",
        config,
        re.S,
    )
    assert match, f"missing severity config for {check_id}"
    return match.group("body")


def test_anticheat_severity_config_contract_terms():
    skill_text = read_skill("milestone-anticheat-check")
    config = _extract_anticheat_severity_config(skill_text)

    for check_id, expected_severity in ANTICHEAT_SEVERITY_DEFAULTS.items():
        check_config = _extract_check_config(config, check_id)
        for field in ANTICHEAT_SEVERITY_REQUIRED_FIELDS:
            assert field in check_config, f"{check_id}: missing {field}"
        assert f"default_severity: {expected_severity}" in check_config, (
            f"{check_id}: default severity weakened or changed"
        )
        assert "hard_fail_veto" in check_config, f"{check_id}: missing hard_fail veto"
        assert "blocked_veto" in check_config, f"{check_id}: missing blocked veto"
        if expected_severity == "high":
            assert "high_severity_weight_modifier" in check_config, (
                f"{check_id}: missing high severity weight modifier"
            )

    assert "veto_power: true" in config
    assert "target_wt_weight: 0" in config
    assert "severity_source" in skill_text
    assert "trigger_type" in skill_text
    assert "explicit_override" in skill_text

    aggregation_text = read_repo_file(
        "docs/harness/artifact/control/milestone-gate-aggregation.md"
    )
    for token in (
        "anticheat_severity_config",
        "required_check_ids: [A1, A2, A3, A4, A5, A6, A7]",
        "default_severity",
        "soft_fail_triggers",
        "hard_fail_triggers",
        "blocking_triggers",
        "weight_modifier.enabled=true; target_wt_weight=0",
    ):
        assert token in aggregation_text, f"aggregation contract missing {token}"
    print("  PASS: anticheat_severity_config_contract_terms")


def test_historical_gap_preservation_contract_terms():
    paths = [
        "product/harness/skills/milestone-anticheat-check/SKILL.md",
        "docs/harness/artifact/control/milestone-gate-aggregation.md",
        "docs/harness/artifact/worktrack/closeout-evidence-bundle.md",
    ]
    for path in paths:
        text = read_repo_file(path)
        lower_text = text.lower().replace("`", "")
        for term in ANTICHEAT_HISTORICAL_GAP_REQUIRED_TERMS:
            assert term.lower() in lower_text, (
                f"{path}: missing historical_gap term {term!r}"
            )
        assert "synthetic pass evidence" in lower_text, (
            f"{path}: missing synthetic pass preservation guard"
        )
    print("  PASS: historical_gap_preservation_contract_terms")


def test_docs_milestone_example_preserves_anticheat_defaults():
    text = read_repo_file("docs/harness/artifact/control/milestone-gate-aggregation.md")
    match = re.search(
        r"## 十、示例：Docs Milestone 的 aggregation_rules(?P<section>.*?)(?=\n## 十一、)",
        text,
        re.S,
    )
    assert match, "missing docs milestone aggregation example"
    section = match.group("section")
    guard_patterns = (
        re.compile(r"bounded manual exception", re.I),
        re.compile(r"manual[- ]exception", re.I),
        re.compile(r"bounded[- ]override", re.I),
        re.compile(r"不得删除、降级或覆盖"),
    )

    risky_patterns = [
        re.compile(r"anticheat:\s*\{\s*veto_power:\s*false\s*\}"),
        re.compile(r"weight_modifier\.enabled:\s*false"),
        re.compile(r"weight_modifier:\n(?:[^\n]*\n){0,6}?\s+enabled:\s*false"),
    ]
    for pattern in risky_patterns:
        for finding in pattern.finditer(text):
            window = text[max(0, finding.start() - 500) : finding.end() + 500]
            assert any(guard.search(window) for guard in guard_patterns), (
                "aggregation doc contains anti-cheat default override "
                f"{finding.group(0)!r} without an explicit manual exception or "
                "bounded override guard"
            )

    assert "anticheat: { veto_power: true }" in section
    assert "enabled: true" in section
    print("  PASS: docs_milestone_example_preserves_anticheat_defaults")


def test_contract_docs_use_canonical_axis_schema():
    anticheat_alias = re.compile(r"(?<![A-Za-z0-9_])anti_cheat(?!_findings_preserved)")
    for path in CONTRACT_SCHEMA_FILES:
        text = read_repo_file(path)
        for token in FORBIDDEN_SCHEMA_TOKENS:
            assert token not in text, f"{path}: forbidden legacy token {token}"
        for pattern in FORBIDDEN_SCHEMA_PATTERNS:
            assert not pattern.search(text), f"{path}: forbidden legacy axis_verdict field"
        assert not anticheat_alias.search(text), f"{path}: forbidden anti_cheat axis alias"

    gate_text = read_repo_file("product/harness/skills/milestone-gate/SKILL.md")
    assert "axis_applicability_state" in gate_text
    for token in (
        "expected_method",
        "runtime_dispatch_profile",
        "missing_evidence",
    ):
        assert token in gate_text, f"product skill missing axis report field {token}"
    assert "axis_applicability: applicable" not in gate_text
    assert "anti_cheat_findings_preserved" in gate_text

    aggregation_text = read_repo_file(
        "docs/harness/artifact/control/milestone-gate-aggregation.md"
    )
    assert "axis_report_status_by_axis" in aggregation_text
    assert "dispatch_model: sibling_delegated" in aggregation_text
    print("  PASS: contract_docs_canonical_axis_schema")


def test_aggregator_all_pass():
    """All WTs pass, no issues → pass."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "feature"},
        {"worktrack_id": "WT-2", "node_type": "docs"},
    ]
    verdicts = {"WT-1": "pass", "WT-2": "pass"}
    axis = {
        "blackbox": "pass",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    assert weighted[0]["final_weight"] == 4 and weighted[1]["final_weight"] == 2, (
        f"weights: {weighted}"
    )

    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not findings, f"unexpected contradictions: {findings}"

    deg, reason = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted
    )
    assert deg, f"expected degenerate AND, got {deg}: {reason}"

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "pass", f"expected pass, got {verdict}"
    print("  PASS: all_pass")


def test_aggregator_contradiction():
    """Critical WT pass + critical WT hard_fail → contradiction blocked."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "feature"},
        {"worktrack_id": "WT-2", "node_type": "release"},
    ]
    verdicts = {"WT-1": "pass", "WT-2": "hard_fail"}
    axis = {
        "blackbox": "pass",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert contradiction_blocked, "contradiction should be detected"
    assert len(findings) == 1
    assert findings[0]["wt_a_id"] == "WT-1" and findings[0]["wt_b_id"] == "WT-2"

    deg, _ = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted
    )
    assert not deg, "degenerate should NOT trigger with contradiction"

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "blocked", f"expected blocked, got {verdict}"
    print("  PASS: contradiction_blocked")


def test_aggregator_veto():
    """Blackbox axis hard_fail → blocked regardless of WT verdicts."""
    wts = [{"worktrack_id": "WT-1", "node_type": "feature"}]
    verdicts = {"WT-1": "pass"}
    axis = {
        "blackbox": "hard_fail",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    deg, _ = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted
    )

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "blocked", f"expected blocked (veto), got {verdict}"
    print("  PASS: veto_power")


def test_aggregator_critical_hard_fail():
    """Critical (weight=5) WT hard_fail → hard_fail, no contradiction (only 1 WT)."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "critical"},
        {"worktrack_id": "WT-2", "node_type": "docs"},
    ]
    verdicts = {"WT-1": "hard_fail", "WT-2": "pass"}
    axis = {
        "blackbox": "pass",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked, "no contradiction (different weights)"

    deg, _ = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted
    )
    assert not deg, "degenerate should NOT trigger (critical fail)"

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "hard_fail", f"expected hard_fail, got {verdict}"
    print("  PASS: critical_hard_fail")


def test_aggregator_weight_modifier():
    """Anticheat high severity → target WT weight=0, doesn't affect verdict."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "feature"},
        {"worktrack_id": "WT-2", "node_type": "docs"},
    ]
    verdicts = {"WT-1": "hard_fail", "WT-2": "pass"}
    axis = {
        "blackbox": "pass",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    # Simulate weight modifier: anticheat high → WT-1 weight = 0
    for w in weighted:
        if w["worktrack_id"] == "WT-1":
            w["final_weight"] = 0  # weight modifier applied

    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked, "WT-1 weight=0, below contradiction threshold"

    deg, _ = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, True, weighted
    )
    assert not deg, "degenerate should NOT trigger (weight modifier applied)"

    # WT-1 weight=0 means no WT with weight>=3 fails → pass
    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "pass", f"expected pass (cheating WT zeroed), got {verdict}"
    print("  PASS: weight_modifier")


def test_aggregator_degenerate_and():
    """Clean inputs with all conditions met → degenerate AND."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "feature"},
        {"worktrack_id": "WT-2", "node_type": "config"},
    ]
    verdicts = {"WT-1": "pass", "WT-2": "pass"}
    axis = {
        "blackbox": "pass",
        "whitebox": "pass",
        "anticheat": "pass",
        "composite": "pass",
    }

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked

    deg, reason = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted
    )
    assert deg, f"expected degenerate AND: {reason}"
    assert "all critical WTs pass" in reason

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "pass", f"expected pass (degenerate), got {verdict}"
    print("  PASS: degenerate_and")


def test_aggregator_override():
    """weight override replaces default weight."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "docs"},
    ]
    overrides = [{"worktrack_id": "WT-1", "weight": 4, "reason": "critical docs"}]
    weighted = simulate_weight_calc(wts, overrides)
    assert weighted[0]["final_weight"] == 4, (
        f"expected 4, got {weighted[0]['final_weight']}"
    )
    assert weighted[0]["overridden"] is True
    assert weighted[0]["override_reason"] == "critical docs"
    print("  PASS: weight_override")


# ---------- 3. Axis skill structure validation ----------

AXIS_SKILLS = [
    "milestone-blackbox-check",
    "milestone-whitebox-check",
    "milestone-anticheat-check",
    "milestone-composite-check",
]


def test_axis_skills_exist():
    for name in AXIS_SKILLS:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.exists(), f"missing: {path}"
    print("  PASS: axis_skills_exist")


def test_axis_skills_have_isolation_guarantee():
    for name in AXIS_SKILLS:
        text = read_skill(name)
        assert "isolation_guarantee" in text, f"{name}: missing isolation_guarantee"
        assert "carrier_isolation_broken" in text, (
            f"{name}: missing carrier_isolation_broken"
        )
        assert "SubAgent" in text, f"{name}: missing SubAgent reference"
    print("  PASS: axis_isolation")


def test_axis_skills_have_permission_boundary():
    for name in AXIS_SKILLS:
        text = read_skill(name)
        assert "只读" in text or "read-only" in text.lower() or "权限边界" in text, (
            f"{name}: missing permission boundary"
        )
    print("  PASS: axis_permission_boundary")


# ---------- 4. Routing validation ----------


def test_gate_skill_exists():
    path = SKILLS_DIR / "milestone-gate" / "SKILL.md"
    assert path.exists(), f"missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert "Layer 1" in text and "Layer 2" in text, (
        "gate skill missing two-layer description"
    )
    print("  PASS: gate_skill_exists")


def test_sensor_references_gate():
    text = read_skill("milestone-status-skill")
    assert "milestone-gate" in text, "sensor skill does not reference gate skill"
    assert "不直接运行 Milestone Gate" in text or "调用" in text, (
        "sensor skill should delegate Gate"
    )
    print("  PASS: sensor_references_gate")


def test_harness_has_conditional_binding():
    text = read_skill("harness-skill")
    assert "milestone-gate" in text, "harness-skill missing gate skill reference"
    assert "worktrack_list_finished" in text, (
        "harness-skill missing conditional trigger"
    )
    print("  PASS: harness_conditional_binding")


# ---------- main ----------


def main() -> int:
    print("\n--- Aggregator logic tests ---")
    for test in [
        test_aggregator_all_pass,
        test_aggregator_contradiction,
        test_aggregator_veto,
        test_aggregator_critical_hard_fail,
        test_aggregator_weight_modifier,
        test_aggregator_degenerate_and,
        test_aggregator_override,
    ]:
        try:
            test()
        except AssertionError as e:
            fail(f"{test.__name__}: {e}")

    print("\n--- Axis report schema tests ---")
    for test in [
        test_closeout_evidence_bundle_schema_complete_bundle,
        test_closeout_evidence_bundle_rejects_missing_core_section,
        test_closeout_evidence_bundle_rejects_missing_nested_field,
        test_dispatch_provenance_requires_linked_runtime_fields,
        test_dispatch_provenance_preserves_distinct_runtime_statuses,
        test_composite_lane_records_require_all_six_link_entries,
        test_closeout_schema_preserves_visible_non_pass_states,
        test_axis_report_schema_complete_bundle,
        test_axis_report_schema_rejects_missing_axis,
        test_axis_report_schema_rejects_legacy_aliases,
        test_axis_report_schema_requires_runtime_dispatch_profile,
        test_axis_report_schema_requires_substituted_axis_fields,
        test_axis_report_schema_requires_dispatch_profile_axis_maps,
        test_axis_report_schema_requires_status_and_report_fields,
        test_axis_report_schema_requires_manual_exception_preservation,
        test_anticheat_severity_config_contract_terms,
        test_historical_gap_preservation_contract_terms,
        test_docs_milestone_example_preserves_anticheat_defaults,
        test_contract_docs_use_canonical_axis_schema,
    ]:
        try:
            test()
        except AssertionError as e:
            fail(f"{test.__name__}: {e}")

    print("\n--- Axis skill structure tests ---")
    for test in [
        test_axis_skills_exist,
        test_axis_skills_have_isolation_guarantee,
        test_axis_skills_have_permission_boundary,
    ]:
        try:
            test()
        except AssertionError as e:
            fail(f"{test.__name__}: {e}")

    print("\n--- Routing validation tests ---")
    for test in [
        test_gate_skill_exists,
        test_sensor_references_gate,
        test_harness_has_conditional_binding,
    ]:
        try:
            test()
        except AssertionError as e:
            fail(f"{test.__name__}: {e}")

    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  FAIL: {f}")
        return 1
    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
