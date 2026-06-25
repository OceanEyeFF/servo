#!/usr/bin/env python3
"""Worktrack Intake Review Check — 检查 worktrack_intake_review 是否满足放行条件。

检查 7 个必填字段存在性 + intake_review_verdict + ready_for_worktrack_init。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/worktrack_intake_review_check.py \\
    --intake-review .servo/repo/worktrack-intake-{id}.md

输出: JSON (ready, blocked, reason, missing_fields, required_action, checked_fields)
"""

import argparse
import json
import os
import sys

from _guard_utils import parse_yaml_field, parse_bool_field, field_present


REQUIRED_FIELDS = [
    "repo_fundamentals",
    "snapshot_freshness",
    "milestone_purpose_alignment",
    "historical_conflict_risk",
    "worktrack_adjustment_recommendations",
    "add_remove_worktrack_recommendations",
]


def main():
    parser = argparse.ArgumentParser(
        description="Worktrack Intake Review Check"
    )
    parser.add_argument(
        "--intake-review", required=True,
        help="Path to worktrack_intake_review (.md)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.intake_review):
        result = {
            "ready": False,
            "blocked": True,
            "reason": "worktrack_intake_review 文件不存在",
            "required_action": "route_to_repo_whats_next_for_intake",
            "missing_fields": ["intake_review_file"],
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    with open(args.intake_review) as f:
        content = f.read()

    # ── 检查 7 个必填字段 ──
    missing = []
    for field in REQUIRED_FIELDS:
        if not field_present(content, field):
            missing.append(field)

    # ── 检查 verdict 和 ready 布尔值 ──
    verdict = parse_yaml_field(content, "intake_review_verdict")
    ready_bool = parse_bool_field(content, "ready_for_worktrack_init")

    checked = {
        "intake_review_verdict": verdict,
        "ready_for_worktrack_init": ready_bool,
        "required_fields_missing": missing,
    }

    # ── 判定逻辑 ──
    if verdict == "blocked":
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_review_verdict=blocked，Worktrack 初始化被阻断",
            "required_action": "handback_to_programmer",
            "missing_fields": missing,
            "checked_fields": checked,
        }
    elif verdict == "refresh_required":
        result = {
            "ready": False,
            "blocked": True,
            "reason": (
                "intake_review_verdict=refresh_required，需先刷新 Repo 基线"
            ),
            "required_action": "route_to_repo_refresh",
            "missing_fields": missing,
            "checked_fields": checked,
        }
    elif verdict == "adjust_worktracks":
        result = {
            "ready": False,
            "blocked": True,
            "reason": (
                "intake_review_verdict=adjust_worktracks，"
                "需调整 Worktrack 列表"
            ),
            "required_action": "route_to_milestone_backlog_adjustment",
            "missing_fields": missing,
            "checked_fields": checked,
        }
    elif verdict == "ready_for_worktrack_init":
        if missing:
            result = {
                "ready": False,
                "blocked": True,
                "reason": (
                    f"verdict=ready_for_worktrack_init 但缺少必填字段: "
                    f"{', '.join(missing)}"
                ),
                "required_action": (
                    "return_to_repo_whats_next_for_completion"
                ),
                "missing_fields": missing,
                "checked_fields": checked,
            }
        elif ready_bool is not True:
            result = {
                "ready": False,
                "blocked": True,
                "reason": (
                    "verdict=ready_for_worktrack_init 但 "
                    f"ready_for_worktrack_init={ready_bool}"
                ),
                "required_action": (
                    "return_to_repo_whats_next_for_completion"
                ),
                "missing_fields": missing,
                "checked_fields": checked,
            }
        else:
            result = {
                "ready": True,
                "blocked": False,
                "reason": "Worktrack intake review 满足所有放行条件",
                "required_action": "proceed_to_init_worktrack",
                "missing_fields": [],
                "checked_fields": checked,
            }
    elif not verdict:
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_review_verdict 字段缺失",
            "required_action": "route_to_repo_whats_next_for_intake",
            "missing_fields": missing + ["intake_review_verdict"],
            "checked_fields": checked,
        }
    else:
        result = {
            "ready": False,
            "blocked": True,
            "reason": f"未知的 intake_review_verdict: {verdict}，保守阻断",
            "required_action": "handback_to_programmer",
            "missing_fields": missing,
            "checked_fields": checked,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
