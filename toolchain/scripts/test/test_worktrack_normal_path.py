from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "product/harness/skills/harness-skill/scripts"
DEFAULT_SETUP_KEYS = {
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


def run_script(
    script_name: str, args: list[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
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


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def parse_json(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return hashes


def repo_snapshot(root: Path) -> dict[str, object]:
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "branch": git(root, "branch", "--show-current"),
        "status": git(root, "status", "--porcelain=v1", "--untracked-files=all"),
        "tree": git(root, "write-tree"),
        "files": file_hashes(root),
    }


def write_setup_fixture(tmp_path: Path) -> dict[str, Path | str]:
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
    subprocess.run(
        ["git", "branch", "-M", "develop-servo"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / ".gitignore").write_text(".servo/\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "README.md"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    milestone_id = "MS-TEST"
    milestone_branch = "ms/MS-TEST-normal-path"
    worktrack_id = "WT-TEST"
    subprocess.run(
        ["git", "switch", "-c", milestone_branch],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    head = git(tmp_path, "rev-parse", "HEAD")

    servo = tmp_path / ".servo"
    (servo / "repo").mkdir(parents=True)
    (servo / "milestone").mkdir(parents=True)
    control = servo / "control-state.md"
    control.write_text(
        textwrap.dedent(
            f"""\
            # Harness Control State

            ## Approval Boundary
            - needs_programmer_approval: no

            ## Branch Environment Guard
            - baseline_branch: develop-servo
            - active_milestone_branch: {milestone_branch}
            - active_milestone: {milestone_id}

            ## Milestone Review Gate
            - milestone_review_gate_ready: true
            - effective_review_pass: true
            - programmer_confirmed: true
            - ready_for_init_milestone: true
            - intake_skipped: false
            - milestone_review_count: 1
            - latest_review_status: effective_pass
            - intake_status: ready
            - milestone_status: active
            - milestone_kind: goal-driven
            - latest_review_checkpoint: fixture-review
            - milestone_input_checkpoint: fixture-intake
            - review_blockers: []
            - review_invalidated_by: []

            ## Route Decision
            - route_decision: setup approved Worktrack from active milestone
            - worktrack_contract_scope: fixture bounded scope
            - selected_task_dispatch_packet: fixture packet
            - runtime_dispatch_profile: fixture profile

            ## Verification Evidence
            - validation_evidence: fixture validation
            - governance_policy_evidence: fixture policy
            """
        ),
        encoding="utf-8",
    )
    control_repo = servo / "control-state-repo.md"
    control_repo.write_text(
        f"# Repo State\n\n- latest_observed_checkpoint: {head}\n",
        encoding="utf-8",
    )
    control_wt = servo / "control-state-wt.md"
    control_wt.write_text("# Worktrack State\n", encoding="utf-8")
    milestone = servo / f"milestone/{milestone_id}.md"
    milestone.write_text(
        textwrap.dedent(
            f"""\
            # Milestone
            - milestone_id: {milestone_id}
            - baseline_ref: develop-servo@{head}
            """
        ),
        encoding="utf-8",
    )
    intake = servo / f"repo/worktrack-intake-{worktrack_id}.md"
    intake.write_text(
        textwrap.dedent(
            f"""\
            # Worktrack Intake
            - worktrack_id: {worktrack_id}
            - milestone_id: {milestone_id}
            - branch_source_ref: {milestone_branch}@{head}
            - intake_review_verdict: ready_for_worktrack_init
            - ready_for_worktrack_init: true
            - repo_fundamentals: ready
            - snapshot_freshness: current
            - milestone_purpose_alignment: aligned
            - historical_conflict_risk: low
            - worktrack_adjustment_recommendations: no_change_recommended
            - add_remove_worktrack_recommendations: no_change_recommended
            """
        ),
        encoding="utf-8",
    )
    return {
        "control": control,
        "control_repo": control_repo,
        "control_wt": control_wt,
        "milestone": milestone,
        "intake": intake,
        "head": head,
        "milestone_id": milestone_id,
        "milestone_branch": milestone_branch,
        "worktrack_id": worktrack_id,
    }


def setup_args(worktrack_id: str = "WT-TEST") -> list[str]:
    return ["--worktrack-id", worktrack_id]


def test_setup_happy_path_is_check_only(tmp_path: Path) -> None:
    fixture = write_setup_fixture(tmp_path)
    before = repo_snapshot(tmp_path)

    result = run_script("worktrack_setup_check.py", setup_args(), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 0, result.stderr
    assert set(payload) == DEFAULT_SETUP_KEYS
    assert payload["can_setup"] is True
    assert payload["blocked"] is False
    assert payload["missing_evidence"] == []
    assert payload["approval_needed"] is False
    assert payload["allowed_write_surface"] == [
        ".servo/worktrack/contract.md",
        ".servo/worktrack/plan-task-queue.md",
        ".servo/worktrack/gate-evidence.md",
        ".servo/control-state-wt.md",
        ".servo/tmp/WT-TEST",
    ]
    assert payload["expected_branch"] == "wt/WT-TEST"
    assert payload["expected_branch_source"] == (
        f"{fixture['milestone_branch']}@{fixture['head']}"
    )
    assert payload["expected_baseline"] == f"develop-servo@{fixture['head']}"
    assert repo_snapshot(tmp_path) == before


def test_setup_diagnostic_is_explicit_and_check_only(tmp_path: Path) -> None:
    fixture = write_setup_fixture(tmp_path)
    before = repo_snapshot(tmp_path)

    result = run_script(
        "worktrack_setup_check.py", [*setup_args(), "--diagnostic"], tmp_path
    )
    payload = parse_json(result)

    assert result.returncode == 0, result.stderr
    assert set(payload) == DEFAULT_SETUP_KEYS | {"diagnostic"}
    diagnostic = payload["diagnostic"]
    assert isinstance(diagnostic, dict)
    assert diagnostic["repo_root"] == str(tmp_path)
    assert diagnostic["current_branch"] == fixture["milestone_branch"]
    assert diagnostic["current_head"] == fixture["head"]
    assert diagnostic["worktree_clean"] is True
    assert set(diagnostic["guard_results"]) == {
        "intake",
        "milestone_review",
        "runtime_backfill",
        "branch",
        "git_hash",
        "autonomy",
    }
    assert repo_snapshot(tmp_path) == before


def test_setup_blocks_wrong_branch(tmp_path: Path) -> None:
    fixture = write_setup_fixture(tmp_path)
    subprocess.run(
        ["git", "switch", "develop-servo"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = run_script("worktrack_setup_check.py", setup_args(), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert payload["blocked"] is True
    assert any("wrong setup branch" in item for item in payload["blocked_why"])
    assert payload["expected_branch_source"].startswith(
        f"{fixture['milestone_branch']}@"
    )


def test_setup_blocks_checkpoint_mismatch(tmp_path: Path) -> None:
    fixture = write_setup_fixture(tmp_path)
    intake = fixture["intake"]
    assert isinstance(intake, Path)
    intake.write_text(
        intake.read_text(encoding="utf-8").replace(
            str(fixture["head"]), "0" * 40
        ),
        encoding="utf-8",
    )

    result = run_script("worktrack_setup_check.py", setup_args(), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert any("milestone checkpoint mismatch" in item for item in payload["blocked_why"])


def test_setup_blocks_dirty_worktree_without_changing_it(tmp_path: Path) -> None:
    write_setup_fixture(tmp_path)
    (tmp_path / "README.md").write_text("dirty\n", encoding="utf-8")
    before = repo_snapshot(tmp_path)

    result = run_script("worktrack_setup_check.py", setup_args(), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert any("worktree is not clean" in item for item in payload["blocked_why"])
    assert repo_snapshot(tmp_path) == before


def test_setup_exposes_approval_stop(tmp_path: Path) -> None:
    fixture = write_setup_fixture(tmp_path)
    control = fixture["control"]
    assert isinstance(control, Path)
    control.write_text(
        control.read_text(encoding="utf-8").replace(
            "needs_programmer_approval: no",
            "needs_programmer_approval: yes_for_source_mutation",
        ),
        encoding="utf-8",
    )

    result = run_script("worktrack_setup_check.py", setup_args(), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert payload["approval_needed"] is True
    assert payload["approval_reasons"] == [
        "pending setup approval: yes_for_source_mutation"
    ]
    assert "setup requires approval" in payload["blocked_why"]


def test_setup_rejects_invalid_worktrack_id(tmp_path: Path) -> None:
    write_setup_fixture(tmp_path)

    result = run_script("worktrack_setup_check.py", setup_args("../escape"), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert "valid_worktrack_id" in payload["missing_evidence"]
    assert payload["expected_branch"] == ""


def test_setup_rejects_worktrack_ids_that_derive_invalid_git_refs(
    tmp_path: Path,
) -> None:
    write_setup_fixture(tmp_path)
    before = repo_snapshot(tmp_path)

    for worktrack_id in ("WT..bad", "WT."):
        result = run_script(
            "worktrack_setup_check.py", setup_args(worktrack_id), tmp_path
        )
        payload = parse_json(result)

        assert result.returncode == 1
        assert "valid_worktrack_branch" in payload["missing_evidence"]
        assert payload["expected_branch"] == ""
        assert any(
            "not a valid Git ref" in blocker for blocker in payload["blocked_why"]
        )
        assert repo_snapshot(tmp_path) == before


def test_setup_rejects_removed_authority_override_flags(tmp_path: Path) -> None:
    write_setup_fixture(tmp_path)

    result = run_script(
        "worktrack_setup_check.py",
        [*setup_args(), "--expected-branch", "wt/override"],
        tmp_path,
    )

    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_run_guard_converts_non_object_json_to_structured_block(
    tmp_path: Path, monkeypatch
) -> None:
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "worktrack_setup_check_test_module", SCRIPT_DIR / "worktrack_setup_check.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)

    completed = subprocess.CompletedProcess([], 0, stdout="[]", stderr="")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: completed)

    payload = module.run_guard("fixture_guard.py", [], tmp_path)

    assert payload["blocked"] is True
    assert payload["reason"] == "fixture_guard.py returned non-object JSON"
    assert payload["missing_fields"] == ["fixture_guard.py:object_output"]


def write_close_fixture(
    tmp_path: Path,
    *,
    legacy_value: str = "",
    legacy_ref: str = "",
    residual_ref: str = "",
) -> Path:
    control = tmp_path / ".servo/control-state.md"
    control.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Control State",
        "- route_decision: close accepted Worktrack",
    ]
    if legacy_value:
        lines.append(f"- worktrack_gate_verdict: {legacy_value}")
    if legacy_ref:
        lines.append(f"- worktrack_gate_verdict_ref: {legacy_ref}")
    if residual_ref:
        lines.append(f"- worktrack_gate_residual_acceptance_ref: {residual_ref}")
    control.write_text("\n".join(lines) + "\n", encoding="utf-8")
    contract = tmp_path / ".servo/worktrack/contract.md"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text("# Worktrack Contract\n", encoding="utf-8")
    return control


def close_args(control: Path) -> list[str]:
    return [
        "--operation",
        "close",
        "--skill",
        "worktrack-close-skill",
        "--control-state",
        str(control),
    ]


def test_close_policy_accepts_exact_legacy_gate_contract(tmp_path: Path) -> None:
    control = write_close_fixture(
        tmp_path,
        legacy_value="pass",
        legacy_ref=".servo/worktrack/gate-report.md",
    )

    result = run_script("autonomy_policy_check.py", close_args(control), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["close_authority"]["complete"] is True
    assert payload["close_authority"]["source"] == "legacy_gate_contract"
    assert payload["close_authority"]["authority"] == {
        "worktrack_gate_verdict": "pass",
        "worktrack_gate_verdict_ref": ".servo/worktrack/gate-report.md",
        "worktrack_gate_residual_acceptance_ref": "",
    }


def test_close_policy_rejects_placeholder_legacy_ref(tmp_path: Path) -> None:
    control = write_close_fixture(
        tmp_path,
        legacy_value="pass",
        legacy_ref="N/A",
    )

    result = run_script("autonomy_policy_check.py", close_args(control), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert "close_authority:legacy_gate_verdict_ref" in payload["evidence_missing"]


def test_close_policy_requires_legacy_residual_acceptance(tmp_path: Path) -> None:
    control = write_close_fixture(
        tmp_path,
        legacy_value="pass_with_residuals",
        legacy_ref=".servo/worktrack/gate-report.md",
    )

    result = run_script("autonomy_policy_check.py", close_args(control), tmp_path)
    payload = parse_json(result)

    assert result.returncode == 1
    assert (
        "close_authority:legacy_gate_residual_acceptance_ref"
        in payload["evidence_missing"]
    )

    accepted_control = write_close_fixture(
        tmp_path,
        legacy_value="pass_with_residuals",
        legacy_ref=".servo/worktrack/gate-report.md",
        residual_ref=".servo/worktrack/residual-acceptance.md",
    )
    accepted = run_script(
        "autonomy_policy_check.py", close_args(accepted_control), tmp_path
    )
    assert accepted.returncode == 0, accepted.stderr


def test_close_policy_rejects_removed_candidate_authority_flag(tmp_path: Path) -> None:
    control = write_close_fixture(
        tmp_path,
        legacy_value="pass",
        legacy_ref=".servo/worktrack/gate-report.md",
    )
    result = run_script(
        "autonomy_policy_check.py",
        [*close_args(control), "--close-authority-json", "{}"],
        tmp_path,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --close-authority-json" in result.stderr


def test_new_skill_autonomy_profiles_are_explicit_and_bounded(tmp_path: Path) -> None:
    control = tmp_path / ".servo/control-state.md"
    control.parent.mkdir(parents=True)
    control.write_text(
        textwrap.dedent(
            """\
            # Control State
            - route_decision: approved route
            - worktrack_contract_scope: bounded scope
            - selected_task_dispatch_packet: bounded packet
            - runtime_dispatch_profile: current-carrier
            - validation_evidence: focused tests
            - governance_policy_evidence: policy checks
            """
        ),
        encoding="utf-8",
    )
    contract = tmp_path / ".servo/worktrack/contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Worktrack Contract\n", encoding="utf-8")
    cases = (
        ("init_worktrack", "worktrack-plan-work-skill"),
        ("schedule", "worktrack-plan-work-skill"),
        ("dispatch", "worktrack-plan-work-skill"),
        ("verify", "worktrack-review-skill"),
    )

    for operation, skill in cases:
        result = run_script(
            "autonomy_policy_check.py",
            [
                "--operation",
                operation,
                "--skill",
                skill,
                "--control-state",
                str(control),
            ],
            tmp_path,
        )
        payload = parse_json(result)

        assert result.returncode == 0, result.stderr
        assert payload["allowed"] is True
        assert payload["blocked"] is False
        assert payload["needs_approval"] is False
        assert payload["forbidden_hit"] == []
        assert payload["stop_condition_hit"] == []
        assert "未在 POLICY_MAP" not in str(payload["reason"])


def test_plan_setup_preflight_does_not_weaken_legacy_init_evidence(
    tmp_path: Path,
) -> None:
    control = tmp_path / ".servo/control-state.md"
    control.parent.mkdir(parents=True)
    control.write_text("# Control\n- route_decision: approved intake\n", encoding="utf-8")

    candidate = run_script(
        "autonomy_policy_check.py",
        [
            "--operation",
            "init_worktrack",
            "--skill",
            "worktrack-plan-work-skill",
            "--control-state",
            str(control),
        ],
        tmp_path,
    )
    legacy = run_script(
        "autonomy_policy_check.py",
        [
            "--operation",
            "init_worktrack",
            "--skill",
            "worktrack-init-skill",
            "--control-state",
            str(control),
        ],
        tmp_path,
    )

    candidate_payload = parse_json(candidate)
    legacy_payload = parse_json(legacy)
    assert candidate.returncode == 0
    assert candidate_payload["evidence_required_complete"] is True
    assert legacy.returncode == 1
    assert legacy_payload["evidence_required_complete"] is False
    assert any(
        "worktrack_contract_scope" in item
        for item in legacy_payload["evidence_missing"]
    )
