from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "product/harness/skills/harness-skill/scripts"


def run_script(script_name: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        ["python3", str(SCRIPT_DIR / script_name), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def init_repo(tmp_path: Path) -> str:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()


def write_control_state(path: Path, checkpoint: str | None = None) -> None:
    checkpoint_line = (
        f"- latest_observed_checkpoint: {checkpoint}\n" if checkpoint is not None else ""
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            ---
            updated: "2026-06-26T00:00:00Z"
            ---
            # Control State Repo

            ## Baseline Traceability
            {checkpoint_line}- verified_at_history:
              - 2026-06-26T00:00:00Z
            """
        ),
        encoding="utf-8",
    )


def test_git_hash_check_defaults_to_control_state_repo_not_root_control(tmp_path: Path) -> None:
    head = init_repo(tmp_path)
    write_control_state(tmp_path / ".servo/control-state-repo.md", checkpoint=head)
    (tmp_path / ".servo/control-state.md").write_text(
        "# root control fields only\n", encoding="utf-8"
    )

    result = run_script("git_hash_check.py", [], tmp_path)
    payload = parse_stdout_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "unchanged"
    assert payload["latest_observed_checkpoint"] == head
    assert payload["repo_baseline_unchanged"] is True


def test_git_hash_check_preserves_explicit_legacy_control_state_path(tmp_path: Path) -> None:
    head = init_repo(tmp_path)
    write_control_state(tmp_path / ".servo/control-state.md", checkpoint=head)

    result = run_script(
        "git_hash_check.py", ["--control-state", ".servo/control-state.md"], tmp_path
    )
    payload = parse_stdout_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "unchanged"
    assert payload["latest_observed_checkpoint"] == head


def test_checkpoint_writeback_defaults_to_control_state_repo(tmp_path: Path) -> None:
    head = init_repo(tmp_path)
    write_control_state(tmp_path / ".servo/control-state-repo.md")
    (tmp_path / ".servo/control-state.md").write_text(
        "# root control fields only\n", encoding="utf-8"
    )

    result = run_script("checkpoint_writeback.py", ["--checkpoint-type", "observed"], tmp_path)
    payload = parse_stdout_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["written"] is True
    assert payload["hash"] == head
    repo_state = (tmp_path / ".servo/control-state-repo.md").read_text(encoding="utf-8")
    root_state = (tmp_path / ".servo/control-state.md").read_text(encoding="utf-8")
    assert f"- latest_observed_checkpoint: {head}" in repo_state
    assert "latest_observed_checkpoint" not in root_state


def test_complex_gate_missing_source_blocks_unless_explicit_not_applicable(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-intake.md"

    blocked = run_script(
        "complex_project_entry_gate_check.py",
        ["--gate-source", str(missing_path)],
        tmp_path,
    )
    blocked_payload = parse_stdout_json(blocked)
    assert blocked.returncode == 1
    assert blocked_payload["blocked"] is True
    assert "unresolved gate blocking default" in blocked_payload["reason"]

    explicit = run_script(
        "complex_project_entry_gate_check.py",
        [
            "--gate-source",
            str(missing_path),
            "--not-applicable-reason",
            "low_risk_single_file_doc_update",
        ],
        tmp_path,
    )
    explicit_payload = parse_stdout_json(explicit)
    assert explicit.returncode == 0, explicit.stderr
    assert explicit_payload["ready"] is True
    assert explicit_payload["not_applicable"] is True
    assert explicit_payload["not_applicable_reason"] == "low_risk_single_file_doc_update"


def test_complex_gate_missing_section_blocks_and_clear_gate_passes(tmp_path: Path) -> None:
    no_gate = tmp_path / "no-gate.md"
    no_gate.write_text("# Intake\n\nNo gate section.\n", encoding="utf-8")

    blocked = run_script(
        "complex_project_entry_gate_check.py",
        ["--gate-source", str(no_gate)],
        tmp_path,
    )
    blocked_payload = parse_stdout_json(blocked)
    assert blocked.returncode == 1
    assert blocked_payload["blocked"] is True
    assert "unresolved gate blocking default" in blocked_payload["reason"]

    clear_gate = tmp_path / "clear-gate.md"
    clear_gate.write_text(
        textwrap.dedent(
            """\
            ## Complex Project Entry Gate

            ```yaml
            complex_project_entry_gate:
              entry_verdict: clear
              recommendation_status: not_needed
              reinforcement_milestone_recommendation:
                needed: false
              blocks_implementation_until_resolved: false
              milestone_blocking_decision: []
            ```
            """
        ),
        encoding="utf-8",
    )
    passed = run_script(
        "complex_project_entry_gate_check.py",
        ["--gate-source", str(clear_gate)],
        tmp_path,
    )
    passed_payload = parse_stdout_json(passed)
    assert passed.returncode == 0, passed.stderr
    assert passed_payload["ready"] is True
    assert passed_payload["blocked"] is False


def test_autonomy_policy_stop_condition_and_missing_evidence_hard_block(tmp_path: Path) -> None:
    control_state = tmp_path / ".servo/control-state.md"
    control_state.parent.mkdir(parents=True)
    control_state.write_text("# root control fields only\n", encoding="utf-8")

    result = run_script(
        "autonomy_policy_check.py",
        [
            "--operation",
            "dispatch",
            "--skill",
            "generic-worker-skill",
            "--control-state",
            str(control_state),
        ],
        tmp_path,
    )
    payload = parse_stdout_json(result)

    assert result.returncode == 1
    assert payload["blocked"] is True
    assert payload["stop_condition_hit"]
    assert payload["evidence_required_complete"] is False


def test_dispatch_mode_recommend_uses_delegated_vocabulary(tmp_path: Path) -> None:
    result = run_script(
        "dispatch_mode_recommend.py",
        [
            "--task-coupling",
            "low",
            "--state-sharing",
            "low",
            "--parallel-value",
            "high",
            "--risk-profile",
            "low",
            "--context-budget-fit",
            "yes",
            "--runtime-supports-subagent",
            "yes",
            "--permission-allows-delegation",
            "yes",
            "--dispatch-package-safe",
            "yes",
        ],
        tmp_path,
    )
    payload = parse_stdout_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["recommended_mode"] == "delegated"
