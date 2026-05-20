from __future__ import annotations

import errno
import os
import select
import shutil
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def run_tui_script(
    repo_root: Path,
    target_repo: Path,
    steps: list[tuple[str, str]],
    *,
    env_overrides: dict[str, str] | None = None,
    timeout_seconds: float = 90.0,
) -> tuple[int, str]:
    if not hasattr(os, "openpty"):
        pytest.skip("PTY support is not available")
    if shutil.which("node") is None:
        pytest.skip("node is not available")

    target_repo.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "AW_HARNESS_REPO_ROOT": str(repo_root),
        "AW_HARNESS_TARGET_REPO_ROOT": str(target_repo),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if env_overrides is not None:
        env.update(env_overrides)

    master_fd, slave_fd = os.openpty()
    process: subprocess.Popen[bytes] | None = None
    output_parts: list[str] = []
    try:
        process = subprocess.Popen(
            [
                "node",
                str(repo_root / "toolchain" / "scripts" / "deploy" / "bin" / "servo-installer.js"),
                "tui",
            ],
            cwd=target_repo,
            env=env,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1

        step_index = 0
        search_pos = 0
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master_fd], [], [], 0.05)
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output_parts.append(chunk.decode("utf-8", errors="replace"))

            output = "".join(output_parts)
            while step_index < len(steps):
                pattern, response = steps[step_index]
                match_index = output.find(pattern, search_pos)
                if match_index == -1:
                    break
                search_pos = match_index + len(pattern)
                if response:
                    os.write(master_fd, response.replace("\n", "\r").encode("utf-8"))
                step_index += 1

            if process.poll() is not None:
                break

        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
            pytest.fail("timed out waiting for servo-installer tui; output so far:\n" + "".join(output_parts))

        while True:
            ready, _, _ = select.select([master_fd], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(master_fd, 4096)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            output_parts.append(chunk.decode("utf-8", errors="replace"))

        return process.returncode or 0, "".join(output_parts)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if slave_fd != -1:
            os.close(slave_fd)
        os.close(master_fd)


def fake_failing_python_bin(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "fake-python-bin"
    fake_bin.mkdir()
    for python_name in ("py", "python3", "python"):
        fake_python = fake_bin / python_name
        fake_python.write_text(
            "#!/bin/sh\n"
            "printf 'unexpected-python %s\\n' \"$*\" >&2\n"
            "exit 97\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
    return fake_bin


def test_tui_show_cli_help_menu_action(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "help-target",
        [
            ("Select an action:", "5\n"),
            ("Press Enter to return to the installer menu", "\n"),
            ("Select an action:", "6\n"),
        ],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "5. Show CLI help" in output
    assert "usage: servo-installer" in output
    assert "check_paths_exist --backend agents|claude" in output


def test_tui_diagnose_menu_action_uses_node_owned_json(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        tmp_path / "diagnose-target",
        [
            ("Select an action:", "2\n"),
            ("Press Enter to return to the installer menu", "\n"),
            ("Select an action:", "6\n"),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert '"backend": "agents"' in output
    assert '"target_root_status": "missing"' in output


def test_tui_verify_menu_action_returns_to_menu_after_strict_verify(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        tmp_path / "verify-target",
        [
            ("Select an action:", "3\n"),
            ("Press Enter to return to the installer menu", "\n"),
            ("Select an action:", "6\n"),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert "[agents] drift" in output
    assert "missing-target-root" in output
    assert output.count("Select an action:") >= 2


def test_tui_update_dry_run_menu_action(repo_root: Path, tmp_path: Path) -> None:
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        tmp_path / "dry-run-target",
        [
            ("Select an action:", "4\n"),
            ("Press Enter to return to the installer menu", "\n"),
            ("Select an action:", "6\n"),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert "[agents] update plan" in output
    assert "dry-run only; pass --yes to apply update" in output
    assert not (tmp_path / "dry-run-target" / ".agents" / "skills").exists()


def test_tui_guided_update_cancel_does_not_install(repo_root: Path, tmp_path: Path) -> None:
    target_repo = tmp_path / "guided-cancel-target"
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        target_repo,
        [
            ("Select an action:", "1\n"),
            ("Step 3: Type yes", "no\n"),
            ("Update cancelled.", "\n"),
            ("Select an action:", "6\n"),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert "Guided update flow" in output
    assert "Step 1: Diagnose current agents install." in output
    assert "Step 2: Review update dry-run plan." in output
    assert "Step 3: Type yes to apply update via prune --all -> check_paths_exist -> install -> verify" in output
    assert "Update cancelled." in output
    assert "[agents] applying update" not in output
    assert not (target_repo / ".agents" / "skills").exists()


def test_tui_guided_update_apply_runs_install_and_verify(repo_root: Path, tmp_path: Path) -> None:
    target_repo = tmp_path / "guided-apply-target"
    code, output = run_tui_script(
        repo_root,
        target_repo,
        [
            ("Select an action:", "1\n"),
            ("Step 3: Type yes", "yes\n"),
            ("Press Enter to return to the installer menu", "\n"),
            ("Select an action:", "6\n"),
        ],
    )

    assert code == 0, output
    assert "Step 4: Applying update and running strict verify." in output
    assert "[agents] applying update" in output
    assert "[agents] ok" in output
    assert "[agents] update complete" in output
    assert (target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md").is_file()


def test_tui_unknown_selection_loops_back_to_menu(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "unknown-target",
        [
            ("Select an action:", "not-a-choice\n"),
            ("Unknown selection.", ""),
            ("Select an action:", "6\n"),
        ],
    )

    assert code == 0, output
    assert "Unknown selection." in output
    assert output.count("Select an action:") >= 2


@pytest.mark.parametrize("exit_text", ["6\n", "q\n", "quit\n", "exit\n"])
def test_tui_exit_choices(repo_root: Path, tmp_path: Path, exit_text: str) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / f"exit-target-{exit_text.strip()}",
        [("Select an action:", exit_text)],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "6. Exit" in output
