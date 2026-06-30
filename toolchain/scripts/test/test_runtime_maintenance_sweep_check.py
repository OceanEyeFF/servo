from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "toolchain" / "scripts" / "test" / "runtime_maintenance_sweep_check.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_maintenance_sweep_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_doc(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_minimal_servo(root: Path) -> Path:
    servo = root / ".servo"
    write_doc(
        servo / "control-state.md",
        "# Control\n\n- active_milestone: MS-001\n- active_worktrack: WT-002\n",
    )
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "# Backlog\n\n"
        "- worktrack_id: WT-001\n"
        "  - milestone_id: MS-001\n"
        "  - status: done\n"
        "  - evidence_ref: .servo/milestone/MS-001-closeout-records.md#WT-001\n"
        "  - closeout_record_ref: .servo/milestone/MS-001-closeout-records.md#WT-001\n",
    )
    write_doc(
        servo / "milestone" / "MS-001.md",
        "# MS-001\n\n- closeout_record: .servo/milestone/MS-001-closeout-records.md\n",
    )
    write_doc(
        servo / "milestone" / "MS-001-closeout-records.md",
        "# Closeout\n\n## WT-001\n\n- evidence_ref: .servo/milestone/MS-001-closeout-records.md#WT-001\n",
    )
    write_doc(servo / "worktrack" / "gate-evidence.md", "# Current Evidence\n")
    return servo


def finding_types(report: dict[str, object]) -> set[str]:
    return {str(finding["type"]) for finding in report["findings"]}


def test_clean_fixture_has_no_findings(tmp_path: Path) -> None:
    module = load_module()
    servo = build_minimal_servo(tmp_path)

    report = module.sweep(servo)

    assert report["finding_count"] == 0
    assert report["cleanup_executed"] is False


def test_reports_stale_refs(tmp_path: Path) -> None:
    module = load_module()
    servo = build_minimal_servo(tmp_path)
    write_doc(servo / "repo" / "append-request-test.md", "- evidence: .servo/milestone/MISSING.md\n")

    report = module.sweep(servo)

    assert "stale_reference" in finding_types(report)


def test_reports_rolling_evidence_reuse_without_stable_ref(tmp_path: Path) -> None:
    module = load_module()
    servo = build_minimal_servo(tmp_path)
    write_doc(
        servo / "repo" / "worktrack-backlog.md",
        "# Backlog\n\n"
        "- worktrack_id: WT-001\n"
        "  - milestone_id: MS-001\n"
        "  - status: done\n"
        "  - evidence_ref: .servo/worktrack/gate-evidence.md\n",
    )

    report = module.sweep(servo)

    assert "rolling_evidence_reuse" in finding_types(report)


def test_reports_orphan_runtime_artifact(tmp_path: Path) -> None:
    module = load_module()
    servo = build_minimal_servo(tmp_path)
    write_doc(servo / "scratchpad" / "orphan-note.md", "# Orphan\n")

    report = module.sweep(servo)

    assert "orphan_artifact" in finding_types(report)


def test_reports_temporary_lifecycle_gap(tmp_path: Path) -> None:
    module = load_module()
    servo = build_minimal_servo(tmp_path)
    write_doc(servo / "repo" / "temporary-discovery-note.md", "# Temporary note\n")

    report = module.sweep(servo)

    assert "temporary_lifecycle_gap" in finding_types(report)


def test_report_mode_exits_zero_with_findings(tmp_path: Path) -> None:
    servo = build_minimal_servo(tmp_path)
    write_doc(servo / "repo" / "append-request-test.md", "- evidence: .servo/milestone/MISSING.md\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--servo-root", str(servo), "--json"],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["finding_count"] >= 1
    assert payload["cleanup_executed"] is False


def test_fail_on_findings_exits_nonzero(tmp_path: Path) -> None:
    servo = build_minimal_servo(tmp_path)
    write_doc(servo / "repo" / "append-request-test.md", "- evidence: .servo/milestone/MISSING.md\n")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--servo-root",
            str(servo),
            "--json",
            "--fail-on-findings",
        ],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
