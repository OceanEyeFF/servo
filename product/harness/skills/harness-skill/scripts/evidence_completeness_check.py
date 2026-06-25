#!/usr/bin/env python3
"""证据完整性检查 — 验证 Gate 裁决前所有 evidence_required 项是否已收集。

检查 gate-evidence.md 中是否包含 9 项必需证据。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/evidence_completeness_check.py \
    --evidence-file .servo/worktrack/gate-evidence.md

输出: JSON (complete, missing, present, checked_items)
"""

import argparse
import json
import os
import re
import sys
from typing import Optional

EVIDENCE_REQUIRED = [
    {
        "key": "route_decision",
        "label": "路由决策",
        "patterns": [r"route.?decision", r"dispatch.?decision", r"路由决策"],
    },
    {
        "key": "worktrack_contract_scope",
        "label": "Worktrack Contract 范围/边界",
        "patterns": [r"contract", r"scope.?bound", r"范围", r"boundary"],
    },
    {
        "key": "selected_task_dispatch_packet",
        "label": "选中任务/分派包",
        "patterns": [r"dispatch.?packet", r"task.*packet", r"分派包", r"任务简报"],
    },
    {
        "key": "runtime_dispatch_profile",
        "label": "运行时 dispatch profile",
        "patterns": [r"runtime.?dispatch.?profile", r"dispatch_profile", r"backend_runtime"],
    },
    {
        "key": "validation_evidence",
        "label": "验证证据（测试/运行结果）",
        "patterns": [r"test.?evidence", r"validation.?evidence", r"验证证据", r"test.*result"],
    },
    {
        "key": "governance_policy_evidence",
        "label": "治理/策略证据",
        "patterns": [r"rule.?check", r"governance", r"policy.?evidence", r"策略证据"],
    },
    {
        "key": "gate_verdict",
        "label": "Gate 裁决",
        "patterns": [r"gate.?verdict", r"verdict", r"gate.?result", r"裁决"],
    },
    {
        "key": "closeout_record",
        "label": "收尾记录",
        "patterns": [r"closeout.?record", r"收尾", r"closeout"],
    },
    {
        "key": "repo_refresh_checkpoint",
        "label": "Repo 刷新 checkpoint",
        "patterns": [r"repo.?refresh", r"checkpoint", r"latest_observed"],
    },
]


def read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


def check_evidence(content: str) -> dict:
    """检查文本中是否包含所有必需证据项。"""
    present = []
    missing = []
    checked_items = {}

    for item in EVIDENCE_REQUIRED:
        matched = False
        for pattern in item["patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                matched = True
                break
        checked_items[item["key"]] = {
            "label": item["label"],
            "present": matched,
        }
        if matched:
            present.append(item["key"])
        else:
            missing.append(item["key"])

    complete = len(missing) == 0
    return {
        "complete": complete,
        "missing": missing,
        "present": present,
        "checked_items": checked_items,
        "reason": (
            f"所有 {len(EVIDENCE_REQUIRED)} 项证据已收集"
            if complete
            else f"缺少 {len(missing)} 项证据: {', '.join(missing)}"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Evidence Completeness Check")
    parser.add_argument(
        "--evidence-file",
        default=".servo/worktrack/gate-evidence.md",
        help="Path to gate-evidence.md",
    )
    parser.add_argument(
        "--evidence-text",
        default=None,
        help="Direct text input (alternative to --evidence-file)",
    )
    args = parser.parse_args()

    if args.evidence_text is not None:
        content = args.evidence_text
    else:
        content = read_file(args.evidence_file)
        if content is None:
            result = {
                "complete": False,
                "missing": [e["key"] for e in EVIDENCE_REQUIRED],
                "present": [],
                "checked_items": {},
                "reason": f"证据文件不存在: {args.evidence_file}",
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

    result = check_evidence(content)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()
