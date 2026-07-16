#!/usr/bin/env python3
"""Split Control State — 将旧版单文件 control-state.md 拆分为四文件架构。

读取旧版 control-state.md（~880 行，~103 字段），按 DESIGN-001 Schema
拆分为四个独立文件：
  - control-state.md (精简版，跨层控制记忆，~18 字段)
  - control-state-repo.md (Repo + Milestone 级，~63 字段)
  - control-state-wt.md (Worktrack 级，~11 字段)
  - operator-config.md (人类可调配置，~14 字段)

用法:
  # Dry-run 预览（不写文件）:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/split_control_state.py \\
    --mode dry-run --input .servo/control-state.md

  # Apply 实际写入:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/split_control_state.py \\
    --mode apply --input .servo/control-state.md

  # Apply + 强制覆盖:
  PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/split_control_state.py \\
    --mode apply --input .servo/control-state.md --force

输出: JSON (status, files_written, fields_migrated, warnings)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Section skip list — sections whose content is NOT migrated to any file
# ---------------------------------------------------------------------------
SKIP_SECTIONS = {
    "Current Control Notes",  # ~540 lines of history, handled by compaction milestone
}

# ---------------------------------------------------------------------------
# Field → output file mapping
# Each entry: field_name → (target_file_key, output_field_name)
# target_file_key: "repo", "wt", "operator", "slim"
# output_field_name: name to use in output (usually same as input)
# ---------------------------------------------------------------------------
FIELD_MAP: dict[str, tuple[str, str]] = {}

# === control-state-repo.md ===
REPO_FIELDS = [
    # Metadata (Repo-level runtime counters)
    ("rotation_count", "repo", "rotation_count"),
    ("last_rotation_at", "repo", "last_rotation_at"),
    ("handback_history_ref", "repo", "handback_history_ref"),
    # Control Level
    ("repo_scope", "repo", "repo_scope"),
    # Active Worktrack registry
    ("closed_worktrack_commits", "repo", "closed_worktrack_commits"),
    # Milestone Pipeline — Active
    ("active_milestone", "repo", "active_milestone"),
    ("milestone_status", "repo", "milestone_status"),
    ("milestone_kind", "repo", "milestone_kind"),
    ("active_milestone_branch", "repo", "active_milestone_branch"),
    ("milestone_pipeline_summary", "repo", "milestone_pipeline_summary"),
    (
        "active_milestone_branch_sync_state",
        "repo",
        "active_milestone_branch_sync_state",
    ),
    ("active_milestone_progress", "repo", "active_milestone_progress"),
    ("active_milestone_branch_head", "repo", "active_milestone_branch_head"),
    ("milestone_pipeline_path", "repo", "milestone_pipeline_path"),
    (
        "active_milestone_review_gate_status",
        "repo",
        "active_milestone_review_gate_status",
    ),
    ("active_milestone_review_count", "repo", "active_milestone_review_count"),
    (
        "active_milestone_review_checkpoint",
        "repo",
        "active_milestone_review_checkpoint",
    ),
    ("active_milestone_review_blockers", "repo", "active_milestone_review_blockers"),
    ("milestone_intake_confirmed", "repo", "milestone_intake_confirmed"),
    # Milestone Pipeline — Planning
    ("planned_milestone", "repo", "planned_milestone"),
    ("planned_milestone_status", "repo", "planned_milestone_status"),
    ("planned_milestone_priority", "repo", "planned_milestone_priority"),
    ("planned_milestone_dependency", "repo", "planned_milestone_dependency"),
    ("accepted_milestone", "repo", "accepted_milestone"),
    # Milestone Review Gate
    ("milestone_review_gate_ready", "repo", "milestone_review_gate_ready"),
    ("latest_review_status", "repo", "latest_review_status"),
    ("milestone_review_count", "repo", "milestone_review_count"),
    ("latest_review_checkpoint", "repo", "latest_review_checkpoint"),
    ("effective_review_pass", "repo", "effective_review_pass"),
    ("review_invalidated_by", "repo", "review_invalidated_by"),
    # Baseline Branch
    ("baseline_branch", "repo", "baseline_branch"),
    ("baseline_ref", "repo", "baseline_ref"),
    ("current_checkout", "repo", "current_checkout"),
    ("remote_branches", "repo", "remote_branches"),
    ("develop_main_head", "repo", "develop_main_head"),
    ("develop-servo_head", "repo", "develop-servo_head"),
    ("master_head", "repo", "master_head"),
    # Branch Environment Guard (Repo-level)
    ("current_branch_context", "repo", "current_branch_context"),
    ("expected_branch_context", "repo", "expected_branch_context"),
    ("branch_context_guard_status", "repo", "branch_context_guard_status"),
    ("branch_context_required_ref", "repo", "branch_context_required_ref"),
    # Baseline Traceability
    ("latest_observed_checkpoint", "repo", "latest_observed_checkpoint"),
    ("last_cleanup_checkpoint", "repo", "last_cleanup_checkpoint"),
    ("last_doc_catch_up_checkpoint", "repo", "last_doc_catch_up_checkpoint"),
    ("milestone_input_checkpoint", "repo", "milestone_input_checkpoint"),
    ("milestone_review_gate_checkpoint", "repo", "milestone_review_gate_checkpoint"),
    ("checkpoint_ref", "repo", "checkpoint_ref"),
    ("release_checkpoint_ref", "repo", "release_checkpoint_ref"),
    ("checkpoint_type", "repo", "checkpoint_type"),
    ("previous_observed_checkpoint", "repo", "previous_observed_checkpoint"),
    ("last_verified_checkpoint", "repo", "last_verified_checkpoint"),
    ("if_no_commit_reason", "repo", "if_no_commit_reason"),
    ("alternative_traceability", "repo", "alternative_traceability"),
    ("verified_at_history", "repo", "verified_at_history"),
    # Linked Formal Documents (Repo-level)
    ("repo_snapshot", "repo", "repo_snapshot"),
    ("repo_analysis", "repo", "repo_analysis"),
    # Notes → Repo Policy
    (
        "returning_to_repo_scope_does_not_clear_handoff",
        "repo",
        "returning_to_repo_scope_does_not_clear_handoff",
    ),
]

# === control-state-wt.md ===
WT_FIELDS = [
    ("worktrack_scope", "wt", "worktrack_scope"),
    ("current_function", "wt", "current_function"),
    ("active_worktrack", "wt", "active_worktrack"),
    ("active_worktrack_branch", "wt", "active_worktrack_branch"),
    ("active_worktrack_node_type", "wt", "active_worktrack_node_type"),
    ("active_worktrack_status", "wt", "active_worktrack_status"),
    ("initial_requirement_ref", "wt", "initial_requirement_ref"),
    ("finished_handback_ref", "wt", "finished_handback_ref"),
    ("implementation_checkpoint", "wt", "implementation_checkpoint"),
    ("worktrack_autonomy_policy", "wt", "worktrack_autonomy_policy"),
    ("recommended_next_route", "wt", "recommended_next_route"),
    ("recommended_next_scope", "wt", "recommended_next_scope"),
    # Branch Environment Guard (WT-level)
    ("worktrack_branch", "wt", "worktrack_branch"),
]

# === operator-config.md ===
OPERATOR_FIELDS = [
    # User-Defined Servo Controls
    (
        "continuous_progression_permission",
        "operator",
        "continuous_progression_permission",
    ),
    (
        "per_milestone_automatic_worktrack_budget",
        "operator",
        "per_milestone_automatic_worktrack_budget",
    ),
    ("default_servo_work_branch", "operator", "default_servo_work_branch"),
    ("protected_branch_policy", "operator", "protected_branch_policy"),
    ("branch_mutation_policy", "operator", "branch_mutation_policy"),
    (
        "auto_maintained_runtime_facts_not_asked",
        "operator",
        "auto_maintained_runtime_facts_not_asked",
    ),
    # Continuation Authority
    ("post_contract_autonomy", "operator", "post_contract_autonomy"),
    ("autonomy_scope", "operator", "autonomy_scope"),
    ("max_auto_new_worktracks", "operator", "max_auto_new_worktracks"),
    ("stop_after_autonomous_slice", "operator", "stop_after_autonomous_slice"),
    ("subagent_dispatch_mode", "operator", "subagent_dispatch_mode"),
    (
        "subagent_dispatch_mode_override_scope",
        "operator",
        "subagent_dispatch_mode_override_scope",
    ),
    ("subagent_default_model", "operator", "subagent_default_model"),
    ("persistent_authority_notes", "operator", "persistent_authority_notes"),
]

# === control-state.md 精简版 ===
SLIM_FIELDS = [
    # Metadata (file-level, moved from old frontmatter/body to slim body)
    ("updated", "slim", "updated"),
    ("owner", "slim", "owner"),
    # Handback Guard
    ("handoff_state", "slim", "handoff_state"),
    ("last_handback_signature", "slim", "last_handback_signature"),
    ("handback_reaffirmed_rounds", "slim", "handback_reaffirmed_rounds"),
    ("stable_handback_threshold", "slim", "stable_handback_threshold"),
    ("handback_lock_active", "slim", "handback_lock_active"),
    ("last_unlock_signal", "slim", "last_unlock_signal"),
    ("stop_reason_history", "slim", "stop_reason_history"),
    # Approval Boundary
    ("needs_programmer_approval", "slim", "needs_programmer_approval"),
    ("reason", "slim", "reason"),
    ("approval_scope", "slim", "approval_scope"),
    ("approval_persistence", "slim", "approval_persistence"),
    # Autonomy Ledger
    ("autonomy_budget_remaining", "slim", "autonomy_budget_remaining"),
    ("autonomous_worktracks_opened", "slim", "autonomous_worktracks_opened"),
]

# Build FIELD_MAP dict
for src_field, target_file, out_field in (
    REPO_FIELDS + WT_FIELDS + OPERATOR_FIELDS + SLIM_FIELDS
):
    FIELD_MAP[src_field] = (target_file, out_field)

# Fields to explicitly skip/delete (not mapped to any output file)
SKIP_FIELDS = {
    # Frontmatter-only fields (not control fields)
    "status",
    # Retired rolling Worktrack interface. Never copy it into split output.
    "worktrack_contract",
    "worktrack_contract_ref",
    "worktrack_plan_ref",
    "plan_task_queue",
    "gate_evidence",
    # Handled via derived logic (read from all_fields in map_fields_to_outputs)
    "current_next_action",
    # runtime_dispatch_profile and all 12 sub-fields (all empty, schema preserved in docs)
    "runtime_dispatch_profile",
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
    "decision_inputs",
}

# Fields from Baseline Branch section that are duplicate of Milestone Pipeline
BASELINE_SKIP_FIELDS = {
    "active_milestone_branch_head",  # value "none", stale duplicate of Milestone Pipeline
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter between --- markers."""
    fm = {}
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return fm
    for i in range(1, len(lines)):
        line = lines[i].rstrip()
        if line.strip() == "---":
            break
        m = re.match(r"^(\w[\w_-]*):\s*(.*)", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            fm[key] = val
    return fm


def parse_sections(content: str) -> dict[str, list[str]]:
    """Split markdown into named sections on ## headers.
    Returns {section_name: [lines including header]}.
    Lines before the first ## go into '_preamble'.
    """
    sections: dict[str, list[str]] = {}
    current_name = "_preamble"
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections[current_name] = current_lines
            current_name = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_name] = current_lines

    return sections


