#!/usr/bin/env python3
"""Dispatch Mode Recommend — Dispatch Decision Policy 确定性分类。

根据 8 个决策因子推荐 SubAgent 或 Current-Carrier 模式。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/dispatch_mode_recommend.py \\
    --task-coupling low \\
    --state-sharing low \\
    --parallel-value high \\
    --risk-profile medium \\
    --context-budget-fit yes \\
    --runtime-supports-subagent yes \\
    --permission-allows-delegation yes \\
    --dispatch-package-safe yes

输出: JSON (recommended_mode, confidence, reasons, needs_llm_review)
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch Mode Recommend"
    )
    parser.add_argument(
        "--task-coupling", required=True,
        choices=["low", "medium", "high"],
    )
    parser.add_argument(
        "--state-sharing", required=True,
        choices=["low", "medium", "high"],
    )
    parser.add_argument(
        "--parallel-value", required=True,
        choices=["low", "medium", "high"],
    )
    parser.add_argument(
        "--risk-profile", required=True,
        choices=["low", "medium", "high"],
    )
    parser.add_argument(
        "--context-budget-fit", required=True,
        choices=["yes", "no"],
    )
    parser.add_argument(
        "--runtime-supports-subagent", required=True,
        choices=["yes", "no", "unknown"],
    )
    parser.add_argument(
        "--permission-allows-delegation", required=True,
        choices=["yes", "no", "unknown"],
    )
    parser.add_argument(
        "--dispatch-package-safe", required=True,
        choices=["yes", "no"],
    )
    args = parser.parse_args()

    reasons = []
    needs_llm = False

    # ── 硬阻断条件 ──
    if args.runtime_supports_subagent == "no":
        reasons.append("runtime 不支持 SubAgent shell → current-carrier")
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "high",
            "reasons": reasons,
            "needs_llm_review": False,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.permission_allows_delegation == "no":
        reasons.append("权限边界禁止委派 → current-carrier")
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "high",
            "reasons": reasons,
            "needs_llm_review": False,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.dispatch_package_safe == "no":
        reasons.append("任务包不满足安全分派条件 → current-carrier")
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "high",
            "reasons": reasons,
            "needs_llm_review": False,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── 未知情况 → 保守 + needs LLM review ──
    if args.runtime_supports_subagent == "unknown":
        reasons.append("runtime SubAgent 可用性未知 → 保守 current-carrier")
        needs_llm = True
    if args.permission_allows_delegation == "unknown":
        reasons.append("委派权限状态未知 → 保守 current-carrier")
        needs_llm = True

    if needs_llm:
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "low",
            "reasons": reasons,
            "needs_llm_review": True,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── 正常决策：综合评分 ──
    score_subagent = 0
    score_current = 0

    # 任务耦合度：低 → SubAgent 有利
    tc = args.task_coupling
    if tc == "low":
        score_subagent += 2
        reasons.append("任务耦合度低 → SubAgent 有利")
    elif tc == "high":
        score_current += 2
        reasons.append("任务耦合度高 → Current-Carrier 有利")
    else:
        score_current += 1
        reasons.append("任务耦合度中等 → 倾向 Current-Carrier")

    # 状态共享需求：低 → SubAgent 有利
    ss = args.state_sharing
    if ss == "low":
        score_subagent += 2
        reasons.append("状态共享需求低 → SubAgent 有利")
    elif ss == "high":
        score_current += 2
        reasons.append("状态共享需求高 → Current-Carrier 有利")
    else:
        score_current += 1
        reasons.append("状态共享需求中等 → 倾向 Current-Carrier")

    # 并行价值：高 → SubAgent 有利
    pv = args.parallel_value
    if pv == "high":
        score_subagent += 2
        reasons.append("并行价值高 → SubAgent 有利")
    elif pv == "low":
        score_current += 1
        reasons.append("并行价值低 → Current-Carrier 更合适")

    # 风险：高 → Current-Carrier + 独立 Verify
    rp = args.risk_profile
    if rp == "high":
        score_current += 2
        reasons.append("高风险任务 → Current-Carrier 执行 + 独立 Verify")
    elif rp == "low":
        score_subagent += 1

    # 上下文预算：不够 → SubAgent 有利
    if args.context_budget_fit == "no":
        score_subagent += 1
        reasons.append("上下文预算紧张 → SubAgent 有利")

    if score_subagent > score_current:
        result = {
            "recommended_mode": "subagent",
            "confidence": "medium",
            "reasons": reasons,
            "needs_llm_review": False,
        }
    elif score_subagent == score_current:
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "low",
            "reasons": reasons + ["综合评分持平 → 保守 current-carrier"],
            "needs_llm_review": True,
        }
    else:
        result = {
            "recommended_mode": "current-carrier",
            "confidence": "medium",
            "reasons": reasons,
            "needs_llm_review": False,
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
