from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import closeout_acceptance_gate
from scope_gate_check import ChangedFile, check_scope, normalize_status_path
from gate_status_backfill import DEFAULT_CLOSEOUT_ROOT, DEFAULT_STATE_FILE, update_state


def test_closeout_gate_does_not_require_python_deploy_reference_entrypoints() -> None:
    assert not hasattr(closeout_acceptance_gate, "SUPPORTED_DEPLOY_VERIFY_BACKENDS")
    assert not hasattr(closeout_acceptance_gate, "DEPLOY_VERIFY_ENTRYPOINTS")


def test_gate_status_backfill_defaults_to_tmp_runtime_root() -> None:
    assert DEFAULT_STATE_FILE.is_absolute()
    assert DEFAULT_CLOSEOUT_ROOT.is_absolute()
    assert ".autoworkflow" not in DEFAULT_STATE_FILE.parts
    assert ".autoworkflow" not in DEFAULT_CLOSEOUT_ROOT.parts
    assert "servo-closeout" in DEFAULT_STATE_FILE.parts
    assert "servo-closeout" in DEFAULT_CLOSEOUT_ROOT.parts


def test_claude_required_payload_skills_are_discovered_from_payload_descriptors() -> None:
    skills_root = (
        closeout_acceptance_gate.REPO_ROOT
        / "product"
        / "harness"
        / "adapters"
        / "claude"
        / "skills"
    )
    expected = tuple(sorted(path.parent.name for path in skills_root.glob("*/payload.json")))

    assert closeout_acceptance_gate.CLAUDE_REQUIRED_PAYLOAD_SKILLS == expected


