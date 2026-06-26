#!/usr/bin/env python3
"""Git Hash Check — Git Commit Hash 基线对比（幂等性守卫）。

比较 control-state-repo 记录的 latest_observed_checkpoint 与当前 HEAD，
判定是否需要刷新 repo 基线。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/git_hash_check.py \\
    --control-state .servo/control-state-repo.md

输出: JSON (status, current_head, checkpoint, repo_baseline_unchanged, repo_baseline_changed)
"""

import argparse
import json
import os
import sys
from typing import Optional

from _git_utils import git_rev_parse_head

def read_checkpoint(path: str) -> Optional[str]:
    """从 control-state-repo.md 读取 latest_observed_checkpoint。"""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("- latest_observed_checkpoint:"):
                val = line.split(":", 1)[1].strip()
                return val if val else None
    return None


def main():
    parser = argparse.ArgumentParser(description="Git Hash Check — 幂等性守卫")
    parser.add_argument(
        "--control-state",
        default=".servo/control-state-repo.md",
        help=(
            "Path to repo checkpoint state "
            "(default: .servo/control-state-repo.md; legacy alias may point "
            "to .servo/control-state.md)"
        ),
    )
    args = parser.parse_args()

    head = git_rev_parse_head()
    checkpoint = read_checkpoint(args.control_state)

    result = {
        "current_head": head,
        "latest_observed_checkpoint": checkpoint,
    }

    if not checkpoint:
        result["status"] = "missing_checkpoint"
        result["repo_baseline_unchanged"] = False
        result["repo_baseline_changed"] = True
        result["reason"] = "latest_observed_checkpoint 缺失，需要刷新 repo 基线"
    elif head == checkpoint:
        result["status"] = "unchanged"
        result["repo_baseline_unchanged"] = True
        result["repo_baseline_changed"] = False
        result["reason"] = f"HEAD ({head[:12]}...) 与 checkpoint 一致，跳过刷新"
    else:
        result["status"] = "changed"
        result["repo_baseline_unchanged"] = False
        result["repo_baseline_changed"] = True
        result["reason"] = (
            f"HEAD ({head[:12]}...) 与 checkpoint ({checkpoint[:12]}...) 不一致，"
            f"需要刷新 repo 基线"
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("repo_baseline_unchanged") else 1)


if __name__ == "__main__":
    main()
