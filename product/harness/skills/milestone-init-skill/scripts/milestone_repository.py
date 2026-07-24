#!/usr/bin/env python3
"""Repository, path, and Git branch contracts for Milestone Init."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, NoReturn


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_STABLE_REF_BYTES = 2 * 1024 * 1024


class RepositoryError(Exception):
    """A deterministic repository or branch failure with located details."""

    def __init__(self, code: str, message: str | None = None, **details: Any) -> None:
        message = message or code.replace("_", " ")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def fail(code: str, message: str | None = None, **details: Any) -> NoReturn:
    raise RepositoryError(code, message, **details)


def require(predicate: object, code: str, message: str | None = None, **details: Any) -> None:
    if not predicate:
        fail(code, message, **details)


@dataclass(frozen=True)
class GitContract:
    source_branch: str
    baseline: str


@dataclass(frozen=True)
class BranchResolution:
    outcome: str
    created: bool
    baseline: str


def run_git(
    repo_root: Path, arguments: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    require(
        not check or completed.returncode == 0,
        "git_error",
        arguments=arguments,
        stderr=completed.stderr.strip(),
    )
    return completed


def ensure_safe_repo_root(value: str) -> Path:
    try:
        repo_root = Path(value).resolve(strict=True)
    except OSError:
        fail("invalid_repo_root", "repo root does not exist")
    require(repo_root.is_dir() and (repo_root / ".git").exists(), "invalid_repo_root")
    return repo_root


def ensure_safe_milestone_dir(repo_root: Path) -> Path:
    servo_dir = repo_root / ".servo"
    milestone_dir = servo_dir / "milestone"
    for path in (servo_dir, milestone_dir):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            fail("missing_milestone_directory", path=str(path))
        require(
            not stat.S_ISLNK(metadata.st_mode) and stat.S_ISDIR(metadata.st_mode),
            "unsafe_milestone_directory",
            path=str(path),
        )
    require(
        milestone_dir.resolve(strict=True).parent == servo_dir.resolve(strict=True),
        "unsafe_milestone_directory",
    )
    return milestone_dir


def current_branch(repo_root: Path) -> str | None:
    completed = run_git(repo_root, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def read_branch_ref(repo_root: Path, branch: str) -> str | None:
    completed = run_git(repo_root, ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"], check=False)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value if FULL_SHA_RE.fullmatch(value) else None


def branch_descends_from(repo_root: Path, branch_commit: str, baseline: str) -> bool:
    return run_git(
        repo_root,
        ["merge-base", "--is-ancestor", baseline, branch_commit],
        check=False,
    ).returncode == 0


def validate_stable_ref_target(repo_root: Path, value: str) -> None:
    relative = value.split("#", 1)[0]
    target = repo_root.joinpath(*relative.split("/"))
    try:
        metadata = target.lstat()
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        fail("missing_stable_ref", ref=value)
    require(resolved.is_relative_to(repo_root), "unsafe_stable_ref", ref=value)
    require(not stat.S_ISLNK(metadata.st_mode) and stat.S_ISREG(metadata.st_mode), "unsafe_file_type", path=str(target))
    flags = os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
    try:
        descriptor = os.open(target, flags)
    except OSError:
        fail("unsafe_file_read", path=str(target))
    try:
        opened = os.fstat(descriptor)
        require((opened.st_dev, opened.st_ino) == (metadata.st_dev, metadata.st_ino), "unsafe_file_read", path=str(target))
        require(stat.S_ISREG(opened.st_mode), "unsafe_file_type", path=str(target))
        remaining = MAX_STABLE_REF_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
        require(remaining > 0, "document_too_large", path=str(target))
    finally:
        os.close(descriptor)


def validate_git_contract(
    repo_root: Path,
    *,
    source_branch: str,
    baseline: str,
    milestone_branch: str,
    close_target: str,
    stable_refs: Iterable[str],
) -> GitContract:
    for value in stable_refs:
        validate_stable_ref_target(repo_root, value)
    require(FULL_SHA_RE.fullmatch(baseline), "invalid_baseline_ref")
    for branch in (source_branch, milestone_branch, close_target):
        checked = run_git(repo_root, ["check-ref-format", "--branch", branch], check=False)
        require(checked.returncode == 0, "invalid_branch_name", branch=branch)
    require(source_branch != milestone_branch, "invalid_branch_contract")
    resolved = run_git(repo_root, ["rev-parse", "--verify", f"{baseline}^{{commit}}"], check=False)
    require(resolved.returncode == 0 and resolved.stdout.strip() == baseline, "missing_baseline_commit", baseline=baseline)
    source_head = read_branch_ref(repo_root, source_branch)
    require(
        source_head is not None and branch_descends_from(repo_root, source_head, baseline),
        "baseline_branch_conflict",
        source_branch=source_branch,
        baseline=baseline,
        source_head=source_head,
    )
    require(read_branch_ref(repo_root, close_target) is not None, "missing_close_target", close_target=close_target)
    return GitContract(source_branch=source_branch, baseline=baseline)


def resolve_branch_contract(
    repo_root: Path,
    *,
    milestone_branch: str,
    current_exists: bool,
    contract_changed: bool,
    baseline: str,
    mutate: bool,
    identical_replay: bool = False,
) -> BranchResolution:
    existing = read_branch_ref(repo_root, milestone_branch)
    if existing is not None:
        if not current_exists or contract_changed:
            require(existing == baseline, "branch_ref_conflict", branch=milestone_branch, expected=baseline, actual=existing)
            return BranchResolution("existing_at_baseline", False, baseline)
        require(
            branch_descends_from(repo_root, existing, baseline),
            "branch_contract_conflict",
            branch=milestone_branch,
            existing=existing,
            baseline=baseline,
        )
        outcome = "already_applied" if identical_replay else "existing_descendant"
        return BranchResolution(outcome, False, baseline)
    require(not current_exists or contract_changed, "missing_milestone_branch", branch=milestone_branch)
    if not mutate:
        return BranchResolution("would_create", False, baseline)
    require(current_branch(repo_root) != milestone_branch, "unsafe_current_branch", branch=milestone_branch)
    created = run_git(
        repo_root,
        ["update-ref", f"refs/heads/{milestone_branch}", baseline, "0" * 40],
        check=False,
    )
    require(created.returncode == 0, "branch_ref_race", branch=milestone_branch, stderr=created.stderr.strip())
    return BranchResolution("created", True, baseline)
