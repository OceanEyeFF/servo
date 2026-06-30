from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "milestone-cleanup-skill"
    / "scripts"
    / "runtime_maintenance_sweep.py"
)
LEGACY_HELPER = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "worktrack-cleanup-skill"
    / "scripts"
    / "runtime_maintenance_sweep.py"
)
PAYLOADS = (
    REPO_ROOT / "product" / "harness" / "adapters" / "agents" / "skills" / "milestone-cleanup-skill" / "payload.json",
    REPO_ROOT / "product" / "harness" / "adapters" / "claude" / "skills" / "milestone-cleanup-skill" / "payload.json",
)


def write_doc(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_servo_fixture(root: Path) -> Path:
    servo = root / ".servo"
    write_doc(servo / "control-state.md", "- active_milestone: MS-001\n")
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "- worktrack_id: WT-001\n"
        "  - milestone_id: MS-001\n"
        "  - status: done\n"
        "  - evidence_ref: .servo/worktrack/gate-evidence.md\n",
    )
    write_doc(servo / "milestone" / "MS-001.md", "- milestone_id: MS-001\n")
    write_doc(servo / "worktrack" / "gate-evidence.md", "# Rolling Evidence\n")
    return servo


def test_cleanup_skill_runtime_sweep_helper_is_report_first(tmp_path: Path) -> None:
    servo = build_servo_fixture(tmp_path)

    result = subprocess.run(
        [sys.executable, str(HELPER), "--servo-root", str(servo), "--json"],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["cleanup_executed"] is False
    assert payload["finding_count"] >= 1
    assert "rolling_evidence_reuse" in payload["counts_by_type"]


def test_legacy_cleanup_runtime_sweep_stays_in_sync_with_canonical() -> None:
    assert LEGACY_HELPER.read_text(encoding="utf-8") == HELPER.read_text(encoding="utf-8")


def test_cleanup_skill_runtime_sweep_reports_milestone_backlog_history_gaps(
    tmp_path: Path,
) -> None:
    servo = tmp_path / ".servo"
    write_doc(
        servo / "control-state.md",
        "# Harness Control State\n\n"
        "## Milestone Pipeline\n"
        "- active_milestone: MS-20260630-003\n"
        "- milestone_status: active\n",
    )
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "- worktrack_id: WT-001\n"
        "  - milestone_id: MS-20260630-001\n"
        "  - status: done\n"
        "  - evidence_ref: .servo/worktrack/gate-evidence.md\n",
    )
    write_doc(
        servo / "repo" / "milestone-backlog.md",
        "- milestone_id: MS-20260630-001\n"
        "  - status: completed\n"
        "  - worktrack_list:\n"
        "    - WT-001 (completed)\n"
        "\n"
        "- milestone_id: MS-20260630-002\n"
        "  - status: completed\n"
        "  - worktrack_list:\n"
        "    - WT-002 (completed)\n"
        "\n"
        "- milestone_id: MS-20260630-003\n"
        "  - status: planned\n"
        "  - worktrack_list:\n"
        "    - WT-003 (planned)\n",
    )
    write_doc(
        servo / "repo" / "milestone-history.md",
        "- milestone_id: MS-20260630-001\n"
        "  - status: completed\n"
        "  - worktrack_list:\n"
        "    - WT-001 (completed)\n"
        "\n"
        "- milestone_id: MS-20260630-004\n"
        "  - status: active\n"
        "  - worktrack_list:\n"
        "    - WT-004 (active)\n",
    )
    write_doc(
        servo / "milestone" / "MS-20260630-005.md",
        "# Completed Milestone\n\n"
        "## milestone_id\n"
        "milestone_id: \"MS-20260630-005\"\n\n"
        "## status\n"
        "status: \"completed\"\n",
    )
    write_doc(servo / "worktrack" / "gate-evidence.md", "# Rolling Evidence\n")

    result = subprocess.run(
        [sys.executable, str(HELPER), "--servo-root", str(servo), "--json"],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    counts = payload["counts_by_type"]
    assert counts["milestone_live_history_status"] == 2
    assert counts["milestone_live_history_overlap"] == 1
    assert counts["milestone_missing_history_record"] == 2
    assert counts["milestone_history_live_status"] == 1
    assert counts["milestone_active_pointer_non_active"] == 1


def test_cleanup_skill_runtime_sweep_accepts_normalized_multi_cycle_state(
    tmp_path: Path,
) -> None:
    servo = tmp_path / ".servo"
    write_doc(
        servo / "control-state.md",
        "# Harness Control State\n\n"
        "## Milestone Pipeline\n"
        "- active_milestone: MS-20260630-004\n"
        "- milestone_status: active\n",
    )
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "- worktrack_id: WT-closed-001\n"
        "  - milestone_id: MS-20260630-001\n"
        "  - status: completed\n"
        "  - evidence_ref: .servo/milestone/MS-20260630-001-closeout-records.md\n"
        "  - closeout_record_ref: .servo/milestone/MS-20260630-001-closeout-records.md#WT-closed-001\n"
        "  - closeout_bundle_status: complete\n"
        "\n"
        "- worktrack_id: WT-active-004\n"
        "  - milestone_id: MS-20260630-004\n"
        "  - status: active\n"
        "  - evidence_ref: .servo/worktrack/gate-evidence.md\n",
    )
    write_doc(
        servo / "repo" / "milestone-backlog.md",
        "- milestone_id: MS-20260630-003\n"
        "  - status: planned\n"
        "  - worktrack_list:\n"
        "    - WT-planned-003 (planned)\n"
        "\n"
        "- milestone_id: MS-20260630-004\n"
        "  - status: active\n"
        "  - worktrack_list:\n"
        "    - WT-active-004 (active)\n"
        "\n"
        "- milestone_id: MS-20260630-005\n"
        "  - status: planned\n"
        "  - worktrack_list:\n"
        "    - WT-planned-005 (planned)\n",
    )
    write_doc(
        servo / "repo" / "milestone-history.md",
        "- milestone_id: MS-20260630-001\n"
        "  - status: completed\n"
        "  - worktrack_list:\n"
        "    - WT-closed-001 (completed)\n"
        "\n"
        "- milestone_id: MS-20260630-002\n"
        "  - status: completed\n"
        "  - worktrack_list:\n"
        "    - WT-closed-002 (completed)\n",
    )
    write_doc(servo / "milestone" / "MS-20260630-001.md", "status: completed\n")
    write_doc(servo / "milestone" / "MS-20260630-002.md", "status: completed\n")
    write_doc(servo / "milestone" / "MS-20260630-004.md", "status: active\n")
    write_doc(
        servo / "milestone" / "MS-20260630-001-closeout-records.md",
        "# Closeout Records\n\n"
        "closeout_record_ref: .servo/milestone/MS-20260630-001-closeout-records.md#WT-closed-001\n",
    )
    write_doc(
        servo / "milestone" / "MS-20260630-002-gate-verdict.md",
        "# Sidecar\n\nstatus: active\n",
    )
    write_doc(servo / "worktrack" / "gate-evidence.md", "# Rolling Evidence\n")

    result = subprocess.run(
        [sys.executable, str(HELPER), "--servo-root", str(servo), "--json"],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    counts = payload["counts_by_type"]
    regression_types = {
        "milestone_live_history_status",
        "milestone_live_history_overlap",
        "milestone_missing_history_record",
        "milestone_history_live_status",
        "milestone_history_unfinished_worktrack_marker",
        "milestone_active_pointer_stale",
        "milestone_active_pointer_non_active",
        "milestone_invalid_status",
    }
    assert regression_types.isdisjoint(counts)
    assert payload["milestone_entry_count"] == 5


def test_cleanup_skill_runtime_sweep_reports_live_worktrack_and_snapshot_drift(
    tmp_path: Path,
) -> None:
    servo = tmp_path / ".servo"
    write_doc(
        servo / "control-state.md",
        "# Harness Control State\n\n"
        "## Active Worktrack\n"
        "- active_worktrack: N/A\n\n"
        "## User-Defined Servo Controls\n"
        "- latest_observed_checkpoint: 1111111\n"
        "- observed_git_hash: 1111111\n"
        "- repo_refresh_checkpoint: 1111111\n",
    )
    write_doc(
        servo / "control-state-repo.md",
        "# Harness Control State - Repo Level\n\n"
        "## Milestone Pipeline - Active Milestone\n"
        "- active_worktrack: N/A\n"
        "- active_milestone_branch_head: 1111111\n\n"
        "## Baseline Traceability\n"
        "- latest_observed_checkpoint: 1111111\n",
    )
    write_doc(
        servo / "control-state-wt.md",
        "# Harness Control State - Worktrack Level\n\n"
        "## Worktrack Current\n"
        "- current_worktrack: WT-stale-active\n"
        "- worktrack_next_action: dispatch\n"
        "- worktrack_branch: wt/WT-stale-active\n",
    )
    write_doc(
        servo / "repo" / "snapshot-status.md",
        "# Repo Snapshot / Status\n\n"
        "## Current Baseline\n\n"
        "```yaml\n"
        "current_head: \"2222222\"\n"
        "```\n\n"
        "## Active Milestone\n\n"
        "```yaml\n"
        "active_milestone_branch_head: \"2222222\"\n"
        "```\n",
    )
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "- worktrack_id: WT-stale-active\n"
        "  - milestone_id: MS-20260630-004\n"
        "  - status: active\n"
        "  - evidence_ref: .servo/worktrack/gate-evidence.md\n",
    )
    write_doc(
        servo / "repo" / "milestone-backlog.md",
        "- milestone_id: MS-20260630-004\n"
        "  - status: active\n"
        "  - worktrack_list:\n"
        "    - WT-stale-active (config, completed)\n",
    )
    write_doc(servo / "worktrack" / "gate-evidence.md", "# Rolling Evidence\n")

    result = subprocess.run(
        [sys.executable, str(HELPER), "--servo-root", str(servo), "--json"],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    counts = payload["counts_by_type"]
    assert counts["worktrack_live_status_stale"] == 1
    assert counts["split_control_state_worktrack_disagreement"] == 1
    assert counts["repo_snapshot_head_drift"] == 1


def test_cleanup_skill_payloads_include_runtime_sweep_and_exclude_generated_cache() -> None:
    for payload_path in PAYLOADS:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        canonical_paths = payload["canonical_paths"]
        required_payload_files = payload["required_payload_files"]

        assert (
            "product/harness/skills/milestone-cleanup-skill/scripts/runtime_maintenance_sweep.py"
            in canonical_paths
        )
        assert "scripts/runtime_maintenance_sweep.py" in required_payload_files
        assert all(".ruff_cache" not in path for path in canonical_paths)
        assert all(".ruff_cache" not in path for path in required_payload_files)