def test_npm_pack_tarball_result_script_resolves_single_pack_result(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    pack_json = tmp_path / "pack.json"
    pack_json.write_text(
        json.dumps([{"filename": "servo-installer-0.0.0.tgz"}]),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parent / "npm_pack_tarball_result.js"

    completed = subprocess.run(
        ["node", str(script), str(pack_json), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == f"{tmp_path / 'servo-installer-0.0.0.tgz'}\n"


def test_successful_npm_command_result_fails_unknown_npm_commands() -> None:
    result = successful_npm_command_result(["npm", "exec", "--", "servo-installer", "unknown"])

    assert result is not None
    assert result["passed"] is False
    assert "unrecognized npm command" in result["stderr"]


NPM_HELP_STDOUT = (
    "usage: servo-installer [tui|<deploy-mode>] [options]\n"
    "Node.js distribution\n"
    "tui\n"
    "diagnose --backend agents|claude\n"
    "verify --backend agents|claude\n"
    "install --backend agents|claude\n"
    "update --backend agents|claude\n"
    "prune --all --backend agents|claude\n"
    "check_paths_exist --backend agents|claude\n"
)
NPM_VERSION = json.loads((closeout_acceptance_gate.REPO_ROOT / "package.json").read_text(encoding="utf-8"))[
    "version"
]
NPM_VERSION_STDOUT = f"servo-installer {NPM_VERSION}\n"
CLAUDE_SKILL_DIR_NAMES = closeout_acceptance_gate.CLAUDE_REQUIRED_PAYLOAD_SKILLS
CLAUDE_TARGET_DIR_BY_SKILL = {
    "set-harness-goal-skill": "servo-set-harness-goal-skill",
}


def write_root_package_json(repo_root: Path, version: str = NPM_VERSION) -> None:
    (repo_root / "package.json").write_text(
        json.dumps({"name": "servo-installer", "version": version}),
        encoding="utf-8",
    )


def write_deploy_package_json(repo_root: Path, version: str = NPM_VERSION) -> None:
    package_path = repo_root / "toolchain" / "scripts" / "deploy" / "package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps({"name": "servo-installer", "version": version}),
        encoding="utf-8",
    )


def npm_pack_stdout(paths: set[str] | None = None, filename: str = f"servo-installer-{NPM_VERSION}.tgz") -> str:
    if paths is None:
        paths = closeout_acceptance_gate.EXPECTED_NPM_PACKAGE_FILES
    return json.dumps(
        [
            {
                "filename": filename,
                "files": [{"path": path} for path in sorted(paths)],
            }
        ]
    )


def successful_npm_command_result(
    command: list[str],
    extra_env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> dict | None:
    def npm_exec_backend() -> str:
        if "--backend" in command:
            return command[command.index("--backend") + 1]
        return "agents"

    def npm_exec_target_root(backend: str | None = None) -> Path:
        current_backend = backend or npm_exec_backend()
        target_repo = (
            extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
            if extra_env is not None
            else None
        )
        repo = Path(target_repo) if target_repo else cwd or Path("/tmp/repo")
        if current_backend == "claude":
            return repo / ".claude" / "skills"
        return repo / ".agents" / "skills"

    def npm_exec_skill_dirs(backend: str | None = None) -> list[Path]:
        current_backend = backend or npm_exec_backend()
        if current_backend == "bundle":
            return [
                *npm_exec_skill_dirs("agents"),
                *npm_exec_skill_dirs("claude"),
            ]
        if current_backend == "claude":
            return [
                npm_exec_target_root("claude") / CLAUDE_TARGET_DIR_BY_SKILL.get(skill_name, skill_name)
                for skill_name in CLAUDE_SKILL_DIR_NAMES
            ]
        return [npm_exec_target_root("agents") / "servo-harness-skill"]

    if command[:4] == ["npm", "pack", "--dry-run", "--json"]:
        packed_paths = (
            closeout_acceptance_gate.EXPECTED_NPM_PACKAGE_FILES
            if cwd is not None and cwd.as_posix().endswith("toolchain/scripts/deploy")
            else closeout_acceptance_gate.ROOT_NPM_REQUIRED_PACKAGE_FILES
        )
        return {
            "command": command,
            "returncode": 0,
            "stdout": npm_pack_stdout(packed_paths),
            "stderr": "",
            "passed": True,
        }
    if command == ["npm", "run", "publish:dry-run", "--silent"]:
        return {
            "command": command,
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "name": "servo-installer",
                    "version": NPM_VERSION,
                    "filename": f"servo-installer-{NPM_VERSION}.tgz",
                    "files": [
                        {"path": path}
                        for path in sorted(closeout_acceptance_gate.ROOT_NPM_REQUIRED_PACKAGE_FILES)
                    ],
                }
            ),
            "stderr": "",
            "passed": True,
        }
    if command in (
        ["npm", "--prefix", "toolchain/scripts/deploy", "test", "--silent"],
        ["npm", "--prefix", "toolchain/scripts/deploy", "run", "smoke", "--silent"],
    ):
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }
    if command[:3] == ["npm", "pack", "--json"] and "--pack-destination" in command:
        package_dir = Path(command[command.index("--pack-destination") + 1])
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / f"servo-installer-{NPM_VERSION}.tgz").write_text("fake package", encoding="utf-8")
        packed_paths = (
            closeout_acceptance_gate.EXPECTED_NPM_PACKAGE_FILES
            if cwd is not None and cwd.as_posix().endswith("toolchain/scripts/deploy")
            else closeout_acceptance_gate.ROOT_NPM_REQUIRED_PACKAGE_FILES
        )
        return {
            "command": command,
            "returncode": 0,
            "stdout": npm_pack_stdout(packed_paths),
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "diagnose" in command:
        if extra_env is None or "SERVO_HARNESS_REPO_ROOT" not in extra_env:
            return {
                "command": command,
                "returncode": 1,
                "stdout": "",
                "stderr": "missing SERVO_HARNESS_REPO_ROOT",
                "passed": False,
            }
        if npm_exec_backend() == "bundle":
            return {
                "command": command,
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "bundle": True,
                        "backends": {
                            "agents": {
                                "backend": "agents",
                                "binding_count": len(npm_exec_skill_dirs("agents")),
                                "source_root": extra_env.get("SERVO_HARNESS_REPO_ROOT") or "/tmp/package-source",
                                "target_root": str(npm_exec_target_root("agents")),
                                "issue_count": 0,
                            },
                            "claude": {
                                "backend": "claude",
                                "binding_count": len(npm_exec_skill_dirs("claude")),
                                "source_root": extra_env.get("SERVO_HARNESS_REPO_ROOT") or "/tmp/package-source",
                                "target_root": str(npm_exec_target_root("claude")),
                                "issue_count": 0,
                            },
                        },
                        "total_issues": 0,
                        "total_managed": len(npm_exec_skill_dirs("bundle")),
                    }
                ),
                "stderr": "",
                "passed": True,
            }
        return {
            "command": command,
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "backend": npm_exec_backend(),
                    "binding_count": len(npm_exec_skill_dirs()),
                    "source_root": extra_env.get("SERVO_HARNESS_REPO_ROOT") or "/tmp/package-source",
                    "target_root": str(npm_exec_target_root()),
                }
            ),
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "update" in command and command[-1] == "--yes":
        backend = npm_exec_backend()
        targets = npm_exec_skill_dirs()
        for target in targets:
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text("# harness\n", encoding="utf-8")
        return {
            "command": command,
            "returncode": 0,
            "stdout": (
                f"[{backend}] applying update\n"
                + "".join(f"installed skill {target.name.removeprefix('aw-')}\n" for target in targets)
                + f"[{backend}] ok: target root is ready\n"
                + f"[{backend}] update complete\n"
            ),
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "tui" in command:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": "servo-installer tui requires an interactive terminal.\n",
            "passed": False,
        }
    if command[:2] == ["npm", "exec"] and "update" in command:
        if extra_env is None or "SERVO_HARNESS_REPO_ROOT" not in extra_env:
            return {
                "command": command,
                "returncode": 1,
                "stdout": "",
                "stderr": "missing SERVO_HARNESS_REPO_ROOT",
                "passed": False,
            }
        return {
            "command": command,
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "backend": npm_exec_backend(),
                    "source_root": extra_env.get("SERVO_HARNESS_REPO_ROOT") or "/tmp/package-source",
                    "target_root": str(npm_exec_target_root()),
                    "blocking_issue_count": 0,
                    "planned_target_paths": [str(target) for target in npm_exec_skill_dirs()],
                }
            ),
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "install" in command:
        targets = npm_exec_skill_dirs()
        for target in targets:
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text("# harness\n", encoding="utf-8")
        return {
            "command": command,
            "returncode": 0,
            "stdout": "".join(f"installed skill {target.name.removeprefix('aw-')}\n" for target in targets),
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "verify" in command:
        backend = npm_exec_backend()
        if backend == "bundle":
            return {
                "command": command,
                "returncode": 0,
                "stdout": "[agents] ok: target root is ready\n[claude] ok: target root is ready\n",
                "stderr": "",
                "passed": True,
            }
        return {
            "command": command,
            "returncode": 0,
            "stdout": f"[{backend}] ok: target root is ready\n",
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "--version" in command:
        return {
            "command": command,
            "returncode": 0,
            "stdout": NPM_VERSION_STDOUT,
            "stderr": "",
            "passed": True,
        }
    if command[:2] == ["npm", "exec"] and "--help" in command:
        return {
            "command": command,
            "returncode": 0,
            "stdout": NPM_HELP_STDOUT,
            "stderr": "",
            "passed": True,
        }
    if command[:1] == ["npm"]:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": f"unrecognized npm command in closeout gate test mock: {command}",
            "passed": False,
        }
    return None


def test_check_scope_accepts_allowed_prefixes() -> None:
    result = check_scope(
        [
            "AGENTS.md",
            "INDEX.md",
            "CONTRIBUTING.md",
            ".codex/config.toml",
            ".github/workflows/ci.yml",
            "docs/README.md",
            "docs/book.md",
            "docs/harness/README.md",
            "docs/project-maintenance/README.md",
            "product/README.md",
            "product/harness/README.md",
            "docs/project-maintenance/governance/review-verify-handbook.md",
            "docs/project-maintenance/governance/path-governance-checks.md",
            "docs/servo-installer/reference/existing-code-adoption.md",
            ".autoworkflow/closeout/demo/summary.json",
            "package.json",
            "product/.servo_template/control-state.md",
            "product/harness/skills/harness-skill/SKILL.md",
            "product/harness/adapters/agents/skills/harness-skill/payload.json",
            ".agents/skills/legacy-skill/SKILL.md",
            "toolchain/scripts/deploy/bin/servo-installer.js",
            "toolchain/scripts/deploy/package.json",
            "toolchain/scripts/deploy/path_safety_policy.json",
            "toolchain/scripts/deploy/README.md",
            "toolchain/scripts/deploy/test_servo_installer.js",
            "toolchain/scripts/test/scope_gate_check.py",
            "tools/scope_gate_check.py",
        ],
        (
            "AGENTS.md",
            "INDEX.md",
            "CONTRIBUTING.md",
            ".codex/",
            ".github/",
            "docs/README.md",
            "docs/book.md",
            ".autoworkflow/closeout/",
            "package.json",
            "docs/project-maintenance/",
            "docs/harness/",
            "docs/servo-installer/",
            "product/README.md",
            "product/harness/README.md",
            "product/.servo_template/",
            "product/harness/skills/",
            "product/harness/adapters/",
            ".agents/",
            "toolchain/scripts/deploy/bin/",
            "toolchain/scripts/deploy/package.json",
            "toolchain/scripts/deploy/path_safety_policy.json",
            "toolchain/scripts/deploy/README.md",
            "toolchain/scripts/deploy/test_servo_installer.js",
            "toolchain/scripts/test/",
            "tools/scope_gate_check.py",
        ),
    )
    assert result.passed is True
    assert result.violations == []


def test_check_scope_accepts_closeout_prefix() -> None:
    result = check_scope(
        ["docs/project-maintenance/governance/review-verify-handbook.md"],
        ("docs/project-maintenance/governance/",),
    )
    assert result.passed is True
    assert result.violations == []


def test_check_scope_file_allowance_is_exact() -> None:
    result = check_scope(
        ["docs/book.md", "docs/book.md.bak", "docs/book.md/extra.md"],
        ("docs/book.md",),
    )

    assert result.passed is False
    assert result.violations == ["docs/book.md.bak", "docs/book.md/extra.md"]


def test_check_scope_flags_disallowed_changes() -> None:
    result = check_scope(["GUIDE.md"], ("docs/project-maintenance/",))
    assert result.passed is False
    assert result.violations == ["GUIDE.md"]


def test_check_scope_allows_runtime_layer_untracking_only() -> None:
    result = check_scope(
        [
            ChangedFile(".servo/control-state.md", "D "),
            ChangedFile(".agents/skills/example/SKILL.md", " D"),
            ChangedFile(".claude/skills/example/SKILL.md", "D "),
        ],
        ("docs/project-maintenance/",),
    )

    assert result.passed is True
    assert result.violations == []


def test_check_scope_blocks_runtime_layer_modification() -> None:
    result = check_scope(
        [
            ChangedFile(".servo/control-state.md", " M"),
            ChangedFile(".agents/skills/example/SKILL.md", "A "),
        ],
        ("docs/project-maintenance/",),
    )

    assert result.passed is False
    assert result.violations == [
        ".servo/control-state.md",
        ".agents/skills/example/SKILL.md",
    ]


def test_normalize_status_path_decodes_git_quoted_utf8_path() -> None:
    quoted = '"docs/harness/foundations/Harness\\350\\277\\220\\350\\241\\214\\345\\215\\217\\350\\256\\256.md"'

    assert normalize_status_path(quoted) == "docs/harness/foundations/Harness运行协议.md"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_pre_push_blocks_origin_head_baseline(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    hook_path = repo_root / "toolchain" / "scripts" / "git-hooks" / "pre-push"
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/master",
        ],
        cwd=tmp_path,
        check=True,
    )

    completed = subprocess.run(
        ["bash", str(hook_path)],
        cwd=tmp_path,
        input=(
            "refs/heads/master 0000000000000000000000000000000000000000 "
            "refs/heads/master 0000000000000000000000000000000000000000\n"
        ),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "direct push to protected baseline 'master' is blocked" in completed.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_pre_push_allows_non_baseline_branch(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    hook_path = repo_root / "toolchain" / "scripts" / "git-hooks" / "pre-push"
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/master",
        ],
        cwd=tmp_path,
        check=True,
    )

    completed = subprocess.run(
        ["bash", str(hook_path)],
        cwd=tmp_path,
        input=(
            "refs/heads/work/test 0000000000000000000000000000000000000000 "
            "refs/heads/work/test 0000000000000000000000000000000000000000\n"
        ),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_pre_push_fallback_blocks_main_when_origin_head_unresolved(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    hook_path = repo_root / "toolchain" / "scripts" / "git-hooks" / "pre-push"
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    completed = subprocess.run(
        ["bash", str(hook_path)],
        cwd=tmp_path,
        input=(
            "refs/heads/main 0000000000000000000000000000000000000000 "
            "refs/heads/main 0000000000000000000000000000000000000000\n"
        ),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "fallback protects main/master" in completed.stderr


def test_update_state_backfills_gate_status() -> None:
    state = {"gates": {"scope_gate": "pending"}}
    updated = update_state(state, "scope_gate", "passed", {"returncode": 0}, "workflow-1")
    assert updated["workflow_id"] == "workflow-1"
    assert updated["gates"]["scope_gate"] == "passed"
    assert updated["last_backfill"]["gate"] == "scope_gate"


def test_update_state_allows_skipped_gate_status() -> None:
    state = {"gates": {"scope_gate": "pending"}}
    updated = update_state(
        state,
        "test_gate",
        "skipped",
        {"returncode": 0, "skip_reasons": ["missing local deploy target root"]},
        "workflow-1",
    )
    assert updated["gates"]["test_gate"] == "skipped"
    assert updated["last_backfill"]["status"] == "skipped"


def test_update_state_replaces_cross_workflow_state() -> None:
    state = {
        "workflow_id": "workflow-1",
        "gates": {"scope_gate": "passed"},
        "status": "completed",
    }
    updated = update_state(state, "spec_gate", "failed", {"returncode": 1}, "workflow-2")
    assert updated["workflow_id"] == "workflow-2"
    assert updated["gates"] == {"spec_gate": "failed"}
    assert "status" not in updated


def test_root_tool_shims_dispatch() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    commands = [
        [sys.executable, "tools/scope_gate_check.py", "--help"],
        [sys.executable, "tools/gate_status_backfill.py", "--help"],
        [sys.executable, "tools/closeout_acceptance_gate.py", "--help"],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True)
        assert completed.returncode == 0


def test_run_scope_gate_allows_foundations_governance_docs(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        captured["command"] = command
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_scope_gate(tmp_path, sys.executable)

    assert result["passed"] is True
    command = captured["command"]
    assert "README.md" in command
    assert "AGENTS.md" in command
    assert "CONTRIBUTING.md" in command
    assert ".gitignore" in command
    assert "docs/README.md" in command
    assert "docs/book.md" in command
    assert ".codex/" in command
    assert ".github/" in command
    assert "docs/project-maintenance/README.md" in command
    assert "docs/harness/" in command
    assert "product/README.md" in command
    assert "product/harness/README.md" in command
    assert "docs/project-maintenance/foundations/root-directory-layering.md" in command
    assert "toolchain/toolchain-layering.md" in command
    assert "docs/project-maintenance/governance/review-verify-handbook.md" in command


def test_run_spec_gate_includes_folder_logic(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        commands.append(command)
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_spec_gate(tmp_path, sys.executable)

    assert result["passed"] is True
    assert [item["name"] for item in result["subchecks"]] == [
        "folder_logic",
        "path_governance",
        "governance_semantic",
    ]
    assert any(command[-2:] == ["--repo-root", str(tmp_path)] for command in commands)
    assert any("folder_logic_check.py" in command[1] for command in commands)
    assert any("docs/harness" in command for command in commands)


def test_run_command_disables_python_bytecode(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_run)

    result = closeout_acceptance_gate.run_command([sys.executable, "--version"], cwd=tmp_path)

    assert result["passed"] is True
    assert captured["env"]["PYTHONDONTWRITEBYTECODE"] == "1"


def test_run_static_gate_uses_in_memory_syntax_check(tmp_path) -> None:
    scripts_root = tmp_path / "toolchain" / "scripts" / "test"
    scripts_root.mkdir(parents=True)
    (scripts_root / "ok.py").write_text("value = 1\n", encoding="utf-8")

    result = closeout_acceptance_gate.run_static_gate(tmp_path, sys.executable)

    assert result["passed"] is True
    assert result["command"] == ["python-syntax-check", "toolchain/scripts/test"]
    assert not list(tmp_path.rglob("__pycache__"))
    assert not list(tmp_path.rglob("*.pyc"))


def test_run_static_gate_reports_syntax_errors(tmp_path) -> None:
    scripts_root = tmp_path / "toolchain" / "scripts" / "test"
    scripts_root.mkdir(parents=True)
    (scripts_root / "bad.py").write_text("def broken(:\n", encoding="utf-8")

    result = closeout_acceptance_gate.run_static_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    assert result["returncode"] == 1
    assert "toolchain/scripts/test/bad.py" in result["stderr"]


def test_run_cache_gate_rejects_runtime_cache_under_controlled_roots(tmp_path) -> None:
    cache_dir = tmp_path / "toolchain" / "scripts" / ".pytest_cache"
    cache_dir.mkdir(parents=True)
    (tmp_path / "product" / "demo" / "__pycache__").mkdir(parents=True)
    (tmp_path / "tools" / "__pycache__").mkdir(parents=True)
    (tmp_path / "docs" / "demo.pyc").parent.mkdir(parents=True)
    (tmp_path / "docs" / "demo.pyc").write_text("cache\n", encoding="utf-8")
    (tmp_path / "product" / "demo.pyo").write_text("cache\n", encoding="utf-8")

    result = closeout_acceptance_gate.run_cache_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    assert "toolchain/scripts/.pytest_cache" in result["stderr"]
    assert "product/demo/__pycache__" in result["stderr"]
    assert "tools/__pycache__" in result["stderr"]
    assert "docs/demo.pyc" in result["stderr"]
    assert "product/demo.pyo" in result["stderr"]


def test_run_cache_gate_allows_root_pytest_cache(tmp_path) -> None:
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / "toolchain").mkdir()

    result = closeout_acceptance_gate.run_cache_gate(tmp_path, sys.executable)

    assert result["passed"] is True
    assert result["stderr"] == ""


def test_run_test_gate_includes_contract_tests(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path)
    calls: list[tuple[list[str], Path, dict[str, str] | None]] = []

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        calls.append((command, cwd, extra_env))
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)
    commands = [command for command, _, _ in calls]
    root_tarball_smoke = next(
        item for item in result["subchecks"] if item["name"] == "root_npm_tarball_smoke_servo_installer"
    )

    assert result["passed"] is True
    assert any(
        item["name"] == "root_npm_exec_tarball_update_apply_claude"
        for item in root_tarball_smoke["subchecks"]
    )
    assert any(
        item["name"] == "root_npm_exec_tarball_diagnose_bundle"
        for item in root_tarball_smoke["subchecks"]
    )
    assert any(
        item["name"] == "root_npm_exec_tarball_verify_bundle"
        for item in root_tarball_smoke["subchecks"]
    )
    assert [item["name"] for item in result["subchecks"][:13]] == [
        "root_package_version_metadata",
        "gate_tool_tests",
        "folder_logic_tests",
        "path_governance_tests",
        "governance_semantic_tests",
        "complexity_signal_scanner_tests",
        "set_harness_goal_e2e_fixture_tests",
        "agents_adapter_contract_tests",
        "servo_installer_cli_tests",
        "servo_installer_tui_tests",
        "deploy_package_unit_tests",
        "repo_analysis_contract_check",
        "npm_pack_dry_run_servo_installer",
    ]
    assert any(command[-1] == "toolchain/scripts/test/test_folder_logic_check.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/test_path_governance_check.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/test_governance_semantic_check.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/test_complexity_signal_scanner.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/test_set_harness_goal_e2e_fixture.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/test_agents_adapter_contract.py" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/servo_installer_cli" for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/servo_installer_tui" for command in commands)
    assert not any(command[:4] == [sys.executable, "-m", "unittest", "discover"] for command in commands)
    assert any(command == ["npm", "--prefix", "toolchain/scripts/deploy", "test", "--silent"] for command in commands)
    assert any(command[-1] == "toolchain/scripts/test/repo_analysis_contract_check.py" for command in commands)
    assert any(
        command == ["npm", "pack", "--dry-run", "--json"]
        and cwd == tmp_path / "toolchain" / "scripts" / "deploy"
        for command, cwd, _ in calls
    )
    assert any(
        command[:3] == ["npm", "pack", "--json"]
        and cwd == tmp_path / "toolchain" / "scripts" / "deploy"
        for command, cwd, _ in calls
    )
    assert any(command[:2] == ["npm", "exec"] for command in commands)
    assert any(
        command[:2] == ["npm", "exec"]
        and "diagnose" in command
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and "update" in command
        and "--json" in command
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-1] == "tui"
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-3:] == ["install", "--backend", "agents"]
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-3:] == ["verify", "--backend", "agents"]
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-4:] == ["update", "--backend", "agents", "--yes"]
        and extra_env is not None
        and extra_env.get("SERVO_HARNESS_REPO_ROOT") == str(tmp_path)
        and extra_env.get("SERVO_HARNESS_TARGET_REPO_ROOT")
        and "fake-python-bin" in extra_env.get("PATH", "")
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-4:] == ["update", "--backend", "claude", "--yes"]
        and extra_env == {"SERVO_HARNESS_REPO_ROOT": "", "SERVO_HARNESS_TARGET_REPO_ROOT": ""}
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-4:] == ["diagnose", "--backend", "bundle", "--json"]
        and extra_env == {"SERVO_HARNESS_REPO_ROOT": "", "SERVO_HARNESS_TARGET_REPO_ROOT": ""}
        for command, _, extra_env in calls
    )
    assert any(
        command[:2] == ["npm", "exec"]
        and command[-3:] == ["verify", "--backend", "bundle"]
        and extra_env == {"SERVO_HARNESS_REPO_ROOT": "", "SERVO_HARNESS_TARGET_REPO_ROOT": ""}
        for command, _, extra_env in calls
    )
    assert not any("adapter_deploy.py" in command[1] for command in commands if len(command) > 1)
    assert not any("harness_deploy.py" in command[1] for command in commands if len(command) > 1)


