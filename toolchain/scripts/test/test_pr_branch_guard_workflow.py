from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-branch-guard.yml"


def test_pr_branch_guard_workflow_uses_pull_request_target_base_checkout() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pull_request_target:" in workflow
    assert "persist-credentials: false" in workflow
    assert "github.event.pull_request.base.sha" in workflow
    assert "toolchain/scripts/test/pr_branch_guard.py" in workflow
    assert re.search(r"\bcontents:\s*read\b", workflow)


def test_pr_branch_guard_workflow_enforces_develop_to_master() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--protected-base master" in workflow
    assert "--allowed-head develop" in workflow
    assert "github.event.pull_request.base.ref" in workflow
    assert "github.event.pull_request.head.ref" in workflow
    assert "github.event.pull_request.base.repo.full_name" in workflow
    assert "github.event.pull_request.head.repo.full_name" in workflow
