#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REQUIRED_SECTIONS = (
    "## Current Control Level",
    "## Active Worktrack",
    "## Milestone Pipeline",
    "## Baseline Branch",
    "## Current Next Action",
    "## Baseline Traceability",
)

REQUIRED_FIELDS = (
    "repo_scope",
    "worktrack_scope",
    "current_function",
    "active_worktrack",
    "active_worktrack_branch",
    "active_worktrack_node_type",
    "active_milestone",
    "milestone_status",
    "active_milestone_branch",
    "active_milestone_branch_head",
    "baseline_branch",
    "current_checkout",
    "recommended_next_route",
    "recommended_next_scope",
    "latest_observed_checkpoint",
    "checkpoint_ref",
)

CONDITIONAL_FIELDS = {
    "branch_guard": (
        "branch_guard",
        "branch_guard_status",
        "protected_branch_policy",
        "active_worktrack_branch",
        "active_milestone_branch",
        "baseline_branch",
        "current_checkout",
    ),
    "review_gate": (
        "review_gate",
        "review_gate_status",
        "gate_status",
        "active_milestone_review_gate_status",
        "milestone_review_gate_ready",
        "milestone_review_gate_checkpoint",
    ),
    "approval_boundary": (
        "approval_boundary",
        "approval_required",
        "approval_status",
        "approval_mode",
        "needs_programmer_approval",
        "approval_scope",
        "approval_persistence",
    ),
    "continuation_authority": (
        "post_contract_autonomy",
        "continuation_authority",
        "autonomy_mode",
    ),
    "handback_guard": ("handoff_state", "handback_guard", "handback_state"),
    "autonomy_ledger": (
        "autonomy_budget_remaining",
        "autonomy_ledger",
        "post_contract_autonomy",
    ),
}

FOLDABLE_KEYS = (
    "latest_closed_worktrack_commit",
    "verified_at",
    "last_stop_reason",
    "handback_note",
    "closeout_summary",
    "checkpoint_note",
)

FIELD_PATTERN = re.compile(r"^\s*-?\s*([A-Za-z0-9_-]+)\s*:\s*(.*)$")
HANDBACK_REF_PATTERN = re.compile(r"^(\s*-?\s*handback_history_ref\s*:\s*)(.*)$")


@dataclass(frozen=True)
class ValidationResult:
    missing_sections: list[str]
    missing_fields: list[str]
    missing_groups: list[str]

    @property
    def ok(self) -> bool:
        return (
            not self.missing_sections
            and not self.missing_fields
            and not self.missing_groups
        )

    def errors(self) -> list[str]:
        errors: list[str] = []
        if self.missing_sections:
            errors.append(
                "missing required control-state sections: "
                + ", ".join(self.missing_sections)
            )
        if self.missing_fields:
            errors.append(
                "missing required control-state fields: "
                + ", ".join(self.missing_fields)
            )
        if self.missing_groups:
            errors.append(
                "missing required control-state semantic groups: "
                + ", ".join(self.missing_groups)
            )
        return errors


@dataclass(frozen=True)
class CompactionPlan:
    compacted_text: str
    externalized_lines: list[str]
    history_ref: str | None

    @property
    def would_change(self) -> bool:
        return bool(self.externalized_lines)


def field_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        match = FIELD_PATTERN.match(line)
        if match:
            names.add(match.group(1))
    return names


def validate_control_state(text: str) -> ValidationResult:
    names = field_names(text)
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
    missing_fields = [field for field in REQUIRED_FIELDS if field not in names]
    missing_groups = [
        group
        for group, aliases in CONDITIONAL_FIELDS.items()
        if not any(alias in names for alias in aliases)
    ]
    return ValidationResult(missing_sections, missing_fields, missing_groups)


def normalize_path_for_policy(path: Path) -> str:
    return path.as_posix().replace("\\", "/").lower()


def is_disallowed_backup_path(path: Path) -> bool:
    normalized = normalize_path_for_policy(path)
    parts = normalized.split("/")
    for index, part in enumerate(parts[:-1]):
        if part == ".servo" and parts[index + 1] in {"backup", "backups"}:
            return True
    disallowed_fragments = (
        "/.servo/backup/",
        "/.servo/backups/",
        "/.servo/backup",
        "/.servo/backups",
        ".servo/backup/",
        ".servo/backups/",
        ".servo/backup",
        ".servo/backups",
    )
    return any(fragment in normalized for fragment in disallowed_fragments)


def default_history_dir(control_state_path: Path) -> Path:
    servo_root = control_state_path.parent
    return servo_root / "history" / "control-state"