def test_run_test_gate_no_longer_runs_local_python_deploy_verify(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path)
    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        commands.append(command)
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        if "adapter_deploy.py" in command[1] or "harness_deploy.py" in command[1]:
            return {
                "command": command,
                "returncode": 1,
                "stdout": (
                    "[agents] drift: 1 issue(s) in local target at /tmp/demo\n"
                    "  - missing-target-root: /tmp/demo (.agents target root does not exist)\n"
                ),
                "stderr": "",
                "passed": False,
            }
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is True
    assert result["status"] == "passed"
    assert not any(item["name"].startswith("deploy_verify_") for item in result["subchecks"])
    assert not any("adapter_deploy.py" in command[1] for command in commands if len(command) > 1)
    assert not any("harness_deploy.py" in command[1] for command in commands if len(command) > 1)


def test_run_test_gate_fails_on_unexpected_npm_packlist(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path)
    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        if command[:4] == ["npm", "pack", "--dry-run", "--json"]:
            return {
                "command": command,
                "returncode": 0,
                "stdout": npm_pack_stdout({"README.md", "adapter_deploy.py"}),
                "stderr": "",
                "passed": True,
            }
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    assert result["status"] == "failed"
    pack_result = next(
        item for item in result["subchecks"] if item["name"] == "npm_pack_dry_run_servo_installer"
    )
    assert pack_result["passed"] is False
    assert "unexpected npm package files" in pack_result["stderr"]


