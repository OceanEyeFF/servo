#!/usr/bin/env python3
"""Simulate runtime artifact consistency outcomes with disposable fixtures."""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from governance_semantic_check import SemanticReport, check_runtime_artifact_consistency
except ModuleNotFoundError:
    from toolchain.scripts.test.governance_semantic_check import (
        SemanticReport,
        check_runtime_artifact_consistency,
    )


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    description: str
    expected_pass: bool
    active_milestone: str = "MS-001"
    active_worktrack: str = "none"
    milestone_status: str = "active"
    summary: str = "planned=0 / active=1 / completed=1 / superseded=0"
    live_status: str = "active"
    history_status: str = "completed"
    milestone_artifact_status: str = "active"
    milestone_artifact_completed: int = 0
    milestone_artifact_total: int = 1
    milestone_artifact_worktrack_status_key: str = "status"
    milestone_artifact_worktrack_status: str = "planned"
    include_live_entry: bool = True
    include_history_entry: bool = True


SCENARIOS = [
    Scenario(
        scenario_id="consistent-active",
        description="Active milestone is live, active pointer matches it, and the only completed milestone is in history.",
        expected_pass=True,
    ),
    Scenario(
        scenario_id="completed-artifact-still-live",
        description="Milestone artifact says completed, but live backlog and active_milestone still point at it.",
        expected_pass=False,
        milestone_artifact_status="completed",
        milestone_artifact_completed=1,
        milestone_artifact_worktrack_status="completed",
    ),
    Scenario(
        scenario_id="active-worktrack-closed",
        description="active_worktrack points at a worktrack whose actual status is completed.",
        expected_pass=False,
        active_worktrack="WT-001",
        milestone_artifact_worktrack_status="completed",
    ),
    Scenario(
        scenario_id="completed-artifact-incomplete-progress",
        description="Completed milestone artifact has progress 0/1, so accepted writeback is internally inconsistent.",
        expected_pass=False,
        active_milestone="none",
        milestone_status="none",
        summary="planned=0 / active=0 / completed=2 / superseded=0",
        include_live_entry=False,
        milestone_artifact_status="completed",
        milestone_artifact_completed=0,
        milestone_artifact_worktrack_status="completed",
    ),
    Scenario(
        scenario_id="active-expected-status-completed",
        description="Active milestone lists expected_status completed for the target worktrack; this is only a goal and must not fail.",
        expected_pass=True,
        active_worktrack="WT-001",
        milestone_artifact_worktrack_status_key="expected_status",
        milestone_artifact_worktrack_status="completed",
    ),
]


def write_doc(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_fixture(root: Path, scenario: Scenario) -> None:
    write_doc(
        root / ".servo/control-state.md",
        "\n".join(
            [
                "# Harness Control State",
                "",
                "## Active Worktrack",
                f"- active_worktrack: {scenario.active_worktrack}",
                "- latest_closed_worktrack: WT-CLOSED",
                "",
                "## Milestone Pipeline",
                f"- active_milestone: {scenario.active_milestone}",
                f"- milestone_status: {scenario.milestone_status}",
                f"- milestone_pipeline_summary: {scenario.summary}",
                "",
            ]
        ),
    )

    live_entry = ""
    if scenario.include_live_entry:
        live_entry = "\n".join(
            [
                "- milestone_id: MS-001",
                f"  - status: {scenario.live_status}",
                "  - worktrack_list:",
                "    - WT-001 (planned)",
                "",
            ]
        )
    write_doc(
        root / ".servo/repo/milestone-backlog.md",
        "# Repo Milestone Backlog\n\n## Pipeline Entries\n\n" + live_entry,
    )

    history_entry = ""
    if scenario.include_history_entry:
        history_entry = "\n".join(
            [
                "- milestone_id: MS-000",
                f"  - status: {scenario.history_status}",
                "  - acceptance:",
                "    - verdict: accepted",
                "  - worktrack_list:",
                "    - WT-000 (done)",
                "",
            ]
        )
        if not scenario.include_live_entry:
            history_entry += "\n".join(
                [
                    "- milestone_id: MS-001",
                    "  - status: completed",
                    "  - acceptance:",
                    "    - verdict: accepted",
                    "  - worktrack_list:",
                    "    - WT-001 (done)",
                    "",
                ]
            )
    write_doc(
        root / ".servo/repo/milestone-history.md",
        "# Repo Milestone History\n\n## History Entries\n\n" + history_entry,
    )

    write_doc(
        root / ".servo/milestone/MS-001.md",
        "\n".join(
            [
                "# Test Milestone",
                "",
                "## milestone_id",
                'milestone_id: "MS-001"',
                "",
                "## status",
                f'status: "{scenario.milestone_artifact_status}"',
                "",
                "## worktrack_list",
                "worktrack_list:",
                '  - worktrack_id: "WT-001"',
                f'    {scenario.milestone_artifact_worktrack_status_key}: "{scenario.milestone_artifact_worktrack_status}"',
                "",
                "## progress_counter",
                "progress_counter:",
                f"  total: {scenario.milestone_artifact_total}",
                f"  completed: {scenario.milestone_artifact_completed}",
                "  blocked: 0",
                "  deferred: 0",
                "",
            ]
        ),
    )
    write_doc(
        root / ".servo/milestone/MS-000.md",
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


def run_scenario(scenario: Scenario) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="servo-runtime-sim-") as tmpdir:
        root = Path(tmpdir)
        build_fixture(root, scenario)
        report = SemanticReport()
        check_runtime_artifact_consistency(root, report)
        passed = not report.failures
        return {
            "scenario_id": scenario.scenario_id,
            "description": scenario.description,
            "expected_pass": scenario.expected_pass,
            "actual_pass": passed,
            "failures": report.failures,
        }


def main() -> int:
    results = [run_scenario(scenario) for scenario in SCENARIOS]
    print(json.dumps({"scenarios": results}, ensure_ascii=False, indent=2))
    return 0 if all(item["expected_pass"] == item["actual_pass"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