def extract_fields_from_section(lines: list[str], section_name: str) -> dict[str, Any]:
    """Extract key-value fields from a section's lines.

    Handles:
      - `- key: value`  (standard markdown list field)
      - `key: value`     (bare field, no dash prefix — in Metadata section)
      - `  - item`       (indented list items → appended to previous field)
      - multi-line values (indented continuation lines)

    Returns {field_name: value} where value is str or list[str].
    """
    fields: dict[str, Any] = {}
    current_field: Optional[str] = None
    current_value: Any = None
    is_list = False

    # Skip the section header line
    body_lines = lines[1:] if lines and lines[0].startswith("## ") else lines

    for line in body_lines:
        # Skip empty lines (they separate field blocks)
        if line.strip() == "":
            current_field = None
            current_value = None
            is_list = False
            continue

        # Skip pure comment lines
        stripped = line.strip()
        if stripped.startswith("> ") or stripped.startswith(">") or stripped == ">":
            continue

        # Detect indented list item (continuation of a list field)
        if line.startswith("  - ") and current_field is not None:
            item = line.strip()[2:]  # remove "  - "
            if is_list and isinstance(current_value, list):
                current_value.append(item)
            elif not is_list:
                # Convert scalar to list
                if current_value is not None and current_value != "":
                    current_value = [str(current_value), item]
                else:
                    current_value = [item]
                is_list = True
                fields[current_field] = current_value
            continue

        # Detect field definition
        # Pattern: "- key: value" or "key: value" (bare)
        m = re.match(r"^(- )?(\S+):\s*(.*)", line)
        if m:
            key = m.group(2)
            raw_value = m.group(3).strip()
            has_dash = m.group(1) is not None

            # Skip fields in the skip set
            if key in SKIP_FIELDS:
                current_field = None
                current_value = None
                is_list = False
                continue

            # Baseline Branch section: skip stale duplicate of active_milestone_branch_head
            if (
                section_name == "Baseline Branch"
                and key == "active_milestone_branch_head"
            ):
                current_field = None
                current_value = None
                is_list = False
                continue

            # Start a new field
            current_field = key
            if raw_value == "":
                # Empty value — might be a list starting on next line
                current_value = ""
                is_list = False
            else:
                current_value = raw_value
                is_list = False

            fields[key] = current_value
            continue

        # Continuation line (indented text, not a list item, not a field def)
        if line.startswith("  ") and current_field is not None and not is_list:
            # Append to current scalar value
            continuation = line.strip()
            if isinstance(current_value, str):
                if current_value:
                    current_value = current_value + " " + continuation
                else:
                    current_value = continuation
                fields[current_field] = current_value
            continue

    return fields


