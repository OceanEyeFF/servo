#!/usr/bin/env python3
"""Complex Project Entry Gate Check — 核心阻塞条件的确定性检查。

检查 complex_project_entry_gate 中的 entry_verdict 和 milestone_blocking_decision。
边缘情况（blank/placeholder/incomplete）标记 needs_llm_review。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/complex_project_entry_gate_check.py \\
    --gate-source .servo/repo/pre-milestone-intake-{id}.md

输出: JSON (ready, blocked, reason, needs_llm_review, checked_fields)
"""

import argparse
import json
import os
import re
import sys

from _guard_utils import parse_yaml_field, parse_bool_field

BLOCKING_DECISIONS = frozenset({
    "block_create", "block_upsert", "block_activate", "block_derive_worktrack",
})
PLACEHOLDER_MARKERS = frozenset({
    "placeholder", "pending", "tbd", "pending_programmer_confirmation",
})


def _looks_like_placeholder(val: str) -> bool:
    """检查字符串是否看起来像占位符而非真实内容。"""
    low = val.strip().lower()
    if not low:
        return True
    return low in PLACEHOLDER_MARKERS


def main():
    parser = argparse.ArgumentParser(
        description="Complex Project Entry Gate Check"
    )
    parser.add_argument(
        "--gate-source", required=True,
        help="Path to file containing complex_project_entry_gate (e.g. intake review)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.gate_source):
        result = {
            "ready": True,
            "blocked": False,
            "reason": "gate source 文件不存在，认为无 complex-project trigger — 跳过",
            "needs_llm_review": False,
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)

    with open(args.gate_source) as f:
        content = f.read()

    # 检测是否存在 complex_project_entry_gate 段
    if "complex_project_entry_gate" not in content.lower():
        result = {
            "ready": True,
            "blocked": False,
            "reason": "gate source 中无 complex_project_entry_gate — 跳过",
            "needs_llm_review": False,
            "checked_fields": {},
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)

    # 隔离 complex_project_entry_gate YAML 块（避免从全文解析导致字段冲突）
    gate_match = re.search(
        r"## Complex Project Entry Gate\s*\r?\n.*?```yaml\s*\r?\n(.*?)```",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if gate_match:
        gate_content = gate_match.group(1)
    else:
        # fallback: 尝试从全文中找 complex_project_entry_gate 开头的 YAML 块
        gate_match = re.search(
            r"complex_project_entry_gate:\s*\r?\n(.*?)(?=\n```|\n\n##|\Z)",
            content,
            re.DOTALL,
        )
        gate_content = gate_match.group(1) if gate_match else content

    entry_verdict = parse_yaml_field(gate_content, "entry_verdict")
    recommendation_status = parse_yaml_field(
        gate_content, "recommendation_status"
    )
    needed = parse_bool_field(gate_content, "needed")
    blocks_impl = parse_bool_field(
        gate_content, "blocks_implementation_until_resolved"
    )

    # milestone_blocking_decision: 从 gate_content 中提取列表
    blocking_decision_match = re.search(
        r"milestone_blocking_decision:\s*\r?\n((?:\s*-.*\r?\n)*)",
        gate_content,
    )
    blocking_decisions = set()
    if blocking_decision_match:
        for line in blocking_decision_match.group(1).splitlines():
            m = re.search(r"[-*]\s*[\"']?(\S+?)[\"']?\s*$", line.strip())
            if m:
                blocking_decisions.add(m.group(1).strip().strip('"').strip("'"))

    blocked_by = blocking_decisions & BLOCKING_DECISIONS

    checked = {
        "entry_verdict": entry_verdict,
        "blocking_decisions_found": list(blocked_by),
        "reinforcement_needed": needed,
        "recommendation_status": recommendation_status,
        "blocks_implementation": blocks_impl,
    }

    reasons = []
    needs_llm = False

    # 边缘检测：占位符 / 空白 / missing
    if not entry_verdict or _looks_like_placeholder(entry_verdict):
        needs_llm = True
        reasons.append("entry_verdict 为空或疑似占位符")

    # 核心条件
    if entry_verdict == "blocked":
        reasons.append("entry_verdict=blocked")
    if blocked_by:
        reasons.append(
            f"milestone_blocking_decision 包含: {', '.join(blocked_by)}"
        )
    if entry_verdict == "needs_reinforcement_milestone":
        reasons.append("entry_verdict=needs_reinforcement_milestone")
    if needed is True:
        if recommendation_status in (
            "recommended", "required", "pending_operator_review",
        ):
            reasons.append(
                f"reinforcement needed=true, "
                f"status={recommendation_status}"
            )
    if blocks_impl is True:
        reasons.append("blocks_implementation_until_resolved=true")

    if not entry_verdict and not blocked_by:
        needs_llm = True
        reasons.append("gate 存在但所有字段为空 — 按 unresolved gate blocking default 阻断")

    if reasons:
        result = {
            "ready": False,
            "blocked": True,
            "reason": "; ".join(reasons),
            "needs_llm_review": needs_llm,
            "checked_fields": checked,
        }
    else:
        result = {
            "ready": True,
            "blocked": False,
            "reason": "complex-project entry gate 核心条件通过",
            "needs_llm_review": needs_llm,
            "checked_fields": checked,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ready"] else 1)


if __name__ == "__main__":
    main()
