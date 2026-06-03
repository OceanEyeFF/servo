#!/usr/bin/env python3
"""Run the repeatable closeout acceptance gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from cache_scan_policy import CACHE_DIR_NAMES, CACHE_FILE_SUFFIXES, CACHE_SCAN_ROOTS
except ModuleNotFoundError:
    from toolchain.scripts.test.cache_scan_policy import (
        CACHE_DIR_NAMES,
        CACHE_FILE_SUFFIXES,
        CACHE_SCAN_ROOTS,
    )


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ID = "closeout-governance-task-list-20260402"
EXPECTED_NPM_PACKAGE_FILES = {
    "README.md",
    "bin/servo-installer.js",
    "package.json",
    "path_safety_policy.json",
}


def claude_required_payload_skills(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    skills_root = repo_root / "product" / "harness" / "adapters" / "claude" / "skills"
    if not skills_root.is_dir():
        return ()
    return tuple(
        sorted(path.parent.name for path in skills_root.glob(f"*/payload.json") if path.is_file())
    )


CLAUDE_REQUIRED_PAYLOAD_SKILLS = claude_required_payload_skills()
ROOT_NPM_REQUIRED_PACKAGE_FILES = {
    "package.json",
    "README.md",
    "LICENSE",
    "toolchain/scripts/deploy/path_safety_policy.json",
    "toolchain/scripts/deploy/bin/servo-installer.js",
    "toolchain/scripts/deploy/bin/check-root-publish.js",
    "product/harness/skills/harness-skill/SKILL.md",
    "product/harness/adapters/agents/skills/harness-skill/payload.json",
} | {
    f"product/harness/adapters/claude/skills/{skill_id}/payload.json"
    for skill_id in CLAUDE_REQUIRED_PAYLOAD_SKILLS
}
ROOT_NPM_FORBIDDEN_PACKAGE_FILES = {
    "toolchain/scripts/deploy/adapter_deploy.py",
    "toolchain/scripts/deploy/harness_deploy.py",
    "toolchain/scripts/deploy/aw_scaffold.py",
    "toolchain/scripts/deploy/bin/servo-harness-deploy.js",
    "product/harness/skills/set-harness-goal-skill/scripts/deploy_aw.py",
}
@dataclass
class GateStep:
    gate: str
    required: bool = True


def extract_verify_issue_codes(stdout: str) -> list[str]:
    return re.findall(r"^\s+- ([a-z0-9-]+):", stdout, flags=re.MULTILINE)


def find_primary_worktree_root(repo_root: Path) -> Path | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    candidates: list[Path] = []
    for line in completed.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        path = Path(line.split(" ", 1)[1]).resolve()
        if path == repo_root:
            continue
        candidates.append(path)

    for path in candidates:
        if "/.worktrees/" not in path.as_posix():
            return path
    return candidates[0] if candidates else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the closeout acceptance gate.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--workflow-id", default=WORKFLOW_ID)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON only.",
    )
    return parser.parse_args()


def run_command(command: list[str], *, cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, cwd=cwd, env=env)
    except FileNotFoundError as error:
        return {
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": str(error),
            "passed": False,
        }
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def npm_pack_record(payload: object, label: str) -> tuple[dict[str, object] | None, str]:
    if not isinstance(payload, list):
        return None, f"expected {label} npm pack JSON list, got {type(payload).__name__}"
    if len(payload) != 1:
        return None, f"expected one {label} npm pack result, got {len(payload)}"
    record = payload[0]
    if not isinstance(record, dict):
        return None, f"expected {label} npm pack result object, got {type(record).__name__}"
    files = record.get("files")
    if not isinstance(files, list):
        return None, f"expected {label} npm pack files list"
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            return None, f"expected {label} npm pack file entries with string path"
    filename = record.get("filename")
    if filename is not None and not isinstance(filename, str):
        return None, f"expected {label} npm pack filename string"
    return record, ""


def run_scope_gate(repo_root: Path, python: str) -> dict:
    return run_command(
        [
            python,
            str(repo_root / "tools" / "scope_gate_check.py"),
            "--repo-root",
            str(repo_root),
            "--json",
            "--allowed-prefix",
            "README.md",
            "--allowed-prefix",
            "INDEX.md",
            "--allowed-prefix",
            "docs/README.md",
            "--allowed-prefix",
            "docs/book.md",
            "--allowed-prefix",
            "AGENTS.md",
            "--allowed-prefix",
            "CLAUDE.md",
            "--allowed-prefix",
            "CONTRIBUTING.md",
            "--allowed-prefix",
            ".gitignore",
            "--allowed-prefix",
            ".codex/",
            "--allowed-prefix",
            ".github/",
            "--allowed-prefix",
            "docs/project-maintenance/README.md",
            "--allowed-prefix",
            "docs/harness/",
            "--allowed-prefix",
            "docs/project-maintenance/governance/review-verify-handbook.md",
            "--allowed-prefix",
            "docs/project-maintenance/foundations/root-directory-layering.md",
            "--allowed-prefix",
            "docs/servo-installer/",
            "--allowed-prefix",
            "toolchain/toolchain-layering.md",
            "--allowed-prefix",
            "product/README.md",
            "--allowed-prefix",
            "product/harness/README.md",
            "--allowed-prefix",
            "toolchain/scripts/deploy/path_safety_policy.json",
            "--allowed-prefix",
            "toolchain/scripts/deploy/test_servo_installer.js",
            # TRANSITIONAL: allow deleted Python deploy files through scope gate.
            # These files were removed in P0-067 (Python cleanup). The allowlist
            # entries exist only to let the deletion diff pass scope validation.
            # TODO(P0-067-cleanup): remove these --allowed-prefix entries after
            # the deletion PR is merged and no future diff references these paths.
            "--allowed-prefix",
            "toolchain/scripts/deploy/adapter_deploy.py",
            "--allowed-prefix",
            "toolchain/scripts/deploy/aw_scaffold.py",
            "--allowed-prefix",
            "toolchain/scripts/deploy/harness_deploy.py",
            "--allowed-prefix",
            "toolchain/scripts/deploy/test_adapter_deploy.py",
            "--allowed-prefix",
            "toolchain/scripts/deploy/test_aw_scaffold.py",
            "--allowed-prefix",
            "package.json",
        ],
        cwd=repo_root,
    )


def run_spec_gate(repo_root: Path, python: str) -> dict:
    subchecks = [
        (
            "folder_logic",
            run_command(
                [
                    python,
                    str(repo_root / "toolchain" / "scripts" / "test" / "folder_logic_check.py"),
                    "--repo-root",
                    str(repo_root),
                ],
                cwd=repo_root,
            ),
        ),
        (
            "path_governance",
            run_command(
                [
                    python,
                    str(repo_root / "toolchain" / "scripts" / "test" / "path_governance_check.py"),
                    "--repo-root",
                    str(repo_root),
                    "--scan-path",
                    "docs/project-maintenance",
                    "--scan-path",
                    "docs/harness",
                    "--scan-path",
                    ".autoworkflow/closeout",
                ],
                cwd=repo_root,
            ),
        ),
        (
            "governance_semantic",
            run_command(
                [
                    python,
                    str(repo_root / "toolchain" / "scripts" / "test" / "governance_semantic_check.py"),
                    "--repo-root",
                    str(repo_root),
                ],
                cwd=repo_root,
            ),
        ),
    ]
    passed = all(result["passed"] for _, result in subchecks)
    return {
        "passed": passed,
        "returncode": 0 if passed else 1,
        "subchecks": [{**result, "name": name} for name, result in subchecks],
    }


def run_static_gate(repo_root: Path, python: str) -> dict:
    del python
    scan_root = repo_root / "toolchain" / "scripts" / "test"
    checked: list[str] = []
    failures: list[str] = []
    for path in sorted(scan_root.rglob("*.py")):
        relative_path = path.relative_to(repo_root).as_posix()
        checked.append(relative_path)
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, relative_path, "exec", dont_inherit=True)
        except SyntaxError as error:
            failures.append(f"{relative_path}:{error.lineno}:{error.offset}: {error.msg}")
        except OSError as error:
            failures.append(f"{relative_path}: {error}")

    passed = not failures
    return {
        "command": ["python-syntax-check", "toolchain/scripts/test"],
        "returncode": 0 if passed else 1,
        "stdout": "\n".join(f"checked {path}" for path in checked),
        "stderr": "\n".join(failures),
        "passed": passed,
    }


def run_cache_gate(repo_root: Path, python: str) -> dict:
    del python
    checked_roots: list[str] = []
    failures: list[str] = []
    for relative_root in CACHE_SCAN_ROOTS:
        scan_root = repo_root / relative_root
        if not scan_root.exists():
            continue
        checked_roots.append(relative_root)
        for path in sorted(scan_root.rglob("*")):
            if path.name in CACHE_DIR_NAMES or path.name.endswith(CACHE_FILE_SUFFIXES):
                failures.append(path.relative_to(repo_root).as_posix())

    passed = not failures
    return {
        "command": ["cache-scan", *CACHE_SCAN_ROOTS],
        "returncode": 0 if passed else 1,
        "stdout": "\n".join(f"checked {root}" for root in checked_roots),
        "stderr": "\n".join(failures),
        "passed": passed,
    }


def root_package_version_metadata_check(repo_root: Path) -> tuple[dict, str]:
    package_json_path = repo_root / "package.json"
    deploy_package_json_path = repo_root / "toolchain" / "scripts" / "deploy" / "package.json"
    version_metadata_error = ""
    if package_json_path.is_file():
        try:
            package_metadata = json.loads(package_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            package_metadata = {}
            version_metadata_error = f"invalid root package.json version metadata: {error}"
        package_version = package_metadata.get("version")
        if not isinstance(package_version, str) or not package_version:
            version_metadata_error = version_metadata_error or "root package.json must contain a string version"
        if deploy_package_json_path.is_file():
            try:
                deploy_package_metadata = json.loads(
                    deploy_package_json_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError) as error:
                deploy_package_metadata = {}
                version_metadata_error = (
                    version_metadata_error
                    or f"invalid deploy package.json version metadata: {error}"
                )
            deploy_package_version = deploy_package_metadata.get("version")
            if not isinstance(deploy_package_version, str) or not deploy_package_version:
                version_metadata_error = (
                    version_metadata_error
                    or "deploy package.json must contain a string version"
                )
            elif isinstance(package_version, str) and deploy_package_version != package_version:
                version_metadata_error = (
                    version_metadata_error
                    or "root package.json version must match toolchain/scripts/deploy/package.json: "
                    f"{package_version} != {deploy_package_version}"
                )
        expected_version_output = f"servo-installer {package_version}" if isinstance(package_version, str) else ""
    else:
        expected_version_output = "servo-installer 0.0.0-local"

    version_metadata_check = {
        "command": ["read-root-package-version", "package.json"],
        "returncode": 0 if not version_metadata_error else 1,
        "stdout": expected_version_output,
        "stderr": version_metadata_error,
        "passed": not version_metadata_error,
    }

    return version_metadata_check, expected_version_output


def run_npm_package_packlist(repo_root: Path) -> dict:
    package_root = repo_root / "toolchain" / "scripts" / "deploy"
    result = run_command(["npm", "pack", "--dry-run", "--json"], cwd=package_root)
    result = {**result, "cwd": package_root.relative_to(repo_root).as_posix()}
    if not result["passed"]:
        return result
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError as error:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": f"{result['stderr']}\ninvalid npm pack JSON: {error}".strip(),
        }
    record, validation_error = npm_pack_record(payload, "deploy package")
    if validation_error:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": validation_error,
        }

    packed_files = {entry["path"] for entry in record["files"]}
    package_filename = record.get("filename")
    failures: list[str] = []
    if packed_files != EXPECTED_NPM_PACKAGE_FILES:
        failures.append(
            "unexpected npm package files: "
            f"expected {sorted(EXPECTED_NPM_PACKAGE_FILES)}, got {sorted(packed_files)}"
        )
    if not package_filename:
        failures.append("missing npm package filename")
    else:
        artifact_path = package_root / package_filename
        if artifact_path.exists():
            failures.append(f"dry-run left package artifact: {artifact_path.relative_to(repo_root).as_posix()}")
    if failures:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": "\n".join(failures),
            "packed_files": sorted(packed_files),
        }
    return {**result, "packed_files": sorted(packed_files)}


def pack_npm_tarball_for_smoke(
    *,
    package_root: Path,
    package_dir_path: Path,
    package_label: str,
    subcheck_name: str,
    cwd_label: str,
    repo_artifact_root: Path,
    missing_filename_message: str,
    missing_file_message: str,
    repo_artifact_message: str,
) -> tuple[Path | None, list[dict], list[str]]:
    failures: list[str] = []
    subchecks: list[dict] = []
    package_filename = ""
    pack_result = {
        **run_command(
            ["npm", "pack", "--json", "--pack-destination", str(package_dir_path)],
            cwd=package_root,
        ),
        "cwd": cwd_label,
    }
    subchecks.append({**pack_result, "name": subcheck_name})
    if pack_result["passed"]:
        try:
            payload = json.loads(pack_result["stdout"])
        except json.JSONDecodeError as error:
            failures.append(f"invalid {package_label} npm pack JSON: {error}")
        else:
            record, validation_error = npm_pack_record(payload, package_label)
            if validation_error:
                failures.append(validation_error)
            else:
                package_filename = str(record.get("filename") or "")
                package_file = package_dir_path / package_filename
                if not package_filename:
                    failures.append(missing_filename_message)
                elif not package_file.is_file():
                    failures.append(f"{missing_file_message}: {package_file}")
                elif (repo_artifact_root / package_filename).exists():
                    failures.append(f"{repo_artifact_message}: {package_filename}")

    if not pack_result["passed"] or failures:
        return None, subchecks, failures
    return package_dir_path / package_filename, subchecks, failures


def run_tarball_servo_installer(
    package_file: Path,
    args: list[str],
    *,
    cwd: Path,
    name: str,
    failures: list[str],
    extra_env: dict[str, str] | None = None,
    validate: Callable[[dict, list[str]], None] | None = None,
) -> dict:
    result = run_command(
        [
            "npm",
            "exec",
            "--yes",
            "--package",
            str(package_file),
            "--",
            "servo-installer",
            *args,
        ],
        cwd=cwd,
        extra_env=extra_env,
    )
    if validate is not None:
        validate(result, failures)
    return {**result, "name": name}


def write_python_sentinel_bin(root: Path) -> Path:
    fake_bin = root / "fake-python-bin"
    fake_bin.mkdir()
    sentinel_script = "#!/bin/sh\nprintf 'unexpected-python %s\\n' \"$*\" >&2\nexit 97\n"
    for python_name in ("py", "python", "python3"):
        python_path = fake_bin / python_name
        python_path.write_text(sentinel_script, encoding="utf-8")
        python_path.chmod(0o755)
    return fake_bin


def run_npm_package_tarball_smoke(repo_root: Path, expected_version_output: str) -> dict:
    package_root = repo_root / "toolchain" / "scripts" / "deploy"
    with tempfile.TemporaryDirectory() as package_dir:
        package_dir_path = Path(package_dir)
        package_file, subchecks, failures = pack_npm_tarball_for_smoke(
            package_root=package_root,
            package_dir_path=package_dir_path,
            package_label="deploy package",
            subcheck_name="npm_pack_tarball",
            cwd_label=package_root.relative_to(repo_root).as_posix(),
            repo_artifact_root=package_root,
            missing_filename_message="missing npm package filename",
            missing_file_message="packed tarball was not created",
            repo_artifact_message="packed tarball was written into repo",
        )
        target_repo = package_dir_path / "target-repo"
        target_repo.mkdir()
        fake_python_bin = write_python_sentinel_bin(package_dir_path)
        no_python_env = {
            "SERVO_HARNESS_REPO_ROOT": str(repo_root),
            "SERVO_HARNESS_TARGET_REPO_ROOT": str(target_repo),
            "PATH": f"{fake_python_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        if package_file is not None:
            def validate_no_python(exec_result: dict, no_python_failures: list[str]) -> None:
                if "unexpected-python" in exec_result["stderr"]:
                    no_python_failures.append("packaged command invoked Python")

            def validate_help(exec_result: dict, help_failures: list[str]) -> None:
                validate_no_python(exec_result, help_failures)
                if not exec_result["passed"]:
                    return
                for required_text in ("servo-installer", "Node.js distribution", "tui", "diagnose", "verify", "install", "update"):
                    if required_text not in exec_result["stdout"]:
                        help_failures.append(f"tarball help omitted {required_text!r}")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["--help"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball",
                    failures=failures,
                    validate=validate_help,
                )
            )

            def validate_version(version_result: dict, version_failures: list[str]) -> None:
                validate_no_python(version_result, version_failures)
                if version_result["passed"] and version_result["stdout"].strip() != expected_version_output:
                    version_failures.append("tarball version probe omitted package version")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["--version"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_version",
                    failures=failures,
                    validate=validate_version,
                )
            )

            def validate_tui_guard(tui_result: dict, tui_failures: list[str]) -> None:
                validate_no_python(tui_result, tui_failures)
                tui_guard_passed = (
                    tui_result["returncode"] == 1
                    and "servo-installer tui requires an interactive terminal" in tui_result["stderr"]
                    and tui_result["stdout"] == ""
                )
                if not tui_guard_passed:
                    tui_failures.append("packaged tui did not enforce non-interactive guard")
                tui_result["passed"] = tui_guard_passed

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["tui"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_tui_noninteractive",
                    failures=failures,
                    validate=validate_tui_guard,
                )
            )

            def validate_diagnose(diagnose_result: dict, diagnose_failures: list[str]) -> None:
                validate_no_python(diagnose_result, diagnose_failures)
                if not diagnose_result["passed"]:
                    return
                try:
                    diagnose_payload = json.loads(diagnose_result["stdout"])
                except json.JSONDecodeError as error:
                    diagnose_failures.append(f"invalid packaged diagnose JSON: {error}")
                    return
                if diagnose_payload.get("backend") != "agents":
                    diagnose_failures.append("packaged diagnose did not report agents backend")
                if diagnose_payload.get("binding_count", 0) <= 0:
                    diagnose_failures.append("packaged diagnose did not load source bindings")
                expected_target = str(target_repo / ".agents" / "skills")
                if diagnose_payload.get("target_root") != expected_target:
                    diagnose_failures.append("packaged diagnose did not use isolated target repo")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["diagnose", "--backend", "agents", "--json"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_diagnose",
                    failures=failures,
                    validate=validate_diagnose,
                )
            )

            def validate_update(update_result: dict, update_failures: list[str]) -> None:
                validate_no_python(update_result, update_failures)
                if not update_result["passed"]:
                    return
                try:
                    update_payload = json.loads(update_result["stdout"])
                except json.JSONDecodeError as error:
                    update_failures.append(f"invalid packaged update JSON: {error}")
                    return
                if update_payload.get("backend") != "agents":
                    update_failures.append("packaged update did not report agents backend")
                if update_payload.get("blocking_issue_count", 0) != 0:
                    update_failures.append("packaged update dry-run reported blocking issues")
                if not update_payload.get("planned_target_paths"):
                    update_failures.append("packaged update dry-run did not report target paths")
                expected_target = str(target_repo / ".agents" / "skills")
                if update_payload.get("target_root") != expected_target:
                    update_failures.append("packaged update dry-run did not use isolated target repo")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["update", "--backend", "agents", "--json"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_update_dry_run",
                    failures=failures,
                    validate=validate_update,
                )
            )

            def validate_install(install_result: dict, install_failures: list[str]) -> None:
                validate_no_python(install_result, install_failures)
                if install_result["passed"]:
                    installed_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                    if not installed_skill.is_file():
                        install_failures.append("packaged install did not write servo-harness-skill")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["install", "--backend", "agents"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_install",
                    failures=failures,
                    validate=validate_install,
                )
            )

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["verify", "--backend", "agents"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_verify",
                    failures=failures,
                    validate=validate_no_python,
                )
            )

            def validate_update_apply(update_apply_result: dict, update_apply_failures: list[str]) -> None:
                validate_no_python(update_apply_result, update_apply_failures)
                if not update_apply_result["passed"]:
                    return
                updated_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                if not updated_skill.is_file():
                    update_apply_failures.append("packaged update apply did not write servo-harness-skill")
                if "[agents] ok" not in update_apply_result["stdout"]:
                    update_apply_failures.append("packaged update apply did not run verify")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["update", "--backend", "agents", "--yes"],
                    cwd=target_repo,
                    extra_env=no_python_env,
                    name="npm_exec_tarball_update_apply",
                    failures=failures,
                    validate=validate_update_apply,
                )
            )

        passed = all(result["passed"] for result in subchecks) and not failures
        return {
            "command": ["npm-package-tarball-smoke"],
            "returncode": 0 if passed else 1,
            "stdout": "",
            "stderr": "\n".join(failures),
            "passed": passed,
            "subchecks": subchecks,
        }

def run_root_npm_package_packlist(repo_root: Path) -> dict:
    result = run_command(["npm", "pack", "--dry-run", "--json"], cwd=repo_root)
    result = {**result, "cwd": "."}
    if not result["passed"]:
        return result
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError as error:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": f"{result['stderr']}\ninvalid root npm pack JSON: {error}".strip(),
        }
    record, validation_error = npm_pack_record(payload, "root package")
    if validation_error:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": validation_error,
        }

    packed_files = {entry["path"] for entry in record["files"]}
    package_filename = record.get("filename")
    failures: list[str] = []
    missing_files = sorted(ROOT_NPM_REQUIRED_PACKAGE_FILES - packed_files)
    if missing_files:
        failures.append(f"root npm package missing required files: {missing_files}")
    forbidden_files = sorted(ROOT_NPM_FORBIDDEN_PACKAGE_FILES & packed_files)
    if forbidden_files:
        failures.append(f"root npm package included forbidden files: {forbidden_files}")
    for disallowed_prefix in (".servo/", ".agents/", ".autoworkflow/", ".claude/"):
        if any(path.startswith(disallowed_prefix) for path in packed_files):
            failures.append(f"root npm package included {disallowed_prefix} content")
    if not package_filename:
        failures.append("missing root npm package filename")
    else:
        artifact_path = repo_root / package_filename
        if artifact_path.exists():
            failures.append(f"dry-run left root package artifact: {artifact_path.name}")
    if failures:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": "\n".join(failures),
            "packed_files": sorted(packed_files),
        }
    return {**result, "packed_files": sorted(packed_files)}


def run_root_npm_publish_dry_run(repo_root: Path) -> dict:
    result = run_command(["npm", "run", "publish:dry-run", "--silent"], cwd=repo_root)
    result = {**result, "cwd": "."}
    if not result["passed"]:
        return result
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError as error:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": f"{result['stderr']}\ninvalid root npm publish dry-run JSON: {error}".strip(),
        }

    packed_files = {entry["path"] for entry in payload.get("files", [])}
    package_filename = payload.get("filename")
    failures: list[str] = []
    if payload.get("name") != "servo-installer":
        failures.append("publish dry-run package name is not servo-installer")
    missing_files = sorted(ROOT_NPM_REQUIRED_PACKAGE_FILES - packed_files)
    if missing_files:
        failures.append(f"root npm publish dry-run missing required files: {missing_files}")
    forbidden_files = sorted(ROOT_NPM_FORBIDDEN_PACKAGE_FILES & packed_files)
    if forbidden_files:
        failures.append(f"root npm publish dry-run included forbidden files: {forbidden_files}")
    if not package_filename:
        failures.append("missing root npm publish dry-run package filename")
    else:
        artifact_path = repo_root / package_filename
        if artifact_path.exists():
            failures.append(f"publish dry-run left root package artifact: {artifact_path.name}")
    if failures:
        return {
            **result,
            "returncode": 1,
            "passed": False,
            "stderr": "\n".join(failures),
            "packed_files": sorted(packed_files),
        }
    return {**result, "packed_files": sorted(packed_files)}


def run_root_npm_package_tarball_smoke(repo_root: Path, expected_version_output: str) -> dict:
    with tempfile.TemporaryDirectory() as package_dir:
        package_file, subchecks, failures = pack_npm_tarball_for_smoke(
            package_root=repo_root,
            package_dir_path=Path(package_dir),
            package_label="root package",
            subcheck_name="root_npm_pack_tarball",
            cwd_label=".",
            repo_artifact_root=repo_root,
            missing_filename_message="missing root npm package filename",
            missing_file_message="root packed tarball was not created",
            repo_artifact_message="root packed tarball was written into repo",
        )
        package_dir_path = Path(package_dir)
        target_repo = package_dir_path / "target-repo"
        target_repo.mkdir()
        if package_file is not None:
            clean_env = {
                "SERVO_HARNESS_REPO_ROOT": "",
                "SERVO_HARNESS_TARGET_REPO_ROOT": "",
            }

            def validate_root_help(exec_result: dict, help_failures: list[str]) -> None:
                if not exec_result["passed"]:
                    return
                for required_text in ("servo-installer", "Node.js distribution", "tui", "diagnose", "update"):
                    if required_text not in exec_result["stdout"]:
                        help_failures.append(f"root tarball help omitted {required_text!r}")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["--help"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball",
                    failures=failures,
                    validate=validate_root_help,
                )
            )

            def validate_root_version(version_result: dict, version_failures: list[str]) -> None:
                if version_result["passed"] and version_result["stdout"].strip() != expected_version_output:
                    version_failures.append("root tarball version probe omitted package version")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["--version"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_version",
                    failures=failures,
                    validate=validate_root_version,
                )
            )

            def validate_tui_guard(tui_result: dict, tui_failures: list[str]) -> None:
                tui_guard_passed = (
                    tui_result["returncode"] == 1
                    and "servo-installer tui requires an interactive terminal" in tui_result["stderr"]
                    and tui_result["stdout"] == ""
                )
                if not tui_guard_passed:
                    tui_failures.append("root packaged tui did not enforce non-interactive guard")
                tui_result["passed"] = tui_guard_passed

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["tui"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_tui_noninteractive",
                    failures=failures,
                    validate=validate_tui_guard,
                )
            )

            def validate_root_diagnose(diagnose_result: dict, diagnose_failures: list[str]) -> None:
                if not diagnose_result["passed"]:
                    return
                try:
                    diagnose_payload = json.loads(diagnose_result["stdout"])
                except json.JSONDecodeError as error:
                    diagnose_failures.append(f"invalid root packaged diagnose JSON: {error}")
                    return
                if diagnose_payload.get("backend") != "agents":
                    diagnose_failures.append("root packaged diagnose did not report agents backend")
                if diagnose_payload.get("binding_count", 0) <= 0:
                    diagnose_failures.append("root packaged diagnose did not load source bindings")
                expected_target = str(target_repo / ".agents" / "skills")
                if diagnose_payload.get("target_root") != expected_target:
                    diagnose_failures.append("root packaged diagnose did not use cwd target root")
                if diagnose_payload.get("source_root") == str(target_repo):
                    diagnose_failures.append("root packaged diagnose used target repo as source root")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["diagnose", "--backend", "agents", "--json"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_diagnose",
                    failures=failures,
                    validate=validate_root_diagnose,
                )
            )

            def validate_root_update(update_result: dict, update_failures: list[str]) -> None:
                if not update_result["passed"]:
                    return
                try:
                    update_payload = json.loads(update_result["stdout"])
                except json.JSONDecodeError as error:
                    update_failures.append(f"invalid root packaged update JSON: {error}")
                    return
                if update_payload.get("backend") != "agents":
                    update_failures.append("root packaged update did not report agents backend")
                if update_payload.get("blocking_issue_count", 0) != 0:
                    update_failures.append("root packaged update dry-run reported blocking issues")
                if not update_payload.get("planned_target_paths"):
                    update_failures.append("root packaged update did not report target paths")
                expected_target = str(target_repo / ".agents" / "skills")
                if update_payload.get("target_root") != expected_target:
                    update_failures.append("root packaged update did not use cwd target root")
                if update_payload.get("source_root") == str(target_repo):
                    update_failures.append("root packaged update used target repo as source root")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["update", "--backend", "agents", "--json"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_update_dry_run",
                    failures=failures,
                    validate=validate_root_update,
                )
            )

            def validate_install(install_result: dict, install_failures: list[str]) -> None:
                if install_result["passed"]:
                    installed_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                    if not installed_skill.is_file():
                        install_failures.append("root packaged install did not write servo-harness-skill")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["install", "--backend", "agents"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_install",
                    failures=failures,
                    validate=validate_install,
                )
            )

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["verify", "--backend", "agents"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_verify",
                    failures=failures,
                )
            )

            def validate_claude_install(
                install_result: dict,
                install_failures: list[str],
            ) -> None:
                if not install_result["passed"]:
                    return
                agents_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                claude_skill = (
                    target_repo
                    / ".claude"
                    / "skills"
                    / "set-harness-goal-skill"
                    / "SKILL.md"
                )
                claude_harness_skill = (
                    target_repo
                    / ".claude"
                    / "skills"
                    / "harness-skill"
                    / "SKILL.md"
                )
                if not agents_skill.is_file():
                    install_failures.append("root packaged claude install removed agents skill")
                if not claude_skill.is_file():
                    install_failures.append("root packaged claude install did not write set-harness-goal skill")
                if not claude_harness_skill.is_file():
                    install_failures.append("root packaged claude install did not write harness skill")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["install", "--backend", "claude"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_install_claude",
                    failures=failures,
                    validate=validate_claude_install,
                )
            )

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["verify", "--backend", "claude"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_verify_claude",
                    failures=failures,
                )
            )

            def validate_bundle_diagnose(
                diagnose_result: dict,
                diagnose_failures: list[str],
            ) -> None:
                if not diagnose_result["passed"]:
                    return
                try:
                    diagnose_payload = json.loads(diagnose_result["stdout"])
                except json.JSONDecodeError as error:
                    diagnose_failures.append(f"invalid root packaged bundle diagnose JSON: {error}")
                    return
                if diagnose_payload.get("bundle") is not True:
                    diagnose_failures.append("root packaged bundle diagnose did not report bundle mode")
                    return
                backends = diagnose_payload.get("backends")
                if not isinstance(backends, dict) or "agents" not in backends or "claude" not in backends:
                    diagnose_failures.append("root packaged bundle diagnose omitted backend summaries")
                    return
                if diagnose_payload.get("total_issues") != 0:
                    diagnose_failures.append("root packaged bundle diagnose reported issues after install")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["diagnose", "--backend", "bundle", "--json"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_diagnose_bundle",
                    failures=failures,
                    validate=validate_bundle_diagnose,
                )
            )

            def validate_bundle_verify(
                verify_result: dict,
                verify_failures: list[str],
            ) -> None:
                if not verify_result["passed"]:
                    return
                if "[agents] ok" not in verify_result["stdout"]:
                    verify_failures.append("root packaged bundle verify did not verify agents")
                if "[claude] ok" not in verify_result["stdout"]:
                    verify_failures.append("root packaged bundle verify did not verify claude")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["verify", "--backend", "bundle"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_verify_bundle",
                    failures=failures,
                    validate=validate_bundle_verify,
                )
            )

            def validate_claude_update_apply(
                update_apply_result: dict,
                update_apply_failures: list[str],
            ) -> None:
                if not update_apply_result["passed"]:
                    return
                agents_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                claude_skill = (
                    target_repo
                    / ".claude"
                    / "skills"
                    / "set-harness-goal-skill"
                    / "SKILL.md"
                )
                claude_harness_skill = (
                    target_repo
                    / ".claude"
                    / "skills"
                    / "harness-skill"
                    / "SKILL.md"
                )
                if not agents_skill.is_file():
                    update_apply_failures.append("root packaged claude update removed agents skill")
                if not claude_skill.is_file():
                    update_apply_failures.append(
                        "root packaged claude update left set-harness-goal skill missing"
                    )
                if not claude_harness_skill.is_file():
                    update_apply_failures.append(
                        "root packaged claude update left harness skill missing"
                    )
                if "[claude] ok" not in update_apply_result["stdout"]:
                    update_apply_failures.append("root packaged claude update apply did not run verify")
                if "[claude] update complete" not in update_apply_result["stdout"]:
                    update_apply_failures.append(
                        "root packaged claude update apply did not complete"
                    )

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["update", "--backend", "claude", "--yes"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_update_apply_claude",
                    failures=failures,
                    validate=validate_claude_update_apply,
                )
            )

            def validate_update_apply(update_apply_result: dict, update_apply_failures: list[str]) -> None:
                if not update_apply_result["passed"]:
                    return
                updated_skill = target_repo / ".agents" / "skills" / "servo-harness-skill" / "SKILL.md"
                if not updated_skill.is_file():
                    update_apply_failures.append("root packaged update apply did not write servo-harness-skill")
                if "[agents] ok" not in update_apply_result["stdout"]:
                    update_apply_failures.append("root packaged update apply did not run verify")

            subchecks.append(
                run_tarball_servo_installer(
                    package_file,
                    ["update", "--backend", "agents", "--yes"],
                    cwd=target_repo,
                    extra_env=clean_env,
                    name="root_npm_exec_tarball_update_apply",
                    failures=failures,
                    validate=validate_update_apply,
                )
            )

    passed = all(result["passed"] for result in subchecks) and not failures
    return {
        "command": ["root-npm-package-tarball-smoke"],
        "returncode": 0 if passed else 1,
        "stdout": "",
        "stderr": "\n".join(failures),
        "passed": passed,
        "subchecks": subchecks,
    }

def run_test_gate_subchecks(repo_root: Path, python: str, version_metadata_check: dict, expected_version_output: str) -> list[tuple[str, dict]]:
    subchecks = [
        ("root_package_version_metadata", version_metadata_check),
        (
            "gate_tool_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_closeout_gate_tools.py"], cwd=repo_root),
        ),
        (
            "folder_logic_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_folder_logic_check.py"], cwd=repo_root),
        ),
        (
            "path_governance_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_path_governance_check.py"], cwd=repo_root),
        ),
        (
            "governance_semantic_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_governance_semantic_check.py"], cwd=repo_root),
        ),
        (
            "complexity_signal_scanner_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_complexity_signal_scanner.py"], cwd=repo_root),
        ),
        (
            "set_harness_goal_e2e_fixture_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_set_harness_goal_e2e_fixture.py"], cwd=repo_root),
        ),
        (
            "agents_adapter_contract_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/test_agents_adapter_contract.py"], cwd=repo_root),
        ),
        (
            "servo_installer_cli_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/servo_installer_cli"], cwd=repo_root),
        ),
        (
            "servo_installer_tui_tests",
            run_command([python, "-m", "pytest", "toolchain/scripts/test/servo_installer_tui"], cwd=repo_root),
        ),
        (
            "deploy_package_unit_tests",
            run_command(["npm", "--prefix", "toolchain/scripts/deploy", "test", "--silent"], cwd=repo_root),
        ),
        (
            "repo_analysis_contract_check",
            run_command([python, "toolchain/scripts/test/repo_analysis_contract_check.py"], cwd=repo_root),
        ),
        (
            "npm_pack_dry_run_servo_installer",
            run_npm_package_packlist(repo_root),
        ),
        (
            "npm_tarball_smoke_servo_installer",
            run_npm_package_tarball_smoke(repo_root, expected_version_output),
        ),
        (
            "root_npm_pack_dry_run_servo_installer",
            run_root_npm_package_packlist(repo_root),
        ),
        (
            "root_npm_publish_dry_run_servo_installer",
            run_root_npm_publish_dry_run(repo_root),
        ),
        (
            "root_npm_tarball_smoke_servo_installer",
            run_root_npm_package_tarball_smoke(repo_root, expected_version_output),
        ),
    ]
    return subchecks


def run_test_gate(repo_root: Path, python: str) -> dict:
    version_metadata_check, expected_version_output = root_package_version_metadata_check(repo_root)
    subchecks = run_test_gate_subchecks(
        repo_root,
        python,
        version_metadata_check,
        expected_version_output,
    )
    passed = all(result["passed"] for _, result in subchecks)
    skipped = any(result.get("skipped", False) for _, result in subchecks)
    return {
        "passed": passed,
        "returncode": 0 if passed else 1,
        "status": "skipped" if passed and skipped else ("passed" if passed else "failed"),
        "subchecks": [{**result, "name": name} for name, result in subchecks],
    }


def run_smoke_gate(repo_root: Path, python: str, workflow_id: str) -> dict:
    def retained_runtime_paths_for(root: Path) -> list[Path]:
        runtime_root = root / ".autoworkflow" / "closeout"
        return [
            runtime_root / "manual-governance-loop-3round-r000001-m000642" / "runtime.json",
            runtime_root / "manual-governance-loop-6-3-3-r000001-m046830" / "runtime.json",
        ]

    def retained_roots_present(paths: list[Path]) -> bool:
        return any(path.parent.exists() or path.parent.is_symlink() for path in paths)

    selected_root = repo_root
    retained_runtime_paths = retained_runtime_paths_for(repo_root)
    if not retained_roots_present(retained_runtime_paths):
        primary_root = find_primary_worktree_root(repo_root)
        if primary_root is not None:
            primary_paths = retained_runtime_paths_for(primary_root)
            if retained_roots_present(primary_paths):
                selected_root = primary_root
                retained_runtime_paths = primary_paths

    backfill_smoke = run_command(
        [
            python,
            str(repo_root / "tools" / "gate_status_backfill.py"),
            "--workflow-id",
            workflow_id,
            "--gate",
            "smoke_gate_dry_run",
            "--status",
            "passed",
            "--details",
            json.dumps({"mode": "smoke", "dry_run": True}, sort_keys=True),
            "--dry-run",
            "--json",
        ],
        cwd=repo_root,
    )

    runtime_checks = []
    if not retained_roots_present(retained_runtime_paths):
        return {
            "passed": backfill_smoke["passed"],
            "returncode": 0 if backfill_smoke["passed"] else 1,
            "status": "skipped" if backfill_smoke["passed"] else "failed",
            "runtime_checks": [
                {
                    "path": str(selected_root / ".autoworkflow" / "closeout"),
                    "passed": True,
                    "skipped": True,
                    "reason": "no retained closeout runtime evidence configured for this repository",
                }
            ],
            "backfill_smoke": backfill_smoke,
        }

    runtime_passed = True
    for runtime_path in retained_runtime_paths:
        if not runtime_path.exists():
            check = {
                "path": str(runtime_path),
                "missing": True,
                "passed": False,
            }
            runtime_checks.append(check)
            runtime_passed = False
            continue
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        active_round = payload.get("active_round")
        check = {
            "path": str(runtime_path),
            "active_round": active_round,
            "passed": active_round is None,
        }
        if selected_root != repo_root:
            check["checked_from"] = str(selected_root)
        runtime_checks.append(check)
        runtime_passed = runtime_passed and check["passed"]

    passed = runtime_passed and backfill_smoke["passed"]
    return {
        "passed": passed,
        "returncode": 0 if passed else 1,
        "status": "passed" if passed else "failed",
        "runtime_checks": runtime_checks,
        "backfill_smoke": backfill_smoke,
    }


def run_gate(gate: str, *, repo_root: Path, python: str, workflow_id: str) -> dict:
    if gate == "scope_gate":
        return run_scope_gate(repo_root, python)
    if gate == "spec_gate":
        return run_spec_gate(repo_root, python)
    if gate == "static_gate":
        return run_static_gate(repo_root, python)
    if gate == "cache_gate":
        return run_cache_gate(repo_root, python)
    if gate == "test_gate":
        return run_test_gate(repo_root, python)
    if gate == "smoke_gate":
        return run_smoke_gate(repo_root, python, workflow_id)
    raise ValueError(f"Unsupported gate: {gate}")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    python = sys.executable
    steps = [
        GateStep(gate="scope_gate"),
        GateStep(gate="spec_gate"),
        GateStep(gate="static_gate"),
        GateStep(gate="cache_gate"),
        GateStep(gate="test_gate"),
        GateStep(gate="smoke_gate"),
    ]

    results = []
    backfill_results = []
    passed = True
    for step in steps:
        result = run_gate(step.gate, repo_root=repo_root, python=python, workflow_id=args.workflow_id)
        result["gate"] = step.gate
        results.append(result)
        skip_reasons: list[str] = []
        for subcheck in result.get("subchecks", []):
            if subcheck.get("skipped"):
                reason = subcheck.get("skip_reason") or subcheck.get("stdout", "").strip() or subcheck["name"]
                skip_reasons.append(f"{subcheck['name']}: {reason}")
        for runtime_check in result.get("runtime_checks", []):
            if runtime_check.get("skipped"):
                reason = runtime_check.get("reason") or runtime_check["path"]
                skip_reasons.append(f"runtime: {reason}")

        backfill_status = result.get("status") or ("passed" if result["passed"] else "failed")
        backfill_details = {"returncode": result["returncode"]}
        if skip_reasons:
            backfill_details["skip_reasons"] = skip_reasons

        backfill = run_command(
            [
                python,
                str(repo_root / "tools" / "gate_status_backfill.py"),
                "--workflow-id",
                args.workflow_id,
                "--gate",
                result["gate"],
                "--status",
                backfill_status,
                "--details",
                json.dumps(backfill_details, sort_keys=True),
            ],
            cwd=repo_root,
        )
        backfill_results.append(
            {
                "gate": result["gate"],
                "returncode": backfill["returncode"],
                "stdout": backfill["stdout"],
                "stderr": backfill["stderr"],
                "passed": backfill["passed"],
            }
        )
        step_passed = result["passed"] and backfill["passed"]
        passed = passed and (step_passed or not step.required)
        if step.required and not step_passed:
            break

    payload = {
        "workflow_id": args.workflow_id,
        "results": results,
        "backfill_results": backfill_results,
        "passed": passed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
