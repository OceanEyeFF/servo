#!/usr/bin/env python3
"""Autonomy Policy Check — Low-Risk Default-Flow Autonomy Policy 运行时检查脚本。

根据 operation + skill 判断当前操作是否命中 forbidden / stop_condition，
并报告 allowed 状态、审批需求和证据完整性。

对应 SKILL.md §10.7 步骤 5 的低风险默认流策略。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/autonomy_policy_check.py \
    --operation {observe|change_goal|init_milestone|cleanup} \
    --skill {skill_name} \
    --control-state .servo/control-state.md

输出: JSON (allowed, blocked, stop_condition_hit, forbidden_hit,
            needs_approval, evidence_required_complete, evidence_missing, reason)
Exit 0 = check passed (无 hard block); exit 1 = hard block.
"""

import argparse
import json
import os
import re
import sys
from typing import Any

# ──────────────────────────────────────────────
# 策略规则定义（4 类，从 SKILL.md §10.7 步骤 5 提取）
# ──────────────────────────────────────────────

FORBIDDEN: dict[str, str] = {
    "goal_change":                         "目标变更",
    "scope_expansion":                     "范围扩展",
    "milestone_final_acceptance":          "Milestone 最终验收",
    "release_publish":                     "发布/打包/标签",
    "github_release":                      "GitHub Release",
    "publish_workflow":                    "发布工作流",
    "protected_branch_mutation":           "受保护分支变更",
    "force_push":                          "强制推送",
    "large_file_deletion":                 "大量文件删除",
    "destructive_cleanup":                 "破坏性清理",
    "secret_security_privacy":             "密钥/安全/隐私",
    "deploy_network_db":                   "部署/网络/数据库迁移",
    "cross_repo_side_effects":             "跨仓库副作用",
    "external_paid_quota":                 "外部付费/配额消耗",
}

STOP_CONDITION: dict[str, str] = {
    "evidence_missing":                    "证据缺失或冲突",
    "branch_mismatch":                     "分支不匹配",
    "gate_fail":                           "Gate 失败",
    "context_noise":                       "上下文噪音/遗忘",
    "needs_programmer_judgment":           "需要程序员判断",
    "authority_boundary_unclear":          "权限边界不清",
    "contract_scope_expansion":            "Contract 外扩",
    "protected_branch_policy_hit":         "受保护分支策略命中",
    "destructive_operation_hit":           "破坏性操作命中",
    "release_sensitive_signal":            "发布敏感信号",
    "milestone_final_acceptance_boundary": "Milestone 最终验收边界",
}

ALLOWED: dict[str, str] = {
    "read_only_observation":       "只读观察",
    "artifact_hydration":          "Artifact 水合",
    "status_consistency_check":    "状态一致性检查",
    "non_destructive_docs_edits":  "非破坏性文档编辑",
    "bounded_local_verification":  "限定范围本地验证",
    "repo_refresh":                "Repo 刷新写回",
    "scaffold_validation":         "脚手架验证无外部副作用",
}

EVIDENCE_REQUIRED: dict[str, str] = {
    "route_decision":              "路由决策",
    "repo_refresh_checkpoint":     "Repo 刷新 checkpoint",
}

PLACEHOLDER_VALUES = {
    "",
    "n/a",
    "none",
    "null",
    "pending",
    "not_started",
    "tbd",
    "unknown",
}


# ──────────────────────────────────────────────
# 操作 → 策略命中映射
# ──────────────────────────────────────────────

class PolicyProfile:
    """单个 operation + skill 组合的策略命中 profile。"""

    __slots__ = (
        "allowed_rules",
        "forbidden_hit",
        "stop_condition_hit",
        "needs_approval",
        "blocked_override",
        "blocking_exception",
        "description",
    )

    def __init__(
        self,
        *,
        allowed_rules: list[str] | None = None,
        forbidden_hit: list[str] | None = None,
        stop_condition_hit: list[str] | None = None,
        needs_approval: bool = False,
        blocked_override: bool | None = None,
        blocking_exception: str | None = None,
        description: str = "",
    ):
        self.allowed_rules = allowed_rules or []
        self.forbidden_hit = forbidden_hit or []
        self.stop_condition_hit = stop_condition_hit or []
        self.needs_approval = needs_approval
        self.blocked_override = blocked_override
        self.blocking_exception = blocking_exception
        self.description = description