def test_root_npm_package_packlist_rejects_forbidden_python_payload(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path)
    packed_paths = set(closeout_acceptance_gate.ROOT_NPM_REQUIRED_PACKAGE_FILES)
    packed_paths.add("product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.py")

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        assert command == ["npm", "pack", "--dry-run", "--json"]
        return {
            "command": command,
            "returncode": 0,
            "stdout": npm_pack_stdout(packed_paths),
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_root_npm_package_packlist(tmp_path)

    assert result["passed"] is False
    assert "root npm package included forbidden files" in result["stderr"]


def test_run_test_gate_fails_on_mismatched_tarball_version(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path, version=NPM_VERSION)

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        if command[:2] == ["npm", "exec"] and "--version" in command:
            return {
                "command": command,
                "returncode": 0,
                "stdout": f"servo-installer {NPM_VERSION}0\n",
                "stderr": "",
                "passed": True,
            }
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    assert result["status"] == "failed"
    tarball_results = [
        item
        for item in result["subchecks"]
        if item["name"] in {"npm_tarball_smoke_servo_installer", "root_npm_tarball_smoke_servo_installer"}
    ]
    assert tarball_results
    assert all(item["passed"] is False for item in tarball_results)
    assert all("version probe omitted package version" in item["stderr"] for item in tarball_results)


def test_run_test_gate_fails_on_invalid_root_package_json(monkeypatch, tmp_path) -> None:
    (tmp_path / "package.json").write_text("{not-json", encoding="utf-8")

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    version_result = result["subchecks"][0]
    assert version_result["name"] == "root_package_version_metadata"
    assert version_result["passed"] is False
    assert "invalid root package.json version metadata" in version_result["stderr"]


def test_run_test_gate_fails_on_mismatched_deploy_package_version(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path, version=NPM_VERSION)
    write_deploy_package_json(tmp_path, version=f"{NPM_VERSION}.mismatch")

    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    version_result = result["subchecks"][0]
    assert version_result["name"] == "root_package_version_metadata"
    assert version_result["passed"] is False
    assert "root package.json version must match toolchain/scripts/deploy/package.json" in version_result["stderr"]


def test_run_test_gate_fails_on_npm_tarball_exec_failure(monkeypatch, tmp_path) -> None:
    write_root_package_json(tmp_path)
    def fake_run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
        if command[:2] == ["npm", "exec"]:
            return {
                "command": command,
                "returncode": 1,
                "stdout": "",
                "stderr": "bin failed",
                "passed": False,
            }
        npm_result = successful_npm_command_result(command, extra_env, cwd)
        if npm_result is not None:
            return npm_result
        return {
            "command": command,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "passed": True,
        }

    monkeypatch.setattr(closeout_acceptance_gate, "run_command", fake_run_command)

    result = closeout_acceptance_gate.run_test_gate(tmp_path, sys.executable)

    assert result["passed"] is False
    assert result["status"] == "failed"
    tarball_result = next(
        item for item in result["subchecks"] if item["name"] == "npm_tarball_smoke_servo_installer"
    )
    assert tarball_result["passed"] is False
    exec_result = next(item for item in tarball_result["subchecks"] if item["name"] == "npm_exec_tarball")
    assert exec_result["stderr"] == "bin failed"


def test_closeout_gate_fails_closed_on_test_gate_failure(monkeypatch, tmp_path, capsys) -> None:
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        return {
            "passed": gate != "test_gate",
            "returncode": 0 if gate != "test_gate" else 1,
        }

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert [result["gate"] for result in payload["results"]] == [
        "scope_gate",
        "spec_gate",
        "static_gate",
        "cache_gate",
        "test_gate",
    ]


def test_run_smoke_gate_skips_missing_runtime_root(monkeypatch, tmp_path) -> None:
    primary_root = tmp_path / "primary"
    runtime_dir = (
        primary_root
        / ".autoworkflow"
        / "closeout"
        / "manual-governance-loop-3round-r000001-m000642"
    )
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "runtime.json").write_text('{"active_round": null}', encoding="utf-8")
    other_runtime_dir = (
        primary_root
        / ".autoworkflow"
        / "closeout"
        / "manual-governance-loop-6-3-3-r000001-m046830"
    )
    other_runtime_dir.mkdir(parents=True)
    (other_runtime_dir / "runtime.json").write_text('{"active_round": null}', encoding="utf-8")
    monkeypatch.setattr(closeout_acceptance_gate, "find_primary_worktree_root", lambda repo_root: primary_root)
    monkeypatch.setattr(
        closeout_acceptance_gate,
        "run_command",
        lambda command, cwd: {
            "command": command,
            "returncode": 0,
            "stdout": "{}",
            "stderr": "",
            "passed": True,
        },
    )

    result = closeout_acceptance_gate.run_smoke_gate(tmp_path, sys.executable, "workflow-1")
    assert result["passed"] is True
    assert result["status"] == "passed"
    assert result["backfill_smoke"]["passed"] is True
    assert len(result["runtime_checks"]) == 2
    assert all(check["passed"] is True for check in result["runtime_checks"])
    assert all(check["checked_from"] == str(primary_root) for check in result["runtime_checks"])


