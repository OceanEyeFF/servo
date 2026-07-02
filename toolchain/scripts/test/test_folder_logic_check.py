from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from folder_logic_check import FolderRules, run_checks


def write_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def git(repo_root: Path, *args: str, force: bool = False) -> None:
    command = ["git", "-C", str(repo_root), *args]
    if force and "add" in args:
        command.insert(command.index("add") + 1, "-f")
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def create_nav_symlink(path: Path, target: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)


def create_valid_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path
    git(repo_root, "init")

    for root_file in ("README.md", "INDEX.md", "AGENTS.md", "CLAUDE.md", "LICENSE", ".gitignore", ".claudeignore"):
        write_file(repo_root / root_file, root_file)

    for path in (
        repo_root / "product/README.md",
        repo_root / "docs/README.md",
        repo_root / "toolchain/README.md",
    ):
        write_file(path, path.name)

    for directory in (
        ".codex/rules",
        "product/harness",
        "product/harness/skills",
        "docs/project-maintenance",
        "docs/harness",
        "toolchain/scripts",
        "tools",
    ):
        (repo_root / directory).mkdir(parents=True, exist_ok=True)

    for tool_path in (
        "tools/closeout_acceptance_gate.py",
        "tools/gate_status_backfill.py",
        "tools/scope_gate_check.py",
    ):
        write_file(repo_root / tool_path, "# shim\n")

    write_file(
        repo_root / ".codex/config.toml",
        "approval_policy = \"on-request\"\nsandbox_mode = \"workspace-write\"\npersonality = \"pragmatic\"\nmodel_reasoning_effort = \"high\"\nweb_search = \"cached\"\n\n[features]\nmulti_agent = true\n",
    )
    write_file(
        repo_root / ".codex/rules/repo.rules",
        "prefix_rule(\n    pattern = [\"git\", \"push\"],\n    decision = \"prompt\",\n    justification = \"Publishing repository changes must stay explicit in this repository.\",\n    match = [\"git push\", \"git push origin main\"],\n)\n",
    )

    (repo_root / ".nav").mkdir(parents=True, exist_ok=True)
    write_file(repo_root / ".nav/README.md", "# nav\n")
    create_nav_symlink(repo_root / ".nav/@docs", repo_root / "docs")
    create_nav_symlink(repo_root / ".nav/@skills", repo_root / "product/harness/skills")

    git(
        repo_root,
        "add",
        "AGENTS.md",
        "CLAUDE.md",
        "INDEX.md",
        "LICENSE",
        "README.md",
        ".gitignore",
        ".claudeignore",
        force=True,
    )
    git(repo_root, "add", "product", "docs", "toolchain", "tools", ".nav", ".codex", force=True)
    return repo_root


def issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def issue_paths(report) -> set[str]:
    return {issue.path for issue in report.issues}


def test_valid_repo_passes(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    report = run_checks(repo_root)
    assert report.issues == []


def test_root_unknown_directory_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / "scratch").mkdir()

    report = run_checks(repo_root)

    assert "FL001" in issue_codes(report)
    assert "scratch" in issue_paths(report)


def test_local_ignored_root_directory_does_not_define_repo_structure(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / "local-tool-cache").mkdir()
    exclude_path = repo_root / ".git/info/exclude"
    exclude_path.write_text(
        f"{exclude_path.read_text(encoding='utf-8')}local-tool-cache/\n",
        encoding="utf-8",
    )

    report = run_checks(repo_root)

    assert "FL001" not in issue_codes(report)
    assert "local-tool-cache" not in issue_paths(report)


def test_tools_must_be_declared_as_compat_shim(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    rules = FolderRules(root_allowed_names=set(FolderRules().root_allowed_names) - {"tools"})

    report = run_checks(repo_root, rules=rules)

    assert "FL001" in issue_codes(report)
    assert "tools" in issue_paths(report)


def test_pytest_cache_untracked_passes_but_tracked_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".pytest_cache/README.md", "cache\n")

    untracked_report = run_checks(repo_root)
    assert "FL013" not in issue_codes(untracked_report)

    git(repo_root, "add", ".pytest_cache/README.md", force=True)
    tracked_report = run_checks(repo_root)

    assert "FL013" in issue_codes(tracked_report)