# ── operation → skill-specific profiles ──
# key format: "operation::skill"
# 未在映射中的组合走默认通用策略

POLICY_MAP: dict[str, PolicyProfile] = {
    # ── observe ──
    "observe::repo-status-skill": PolicyProfile(
        allowed_rules=["read_only_observation", "artifact_hydration",
                        "status_consistency_check"],
        description="RepoScope 只读观察：安全，在 allowed 范围内",
    ),

    # ── schedule ──
    # ── verify ──
    # ── dispatch ──
    # ── close ──
    # ── recover ──

    # ── change_goal ──
    "change_goal::repo-change-goal-skill": PolicyProfile(
        allowed_rules=[],
        forbidden_hit=["goal_change"],
        stop_condition_hit=[
            "needs_programmer_judgment",
            "milestone_final_acceptance_boundary",
        ],
        needs_approval=True,
        blocked_override=False,
        blocking_exception="repo-change-goal-skill requires separate programmer approval gate before mutation",
        description=(
            "目标变更命中 forbidden:goal_change，但 repo-change-goal-skill "
            "有独立审批门，标记 needs_approval: true 而非 blocked"
        ),
    ),

    # ── init_milestone ──
    "init_milestone::init-milestone-skill": PolicyProfile(
        allowed_rules=[],
        forbidden_hit=[],
        stop_condition_hit=[
            "contract_scope_expansion",
            "needs_programmer_judgment",
        ],
        needs_approval=True,
        description="Milestone 初始化可能扩大 scope，需要审批",
    ),
    "init_milestone::milestone-init-skill": PolicyProfile(
        allowed_rules=[
            "artifact_hydration",
            "status_consistency_check",
            "scaffold_validation",
        ],
        forbidden_hit=[],
        stop_condition_hit=[],
        needs_approval=False,
        description=(
            "milestone-init-skill 在自然语言 discussion-sufficiency admission "
            "通过后，由 LLM 完整 author candidate，在 exact preview/digest、"
            "expected canonical revision/digest、explicit approval 与 branch "
            "contract 下执行 bounded create/amend；它不拥有 Harness currentness、"
            "selection、Worktrack、Gate 或 result/final refs。"
            "release/publish/tag/push/deploy、protected branch mutation、scope "
            "expansion 和 destructive cleanup 仍由 forbidden/stop 边界阻断"
        ),
    ),

    # ── init_worktrack ──
    # ── cleanup ──
    "cleanup::milestone-cleanup-skill": PolicyProfile(
        allowed_rules=["non_destructive_docs_edits"],
        forbidden_hit=[],
        stop_condition_hit=[],
        needs_approval=False,
        description=(
            "milestone-cleanup-skill 只允许 milestone closeout 后的"
            "repo/runtime cleanup report 与非破坏性 dry-run 维护；"
            "cleanup apply/delete/move/archive 仍需独立显式审批"
        ),
    ),

    # ── doc_catch_up ──
}


# ──────────────────────────────────────────────
# 默认通用策略 profile（operation 的保守默认）
# ──────────────────────────────────────────────

