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
    timeout_seconds: float = 15.0,
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

    def write_response(response: str) -> None:
        payload = response
        index = 0
        while index < len(payload):
            if payload.startswith("\x1b[", index) and index + 2 < len(payload):
                token = payload[index : index + 3]
                index += 3
            else:
                token = payload[index]
                index += 1
            os.write(master_fd, token.encode("utf-8"))
            time.sleep(0.03)

    master_fd, slave_fd = os.openpty()
    process: subprocess.Popen[bytes] | None = None
    output_parts: list[str] = []
    try:
        process = subprocess.Popen(
            [
                "node",
                str(repo_root / "toolchain" / "scripts" / "deploy" / "bin" / "aw-installer.js"),
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
                    write_response(response)
                step_index += 1

            if process.poll() is not None:
                break

        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
            pytest.fail("timed out waiting for aw-installer tui; output so far:\n" + "".join(output_parts))

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


def test_tui_menu_renders_and_exits_with_current_arrow_key_contract(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "help-target",
        [
            ("Enter confirm", "q\n"),
        ],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "backend: bundle" in output
    assert "Guided install/update" in output
    assert "Show update dry-run plan" in output
    assert "Exit" in output


def test_tui_ignores_unknown_key_and_can_exit(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "unknown-target",
        [
            ("Enter confirm", "xq\n"),
        ],
    )

    assert code == 0, output
    assert output.count("TUI Menu") >= 1


def test_tui_exit_choice(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "exit-target",
        [("Enter confirm", "q\n")],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "Exit" in output


def test_tui_arrow_key_enter_can_select_exit(repo_root: Path, tmp_path: Path) -> None:
    code, output = run_tui_script(
        repo_root,
        tmp_path / "arrow-exit-target",
        [("Enter confirm", "\x1b[B\x1b[B\x1b[B\x1b[B\x1b[B\r")],
    )

    assert code == 0, output
    assert "AW Installer" in output
    assert "Exit" in output