def test_run_smoke_gate_fails_when_runtime_root_exists_but_retained_files_are_missing(monkeypatch, tmp_path) -> None:
    (
        tmp_path
        / ".autoworkflow"
        / "closeout"
        / "manual-governance-loop-3round-r000001-m000642"
    ).mkdir(parents=True)
    monkeypatch.setattr(
        closeout_acceptance_gate,
        "run_command",
        lambda command, cwd: {
            "command": command,
            "returncode": 0,
            "stdout": "{}",
            "stderr": "",
            "passed": True,
        },
    )

    result = closeout_acceptance_gate.run_smoke_gate(tmp_path, sys.executable, "workflow-1")
    assert result["passed"] is False
    assert result["backfill_smoke"]["passed"] is True
    assert len(result["runtime_checks"]) == 2
    assert all(check["passed"] is False for check in result["runtime_checks"])
    assert all(check["missing"] is True for check in result["runtime_checks"])


def test_run_smoke_gate_skips_when_only_unrelated_runtime_artifacts_exist(monkeypatch, tmp_path) -> None:
    primary_root = tmp_path / "primary"
    (primary_root / ".autoworkflow" / "closeout" / "some-other-run").mkdir(parents=True)
    monkeypatch.setattr(closeout_acceptance_gate, "find_primary_worktree_root", lambda repo_root: primary_root)
    monkeypatch.setattr(
        closeout_acceptance_gate,
        "run_command",
        lambda command, cwd: {
            "command": command,
            "returncode": 0,
            "stdout": "{}",
            "stderr": "",
            "passed": True,
        },
    )

    result = closeout_acceptance_gate.run_smoke_gate(tmp_path, sys.executable, "workflow-1")
    assert result["passed"] is True
    assert result["status"] == "skipped"
    assert len(result["runtime_checks"]) == 1
    assert result["runtime_checks"][0]["skipped"] is True


