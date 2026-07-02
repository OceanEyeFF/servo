#!/usr/bin/env python3
"""Validate repository folder layering, tracked exceptions, and compatibility slots."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

ROOT_ALLOWED_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "INDEX.md",
    "LICENSE",
    "package.json",
    "README.md",
    ".github",
    ".aw",
    ".codex",
    "docs",
    "product",
    "toolchain",
    "tools",
    ".agents",
    ".autoworkflow",
    ".claude",
    ".claudeignore",
    ".nav",
    ".pytest_cache",
    ".ruff_cache",
    ".spec-workflow",
    ".test",
}
ROOT_ALLOWED_PREFIXES = (".git",)
NAV_SLOT_TARGETS = {
    "@docs": "docs",
    "@skills": "product/harness/skills",
}
FIRST_LEVEL_ALLOWLIST = {
    "product": {"README.md", ".servo_template", "harness"},
    "docs": {"README.md", "book.md", "project-maintenance", "harness", "analysis", "ideas", "archive", "servo-installer"},
    "toolchain": {"README.md", "toolchain-layering.md", "scripts"},
}
TOOLS_TRACKED_ALLOWLIST = {
    "tools/closeout_acceptance_gate.py",
    "tools/gate_status_backfill.py",
    "tools/scope_gate_check.py",
}
CODEX_TRACKED_ALLOWLIST = {
    ".codex/config.toml",
    ".codex/rules/repo.rules",
}
MOUNT_LAYER_PREFIXES = (".agents/", ".claude/")
RUNTIME_STATE_LAYER_PREFIXES = (".servo/",)
CODEX_ALLOWED_ENTRIES = {"config.toml", "rules"}
CODEX_RULES_ALLOWED_ENTRIES = {"repo.rules"}
NAV_ALLOWED_ENTRIES = {"README.md", "@docs", "@skills"}
NAV_REQUIRED_SLOTS = tuple(NAV_SLOT_TARGETS)
PRODUCT_STATE_FILENAMES = {"runtime.json", "runtime.yaml", "runtime.yml", "state.json", "state.yaml", "state.yml"}
GENERIC_RUNTIME_FILENAMES = PRODUCT_STATE_FILENAMES | {"session.json"}
PRODUCT_BANNED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".autoworkflow",
    ".spec-workflow",
    "cache",
    "logs",
    "operations",
    "runbook",
    "runbooks",
}
PRODUCT_ALLOWED_HIDDEN_DIRS = {
    "product/.servo_template",
}
DOCS_BANNED_SEGMENTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "cache",
    "dist",
    "logs",
    "node_modules",
}
DOCS_SCRIPT_SUFFIXES = {".bash", ".js", ".ps1", ".py", ".rb", ".sh", ".ts", ".zsh"}
TOOLCHAIN_BANNED_SEGMENTS = {
    ".agents",
    ".autoworkflow",
    ".claude",
    ".nav",
    ".pytest_cache",
    ".ruff_cache",
    ".spec-workflow",
    "__pycache__",
    "adapters",
    "cache",
    "logs",
    "manifests",
    "skills",
}


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str


@dataclass
class FolderRules:
    root_allowed_names: set[str] = field(default_factory=lambda: set(ROOT_ALLOWED_NAMES))
    root_allowed_prefixes: tuple[str, ...] = ROOT_ALLOWED_PREFIXES
    first_level_allowlist: dict[str, set[str]] = field(
        default_factory=lambda: {key: set(value) for key, value in FIRST_LEVEL_ALLOWLIST.items()}
    )
    tools_tracked_allowlist: set[str] = field(default_factory=lambda: set(TOOLS_TRACKED_ALLOWLIST))
    codex_tracked_allowlist: set[str] = field(default_factory=lambda: set(CODEX_TRACKED_ALLOWLIST))


@dataclass
class FolderLogicReport:
    issues: list[Issue] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def add_issue(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue(code=code, path=path, message=message))

    def add_info(self, message: str) -> None:
        self.infos.append(message)

    @property
    def failures(self) -> list[str]:
        return [format_issue(issue) for issue in self.issues]


def format_issue(issue: Issue) -> str:
    location = issue.path or "."
    return f"[{issue.code}] {location}: {issue.message}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate folder layering, tracked exceptions, and nav slots.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def collect_tracked_paths(repo_root: Path) -> set[str]:
    completed = run_git(repo_root, "ls-files", "-z")
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git ls-files failed")
    return {entry for entry in completed.stdout.split("\x00") if entry}


def is_tracked_path(relative_path: str, tracked_paths: set[str]) -> bool:
    prefix = f"{relative_path.rstrip('/')}/"
    return relative_path in tracked_paths or any(path.startswith(prefix) for path in tracked_paths)


def is_git_ignored_path(repo_root: Path, relative_path: str) -> bool:
    completed = run_git(repo_root, "check-ignore", "-q", "--", relative_path)
    return completed.returncode == 0


def is_untracked_ignored_path(repo_root: Path, relative_path: str, tracked_paths: set[str]) -> bool:
    return not is_tracked_path(relative_path, tracked_paths) and is_git_ignored_path(repo_root, relative_path)


def normalize_real_path(path: Path) -> str:
    raw = os.path.realpath(path)
    normalized = raw.replace("\\", "/").rstrip("/")
    return normalized.casefold() or "/"


def resolve_repo_relative_target(path: Path, repo_root: Path) -> str | None:
    if not path.exists():
        return None
    repo_norm = normalize_real_path(repo_root)
    target_norm = normalize_real_path(path)
    if target_norm == repo_norm:
        return ""
    prefix = f"{repo_norm}/"
    if not target_norm.startswith(prefix):
        return None
    return target_norm[len(prefix) :]


def iter_relative_paths(base_dir: Path, repo_root: Path) -> list[str]:
    if not base_dir.exists():
        return []
    return sorted(path.relative_to(repo_root).as_posix() for path in base_dir.rglob("*"))


def path_has_segment(path: str, segments: set[str]) -> bool:
    return any(segment in segments for segment in Path(path).parts)


def path_has_suffix(path: str, suffixes: set[str]) -> bool:
    return Path(path).suffix in suffixes


def path_is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def check_root_allowlist(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport, rules: FolderRules) -> None:
    checked = 0
    for entry in sorted(repo_root.iterdir(), key=lambda item: item.name):
        checked += 1
        name = entry.name
        if not is_tracked_path(name, tracked_paths) and is_git_ignored_path(repo_root, name):
            continue
        if name in rules.root_allowed_names or name.startswith(rules.root_allowed_prefixes):
            continue
        report.add_issue("FL001", name, "root object is not registered in the folder allowlist")
    report.add_info(f"checked {checked} root objects against the folder allowlist")

    checked_cache_tracking = False
    for cache_path in (".pytest_cache", ".ruff_cache"):
        checked_cache_tracking = True
        if is_tracked_path(cache_path, tracked_paths):
            report.add_issue(
                "FL013",
                cache_path,
                "ephemeral cache may exist locally but must not be tracked",
            )
    if checked_cache_tracking:
        report.add_info("checked local cache tracked state")


def check_first_level_allowlist(repo_root: Path, report: FolderLogicReport, rules: FolderRules) -> None:
    checked = 0
    for parent_name, allowed_entries in rules.first_level_allowlist.items():
        parent_dir = repo_root / parent_name
        if not parent_dir.exists():
            continue
        for entry in sorted(parent_dir.iterdir(), key=lambda item: item.name):
            checked += 1
            if entry.name not in allowed_entries:
                report.add_issue(
                    "FL003",
                    f"{parent_name}/{entry.name}",
                    f"first-level entry is not allowed under {parent_name}/",
                )
    report.add_info(f"checked {checked} first-level entries under product/, docs/, and toolchain/")


def check_codex_layer(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport, rules: FolderRules) -> None:
    codex_dir = repo_root / ".codex"
    if not codex_dir.exists():
        report.add_info("checked .codex execution config layer: directory not present")
        return
    if not codex_dir.is_dir():
        report.add_issue("FL015", ".codex", "execution config layer must be a directory when present")
        return

    checked = 0
    entries = {entry.name: entry for entry in codex_dir.iterdir()}
    for name in sorted(entries):
        checked += 1
        if name not in CODEX_ALLOWED_ENTRIES:
            issue_code = "FL016" if is_tracked_path(f".codex/{name}", tracked_paths) else "FL015"
            report.add_issue(issue_code, f".codex/{name}", ".codex only allows config.toml and rules/")

    config_path = codex_dir / "config.toml"
    if not config_path.exists():
        report.add_issue("FL015", ".codex/config.toml", "execution config layer must provide config.toml")
    elif not config_path.is_file():
        report.add_issue("FL015", ".codex/config.toml", "execution config layer config.toml must be a file")

    rules_dir = codex_dir / "rules"
    if not rules_dir.exists():
        report.add_issue("FL015", ".codex/rules", "execution config layer must provide rules/")
    elif not rules_dir.is_dir():
        report.add_issue("FL015", ".codex/rules", "execution config layer rules/ must be a directory")
    else:
        rule_entries = {entry.name: entry for entry in rules_dir.iterdir()}
        for name in sorted(rule_entries):
            checked += 1
            if name not in CODEX_RULES_ALLOWED_ENTRIES:
                issue_code = "FL016" if is_tracked_path(f".codex/rules/{name}", tracked_paths) else "FL015"
                report.add_issue(issue_code, f".codex/rules/{name}", "rules/ only allows repo.rules")
        repo_rules = rules_dir / "repo.rules"
        if not repo_rules.exists():
            report.add_issue("FL015", ".codex/rules/repo.rules", "execution config layer must provide repo.rules")
        elif not repo_rules.is_file():
            report.add_issue("FL015", ".codex/rules/repo.rules", "rules file must be a regular file")

    report.add_info(f"checked {checked} .codex entries against the execution config layer")


def check_product_patterns(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport) -> None:
    checked = 0
    for relative_path in iter_relative_paths(repo_root / "product", repo_root):
        checked += 1
        if is_untracked_ignored_path(repo_root, relative_path, tracked_paths):
            continue
        name = Path(relative_path).name
        if relative_path == "product/.servo_template" or relative_path.startswith("product/.servo_template/"):
            continue
        if path_has_segment(relative_path, PRODUCT_BANNED_SEGMENTS):
            report.add_issue("FL004", relative_path, "product/ must not contain runbook, cache, log, or state directories")
            continue
        if "runbook" in name.casefold():
            report.add_issue("FL004", relative_path, "product/ must not contain runbook documents or helper files")
            continue
        if name in PRODUCT_STATE_FILENAMES or name.endswith((".log", ".pyc", ".pyo")):
            report.add_issue("FL004", relative_path, "product/ must not contain runtime, state, log, or bytecode files")
    report.add_info(f"checked {checked} product/ paths for misplaced runtime content")


def check_docs_patterns(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport) -> None:
    checked = 0
    for relative_path in iter_relative_paths(repo_root / "docs", repo_root):
        checked += 1
        if is_untracked_ignored_path(repo_root, relative_path, tracked_paths):
            continue
        absolute_path = repo_root / relative_path
        name = absolute_path.name
        if path_has_segment(relative_path, DOCS_BANNED_SEGMENTS):
            report.add_issue("FL005", relative_path, "docs/ must not contain cache, build, or runtime directories")
            continue
        if name in GENERIC_RUNTIME_FILENAMES or name.endswith((".log", ".pyc", ".pyo")):
            report.add_issue("FL005", relative_path, "docs/ must not contain runtime artifact, log, or bytecode files")
            continue
        if path_has_suffix(relative_path, DOCS_SCRIPT_SUFFIXES):
            report.add_issue("FL005", relative_path, "docs/ must not contain script source files")
            continue
        if path_is_executable(absolute_path) and absolute_path.suffix != ".md":
            report.add_issue("FL005", relative_path, "docs/ must not contain executable files")
    report.add_info(f"checked {checked} docs/ paths for misplaced scripts and runtime content")


def check_toolchain_patterns(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport) -> None:
    checked = 0
    for relative_path in iter_relative_paths(repo_root / "toolchain", repo_root):
        checked += 1
        if is_untracked_ignored_path(repo_root, relative_path, tracked_paths):
            continue
        name = Path(relative_path).name
        if path_has_segment(relative_path, TOOLCHAIN_BANNED_SEGMENTS):
            report.add_issue(
                "FL006",
                relative_path,
                "toolchain/ must not contain canonical source roots, repo-local mount content, caches, or state layers",
            )
            continue
        if name in GENERIC_RUNTIME_FILENAMES or name.endswith((".log", ".pyc", ".pyo")):
            report.add_issue("FL006", relative_path, "toolchain/ must not contain runtime logs, state files, or bytecode caches")
    report.add_info(f"checked {checked} toolchain/ paths for misplaced canonical or runtime content")


def check_tools_patterns(repo_root: Path, tracked_paths: set[str], report: FolderLogicReport) -> None:
    checked = 0
    for relative_path in iter_relative_paths(repo_root / "tools", repo_root):
        checked += 1
        if is_untracked_ignored_path(repo_root, relative_path, tracked_paths):
            continue
        name = Path(relative_path).name
        if name in {"__pycache__", ".pytest_cache", ".ruff_cache"} or name.endswith((".pyc", ".pyo")):
            report.add_issue("FL014", relative_path, "tools/ must not contain runtime cache content")
    report.add_info(f"checked {checked} tools/ paths for runtime cache content")


def check_tracked_exceptions(tracked_paths: set[str], report: FolderLogicReport, rules: FolderRules) -> None:
    checked = 0
    for tracked_path in sorted(tracked_paths):
        checked += 1
        if tracked_path.startswith(("tools/",)):
            if tracked_path not in rules.tools_tracked_allowlist:
                report.add_issue("FL014", tracked_path, "tools/ only allows declared compatibility shims")
            continue
        if tracked_path.startswith(".codex/"):
            if tracked_path not in rules.codex_tracked_allowlist:
                report.add_issue("FL016", tracked_path, ".codex/ only allows the explicit tracked whitelist")
            continue
        if tracked_path.startswith(MOUNT_LAYER_PREFIXES + RUNTIME_STATE_LAYER_PREFIXES):
            report.add_issue(
                "FL007",
                tracked_path,
                "repo-local runtime/install/mount layers must not contain tracked content",
            )
            continue
    report.add_info(f"checked {checked} tracked paths for hidden-layer exceptions")


def validate_nav_target(slot_name: str, target_relative: str | None) -> bool:
    return target_relative == NAV_SLOT_TARGETS.get(slot_name)


def check_nav_layer(repo_root: Path, report: FolderLogicReport) -> None:
    nav_dir = repo_root / ".nav"
    if not nav_dir.exists():
        report.add_info("checked .nav compatibility slots: directory not present")
        return

    checked = 0
    entries = {entry.name: entry for entry in nav_dir.iterdir()}
    for name in sorted(entries):
        checked += 1
        if name not in NAV_ALLOWED_ENTRIES:
            report.add_issue("FL010", f".nav/{name}", ".nav only allows README.md, @docs, and @skills")

    for slot_name in NAV_REQUIRED_SLOTS:
        slot_path = nav_dir / slot_name
        if not slot_path.exists() and not slot_path.is_symlink():
            report.add_issue("FL011", f".nav/{slot_name}", "required nav slot is missing or is not a symlink")
            continue
        if not slot_path.is_symlink():
            report.add_issue("FL011", f".nav/{slot_name}", "nav slot must be a symlink")
            continue
        target_relative = resolve_repo_relative_target(slot_path, repo_root)
        if not validate_nav_target(slot_name, target_relative):
            report.add_issue("FL012", f".nav/{slot_name}", "nav symlink target resolves outside the allowed target set")
    report.add_info(f"checked {checked} .nav entries and required compatibility slots")


def run_checks(repo_root: Path, rules: FolderRules | None = None) -> FolderLogicReport:
    effective_rules = rules or FolderRules()
    report = FolderLogicReport()
    try:
        tracked_paths = collect_tracked_paths(repo_root)
    except RuntimeError as exc:
        report.add_issue("FL000", ".", f"unable to read git tracked state: {exc}")
        return report

    check_root_allowlist(repo_root, tracked_paths, report, effective_rules)
    check_first_level_allowlist(repo_root, report, effective_rules)
    check_codex_layer(repo_root, tracked_paths, report, effective_rules)
    check_product_patterns(repo_root, tracked_paths, report)
    check_docs_patterns(repo_root, tracked_paths, report)
    check_toolchain_patterns(repo_root, tracked_paths, report)
    check_tools_patterns(repo_root, tracked_paths, report)
    check_tracked_exceptions(tracked_paths, report, effective_rules)
    check_nav_layer(repo_root, report)
    return report


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    report = run_checks(repo_root)
    payload = {
        "passed": not report.issues,
        "failures": report.failures,
        "infos": report.infos,
        "issues": [issue.__dict__ for issue in report.issues],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for info in report.infos:
            print(f"info: {info}")
        if report.issues:
            for failure in report.failures:
                print(f"failure: {failure}")
        else:
            print("folder logic checks passed")
    return 0 if not report.issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
