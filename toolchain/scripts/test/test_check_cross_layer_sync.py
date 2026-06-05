from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_cross_layer_sync import (
    check_charter_registry_consistency,
    check_contract_template_alignment,
    check_control_state_template_alignment,
)


def write_doc(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_charter_registry_uses_tracked_source_without_runtime_aw(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/skills/set-harness-goal-skill/assets/goal-charter.md",
        "\n".join(
            [
                "### Node Type Registry",
                "",
                "| type | merge_required |",
                "|------|----------------|",
                "| `bugfix` | yes |",
            ]
        )
        + "\n",
    )
    write_doc(
        tmp_path / "docs/harness/artifact/control/node-type-registry.md",
        "### bugfix\n",
    )

    result = check_charter_registry_consistency(tmp_path)

    assert result["status"] == "pass"
    assert any("runtime charter instance absent" in item for item in result["infos"])


def test_charter_registry_does_not_promote_runtime_aw_truth(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "product/harness/skills/set-harness-goal-skill/assets/goal-charter.md",
        "\n".join(
            [
                "### Node Type Registry",
                "",
                "| type | merge_required |",
                "|------|----------------|",
                "| `bugfix` | yes |",
            ]
        )
        + "\n",
    )
    write_doc(
        tmp_path / "docs/harness/artifact/control/node-type-registry.md",
        "### bugfix\n",
    )
    write_doc(
        tmp_path / ".servo/goal-charter.md",
        "\n".join(
            [
                "### Node Type Registry",
                "",
                "| type | merge_required |",
                "|------|----------------|",
                "| `runtime-only` | yes |",
            ]
        )
        + "\n",
    )

    result = check_charter_registry_consistency(tmp_path)

    assert result["status"] == "pass"
    assert any("runtime charter instance present" in item for item in result["infos"])


def test_contract_template_alignment_pass(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/worktrack/contract.md",
        "\n".join([
            "## Node Type",
            "",
            "- type:",
            "- source_from_goal_charter:",
            "- baseline_form:",
            "- merge_required:",
            "- gate_criteria:",
            "- if_interrupted_strategy:",
            "",
            "## Execution Policy",
            "",
            "- runtime_dispatch_mode:",
            "- dispatch_mode_source:",
            "- allowed_values:",
            "- fallback_reason_required:",
            "",
        ]) + "\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "\n".join([
            "## Node Type",
            "",
            "- type: feature",
            "- source_from_goal_charter: yes",
            "- baseline_form: commit-on-feature-branch",
            "- merge_required: true",
            "- gate_criteria: standard",
            "- if_interrupted_strategy: stop",
            "",
            "## Execution Policy",
            "",
            "- runtime_dispatch_mode: auto",
            "- dispatch_mode_source: contract",
            "- allowed_values: [auto, delegated]",
            "- fallback_reason_required: true",
            "",
        ]) + "\n",
    )

    result = check_contract_template_alignment(tmp_path)

    assert result["status"] == "pass"


def test_contract_template_alignment_missing_file(tmp_path: Path) -> None:
    result = check_contract_template_alignment(tmp_path)
    assert result["status"] == "fail"
    assert any("missing" in e for e in result["errors"])


def test_control_state_template_alignment_pass(tmp_path: Path) -> None:
    write_doc(
        tmp_path / "docs/harness/artifact/control/control-state.md",
        "\n".join([
            "## Handback Guard",
            "",
            "- handoff_state:",
            "- last_stop_reason:",
            "- last_handback_signature:",
            "- handback_reaffirmed_rounds:",
            "- stable_handback_threshold:",
            "- handback_lock_active:",
            "- last_unlock_signal:",
            "- autonomy_budget_remaining:",
            "- autonomous_worktracks_opened:",
            "- continuous_progression_permission:",
            "- per_milestone_automatic_worktrack_budget:",
            "- default_servo_work_branch:",
            "- protected_branch_policy:",
            "- branch_mutation_policy:",
            "- auto_maintained_runtime_facts_not_asked:",
            "",
        ]) + "\n",
    )
    write_doc(
        tmp_path / "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
        "\n".join([
            "## Handback Guard",
            "",
            "- handoff_state: repo-ready",
            "- last_stop_reason: review completed",
            "- last_handback_signature: abc123",
            "- handback_reaffirmed_rounds: 2",
            "- stable_handback_threshold: 3",
            "- handback_lock_active: false",
            "- last_unlock_signal: programmer directive",
            "- autonomy_budget_remaining: 27",
            "- autonomous_worktracks_opened: 5",
            "- continuous_progression_permission: pending_programmer_confirmation",
            "- per_milestone_automatic_worktrack_budget: pending_programmer_confirmation",
            "- default_servo_work_branch: pending_programmer_confirmation",
            "- protected_branch_policy: pending_programmer_confirmation",
            "- branch_mutation_policy: pending_programmer_confirmation",
            "- auto_maintained_runtime_facts_not_asked:",
            "",
        ]) + "\n",
    )

    result = check_control_state_template_alignment(tmp_path)

    assert result["status"] == "pass"


def test_control_state_template_alignment_missing_file(tmp_path: Path) -> None:
    result = check_control_state_template_alignment(tmp_path)
    assert result["status"] == "fail"
    assert any("missing" in e for e in result["errors"])
