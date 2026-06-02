import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
NODE_HELPER = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "set-harness-goal-skill"
    / "scripts"
    / "deploy_servo.js"
)
AGENTS_PAYLOAD = (
    REPO_ROOT
    / "product"
    / "harness"
    / "adapters"
    / "agents"
    / "skills"
    / "set-harness-goal-skill"
    / "payload.json"
)
INSTALLER = REPO_ROOT / "toolchain" / "scripts" / "deploy" / "bin" / "servo-installer.js"
CLAUDE_PAYLOAD = (
    REPO_ROOT
    / "product"
    / "harness"
    / "adapters"
    / "claude"
    / "skills"
    / "set-harness-goal-skill"
    / "payload.json"
)


def run_node(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(NODE_HELPER), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_installed_node(
    helper: Path, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(helper), *args],
        cwd=cwd or helper.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_installer(
    cwd: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(INSTALLER), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, check=True)
    (path / "README.md").write_text("# temporary target\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
    )


def test_node_deploy_servo_validates_skill_assets() -> None:
    completed = run_node("validate")

    assert completed.returncode == 0, completed.stderr
    assert "[goal-charter] ok:" in completed.stdout
    assert "deploy_aw.py" not in completed.stdout


def test_node_deploy_servo_generates_existing_code_adoption_profile(tmp_path: Path) -> None:
    completed = run_node(
        "generate",
        "--deploy-path",
        str(tmp_path),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-05-03",
        "--adoption-mode",
        "existing-code-adoption",
    )

    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / ".servo" / "control-state.md").is_file()
    assert (tmp_path / ".servo" / "repo" / "discovery-input.md").is_file()
    assert not (tmp_path / ".servo" / "repo" / "temporary-understanding.md").exists()
    assert not (tmp_path / ".servo" / "repo" / "complex-project-entry-gate.md").exists()
    assert (tmp_path / ".servo" / "template" / "goal-charter.template.md").is_file()
    discovery = (tmp_path / ".servo" / "repo" / "discovery-input.md").read_text(
        encoding="utf-8"
    )
    assert "adoption_mode: existing-code-adoption" in discovery
    assert "baseline_branch: main" in discovery
    control_state = (tmp_path / ".servo" / "control-state.md").read_text(
        encoding="utf-8"
    )
    assert "- repo_scope: active" in control_state
    assert "- worktrack_scope: closed" in control_state
    assert "- latest_observed_checkpoint:" in control_state
    assert "- last_doc_catch_up_checkpoint:" in control_state


def test_node_deploy_servo_generates_weak_doc_temporary_understanding_when_requested(
    tmp_path: Path,
) -> None:
    completed = run_node(
        "generate",
        "--deploy-path",
        str(tmp_path),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-05-31",
        "--adoption-mode",
        "existing-code-adoption",
        "--weak-doc-onboarding",
    )

    assert completed.returncode == 0, completed.stderr
    temp_understanding_path = tmp_path / ".servo" / "repo" / "temporary-understanding.md"
    complex_gate_path = tmp_path / ".servo" / "repo" / "complex-project-entry-gate.md"
    assert temp_understanding_path.is_file()
    assert complex_gate_path.is_file()
    temp_understanding = temp_understanding_path.read_text(encoding="utf-8")
    assert "temporary_understanding: repo/temporary-understanding.md" in temp_understanding
    assert "truth_status: temporary-inferred" in temp_understanding
    assert "not Goal Charter truth" in temp_understanding
    complex_gate = complex_gate_path.read_text(encoding="utf-8")
    assert "gate_id: complex_project_entry_gate" in complex_gate
    assert "scanner_output_role: scanner output is evidence, not verdict" in complex_gate
    assert "gate_truth_status: runtime-evidence" in complex_gate
    assert "trigger_conditions: pending_observed_signal_review" in complex_gate
    assert "allowed_high_risk_command_modes: pending_programmer_confirmation" in complex_gate
    assert "\n    - normal\n" not in complex_gate
    assert "\n    - autoreview\n" not in complex_gate
    assert "\n    - yolo\n" not in complex_gate
    assert "entry_verdict: blocked" in complex_gate
    assert "milestone_blocking_decision: block_derive_worktrack" in complex_gate
    assert "needed: true" in complex_gate
    assert "recommendation_status: pending_operator_review" in complex_gate
    assert "blocks_implementation_until_resolved: true" in complex_gate
    assert "temporary_understanding_ref: temporary-understanding.md" in complex_gate


def test_node_deploy_servo_generates_complex_project_gate_when_requested(
    tmp_path: Path,
) -> None:
    completed = run_node(
        "generate",
        "--deploy-path",
        str(tmp_path),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-06-02",
        "--adoption-mode",
        "existing-code-adoption",
        "--complex-project-entry-gate",
    )

    assert completed.returncode == 0, completed.stderr
    complex_gate_path = tmp_path / ".servo" / "repo" / "complex-project-entry-gate.md"
    assert complex_gate_path.is_file()
    assert not (tmp_path / ".servo" / "repo" / "temporary-understanding.md").exists()
    complex_gate = complex_gate_path.read_text(encoding="utf-8")
    assert "trigger_source: repo-init" in complex_gate
    assert "Milestone-side blocking gate, not fixed heavy mode" in complex_gate
    assert "scanner output is evidence, not verdict" in complex_gate
    assert "trigger_conditions: pending_observed_signal_review" in complex_gate
    assert "allowed_high_risk_command_modes: pending_programmer_confirmation" in complex_gate
    assert "\n    - normal\n" not in complex_gate
    assert "\n    - autoreview\n" not in complex_gate
    assert "\n    - yolo\n" not in complex_gate
    assert "entry_verdict: blocked" in complex_gate
    assert "milestone_blocking_decision: block_derive_worktrack" in complex_gate
    assert "needed: false" in complex_gate
    assert "recommendation_status: not_needed" in complex_gate
    assert "blocks_implementation_until_resolved: false" in complex_gate
    assert "temporary_understanding_ref: N/A" in complex_gate


