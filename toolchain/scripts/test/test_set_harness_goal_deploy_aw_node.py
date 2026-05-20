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
    / "deploy_aw.js"
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


def test_node_deploy_aw_validates_skill_assets() -> None:
    completed = run_node("validate")

    assert completed.returncode == 0, completed.stderr
    assert "[goal-charter] ok:" in completed.stdout
    assert "deploy_aw.py" not in completed.stdout


def test_node_deploy_aw_generates_existing_code_adoption_profile(tmp_path: Path) -> None:
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
    assert (tmp_path / ".aw" / "control-state.md").is_file()
    assert (tmp_path / ".aw" / "repo" / "discovery-input.md").is_file()
    assert (tmp_path / ".aw" / "template" / "goal-charter.template.md").is_file()
    discovery = (tmp_path / ".aw" / "repo" / "discovery-input.md").read_text(
        encoding="utf-8"
    )
    assert "adoption_mode: existing-code-adoption" in discovery
    assert "baseline_branch: main" in discovery
    control_state = (tmp_path / ".aw" / "control-state.md").read_text(
        encoding="utf-8"
    )
    assert "- repo_scope: active" in control_state
    assert "- worktrack_scope: closed" in control_state
    assert "- latest_observed_checkpoint:" in control_state
    assert "- last_doc_catch_up_checkpoint:" in control_state


def test_node_deploy_aw_blocks_unverified_baseline_before_writes(tmp_path: Path) -> None:
    completed = run_node("generate", "--deploy-path", str(tmp_path))

    assert completed.returncode == 1
    assert "unable to resolve baseline branch" in completed.stderr
    assert not (tmp_path / ".aw").exists()


def test_node_deploy_aw_installs_claude_skill_without_python_helper(tmp_path: Path) -> None:
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
        / "aw-set-harness-goal-skill"
    )
    assert (installed / "scripts" / "deploy_aw.js").is_file()
    assert not (installed / "scripts" / "deploy_aw.py").exists()
    assert not (installed / "payload.json").exists()
    assert not (installed / "aw.marker").exists()


def test_set_harness_goal_payload_descriptors_use_node_helper() -> None:
    for payload_path in (AGENTS_PAYLOAD, CLAUDE_PAYLOAD):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        assert (
            "product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.js"
            in payload["canonical_paths"]
        )
        assert "scripts/deploy_aw.js" in payload["required_payload_files"]
        assert (
            "product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.py"
            not in payload["canonical_paths"]
        )
        assert "scripts/deploy_aw.py" not in payload["required_payload_files"]
