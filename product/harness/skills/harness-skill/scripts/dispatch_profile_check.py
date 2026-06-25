#!/usr/bin/env python3
"""Dispatch Profile Check — 验证 runtime_dispatch_profile 字段完整性。

检查 dispatch result 是否包含所有 10 个必填字段。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/dispatch_profile_check.py \\
    --profile-json '{"backend_runtime":"...","model_family":"...",...}'

输出: JSON (complete, missing_fields, checked_fields)
"""

import argparse
import json
import sys

REQUIRED_FIELDS = [
    "backend_runtime",
    "model_family",
    "subagent_dispatch_shell",
    "runtime_supports_subagent",
    "subagent_permission_state",
    "permission_allows_delegation",
    "dispatch_package_safety",
    "delegation_attempted",
    "attempted_carrier",
    "carrier_decision",
    "fallback_reason",
]


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch Profile Check"
    )
    parser.add_argument(
        "--profile-json", required=True,
        help="JSON string of runtime_dispatch_profile"
    )
    args = parser.parse_args()

    try:
        profile = json.loads(args.profile_json)
    except json.JSONDecodeError as e:
        result = {
            "complete": False,
            "missing_fields": REQUIRED_FIELDS,
            "checked_fields": {},
            "reason": f"JSON 解析失败: {e}",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    if not isinstance(profile, dict):
        result = {
            "complete": False,
            "missing_fields": REQUIRED_FIELDS,
            "checked_fields": {},
            "reason": "输入不是有效的 JSON object",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    missing = []
    checked = {}
    for field in REQUIRED_FIELDS:
        val = profile.get(field)
        checked[field] = "present" if val is not None else "missing"
        if val is None:
            missing.append(field)

    if not missing:
        result = {
            "complete": True,
            "missing_fields": [],
            "checked_fields": checked,
            "reason": "所有 runtime_dispatch_profile 字段已填充",
        }
    else:
        result = {
            "complete": False,
            "missing_fields": missing,
            "checked_fields": checked,
            "reason": (
                f"缺少 {len(missing)} 个必填字段: {', '.join(missing)}"
            ),
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()
