#!/usr/bin/env python3
"""Check Worktrack setup legality for the single servo-managed Git topology."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from _guard_utils import parse_yaml_field


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_WRITE_SURFACE = [
    ".servo/worktrack/contract.md",
    ".servo/worktrack/plan-task-queue.md",
    ".servo/worktrack/gate-evidence.md",
    ".servo/control-state-wt.md",
]
DEFAULT_OUTPUT_KEYS = {
    "can_setup",
    "blocked",
    "blocked_why",
    "missing_evidence",
    "allowed_write_surface",
    "approval_needed",
    "approval_reasons",
    "expected_branch",
    "expected_branch_source",
    "expected_baseline",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NO_APPROVAL_VALUES = {"no", "false", "none", "n/a", "not_required"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def git_value(repo_root: Path, *args: str) -> tuple[str, str]:
    completed = run_command(["git", *args], repo_root)
    if completed.returncode != 0:
        reason = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        return "", reason
    return completed.stdout.strip(), ""


def resolve_repo_root() -> tuple[Path | None, str]:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None, completed.stderr.strip() or "current directory is not inside a Git repository"
    return Path(completed.stdout.strip()).resolve(), ""


def run_guard(script_name: str, args: list[str], repo_root: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / script_name), *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired:
        return {
            "blocked": True,
            "reason": f"{script_name} timed out",
            "missing_fields": [f"{script_name}:completed_result"],
            "returncode": 124,
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "blocked": True,
            "reason": f"{script_name} did not return JSON",
            "missing_fields": [f"{script_name}:structured_output"],
            "returncode": completed.returncode,
        }
    if not isinstance(payload, dict):
        return {
            "blocked": True,
            "reason": f"{script_name} returned non-object JSON",
            "missing_fields": [f"{script_name}:object_output"],
            "returncode": completed.returncode,
        }
    payload["returncode"] = completed.returncode
    return payload


def append_guard_blocker(
    blockers: list[str], missing: list[str], guard_name: str, result: dict[str, Any]
) -> None:
    if bool(result.get("blocked")) or result.get("returncode", 0) != 0:
        blockers.append(f"{guard_name}: {result.get('reason', 'blocked')}")
    raw_missing = result.get("missing_fields", [])
    if isinstance(raw_missing, dict):
        raw_missing = list(raw_missing)
    if isinstance(raw_missing, list):
        missing.extend(f"{guard_name}:{item}" for item in raw_missing)


def parse_ref(value: str) -> tuple[str, str]:
    if "@" not in value:
        return "", ""
    branch, checkpoint = value.rsplit("@", 1)
    return branch.strip(), checkpoint.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Worktrack setup legality")
    parser.add_argument("--worktrack-id", required=True)
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Include nested guard and Git diagnostics",
    )
    args = parser.parse_args()

    blockers: list[str] = []
    missing: list[str] = []
    approval_reasons: list[str] = []
    guards: dict[str, dict[str, Any]] = {}

    if not SAFE_ID.fullmatch(args.worktrack_id):
        blockers.append("worktrack_id must use only letters, numbers, dot, underscore, or hyphen")
        missing.append("valid_worktrack_id")

    repo_root, root_error = resolve_repo_root()
    if repo_root is None:
        blockers.append(root_error)
        missing.append("git_repo_root")

    control = repo_root / ".servo/control-state.md" if repo_root else Path()
    control_repo = repo_root / ".servo/control-state-repo.md" if repo_root else Path()
    control_wt = repo_root / ".servo/control-state-wt.md" if repo_root else Path()

    active_milestone = ""
    control_content = ""
    if repo_root:
        for label, path in (
            ("control_state", control),
            ("control_state_repo", control_repo),
            ("control_state_wt", control_wt),
        ):
            if not path.is_file():
                blockers.append(f"missing required {label}: {path}")
                missing.append(label)
        if control.is_file():
            control_content = read_text(control)
            active_milestone = parse_yaml_field(control_content, "active_milestone")
            if not active_milestone or not SAFE_ID.fullmatch(active_milestone):
                blockers.append("missing or invalid active_milestone")
                missing.append("active_milestone")

    milestone = (
        repo_root / f".servo/milestone/{active_milestone}.md"
        if repo_root and active_milestone
        else Path()
    )
    intake = (
        repo_root / f".servo/repo/worktrack-intake-{args.worktrack_id}.md"
        if repo_root and SAFE_ID.fullmatch(args.worktrack_id)
        else Path()
    )
    if repo_root and active_milestone and not milestone.is_file():
        blockers.append(f"missing required milestone: {milestone}")
        missing.append("milestone")
    if repo_root and SAFE_ID.fullmatch(args.worktrack_id) and not intake.is_file():
        blockers.append(f"missing required worktrack intake: {intake}")
        missing.append("worktrack_intake")

    repo_content = read_text(control_repo) if control_repo.is_file() else ""
    milestone_content = read_text(milestone) if milestone.is_file() else ""
    intake_content = read_text(intake) if intake.is_file() else ""

    milestone_id = parse_yaml_field(milestone_content, "milestone_id")
    intake_milestone_id = parse_yaml_field(intake_content, "milestone_id")
    intake_worktrack_id = parse_yaml_field(intake_content, "worktrack_id")
    for label, value in (
        ("milestone_id", milestone_id),
        ("intake_milestone_id", intake_milestone_id),
        ("intake_worktrack_id", intake_worktrack_id),
    ):
        if not value:
            blockers.append(f"missing required identity: {label}")
            missing.append(label)
    if milestone_id and milestone_id != active_milestone:
        blockers.append(
            f"milestone mismatch: active={active_milestone}, artifact={milestone_id}"
        )
    if intake_milestone_id and intake_milestone_id != active_milestone:
        blockers.append(
            f"intake milestone mismatch: active={active_milestone}, intake={intake_milestone_id}"
        )
    if intake_worktrack_id and intake_worktrack_id != args.worktrack_id:
        blockers.append(
            f"worktrack mismatch: requested={args.worktrack_id}, intake={intake_worktrack_id}"
        )

    active_milestone_branch = parse_yaml_field(control_content, "active_milestone_branch")
    branch_source_ref = parse_yaml_field(intake_content, "branch_source_ref")
    source_branch, source_checkpoint = parse_ref(branch_source_ref)
    baseline_ref = parse_yaml_field(milestone_content, "baseline_ref")
    expected_branch = f"wt/{args.worktrack_id}" if SAFE_ID.fullmatch(args.worktrack_id) else ""
    if repo_root and expected_branch:
        branch_check = run_command(
            ["git", "check-ref-format", "--branch", expected_branch], repo_root
        )
        if branch_check.returncode != 0:
            blockers.append(
                f"derived worktrack branch is not a valid Git ref: {expected_branch}"
            )
            missing.append("valid_worktrack_branch")
            expected_branch = ""

    current_branch = ""
    current_head = ""
    worktree_status = ""
    if repo_root:
        current_branch, branch_error = git_value(repo_root, "branch", "--show-current")
        current_head, head_error = git_value(repo_root, "rev-parse", "HEAD")
        worktree_status, status_error = git_value(
            repo_root, "status", "--porcelain=v1", "--untracked-files=normal"
        )
        for label, value, error in (
            ("current_branch", current_branch, branch_error),
            ("current_head", current_head, head_error),
        ):
            if error or not value:
                blockers.append(f"missing Git evidence {label}: {error or 'empty'}")
                missing.append(label)
        if status_error:
            blockers.append(f"unable to inspect worktree: {status_error}")
            missing.append("worktree_status")
        elif worktree_status:
            blockers.append("setup source worktree is not clean")

    for label, value in (
        ("active_milestone_branch", active_milestone_branch),
        ("branch_source_ref", branch_source_ref),
        ("branch_source_checkpoint", source_checkpoint),
        ("baseline_ref", baseline_ref),
    ):
        if not value:
            blockers.append(f"missing branch/baseline evidence: {label}")
            missing.append(label)
    if current_branch and active_milestone_branch and current_branch != active_milestone_branch:
        blockers.append(
            f"wrong setup branch: current={current_branch}, expected={active_milestone_branch}"
        )
    if source_branch and active_milestone_branch and source_branch != active_milestone_branch:
        blockers.append(
            f"branch source mismatch: intake={source_branch}, active={active_milestone_branch}"
        )
    if current_head and source_checkpoint and current_head != source_checkpoint:
        blockers.append(
            f"milestone checkpoint mismatch: HEAD={current_head}, expected={source_checkpoint}"
        )

    approval_value = parse_yaml_field(control_content, "needs_programmer_approval")
    approval_needed = approval_value.lower() not in NO_APPROVAL_VALUES
    if not approval_value:
        missing.append("needs_programmer_approval")
        approval_reasons.append("setup approval state is missing")
    elif approval_needed:
        approval_reasons.append(f"pending setup approval: {approval_value}")
    if approval_needed:
        blockers.append("setup requires approval")

    if repo_root and not blockers:
        guards["intake"] = run_guard(
            "worktrack_intake_review_check.py",
            ["--intake-review", str(intake)],
            repo_root,
        )
        guards["milestone_review"] = run_guard(
            "milestone_review_gate_check.py",
            ["--control-state", str(control)],
            repo_root,
        )
        guards["runtime_backfill"] = run_guard(
            "runtime_backfill_detect.py", ["--artifact", str(control)], repo_root
        )
        guards["branch"] = run_guard(
            "branch_context_check.py",
            [
                "--control-state",
                str(control),
                "--scope",
                "WorktrackScope",
                "--function",
                "Init",
            ],
            repo_root,
        )
        guards["git_hash"] = run_guard(
            "git_hash_check.py", ["--control-state", str(control_repo)], repo_root
        )
        guards["autonomy"] = run_guard(
            "autonomy_policy_check.py",
            [
                "--operation",
                "init_worktrack",
                "--skill",
                "worktrack-plan-work-skill",
                "--control-state",
                str(control),
            ],
            repo_root,
        )
        for name in ("intake", "milestone_review", "branch", "git_hash", "autonomy"):
            append_guard_blocker(blockers, missing, name, guards[name])

        backfill_missing = guards["runtime_backfill"].get("missing_fields", {})
        if backfill_missing:
            blockers.append("runtime_backfill: required control fields are missing")
            if isinstance(backfill_missing, dict):
                missing.extend(f"runtime_backfill:{item}" for item in backfill_missing)

    result: dict[str, Any] = {
        "can_setup": not blockers,
        "blocked": bool(blockers),
        "blocked_why": blockers,
        "missing_evidence": sorted(set(missing)),
        "allowed_write_surface": [
            *DEFAULT_WRITE_SURFACE,
            *(
                [f".servo/tmp/{args.worktrack_id}"]
                if expected_branch
                else []
            ),
        ],
        "approval_needed": approval_needed,
        "approval_reasons": approval_reasons,
        "expected_branch": expected_branch,
        "expected_branch_source": branch_source_ref,
        "expected_baseline": baseline_ref,
    }
    assert set(result) == DEFAULT_OUTPUT_KEYS
    if args.diagnostic:
        result["diagnostic"] = {
            "repo_root": str(repo_root) if repo_root else "",
            "current_branch": current_branch,
            "current_head": current_head,
            "worktree_clean": not bool(worktree_status),
            "active_milestone": active_milestone,
            "guard_results": guards,
            "notes": [
                "check-only: no branch, artifact, plan, task, or control-state mutation"
            ],
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["can_setup"] else 1)


if __name__ == "__main__":
    main()