def repo_relative_ref(path: Path) -> str:
    parts = path.parts
    if ".servo" in parts:
        servo_index = parts.index(".servo")
        return Path(*parts[servo_index:]).as_posix()
    return path.as_posix()


def history_artifact_text(
    *,
    source_path: Path,
    source_hash: str,
    created_at: str,
    externalized_lines: Sequence[str],
) -> str:
    body = "\n".join(externalized_lines)
    if body:
        body = body + "\n"
    preserved_fields = "\n".join(f"- {field}" for field in REQUIRED_FIELDS)
    return (
        "# Control-state Compaction History\n\n"
        "## Metadata\n\n"
        f"- source: {source_path.as_posix()}\n"
        f"- source_sha256: {source_hash}\n"
        f"- created_at: {created_at}\n"
        "- generated_by: milestone-cleanup-skill/scripts/control_state_compact.py\n\n"
        "## Preserved Field Summary\n\n"
        f"{preserved_fields}\n\n"
        "## Externalized Sections\n\n"
        "```text\n"
        f"{body}"
        "```\n"
    )


def update_handback_history_ref(lines: list[str], history_ref: str) -> list[str]:
    updated: list[str] = []
    replaced = False
    for line in lines:
        match = HANDBACK_REF_PATTERN.match(line)
        if match:
            prefix = match.group(1)
            if not prefix.endswith(" "):
                prefix = prefix + " "
            updated.append(f"{prefix}{history_ref}")
            replaced = True
        else:
            updated.append(line)

    if replaced:
        return updated

    insert_at = 0
    for index, line in enumerate(updated):
        if line.startswith("## Current Control Level"):
            insert_at = index
            break
    updated.insert(insert_at, f"handback_history_ref: {history_ref}")
    return updated


def build_compaction_plan(text: str, history_ref: str | None) -> CompactionPlan:
    seen_foldable: set[str] = set()
    externalized: list[str] = []
    kept: list[str] = []

    for line in text.splitlines():
        match = FIELD_PATTERN.match(line)
        field_name = match.group(1) if match else None
        if field_name in FOLDABLE_KEYS:
            if field_name in seen_foldable:
                externalized.append(line)
                continue
            seen_foldable.add(field_name)
        kept.append(line)

    if externalized and history_ref:
        kept = update_handback_history_ref(kept, history_ref)

    trailing_newline = "\n" if text.endswith("\n") else ""
    compacted_text = "\n".join(kept) + trailing_newline
    return CompactionPlan(
        compacted_text, externalized, history_ref if externalized else None
    )


def report_payload(
    *,
    mode: str,
    control_state: Path,
    would_change: bool,
    changed: bool,
    preserved_validation: ValidationResult,
    externalized_lines: Sequence[str],
    history_ref: str | None,
    verdict: str,
    errors: Sequence[str],
    recommendations: Sequence[str],
) -> dict[str, object]:
    return {
        "cleanup_type": "control_state_compact",
        "mode": mode,
        "control_state": control_state.as_posix(),
        "would_change": would_change,
        "changed": changed,
        "preserved_fields": {
            "required_sections": list(REQUIRED_SECTIONS),
            "required_fields": list(REQUIRED_FIELDS),
            "semantic_groups": {
                key: list(value) for key, value in CONDITIONAL_FIELDS.items()
            },
            "missing_sections": preserved_validation.missing_sections,
            "missing_fields": preserved_validation.missing_fields,
            "missing_groups": preserved_validation.missing_groups,
        },
        "externalized_sections": list(externalized_lines),
        "history_artifact_ref": history_ref or "N/A",
        "post_verify_verdict": verdict,
        "errors": list(errors),
        "recommendations": list(recommendations),
    }


