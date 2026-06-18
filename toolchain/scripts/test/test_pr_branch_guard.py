from __future__ import annotations

from toolchain.scripts.test.pr_branch_guard import evaluate_pr_branch


def test_allows_canonical_develop_into_master() -> None:
    ok, message = evaluate_pr_branch(
        base_ref="master",
        head_ref="develop",
        base_repo="OceanEyeFF/servo",
        head_repo="OceanEyeFF/servo",
        protected_base="master",
        allowed_head="develop",
    )

    assert ok
    assert "passed" in message


def test_blocks_worktrack_branch_into_master() -> None:
    ok, message = evaluate_pr_branch(
        base_ref="master",
        head_ref="wt-20260617-v061-stable-post-publish-sync",
        base_repo="OceanEyeFF/servo",
        head_repo="OceanEyeFF/servo",
        protected_base="master",
        allowed_head="develop",
    )

    assert not ok
    assert "must use head branch 'develop'" in message


def test_blocks_fork_develop_into_master() -> None:
    ok, message = evaluate_pr_branch(
        base_ref="master",
        head_ref="develop",
        base_repo="OceanEyeFF/servo",
        head_repo="contributor/servo",
        protected_base="master",
        allowed_head="develop",
    )

    assert not ok
    assert "canonical repo" in message


def test_skips_non_protected_base() -> None:
    ok, message = evaluate_pr_branch(
        base_ref="develop",
        head_ref="wt-docs",
        base_repo="OceanEyeFF/servo",
        head_repo="OceanEyeFF/servo",
        protected_base="master",
        allowed_head="develop",
    )

    assert ok
    assert "skipped" in message
