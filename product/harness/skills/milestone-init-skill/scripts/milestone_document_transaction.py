#!/usr/bin/env python3
"""Check and persist one complete, approved Milestone document.

The LLM owns admission and document authoring.  This worker only parses explicit
machine-control fields, validates deterministic Milestone invariants, and
persists the exact approved bytes under the supported single-Harness-writer
contract.  It never repairs, normalizes, reorders, or serializes the document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, NoReturn


MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ALLOWED_DISPOSITIONS = {"open", "finished", "superseded"}
ALLOWED_CONDITIONS = {"required", "conditional", "deferred", "superseded"}
REQUIRED_FRONTMATTER = {
    "title",
    "artifact_type",
    "milestone_id",
    "revision",
    "maturity",
    "disposition",
    "updated",
    "owner",
    "milestone_kind",
    "milestone_branch",
    "baseline_ref",
    "close_target",
}
PROHIBITED_FRONTMATTER = {
    "active",
    "active_milestone",
    "active_milestone_ref",
    "current",
    "current_branch",
    "current_carrier",
    "current_phase",
    "progress_counter",
    "pipeline_position",
}
CORE_SECTION_ALIASES = {
    "Goal": ("Goal",),
    "Scope": ("Scope",),
    "Non-Goals": ("Non-Goals",),
    "Cross-Worktrack Design Decisions": (
        "Cross-Worktrack Design Decisions",
        "Cross-Layer Design Decisions",
    ),
    "Worktrack Tasklist": ("Worktrack Tasklist",),
    "Milestone-Level Acceptance Criteria": ("Milestone-Level Acceptance Criteria",),
    "Amendments": ("Amendments",),
    "Finalization References": ("Finalization References",),
}
ENTRY_REQUIRED_FIELDS = {
    "worktrack_id",
    "outcome",
    "condition",
    "covers",
    "result_ref",
}
ENTRY_ALLOWED_FIELDS = ENTRY_REQUIRED_FIELDS | {
    "depends_on",
    "execution_condition",
    "boundary_hint",
}
AMENDMENT_REQUIRED_FIELDS = {
    "changed",
    "reason",
    "affected_worktracks",
    "evidence_still_valid",
    "evidence_requires_revalidation",
    "approval_ref",
}
AMENDMENT_ALLOWED_FIELDS = AMENDMENT_REQUIRED_FIELDS | {"revision"}
NULL_VALUES = {"", "null", "none", "n/a", "na", "-"}


class TransactionError(Exception):
    """A deterministic public failure with located details."""

    def __init__(self, code: str, message: str | None = None, **details: Any) -> None:
        message = message or code.replace("_", " ")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def fail(code: str, message: str | None = None, **details: Any) -> NoReturn:
    raise TransactionError(code, message, **details)


CONFLICT_ERROR_CODES = {
    "amend_mode_required",
    "amendment_history_change",
    "baseline_branch_conflict",
    "branch_contract_conflict",
    "branch_ref_conflict",
    "branch_ref_race",
    "canonical_identity_conflict",
    "expected_state_mismatch",
    "missing_current_document",
    "missing_milestone_branch",
    "same_revision_conflict",
    "skipped_revision",
    "stale_compare_and_swap",
    "stale_revision",
}

BLOCKED_ERROR_CODES = {
    "checkout_changed",
    "final_acceptance_authority_violation",
    "git_error",
    "injected_failure",
    "invalid_repo_root",
    "lifecycle_authority_violation",
    "milestone_id_change",
    "missing_approval_ref",
    "missing_baseline_commit",
    "missing_close_target",
    "missing_milestone_directory",
    "readback_mismatch",
    "result_authority_violation",
    "test_failure_not_enabled",
    "transaction_failure",
    "unsafe_current_branch",
    "unsafe_file_read",
    "unsafe_file_type",
    "unsafe_milestone_directory",
    "unsafe_stable_ref",
}


def signal_for_error(code: str) -> str:
    if code in CONFLICT_ERROR_CODES:
        return "conflict"
    if code in BLOCKED_ERROR_CODES:
        return "blocked"
    return "invalid"


@dataclass(frozen=True)
class WorktrackEntry:
    worktrack_id: str
    checked: bool
    fields: dict[str, str]
    depends_on: tuple[str, ...]
    covers: tuple[str, ...]
    result_ref: str | None


@dataclass(frozen=True)
class Document:
    raw: bytes
    text: str
    digest: str
    fields: dict[str, str]
    milestone_id: str
    revision: int
    sections: dict[str, str]
    criteria: tuple[str, ...]
    entries: dict[str, WorktrackEntry]
    amendments: dict[int, dict[str, str]]
    amendment_blocks: dict[int, str]
    amendment: dict[str, str] | None
    final_refs: dict[str, str | None]


def sha256_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def json_out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            fail("invalid_frontmatter_value", value=value)
        if not isinstance(decoded, str):
            fail("invalid_frontmatter_value", value=value)
        return decoded
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def clean_markdown_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "`":
        value = value[1:-1].strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value.strip()


def nullable(value: str) -> str | None:
    cleaned = clean_markdown_value(value)
    return None if cleaned.lower() in NULL_VALUES else cleaned


def parse_inline_list(
    value: str, field: str, context_id: str
) -> tuple[str, ...]:
    cleaned = value.strip()
    # A whole list may be one code span (`[A, B]` or `A, B`), while the
    # preferred human-readable form uses one code span per item (`A`, `B`).
    # Strip an enclosing span only when it is the sole span.
    if (
        len(cleaned) >= 2
        and cleaned[0] == cleaned[-1] == "`"
        and cleaned.count("`") == 2
    ):
        cleaned = cleaned[1:-1].strip()
    if cleaned.lower() in NULL_VALUES or cleaned == "[]":
        return ()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    if not cleaned:
        return ()
    items: list[str] = []
    for item in cleaned.split(","):
        normalized = clean_markdown_value(item)
        if not normalized:
            fail(
                "invalid_structured_list",
                field=field,
                context=context_id,
            )
        items.append(normalized)
    if len(items) != len(set(items)):
        fail(
            "duplicate_structured_list_item",
            field=field,
            context=context_id,
            values=items,
        )
    return tuple(items)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    opening = re.match(r"\A---[ \t]*\r?\n", text)
    if opening is None:
        fail("missing_frontmatter")
    closing_match = re.search(
        r"^---[ \t]*\r?$",
        text[opening.end() :],
        flags=re.MULTILINE,
    )
    if closing_match is None:
        fail("missing_frontmatter")
    closing_start = opening.end() + closing_match.start()
    closing_end = opening.end() + closing_match.end()
    if closing_end >= len(text) or text[closing_end] != "\n":
        fail("missing_frontmatter")
    block = text[opening.end() : closing_start]
    body = text[closing_end + 1 :]
    fields: dict[str, str] = {}
    for line_number, line in enumerate(block.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z0-9_]*)\s*:\s*(.*?)\s*", line)
        if match is None:
            fail("invalid_frontmatter", line=line_number, content=line)
        key, value = match.groups()
        if key in fields:
            fail("duplicate_frontmatter_field", field=key)
        fields[key] = clean_scalar(value)
    missing = sorted(REQUIRED_FRONTMATTER - fields.keys())
    if missing:
        fail("missing_frontmatter_fields", missing=missing)
    prohibited = sorted(PROHIBITED_FRONTMATTER & fields.keys())
    if prohibited:
        fail("runtime_state_in_document", prohibited=prohibited)
    unknown = sorted(fields.keys() - REQUIRED_FRONTMATTER)
    if unknown:
        fail("unknown_frontmatter_fields", unknown=unknown)
    return fields, body


def mask_fenced_markdown(text: str) -> str:
    """Hide fenced code from control parsing while preserving source offsets."""

    masked: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    opener = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})([^\r\n]*)$")

    def mask_line(line: str) -> str:
        return "".join(character if character in "\r\n" else " " for character in line)

    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence_character is None:
            match = opener.fullmatch(content)
            if match is None:
                masked.append(line)
                continue
            fence = match.group(1)
            info = match.group(2)
            if fence[0] == "`" and "`" in info:
                masked.append(line)
                continue
            fence_character = fence[0]
            fence_length = len(fence)
            masked.append(mask_line(line))
            continue

        masked.append(mask_line(line))
        if re.fullmatch(
            rf"[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
            content,
        ):
            fence_character = None
            fence_length = 0
    return "".join(masked)


def split_sections(body: str, title: str) -> dict[str, str]:
    control_body = mask_fenced_markdown(body)
    h1_matches = list(
        re.finditer(
            r"^[ \t]{0,3}#(?!#)[ \t]+([^\r\n]+?)[ \t]*\r?$",
            control_body,
            flags=re.MULTILINE,
        )
    )
    if len(h1_matches) != 1 or body[: h1_matches[0].start()].strip():
        fail("invalid_document_envelope", h1_count=len(h1_matches))
    h1 = h1_matches[0]
    if h1.group(1).strip() != title:
        fail(
            "invalid_document_envelope",
            expected_title=title,
            observed_h1=h1.group(1).strip(),
        )
    headings = list(
        re.finditer(
            r"^[ \t]{0,3}##(?!#)[ \t]+([^\r\n]+?)[ \t]*\r?$",
            control_body,
            flags=re.MULTILINE,
        )
    )
    if not headings or headings[0].start() < h1.end():
        fail("invalid_document_envelope")
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).strip()
        if name in sections:
            fail("duplicate_section", section=name)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[name] = body[heading.end() : end]

    resolved = dict(sections)
    missing: list[str] = []
    for canonical_name, aliases in CORE_SECTION_ALIASES.items():
        present = [name for name in aliases if name in sections]
        if len(present) > 1:
            fail(
                "duplicate_section",
                section=canonical_name,
                observed=present,
            )
        if not present:
            missing.append(canonical_name)
        else:
            resolved[canonical_name] = sections[present[0]]
    if missing:
        fail("missing_sections", missing=missing)
    required_content = (
        "Goal",
        "Scope",
        "Non-Goals",
        "Cross-Worktrack Design Decisions",
        "Worktrack Tasklist",
        "Milestone-Level Acceptance Criteria",
    )
    empty = [name for name in required_content if not resolved[name].strip()]
    if empty:
        fail("missing_sections", missing=empty)
    return resolved


def parse_known_bullets(
    block: str,
    known_fields: set[str],
    context: str,
) -> dict[str, str]:
    """Extract declared control bullets while leaving all other prose opaque."""

    result: dict[str, str] = {}
    pattern = re.compile(
        r"^[ \t]*-[ \t]+([a-z][a-z0-9_]*)[ \t]*:[ \t]*(.*?)[ \t]*$"
    )
    for line_number, line in enumerate(
        mask_fenced_markdown(block).splitlines(),
        start=1,
    ):
        match = pattern.fullmatch(line)
        if match is None:
            continue
        key, value = match.groups()
        if key not in known_fields:
            continue
        if key in result:
            fail(
                "duplicate_field",
                context=context,
                field=key,
                line=line_number,
            )
        result[key] = value
    return result


def parse_criteria(section: str) -> tuple[str, ...]:
    control_section = mask_fenced_markdown(section)
    headings = list(
        re.finditer(
            r"^[ \t]{0,3}###[ \t]+([^\s]+)(?:\s|$)",
            control_section,
            flags=re.MULTILINE,
        )
    )
    criteria: list[str] = []
    for index, heading in enumerate(headings):
        criterion_id = clean_markdown_value(heading.group(1))
        if not SAFE_ID_RE.fullmatch(criterion_id):
            fail("invalid_acceptance_id", criterion_id=criterion_id)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        if not section[heading.end() : end].strip():
            fail("invalid_acceptance_content", criterion_id=criterion_id)
        criteria.append(criterion_id)
    if not criteria:
        fail("missing_acceptance_criteria")
    if len(criteria) != len(set(criteria)):
        fail("duplicate_acceptance_criteria")
    return tuple(criteria)


def validate_result_ref_shape(result_ref: str, worktrack_id: str) -> None:
    match = re.fullmatch(
        r"\.servo/worktrack/([^/#]+)/finished-handback\.ya?ml"
        r"(?:#[A-Za-z0-9][A-Za-z0-9._:/-]*)?",
        result_ref,
    )
    if match is None or match.group(1) != worktrack_id:
        fail(
            "unstable_result_ref",
            worktrack_id=worktrack_id,
            result_ref=result_ref,
        )


def parse_worktrack_entries(
    section: str,
    criteria: Iterable[str],
) -> dict[str, WorktrackEntry]:
    control_section = mask_fenced_markdown(section)
    headings = list(
        re.finditer(
            r"^[ \t]{0,3}###[ \t]+\[([ xX])\][ \t]+([^\r\n]+?)[ \t]*\r?$",
            control_section,
            flags=re.MULTILINE,
        )
    )
    if not headings:
        fail("missing_worktrack_entries")
    criterion_set = set(criteria)
    entries: dict[str, WorktrackEntry] = {}
    for index, heading in enumerate(headings):
        checked = heading.group(1).lower() == "x"
        heading_id = clean_markdown_value(heading.group(2))
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        block = section[heading.end() : end]
        fields = parse_known_bullets(
            block,
            ENTRY_ALLOWED_FIELDS,
            f"Worktrack {heading_id}",
        )
        missing = sorted(ENTRY_REQUIRED_FIELDS - fields.keys())
        dependency_fields = {"depends_on", "execution_condition"} & fields.keys()
        if not dependency_fields:
            missing.append("depends_on_or_execution_condition")
        if missing or len(dependency_fields) != 1:
            fail(
                "invalid_worktrack_entry_fields",
                worktrack_id=heading_id,
                missing=missing,
                dependency_fields=sorted(dependency_fields),
            )
        worktrack_id = clean_markdown_value(fields["worktrack_id"])
        if not SAFE_ID_RE.fullmatch(worktrack_id) or worktrack_id != heading_id:
            fail(
                "invalid_worktrack_id",
                heading_id=heading_id,
                worktrack_id=worktrack_id,
            )
        if worktrack_id in entries:
            fail("duplicate_worktrack", worktrack_id=worktrack_id)
        outcome = clean_markdown_value(fields["outcome"])
        if not outcome or "\n" in outcome:
            fail("invalid_worktrack_entry", worktrack_id=worktrack_id)
        condition = clean_markdown_value(fields["condition"])
        if condition not in ALLOWED_CONDITIONS:
            fail(
                "invalid_worktrack_condition",
                worktrack_id=worktrack_id,
                condition=condition,
            )
        expected_dependency_field = (
            "depends_on"
            if condition == "required"
            else "execution_condition"
            if condition == "conditional"
            else None
        )
        if expected_dependency_field and dependency_fields != {
            expected_dependency_field
        }:
            fail(
                "invalid_worktrack_dependency_form",
                worktrack_id=worktrack_id,
                condition=condition,
                expected=expected_dependency_field,
                observed=sorted(dependency_fields),
            )
        depends_on = parse_inline_list(
            fields.get("depends_on", "[]"),
            "depends_on",
            worktrack_id,
        )
        if (
            "execution_condition" in fields
            and nullable(fields["execution_condition"]) is None
        ):
            fail("invalid_worktrack_entry", worktrack_id=worktrack_id)
        covers = parse_inline_list(fields["covers"], "covers", worktrack_id)
        if not covers:
            fail("invalid_worktrack_coverage", worktrack_id=worktrack_id)
        unknown_coverage = sorted(set(covers) - criterion_set)
        if unknown_coverage:
            fail(
                "invalid_worktrack_coverage",
                worktrack_id=worktrack_id,
                unknown=unknown_coverage,
            )
        result_ref = nullable(fields["result_ref"])
        if result_ref is not None:
            validate_result_ref_shape(result_ref, worktrack_id)
        if checked != (result_ref is not None):
            fail(
                "checkbox_result_mismatch",
                worktrack_id=worktrack_id,
                checked=checked,
                result_ref=result_ref,
            )
        entries[worktrack_id] = WorktrackEntry(
            worktrack_id=worktrack_id,
            checked=checked,
            fields={
                key: clean_markdown_value(value)
                for key, value in fields.items()
            },
            depends_on=depends_on,
            covers=covers,
            result_ref=result_ref,
        )

    for entry in entries.values():
        unknown_dependencies = sorted(set(entry.depends_on) - entries.keys())
        if unknown_dependencies:
            fail(
                "unknown_worktrack_dependency",
                worktrack_id=entry.worktrack_id,
                unknown=unknown_dependencies,
            )
        if entry.worktrack_id in entry.depends_on:
            fail("cyclic_worktrack_dependency", worktrack_id=entry.worktrack_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(worktrack_id: str) -> None:
        if worktrack_id in visiting:
            fail("cyclic_worktrack_dependency", worktrack_id=worktrack_id)
        if worktrack_id in visited:
            return
        visiting.add(worktrack_id)
        for dependency in entries[worktrack_id].depends_on:
            visit(dependency)
        visiting.remove(worktrack_id)
        visited.add(worktrack_id)

    for worktrack_id in entries:
        visit(worktrack_id)
    return entries


def parse_amendments(
    section: str,
    revision: int,
    worktrack_ids: Iterable[str],
) -> tuple[dict[int, dict[str, str]], dict[int, str]]:
    control_section = mask_fenced_markdown(section)
    headings = list(
        re.finditer(
            r"^[ \t]{0,3}###[ \t]+Revision[ \t]+(\d+)[ \t]+Amendment[ \t]*\r?$",
            control_section,
            flags=re.MULTILINE,
        )
    )
    if revision == 1:
        if headings:
            fail("invalid_initial_amendment")
        structured = parse_known_bullets(
            section,
            AMENDMENT_ALLOWED_FIELDS,
            "revision 1 amendment prose",
        )
        if structured:
            fail("invalid_initial_amendment", observed=sorted(structured))
        return {}, {}
    observed = [int(heading.group(1)) for heading in headings]
    expected = list(range(2, revision + 1))
    if observed != expected:
        fail(
            "invalid_amendment_history",
            revision=revision,
            expected=expected,
            observed=observed,
        )
    worktrack_set = set(worktrack_ids)
    amendments: dict[int, dict[str, str]] = {}
    blocks: dict[int, str] = {}
    for index, heading in enumerate(headings):
        amendment_revision = observed[index]
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        fields = parse_known_bullets(
            section[heading.end() : end],
            AMENDMENT_ALLOWED_FIELDS,
            f"Revision {amendment_revision} Amendment",
        )
        missing = sorted(AMENDMENT_REQUIRED_FIELDS - fields.keys())
        if missing:
            fail(
                "incomplete_amendment",
                revision=amendment_revision,
                missing=missing,
            )
        for key in AMENDMENT_REQUIRED_FIELDS:
            if nullable(fields[key]) is None:
                fail(
                    "incomplete_amendment",
                    revision=amendment_revision,
                    field=key,
                )
        if "revision" in fields and clean_markdown_value(
            fields["revision"]
        ) != str(amendment_revision):
            fail(
                "invalid_amendment_history",
                heading_revision=amendment_revision,
                field_revision=clean_markdown_value(fields["revision"]),
            )
        affected = parse_inline_list(
            fields["affected_worktracks"],
            "affected_worktracks",
            f"revision-{amendment_revision}",
        )
        invalid_affected = sorted(
            value
            for value in affected
            if not SAFE_ID_RE.fullmatch(value) or value not in worktrack_set
        )
        if not affected or invalid_affected:
            fail(
                "invalid_amendment_worktracks",
                revision=amendment_revision,
                invalid=invalid_affected,
            )
        amendments[amendment_revision] = {
            key: clean_markdown_value(value)
            for key, value in fields.items()
        }
        # Boundary whitespace and commentary are approved history bytes.
        blocks[amendment_revision] = section[heading.start() : end]
    return amendments, blocks


def parse_final_refs(
    section: str,
    milestone_id: str,
) -> dict[str, str | None]:
    expected = {"milestone_gate_ref", "final_acceptance_ref"}
    fields = parse_known_bullets(section, expected, "Finalization References")
    missing = sorted(expected - fields.keys())
    if missing:
        fail("missing_final_refs", missing=missing)
    result = {key: nullable(value) for key, value in fields.items()}
    for key, value in result.items():
        if value is None:
            continue
        if re.fullmatch(
            r"\.servo/milestone/[A-Za-z0-9][A-Za-z0-9._-]*\.md"
            r"(?:#[A-Za-z0-9][A-Za-z0-9._:/-]*)?",
            value,
        ) is None:
            fail(
                "unstable_final_ref",
                milestone_id=milestone_id,
                field=key,
                value=value,
            )
    return result


def parse_baseline_ref(value: str) -> tuple[str, str]:
    if "@" not in value:
        fail("invalid_baseline_ref")
    branch, checkpoint = value.rsplit("@", 1)
    if (
        not branch
        or branch.startswith("-")
        or ".." in branch
        or branch.endswith("/")
        or not FULL_SHA_RE.fullmatch(checkpoint)
    ):
        fail("invalid_baseline_ref")
    return branch, checkpoint


def parse_document(raw: bytes, mode: str) -> Document:
    if len(raw) > MAX_DOCUMENT_BYTES:
        fail("document_too_large", max_bytes=MAX_DOCUMENT_BYTES)
    if b"\x00" in raw:
        fail("invalid_encoding", "document contains NUL bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("invalid_encoding")
    if re.search(r"\r(?!\n)", text):
        fail("invalid_newlines")
    fields, body = parse_frontmatter(text)
    if fields["artifact_type"] != "milestone":
        fail("invalid_artifact_type")
    empty = [
        key
        for key in (
            "title",
            "updated",
            "owner",
            "milestone_kind",
            "milestone_branch",
            "baseline_ref",
            "close_target",
        )
        if not fields[key]
    ]
    if empty:
        fail("empty_frontmatter_fields", fields=empty)
    try:
        updated = datetime.fromisoformat(fields["updated"].replace("Z", "+00:00"))
    except ValueError:
        fail("invalid_updated_timestamp")
    if updated.tzinfo is None:
        fail("invalid_updated_timestamp")
    milestone_id = fields["milestone_id"]
    if not SAFE_ID_RE.fullmatch(milestone_id):
        fail("invalid_milestone_id", milestone_id=milestone_id)
    try:
        revision = int(fields["revision"])
    except ValueError:
        fail("invalid_revision")
    if revision < 1:
        fail("invalid_revision")
    if fields["maturity"] != "planned":
        fail("non_planned_document")
    if fields["disposition"] not in ALLOWED_DISPOSITIONS:
        fail("invalid_disposition", disposition=fields["disposition"])
    if mode == "create" and (revision != 1 or fields["disposition"] != "open"):
        fail(
            "invalid_create_state",
            revision=revision,
            disposition=fields["disposition"],
        )
    if mode == "amend" and revision <= 1:
        fail("invalid_amendment_revision")
    for key in ("milestone_branch", "close_target"):
        branch = fields[key]
        if branch.startswith("-") or ".." in branch or branch.endswith("/"):
            fail("invalid_branch_name", field=key, branch=branch)
    source_branch, _ = parse_baseline_ref(fields["baseline_ref"])
    if fields["milestone_branch"] in {source_branch, fields["close_target"]}:
        fail(
            "invalid_branch_contract",
            milestone_branch=fields["milestone_branch"],
            source_branch=source_branch,
            close_target=fields["close_target"],
        )
    sections = split_sections(body, fields["title"])
    criteria = parse_criteria(sections["Milestone-Level Acceptance Criteria"])
    entries = parse_worktrack_entries(sections["Worktrack Tasklist"], criteria)
    amendments, amendment_blocks = parse_amendments(
        sections["Amendments"],
        revision,
        entries.keys(),
    )
    final_refs = parse_final_refs(
        sections["Finalization References"],
        milestone_id,
    )
    return Document(
        raw=raw,
        text=text,
        digest=sha256_digest(raw),
        fields=fields,
        milestone_id=milestone_id,
        revision=revision,
        sections=sections,
        criteria=criteria,
        entries=entries,
        amendments=amendments,
        amendment_blocks=amendment_blocks,
        amendment=amendments.get(revision),
        final_refs=final_refs,
    )


def run_git(
    repo_root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if check and completed.returncode != 0:
        fail(
            "git_error",
            arguments=arguments,
            stderr=completed.stderr.strip(),
        )
    return completed


def ensure_safe_repo_root(value: str) -> Path:
    try:
        repo_root = Path(value).resolve(strict=True)
    except OSError:
        fail("invalid_repo_root", "repo root does not exist")
    if not repo_root.is_dir() or not (repo_root / ".git").exists():
        fail("invalid_repo_root")
    return repo_root


def ensure_safe_milestone_dir(repo_root: Path) -> Path:
    servo_dir = repo_root / ".servo"
    milestone_dir = servo_dir / "milestone"
    for path in (servo_dir, milestone_dir):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            fail("missing_milestone_directory", path=str(path))
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            fail("unsafe_milestone_directory", path=str(path))
    if milestone_dir.resolve(strict=True).parent != servo_dir.resolve(strict=True):
        fail("unsafe_milestone_directory")
    return milestone_dir


def safe_read_regular(path: Path, *, missing_ok: bool) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        fail("missing_file", "required file is missing", path=str(path))
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        fail("unsafe_file_type", path=str(path))
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        fail("unsafe_file_read", path=str(path))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            fail("unsafe_file_read", path=str(path))
        if not stat.S_ISREG(opened.st_mode):
            fail("unsafe_file_type", path=str(path))
        if opened.st_size > MAX_DOCUMENT_BYTES:
            fail("document_too_large", path=str(path))
        chunks: list[bytes] = []
        remaining = MAX_DOCUMENT_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_DOCUMENT_BYTES:
            fail("document_too_large", path=str(path))
        return data
    finally:
        os.close(descriptor)


def read_candidate(path_value: str) -> bytes:
    return safe_read_regular(Path(path_value), missing_ok=False) or b""


def current_branch(repo_root: Path) -> str | None:
    completed = run_git(
        repo_root,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def read_branch_ref(repo_root: Path, branch: str) -> str | None:
    completed = run_git(
        repo_root,
        ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"],
        check=False,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value if FULL_SHA_RE.fullmatch(value) else None


def branch_descends_from(
    repo_root: Path,
    branch_commit: str,
    baseline: str,
) -> bool:
    completed = run_git(
        repo_root,
        ["merge-base", "--is-ancestor", baseline, branch_commit],
        check=False,
    )
    return completed.returncode == 0


def validate_stable_ref_target(repo_root: Path, value: str) -> None:
    relative = value.split("#", 1)[0]
    target = repo_root.joinpath(*relative.split("/"))
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        fail("missing_stable_ref", ref=value)
    if not resolved.is_relative_to(repo_root):
        fail("unsafe_stable_ref", ref=value)
    safe_read_regular(target, missing_ok=False)


def validate_stable_refs(repo_root: Path, document: Document) -> None:
    for entry in document.entries.values():
        if entry.result_ref is not None:
            validate_stable_ref_target(repo_root, entry.result_ref)
    for value in document.final_refs.values():
        if value is not None:
            validate_stable_ref_target(repo_root, value)


def validate_git_contract(
    repo_root: Path,
    document: Document,
) -> tuple[str, str]:
    validate_stable_refs(repo_root, document)
    source_branch, baseline = parse_baseline_ref(document.fields["baseline_ref"])
    for branch in (
        source_branch,
        document.fields["milestone_branch"],
        document.fields["close_target"],
    ):
        checked = run_git(
            repo_root,
            ["check-ref-format", "--branch", branch],
            check=False,
        )
        if checked.returncode != 0:
            fail("invalid_branch_name", branch=branch)
    if source_branch == document.fields["milestone_branch"]:
        fail("invalid_branch_contract")
    resolved = run_git(
        repo_root,
        ["rev-parse", "--verify", f"{baseline}^{{commit}}"],
        check=False,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != baseline:
        fail("missing_baseline_commit", baseline=baseline)
    source_head = read_branch_ref(repo_root, source_branch)
    if source_head is None or not branch_descends_from(
        repo_root,
        source_head,
        baseline,
    ):
        fail(
            "baseline_branch_conflict",
            source_branch=source_branch,
            baseline=baseline,
            source_head=source_head,
        )
    close_target = document.fields["close_target"]
    if read_branch_ref(repo_root, close_target) is None:
        fail("missing_close_target", close_target=close_target)
    return source_branch, baseline


def resolve_branch_contract(
    repo_root: Path,
    candidate: Document,
    current: Document | None,
    *,
    mutate: bool,
    identical_replay: bool = False,
) -> tuple[str, bool, str]:
    _, baseline = validate_git_contract(repo_root, candidate)
    branch = candidate.fields["milestone_branch"]
    existing = read_branch_ref(repo_root, branch)
    contract_changed = current is not None and any(
        current.fields[key] != candidate.fields[key]
        for key in ("milestone_branch", "baseline_ref", "close_target")
    )
    if existing is not None:
        if current is None or contract_changed:
            if existing != baseline:
                fail(
                    "branch_ref_conflict",
                    branch=branch,
                    expected=baseline,
                    actual=existing,
                )
            return "existing_at_baseline", False, baseline
        if not branch_descends_from(repo_root, existing, baseline):
            fail(
                "branch_contract_conflict",
                branch=branch,
                existing=existing,
                baseline=baseline,
            )
        return (
            "already_applied" if identical_replay else "existing_descendant",
            False,
            baseline,
        )
    if current is not None and not contract_changed:
        fail("missing_milestone_branch", branch=branch)
    if not mutate:
        return "would_create", False, baseline
    if current_branch(repo_root) == branch:
        fail("unsafe_current_branch", branch=branch)
    created = run_git(
        repo_root,
        ["update-ref", f"refs/heads/{branch}", baseline, "0" * 40],
        check=False,
    )
    if created.returncode != 0:
        fail(
            "branch_ref_race",
            branch=branch,
            stderr=created.stderr.strip(),
        )
    return "created", True, baseline


def write_temp(milestone_dir: Path, milestone_id: str, raw: bytes) -> Path:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{milestone_id}.",
        suffix=".tmp",
        dir=milestone_dir,
    )
    path = Path(temp_name)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while persisting Milestone document")
            view = view[written:]
        os.fsync(descriptor)
    except Exception:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    os.close(descriptor)
    return path


def fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def inject_failure(point: str | None, expected: str) -> None:
    if point == expected:
        fail(
            "injected_failure",
            "test-only failure injection",
            failure_point=expected,
        )


def enforce_init_authority(
    candidate: Document,
    current: Document | None,
    approval_ref: str | None,
) -> None:
    if candidate.revision > 1:
        if candidate.amendment is None:
            fail("incomplete_amendment", revision=candidate.revision)
        if (
            approval_ref is not None
            and candidate.amendment["approval_ref"] != approval_ref
        ):
            fail(
                "approval_ref_mismatch",
                document_approval_ref=candidate.amendment["approval_ref"],
                supplied_approval_ref=approval_ref,
            )
    candidate_results = {
        worktrack_id: entry.result_ref
        for worktrack_id, entry in candidate.entries.items()
    }
    if current is None:
        newly_accepted = sorted(
            worktrack_id
            for worktrack_id, result_ref in candidate_results.items()
            if result_ref is not None
        )
        non_null_final = sorted(
            key
            for key, value in candidate.final_refs.items()
            if value is not None
        )
        if newly_accepted:
            fail(
                "result_authority_violation",
                worktracks=newly_accepted,
            )
        if non_null_final:
            fail(
                "final_acceptance_authority_violation",
                final_refs=non_null_final,
            )
        return
    if candidate.milestone_id != current.milestone_id:
        fail("milestone_id_change")
    if current.fields["disposition"] != "open":
        fail(
            "lifecycle_authority_violation",
            disposition=current.fields["disposition"],
        )
    if candidate.fields["disposition"] != current.fields["disposition"]:
        fail(
            "lifecycle_authority_violation",
            current=current.fields["disposition"],
            candidate=candidate.fields["disposition"],
        )
    for revision, approved_block in current.amendment_blocks.items():
        if candidate.amendment_blocks.get(revision) != approved_block:
            fail("amendment_history_change", revision=revision)
    for worktrack_id, result_ref in candidate_results.items():
        previous = current.entries.get(worktrack_id)
        previous_ref = previous.result_ref if previous is not None else None
        if result_ref != previous_ref:
            fail(
                "result_authority_violation",
                worktrack_id=worktrack_id,
                previous=previous_ref,
                candidate=result_ref,
            )
    for worktrack_id, entry in current.entries.items():
        if entry.result_ref is not None and worktrack_id not in candidate.entries:
            fail(
                "result_authority_violation",
                worktrack_id=worktrack_id,
            )
        if (
            entry.result_ref is not None
            and worktrack_id in candidate.entries
            and candidate.entries[worktrack_id].fields != entry.fields
        ):
            fail(
                "result_authority_violation",
                worktrack_id=worktrack_id,
                reason="accepted Worktrack control fields cannot be reinterpreted",
            )
    if candidate.final_refs != current.final_refs:
        fail("final_acceptance_authority_violation")


def classify_candidate(
    candidate: Document,
    current_raw: bytes | None,
    mode: str,
) -> tuple[str, Document | None]:
    if current_raw is None:
        if mode == "amend":
            fail("missing_current_document")
        return "create", None
    current = parse_document(current_raw, "existing")
    if candidate.milestone_id != current.milestone_id:
        fail(
            "canonical_identity_conflict",
            current=current.milestone_id,
            candidate=candidate.milestone_id,
        )
    if candidate.revision == current.revision and candidate.raw == current.raw:
        return "already_applied", current
    if candidate.revision == current.revision:
        fail(
            "same_revision_conflict",
            revision=candidate.revision,
            current_digest=current.digest,
            candidate_digest=candidate.digest,
        )
    if candidate.revision < current.revision:
        fail(
            "stale_revision",
            current_revision=current.revision,
            candidate_revision=candidate.revision,
        )
    if candidate.revision > current.revision + 1:
        fail(
            "skipped_revision",
            current_revision=current.revision,
            candidate_revision=candidate.revision,
        )
    if mode != "amend":
        fail(
            "amend_mode_required",
            current_revision=current.revision,
            candidate_revision=candidate.revision,
        )
    return "amend", current


def validate_expected_state(
    action: str,
    candidate: Document,
    current: Document | None,
    expected_revision: int,
    expected_digest: str,
) -> None:
    if action == "create":
        if expected_revision != 0 or expected_digest != "absent":
            fail("expected_state_mismatch")
        return
    if current is None:
        fail("expected_state_mismatch", "current document is missing")
    if action == "amend":
        if expected_revision != current.revision or expected_digest != current.digest:
            fail(
                "stale_compare_and_swap",
                expected_revision=expected_revision,
                actual_revision=current.revision,
                expected_digest=expected_digest,
                actual_digest=current.digest,
            )
        return
    # Safe repeat accepts a verifiable now-current state. Revision-1 create may
    # also replay its only legal prior state (absence). A prior amend digest is
    # not retained by this stateless exact-byte worker, so accepting one by shape
    # alone would bypass expected-state validation; callers must reread current
    # state before an amend roll-forward retry.
    current_state = (
        expected_revision == current.revision
        and expected_digest == current.digest
    )
    create_prior = (
        current.revision == 1
        and expected_revision == 0
        and expected_digest == "absent"
    )
    if not (current_state or create_prior):
        fail(
            "stale_compare_and_swap",
            expected_revision=expected_revision,
            actual_revision=current.revision,
            expected_digest=expected_digest,
            actual_digest=current.digest,
            candidate_digest=candidate.digest,
        )


def control_summary(document: Document) -> dict[str, Any]:
    return {
        "milestone_id": document.milestone_id,
        "revision": document.revision,
        "maturity": document.fields["maturity"],
        "disposition": document.fields["disposition"],
        "worktrack_ids": list(document.entries),
        "acceptance_ids": list(document.criteria),
        "amendment_revisions": sorted(document.amendments),
        "milestone_branch": document.fields["milestone_branch"],
        "baseline_ref": document.fields["baseline_ref"],
        "close_target": document.fields["close_target"],
    }


def validate_command(args: argparse.Namespace) -> int:
    repo_root = ensure_safe_repo_root(args.repo_root)
    milestone_dir = ensure_safe_milestone_dir(repo_root)
    candidate = parse_document(read_candidate(args.candidate), args.mode)
    target = milestone_dir / f"{candidate.milestone_id}.md"
    current_raw = safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, current_raw, args.mode)
    enforce_init_authority(candidate, current, None)
    branch_outcome, _, _ = resolve_branch_contract(
        repo_root,
        candidate,
        current,
        mutate=False,
        identical_replay=action == "already_applied",
    )
    json_out(
        {
            "signal": "proposal_ready",
            "status": "valid",
            "mode": args.mode,
            "milestone_id": candidate.milestone_id,
            "revision": candidate.revision,
            "canonical_ref": str(target.relative_to(repo_root)),
            "preview_digest": candidate.digest,
            "current_revision": current.revision if current else 0,
            "current_digest": current.digest if current else "absent",
            "proposed_action": action,
            "branch_outcome": branch_outcome,
            "control_summary": control_summary(candidate),
            "writes": [],
        }
    )
    return 0


def durable_writes_after_failure(
    repo_root: Path,
    target: Path,
    candidate: Document,
    *,
    branch_created: bool,
    branch_baseline: str,
) -> list[str]:
    writes: list[str] = []
    if branch_created and read_branch_ref(
        repo_root,
        candidate.fields["milestone_branch"],
    ) == branch_baseline:
        writes.append(f"refs/heads/{candidate.fields['milestone_branch']}")
    try:
        observed = safe_read_regular(target, missing_ok=True)
    except TransactionError:
        observed = None
    if observed == candidate.raw:
        writes.append(str(target.relative_to(repo_root)))
    return writes


def apply_command(args: argparse.Namespace) -> int:
    repo_root = ensure_safe_repo_root(args.repo_root)
    milestone_dir = ensure_safe_milestone_dir(repo_root)
    candidate = parse_document(read_candidate(args.candidate), args.mode)
    if DIGEST_RE.fullmatch(args.approved_digest) is None:
        fail("invalid_approved_digest")
    if candidate.digest != args.approved_digest:
        fail(
            "approval_digest_mismatch",
            approved_digest=args.approved_digest,
            candidate_digest=candidate.digest,
        )
    approval_ref = args.approval_ref.strip()
    if not approval_ref or "\n" in approval_ref or len(approval_ref) > 512:
        fail("missing_approval_ref")
    if (
        args.expected_current_digest != "absent"
        and DIGEST_RE.fullmatch(args.expected_current_digest) is None
    ):
        fail("invalid_expected_digest")

    target = milestone_dir / f"{candidate.milestone_id}.md"
    previous_raw = safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, previous_raw, args.mode)
    validate_expected_state(
        action,
        candidate,
        current,
        args.expected_current_revision,
        args.expected_current_digest,
    )
    enforce_init_authority(candidate, current, approval_ref)
    validate_git_contract(repo_root, candidate)

    original_checkout = current_branch(repo_root)
    branch_created = False
    branch_baseline = ""
    branch_outcome = "not_attempted"
    temp_path: Path | None = None
    replaced = False
    try:
        branch_outcome, branch_created, branch_baseline = resolve_branch_contract(
            repo_root,
            candidate,
            current,
            mutate=action != "already_applied",
            identical_replay=action == "already_applied",
        )
        inject_failure(args.test_failure_point, "after-branch")

        if action != "already_applied":
            temp_path = write_temp(
                milestone_dir,
                candidate.milestone_id,
                candidate.raw,
            )
            inject_failure(args.test_failure_point, "before-replace")
            latest_raw = safe_read_regular(target, missing_ok=True)
            if latest_raw != previous_raw:
                fail("stale_compare_and_swap")
            os.replace(temp_path, target)
            temp_path = None
            replaced = True
            fsync_directory(milestone_dir)
            inject_failure(args.test_failure_point, "after-replace")

        readback = safe_read_regular(target, missing_ok=False)
        if readback != candidate.raw:
            fail(
                (
                    "stale_compare_and_swap"
                    if action == "already_applied"
                    else "readback_mismatch"
                ),
                "canonical readback does not match approved bytes",
            )
        if current_branch(repo_root) != original_checkout:
            fail("checkout_changed")
        # Recheck branch state after persistence; no branch is created here.
        resolve_branch_contract(
            repo_root,
            candidate,
            candidate if action == "already_applied" else current,
            mutate=False,
            identical_replay=action == "already_applied",
        )
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        writes = durable_writes_after_failure(
            repo_root,
            target,
            candidate,
            branch_created=branch_created,
            branch_baseline=branch_baseline,
        )
        if isinstance(exc, TransactionError):
            exc.details.update(
                {
                    "commit_point": (
                        "after_replace" if replaced else "before_replace"
                    ),
                    "roll_forward_required": replaced,
                    "writes": writes,
                }
            )
            raise
        fail(
            "transaction_failure",
            error=str(exc),
            commit_point="after_replace" if replaced else "before_replace",
            roll_forward_required=replaced,
            writes=writes,
        )

    outcome = (
        "created"
        if action == "create"
        else "revised"
        if action == "amend"
        else "already_applied"
    )
    writes: list[str] = []
    if branch_created:
        writes.append(f"refs/heads/{candidate.fields['milestone_branch']}")
    if action != "already_applied":
        writes.append(str(target.relative_to(repo_root)))
    json_out(
        {
            "signal": "milestone_ready",
            "status": outcome,
            "transaction_outcome": outcome,
            "mode": args.mode,
            "milestone_id": candidate.milestone_id,
            "revision": candidate.revision,
            "canonical_ref": str(target.relative_to(repo_root)),
            "canonical_digest": candidate.digest,
            "approval_ref": approval_ref,
            "branch_outcome": branch_outcome,
            "writes": writes,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check or persist one complete approved Milestone document"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser(
        "validate",
        help="check complete exact bytes without writes",
    )
    validate.add_argument("--mode", choices=("create", "amend"), required=True)
    validate.add_argument("--candidate", required=True)
    validate.add_argument("--repo-root", required=True)

    apply = subparsers.add_parser(
        "apply",
        help="persist complete exact approved bytes",
    )
    apply.add_argument("--mode", choices=("create", "amend"), required=True)
    apply.add_argument("--candidate", required=True)
    apply.add_argument("--repo-root", required=True)
    apply.add_argument("--approval-ref", required=True)
    apply.add_argument("--approved-digest", required=True)
    apply.add_argument("--expected-current-revision", type=int, required=True)
    apply.add_argument("--expected-current-digest", required=True)
    apply.add_argument(
        "--test-failure-point",
        choices=("after-branch", "before-replace", "after-replace"),
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if (
        getattr(args, "test_failure_point", None)
        and os.environ.get("SERVO_MILESTONE_INIT_ALLOW_TEST_FAILURE") != "1"
    ):
        fail("test_failure_not_enabled")
    return (
        validate_command(args)
        if args.command == "validate"
        else apply_command(args)
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TransactionError as exc:
        details = dict(exc.details)
        writes = details.pop("writes", [])
        json_out(
            {
                "signal": signal_for_error(exc.code),
                "status": exc.code,
                "reason": exc.message,
                "details": details,
                "writes": writes,
            }
        )
        raise SystemExit(2)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        json_out(
            {
                "signal": "blocked",
                "status": "internal_error",
                "reason": str(exc),
                "writes": [],
            }
        )
        raise SystemExit(3)
