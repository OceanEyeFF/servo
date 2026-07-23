from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "product/harness/skills/harness-skill/scripts"
AUTONOMY_POLICY_COPY_PATHS = (
    SCRIPT_DIR / "autonomy_policy_check.py",
    REPO_ROOT / ".agents/skills/harness-skill/scripts/autonomy_policy_check.py",
    REPO_ROOT / ".claude/skills/harness-skill/scripts/autonomy_policy_check.py",
)


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


def write_branch_control_state(path: Path, baseline: str, milestone: str = "") -> None:
    milestone_line = (
        f"- active_milestone_branch: {milestone}\n"
        if milestone
        else "- active_milestone_branch: none\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            ---
            updated: "2026-06-30T00:00:00Z"
            ---
            # Control State

            ## Branch Context
            - baseline_branch: {baseline}
            {milestone_line}- latest_observed_checkpoint: test-checkpoint
            """
        ),
        encoding="utf-8",
    )


def checkout_branch(repo: Path, branch: str) -> None:
    subprocess.run(
        ["git", "checkout", "-B", branch],
        cwd=repo,
        check=True,
        capture_output=True,
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


def test_autonomy_policy_cleanup_skills_use_explicit_non_destructive_profiles(
    tmp_path: Path,
) -> None:
    control_state = tmp_path / ".servo/control-state.md"
    control_state.parent.mkdir(parents=True)
    control_state.write_text(
        "# Control State\n\n- closeout_record: .servo/milestone/closeout.md\n",
        encoding="utf-8",
    )

    for skill in (
        "milestone-cleanup-skill",
        "worktrack-cleanup-skill",
        "servo-cleanup-skill",
        "cleanup-skill",
    ):
        result = run_script(
            "autonomy_policy_check.py",
            [
                "--operation",
                "cleanup",
                "--skill",
                skill,
                "--control-state",
                str(control_state),
            ],
            tmp_path,
        )
        payload = parse_stdout_json(result)

        assert result.returncode == 0, result.stderr
        assert payload["allowed"] is True
        assert payload["blocked"] is False
        assert payload["needs_approval"] is False
        assert payload["forbidden_hit"] == []
        assert payload["stop_condition_hit"] == []
        assert "cleanup apply/delete/move/archive" in str(payload["reason"])
        assert "显式审批" in str(payload["reason"])
        assert "未在 POLICY_MAP" not in str(payload["reason"])


def test_autonomy_policy_cleanup_copies_reject_stale_safe_delete_wording() -> None:
    stale_terms = ("使用 -d 安全删除", "不命中 forbidden:destructive_cleanup")
    checked_paths = [path for path in AUTONOMY_POLICY_COPY_PATHS if path.exists()]

    assert SCRIPT_DIR / "autonomy_policy_check.py" in checked_paths

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for term in stale_terms:
            assert term not in text, f"{path} still contains stale term {term!r}"

        for skill in ("servo-cleanup-skill", "cleanup-skill"):
            profile_start = text.index(f'"cleanup::{skill}"')
            profile_block = text[profile_start : profile_start + 1000]
            assert "cleanup report/dry-run" in profile_block
            assert "cleanup apply/delete/" in profile_block
            assert "move/archive" in profile_block
            assert "显式审批" in profile_block

        default_start = text.index('"cleanup": PolicyProfile(')
        default_block = text[default_start : default_start + 400]
        assert "仅允许非破坏性 cleanup report/dry-run" in default_block
        assert "cleanup apply/delete/move/archive" in default_block
        assert "安全删除" not in default_block


def test_autonomy_policy_allows_unified_milestone_init_with_embedded_approval_boundary(
    tmp_path: Path,
) -> None:
    control_state = tmp_path / ".servo" / "control-state.md"
    control_state.parent.mkdir(parents=True)
    control_state.write_text(
        "# control\n\n- route_decision: discuss and apply one exact approved Milestone revision\n",
        encoding="utf-8",
    )

    result = run_script(
        "autonomy_policy_check.py",
        [
            "--operation",
            "init_milestone",
            "--skill",
            "milestone-init-skill",
            "--control-state",
            str(control_state),
        ],
        tmp_path,
    )
    payload = parse_stdout_json(result)

    assert result.returncode == 0, result.stderr
    assert payload["allowed"] is True
    assert payload["blocked"] is False
    assert payload["needs_approval"] is False
    assert payload["forbidden_hit"] == []
    assert payload["stop_condition_hit"] == []
    assert "exact preview" in str(payload["reason"])
    assert "expected canonical revision/digest" in str(payload["reason"])
    assert "release/publish/tag/push/deploy" in str(payload["reason"])
    assert "未在 POLICY_MAP" not in str(payload["reason"])


def test_milestone_callers_use_preserved_lifecycle_and_authority_vocabulary() -> None:
    whats_next = (
        REPO_ROOT / "product/harness/skills/repo-whats-next-skill/SKILL.md"
    ).read_text(encoding="utf-8")
    harness = (
        REPO_ROOT / "product/harness/skills/harness-skill/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "goal_achieved" not in whats_next
    assert "purpose_achieved" in whats_next
    assert "create/activate/append_worktracks" not in harness
    assert "`create/amend/select`" in harness
    assert "milestone-init-skill` 承接 create/amend" in harness
    assert "select 仍由 Harness 独占" in harness


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


def test_runtime_skill_docs_use_package_local_script_commands() -> None:
    cleanup_docs = [
        "product/harness/skills/milestone-cleanup-skill/SKILL.md",
        "product/harness/skills/worktrack-cleanup-skill/SKILL.md",
    ]
    cleanup_installed_docs = [
        ".agents/skills/milestone-cleanup-skill/SKILL.md",
        ".agents/skills/worktrack-cleanup-skill/SKILL.md",
        ".claude/skills/milestone-cleanup-skill/SKILL.md",
        ".claude/skills/worktrack-cleanup-skill/SKILL.md",
    ]
    repo_init_goal_runtime_docs = [
        "product/harness/skills/repo-init-goal-skill/SKILL.md",
        "docs/project-maintenance/usage-help/claude.md",
    ]
    repo_init_goal_installed_runtime_docs = [
        ".agents/skills/repo-init-goal-skill/SKILL.md",
        ".claude/skills/repo-init-goal-skill/SKILL.md",
    ]
    repo_init_goal_asset_docs = [
        "product/harness/skills/repo-init-goal-skill/assets/README.md",
    ]
    repo_init_goal_installed_asset_docs = [
        ".agents/skills/repo-init-goal-skill/assets/README.md",
        ".claude/skills/repo-init-goal-skill/assets/README.md",
    ]
    bare_python_runtime = "python3 " + "scripts/"
    bare_node_deploy = "node " + "scripts/deploy_servo.js"

    optional_installed_paths = (
        cleanup_installed_docs
        + repo_init_goal_installed_runtime_docs
        + repo_init_goal_installed_asset_docs
    )
    existing_optional_paths = [
        path for path in optional_installed_paths if (REPO_ROOT / path).exists()
    ]

    for relative_path in cleanup_docs + [
        path for path in existing_optional_paths if "cleanup-skill" in path
    ]:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert bare_python_runtime not in text, relative_path
        assert "python3 ./scripts/control_state_compact.py" in text, relative_path
        assert "python3 ./scripts/runtime_maintenance_sweep.py" in text, relative_path

    for relative_path in repo_init_goal_runtime_docs + repo_init_goal_asset_docs + [
        path for path in existing_optional_paths if "repo-init-goal-skill" in path
    ]:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert bare_node_deploy not in text, relative_path
        assert "node ./scripts/deploy_servo.js" in text, relative_path


def test_branch_context_refresh_accepts_milestone_and_baseline_refs(
    tmp_path: Path,
) -> None:
    init_repo(tmp_path)
    baseline = "develop-servo"
    milestone = "ms/MS-20260630-001-harness-guard-fixtures"
    subprocess.run(["git", "branch", "-M", baseline], cwd=tmp_path, check=True)
    write_branch_control_state(tmp_path / ".servo/control-state.md", baseline, milestone)

    checkout_branch(tmp_path, milestone)
    milestone_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--scope",
            "RepoScope",
            "--function",
            "Refresh",
        ],
        tmp_path,
    )
    milestone_payload = parse_stdout_json(milestone_result)
    assert milestone_result.returncode == 0, milestone_result.stderr
    assert milestone_payload["blocked"] is False
    assert milestone_payload["branch_context"] == "milestone"
    assert milestone_payload["expected_contexts"] == []
    assert milestone_payload["expected_branches"] == [milestone, baseline]

    checkout_branch(tmp_path, baseline)
    baseline_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--scope",
            "RepoScope",
            "--function",
            "Refresh",
        ],
        tmp_path,
    )
    baseline_payload = parse_stdout_json(baseline_result)
    assert baseline_result.returncode == 0, baseline_result.stderr
    assert baseline_payload["blocked"] is False
    assert baseline_payload["branch_context"] == "baseline"
    assert baseline_payload["expected_branches"] == [milestone, baseline]


def test_branch_context_candidate_init_and_review_derive_worktrack_branch(
    tmp_path: Path,
) -> None:
    init_repo(tmp_path)
    baseline = "develop-servo"
    milestone = "ms/MS-20260630-001-harness-guard-fixtures"
    worktrack_id = "WT-branch-context-refresh-guard-fix"
    worktrack = f"wt/{worktrack_id}"
    subprocess.run(["git", "branch", "-M", baseline], cwd=tmp_path, check=True)
    write_branch_control_state(tmp_path / ".servo/control-state.md", baseline, milestone)

    checkout_branch(tmp_path, milestone)
    init_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--worktrack-id",
            worktrack_id,
            "--scope",
            "WorktrackScope",
            "--function",
            "Init",
        ],
        tmp_path,
    )
    init_payload = parse_stdout_json(init_result)
    assert init_result.returncode == 0, init_result.stderr
    assert init_payload["blocked"] is False
    assert init_payload["derived_worktrack_branch"] == worktrack
    assert init_payload["expected_branches"] == [milestone]

    checkout_branch(tmp_path, worktrack)
    review_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--worktrack-id",
            worktrack_id,
            "--scope",
            "WorktrackScope",
            "--function",
            "Verify",
        ],
        tmp_path,
    )
    review_payload = parse_stdout_json(review_result)
    assert review_result.returncode == 0, review_result.stderr
    assert review_payload["blocked"] is False
    assert review_payload["branch_context"] == "worktrack"
    assert review_payload["expected_branches"] == []


def test_branch_context_close_accepts_worktrack_and_closeout_target_refs(
    tmp_path: Path,
) -> None:
    init_repo(tmp_path)
    baseline = "develop-servo"
    milestone = "ms/MS-20260630-001-harness-guard-fixtures"
    worktrack_id = "WT-branch-context-refresh-guard-fix"
    worktrack = f"wt/{worktrack_id}"
    subprocess.run(["git", "branch", "-M", baseline], cwd=tmp_path, check=True)
    write_branch_control_state(tmp_path / ".servo/control-state.md", baseline, milestone)

    checkout_branch(tmp_path, worktrack)
    worktrack_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--worktrack-id",
            worktrack_id,
            "--scope",
            "WorktrackScope",
            "--function",
            "Close",
        ],
        tmp_path,
    )
    worktrack_payload = parse_stdout_json(worktrack_result)
    assert worktrack_result.returncode == 0, worktrack_result.stderr
    assert worktrack_payload["blocked"] is False
    assert worktrack_payload["branch_context"] == "worktrack"
    assert worktrack_payload["expected_contexts"] == ["worktrack"]
    assert worktrack_payload["expected_branches"] == [worktrack, milestone]

    checkout_branch(tmp_path, milestone)
    closeout_result = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--worktrack-id",
            worktrack_id,
            "--scope",
            "WorktrackScope",
            "--function",
            "Close",
        ],
        tmp_path,
    )
    closeout_payload = parse_stdout_json(closeout_result)
    assert closeout_result.returncode == 0, closeout_result.stderr
    assert closeout_payload["blocked"] is False
    assert closeout_payload["branch_context"] == "milestone"
    assert closeout_payload["expected_contexts"] == ["worktrack"]
    assert closeout_payload["expected_branches"] == [worktrack, milestone]

    checkout_branch(tmp_path, "feature/wrong-close-target")
    blocked = run_script(
        "branch_context_check.py",
        [
            "--control-state",
            ".servo/control-state.md",
            "--worktrack-id",
            worktrack_id,
            "--scope",
            "WorktrackScope",
            "--function",
            "Close",
        ],
        tmp_path,
    )
    blocked_payload = parse_stdout_json(blocked)
    assert blocked.returncode == 1
    assert blocked_payload["blocked"] is True
    assert blocked_payload["branch_context"] == "unknown"
    assert blocked_payload["target_branch"] == milestone
    assert blocked_payload["expected_branches"] == [worktrack, milestone]


def test_branch_context_rejects_missing_or_invalid_candidate_worktrack_id(
    tmp_path: Path,
) -> None:
    init_repo(tmp_path)
    baseline = "develop-servo"
    milestone = "ms/MS-20260630-001-harness-guard-fixtures"
    subprocess.run(["git", "branch", "-M", baseline], cwd=tmp_path, check=True)
    write_branch_control_state(tmp_path / ".servo/control-state.md", baseline, milestone)
    checkout_branch(tmp_path, milestone)

    for worktrack_id in ("", "../escape", "WT..bad"):
        args = [
            "--control-state",
            ".servo/control-state.md",
            "--scope",
            "WorktrackScope",
            "--function",
            "Init",
        ]
        if worktrack_id:
            args.extend(["--worktrack-id", worktrack_id])
        result = run_script("branch_context_check.py", args, tmp_path)
        payload = parse_stdout_json(result)

        assert result.returncode == 1
        assert payload["blocked"] is True
        assert payload["derived_worktrack_branch"] == ""