def parse_legacy_control_state(path: str) -> dict[str, Any]:
    """Parse the legacy control-state.md into a flat field dict.

    Returns {field_name: value} for all recognized fields across all sections.
    Frontmatter fields are merged.
    """
    with open(path, "r") as f:
        content = f.read()

    fm = parse_frontmatter(content)
    sections = parse_sections(content)

    all_fields: dict[str, Any] = {}

    # Extract frontmatter fields
    for key in ("updated", "owner"):
        if key in fm:
            all_fields[key] = fm[key]

    # Extract fields from each section
    for section_name, lines in sections.items():
        if section_name in SKIP_SECTIONS:
            continue
        if section_name == "_preamble":
            continue
        fields = extract_fields_from_section(lines, section_name)
        for key, val in fields.items():
            all_fields[key] = val

    return all_fields


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------


def map_fields_to_outputs(
    all_fields: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    """Map parsed fields to four output dicts.

    Returns (repo, wt, operator, slim, warnings).
    """
    repo: dict[str, Any] = {}
    wt: dict[str, Any] = {}
    operator: dict[str, Any] = {}
    slim: dict[str, Any] = {}
    warnings: list[str] = []

    mapped_count = 0
    unmapped_fields: list[str] = []

    for field_name, value in all_fields.items():
        if field_name in FIELD_MAP:
            target_file, out_name = FIELD_MAP[field_name]
            if target_file == "repo":
                repo[out_name] = value
            elif target_file == "wt":
                wt[out_name] = value
            elif target_file == "operator":
                operator[out_name] = value
            elif target_file == "slim":
                slim[out_name] = value
            mapped_count += 1
        elif field_name in SKIP_FIELDS:
            continue  # explicitly skipped
        elif field_name in BASELINE_SKIP_FIELDS:
            continue
        else:
            unmapped_fields.append(field_name)

    if unmapped_fields:
        warnings.append(
            f"Unmapped fields ({len(unmapped_fields)}): "
            + ", ".join(sorted(unmapped_fields))
        )

    # Derive repo_next_action from current state
    active_wt = wt.get("active_worktrack", "")
    wt_status = wt.get("active_worktrack_status", "")
    if active_wt and wt_status:
        repo["repo_next_action"] = f"{active_wt} {wt_status}; pending"
    elif repo.get("active_milestone"):
        repo["repo_next_action"] = (
            f"activate milestone {repo.get('active_milestone', '')}"
        )
    else:
        repo["repo_next_action"] = "no active milestone; select next milestone"

    # Derive worktrack_next_action from legacy current_next_action
    # The legacy "Current Next Action" section has:
    #   - recommended_next_route: ...
    #   - recommended_next_scope: ...
    #   - current_next_action: ...
    # current_next_action goes to worktrack_next_action
    legacy_next = all_fields.get("current_next_action", "")
    if legacy_next:
        wt["worktrack_next_action"] = legacy_next
    elif active_wt:
        wt["worktrack_next_action"] = (
            f"{active_wt} ({wt.get('active_worktrack_node_type', '')}); pending"
        )
    else:
        wt["worktrack_next_action"] = None

    # Ensure release/governance fields have defaults if not present
    if "release_facts" not in repo:
        repo["release_facts"] = {
            "package": "",
            "source_version": "",
            "approval_lock": "",
            "status": "",
            "registry_latest": "",
            "registry_stable": "",
            "registry_next": "",
            "registry_observed_at": "",
        }
    if "release_boundary_note" not in repo:
        repo["release_boundary_note"] = None
    if "stable_candidate_facts" not in repo:
        repo["stable_candidate_facts"] = {
            "candidate_version": "",
            "candidate_git_tag": "",
            "candidate_channel": "",
            "status": "",
        }
    if "governance_blockers" not in repo:
        repo["governance_blockers"] = []
    if "deploy_target_drift" not in repo:
        repo["deploy_target_drift"] = None

    return repo, wt, operator, slim, warnings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fmt_val(val: Any) -> str:
    """Format a field value for output."""
    if val is None:
        return ""
    if isinstance(val, list):
        if not val:
            return ""
        # For short lists (≤3 items), use inline format
        if all(len(str(item)) < 50 for item in val) and len(val) <= 3:
            return ", ".join(str(item) for item in val)
        # For longer lists, use indented format
        items = "\n".join(f"  - {item}" for item in val)
        return f"\n{items}"
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


def _fmt_field(name: str, val: Any) -> str:
    """Format a single field line."""
    formatted = _fmt_val(val)
    if (
        isinstance(val, list)
        and val
        and (len(val) > 3 or any(len(str(item)) >= 50 for item in val))
    ):
        return f"- {name}:\n{formatted}"
    if "\n" in formatted:
        return f"- {name}:\n{formatted}"
    return f"- {name}: {formatted}"


def _now_iso() -> str:
    """Current time in ISO 8601 with +08:00 timezone."""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def render_repo(fields: dict[str, Any]) -> str:
    """Render control-state-repo.md."""
    now = _now_iso()
    out = f"""---
title: "Harness Control State — Repo Level"
artifact_type: "control-state-repo"
updated: "{now}"
owner: "servo-kernel"
status: "active"
---
# Harness Control State — Repo Level

> 自 2026-06-25 起控制状态拆分为四个文件。
> 本文件维护 Repo + Milestone 级控制状态。
> 已吸收退休的 `.servo/repo/snapshot-status.md` 有效内容。
> 不得将业务真相写入本文件。
> 本文件不持有 `control_state_version` 标签。

## Repo Metadata

{_fmt_field("rotation_count", fields.get("rotation_count", 0))}
{_fmt_field("last_rotation_at", fields.get("last_rotation_at", ""))}
{_fmt_field("handback_history_ref", fields.get("handback_history_ref", []))}

## Repo Control Level

{_fmt_field("repo_scope", fields.get("repo_scope", "uninitialized"))}
{_fmt_field("repo_next_action", fields.get("repo_next_action", ""))}

## Active Worktrack Registry

> 跨 Milestone 的已关闭 Worktrack 注册表。仅追加，可被 compaction 压缩。

{_fmt_field("closed_worktrack_commits", fields.get("closed_worktrack_commits", []))}

## Milestone Pipeline — Active Milestone

{_fmt_field("active_milestone", fields.get("active_milestone", ""))}
{_fmt_field("milestone_status", fields.get("milestone_status", "none"))}
{_fmt_field("milestone_kind", fields.get("milestone_kind", ""))}
{_fmt_field("active_milestone_branch", fields.get("active_milestone_branch", ""))}
{
        _fmt_field(
            "milestone_pipeline_summary",
            fields.get(
                "milestone_pipeline_summary",
                "planned=0 / active=0 / completed=0 / superseded=0",
            ),
        )
    }
{
        _fmt_field(
            "active_milestone_branch_sync_state",
            fields.get("active_milestone_branch_sync_state", "unknown"),
        )
    }
{
        _fmt_field(
            "active_milestone_progress", fields.get("active_milestone_progress", "0/0")
        )
    }
{
        _fmt_field(
            "active_milestone_branch_head",
            fields.get("active_milestone_branch_head", ""),
        )
    }
{
        _fmt_field(
            "milestone_pipeline_path",
            fields.get("milestone_pipeline_path", ".servo/repo/milestone-backlog.md"),
        )
    }
{
        _fmt_field(
            "milestone_intake_confirmed",
            fields.get("milestone_intake_confirmed", False),
        )
    }

## Milestone Pipeline — Review Gate Routing Mirrors

> 本节为路由镜像。真相源见下节 "Milestone Review Gate"。
> 当 `active_milestone_review_gate_status = effective_pass`、`active_milestone_review_count >= 1`、`active_milestone_review_checkpoint` 非空时，才允许 Worktrack Init。

{
        _fmt_field(
            "active_milestone_review_gate_status",
            fields.get("active_milestone_review_gate_status", "missing"),
        )
    }
{
        _fmt_field(
            "active_milestone_review_count",
            fields.get("active_milestone_review_count", 0),
        )
    }
{
        _fmt_field(
            "active_milestone_review_checkpoint",
            fields.get("active_milestone_review_checkpoint", ""),
        )
    }
{
        _fmt_field(
            "active_milestone_review_blockers",
            fields.get(
                "active_milestone_review_blockers", ["milestone_review_gate_not_ready"]
            ),
        )
    }

## Milestone Review Gate

{
        _fmt_field(
            "milestone_review_gate_ready",
            fields.get("milestone_review_gate_ready", False),
        )
    }
{_fmt_field("latest_review_status", fields.get("latest_review_status", "missing"))}
{_fmt_field("milestone_review_count", fields.get("milestone_review_count", 0))}
{_fmt_field("latest_review_checkpoint", fields.get("latest_review_checkpoint", ""))}
{_fmt_field("effective_review_pass", fields.get("effective_review_pass", False))}
{_fmt_field("review_invalidated_by", fields.get("review_invalidated_by", []))}

## Milestone Pipeline — Planning

{_fmt_field("planned_milestone", fields.get("planned_milestone", []))}
{_fmt_field("planned_milestone_status", fields.get("planned_milestone_status", "none"))}
{_fmt_field("planned_milestone_priority", fields.get("planned_milestone_priority", ""))}
{
        _fmt_field(
            "planned_milestone_dependency",
            fields.get("planned_milestone_dependency", ""),
        )
    }
{_fmt_field("accepted_milestone", fields.get("accepted_milestone", ""))}

## Baseline Branch

{_fmt_field("baseline_branch", fields.get("baseline_branch", "develop-servo"))}
{_fmt_field("baseline_ref", fields.get("baseline_ref", ""))}
{_fmt_field("current_checkout", fields.get("current_checkout", ""))}
{_fmt_field("remote_branches", fields.get("remote_branches", ""))}
{_fmt_field("develop_main_head", fields.get("develop_main_head", ""))}
{_fmt_field("develop-servo_head", fields.get("develop-servo_head", ""))}
{_fmt_field("master_head", fields.get("master_head", ""))}

## Branch Environment Guard — Repo Level

> `branch_context_guard_status = blocked` 阻断所有 mutating 操作。

{_fmt_field("current_branch_context", fields.get("current_branch_context", "unknown"))}
{
        _fmt_field(
            "expected_branch_context", fields.get("expected_branch_context", "unknown")
        )
    }
{
        _fmt_field(
            "branch_context_guard_status",
            fields.get("branch_context_guard_status", "blocked"),
        )
    }
{
        _fmt_field(
            "branch_context_required_ref", fields.get("branch_context_required_ref", "")
        )
    }

## Baseline Traceability

> `latest_observed_checkpoint` 与 `last_doc_catch_up_checkpoint` 是 git hash 幂等性锚点。
> 空值表示锚点尚未建立，首次观察必须完整刷新。

{_fmt_field("latest_observed_checkpoint", fields.get("latest_observed_checkpoint", ""))}
{_fmt_field("last_cleanup_checkpoint", fields.get("last_cleanup_checkpoint", ""))}
{
        _fmt_field(
            "last_doc_catch_up_checkpoint",
            fields.get("last_doc_catch_up_checkpoint", ""),
        )
    }
{_fmt_field("milestone_input_checkpoint", fields.get("milestone_input_checkpoint", ""))}
{
        _fmt_field(
            "milestone_review_gate_checkpoint",
            fields.get("milestone_review_gate_checkpoint", ""),
        )
    }
{_fmt_field("checkpoint_ref", fields.get("checkpoint_ref", ""))}
{_fmt_field("release_checkpoint_ref", fields.get("release_checkpoint_ref", ""))}
{_fmt_field("checkpoint_type", fields.get("checkpoint_type", ""))}
{
        _fmt_field(
            "previous_observed_checkpoint",
            fields.get("previous_observed_checkpoint", ""),
        )
    }
{_fmt_field("last_verified_checkpoint", fields.get("last_verified_checkpoint", ""))}
{_fmt_field("if_no_commit_reason", fields.get("if_no_commit_reason", ""))}
{_fmt_field("alternative_traceability", fields.get("alternative_traceability", ""))}
{_fmt_field("verified_at_history", fields.get("verified_at_history", []))}

## Linked Formal Documents — Repo Level

{
        _fmt_field(
            "repo_snapshot",
            fields.get("repo_snapshot", ".servo/repo/snapshot-status.md"),
        )
    }
{_fmt_field("repo_analysis", fields.get("repo_analysis", ""))}

## Release Facts

> 来自退休的 `snapshot-status.md` 的 Release Fact Observations 段。

{_fmt_field("release_facts", _format_release_facts(fields.get("release_facts", {})))}

{_fmt_field("release_boundary_note", fields.get("release_boundary_note", ""))}

{
        _fmt_field(
            "stable_candidate_facts",
            _format_stable_candidate(fields.get("stable_candidate_facts", {})),
        )
    }

## Governance Status

> 来自退休的 `snapshot-status.md` 的 Governance Status 段。

{_fmt_field("governance_blockers", fields.get("governance_blockers", []))}
{_fmt_field("deploy_target_drift", fields.get("deploy_target_drift", ""))}

## Repo Policy

{
        _fmt_field(
            "returning_to_repo_scope_does_not_clear_handoff",
            fields.get("returning_to_repo_scope_does_not_clear_handoff", "yes"),
        )
    }
"""
    return out


def _format_release_facts(rf: Any) -> str:
    """Format release_facts structured block."""
    if isinstance(rf, dict):
        parts = []
        for k, v in rf.items():
            parts.append(f"  - {k}: {v if v else ''}")
        return "\n".join(parts)
    return str(rf) if rf else ""


def _format_stable_candidate(sc: Any) -> str:
    """Format stable_candidate_facts structured block."""
    if isinstance(sc, dict):
        parts = []
        for k, v in sc.items():
            parts.append(f"  - {k}: {v if v else ''}")
        return "\n".join(parts)
    return str(sc) if sc else ""


def render_wt(fields: dict[str, Any]) -> str:
    """Render control-state-wt.md."""
    now = _now_iso()
    out = f"""---
title: "Harness Control State — Worktrack Level"
artifact_type: "control-state-wt"
updated: "{now}"
owner: "servo-kernel"
status: "active"
---
# Harness Control State — Worktrack Level

> 自 2026-06-25 起控制状态拆分为四个文件。
> 本文件维护 Worktrack 级活性控制状态。
> Worktrack 不存在时 (`worktrack_scope = none`) 本文件仍持久存在。
> 缺失字段只能按 artifact 合同默认值降级解释，不能扩大权限。

## Worktrack Control Level

{_fmt_field("worktrack_scope", fields.get("worktrack_scope", "none"))}
{_fmt_field("current_function", fields.get("current_function", ""))}
{_fmt_field("worktrack_next_action", fields.get("worktrack_next_action", ""))}

## Active Worktrack

{_fmt_field("active_worktrack", fields.get("active_worktrack", ""))}
{_fmt_field("active_worktrack_branch", fields.get("active_worktrack_branch", ""))}
{_fmt_field("active_worktrack_node_type", fields.get("active_worktrack_node_type", ""))}
{_fmt_field("active_worktrack_status", fields.get("active_worktrack_status", "none"))}
{_fmt_field("initial_requirement_ref", fields.get("initial_requirement_ref", ""))}
{_fmt_field("finished_handback_ref", fields.get("finished_handback_ref", ""))}
{_fmt_field("implementation_checkpoint", fields.get("implementation_checkpoint", ""))}
{_fmt_field("worktrack_autonomy_policy", fields.get("worktrack_autonomy_policy", "manual-only"))}

## Branch Environment Guard — WT Level

> Worktrack 分支的唯一真相源。不得在其他文件维护镜像。

{_fmt_field("worktrack_branch", fields.get("worktrack_branch", ""))}
"""
    return out


def render_operator(fields: dict[str, Any]) -> str:
    """Render operator-config.md."""
    now = _now_iso()
    out = f"""---
title: "Servo Operator Configuration"
artifact_type: "operator-config"
updated: "{now}"
owner: "servo-kernel"
status: "active"
---
# Servo Operator Configuration

> 自 2026-06-25 起控制状态拆分为四个文件。
> 本文件保存人类可调的控制偏好与长期权限策略。
> 未确认字段按保守默认解释，不扩大权限。
> 一次性审批只写入本轮 evidence/handoff，不改变本文件的长期默认值。
> 仅当 programmer 明确表达持久授权或更改默认策略时，才可更新本文件。
>
> `runtime_dispatch_profile` 及其 12 子字段已从本文件删除。
> 运行时字段以本文件内联结构、随包脚本与当前 `.servo` artifacts 为准。
> 运行时填充逻辑不变 (由 Dispatch 步骤写入本轮 evidence)。

## User-Defined Servo Controls

> 初始化时只询问用户可定义的控制偏好；不要询问 Servo 可自动维护的 runtime facts。
> 未确认字段按保守默认解释，不扩大权限。

{
        _fmt_field(
            "continuous_progression_permission",
            fields.get(
                "continuous_progression_permission", "pending_programmer_confirmation"
            ),
        )
    }
{
        _fmt_field(
            "per_milestone_automatic_worktrack_budget",
            fields.get(
                "per_milestone_automatic_worktrack_budget",
                "pending_programmer_confirmation",
            ),
        )
    }
{
        _fmt_field(
            "default_servo_work_branch",
            fields.get("default_servo_work_branch", "pending_programmer_confirmation"),
        )
    }
{
        _fmt_field(
            "protected_branch_policy",
            fields.get("protected_branch_policy", "pending_programmer_confirmation"),
        )
    }
{
        _fmt_field(
            "branch_mutation_policy",
            fields.get("branch_mutation_policy", "pending_programmer_confirmation"),
        )
    }

## Auto-Maintained Runtime Facts Exclusion

> 初始化时禁止向用户询问的字段范围。本列表不能替代 skill 实现中的逻辑。

{
        _fmt_field(
            "auto_maintained_runtime_facts_not_asked",
            fields.get(
                "auto_maintained_runtime_facts_not_asked",
                [
                    "active_milestone",
                    "active_worktrack",
                    "observed_git_hash",
                    "progress_counters",
                    "runtime_dispatch_profile",
                    "latest_observed_checkpoint",
                    "last_doc_catch_up_checkpoint",
                    "milestone_pipeline_summary",
                ],
            ),
        )
    }

## Continuation Authority

> `subagent_dispatch_mode` 是使用 SubAgent 的 repo 级默认开关。
> `subagent_dispatch_mode_override_scope: worktrack-contract-primary` 表示默认让工作追踪内的 `runtime_dispatch_mode` 优先。
> 用户授予的长期权限、自动性或分派策略变更必须写入本段或 Autonomy Ledger；一次性审批只写入本轮 evidence / handoff，不改变长期默认值。

{
        _fmt_field(
            "post_contract_autonomy",
            fields.get("post_contract_autonomy", "manual-only"),
        )
    }
{_fmt_field("autonomy_scope", fields.get("autonomy_scope", "current-goal-only"))}
{_fmt_field("max_auto_new_worktracks", fields.get("max_auto_new_worktracks", 1))}
{
        _fmt_field(
            "stop_after_autonomous_slice",
            fields.get("stop_after_autonomous_slice", "yes"),
        )
    }
{_fmt_field("subagent_dispatch_mode", fields.get("subagent_dispatch_mode", "auto"))}
{
        _fmt_field(
            "subagent_dispatch_mode_override_scope",
            fields.get(
                "subagent_dispatch_mode_override_scope", "worktrack-contract-primary"
            ),
        )
    }
{_fmt_field("subagent_default_model", fields.get("subagent_default_model", ""))}
{_fmt_field("persistent_authority_notes", fields.get("persistent_authority_notes", ""))}
"""
    return out


def render_slim(fields: dict[str, Any]) -> str:
    """Render control-state.md (精简版)."""
    now = _now_iso()
    out = f"""---
title: "Harness Control State"
artifact_type: "control-state"
control_state_version: split
generated_from: "harness-skill"
updated: "{now}"
owner: "servo-kernel"
status: "active"
---
# Harness Control State

> 自 2026-06-25 起控制状态拆分为四个文件，本文件仅保留跨 Repo/Worktrack 的控制记忆。
> Repo + Milestone 级字段 → `.servo/control-state-repo.md`
> Worktrack 级字段 → `.servo/control-state-wt.md`
> 人类可调配置 → `.servo/operator-config.md`
>
> `control_state_version: split` 是必填 frontmatter 字段，触发分拆文件 hydration。
> 缺失字段只能按 artifact 合同默认值降级解释，不能扩大权限。

## Handback Guard

> 跨 Repo/Worktrack 的 Handback 交接状态。
> `handoff_state = awaiting-handoff` 且 `handback_lock_active = true` → 仅显式 unlock signal 可解除。
> Worktrack 关闭后返回 RepoScope 不得自动清空 `handoff_state`。

{_fmt_field("handoff_state", fields.get("handoff_state", "none"))}
{_fmt_field("last_handback_signature", fields.get("last_handback_signature", ""))}
{_fmt_field("handback_reaffirmed_rounds", fields.get("handback_reaffirmed_rounds", 0))}
{_fmt_field("stable_handback_threshold", fields.get("stable_handback_threshold", 2))}
{_fmt_field("handback_lock_active", fields.get("handback_lock_active", "false"))}
{_fmt_field("last_unlock_signal", fields.get("last_unlock_signal", "N/A"))}
{_fmt_field("stop_reason_history", fields.get("stop_reason_history", []))}

## Approval Boundary

> 跨层审批边界。`approval_persistence = one-shot` 在当前审批消费后，下次 handback 时清理。

{_fmt_field("needs_programmer_approval", fields.get("needs_programmer_approval", "yes"))}
{_fmt_field("reason", fields.get("reason", ""))}
{_fmt_field("approval_scope", fields.get("approval_scope", ""))}
{_fmt_field("approval_persistence", fields.get("approval_persistence", "one-shot"))}

## Worktrack Pointers

> Candidate Worktrack 持久入口、完成交接与当前实现 checkpoint 指针。
> 无活跃或已完成 Worktrack 时，对应字段可以为空。

{_fmt_field("initial_requirement_ref", fields.get("initial_requirement_ref", ""))}
{_fmt_field("finished_handback_ref", fields.get("finished_handback_ref", ""))}
{_fmt_field("implementation_checkpoint", fields.get("implementation_checkpoint", ""))}

## Autonomy Ledger

> 跨层 autonomy 预算追踪。`autonomy_budget_remaining` 从 `operator-config.md` 的 `max_auto_new_worktracks` 初始化。
> `autonomy_budget_remaining <= 0` → 不得开启新的 autonomous slice。

{_fmt_field("autonomy_budget_remaining", fields.get("autonomy_budget_remaining", 0))}
{_fmt_field("autonomous_worktracks_opened", fields.get("autonomous_worktracks_opened", 0))}
"""
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _count_fields(rendered: str) -> int:
    """Count how many `- field_name:` lines exist in rendered output."""
    return len(re.findall(r"^- (\S+):", rendered, re.MULTILINE))


def main():
    parser = argparse.ArgumentParser(
        description="Split Control State — 旧版单文件 → 四文件架构"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["dry-run", "apply"],
        help="dry-run: preview only; apply: write files to .servo/",
    )
    parser.add_argument(
        "--input", required=True, help="Path to legacy .servo/control-state.md"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing split files in apply mode",
    )
    args = parser.parse_args()

    # Validate input exists
    if not os.path.exists(args.input):
        result = {
            "status": "error",
            "error": f"Input file not found: {args.input}",
            "files_written": [],
            "fields_migrated": 0,
            "warnings": [],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Determine output directory (same directory as input, i.e., .servo/)
    output_dir = os.path.dirname(os.path.abspath(args.input)) or "."

    # Output file paths
    output_files = {
        "repo": os.path.join(output_dir, "control-state-repo.md"),
        "wt": os.path.join(output_dir, "control-state-wt.md"),
        "operator": os.path.join(output_dir, "operator-config.md"),
        "slim": os.path.join(output_dir, "control-state.md"),
    }

    # Check for existing split files in apply mode without --force
    if args.mode == "apply" and not args.force:
        existing = [p for p in output_files.values() if os.path.exists(p)]
        if existing:
            result = {
                "status": "error",
                "error": (
                    "Target files already exist. Use --force to overwrite, "
                    "or review with --mode dry-run first."
                ),
                "existing_files": [os.path.basename(p) for p in existing],
                "files_written": [],
                "fields_migrated": 0,
                "warnings": [],
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

    # Parse legacy control-state.md
    try:
        all_fields = parse_legacy_control_state(args.input)
    except Exception as e:
        result = {
            "status": "error",
            "error": f"Failed to parse {args.input}: {e}",
            "files_written": [],
            "fields_migrated": 0,
            "warnings": [],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Map to four output dicts
    repo, wt, operator, slim, warnings = map_fields_to_outputs(all_fields)

    # Render each file
    renderers = {
        "repo": (render_repo, repo),
        "wt": (render_wt, wt),
        "operator": (render_operator, operator),
        "slim": (render_slim, slim),
    }

    rendered: dict[str, str] = {}
    field_counts: dict[str, int] = {}
    for key, (render_fn, fields_dict) in renderers.items():
        content = render_fn(fields_dict)
        rendered[key] = content
        field_counts[key] = _count_fields(content)

    total_fields = sum(field_counts.values())
    warnings.append(
        "Field counts per file: "
        + ", ".join(f"{k}={v}" for k, v in field_counts.items())
        + f" (total={total_fields})"
    )

    # Output JSON result
    result = {
        "status": "ok",
        "mode": args.mode,
        "input": args.input,
        "input_size_lines": len(open(args.input).read().split("\n")),
        "fields_migrated": total_fields,
        "field_counts_per_file": field_counts,
        "files_written": [],
        "warnings": warnings,
    }

    if args.mode == "dry-run":
        result["preview"] = {
            "files": {
                k: v[:500] + "..." if len(v) > 500 else v for k, v in rendered.items()
            }
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Apply mode — write files
        written = []
        for key, path in output_files.items():
            content = rendered[key]
            with open(path, "w") as f:
                f.write(content)
            written.append(os.path.basename(path))

        result["files_written"] = written
        result["output_dir"] = output_dir
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
