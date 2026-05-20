#!/usr/bin/env python3
"""Recommend minimal verification set based on git diff paths.

Analyzes ``git diff --name-only`` output and maps changed files to the
minimum set of governance/test checks that should be run before merging.

Usage::

    PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/recommend_verification.py
    PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/recommend_verification.py --json
    PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/recommend_verification.py --run
    PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/recommend_verification.py --base origin/master
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]

# ── Domain → check rules ──────────────────────────────────────────────
# Each entry maps a path prefix to a list of (label, command) tuples.
# The "label" is the human-readable check name; "command" is structured
# execution metadata. Commands are never run through a shell.

_SCRIPTS = "toolchain/scripts"
_TEST = f"{_SCRIPTS}/test"
_DEPLOY = f"{_SCRIPTS}/deploy"


class CommandSpec(TypedDict, total=False):
    argv: List[str]
    env: Dict[str, str]
    cwd: str


CheckRule = Tuple[str, CommandSpec]


def _command(
    argv: List[str],
    *,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[str] = None,
) -> CommandSpec:
    spec: CommandSpec = {"argv": argv}
    if env:
        spec["env"] = dict(env)
    if cwd:
        spec["cwd"] = cwd
    return spec


def _python_check(script_path: str, *args: str) -> CommandSpec:
    return _command(
        ["python3", script_path, *args],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )


def _python_module(module: str, *args: str) -> CommandSpec:
    return _command(
        ["python3", "-m", module, *args],
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )


def _node_check(script_path: str, *args: str) -> CommandSpec:
    return _command(["node", script_path, *args])


def _node_test(script_path: str) -> CommandSpec:
    return _command(["node", "--test", script_path])


def _npm_check(*args: str, cwd: Optional[str] = None) -> CommandSpec:
    return _command(["npm", *args], cwd=cwd)


def _display_command(command: CommandSpec) -> str:
    env = command.get("env", {})
    env_prefix = [f"{key}={value}" for key, value in sorted(env.items())]
    return " ".join([*env_prefix, shlex.join(command["argv"])])


def _check_entry(check_label: str, command: CommandSpec, reason: str) -> Dict[str, object]:
    entry: Dict[str, object] = {
        "check": check_label,
        "command": _display_command(command),
        "argv": list(command["argv"]),
        "reason": reason,
    }
    if "env" in command:
        entry["env"] = dict(command["env"])
    if "cwd" in command:
        entry["cwd"] = command["cwd"]
    return entry


_NODE_TEST_AW_INSTALLER: CheckRule = (
    "node --test test_servo_installer.js",
    _node_test(f"{_DEPLOY}/test_servo_installer.js"),
)
_AW_INSTALLER_VERIFY_BUNDLE: CheckRule = (
    "servo-installer.js verify --backend bundle",
    _node_check(f"{_DEPLOY}/bin/servo-installer.js", "verify", "--backend", "bundle"),
)
_NPM_PACK_DEPLOY_DRY_RUN: CheckRule = (
    "npm pack --dry-run in toolchain/scripts/deploy",
    _npm_check("pack", "--dry-run", cwd=_DEPLOY),
)


DOMAIN_RULES: List[Tuple[str, List[CheckRule]]] = [
    (
        "docs/harness/",
        [
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
        ],
    ),
    (
        "docs/project-maintenance/",
        [
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
        ],
    ),
    (
        f"{_DEPLOY}/bin/servo-installer.js",
        [
            _NODE_TEST_AW_INSTALLER,
            ("closeout_acceptance_gate.py --json", _python_check(f"{_TEST}/closeout_acceptance_gate.py", "--json")),
            _AW_INSTALLER_VERIFY_BUNDLE,
            _NPM_PACK_DEPLOY_DRY_RUN,
        ],
    ),
    (
        f"{_DEPLOY}/test_servo_installer.js",
        [
            _NODE_TEST_AW_INSTALLER,
        ],
    ),
    (
        f"{_TEST}/folder_logic_check.py",
        [
            ("folder_logic_check.py", _python_check(f"{_TEST}/folder_logic_check.py")),
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
            (f"pytest {_TEST}/test_folder_logic_check.py", _python_module("pytest", f"{_TEST}/test_folder_logic_check.py")),
        ],
    ),
    (
        f"{_TEST}/path_governance_check.py",
        [
            ("folder_logic_check.py", _python_check(f"{_TEST}/folder_logic_check.py")),
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
            (f"pytest {_TEST}/test_path_governance_check.py", _python_module("pytest", f"{_TEST}/test_path_governance_check.py")),
        ],
    ),
    (
        f"{_TEST}/governance_semantic_check.py",
        [
            ("folder_logic_check.py", _python_check(f"{_TEST}/folder_logic_check.py")),
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
            (f"pytest {_TEST}/test_governance_semantic_check.py", _python_module("pytest", f"{_TEST}/test_governance_semantic_check.py")),
        ],
    ),
    (
        "product/harness/skills/",
        [
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
            ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
            ("closeout_acceptance_gate.py --json", _python_check(f"{_TEST}/closeout_acceptance_gate.py", "--json")),
        ],
    ),
    (
        "product/harness/adapters/",
        [
            ("closeout_acceptance_gate.py", _python_check(f"{_TEST}/closeout_acceptance_gate.py")),
            (f"PYTHONDONTWRITEBYTECODE=1 python3 {_TEST}/test_agents_adapter_contract.py", _python_check(f"{_TEST}/test_agents_adapter_contract.py")),
        ],
    ),
    (
        f"{_DEPLOY}/package.json",
        [
            ("closeout_acceptance_gate.py", _python_check(f"{_TEST}/closeout_acceptance_gate.py")),
            _NODE_TEST_AW_INSTALLER,
            _AW_INSTALLER_VERIFY_BUNDLE,
            _NPM_PACK_DEPLOY_DRY_RUN,
        ],
    ),
    (
        f"{_DEPLOY}/",
        [
            ("closeout_acceptance_gate.py", _python_check(f"{_TEST}/closeout_acceptance_gate.py")),
            _NODE_TEST_AW_INSTALLER,
            _AW_INSTALLER_VERIFY_BUNDLE,
            _NPM_PACK_DEPLOY_DRY_RUN,
        ],
    ),
    (
        ".servo/",
        [
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
        ],
    ),
    (
        ".claude/",
        [
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
        ],
    ),
    (
        ".agents/",
        [
            ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
        ],
    ),
]

# Special rules: exact file matches (checked before prefix matches).
# Lazily initialized on first access so that import-time filesystem state
# (e.g. sparse checkouts) does not silently drop exact-match rules.
_EXACT_RULES_CACHE: Optional[Dict[str, List[CheckRule]]] = None


def _get_exact_rules() -> Dict[str, List[CheckRule]]:
    global _EXACT_RULES_CACHE
    if _EXACT_RULES_CACHE is None:
        _EXACT_RULES_CACHE = {}
        for prefix, checks in DOMAIN_RULES:
            full_path = REPO_ROOT / prefix
            if full_path.is_file():
                _EXACT_RULES_CACHE[prefix] = checks
    return _EXACT_RULES_CACHE

# ── full-verification set (used when >THRESHOLD domains match) ────────
_MULTI_DOMAIN_THRESHOLD = 4

FULL_VERIFICATION: List[CheckRule] = [
    ("folder_logic_check.py", _python_check(f"{_TEST}/folder_logic_check.py")),
    ("path_governance_check.py", _python_check(f"{_TEST}/path_governance_check.py")),
    ("governance_semantic_check.py", _python_check(f"{_TEST}/governance_semantic_check.py")),
    ("closeout_acceptance_gate.py --json", _python_check(f"{_TEST}/closeout_acceptance_gate.py", "--json")),
    _NODE_TEST_AW_INSTALLER,
]


def get_diff_files(base: Optional[str] = None) -> List[str]:
    """Return list of changed files from ``git diff --name-only``.

    When *base* is provided the diff is computed against that ref;
    otherwise it uses the default (HEAD / unstaged + staged).
    """
    argv = ["git", "diff", "--name-only"]
    if base:
        argv.append(base)
    result = subprocess.run(
        argv, capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    if result.returncode != 0:
        print(f"Error running git diff: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return files


def _prefix_matches(file_path: str, prefix: str) -> bool:
    """Check if *file_path* starts with *prefix*.

    For directory prefixes (ending with ``/``) this is a simple prefix match.
    For file prefixes (no trailing ``/``) this is an exact match.
    """
    if prefix.endswith("/"):
        return file_path == prefix.rstrip("/") or file_path.startswith(prefix)
    return file_path == prefix


def _matches_domain(file_path: str, domain_prefix: str) -> bool:
    """True if *file_path* falls under *domain_prefix*."""
    if domain_prefix in _get_exact_rules():
        return file_path == domain_prefix
    return _prefix_matches(file_path, domain_prefix)


def recommend(files: List[str]) -> Dict[str, object]:
    """Map changed files to recommended checks.

    Returns a dict with keys:
    - ``domains``: list of matched domain labels
    - ``domain_files``: dict mapping domain → list of matched files
    - ``domain_checks``: dict mapping domain → list of (label, command metadata)
    - ``all_checks``: deduplicated ordered list with display command, argv/env/cwd, and reason
    - ``files_changed``: total number of changed files
    """
    domain_labels: List[str] = []
    domain_files: Dict[str, List[str]] = OrderedDict()
    domain_checks: Dict[str, List[CheckRule]] = OrderedDict()

    for f in files:
        for prefix, checks in DOMAIN_RULES:
            if _matches_domain(f, prefix):
                label = prefix.rstrip("/")
                if label not in domain_labels:
                    domain_labels.append(label)
                    domain_checks[label] = []
                domain_files.setdefault(label, []).append(f)

    # Collect checks per domain (deduplicate within each domain)
    for label in domain_labels:
        seen: set = set()
        for prefix, checks in DOMAIN_RULES:
            if prefix.rstrip("/") == label:
                for check_label, command in checks:
                    if check_label not in seen:
                        seen.add(check_label)
                        domain_checks[label].append((check_label, command))
                break

    # Build global deduplicated check list with reasons
    all_checks: list = []
    seen_checks: set = set()
    for label in domain_labels:
        for check_label, command in domain_checks[label]:
            dedup_key = check_label
            if dedup_key not in seen_checks:
                seen_checks.add(dedup_key)
                all_checks.append(_check_entry(
                    check_label,
                    command,
                    f"{label} changes",
                ))

    # If many domains are touched, escalate to full verification
    if len(domain_labels) >= _MULTI_DOMAIN_THRESHOLD:
        all_checks = []
        for check_label, command in FULL_VERIFICATION:
            all_checks.append(_check_entry(
                check_label,
                command,
                f"multi-domain diff ({len(domain_labels)} domains)",
            ))

    return {
        "domains": domain_labels,
        "domain_files": domain_files,
        "domain_checks": domain_checks,
        "all_checks": all_checks,
        "files_changed": len(files),
    }


def format_text_output(result: Dict[str, object]) -> str:
    """Format recommendations as human-readable text."""
    lines = ["Recommended verification for current diff:\n"]
    for label, files in result["domain_files"].items():
        lines.append(f"  Domain: {label} ({len(files)} file{'s' if len(files) != 1 else ''})")
        for check_label, _command in result["domain_checks"].get(label, []):
            lines.append(f"    -> {check_label}")
        lines.append("")

    total = len(result["all_checks"])
    domains = len(result["domains"])
    lines.append(f"Summary: {total} check{'s' if total != 1 else ''} recommended across {domains} domain{'s' if domains != 1 else ''}")
    return "\n".join(lines)


def format_json_output(result: Dict[str, object]) -> str:
    """Format recommendations as JSON."""
    payload = {
        "domains": result["domains"],
        "files_changed": result["files_changed"],
        "recommended_checks": [
            {"check": c["check"], "reason": c["reason"]}
            for c in result["all_checks"]
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def run_checks(result: Dict[str, object], cwd: Optional[str] = None) -> int:
    """Execute recommended checks sequentially; return worst exit code."""
    if cwd is None:
        cwd = str(REPO_ROOT)

    checks: list = result["all_checks"]
    if not checks:
        print("No checks to run.")
        return 0

    print(f"Running {len(checks)} check(s)...\n")
    worst_rc = 0
    passed = 0
    failed = 0
    skipped = 0

    for entry in checks:
        label = entry["check"]
        command = entry["command"]
        argv = entry["argv"]
        print(f"--- {label} ---")
        print(f"  $ {command}")

        run_cwd = cwd
        command_cwd = entry.get("cwd")
        if isinstance(command_cwd, str):
            run_cwd = str(REPO_ROOT / command_cwd)

        env = os.environ.copy()
        command_env = entry.get("env")
        if isinstance(command_env, dict):
            env.update(command_env)

        try:
            proc = subprocess.run(
                argv,
                cwd=run_cwd,
                env=env,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print(f"  [SKIP] command not found: {argv[0]}")
            skipped += 1
            print()
            continue

        if proc.returncode == 0:
            print(f"  [PASS]")
            passed += 1
        else:
            print(f"  [FAIL] exit={proc.returncode}")
            if proc.stderr:
                # Print last 5 lines of stderr
                stderr_lines = proc.stderr.strip().split("\n")
                for line in stderr_lines[-5:]:
                    print(f"    stderr: {line}")
            failed += 1
            worst_rc = proc.returncode

        print()

    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    return worst_rc


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recommend minimal verification set from git diff paths."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output recommendations as JSON."
    )
    parser.add_argument(
        "--run", action="store_true",
        help="Execute the recommended checks and report results."
    )
    parser.add_argument(
        "--base", default=None, metavar="REF",
        help="Compare against a specific ref instead of the default (e.g. origin/master)."
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    files = get_diff_files(base=args.base)
    if not files:
        print("No diff detected (no changed files).")
        return 0

    result = recommend(files)

    if args.json:
        print(format_json_output(result))
    else:
        print(format_text_output(result))

    if args.run:
        print()
        return run_checks(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
