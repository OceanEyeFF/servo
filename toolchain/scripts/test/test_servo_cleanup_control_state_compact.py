from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "milestone-cleanup-skill"
    / "scripts"
    / "control_state_compact.py"
)
SERVO_TEMPLATE_CONTROL_STATE = REPO_ROOT / "product" / ".servo_template" / "control-state.md"
SET_GOAL_CONTROL_STATE_ASSET = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "harness-set-goal-skill"
    / "assets"
    / "control-state.md"
)


def load_helper_module():
    spec = importlib.util.spec_from_file_location("control_state_compact", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def sample_split_primary_control_state() -> str:
    return (
        "---\n"
        "artifact_type: \"control-state\"\n"
        "control_state_version: split\n"
        "---\n"
        "# Harness Control State\n\n"
        "## Handback Guard\n\n"
        "- handoff_state: worktrack-active-WT-example\n\n"
        "## Approval Boundary\n\n"
        "- needs_programmer_approval: no\n"
        "- approval_scope: current worktrack only\n"
        "- approval_persistence: one-shot\n\n"
        "## Branch Environment Guard\n\n"
        "- baseline_branch: develop-servo\n"
        "- active_milestone_branch: ms/MS-example\n"
        "- current_branch_context: worktrack\n"
        "- expected_branch_context: worktrack\n"
        "- branch_context_guard_status: active\n"
        "- worktrack_branch: wt/WT-example\n\n"
        "## User-Defined Servo Controls\n\n"
        "- latest_observed_checkpoint: abc123\n"
        "- observed_git_hash: abc123\n"
        "- active_worktrack: WT-example\n\n"
        "## Continuation Authority\n\n"
        "- post_contract_autonomy: false\n\n"
        "## Review Gate\n\n"
        "- milestone_review_gate_ready: true\n"
        "- milestone_review_gate_checkpoint: abc123\n\n"
        "## Autonomy Ledger\n\n"
        "- autonomy_budget_remaining: 1\n\n"
        "## Current Control Level\n\n"
        "- repo_scope: active\n"
        "- worktrack_scope: active\n"
        "- current_function: WorktrackDispatch\n\n"
        "## Active Worktrack\n\n"
        "- active_worktrack: WT-example\n"
        "- latest_closed_worktrack: WT-previous\n\n"
        "## Milestone Pipeline\n\n"
        "- active_milestone: MS-example\n"
        "- milestone_status: active\n\n"
        "## Route Decision\n\n"
        "- recommended_next_route: WorktrackScope.Dispatch\n"
    )


def sample_split_repo_control_state() -> str:
    return (
        "---\n"
        "artifact_type: \"control-state-repo\"\n"
        "---\n"
        "# Harness Control State — Repo Level\n\n"
        "## Repo Control Level\n\n"
        "- repo_scope: active\n"
        "- repo_next_action: N/A\n\n"
        "## Active Worktrack Registry\n\n"
        "- closed_worktrack_commits: []\n\n"
        "## Milestone Pipeline — Active Milestone\n\n"
        "- active_milestone: MS-example\n"
        "- milestone_status: active\n"
        "- active_milestone_branch: ms/MS-example\n"
        "- active_milestone_branch_head: abc123\n"
        "- milestone_pipeline_summary: planned=1 / active=1 / completed=0 / superseded=0\n"
        "- active_milestone_progress: 0/1\n"
        "- active_milestone_progress_breakdown: 0 closed / 1 active / 0 planned\n"
        "- active_worktrack: WT-example\n"
        "- active_worktrack_branch: wt/WT-example\n\n"
        "## Baseline Traceability\n\n"
        "- latest_observed_checkpoint: abc123\n"
        "- last_doc_catch_up_checkpoint: def456\n"
    )


def sample_split_wt_control_state() -> str:
    return (
        "---\n"
        "artifact_type: \"control-state-wt\"\n"
        "---\n"
        "# Harness Control State — Worktrack Level\n\n"
        "## Worktrack Current\n\n"
        "- worktrack_scope: active\n"
        "- worktrack_next_action: dispatch\n"
        "- current_worktrack: WT-example\n"
        "- last_closed_worktrack: WT-previous\n"
        "- worktrack_branch: wt/WT-example\n\n"
        "## Current Next Action\n\n"
        "- repo_next_action: N/A\n"
        "- worktrack_next_action: dispatch\n"
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


def test_control_state_templates_include_compaction_required_fields() -> None:
    helper = load_helper_module()

    for template_path in (SERVO_TEMPLATE_CONTROL_STATE, SET_GOAL_CONTROL_STATE_ASSET):
        text = template_path.read_text(encoding="utf-8")
        validation = helper.validate_control_state(text)
        assert validation.missing_sections == [], template_path
        assert validation.missing_fields == [], template_path
        assert validation.missing_groups == [], template_path


def test_split_runtime_profiles_include_compaction_required_fields() -> None:
    helper = load_helper_module()

    samples = {
        ".servo/control-state.md": sample_split_primary_control_state(),
        ".servo/control-state-repo.md": sample_split_repo_control_state(),
        ".servo/control-state-wt.md": sample_split_wt_control_state(),
    }
    for relative_path, text in samples.items():
        validation = helper.validate_control_state(text, Path(relative_path))
        assert validation.missing_sections == [], relative_path
        assert validation.missing_fields == [], relative_path
        assert validation.missing_groups == [], relative_path


def test_split_runtime_cli_dry_run_accepts_all_control_state_artifacts(tmp_path: Path) -> None:
    samples = {
        ".servo/control-state.md": (
            sample_split_primary_control_state(),
            "split-primary-control-state",
        ),
        ".servo/control-state-repo.md": (
            sample_split_repo_control_state(),
            "split-repo-control-state",
        ),
        ".servo/control-state-wt.md": (
            sample_split_wt_control_state(),
            "split-worktrack-control-state",
        ),
    }

    for relative_path, (text, expected_profile) in samples.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

        result = run_helper(
            "--control-state",
            str(target),
            "--dry-run",
            "--json",
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stdout
        payload = json.loads(result.stdout)
        assert payload["post_verify_verdict"] == "pass"
        assert payload["preserved_fields"]["validation_profile"] == expected_profile
        assert target.read_text(encoding="utf-8") == text


def test_servo_template_does_not_reference_installer_backup_artifacts() -> None:
    text = SERVO_TEMPLATE_CONTROL_STATE.read_text(encoding="utf-8")
    manifest_text = (REPO_ROOT / "product" / ".servo_template" / "MANIFEST.md").read_text(
        encoding="utf-8"
    )

    disallowed_terms = (
        ".servo/backup",
        ".servo/backups",
        "installer-generated backup/update artifacts",
    )
    for term in disallowed_terms:
        assert term not in text

    assert "backup/update artifacts and runtime history rows intentionally not templated" in manifest_text
