from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
NODE_HELPER = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "repo-init-goal-skill"
    / "scripts"
    / "deploy_servo.js"
)
SCANNER = REPO_ROOT / "toolchain" / "scripts" / "test" / "complexity_signal_scanner.py"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_node(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(NODE_HELPER), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_scanner(repo: Path) -> dict[str, object]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, str(SCANNER), "--repo", str(repo), "--json"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    return json.loads(completed.stdout)


def signal_by_id(result: dict[str, object], signal_id: str) -> dict[str, object]:
    signals = result["signals"]
    assert isinstance(signals, list)
    for item in signals:
        if item["signal"] == signal_id:
            return item
    raise AssertionError(f"missing signal: {signal_id}")


def generate_existing_code_adoption(target: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return run_node(
        "generate",
        "--deploy-path",
        str(target),
        "--baseline-branch",
        "main",
        "--owner",
        "servo-kernel",
        "--updated",
        "2026-06-02",
        "--adoption-mode",
        "existing-code-adoption",
        *extra_args,
    )


def test_low_risk_existing_code_adoption_stays_lightweight_by_default(tmp_path: Path) -> None:
    target = tmp_path / "small-repo"
    write_file(target / "package.json", '{"scripts":{"test":"node src/index.js"}}\n')
    write_file(target / "src" / "index.js", "console.log('ok')\n")

    scanner_result = run_scanner(target)
    assert scanner_result["scanner"]["semantics"] == "scanner output is evidence, not verdict"
    assert scanner_result["summary"]["strongest_signal_level"] == "low"
    assert signal_by_id(scanner_result, "compose_files")["observed_value"] == 0
    assert signal_by_id(scanner_result, "compose_services")["observed_value"] == 0
    assert signal_by_id(scanner_result, "package_managers")["observed_value"] == 1
    assert scanner_result["safety"]["secret_like_path_content_read"] is False
    assert scanner_result["safety"]["file_contents_emitted"] is False

    completed = generate_existing_code_adoption(target)

    assert completed.returncode == 0, completed.stderr
    assert (target / ".servo" / "repo" / "discovery-input.md").is_file()
    assert not (target / ".servo" / "repo" / "temporary-understanding.md").exists()
    assert not (target / ".servo" / "repo" / "complex-project-entry-gate.md").exists()


def test_weak_doc_onboarding_generates_runtime_understanding_and_blocking_gate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "weak-doc-repo"
    write_file(target / "src" / "main.py", "print('needs understanding')\n")

    completed = generate_existing_code_adoption(target, "--weak-doc-onboarding")

    assert completed.returncode == 0, completed.stderr
    temporary_understanding = target / ".servo" / "repo" / "temporary-understanding.md"
    complex_gate = target / ".servo" / "repo" / "complex-project-entry-gate.md"
    assert temporary_understanding.is_file()
    assert complex_gate.is_file()

    temporary_understanding_text = temporary_understanding.read_text(encoding="utf-8")
    assert "truth_status: temporary-inferred" in temporary_understanding_text
    assert "not Goal Charter truth" in temporary_understanding_text

    complex_gate_text = complex_gate.read_text(encoding="utf-8")
    assert "Milestone-side blocking gate, not fixed heavy mode" in complex_gate_text
    assert "scanner_output_role: scanner output is evidence, not verdict" in complex_gate_text
    assert "entry_verdict: blocked" in complex_gate_text
    assert "milestone_blocking_decision: block_create, block_upsert, block_activate, block_derive_worktrack" in complex_gate_text
    assert "needed: true" in complex_gate_text
    assert "recommendation_status: pending_operator_review" in complex_gate_text
    assert "blocks_implementation_until_resolved: true" in complex_gate_text
    assert "temporary_understanding_ref: temporary-understanding.md" in complex_gate_text


def test_complex_fixture_scanner_evidence_and_explicit_gate_without_weak_doc(
    tmp_path: Path,
) -> None:
    target = tmp_path / "complex-repo"
    write_file(
        target / "docker-compose.yml",
        textwrap.dedent(
            """\
            services:
              api:
                build:
                  context: ./services/api
                ports:
                  - "8000:8000"
                env_file:
                  - .env
              worker:
                build: ./services/worker
              web:
                build: ./apps/web
              db:
                image: postgres:16
                volumes:
                  - ./data:/var/lib/postgresql/data
              cache:
                image: redis:7
            """
        ),
    )
    write_file(target / "package.json", '{"scripts":{"test":"node test.js"}}\n')
    write_file(target / "pyproject.toml", "[project]\nname = 'complex-demo'\n")
    write_file(target / "services" / "api" / "main.py", "# TODO: split service\n")
    write_file(target / "services" / "worker" / "job.py", "# FIXME: retry policy\n")
    write_file(target / "apps" / "web" / "index.ts", "export const app = 'web'\n")
    write_file(target / "db" / "migrations" / "001_init.sql", "create table demo(id int);\n")
    write_file(target / ".github" / "workflows" / "deploy.yml", "name: deploy\n")
    write_file(target / ".env", "SECRET_VALUE=must-not-be-read\n")

    scanner_result = run_scanner(target)
    assert scanner_result["scanner"]["semantics"] == "scanner output is evidence, not verdict"
    assert signal_by_id(scanner_result, "compose_files")["observed_value"] == 1
    assert signal_by_id(scanner_result, "compose_services")["observed_value"] == 5
    assert signal_by_id(scanner_result, "package_managers")["observed_value"] == 2
    assert signal_by_id(scanner_result, "migration_data_hints")["observed_value"] >= 1
    assert scanner_result["safety"]["secret_like_path_content_read"] is False
    assert scanner_result["safety"]["file_contents_emitted"] is False
    assert scanner_result["safety"]["skipped_secret_like_files"] == [".env"]

    completed = generate_existing_code_adoption(target, "--complex-project-entry-gate")

    assert completed.returncode == 0, completed.stderr
    complex_gate = target / ".servo" / "repo" / "complex-project-entry-gate.md"
    assert complex_gate.is_file()
    assert not (target / ".servo" / "repo" / "temporary-understanding.md").exists()
    complex_gate_text = complex_gate.read_text(encoding="utf-8")
    assert "Milestone-side blocking gate, not fixed heavy mode" in complex_gate_text
    assert "scanner output is evidence, not verdict" in complex_gate_text
    assert "entry_verdict: blocked" in complex_gate_text
    assert "milestone_blocking_decision: block_create, block_upsert, block_activate, block_derive_worktrack" in complex_gate_text
    assert "needed: false" in complex_gate_text
    assert "recommendation_status: not_needed" in complex_gate_text
    assert "blocks_implementation_until_resolved: false" in complex_gate_text
    assert "temporary_understanding_ref: N/A" in complex_gate_text
