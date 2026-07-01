#!/usr/bin/env python3
"""Check cross-layer synchronization between docs contracts and implementation templates.

Checks:
  1. artifact contract (docs/harness/artifact/worktrack/contract.md)
     ↔ skill template (product/harness/skills/worktrack-init-skill/templates/contract.template.md)
  2. tracked goal-charter template source
     (product/harness/skills/repo-init-goal-skill/assets/goal-charter.md)
     ↔ node-type-registry (docs/harness/artifact/control/node-type-registry.md)
  3. control-state contract (docs/harness/artifact/control/control-state.md)
     ↔ repo-init-goal template (product/harness/skills/repo-init-goal-skill/assets/control-state.md)
  4. plan-task-queue contract (docs/harness/artifact/worktrack/plan-task-queue.md)
     ↔ runtime and schedule skill templates
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]

# ── file paths ──────────────────────────────────────────────────────────────────
CONTRACT_PATH = "docs/harness/artifact/worktrack/contract.md"
CONTRACT_TEMPLATE_PATH = (
    "product/harness/skills/worktrack-init-skill/templates/contract.template.md"
)
GOAL_CHARTER_SOURCE_PATH = (
    "product/harness/skills/repo-init-goal-skill/assets/goal-charter.md"
)
RUNTIME_CHARTER_PATH = ".servo/goal-charter.md"
REGISTRY_PATH = "docs/harness/artifact/control/node-type-registry.md"
CONTROL_STATE_CONTRACT_PATH = "docs/harness/artifact/control/control-state.md"
CONTROL_STATE_TEMPLATE_PATH = (
    "product/harness/skills/repo-init-goal-skill/assets/control-state.md"
)
PLAN_TASK_QUEUE_CONTRACT_PATH = "docs/harness/artifact/worktrack/plan-task-queue.md"
PLAN_TASK_QUEUE_TEMPLATE_PATHS = [
    "product/.servo_template/worktrack/plan-task-queue.md",
    "product/harness/skills/worktrack-schedule-skill/templates/plan-task-queue.template.md",
    "product/harness/skills/repo-init-goal-skill/assets/worktrack/plan-task-queue.md",
]

# ── key fields for check 1 ──────────────────────────────────────────────────────
# Fields under Node Type in the contract's "上游输入" section
NODE_TYPE_FIELDS = [
    "type",
    "source_from_goal_charter",
    "baseline_form",
    "merge_required",
    "gate_criteria",
    "if_interrupted_strategy",
]

# Fields under Execution Policy in the contract's "上游输入" section
EXECUTION_POLICY_FIELDS = [
    "runtime_dispatch_mode",
    "dispatch_mode_source",
    "allowed_values",
    "fallback_reason_required",
]

# ── key fields for check 3 ──────────────────────────────────────────────────────
# Handback Guard fields defined in control-state contract
HANDBACK_GUARD_FIELDS = [
    "handoff_state",
    "last_stop_reason",
    "last_handback_signature",
    "handback_reaffirmed_rounds",
    "stable_handback_threshold",
    "handback_lock_active",
    "last_unlock_signal",
    "autonomy_budget_remaining",
    "autonomous_worktracks_opened",
]
USER_DEFINED_SERVO_CONTROL_FIELDS = [
    "continuous_progression_permission",
    "per_milestone_automatic_worktrack_budget",
    "default_servo_work_branch",
    "protected_branch_policy",
    "branch_mutation_policy",
    "auto_maintained_runtime_facts_not_asked",
]
PLAN_TASK_QUEUE_WINDOW_FIELDS = [
    "task_window_id",
    "window_boundary",
    "selected_next_action_id",
    "selected_next_action",
    "dispatch_handoff_packet",
    "depends_on",
    "acceptance",
    "risk_level",
    "stop_condition",
]


# ═══════════════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════════════


def _read(repo_root: Path, relative_path: str) -> str | None:
    """Return file text or None when the file is missing."""
    path = repo_root / relative_path
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _extract_field_names_from_text(
    text: str, section_heading: str | None = None
) -> set[str]:
    """Extract ``- field_name:`` patterns from markdown text.

    When *section_heading* is given, extraction is limited to the section
    between that heading (##-level) and the next heading of equal-or-higher
    rank.
    """
    if section_heading is not None:
        # scope to the target section
        pattern = re.compile(
            rf"^{re.escape(section_heading)}\s*$",
            re.MULTILINE,
        )
        m = pattern.search(text)
        if not m:
            return set()
        start = m.end()
        # find next ##-level heading (or end of text)
        next_heading = re.compile(r"^##\s", re.MULTILINE)
        m2 = next_heading.search(text, start)
        end = m2.start() if m2 else len(text)
        text = text[start:end]

    fields: set[str] = set()
    for m in re.finditer(r"^- (\w[\w_]*):", text, re.MULTILINE):
        fields.add(m.group(1))
    return fields


# ═══════════════════════════════════════════════════════════════════════════════════
# check 1: artifact contract ↔ skill template field alignment
# ═══════════════════════════════════════════════════════════════════════════════════


def check_contract_template_alignment(repo_root: Path) -> dict:
    """Check artifact contract fields align with skill templates.

    Key fields in the contract's "上游输入" section (Node Type and Execution
    Policy sub-fields) must also appear in the skill template.
    """
    errors: list[str] = []
    infos: list[str] = []

    contract_text = _read(repo_root, CONTRACT_PATH)
    template_text = _read(repo_root, CONTRACT_TEMPLATE_PATH)

    if contract_text is None:
        errors.append(f"missing contract file: {CONTRACT_PATH}")
    if template_text is None:
        errors.append(f"missing template file: {CONTRACT_TEMPLATE_PATH}")

    if errors:
        return {
            "status": "fail",
            "summary": f"{len(errors)} missing file(s)",
            "errors": errors,
            "infos": infos,
        }

    # --- Node Type fields ---
    template_node_fields = _extract_field_names_from_text(
        template_text, section_heading="## Node Type"
    )
    missing_nt = [
        f for f in NODE_TYPE_FIELDS if f not in template_node_fields
    ]
    for f in missing_nt:
        errors.append(
            f"Node Type field '{f}' in contract ({CONTRACT_PATH}) "
            f"not found in template ({CONTRACT_TEMPLATE_PATH})"
        )
    infos.append(
        f"checked {len(NODE_TYPE_FIELDS)} Node Type fields: "
        f"{len(NODE_TYPE_FIELDS) - len(missing_nt)}/{len(NODE_TYPE_FIELDS)} present"
    )

    # --- Execution Policy fields ---
    template_ep_fields = _extract_field_names_from_text(
        template_text, section_heading="## Execution Policy"
    )
    missing_ep = [
        f for f in EXECUTION_POLICY_FIELDS if f not in template_ep_fields
    ]
    for f in missing_ep:
        errors.append(
            f"Execution Policy field '{f}' in contract ({CONTRACT_PATH}) "
            f"not found in template ({CONTRACT_TEMPLATE_PATH})"
        )
    infos.append(
        f"checked {len(EXECUTION_POLICY_FIELDS)} Execution Policy fields: "
        f"{len(EXECUTION_POLICY_FIELDS) - len(missing_ep)}/{len(EXECUTION_POLICY_FIELDS)} present"
    )

    status = "pass" if not errors else "fail"
    return {
        "status": status,
        "summary": (
            "all contract fields present in template"
            if status == "pass"
            else f"{len(errors)} field(s) missing from template"
        ),
        "errors": errors,
        "infos": infos,
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# check 2: tracked goal-charter source ↔ node-type-registry consistency
# ═══════════════════════════════════════════════════════════════════════════════════


def _extract_charter_node_types(text: str) -> set[str]:
    """Extract node type names from the goal-charter markdown.

    Sources:
      - "Node Type Registry" table (first column, backtick-quoted)
      - "This Goal's Node Types" list (``- type: <name>`` lines)
    """
    types: set[str] = set()

    # From the table (after "### Node Type Registry" up to the next heading)
    table_section_pattern = re.compile(
        r"^### Node Type Registry\s*$(.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = table_section_pattern.search(text)
    if m:
        table_text = m.group(1)
        # Match first column of data rows: | `typename` | ...
        for row in re.finditer(
            r"^\|\s*`(\w[\w-]*)`\s*\|", table_text, re.MULTILINE
        ):
            types.add(row.group(1))

    # From "This Goal's Node Types" list
    list_section_pattern = re.compile(
        r"^### This Goal's Node Types\s*$(.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = list_section_pattern.search(text)
    if m:
        list_text = m.group(1)
        for match in re.finditer(r"^- type:\s*(\w[\w-]*)", list_text, re.MULTILINE):
            types.add(match.group(1))

    return types


def _extract_registry_node_types(text: str) -> set[str]:
    """Extract node type names from the node-type-registry (``### <type>`` headings)."""
    types: set[str] = set()
    for m in re.finditer(r"^### (\w[\w-]*)\s*$", text, re.MULTILINE):
        candidate = m.group(1)
        # Skip non-type headings like "Gate Criteria 组合语义", "使用约定", etc.
        if candidate in (
            "gate",
            "node",
            "使用约定",
            "gate-criteria-组合语义",
        ):
            continue
        # Skip Chinese headings
        if re.search(r"[一-鿿]", candidate):
            continue
        types.add(candidate)
    return types


def check_charter_registry_consistency(repo_root: Path) -> dict:
    """Check tracked goal-charter source node types exist in the registry.

    ``.servo/goal-charter.md`` is an ignored runtime instance. Clean CI checkouts
    must not require it, and this governance check must not promote runtime
    state into canonical source truth.
    """
    errors: list[str] = []
    infos: list[str] = []

    charter_text = _read(repo_root, GOAL_CHARTER_SOURCE_PATH)
    registry_text = _read(repo_root, REGISTRY_PATH)

    if charter_text is None:
        errors.append(f"missing tracked charter source: {GOAL_CHARTER_SOURCE_PATH}")
    if registry_text is None:
        errors.append(f"missing registry file: {REGISTRY_PATH}")

    if errors:
        return {
            "status": "fail",
            "summary": f"{len(errors)} missing file(s)",
            "errors": errors,
            "infos": infos,
        }

    charter_types = _extract_charter_node_types(charter_text)
    registry_types = _extract_registry_node_types(registry_text)

    if not charter_types:
        errors.append(
            f"could not extract any node types from tracked charter source "
            f"({GOAL_CHARTER_SOURCE_PATH})"
        )
    if not registry_types:
        errors.append(
            f"could not extract any node types from registry ({REGISTRY_PATH})"
        )

    missing = charter_types - registry_types
    for t in sorted(missing):
        errors.append(
            f"node type '{t}' referenced in tracked charter source "
            f"({GOAL_CHARTER_SOURCE_PATH}) "
            f"but not defined in registry ({REGISTRY_PATH})"
        )

    infos.append(
        f"tracked charter source declares {len(charter_types)} type(s): "
        f"{', '.join(sorted(charter_types))}"
    )
    infos.append(
        f"registry defines {len(registry_types)} type(s): {', '.join(sorted(registry_types))}"
    )
    if (repo_root / RUNTIME_CHARTER_PATH).is_file():
        infos.append(
            f"runtime charter instance present but not authoritative for this check: "
            f"{RUNTIME_CHARTER_PATH}"
        )
    else:
        infos.append(
            f"runtime charter instance absent; clean CI uses tracked source: "
            f"{GOAL_CHARTER_SOURCE_PATH}"
        )

    status = "pass" if not errors else "fail"
    return {
        "status": status,
        "summary": (
            "all charter node types defined in registry"
            if status == "pass"
            else f"{len(missing)} charter type(s) missing from registry"
        ),
        "errors": errors,
        "infos": infos,
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# check 3: control-state contract ↔ repo-init-goal template consistency
# ═══════════════════════════════════════════════════════════════════════════════════


def check_control_state_template_alignment(repo_root: Path) -> dict:
    """Check control-state contract Handback Guard fields align with template."""
    errors: list[str] = []
    infos: list[str] = []

    contract_text = _read(repo_root, CONTROL_STATE_CONTRACT_PATH)
    template_text = _read(repo_root, CONTROL_STATE_TEMPLATE_PATH)

    if contract_text is None:
        errors.append(f"missing contract file: {CONTROL_STATE_CONTRACT_PATH}")
    if template_text is None:
        errors.append(f"missing template file: {CONTROL_STATE_TEMPLATE_PATH}")

    if errors:
        return {
            "status": "fail",
            "summary": f"{len(errors)} missing file(s)",
            "errors": errors,
            "infos": infos,
        }

    # Collect field names from the template — look across the whole file
    # because autonomy_budget_remaining / autonomous_worktracks_opened live
    # under "## Autonomy Ledger", not "## Handback Guard".
    template_fields = _extract_field_names_from_text(template_text)

    # Also collect field names specifically under "## Handback Guard"
    template_hb_fields = _extract_field_names_from_text(
        template_text, section_heading="## Handback Guard"
    )

    missing = [f for f in HANDBACK_GUARD_FIELDS if f not in template_fields]
    for f in missing:
        # Distinguish "defined in contract but entirely absent" vs
        # "present in contract but placed under a different section"
        errors.append(
            f"Handback Guard field '{f}' defined in contract "
            f"({CONTROL_STATE_CONTRACT_PATH}) not found in template "
            f"({CONTROL_STATE_TEMPLATE_PATH})"
        )

    present = len(HANDBACK_GUARD_FIELDS) - len(missing)
    infos.append(
        f"checked {len(HANDBACK_GUARD_FIELDS)} Handback Guard fields: "
        f"{present}/{len(HANDBACK_GUARD_FIELDS)} present in template"
    )
    if template_hb_fields:
        infos.append(
            f"template Handback Guard section fields: "
            f"{', '.join(sorted(template_hb_fields))}"
        )

    missing_controls = [
        f for f in USER_DEFINED_SERVO_CONTROL_FIELDS if f not in template_fields
    ]
    for f in missing_controls:
        errors.append(
            f"User-Defined Servo Controls field '{f}' defined in contract "
            f"({CONTROL_STATE_CONTRACT_PATH}) not found in template "
            f"({CONTROL_STATE_TEMPLATE_PATH})"
        )
    controls_present = len(USER_DEFINED_SERVO_CONTROL_FIELDS) - len(missing_controls)
    infos.append(
        f"checked {len(USER_DEFINED_SERVO_CONTROL_FIELDS)} User-Defined Servo Controls "
        f"fields: {controls_present}/{len(USER_DEFINED_SERVO_CONTROL_FIELDS)} present in template"
    )

    status = "pass" if not errors else "fail"
    return {
        "status": status,
        "summary": (
            "all Handback Guard and User-Defined Servo Controls fields present in template"
            if status == "pass"
            else f"{len(missing) + len(missing_controls)} control-state field(s) missing from template"
        ),
        "errors": errors,
        "infos": infos,
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# check 4: plan-task-queue contract ↔ runtime/schedule templates
# ═══════════════════════════════════════════════════════════════════════════════════


def check_plan_task_queue_template_alignment(repo_root: Path) -> dict:
    """Check Plan / Task Queue task-window fields align with templates."""
    errors: list[str] = []
    infos: list[str] = []

    contract_text = _read(repo_root, PLAN_TASK_QUEUE_CONTRACT_PATH)
    if contract_text is None:
        errors.append(f"missing contract file: {PLAN_TASK_QUEUE_CONTRACT_PATH}")
    else:
        for field in PLAN_TASK_QUEUE_WINDOW_FIELDS:
            if field not in contract_text:
                errors.append(
                    f"Plan / Task Queue field '{field}' not found in contract "
                    f"({PLAN_TASK_QUEUE_CONTRACT_PATH})"
                )

    for template_path in PLAN_TASK_QUEUE_TEMPLATE_PATHS:
        template_text = _read(repo_root, template_path)
        if template_text is None:
            errors.append(f"missing template file: {template_path}")
            continue
        missing = [
            field for field in PLAN_TASK_QUEUE_WINDOW_FIELDS if field not in template_text
        ]
        for field in missing:
            errors.append(
                f"Plan / Task Queue field '{field}' in contract "
                f"({PLAN_TASK_QUEUE_CONTRACT_PATH}) not found in template ({template_path})"
            )
        infos.append(
            f"checked {len(PLAN_TASK_QUEUE_WINDOW_FIELDS)} Plan / Task Queue fields in "
            f"{template_path}: {len(PLAN_TASK_QUEUE_WINDOW_FIELDS) - len(missing)}/"
            f"{len(PLAN_TASK_QUEUE_WINDOW_FIELDS)} present"
        )

    status = "pass" if not errors else "fail"
    return {
        "status": status,
        "summary": (
            "all Plan / Task Queue task-window fields present in templates"
            if status == "pass"
            else f"{len(errors)} plan-task-queue field alignment issue(s)"
        ),
        "errors": errors,
        "infos": infos,
    }


# ═══════════════════════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check cross-layer synchronization (docs ↔ impl)."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON only."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()

    results: dict[str, dict] = {
        "contract_template": check_contract_template_alignment(repo_root),
        "charter_registry": check_charter_registry_consistency(repo_root),
        "control_state_template": check_control_state_template_alignment(repo_root),
        "plan_task_queue_template": check_plan_task_queue_template_alignment(repo_root),
    }

    all_pass = all(r["status"] == "pass" for r in results.values())

    if args.json:
        payload: dict = {
            "status": "pass" if all_pass else "fail",
            "checks": results,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for name, result in results.items():
            status_label = "PASS" if result["status"] == "pass" else "FAIL"
            print(f"  {name}: {status_label} - {result.get('summary', '')}")
            for info in result.get("infos", []):
                print(f"    info: {info}")
            for err in result.get("errors", []):
                print(f"    error: {err}")

        if all_pass:
            print("cross-layer sync checks passed")
        else:
            print("cross-layer sync checks failed")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