def test_node_deploy_servo_rejects_complex_gate_without_adoption_mode(tmp_path: Path) -> None:
    completed = run_node(
        "generate",
        "--deploy-path",
        str(tmp_path),
        "--complex-project-entry-gate",
    )

    assert completed.returncode != 0
    assert "--complex-project-entry-gate requires --adoption-mode existing-code-adoption" in completed.stderr


def test_node_deploy_servo_rejects_weak_doc_without_adoption_mode(tmp_path: Path) -> None:
    completed = run_node(
        "generate",
        "--deploy-path",
        str(tmp_path),
        "--weak-doc-onboarding",
    )

    assert completed.returncode != 0
    assert "--weak-doc-onboarding requires --adoption-mode existing-code-adoption" in completed.stderr


def test_node_deploy_servo_blocks_unverified_baseline_before_writes(tmp_path: Path) -> None:
    completed = run_node("generate", "--deploy-path", str(tmp_path))

    assert completed.returncode == 1
    assert "unable to resolve baseline branch" in completed.stderr
    assert not (tmp_path / ".servo").exists()
    assert not (tmp_path / ".gitignore").exists()


def test_node_deploy_servo_installs_claude_skill_without_python_helper(tmp_path: Path) -> None:
    completed = run_node(
        "install-claude-skill",
        "--deploy-path",
        str(tmp_path),
    )

    assert completed.returncode == 0, completed.stderr
    installed = (
        tmp_path
        / ".claude"
        / "skills"
        / "servo-set-harness-goal-skill"
    )
    assert (installed / "scripts" / "deploy_servo.js").is_file()
    assert not (installed / "scripts" / "deploy_aw.py").exists()
    assert not (installed / "payload.json").exists()
    assert not (installed / "aw.marker").exists()


def test_installed_skills_can_initialize_servo_when_target_has_no_servo(
    tmp_path: Path,
) -> None:
    target_repo = tmp_path / "target-repo"
    target_repo.mkdir()
    init_git_repo(target_repo)

    agents_install = run_installer(
        target_repo,
        "install",
        "--backend",
        "agents",
        "--agents-root",
        str(target_repo / ".agents" / "skills"),
    )
    assert agents_install.returncode == 0, agents_install.stderr

    claude_install = run_installer(
        target_repo,
        "install",
        "--backend",
        "claude",
        "--claude-root",
        str(target_repo / ".claude" / "skills"),
    )
    assert claude_install.returncode == 0, claude_install.stderr

    assert not (target_repo / ".servo").exists()

    agents_helper = (
        target_repo
        / ".agents"
        / "skills"
        / "servo-set-harness-goal-skill"
        / "scripts"
        / "deploy_servo.js"
    )
    agents_generate = run_installed_node(
        agents_helper,
        "generate",
        "--deploy-path",
        str(target_repo),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-05-21",
        "--adoption-mode",
        "existing-code-adoption",
    )
    assert agents_generate.returncode == 0, agents_generate.stderr
    assert (target_repo / ".servo" / "control-state.md").is_file()
    assert (target_repo / ".servo" / "repo" / "discovery-input.md").is_file()
    assert (target_repo / ".servo" / "worktrack" / "gate-evidence.md").is_file()

    for servo_path in sorted((target_repo / ".servo").rglob("*"), reverse=True):
        if servo_path.is_file():
            servo_path.unlink()
        else:
            servo_path.rmdir()
    (target_repo / ".servo").rmdir()

    claude_helper = (
        target_repo
        / ".claude"
        / "skills"
        / "set-harness-goal-skill"
        / "scripts"
        / "deploy_servo.js"
    )
    claude_generate = run_installed_node(
        claude_helper,
        "generate",
        "--deploy-path",
        str(target_repo),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-05-21",
    )
    assert claude_generate.returncode == 0, claude_generate.stderr
    assert (target_repo / ".servo" / "control-state.md").is_file()
    assert (target_repo / ".servo" / "goal-charter.md").is_file()
    assert (target_repo / ".servo" / "repo" / "analysis.md").is_file()
    assert (target_repo / ".servo" / "worktrack" / "plan-task-queue.md").is_file()


def test_set_harness_goal_payload_descriptors_use_node_helper() -> None:
    for payload_path in (AGENTS_PAYLOAD, CLAUDE_PAYLOAD):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        assert (
            "product/harness/skills/set-harness-goal-skill/scripts/deploy_servo.js"
            in payload["canonical_paths"]
        )
        assert "scripts/deploy_servo.js" in payload["required_payload_files"]
        assert (
            "product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.py"
            not in payload["canonical_paths"]
        )
        assert "scripts/deploy_aw.py" not in payload["required_payload_files"]
