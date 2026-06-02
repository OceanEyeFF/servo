from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from complexity_signal_scanner import EVIDENCE_DISCLAIMER, scan_repo


SCANNER = Path(__file__).resolve().parent / "complexity_signal_scanner.py"
CONTRACT_TERMS = (
    "scanner output is evidence",
    "complexity_signals",
    "CI",
    "no_network",
    "no_service_start",
)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def signal_by_id(result: dict[str, object], signal_id: str) -> dict[str, object]:
    signals = result["signals"]
    assert isinstance(signals, list)
    for item in signals:
        if item["signal"] == signal_id:
            return item
    raise AssertionError(f"missing signal: {signal_id}")


def test_scanner_emits_evidence_only_json_with_visible_thresholds(tmp_path: Path) -> None:
    source_text = SCANNER.read_text(encoding="utf-8")
    test_text = Path(__file__).read_text(encoding="utf-8")
    assert all(term in source_text or term in test_text for term in CONTRACT_TERMS)

    write_file(
        tmp_path / "docker-compose.yml",
        textwrap.dedent(
            """\
            services:
              api:
                build:
                  context: ./services/api
                ports:
                  - "8000:8000"
                volumes:
                  - ./data:/data
                env_file:
                  - .env
              worker:
                build: ./services/worker
            """
        ),
    )
    write_file(tmp_path / "package.json", '{"scripts":{"test":"node test.js"}}\n')
    write_file(tmp_path / "pyproject.toml", "[project]\nname = 'demo'\n")
    write_file(tmp_path / "services/api/main.py", "# TODO: split service\nprint('ok')\n")
    write_file(tmp_path / "services/worker/job.py", "# FIXME: retry policy\n")
    write_file(tmp_path / ".github/workflows/deploy.yml", "name: deploy\n")
    write_file(tmp_path / "db/migrations/001_init.sql", "create table demo(id int);\n")
    write_file(tmp_path / ".env", "SECRET_VALUE=must-not-be-read\n")

    result = scan_repo(tmp_path)

    assert result["schema_version"] == "complexity-signal-scanner/v1"
    assert result["scanner"]["evidence_only"] is True
    assert result["scanner"]["verdict"] == "not_provided"
    assert result["scanner"]["semantics"] == EVIDENCE_DISCLAIMER
    assert result["summary"]["scanner_output_role"] == EVIDENCE_DISCLAIMER
    assert "thresholds" in result
    assert result["complexity_signals"] == result["signals"]
    assert signal_by_id(result, "compose_files")["threshold"] == {"medium": 1, "high": 2}
    assert signal_by_id(result, "compose_services")["observed_value"] == 2
    assert signal_by_id(result, "package_managers")["observed_value"] == 2
    assert signal_by_id(result, "migration_data_hints")["observed_value"] >= 1
    assert signal_by_id(result, "ci_deploy_hints")["observed_value"] >= 1
    assert signal_by_id(result, "debt_proxy_markers")["observed_value"] == 2

    observations = result["observations"]
    assert observations["compose_key_totals"]["build"] == 2
    assert observations["compose_key_totals"]["build_context"] == 1
    assert observations["compose_key_totals"]["ports"] == 1
    assert observations["compose_key_totals"]["volumes"] == 1
    assert observations["compose_key_totals"]["env_file"] == 1
    assert "services/api" in observations["service_like_dirs"]
    assert "services/worker" in observations["service_like_dirs"]
    assert result["safety"]["secret_content_read"] is False
    assert result["safety"]["no_network"] is True
    assert result["safety"]["no_service_start"] is True
    assert result["safety"]["skipped_secret_like_files"] == [".env"]


def test_scanner_skips_runtime_and_dependency_dirs(tmp_path: Path) -> None:
    write_file(tmp_path / ".servo/hidden.py", "# TODO ignored\n")
    write_file(tmp_path / ".logs/runtime.py", "# FIXME ignored\n")
    write_file(tmp_path / "node_modules/pkg/index.js", "// TODO ignored\n")
    write_file(tmp_path / "src/app.py", "print('counted')\n")

    result = scan_repo(tmp_path)

    observations = result["observations"]
    assert observations["debt_proxy_signals"]["marker_count"] == 0
    assert observations["code_size"]["file_count"] == 1


def test_scanner_cli_json_output(tmp_path: Path) -> None:
    write_file(tmp_path / "go.mod", "module demo\n")
    write_file(tmp_path / "cmd/server/main.go", "package main\n")

    completed = subprocess.run(
        [sys.executable, str(SCANNER), "--repo", str(tmp_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["scanner"]["semantics"] == EVIDENCE_DISCLAIMER
    assert signal_by_id(payload, "package_managers")["observed_value"] == 1
    assert completed.stderr == ""