DEFAULT_OPERATION_PROFILES: dict[str, PolicyProfile] = {
    "observe": PolicyProfile(
        allowed_rules=["read_only_observation"],
        needs_approval=False,
        description="observe 默认：只读观察，安全",
    ),
    "change_goal": PolicyProfile(
        allowed_rules=[],
        forbidden_hit=["goal_change"],
        stop_condition_hit=["needs_programmer_judgment"],
        needs_approval=True,
        blocked_override=False,
        blocking_exception="change_goal default requires separate programmer approval gate before mutation",
        description="change_goal 默认：目标变更需审批",
    ),
    "init_milestone": PolicyProfile(
        allowed_rules=[],
        stop_condition_hit=["contract_scope_expansion"],
        needs_approval=True,
        description="init_milestone 默认：可能扩大 scope，需要审批",
    ),
    "cleanup": PolicyProfile(
        allowed_rules=["non_destructive_docs_edits"],
        needs_approval=False,
        description=(
            "cleanup 默认：仅允许非破坏性 cleanup report/dry-run；"
            "cleanup apply/delete/move/archive 需独立显式审批"
        ),
    ),
}


# ──────────────────────────────────────────────
# 证据检查 — 基于 operation 判定哪些证据需要存在
# ──────────────────────────────────────────────

# operation → 必需证据项
REQUIRED_EVIDENCE: dict[str, list[str]] = {
    "observe": [
        "repo_refresh_checkpoint",
    ],
    "change_goal": [
        "route_decision",
    ],
    "init_milestone": [
        "route_decision",
    ],
    "cleanup": [],
}

def resolve_profile(operation: str, skill: str) -> PolicyProfile:
    """按 operation::skill 精确查找策略 profile，fallback 到 operation 默认。"""
    key = f"{operation}::{skill}"
    if key in POLICY_MAP:
        return POLICY_MAP[key]

    if operation in DEFAULT_OPERATION_PROFILES:
        profile = DEFAULT_OPERATION_PROFILES[operation]
        # 补充说明未明确注册的 skill
        profile.description = (
            f"[{skill}] 未在 POLICY_MAP 中显式注册，"
            f"使用 operation={operation} 保守默认。{profile.description}"
        )
        return profile

    # 完全未知的 operation → 最保守
    return PolicyProfile(
        allowed_rules=[],
        forbidden_hit=[],
        stop_condition_hit=[
            "authority_boundary_unclear",
            "needs_programmer_judgment",
        ],
        needs_approval=True,
        description=f"未知 operation={operation}，使用最保守默认：需要审批",
    )


# ──────────────────────────────────────────────
# 证据检查辅助
# ──────────────────────────────────────────────

def check_evidence(
    operation: str, control_state_path: str, skill: str = ""
) -> dict[str, Any]:
    """检查指定 operation 所需的证据是否存在。

    返回 {evidence_required_complete: bool, evidence_missing: [str, ...]}。
    """
    required = REQUIRED_EVIDENCE.get(operation, [])
    if not required:
        return {
            "evidence_required_complete": True,
            "evidence_missing": [],
        }

    # 检查 control-state.md 是否存在
    if not os.path.exists(control_state_path):
        return {
            "evidence_required_complete": False,
            "evidence_missing": [
                f"{item}（control-state.md 缺失）" for item in required
            ],
        }

    with open(control_state_path, "r") as f:
        content = f.read()

    missing: list[str] = []
    for item in required:
        found = _check_evidence_item(item, content, control_state_path)
        if not found:
            missing.append(f"{item}（{EVIDENCE_REQUIRED.get(item, item)}）")

    return {
        "evidence_required_complete": len(missing) == 0,
        "evidence_missing": missing,
    }


def _check_evidence_item(item: str, control_state_content: str,
                          control_state_path: str) -> bool:
    """对单个 evidence item 做基本存在性检查。

    直接检查 control-state 中对应字段或关联 artifact 文件是否存在。
    """
    repo_dir = os.path.dirname(os.path.dirname(control_state_path))
    servo_dir = os.path.join(repo_dir, ".servo") if repo_dir else ".servo"

    checks: dict[str, Any] = {
        "route_decision": lambda: (
            bool(re.search(r"route_decision|recommended_next_route",
                          control_state_content, re.IGNORECASE))
        ),
        "repo_refresh_checkpoint": lambda: (
            bool(re.search(r"latest_observed_checkpoint|repo_refresh_checkpoint",
                          control_state_content, re.IGNORECASE))
        ),
    }

    checker = checks.get(item)
    if checker is None:
        # 未知 evidence item → 不做自动检测，标记为 missing
        return False
    try:
        return bool(checker())
    except Exception:
        return False


