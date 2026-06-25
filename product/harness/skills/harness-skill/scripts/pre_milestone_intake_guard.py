#!/usr/bin/env python3
"""Pre-Milestone Intake Guard — 检查 intake review 是否满足放行条件。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/pre_milestone_intake_guard.py \\
    --intake-review .servo/repo/pre-milestone-intake-{id}.md

输出: JSON (ready, blocked, reason, required_action, intake_status, checked_fields)
"""

import argparse
import json
import os
import re
import sys

from _guard_utils import parse_yaml_field, parse_bool_field


def main():
    parser = argparse.ArgumentParser(
        description="Pre-Milestone Intake Guard"
    )
    parser.add_argument(
        "--intake-review", required=True,
        help="Path to pre_milestone_intake_review (.md)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.intake_review):
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_review_missing: pre_milestone_intake_review 文件不存在",
            "required_action": "route_to_pre_milestone_intake_skill",
            "intake_status": "missing",
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    with open(args.intake_review) as f:
        content = f.read()

    # 定位 Intake Status YAML 块（兼容 \\r\\n）
    yaml_match = re.search(
        r"```yaml\s*\r?\n(.*?)```",
        content,
        re.DOTALL,
    )
    if not yaml_match:
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_review 中未找到结构化 YAML 块",
            "required_action": "route_to_pre_milestone_intake_skill",
            "intake_status": "unparseable",
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    yaml_block = yaml_match.group(1)

    intake_status = parse_yaml_field(yaml_block, "intake_status")
    programmer_confirmed = parse_bool_field(yaml_block, "programmer_confirmed")
    ready_for_init_milestone = parse_bool_field(
        yaml_block, "ready_for_init_milestone"
    )
    intake_skipped = parse_bool_field(yaml_block, "intake_skipped")

    checked = {
        "intake_status": intake_status,
        "programmer_confirmed": programmer_confirmed,
        "ready_for_init_milestone": ready_for_init_milestone,
        "intake_skipped": intake_skipped,
    }

    # ── 判定逻辑 ──
    if intake_status == "ready":
        if (
            programmer_confirmed is True
            and ready_for_init_milestone is True
            and intake_skipped is False
        ):
            result = {
                "ready": True,
                "blocked": False,
                "reason": "intake review 满足 ready 放行条件",
                "required_action": "proceed_to_init_milestone",
                "intake_status": "ready",
                "checked_fields": checked,
            }
        else:
            result = {
                "ready": False,
                "blocked": True,
                "reason": (
                    f"intake_status=ready 但字段不完整: "
                    f"programmer_confirmed={programmer_confirmed}, "
                    f"ready_for_init_milestone={ready_for_init_milestone}, "
                    f"intake_skipped={intake_skipped}"
                ),
                "required_action": "return_to_pre_milestone_intake_skill",
                "intake_status": intake_status,
                "checked_fields": checked,
            }

    elif intake_status == "skipped":
        if intake_skipped is True:
            result = {
                "ready": True,
                "blocked": False,
                "reason": "intake skipped 且 programmer 显式接受风险，允许继续",
                "required_action": "proceed_with_risk_record",
                "intake_status": "skipped",
                "checked_fields": checked,
            }
        else:
            result = {
                "ready": False,
                "blocked": True,
                "reason": "intake_status=skipped 但 intake_skipped 字段不匹配",
                "required_action": "return_to_pre_milestone_intake_skill",
                "intake_status": intake_status,
                "checked_fields": checked,
            }

    elif intake_status == "questions_required":
        result = {
            "ready": False,
            "blocked": True,
            "reason": (
                "intake_status=questions_required，"
                "需继续 continuous intake 直到 ready"
            ),
            "required_action": "return_to_pre_milestone_intake_skill",
            "intake_status": "questions_required",
            "checked_fields": checked,
        }

    elif intake_status == "blocked":
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_status=blocked，Milestone 初始化被阻断",
            "required_action": "handback_to_programmer",
            "intake_status": "blocked",
            "checked_fields": checked,
        }

    elif not intake_status:
        result = {
            "ready": False,
            "blocked": True,
            "reason": "intake_status 字段缺失或为空",
            "required_action": "route_to_pre_milestone_intake_skill",
            "intake_status": "missing",
            "checked_fields": checked,
        }

    else:
        result = {
            "ready": False,
            "blocked": True,
            "reason": f"未知的 intake_status: {intake_status}，保守阻断",
            "required_action": "handback_to_programmer",
            "intake_status": intake_status,
            "checked_fields": checked,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