def test_root_bytecode_files_fail_root_allowlist(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / "demo.pyc", "cache\n")
    write_file(repo_root / "demo.pyo", "cache\n")

    report = run_checks(repo_root)

    assert "FL001" in issue_codes(report)
    assert "demo.pyc" in issue_paths(report)
    assert "demo.pyo" in issue_paths(report)


def test_codex_layer_passes_when_config_and_rules_are_present(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)

    report = run_checks(repo_root)

    assert "FL015" not in issue_codes(report)
    assert "FL016" not in issue_codes(report)


def test_codex_unknown_entry_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".codex/cache.json", "{}\n")

    report = run_checks(repo_root)

    assert "FL015" in issue_codes(report)
    assert ".codex/cache.json" in issue_paths(report)


def test_codex_tracked_non_whitelist_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".codex/notes.md", "# notes\n")
    git(repo_root, "add", ".codex/notes.md", force=True)

    report = run_checks(repo_root)

    assert "FL016" in issue_codes(report)
    assert ".codex/notes.md" in issue_paths(report)


def test_retired_serena_root_directory_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / ".serena").mkdir()
    report = run_checks(repo_root)

    assert "FL001" in issue_codes(report)
    assert ".serena" in issue_paths(report)


def test_repo_local_mount_content_must_not_be_tracked(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".agents/skills/demo-skill/SKILL.md", "---\nname: demo-skill\ndescription: demo\n---\n")
    git(repo_root, "add", ".agents/skills/demo-skill/SKILL.md", force=True)

    skill_payload_report = run_checks(repo_root)

    assert "FL007" in issue_codes(skill_payload_report)
    assert ".agents/skills/demo-skill/SKILL.md" in issue_paths(skill_payload_report)

    git(repo_root, "rm", "--cached", ".agents/skills/demo-skill/SKILL.md")
    write_file(repo_root / ".agents/runtime.json", "{}\n")
    git(repo_root, "add", ".agents/runtime.json", force=True)

    runtime_report = run_checks(repo_root)

    assert "FL007" in issue_codes(runtime_report)
    assert ".agents/runtime.json" in issue_paths(runtime_report)


def test_aw_runtime_control_plane_state_must_not_be_tracked(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".servo/control-state.md", "# Harness Control State\n")
    git(repo_root, "add", ".servo/control-state.md", force=True)

    report = run_checks(repo_root)

    assert "FL007" in issue_codes(report)
    assert ".servo/control-state.md" in issue_paths(report)


def test_first_level_allowlist_drift_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / "toolchain/misc").mkdir()

    report = run_checks(repo_root)

    assert "FL003" in issue_codes(report)
    assert "toolchain/misc" in issue_paths(report)


def test_harness_partition_is_allowed_under_product_and_docs(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / "product/harness").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/harness").mkdir(parents=True, exist_ok=True)

    report = run_checks(repo_root)

    assert "product/harness" not in issue_paths(report)
    assert "docs/harness" not in issue_paths(report)


def test_docs_book_chapters_are_allowed_under_docs(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    for chapter in ("analysis", "ideas", "archive"):
        write_file(repo_root / f"docs/{chapter}/README.md", f"# {chapter}\n")

    report = run_checks(repo_root)

    assert "FL003" not in issue_codes(report)
    for chapter in ("analysis", "ideas", "archive"):
        assert f"docs/{chapter}" not in issue_paths(report)


def test_misplaced_content_patterns_fail(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / "product/runbook.md", "# runbook\n")
    write_file(repo_root / "docs/helper.py", "print('no')\n")
    write_file(repo_root / "toolchain/logs/output.log", "bad\n")

    report = run_checks(repo_root)

    assert {"FL004", "FL005", "FL006"} <= issue_codes(report)


def test_toolchain_cache_content_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / "toolchain/scripts/__pycache__/helper.cpython-313.pyc", "cache\n")
    write_file(repo_root / "toolchain/scripts/.pytest_cache/README.md", "cache\n")
    write_file(repo_root / "toolchain/scripts/cache/state.json", "{}\n")
    write_file(repo_root / "toolchain/scripts/demo.pyo", "cache\n")

    report = run_checks(repo_root)

    assert "FL006" in issue_codes(report)
    assert "toolchain/scripts/__pycache__" in issue_paths(report)
    assert "toolchain/scripts/__pycache__/helper.cpython-313.pyc" in issue_paths(report)
    assert "toolchain/scripts/.pytest_cache" in issue_paths(report)
    assert "toolchain/scripts/cache" in issue_paths(report)
    assert "toolchain/scripts/demo.pyo" in issue_paths(report)


