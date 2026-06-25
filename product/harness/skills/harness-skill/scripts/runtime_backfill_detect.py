#!/usr/bin/env python3
"""Runtime Backfill Detect — 检测 .servo artifact 中缺失的 additive 字段并计算保守默认值。

Detective 角色：检测缺失字段 → 计算保守默认值 → 记录 gaps。
Prescriptive 角色（"不得扩大权限"等行为约束）保留在 Skill 文本内。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/runtime_backfill_detect.py \\
    --artifact .servo/control-state.md \\
    [--schema-file .servo/template/control-state.md]

输出: JSON (missing_fields, backfill_values, gaps_recorded)
"""

import argparse
import json
import os
import re
import sys

from _guard_utils import parse_yaml_field

# 字段类型 → 保守默认值映射
CONSERVATIVE_DEFAULTS = {
    # 布尔字段 → false
    "milestone_review_gate_ready": False,
    "effective_review_pass": False,
    "programmer_confirmed": False,
    "ready_for_init_milestone": False,
    "intake_skipped": False,
    # 计数字段 → 0
    "milestone_review_count": 0,
    # 状态字段 → missing/blocked/not ready
    "latest_review_status": "missing",
    "intake_status": "missing",
    "milestone_status": "N/A",
    "milestone_kind": "N/A",
    # 字符串字段 → N/A
    "latest_review_checkpoint": "N/A",
    "milestone_input_checkpoint": "N/A",
    # 列表字段 → []
    "review_blockers": [],
    "review_invalidated_by": [],
}


def detect_missing_fields(artifact_path: str, schema_path: str = "") -> dict:
    """检测 artifact 中缺失的字段，返回 {field: conservative_default}。"""
    if not os.path.exists(artifact_path):
        return {"_artifact_missing": "file not found"}

    with open(artifact_path) as f:
        content = f.read()

    # 如果提供了 schema 文件，从 schema 提取期望字段列表
    # 否则使用 built-in CONSERVATIVE_DEFAULTS
    expected_fields = set(CONSERVATIVE_DEFAULTS.keys())

    if schema_path and os.path.exists(schema_path):
        with open(schema_path) as f:
            schema_content = f.read()
        # 从 schema 中提取字段名（简单启发式：查找 YAML key 模式）
        for match in re.finditer(
            r"^[- ]\s*(\w+):", schema_content, re.MULTILINE
        ):
            expected_fields.add(match.group(1))

    missing = {}
    for field in sorted(expected_fields):
        val = parse_yaml_field(content, field)
        # 字段不存在（parse_yaml_field 返回 ""）或值为空字符串
        if not val:
            default = CONSERVATIVE_DEFAULTS.get(
                field, "N/A"
            )
            missing[field] = default

    return missing


def main():
    parser = argparse.ArgumentParser(
        description="Runtime Backfill Detect"
    )
    parser.add_argument(
        "--artifact", required=True,
        help="Path to .servo artifact (control-state.md or milestone.md)"
    )
    parser.add_argument(
        "--schema-file", default="",
        help="Optional path to template/schema for expected fields"
    )
    args = parser.parse_args()

    missing = detect_missing_fields(args.artifact, args.schema_file)

    if not missing:
        result = {
            "missing_fields": {},
            "backfill_values": {},
            "gaps_recorded": [],
            "reason": "所有已知字段均已存在，无需 backfill",
        }
    else:
        result = {
            "missing_fields": missing,
            "backfill_values": missing,
            "gaps_recorded": [
                f"{field}: missing → default={repr(val)}"
                for field, val in missing.items()
            ],
            "reason": (
                f"检测到 {len(missing)} 个缺失字段，"
                f"已按保守默认值计算 backfill。"
                f"注意：脚本仅负责检测和计算默认值；"
                f"行为约束（不得扩大权限、不得推断 programmer confirmation、"
                f"不得增加 counter、不得允许 Worktrack Init/Dispatch）"
                f"由 Skill 文本和 LLM 行为层保障。"
            ),
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
