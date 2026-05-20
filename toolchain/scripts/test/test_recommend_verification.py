from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "toolchain" / "scripts" / "test" / "recommend_verification.py"

spec = importlib.util.spec_from_file_location("recommend_verification", MODULE_PATH)
assert spec is not None
assert spec.loader is not None
recommend_verification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recommend_verification)


def test_deploy_package_recommendations_use_node_owned_checks() -> None:
    changed_files = [
        "toolchain/scripts/deploy/package.json",
        "toolchain/scripts/deploy/package-lock.json",
    ]
    for changed_file in changed_files:
        result = recommend_verification.recommend([changed_file])

        checks = {entry["check"]: entry for entry in result["all_checks"]}
        rendered = "\n".join(str(entry["command"]) for entry in result["all_checks"])

        assert "adapter_deploy.py verify" not in checks
        assert "adapter_deploy.py" not in rendered
        assert checks["node --test test_servo_installer.js"]["argv"] == [
            "node",
            "--test",
            "toolchain/scripts/deploy/test_servo_installer.js",
        ]
        assert checks["servo-installer.js verify --backend bundle"]["argv"] == [
            "node",
            "toolchain/scripts/deploy/bin/servo-installer.js",
            "verify",
            "--backend",
            "bundle",
        ]
        assert checks["npm pack --dry-run in toolchain/scripts/deploy"]["argv"] == [
            "npm",
            "pack",
            "--dry-run",
        ]
        assert (
            checks["npm pack --dry-run in toolchain/scripts/deploy"]["cwd"]
            == "toolchain/scripts/deploy"
        )


def test_run_checks_uses_argv_env_and_metadata_cwd(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run(
        argv: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append({
            "argv": argv,
            "cwd": cwd,
            "env": env,
            "capture_output": capture_output,
            "text": text,
        })
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(recommend_verification.subprocess, "run", fake_run)

    result = {
        "all_checks": [
            recommend_verification._check_entry(
                "path_governance_check.py",
                recommend_verification._python_check(
                    "toolchain/scripts/test/path_governance_check.py",
                ),
                "test",
            ),
            recommend_verification._check_entry(
                "npm pack --dry-run in toolchain/scripts/deploy",
                recommend_verification._npm_check(
                    "pack",
                    "--dry-run",
                    cwd="toolchain/scripts/deploy",
                ),
                "test",
            ),
        ],
    }

    assert recommend_verification.run_checks(result, cwd="/tmp/custom") == 0

    assert calls[0]["argv"] == [
        "python3",
        "toolchain/scripts/test/path_governance_check.py",
    ]
    assert calls[0]["cwd"] == "/tmp/custom"
    assert calls[0]["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True
    assert calls[1]["argv"] == ["npm", "pack", "--dry-run"]
    assert calls[1]["cwd"] == str(REPO_ROOT / "toolchain/scripts/deploy")


def test_full_verification_escalation_with_multi_domain() -> None:
    changed_files = [
        "docs/harness/artifact/control/milestone.md",
        "product/harness/skills/harness-skill/SKILL.md",
        "toolchain/scripts/test/recommend_verification.py",
        "toolchain/scripts/deploy/bin/servo-installer.js",
    ]
    result = recommend_verification.recommend(changed_files)

    assert len(result["domains"]) >= recommend_verification._MULTI_DOMAIN_THRESHOLD
    full_labels = {entry[0] for entry in recommend_verification.FULL_VERIFICATION}
    result_labels = {entry["check"] for entry in result["all_checks"]}
    assert result_labels == full_labels


def test_run_checks_subprocess_failure() -> None:
    import subprocess

    result = {
        "all_checks": [
            recommend_verification._check_entry(
                "failing_check",
                recommend_verification._python_check("nonexistent.py"),
                "test",
            ),
        ],
    }
    rc = recommend_verification.run_checks(result)
    assert rc != 0


def test_recommend_empty_files() -> None:
    result = recommend_verification.recommend([])
    assert result["files_changed"] == 0
    assert len(result["all_checks"]) == 0