def test_closeout_gate_backfills_skipped_status(monkeypatch, tmp_path, capsys) -> None:
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True

    backfill_commands: list[list[str]] = []

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        if gate == "scope_gate":
            return {"passed": True, "returncode": 0}
        if gate == "spec_gate":
            return {"passed": True, "returncode": 0}
        if gate == "static_gate":
            return {"passed": True, "returncode": 0}
        if gate == "test_gate":
            return {
                "passed": True,
                "returncode": 0,
                "status": "skipped",
                "subchecks": [
                    {
                        "name": "deploy_verify_agents",
                        "passed": True,
                        "skipped": True,
                        "skip_reason": "missing local deploy target root /tmp/demo",
                    }
                ],
            }
        return {"passed": True, "returncode": 0}

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        command = args[0]
        backfill_commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    test_gate_backfill = next(command for command in backfill_commands if "--gate" in command and command[command.index("--gate") + 1] == "test_gate")
    assert test_gate_backfill[test_gate_backfill.index("--status") + 1] == "skipped"
    details = json.loads(test_gate_backfill[test_gate_backfill.index("--details") + 1])
    assert "skip_reasons" in details


def test_closeout_gate_backfill_subprocess_uses_bytecode_free_env(monkeypatch, tmp_path, capsys) -> None:
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True

    captured_envs: list[dict[str, str]] = []

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        return {"passed": True, "returncode": 0}

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        if "gate_status_backfill.py" in args[0][1]:
            captured_envs.append(kwargs["env"])
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 0
    json.loads(capsys.readouterr().out)
    assert captured_envs
    assert all(env["PYTHONDONTWRITEBYTECODE"] == "1" for env in captured_envs)


