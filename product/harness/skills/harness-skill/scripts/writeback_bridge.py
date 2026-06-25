#!/usr/bin/env python3
"""Writeback Bridge — Milestone 写回格式桥接。

milestone-status-skill 输出的 writeback_instructions 格式与
servo-writeback-skill 期望的多步指令格式之间的翻译器。

用法:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/writeback_bridge.py \\
    --milestone-id MS-20260623-004 \\
    --instructions-json '{"writeback_required": true, "writeback_instructions": {...}}'

输出: JSON (bridge_ok, steps, step_count) 或 (bridge_ok: false, reason)
"""

import argparse
import json
import sys


# ── 翻译规则映射 ──

def _translate_milestone_artifact_updates(instructions, milestone_id):
    """milestone_artifact_updates → milestone-artifact-update"""
    field_updates = instructions.get("milestone_artifact_updates", {})
    if not field_updates:
        return None
    return {
        "mode": "milestone-artifact-update",
        "params": {
            "milestone_id": milestone_id,
            "field_updates": field_updates,
        },
    }


def _translate_backlog_upsert(instructions, milestone_id):
    """backlog_updates.milestone_backlog_upsert → milestone-backlog-upsert"""
    upsert = instructions.get("backlog_updates", {}).get("milestone_backlog_upsert")
    if not upsert:
        return None
    return {
        "mode": "milestone-backlog-upsert",
        "params": {
            "milestone_id": upsert.get("milestone_id", milestone_id),
            "status": upsert.get("status", ""),
        },
    }


def _translate_backlog_history_archive(instructions, milestone_id):
    """backlog_updates.milestone_history_append → milestone-history-archive"""
    hist = instructions.get("backlog_updates", {}).get("milestone_history_append")
    if not hist:
        return None
    return {
        "mode": "milestone-history-archive",
        "params": {
            "milestone_id": hist.get("milestone_id", milestone_id),
            "final_status": hist.get("status", ""),
        },
    }


def _translate_checkpoint(instructions, _milestone_id):
    """control_state_updates.milestone_input_checkpoint → baseline-checkpoint-update"""
    cp = instructions.get("control_state_updates", {})
    ckpt = cp.get("milestone_input_checkpoint")
    if not ckpt:
        return None
    return {
        "mode": "baseline-checkpoint-update",
        "params": {
            "checkpoint_type": "milestone_input_checkpoint",
            "checkpoint_value": ckpt,
        },
    }


def _translate_pipeline_summary(instructions, _milestone_id):
    """control_state_updates.milestone_pipeline_summary → pipeline-summary-recalc"""
    cp = instructions.get("control_state_updates", {})
    summary = cp.get("milestone_pipeline_summary")
    if not summary:
        return None
    return {
        "mode": "pipeline-summary-recalc",
        "params": {
            "summary": summary,
        },
    }


def _translate_activation_switch(instructions, _milestone_id):
    """pipeline_advancement_action → milestone-activation-switch (仅 action=activate_next)"""
    adv = instructions.get("pipeline_advancement_action")
    if not adv:
        return None
    if adv.get("action") != "activate_next":
        return None
    return {
        "mode": "milestone-activation-switch",
        "params": {
            "milestone_id": adv.get("next_milestone_id", ""),
            "previous_active": adv.get("previous_active", ""),
        },
    }


def _translate_control_state_route(instructions, milestone_id):
    """control_state_updates.milestone_status → control-state-route-update"""
    cp = instructions.get("control_state_updates", {})
    status = cp.get("milestone_status")
    if not status:
        return None
    return {
        "mode": "control-state-route-update",
        "params": {
            "milestone_id": milestone_id,
            "milestone_status": status,
        },
    }


TRANSLATORS = [
    _translate_milestone_artifact_updates,
    _translate_backlog_upsert,
    _translate_backlog_history_archive,
    _translate_checkpoint,
    _translate_pipeline_summary,
    _translate_activation_switch,
    _translate_control_state_route,
]


def translate(instructions, milestone_id):
    """将 milestone-status-skill 的 writeback_instructions 翻译为多步指令列表。

    Returns:
        list of step dicts — 可能为空（无可翻译的内容），但不为 None
    """
    steps = []
    for translator in TRANSLATORS:
        step = translator(instructions, milestone_id)
        if step is not None:
            steps.append(step)
    return steps


def main():
    parser = argparse.ArgumentParser(
        description="Milestone 写回格式桥接 — 将 milestone-status 输出翻译为 writeback-skill 多步指令"
    )
    parser.add_argument(
        "--milestone-id", required=True,
        help="当前里程碑 ID（如 MS-20260623-004）",
    )
    parser.add_argument(
        "--instructions-json", required=True,
        help="milestone-status-skill 输出的完整 JSON 字符串",
    )
    args = parser.parse_args()

    # ── 解析输入 JSON ──
    try:
        payload = json.loads(args.instructions_json)
    except json.JSONDecodeError as exc:
        result = {
            "bridge_ok": False,
            "reason": f"instructions-json 不是合法 JSON: {exc}",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # ── 校验顶层结构 ──
    if not isinstance(payload, dict):
        result = {
            "bridge_ok": False,
            "reason": "输入 JSON 必须是对象（dict）",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    if "writeback_required" not in payload:
        result = {
            "bridge_ok": False,
            "reason": '缺少 writeback_required 字段',
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # ── 若不需要写回，直接退出 ──
    if not payload.get("writeback_required"):
        result = {
            "bridge_ok": True,
            "reason": "writeback_required=false — 无需写回",
            "steps": [],
            "step_count": 0,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # ── 校验 writeback_instructions 存在性 ──
    instructions = payload.get("writeback_instructions")
    if instructions is None:
        result = {
            "bridge_ok": False,
            "reason": "writeback_instructions 为 null — 无法翻译",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    if not isinstance(instructions, dict):
        result = {
            "bridge_ok": False,
            "reason": "writeback_instructions 必须是对象（dict）",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # ── 执行翻译 ──
    steps = translate(instructions, args.milestone_id)

    result = {
        "bridge_ok": True,
        "steps": steps,
        "step_count": len(steps),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
