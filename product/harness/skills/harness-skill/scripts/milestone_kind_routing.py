#!/usr/bin/env python3
"""Milestone Kind Routing Check — work-collection vs goal-driven 路由差异判定。

检查 active milestone 的 milestone_kind，决定 handback 行为和 pipeline 推进策略。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/milestone_kind_routing.py \\
    --milestone .servo/milestone/{id}.md

输出: JSON (milestone_kind, ready, handback_required, auto_advance, blocked, reason)
"""

import argparse
import json
import os
import sys

from _guard_utils import parse_yaml_field


def parse_milestone_kind(path: str) -> str:
    """从 milestone artifact 读取 milestone_kind。"""
    if not path or not os.path.exists(path):
        return ""
    with open(path) as f:
        content = f.read()
    return parse_yaml_field(content, "milestone_kind")


def main():
    parser = argparse.ArgumentParser(
        description="Milestone Kind Routing Check"
    )
    parser.add_argument(
        "--milestone", required=True,
        help="Path to .servo/milestone/{id}.md"
    )
    args = parser.parse_args()

    if not os.path.exists(args.milestone):
        result = {
            "milestone_kind": "unknown",
            "ready": False,
            "handback_required": None,
            "auto_advance": False,
            "blocked": True,
            "reason": "milestone 文件不存在",
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    kind = parse_milestone_kind(args.milestone)

    if not kind:
        result = {
            "milestone_kind": "unknown",
            "ready": False,
            "handback_required": None,
            "auto_advance": False,
            "blocked": True,
            "reason": "milestone_kind 字段缺失或无法解析",
            "checked_fields": {"milestone_kind": ""},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    if kind == "work-collection":
        result = {
            "milestone_kind": "work-collection",
            "ready": True,
            "handback_required": False,
            "auto_advance": True,
            "blocked": False,
            "reason": (
                "work-collection milestone: achieved 后不触发 handback，"
                "自动推进 pipeline"
            ),
            "checked_fields": {"milestone_kind": kind},
        }
    elif kind == "goal-driven":
        result = {
            "milestone_kind": "goal-driven",
            "ready": True,
            "handback_required": True,
            "auto_advance": False,
            "blocked": False,
            "reason": (
                "goal-driven milestone: achieved 后触发 handback，"
                "等待 programmer 最终验收"
            ),
            "checked_fields": {"milestone_kind": kind},
        }
    else:
        result = {
            "milestone_kind": kind,
            "ready": False,
            "handback_required": None,
            "auto_advance": False,
            "blocked": True,
            "reason": f"未知的 milestone_kind: {kind}，保守阻断",
            "checked_fields": {"milestone_kind": kind},
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if not result["blocked"] else 1)


if __name__ == "__main__":
    main()