def emit_report(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(f"cleanup_type: {payload['cleanup_type']}")
    print(f"mode: {payload['mode']}")
    print(f"would_change: {payload['would_change']}")
    print(f"changed: {payload['changed']}")
    print(f"history_artifact_ref: {payload['history_artifact_ref']}")
    print(f"post_verify_verdict: {payload['post_verify_verdict']}")
    errors = payload["errors"]
    if isinstance(errors, list) and errors:
        print("errors:")
        for error in errors:
            print(f"- {error}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely compact duplicate history lines in .servo/control-state.md."
    )
    parser.add_argument(
        "--control-state",
        default=".servo/control-state.md",
        type=Path,
        help="Path to the control-state markdown file.",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Directory for generated compaction history artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan compaction without writing files. This is the default.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the compacted control-state and generated history artifact.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    control_state = args.control_state
    apply_changes = bool(args.apply)
    mode = "apply" if apply_changes else "dry-run"

    if args.apply and args.dry_run:
        validation = ValidationResult([], [], [])
        payload = report_payload(
            mode="invalid",
            control_state=control_state,
            would_change=False,
            changed=False,
            preserved_validation=validation,
            externalized_lines=[],
            history_ref=None,
            verdict="blocked",
            errors=["--apply and --dry-run cannot be used together"],
            recommendations=["Choose either --dry-run or --apply."],
        )
        emit_report(payload, as_json=args.json)
        return 2

    history_dir = args.history_dir or default_history_dir(control_state)
    if is_disallowed_backup_path(history_dir):
        validation = ValidationResult([], [], [])
        payload = report_payload(
            mode=mode,
            control_state=control_state,
            would_change=False,
            changed=False,
            preserved_validation=validation,
            externalized_lines=[],
            history_ref=None,
            verdict="blocked",
            errors=[
                "history-dir must not point at installer-generated .servo backup paths"
            ],
            recommendations=[
                "Use a generated compaction history path such as .servo/history/control-state."
            ],
        )
        emit_report(payload, as_json=args.json)
        return 2

    if not control_state.is_file():
        validation = ValidationResult([], [], [])
        payload = report_payload(
            mode=mode,
            control_state=control_state,
            would_change=False,
            changed=False,
            preserved_validation=validation,
            externalized_lines=[],
            history_ref=None,
            verdict="blocked",
            errors=[f"control-state file does not exist: {control_state.as_posix()}"],
            recommendations=[
                "Run this helper from a repo with an initialized .servo runtime."
            ],
        )
        emit_report(payload, as_json=args.json)
        return 2

    original_text = control_state.read_text(encoding="utf-8")
    pre_validation = validate_control_state(original_text)
    if not pre_validation.ok:
        payload = report_payload(
            mode=mode,
            control_state=control_state,
            would_change=False,
            changed=False,
            preserved_validation=pre_validation,
            externalized_lines=[],
            history_ref=None,
            verdict="blocked",
            errors=pre_validation.errors(),
            recommendations=[
                "Repair the control-state structure before attempting compaction.",
                "Do not hydrate missing values from installer-generated backup artifacts.",
            ],
        )
        emit_report(payload, as_json=args.json)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    created_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact_name = "control-state-history-" + now.strftime("%Y%m%dT%H%M%SZ") + ".md"
    history_path = history_dir / artifact_name
    history_ref = repo_relative_ref(history_path)
    plan = build_compaction_plan(original_text, history_ref)
    post_validation = validate_control_state(plan.compacted_text)

    if not post_validation.ok:
        payload = report_payload(
            mode=mode,
            control_state=control_state,
            would_change=plan.would_change,
            changed=False,
            preserved_validation=post_validation,
            externalized_lines=plan.externalized_lines,
            history_ref=plan.history_ref,
            verdict="blocked",
            errors=post_validation.errors(),
            recommendations=[
                "Compaction would remove hydration-critical context; keep the original file."
            ],
        )
        emit_report(payload, as_json=args.json)
        return 2

    changed = False
    if apply_changes and plan.would_change:
        source_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
        history_dir.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            history_artifact_text(
                source_path=control_state,
                source_hash=source_hash,
                created_at=created_at,
                externalized_lines=plan.externalized_lines,
            ),
            encoding="utf-8",
        )
        control_state.write_text(plan.compacted_text, encoding="utf-8")
        reread_validation = validate_control_state(
            control_state.read_text(encoding="utf-8")
        )
        if not reread_validation.ok:
            control_state.write_text(original_text, encoding="utf-8")
            history_path.unlink(missing_ok=True)
            payload = report_payload(
                mode=mode,
                control_state=control_state,
                would_change=plan.would_change,
                changed=False,
                preserved_validation=reread_validation,
                externalized_lines=plan.externalized_lines,
                history_ref=plan.history_ref,
                verdict="blocked",
                errors=[
                    *reread_validation.errors(),
                    "post-write verification failed; original control-state restored",
                ],
                recommendations=[
                    "Inspect the generated history artifact before retrying."
                ],
            )
            emit_report(payload, as_json=args.json)
            return 2
        changed = True

    recommendations: list[str] = []
    if not plan.would_change:
        recommendations.append(
            "No duplicate compactable control-state lines were found."
        )
    elif not apply_changes:
        recommendations.append(
            "Review dry-run output, then rerun with --apply if approved."
        )
    else:
        recommendations.append("Review the generated compaction history artifact.")

    payload = report_payload(
        mode=mode,
        control_state=control_state,
        would_change=plan.would_change,
        changed=changed,
        preserved_validation=post_validation,
        externalized_lines=plan.externalized_lines,
        history_ref=plan.history_ref,
        verdict="pass",
        errors=[],
        recommendations=recommendations,
    )
    emit_report(payload, as_json=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
