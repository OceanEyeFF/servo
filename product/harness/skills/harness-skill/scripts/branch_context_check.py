#!/usr/bin/env python3
"""Branch Context Guard — 分支环境检查器。

检查当前 git branch 是否匹配 control-state / Worktrack Contract 预期的上下文。
Harness 在状态估计阶段（§10.1 步骤 3）调用此脚本。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/branch_context_check.py \\
    --control-state .servo/control-state.md \\
    [--worktrack-contract .servo/worktrack/contract.md] \\
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
            state["baseline_branch"] = line.split(":", 1)[1].strip()
        elif line.startswith("- active_milestone_branch:"):
            val = line.split(":", 1)[1].strip()
            if val and val != "none":
                state["active_milestone_branch"] = val
        elif line.startswith("- latest_observed_checkpoint:"):
            state["latest_observed_checkpoint"] = line.split(":", 1)[1].strip()

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


def parse_worktrack_contract(path: str) -> dict:
    """从 Worktrack Contract 提取分支相关字段。"""
    contract = {
        "worktrack_branch": "",
        "closeout_target_ref": "",
        "branch_source_ref": "",
        "checkpoint_base_ref": "",
    }
    if not path or not os.path.exists(path):
        return contract

    with open(path, "r") as f:
        content = f.read()

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- worktrack_branch:"):
            contract["worktrack_branch"] = line.split(":", 1)[1].strip()
        elif line.startswith("- closeout_target_ref:"):
            contract["closeout_target_ref"] = line.split(":", 1)[1].strip()
        elif line.startswith("- branch_source_ref:"):
            contract["branch_source_ref"] = line.split(":", 1)[1].strip()
        elif line.startswith("- checkpoint_base_ref:"):
            contract["checkpoint_base_ref"] = line.split(":", 1)[1].strip()

    return contract


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
    contract: dict,
) -> dict:
    """根据 Scope/Function 检查分支上下文是否合法。"""
    result = {
        "current_branch": git_branch_current(),
        "branch_context": branch_context,
        "expected_contexts": [],
        "legal": True,
        "blocked": False,
        "warning": None,
        "target_branch": None,
        "reason": "",
    }

    baseline = control["baseline_branch"]
    milestone = control["active_milestone_branch"]
    worktrack = contract.get("worktrack_branch", "")
    closeout_target = contract.get("closeout_target_ref", "")

    # ── 构建允许的上下文列表 → 同时用于 expected_contexts 和准入检查 ──
    allowed = []

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
            if closeout_target:
                allowed = [closeout_target]
            else:
                allowed = [b for b in (milestone, baseline) if b]
            if branch_context not in allowed:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = allowed[0] if allowed else baseline
                result["reason"] = (
                    "RepoScope.Refresh 必须在 "
                    + " / ".join(allowed)
                    + f" 上执行，当前在 {branch_context}"
                )
            else:
                result["reason"] = "RepoScope.Refresh 上下文合法"

    elif scope == "WorktrackScope":
        if function == "Init":
            if milestone:
                allowed = ["milestone"]
            else:
                allowed = ["baseline"]
            if branch_context not in allowed:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = allowed[0]
                result["reason"] = (
                    f"WorktrackScope.Init 必须在 {allowed[0]} 上执行，"
                    f"当前在 {branch_context}"
                )
            else:
                result["reason"] = f"WorktrackScope.Init 在 {allowed[0]} 上执行，合法"

        elif function in ("Dispatch", "Verify", "Judge"):
            allowed = ["worktrack"]
            if branch_context not in allowed:
                if function == "Verify":
                    result["warning"] = (
                        "Verify 只读 evidence collection 可在不匹配上下文继续，"
                        "但不得修改非合同 worktrack branch"
                    )
                    result["reason"] = "Verify 只读，记录 warning"
                else:
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
            if closeout_target:
                allowed.append(closeout_target)
            else:
                if milestone:
                    allowed.append(milestone)
                allowed.append(baseline)
            if branch_context not in allowed:
                result["legal"] = False
                result["blocked"] = True
                result["target_branch"] = closeout_target or milestone or baseline
                result["reason"] = (
                    "WorktrackScope.Close 需要 "
                    + " / ".join(allowed)
                    + f" 上下文，当前在 {branch_context}"
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

    if result["blocked"]:
        result["legal"] = False

    return result


def main():
    parser = argparse.ArgumentParser(description="Branch Context Guard")
    parser.add_argument(
        "--control-state", required=True, help="Path to .servo/control-state.md"
    )
    parser.add_argument(
        "--worktrack-contract",
        default=None,
        help="Path to .servo/worktrack/contract.md",
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
    contract = parse_worktrack_contract(args.worktrack_contract)

    branch_context = classify_branch_context(
        current,
        control["baseline_branch"],
        control["active_milestone_branch"],
        contract.get("worktrack_branch", ""),
    )

    result = check_context(args.scope, args.function, branch_context, control, contract)
    result["head_hash"] = git_rev_parse_head()
    result["config_hydration_gaps"] = control["config_hydration_gaps"]

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1 if result["blocked"] else 0)


if __name__ == "__main__":
    main()