def _control_field(content: str, field: str) -> str:
    match = re.search(
        rf"^\s*-\s*{re.escape(field)}:\s*(.*?)\s*$", content, re.MULTILINE
    )
    if not match:
        return ""
    return match.group(1).strip().strip("`\"'")


def _meaningful(value: object) -> bool:
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDER_VALUES


# ──────────────────────────────────────────────
# 主逻辑
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomy Policy Check — Low-Risk Default-Flow Autonomy Policy"
    )
    parser.add_argument(
        "--operation", required=True,
        choices=[
            "observe", "change_goal", "init_milestone", "cleanup",
        ],
        help="当前 Harness Function 算子",
    )
    parser.add_argument(
        "--skill", required=True,
        help="绑定的 Skill 名称",
    )
    parser.add_argument(
        "--control-state", default=".servo/control-state.md",
        help="Path to .servo/control-state.md",
    )
    args = parser.parse_args()

    operation: str = args.operation
    skill: str = args.skill
    control_state_path: str = args.control_state

    # ── 1. 策略解析 ──
    profile = resolve_profile(operation, skill)

    # ── 2. 证据检查 ──
    evidence = check_evidence(operation, control_state_path, skill)

    # ── 3. 组装结果 ──
    # allowed = 至少命中一条 allowed 规则
    is_allowed = len(profile.allowed_rules) > 0

    # blocked = forbidden / stop_condition / missing evidence hard block by default.
    # A blocked_override=False exception only suppresses forbidden hard-blocking
    # when the profile documents a separate approval gate. Stop conditions and
    # missing required evidence remain hard blocks.
    if profile.blocked_override is not None:
        forbidden_blocked = profile.blocked_override
    else:
        forbidden_blocked = len(profile.forbidden_hit) > 0
    stop_condition_blocked = len(profile.stop_condition_hit) > 0
    evidence_blocked = not evidence["evidence_required_complete"]
    is_blocked = forbidden_blocked or stop_condition_blocked or evidence_blocked

    reason_parts: list[str] = [profile.description]

    if is_allowed:
        reason_parts.append(
            f"allowed 规则命中: {', '.join(profile.allowed_rules)}"
        )
    else:
        reason_parts.append("未命中任何 allowed 规则")

    if profile.forbidden_hit:
        for rule in profile.forbidden_hit:
            reason_parts.append(
                f"forbidden 命中: {rule}（{FORBIDDEN[rule]}）"
            )
        if profile.blocked_override is False:
            reason_parts.append(
                f"forbidden blocking exception: {profile.blocking_exception}"
            )

    if profile.stop_condition_hit:
        for rule in profile.stop_condition_hit:
            reason_parts.append(
                f"stop_condition 命中: {rule}（{STOP_CONDITION[rule]}）"
            )

    if profile.needs_approval:
        reason_parts.append("需要审批")

    if not evidence["evidence_required_complete"]:
        reason_parts.append(
            f"证据缺失: {', '.join(evidence['evidence_missing'])}"
        )

    result = {
        "operation": operation,
        "skill": skill,
        "allowed": is_allowed,
        "blocked": is_blocked,
        "forbidden_hit": profile.forbidden_hit,
        "stop_condition_hit": profile.stop_condition_hit,
        "allowed_rules": profile.allowed_rules,
        "needs_approval": profile.needs_approval,
        "blocking_exception": profile.blocking_exception,
        "evidence_required_complete": evidence["evidence_required_complete"],
        "evidence_missing": evidence["evidence_missing"],
        "reason": " | ".join(reason_parts),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # ── 退出码：hard block → exit 1; 通过 → exit 0 ──
    sys.exit(1 if is_blocked else 0)


if __name__ == "__main__":
    main()
