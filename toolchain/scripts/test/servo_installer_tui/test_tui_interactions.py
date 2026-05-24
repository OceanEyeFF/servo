from __future__ import annotations

import errno
import os
import re
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
        "SERVO_HARNESS_REPO_ROOT": str(repo_root),
        "SERVO_HARNESS_TARGET_REPO_ROOT": str(target_repo),
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
        normalized_output = ""
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
            normalized_output = strip_ansi(output)
            while step_index < len(steps):
                pattern, response = steps[step_index]
                match_index = normalized_output.find(pattern, search_pos)
                if match_index == -1:
                    break
                search_pos = match_index + len(pattern)
                if response:
                    if response.startswith("raw:"):
                        encoded_response = response.removeprefix("raw:")
                    else:
                        encoded_response = response
                    os.write(master_fd, encoded_response.encode("utf-8"))
                step_index += 1

            if process.poll() is not None:
                break

        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
            pytest.fail("timed out waiting for servo-installer tui; output so far:\n" + strip_ansi("".join(output_parts)))

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

        return process.returncode or 0, strip_ansi("".join(output_parts))
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if slave_fd != -1:
            os.close(slave_fd)
        os.close(master_fd)


ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", output)


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


def choose_menu_steps(index: int) -> list[tuple[str, str]]:
    return [("↑↓ navigate", "raw:\x1b[B") for _ in range(index)] + [("↑↓ navigate", "raw:\r")]


def quit_menu_step() -> tuple[str, str]:
    return ("↑↓ navigate", "raw:q")


def test_tui_menu_renders_current_actions_and_exits(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "menu-target",
        choose_menu_steps(5),
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "Guided install/update" in output
    assert "Show update dry-run plan" in output
    assert "Exit" in output


def test_tui_diagnose_menu_action_uses_node_owned_json(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        tmp_path / "diagnose-target",
        [
            *choose_menu_steps(2),
            ("Press Enter to return to the installer menu...", "\n"),
            quit_menu_step(),
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
            *choose_menu_steps(3),
            ("Press Enter to return to the installer menu...", "\n"),
            quit_menu_step(),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert "[agents] drift" in output
    assert "missing-target-root" in output
    assert output.count("TUI Menu") >= 2


def test_tui_update_dry_run_menu_action(repo_root: Path, tmp_path: Path) -> None:
    fake_bin = fake_failing_python_bin(tmp_path)
    code, output = run_tui_script(
        repo_root,
        tmp_path / "dry-run-target",
        [
            *choose_menu_steps(4),
            ("Press Enter to return to the installer menu...", "\n"),
            quit_menu_step(),
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
            *choose_menu_steps(0),
            ("Press Enter to return to the installer menu...", "\n"),
            ("No pre-existing paths", "\n"),
            ("Type yes to proceed", "no\n"),
            quit_menu_step(),
        ],
        env_overrides={"PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
    )

    assert code == 0, output
    assert "unexpected-python" not in output
    assert "Diagnosing bundle install" in output
    assert "No pre-existing paths" in output
    assert "Ready to install/update bundle." in output
    assert "Guided flow cancelled. No changes made." in output
    assert "[agents] applying update" not in output
    assert not (target_repo / ".agents" / "skills").exists()


def test_tui_guided_update_apply_runs_install_and_verify(repo_root: Path, tmp_path: Path) -> None:
    target_repo = tmp_path / "guided-apply-target"
    code, output = run_tui_script(
        repo_root,
        target_repo,
        [
            *choose_menu_steps(0),
            ("Press Enter to return to the installer menu...", "\n"),
            ("No pre-existing paths", "\n"),
            ("Type yes to proceed", "yes\n"),
            ("Install complete for bundle", "\n"),
            ("Verification passed", "\n"),
            ("All stages completed successfully", "\n"),
            ("Press Enter to return to the installer menu...", "\n"),
            quit_menu_step(),
        ],
    )

    assert code == 0, output
    assert "Installing bundle" in output
    assert "[agents] ok" in output
    assert "[claude] ok" in output
    assert "[bundle] install complete for both backends" in output
    assert "All stages completed successfully." in output
    assert (target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md").is_file()


def test_tui_unknown_key_stays_on_menu_then_quits(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "unknown-target",
        [
            ("↑↓ navigate", "raw:x"),
            ("↑↓ navigate", "raw:q"),
        ],
    )

    assert code == 0, output
    assert "Guided install/update" in output


def test_tui_exit_choice_quits(repo_root: Path, tmp_path: Path) -> None:
    exit_text = "q"
    code, output = run_tui_script(
        repo_root,
        tmp_path / f"exit-target-{exit_text.strip()}",
        [("↑↓ navigate", f"raw:{exit_text}")],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "Exit" in output
