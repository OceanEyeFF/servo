#!/usr/bin/env python3
"""Check that the current working tree only touches an approved closeout scope."""

from __future__ import annotations

import argparse
import codecs
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ALLOWED_PREFIXES = (
    "docs/README.md",
    ".autoworkflow/contracts/",
    ".autoworkflow/closeout/",
    ".autoworkflow/state/",
    "docs/project-maintenance/",
    "docs/harness/",
    "product/README.md",
    "product/.servo_template/",
    "package.json",
    "product/harness/skills/",
    "product/harness/adapters/",
    ".agents/",
    ".claude/",
    "toolchain/scripts/deploy/bin/",
    "toolchain/scripts/deploy/package.json",
    "toolchain/scripts/deploy/README.md",
    "toolchain/scripts/test/",
    "tools/closeout_acceptance_gate.py",
    "tools/gate_status_backfill.py",
    "tools/scope_gate_check.py",
)


@dataclass
class ScopeGateResult:
    passed: bool
    changed_files: list[str]
    violations: list[str]


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the closeout worktree scope.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root used for git status inspection.",
    )
    parser.add_argument(
        "--allowed-prefix",
        action="append",
        default=[],
        help="Additional path prefix that is allowed to change.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON only.",
    )
    return parser.parse_args()


def collect_changed_files(repo_root: Path) -> list[ChangedFile]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "-c",
            "core.quotePath=false",
            "status",
            "--short",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    changed: list[ChangedFile] = []
    for raw_line in completed.stdout.splitlines():
        if not raw_line:
            continue
        status = raw_line[:2]
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = normalize_status_path(path)
        changed.append(ChangedFile(path=path, status=status))
    return changed


def normalize_status_path(path: str) -> str:
    """Decode Git-quoted UTF-8 octal paths from status output.

    `latin-1` is used only as a byte-preserving bridge after
    `unicode_escape`; it is not an assertion that repository paths are
    Latin-1 encoded. `collect_changed_files` requests `core.quotePath=false`,
    so this is mainly a compatibility fallback for quoted status lines.
    """
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    inner = path[1:-1]
    try:
        decoded = codecs.decode(inner, "unicode_escape")
        return decoded.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return path


def is_allowed_path(path: str, allowed_path: str) -> bool:
    if allowed_path.endswith("/"):
        return path == allowed_path.rstrip("/") or path.startswith(allowed_path)
    return path == allowed_path


def is_allowed_runtime_untrack(change: ChangedFile) -> bool:
    if change.path.startswith((".servo/", ".agents/", ".autoworkflow/", ".claude/")):
        return change.status.strip(" ") == "D"
    return False


def check_scope(changed_files: list[ChangedFile] | list[str], allowed_prefixes: tuple[str, ...]) -> ScopeGateResult:
    violations: list[str] = []
    normalized_changes = [
        change if isinstance(change, ChangedFile) else ChangedFile(path=change, status=" M")
        for change in changed_files
    ]
    for change in normalized_changes:
        path = change.path
        if path.startswith(".git"):
            continue
        if any(is_allowed_path(path, prefix) for prefix in allowed_prefixes):
            continue
        if is_allowed_runtime_untrack(change):
            continue
        violations.append(path)
    return ScopeGateResult(
        passed=not violations,
        changed_files=[change.path for change in normalized_changes],
        violations=violations,
    )


def main() -> int:
    args = parse_args()
    allowed_prefixes = DEFAULT_ALLOWED_PREFIXES + tuple(args.allowed_prefix)
    changed_files = collect_changed_files(args.repo_root)
    result = check_scope(changed_files, allowed_prefixes)

    payload = {
        "passed": result.passed,
        "changed_files": result.changed_files,
        "violations": result.violations,
        "allowed_prefixes": list(allowed_prefixes),
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if result.passed:
            print("Scope gate passed.")
        else:
            print("Scope gate failed.")
            for violation in result.violations:
                print(f"  disallowed change: {violation}")
        print(json.dumps(payload, indent=2, sort_keys=True))

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
