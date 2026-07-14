#!/usr/bin/env python3
"""Branch Context Guard — 分支环境检查器。

检查当前 git branch 是否匹配 control-state 与 Candidate Worktrack 预期的上下文。
Harness 在状态估计阶段（§10.1 步骤 3）调用此脚本。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/branch_context_check.py \\
    --control-state .servo/control-state.md \\
    [--worktrack-id WT-example] \\
    --scope RepoScope|WorktrackScope \\
    --function Observe|Decide|Init|Dispatch|Verify|Judge|Close|Refresh|Recover

输出: JSON (status, branch_context, expected_context, blocked, warning, target_branch, reason)
"""

import argparse
import json
import os
import re
import subprocess
import sys

from _git_utils import git_branch_current, git_rev_parse_head


def git_remote_head_branch() -> str:
    """动态解析 origin/HEAD 指向的分支名。"""
    try:
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            capture_output=True, text=True, check=True,
            timeout=30,
        )
        for line in result.stdout.splitlines():
            m = re.match(r"\s*HEAD branch:\s*(.+)", line)
            if m:
                return m.group(1).strip()
    except subprocess.CalledProcessError:
        pass
    return ""


def parse_control_state(path: str) -> dict:
    """从 control-state.md 提取分支相关字段。"""
    state = {
        "baseline_branch": "",
        "active_milestone_branch": "",
        "latest_observed_checkpoint": "",
        "config_hydration_gaps": [],
    }
    if not os.path.exists(path):
        state["config_hydration_gaps"].append("control_state_missing")
        return state

    with open(path, "r") as f:
        content = f.read()

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- baseline_branch:"):
            state["baseline_branch"] = line.split(":", 1)[1].strip().strip("`\"'")
        elif line.startswith("- active_milestone_branch:"):
            val = line.split(":", 1)[1].strip().strip("`\"'")
            if val and val != "none":
                state["active_milestone_branch"] = val
        elif line.startswith("- latest_observed_checkpoint:"):
            state["latest_observed_checkpoint"] = (
                line.split(":", 1)[1].strip().strip("`\"'")
            )

    # 缺失 baseline_branch → 动态解析
    if not state["baseline_branch"]:
        resolved = git_remote_head_branch()
        if resolved:
            state["baseline_branch"] = resolved
        else:
            state["baseline_branch"] = "develop"  # 最终 fallback
        state["config_hydration_gaps"].append(
            f"baseline_branch_missing_resolved_to_{state['baseline_branch']}"
        )

    return state


