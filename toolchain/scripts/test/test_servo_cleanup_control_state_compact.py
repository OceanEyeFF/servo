from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "servo-cleanup-skill"
    / "scripts"
    / "control_state_compact.py"
)


def sample_control_state(*, include_active_milestone: bool = True) -> str:
    active_milestone = "- active_milestone: MS-20260622-001\n" if include_active_milestone else ""
    return (
        "# Harness Control State\n\n"
        "## Metadata\n\n"
        "- updated: 2026-06-22T20:37:35+08:00\n"
        "handback_history_ref:\n\n"
        "## Current Control Level\n\n"
        "- repo_scope: initialized\n"
        "- worktrack_scope: closed\n"
        "- current_function: RepoScope.Observe\n\n"
        "## Active Worktrack\n\n"
        "- active_worktrack: N/A\n"
        "- active_worktrack_branch: N/A\n"
        "- active_worktrack_node_type: N/A\n"
        "- latest_closed_worktrack_commit: wt/current@2222222\n"
        "- latest_closed_worktrack_commit: wt/old@1111111\n\n"
        "## Milestone Pipeline\n\n"
        f"{active_milestone}"
        "- milestone_status: active\n"
        "- active_milestone_branch: ms/MS-20260622-001-servo-runtime-footprint-cleanup\n"
        "- active_milestone_review_gate_status: effective_pass\n"
        "- active_milestone_branch_head: 2222222\n\n"
        "## Baseline Branch\n\n"
        "- baseline_branch: develop\n"
        "- current_checkout: ms/MS-20260622-001-servo-runtime-footprint-cleanup@2222222\n\n"
        "## Current Next Action\n\n"
        "- recommended_next_route: RepoScope.Decide\n"
        "- recommended_next_scope: RepoScope\n\n"
        "## Handback Guard\n\n"
        "- last_stop_reason: latest stop\n"
        "- last_stop_reason: old stop\n"
        "- handoff_state: repo-scope-ready\n\n"
        "## Baseline Traceability\n\n"
        "- latest_observed_checkpoint: 2222222\n"
        "- checkpoint_ref: ms/MS-20260622-001-servo-runtime-footprint-cleanup@2222222\n"
        "- verified_at: 2026-06-22T20:37:35+08:00\n"
        "- verified_at: 2026-06-21T20:37:35+08:00\n\n"
        "## Autonomy Ledger\n\n"
        "- post_contract_autonomy: delegated-minimal\n"
        "- autonomy_budget_remaining: 1\n"
        "- needs_programmer_approval: no for current dry-run\n"
    )


def run_helper(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_dry_run_reports_compaction_without_writing(tmp_path: Path) -> None:
    control_state = tmp_path / ".servo" / "control-state.md"
    control_state.parent.mkdir()
    original = sample_control_state()
    control_state.write_text(original, encoding="utf-8")

    result = run_helper(
        "--control-state",
        str(control_state),
        "--dry-run",
        "--json",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["would_change"] is True
    assert payload["changed"] is False
    assert payload["post_verify_verdict"] == "pass"
    assert ".servo/history/control-state/" in payload["history_artifact_ref"]
    assert control_state.read_text(encoding="utf-8") == original
    assert not (tmp_path / ".servo" / "history").exists()


def test_apply_generates_history_and_updates_handback_ref(tmp_path: Path) -> None:
    control_state = tmp_path / ".servo" / "control-state.md"
    control_state.parent.mkdir()
    control_state.write_text(sample_control_state(), encoding="utf-8")

    result = run_helper(
        "--control-state",
        str(control_state),
        "--apply",
        "--json",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "apply"
    assert payload["would_change"] is True
    assert payload["changed"] is True
    assert payload["post_verify_verdict"] == "pass"
    assert payload["history_artifact_ref"].startswith(".servo/history/control-state/")

    history_path = tmp_path / payload["history_artifact_ref"]
    assert history_path.is_file()
    history_text = history_path.read_text(encoding="utf-8")
    assert "wt/old@1111111" in history_text
    assert "2026-06-21T20:37:35+08:00" in history_text

    compacted = control_state.read_text(encoding="utf-8")
    assert f"handback_history_ref: {payload['history_artifact_ref']}" in compacted
    assert "wt/current@2222222" in compacted
    assert "wt/old@1111111" not in compacted
    assert "2026-06-22T20:37:35+08:00" in compacted
    assert "2026-06-21T20:37:35+08:00" not in compacted


def test_missing_required_field_blocks_without_writing(tmp_path: Path) -> None:
    control_state = tmp_path / ".servo" / "control-state.md"
    control_state.parent.mkdir()
    original = sample_control_state(include_active_milestone=False)
    control_state.write_text(original, encoding="utf-8")

    result = run_helper(
        "--control-state",
        str(control_state),
        "--apply",
        "--json",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["post_verify_verdict"] == "blocked"
    assert "active_milestone" in payload["preserved_fields"]["missing_fields"]
    assert control_state.read_text(encoding="utf-8") == original
    assert not (tmp_path / ".servo" / "history").exists()


def test_backup_history_dir_is_rejected(tmp_path: Path) -> None:
    control_state = tmp_path / ".servo" / "control-state.md"
    control_state.parent.mkdir()
    original = sample_control_state()
    control_state.write_text(original, encoding="utf-8")

    result = run_helper(
        "--control-state",
        str(control_state),
        "--history-dir",
        str(tmp_path / ".servo" / "backups" / "control-state"),
        "--apply",
        "--json",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["post_verify_verdict"] == "blocked"
    assert "backup paths" in payload["errors"][0]
    assert control_state.read_text(encoding="utf-8") == original