def test_gitignored_ruff_cache_under_toolchain_passes_but_tracked_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".gitignore", ".ruff_cache/\n")
    write_file(repo_root / "toolchain/scripts/test/.ruff_cache/CACHEDIR.TAG", "cache\n")

    untracked_report = run_checks(repo_root)
    assert "toolchain/scripts/test/.ruff_cache" not in issue_paths(untracked_report)

    git(repo_root, "add", "toolchain/scripts/test/.ruff_cache/CACHEDIR.TAG", force=True)
    tracked_report = run_checks(repo_root)

    assert "FL006" in issue_codes(tracked_report)
    assert "toolchain/scripts/test/.ruff_cache" in issue_paths(tracked_report)


def test_product_and_docs_bytecode_files_fail(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / "product/harness/demo.pyc", "cache\n")
    write_file(repo_root / "product/harness/demo.pyo", "cache\n")
    write_file(repo_root / "docs/project-maintenance/demo.pyc", "cache\n")
    write_file(repo_root / "docs/project-maintenance/demo.pyo", "cache\n")

    report = run_checks(repo_root)

    assert {"FL004", "FL005"} <= issue_codes(report)
    assert "product/harness/demo.pyc" in issue_paths(report)
    assert "product/harness/demo.pyo" in issue_paths(report)
    assert "docs/project-maintenance/demo.pyc" in issue_paths(report)
    assert "docs/project-maintenance/demo.pyo" in issue_paths(report)


def test_tools_cache_content_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / "tools/__pycache__/scope_gate_check.cpython-313.pyc", "cache\n")
    write_file(repo_root / "tools/.pytest_cache/README.md", "cache\n")
    write_file(repo_root / "tools/gate_status_backfill.pyo", "cache\n")

    report = run_checks(repo_root)

    assert "FL014" in issue_codes(report)
    assert "tools/__pycache__" in issue_paths(report)
    assert "tools/__pycache__/scope_gate_check.cpython-313.pyc" in issue_paths(report)
    assert "tools/.pytest_cache" in issue_paths(report)
    assert "tools/gate_status_backfill.pyo" in issue_paths(report)


def test_nav_extra_entry_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    write_file(repo_root / ".nav/@tmp", "bad\n")
    git(repo_root, "add", ".nav/@tmp", force=True)

    report = run_checks(repo_root)

    assert "FL010" in issue_codes(report)
    assert ".nav/@tmp" in issue_paths(report)


def test_nav_required_slots_must_be_symlinks(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / ".nav/@docs").unlink()
    write_file(repo_root / ".nav/@docs", "not a symlink\n")

    report = run_checks(repo_root)

    assert "FL011" in issue_codes(report)
    assert ".nav/@docs" in issue_paths(report)


def test_nav_symlink_target_must_be_allowed(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    (repo_root / ".nav/@skills").unlink()
    create_nav_symlink(repo_root / ".nav/@skills", repo_root / "product/harness")

    report = run_checks(repo_root)

    assert "FL012" in issue_codes(report)
    assert ".nav/@skills" in issue_paths(report)


def test_docs_executable_file_fails(tmp_path: Path) -> None:
    repo_root = create_valid_repo(tmp_path)
    path = repo_root / "docs/project-maintenance/run.sh"
    write_file(path, "#!/bin/sh\nexit 0\n")
    make_executable(path)

    report = run_checks(repo_root)

    assert "FL005" in issue_codes(report)
