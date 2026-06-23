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


# ---------- 1. Aggregator logic tests ----------

def simulate_weight_calc(
    worktracks: list[dict],
    overrides: list[dict] | None = None,
) -> list[dict]:
    """Simulate Step 1: weight_rules."""
    default_weights = {
        "critical": 5, "feature": 4, "release": 4,
        "config": 3, "test": 3, "docs": 2, "demo": 1,
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
        results.append({
            "worktrack_id": wt["worktrack_id"],
            "node_type": node,
            "base_weight": base,
            "final_weight": final,
            "overridden": overridden,
            "override_reason": reason,
        })
    return results


def detect_contradictions(
    weighted: list[dict],
    verdicts: dict[str, str],
    threshold: int = 3,
) -> tuple[list[dict], bool]:
    """Simulate Step 2: contradiction_rules."""
    findings = []
    blocked = False
    mismatch_pairs = {("pass", "hard_fail"), ("pass", "blocked"),
                      ("hard_fail", "pass"), ("blocked", "pass")}

    for i, a in enumerate(weighted):
        for b in weighted[i + 1:]:
            if a["final_weight"] >= threshold and b["final_weight"] >= threshold:
                va = verdicts[a["worktrack_id"]]
                vb = verdicts[b["worktrack_id"]]
                if (va, vb) in mismatch_pairs:
                    findings.append({
                        "wt_a_id": a["worktrack_id"], "verdict_a": va,
                        "wt_b_id": b["worktrack_id"], "verdict_b": vb,
                        "severity": "high",
                        "recommended_resolution": "new_verification_worktrack",
                    })
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
    lanes_consistent = len(set(axis_verdicts.values())) == 1 and "pass" in axis_verdicts.values()

    if (not contradiction_blocked and not anticheat_high and lanes_consistent
            and not overrides_applied and all_critical_pass):
        return True, "Degenerate AND: no contradiction, no anti-cheat high, all lanes consistent, all critical WTs pass"
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
        w for w in weighted
        if w["final_weight"] >= 4 and verdicts.get(w["worktrack_id"]) == "hard_fail"
    ]
    heavy_fails = [
        w for w in weighted
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


def test_aggregator_all_pass():
    """All WTs pass, no issues → pass."""
    wts = [
        {"worktrack_id": "WT-1", "node_type": "feature"},
        {"worktrack_id": "WT-2", "node_type": "docs"},
    ]
    verdicts = {"WT-1": "pass", "WT-2": "pass"}
    axis = {"blackbox": "pass", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    assert weighted[0]["final_weight"] == 4 and weighted[1]["final_weight"] == 2, \
        f"weights: {weighted}"

    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not findings, f"unexpected contradictions: {findings}"

    deg, reason = check_degenerate_conditions(
        contradiction_blocked, False, axis, verdicts, False, weighted)
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
    axis = {"blackbox": "pass", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert contradiction_blocked, "contradiction should be detected"
    assert len(findings) == 1
    assert findings[0]["wt_a_id"] == "WT-1" and findings[0]["wt_b_id"] == "WT-2"

    deg, _ = check_degenerate_conditions(contradiction_blocked, False, axis, verdicts, False, weighted)
    assert not deg, "degenerate should NOT trigger with contradiction"

    verdict = compute_verdict(weighted, verdicts, axis, contradiction_blocked, deg)
    assert verdict == "blocked", f"expected blocked, got {verdict}"
    print("  PASS: contradiction_blocked")


def test_aggregator_veto():
    """Blackbox axis hard_fail → blocked regardless of WT verdicts."""
    wts = [{"worktrack_id": "WT-1", "node_type": "feature"}]
    verdicts = {"WT-1": "pass"}
    axis = {"blackbox": "hard_fail", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    deg, _ = check_degenerate_conditions(contradiction_blocked, False, axis, verdicts, False, weighted)

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
    axis = {"blackbox": "pass", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked, "no contradiction (different weights)"

    deg, _ = check_degenerate_conditions(contradiction_blocked, False, axis, verdicts, False, weighted)
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
    axis = {"blackbox": "pass", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    # Simulate weight modifier: anticheat high → WT-1 weight = 0
    for w in weighted:
        if w["worktrack_id"] == "WT-1":
            w["final_weight"] = 0  # weight modifier applied

    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked, "WT-1 weight=0, below contradiction threshold"

    deg, _ = check_degenerate_conditions(contradiction_blocked, False, axis, verdicts, True, weighted)
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
    axis = {"blackbox": "pass", "whitebox": "pass", "anticheat": "pass", "composite": "pass"}

    weighted = simulate_weight_calc(wts)
    findings, contradiction_blocked = detect_contradictions(weighted, verdicts)
    assert not contradiction_blocked

    deg, reason = check_degenerate_conditions(contradiction_blocked, False, axis, verdicts, False, weighted)
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
    assert weighted[0]["final_weight"] == 4, f"expected 4, got {weighted[0]['final_weight']}"
    assert weighted[0]["overridden"] is True
    assert weighted[0]["override_reason"] == "critical docs"
    print("  PASS: weight_override")


# ---------- 2. Axis skill structure validation ----------

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
        assert "carrier_isolation_broken" in text, f"{name}: missing carrier_isolation_broken"
        assert "SubAgent" in text, f"{name}: missing SubAgent reference"
    print("  PASS: axis_isolation")


def test_axis_skills_have_permission_boundary():
    for name in AXIS_SKILLS:
        text = read_skill(name)
        assert "只读" in text or "read-only" in text.lower() or "权限边界" in text, \
            f"{name}: missing permission boundary"
    print("  PASS: axis_permission_boundary")


# ---------- 3. Routing validation ----------

def test_gate_skill_exists():
    path = SKILLS_DIR / "milestone-gate" / "SKILL.md"
    assert path.exists(), f"missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert "Layer 1" in text and "Layer 2" in text, "gate skill missing two-layer description"
    print("  PASS: gate_skill_exists")


def test_sensor_references_gate():
    text = read_skill("milestone-status-skill")
    assert "milestone-gate" in text, "sensor skill does not reference gate skill"
    assert "不直接运行 Milestone Gate" in text or "调用" in text, \
        "sensor skill should delegate Gate"
    print("  PASS: sensor_references_gate")


def test_harness_has_conditional_binding():
    text = read_skill("harness-skill")
    assert "milestone-gate" in text, "harness-skill missing gate skill reference"
    assert "worktrack_list_finished" in text, "harness-skill missing conditional trigger"
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
