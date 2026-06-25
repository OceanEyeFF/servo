#!/usr/bin/env python3
"""Milestone Review Gate Check — 检查 Milestone Review Gate 是否就绪。

从 control-state.md 的 "Milestone Review Gate" 段读取字段，
判定是否允许从 active goal-driven milestone 进入 WorktrackScope.Init。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/milestone_review_gate_check.py \\
    --control-state .servo/control-state.md

输出: JSON (ready, blocked, reason, missing_fields, checked_fields)
"""

import argparse
import json
import os
import re
import sys

from _guard_utils import parse_yaml_field, parse_bool_field, parse_int_field


def main():
    parser = argparse.ArgumentParser(
        description="Milestone Review Gate Check"
    )
    parser.add_argument(
        "--control-state", required=True,
        help="Path to .servo/control-state.md"
    )
    args = parser.parse_args()

    if not os.path.exists(args.control_state):
        result = {
            "ready": False,
            "blocked": True,
            "reason": "control-state.md 不存在，无法检查 Milestone Review Gate",
            "missing_fields": ["control_state_file"],
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    with open(args.control_state) as f:
        content = f.read()

    # 定位 "Milestone Review Gate" 段（兼容 \\r\\n）
    section_match = re.search(
        r"## Milestone Review Gate\s*\r?\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not section_match:
        result = {
            "ready": False,
            "blocked": True,
            "reason": "control-state.md 中未找到 '## Milestone Review Gate' 段",
            "missing_fields": ["milestone_review_gate_section"],
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    section = section_match.group(1)

    gate_ready = parse_bool_field(section, "milestone_review_gate_ready")
    review_status = parse_yaml_field(section, "latest_review_status")
    review_count = parse_int_field(section, "milestone_review_count")
    effective_pass = parse_bool_field(section, "effective_review_pass")
    checkpoint = parse_yaml_field(section, "latest_review_checkpoint")

    # review_invalidated_by: 检查列表是否非空且不是 "none"
    invalidated_match = re.search(
        r"review_invalidated_by:\s*\r?\n((?:\s*-.*\r?\n)*)",
        section,
    )
    invalidated_text = (
        invalidated_match.group(1).strip() if invalidated_match else ""
    )
    has_invalidated = bool(
        invalidated_text and invalidated_text.lower() != "none"
    )

    checked = {
        "milestone_review_gate_ready": gate_ready,
        "latest_review_status": review_status,
        "milestone_review_count": review_count,
        "effective_review_pass": effective_pass,
        "latest_review_checkpoint": checkpoint,
        "review_invalidated_by": "present" if has_invalidated else "empty/absent",
    }

    missing = []
    if gate_ready is not True:
        missing.append("milestone_review_gate_ready != true")
    if review_status != "effective_pass":
        missing.append(
            f"latest_review_status={review_status} (need effective_pass)"
        )
    if review_count is None or review_count < 1:
        missing.append(
            f"milestone_review_count={review_count} (need >= 1)"
        )
    if effective_pass is not True:
        missing.append("effective_review_pass != true")
    if not checkpoint or checkpoint.lower() in ("none", "n/a", ""):
        missing.append("latest_review_checkpoint is empty/none")
    if has_invalidated:
        missing.append("review_invalidated_by has blocking entries")

    if missing:
        result = {
            "ready": False,
            "blocked": True,
            "reason": (
                f"Milestone Review Gate 未就绪: {', '.join(missing)}"
            ),
            "missing_fields": missing,
            "checked_fields": checked,
        }
    else:
        result = {
            "ready": True,
            "blocked": False,
            "reason": "Milestone Review Gate 就绪，所有字段通过检查",
            "missing_fields": [],
            "checked_fields": checked,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
