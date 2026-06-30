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
    / "worktrack-cleanup-skill"
    / "scripts"
    / "runtime_maintenance_sweep.py"
)
PAYLOADS = (
    REPO_ROOT / "product" / "harness" / "adapters" / "agents" / "skills" / "worktrack-cleanup-skill" / "payload.json",
    REPO_ROOT / "product" / "harness" / "adapters" / "claude" / "skills" / "worktrack-cleanup-skill" / "payload.json",
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


def test_cleanup_skill_payloads_include_runtime_sweep_and_exclude_generated_cache() -> None:
    for payload_path in PAYLOADS:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        canonical_paths = payload["canonical_paths"]
        required_payload_files = payload["required_payload_files"]

        assert (
            "product/harness/skills/worktrack-cleanup-skill/scripts/runtime_maintenance_sweep.py"
            in canonical_paths
        )
        assert "scripts/runtime_maintenance_sweep.py" in required_payload_files
        assert all(".ruff_cache" not in path for path in canonical_paths)
        assert all(".ruff_cache" not in path for path in required_payload_files)
