"""Shared git utilities for harness-skill scripts.

Usage:
    from _git_utils import git_rev_parse_head, git_branch_current
"""

import subprocess


def git_branch_current() -> str:
    """Return the currently checked-out branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, check=True,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def git_rev_parse_head() -> str:
    """Return the current HEAD commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""