def test_find_primary_worktree_root_prefers_non_nested_worktree(monkeypatch, tmp_path) -> None:
    current_root = tmp_path / ".worktrees" / "topic"
    current_root.mkdir(parents=True)
    primary_root = tmp_path / "repo"
    primary_root.mkdir()

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=(
                f"worktree {primary_root}\n"
                "HEAD abcdef\n"
                "branch refs/heads/develop-main\n"
                f"worktree {current_root}\n"
                "HEAD 123456\n"
                "branch refs/heads/topic\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_run)

    assert closeout_acceptance_gate.find_primary_worktree_root(current_root.resolve()) == primary_root.resolve()


def test_main_with_profile_lightweight_runs_four_gates(monkeypatch, tmp_path, capsys) -> None:
    """Verify --profile lightweight runs only scope/spec/static/cache gates."""
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True
        profile = "lightweight"

    gates_run: list[str] = []

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        gates_run.append(gate)
        return {"passed": True, "returncode": 0}

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 0
    assert gates_run == ["scope_gate", "spec_gate", "static_gate", "cache_gate"]

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["results"]) == 4


def test_main_with_profile_full_runs_all_six_gates(monkeypatch, tmp_path, capsys) -> None:
    """Verify --profile full runs all 6 gates (same as default)."""
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True
        profile = "full"

    gates_run: list[str] = []

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        gates_run.append(gate)
        return {"passed": True, "returncode": 0}

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 0
    assert gates_run == ["scope_gate", "spec_gate", "static_gate", "cache_gate", "test_gate", "smoke_gate"]

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["results"]) == 6


def test_main_without_profile_defaults_to_full(monkeypatch, tmp_path, capsys) -> None:
    """Verify no --profile defaults to full (6 gates, backward compat)."""
    class Args:
        repo_root = tmp_path
        workflow_id = "workflow-1"
        json = True
        # profile not set → default "full"

    gates_run: list[str] = []

    def fake_run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
        gates_run.append(gate)
        return {"passed": True, "returncode": 0}

    def fake_subprocess_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, stdout="{}", stderr="")

    monkeypatch.setattr(closeout_acceptance_gate, "parse_args", lambda: Args())
    monkeypatch.setattr(closeout_acceptance_gate, "run_gate", fake_run_gate)
    monkeypatch.setattr(closeout_acceptance_gate.subprocess, "run", fake_subprocess_run)

    assert closeout_acceptance_gate.main() == 0
    assert len(gates_run) == 6