def derive_worktrack_branch(worktrack_id: str) -> tuple[str, str]:
    """Derive and validate the only Candidate Worktrack branch."""
    if not worktrack_id:
        return "", "worktrack_id is required for WorktrackScope"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", worktrack_id):
        return "", "worktrack_id contains unsupported characters"

    branch = f"wt/{worktrack_id}"
    completed = subprocess.run(
        ["git", "check-ref-format", "--branch", branch],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "", f"derived Worktrack branch is not a valid Git ref: {branch}"
    return branch, ""


def classify_branch_context(
    current: str, baseline: str, milestone: str, worktrack: str
) -> str:
    """将当前分支分类为 baseline / milestone / worktrack / unknown。"""
    if current == baseline:
        return "baseline"
    if milestone and current == milestone:
        return "milestone"
    if worktrack and current == worktrack:
        return "worktrack"
    return "unknown"


def check_context(
    scope: str,
    function: str,
    branch_context: str,
    control: dict,
    worktrack: str,
) -> dict:
    """根据 Scope/Function 检查分支上下文是否合法。"""
    result = {
        "current_branch": git_branch_current(),
        "branch_context": branch_context,
        "expected_contexts": [],
        "expected_branches": [],
        "legal": True,
        "blocked": False,
        "warning": None,
        "target_branch": None,
        "reason": "",
    }

    baseline = control["baseline_branch"]
    milestone = control["active_milestone_branch"]
    # Context labels (baseline/milestone/worktrack) and concrete branch refs are
    # intentionally separate: a label must never be compared with a branch name.
    allowed = []
    allowed_branches = []

    if scope == "RepoScope":
        if function in ("Observe", "Decide"):
            allowed = ["baseline", "milestone"]
            if branch_context not in allowed:
                result["warning"] = (
                    f"branch_context_warning: current={result['current_branch']}, "
                    f"context={branch_context}. Observe/Decide 可在任意上下文继续，"
                    f"但修改状态前需切换到 baseline 或 milestone"
                )
                result["target_branch"] = baseline
            result["reason"] = (
                "RepoScope.Observe/Decide 只读，允许不匹配上下文但需记录 warning"
            )

        elif function == "Init":
            allowed = ["baseline"]
            if branch_context not in allowed:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = baseline
                result["reason"] = (
                    f"RepoScope.Init 必须在 baseline ({baseline}) 上执行，"
                    f"当前在 {branch_context}"
                )
            else:
                result["reason"] = "RepoScope.Init 在 baseline 上执行，合法"

        elif function == "Refresh":
            if worktrack and milestone:
                allowed_branches = [milestone]
            else:
                allowed_branches = [b for b in (milestone, baseline) if b]
            if result["current_branch"] not in allowed_branches:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = (
                    allowed_branches[0] if allowed_branches else baseline
                )
                result["reason"] = (
                    "RepoScope.Refresh 必须在 "
                    + " / ".join(allowed_branches)
                    + f" 上执行，当前在 {result['current_branch']} ({branch_context})"
                )
            else:
                result["reason"] = "RepoScope.Refresh 上下文合法"

    elif scope == "WorktrackScope":
        if function == "Init":
            expected_branch = milestone or baseline
            allowed = ["milestone"] if milestone else ["baseline"]
            allowed_branches = [expected_branch]
            if result["current_branch"] != expected_branch:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = expected_branch
                result["reason"] = (
                    f"WorktrackScope.Init 必须在 {expected_branch} 上执行，"
                    f"当前在 {result['current_branch']}"
                )
            else:
                result["reason"] = (
                    f"WorktrackScope.Init 在 {expected_branch} 上执行，合法"
                )

        elif function in ("Dispatch", "Verify", "Judge"):
            allowed = ["worktrack"]
            if branch_context not in allowed:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = worktrack or "unknown"
                result["reason"] = (
                    f"WorktrackScope.{function} 必须在 worktrack branch 上执行，"
                    f"当前在 {branch_context}"
                )
            else:
                result["reason"] = (
                    f"WorktrackScope.{function} 在 worktrack 上执行，合法"
                )

        elif function == "Close":
            allowed = ["worktrack"]
            allowed_branches = [b for b in (worktrack, milestone) if b]
            if (
                branch_context not in allowed
                and result["current_branch"] not in allowed_branches
            ):
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = milestone or baseline
                result["reason"] = (
                    "WorktrackScope.Close 需要 "
                    + " / ".join(allowed_branches or allowed)
                    + f" 上执行，当前在 {result['current_branch']} ({branch_context})"
                )
            else:
                result["reason"] = "WorktrackScope.Close 上下文合法"

        elif function in ("Observe", "Decide"):
            allowed = ["worktrack"]
            if branch_context not in allowed:
                result["warning"] = (
                    f"WorktrackScope.{function} 应在 worktrack branch 上执行，"
                    f"当前在 {branch_context}"
                )
            result["reason"] = (
                f"WorktrackScope.{function} 在 worktrack 上更佳，不匹配仅记录 warning"
            )

        elif function == "Recover":
            allowed = ["worktrack"]
            if branch_context not in allowed:
                result["warning"] = (
                    f"Recover 应在 worktrack branch 上执行，当前在 {branch_context}。"
                    f"作为恢复路径继续，但恢复结果应用于正确的 worktrack branch"
                )
            result["reason"] = "Recover 在 worktrack 上执行"

    result["expected_contexts"] = allowed
    result["expected_branches"] = allowed_branches

    if result["blocked"]:
        result["legal"] = False

    return result


def main():
    parser = argparse.ArgumentParser(description="Branch Context Guard")
    parser.add_argument(
        "--control-state", required=True, help="Path to .servo/control-state.md"
    )
    parser.add_argument(
        "--worktrack-id",
        default="",
        help="Candidate Worktrack id used to derive wt/<worktrack-id>",
    )
    parser.add_argument(
        "--scope", required=True, choices=["RepoScope", "WorktrackScope"]
    )
    parser.add_argument(
        "--function",
        required=True,
        choices=[
            "Observe",
            "Decide",
            "Init",
            "Dispatch",
            "Verify",
            "Judge",
            "Close",
            "Refresh",
            "Recover",
        ],
    )
    args = parser.parse_args()

    current = git_branch_current()
    control = parse_control_state(args.control_state)
    worktrack, worktrack_error = derive_worktrack_branch(args.worktrack_id)

    if worktrack_error and (args.scope == "WorktrackScope" or args.worktrack_id):
        result = {
            "current_branch": current,
            "branch_context": "unknown",
            "expected_contexts": [],
            "expected_branches": [],
            "legal": False,
            "blocked": True,
            "warning": None,
            "target_branch": control["active_milestone_branch"] or None,
            "reason": worktrack_error,
            "worktrack_id": args.worktrack_id,
            "derived_worktrack_branch": "",
            "active_milestone_branch": control["active_milestone_branch"],
            "head_hash": git_rev_parse_head(),
            "config_hydration_gaps": control["config_hydration_gaps"],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    branch_context = classify_branch_context(
        current,
        control["baseline_branch"],
        control["active_milestone_branch"],
        worktrack,
    )

    result = check_context(args.scope, args.function, branch_context, control, worktrack)
    result["worktrack_id"] = args.worktrack_id
    result["derived_worktrack_branch"] = worktrack
    result["active_milestone_branch"] = control["active_milestone_branch"]
    result["head_hash"] = git_rev_parse_head()
    result["config_hydration_gaps"] = control["config_hydration_gaps"]

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1 if result["blocked"] else 0)


if __name__ == "__main__":
    main()
