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
REQUIRED_FRONTMATTER = set(
    """title artifact_type milestone_id revision maturity disposition updated
    owner milestone_kind milestone_branch baseline_ref close_target""".split()
)
PROHIBITED_FRONTMATTER = set(
    """active active_milestone active_milestone_ref current current_branch
    current_carrier current_phase progress_counter pipeline_position""".split()
)
CORE_SECTION_ALIASES = {
    "Goal": ("Goal",),
    "Scope": ("Scope",),
    "Non-Goals": ("Non-Goals",),
    "Cross-Worktrack Design Decisions": ("Cross-Worktrack Design Decisions", "Cross-Layer Design Decisions"),
    "Worktrack Tasklist": ("Worktrack Tasklist",),
    "Milestone-Level Acceptance Criteria": ("Milestone-Level Acceptance Criteria",),
    "Amendments": ("Amendments",),
    "Finalization References": ("Finalization References",),
}
ENTRY_REQUIRED_FIELDS = set("worktrack_id outcome condition covers result_ref".split())
ENTRY_ALLOWED_FIELDS = ENTRY_REQUIRED_FIELDS | set("depends_on execution_condition boundary_hint".split())
AMENDMENT_REQUIRED_FIELDS = set(
    """changed reason affected_worktracks evidence_still_valid
    evidence_requires_revalidation approval_ref""".split()
)
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


def require(predicate: object, code: str, message: str | None = None, **details: Any) -> None:
    """Fail with one public diagnostic unless a deterministic condition holds."""
    if not predicate:
        fail(code, message, **details)


CONFLICT_ERROR_CODES = set(
    """amend_mode_required amendment_history_change baseline_branch_conflict
    branch_contract_conflict branch_ref_conflict branch_ref_race canonical_identity_conflict
    expected_state_mismatch missing_current_document missing_milestone_branch
    same_revision_conflict skipped_revision stale_compare_and_swap stale_revision""".split()
)
BLOCKED_ERROR_CODES = set(
    """checkout_changed final_acceptance_authority_violation git_error injected_failure
    invalid_repo_root lifecycle_authority_violation milestone_id_change missing_approval_ref
    missing_baseline_commit missing_close_target missing_milestone_directory readback_mismatch
    result_authority_violation test_failure_not_enabled transaction_failure unsafe_current_branch
    unsafe_file_read unsafe_file_type unsafe_milestone_directory unsafe_stable_ref""".split()
)


def signal_for_error(code: str) -> str:
    return "conflict" if code in CONFLICT_ERROR_CODES else "blocked" if code in BLOCKED_ERROR_CODES else "invalid"


@dataclass(frozen=True)
class WorktrackEntry:
    worktrack_id: str
    fields: dict[str, str]
    depends_on: tuple[str, ...]
    covers: tuple[str, ...]
    result_ref: str | None


@dataclass(frozen=True)
class Document:
    raw: bytes
    digest: str
    fields: dict[str, str]
    milestone_id: str
    revision: int
    criteria: tuple[str, ...]
    entries: dict[str, WorktrackEntry]
    amendments: dict[int, dict[str, str]]
    amendment_blocks: dict[int, str]
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
        require(isinstance(decoded, str), "invalid_frontmatter_value", value=value)
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


def parse_inline_list(value: str, field: str, context_id: str) -> tuple[str, ...]:
    cleaned = value.strip()
    # A whole list may be one code span (`[A, B]` or `A, B`), while the
    # preferred human-readable form uses one code span per item (`A`, `B`).
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] == "`" and cleaned.count("`") == 2:
        cleaned = cleaned[1:-1].strip()
    if cleaned.lower() in NULL_VALUES or cleaned == "[]":
        return ()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    if not cleaned:
        return ()
    items = [clean_markdown_value(item) for item in cleaned.split(",")]
    require(
        all(items),
        "invalid_structured_list",
        field=field,
        context=context_id,
    )
    require(
        len(items) == len(set(items)),
        "duplicate_structured_list_item",
        field=field,
        context=context_id,
        values=items,
    )
    return tuple(items)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    opening = re.match(r"\A---[ \t]*\r?\n", text)
    require(opening is not None, "missing_frontmatter")
    assert opening is not None
    closing_match = re.search(
        r"^---[ \t]*\r?$",
        text[opening.end() :],
        flags=re.MULTILINE,
    )
    require(closing_match is not None, "missing_frontmatter")
    assert closing_match is not None
    closing_start = opening.end() + closing_match.start()
    closing_end = opening.end() + closing_match.end()
    require(closing_end < len(text) and text[closing_end] == "\n", "missing_frontmatter")
    block = text[opening.end() : closing_start]
    body = text[closing_end + 1 :]
    fields: dict[str, str] = {}
    for line_number, line in enumerate(block.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z0-9_]*)\s*:\s*(.*?)\s*", line)
        require(match is not None, "invalid_frontmatter", line=line_number, content=line)
        assert match is not None
        key, value = match.groups()
        require(key not in fields, "duplicate_frontmatter_field", field=key)
        fields[key] = clean_scalar(value)
    missing = sorted(REQUIRED_FRONTMATTER - fields.keys())
    require(not missing, "missing_frontmatter_fields", missing=missing)
    prohibited = sorted(PROHIBITED_FRONTMATTER & fields.keys())
    require(not prohibited, "runtime_state_in_document", prohibited=prohibited)
    unknown = sorted(fields.keys() - REQUIRED_FRONTMATTER)
    require(not unknown, "unknown_frontmatter_fields", unknown=unknown)
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
        if fence_character is not None:
            masked.append(mask_line(line))
            closing = rf"[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*"
            if re.fullmatch(closing, content):
                fence_character = None
                fence_length = 0
            continue
        match = opener.fullmatch(content)
        if match is None or (match.group(1)[0] == "`" and "`" in match.group(2)):
            masked.append(line)
            continue
        fence_character = match.group(1)[0]
        fence_length = len(match.group(1))
        masked.append(mask_line(line))
    return "".join(masked)


def split_sections(body: str, title: str) -> dict[str, str]:
    control_body = mask_fenced_markdown(body)
    h1_matches = list(
        re.finditer(r"^[ \t]{0,3}#(?!#)[ \t]+([^\r\n]+?)[ \t]*\r?$", control_body, re.MULTILINE)
    )
    require(
        len(h1_matches) == 1 and not body[: h1_matches[0].start()].strip(),
        "invalid_document_envelope",
        h1_count=len(h1_matches),
    )
    h1 = h1_matches[0]
    require(
        h1.group(1).strip() == title,
        "invalid_document_envelope",
        expected_title=title,
        observed_h1=h1.group(1).strip(),
    )
    headings = list(
        re.finditer(r"^[ \t]{0,3}##(?!#)[ \t]+([^\r\n]+?)[ \t]*\r?$", control_body, re.MULTILINE)
    )
    require(headings and headings[0].start() >= h1.end(), "invalid_document_envelope")
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).strip()
        require(name not in sections, "duplicate_section", section=name)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[name] = body[heading.end() : end]

    resolved = dict(sections)
    missing: list[str] = []
    for canonical_name, aliases in CORE_SECTION_ALIASES.items():
        present = [name for name in aliases if name in sections]
        require(
            len(present) <= 1,
            "duplicate_section",
            section=canonical_name,
            observed=present,
        )
        if not present:
            missing.append(canonical_name)
        else:
            resolved[canonical_name] = sections[present[0]]
    require(not missing, "missing_sections", missing=missing)
    required_content = (
        "Goal",
        "Scope",
        "Non-Goals",
        "Cross-Worktrack Design Decisions",
        "Worktrack Tasklist",
        "Milestone-Level Acceptance Criteria",
    )
    empty = [name for name in required_content if not resolved[name].strip()]
    require(not empty, "missing_sections", missing=empty)
    return resolved


def parse_known_bullets(block: str, known_fields: set[str], context: str) -> dict[str, str]:
    """Extract declared control bullets while leaving all other prose opaque."""

    result: dict[str, str] = {}
    pattern = re.compile(r"^[ \t]*-[ \t]+([a-z][a-z0-9_]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
    for line_number, line in enumerate(mask_fenced_markdown(block).splitlines(), start=1):
        match = pattern.fullmatch(line)
        if match is None or match.group(1) not in known_fields:
            continue
        key, value = match.groups()
        require(
            key not in result,
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
        re.finditer(r"^[ \t]{0,3}###[ \t]+([^\s]+)(?:\s|$)", control_section, re.MULTILINE)
    )
    criteria: list[str] = []
    for index, heading in enumerate(headings):
        criterion_id = clean_markdown_value(heading.group(1))
        require(SAFE_ID_RE.fullmatch(criterion_id), "invalid_acceptance_id", criterion_id=criterion_id)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        require(
            section[heading.end() : end].strip(),
            "invalid_acceptance_content",
            criterion_id=criterion_id,
        )
        criteria.append(criterion_id)
    require(criteria, "missing_acceptance_criteria")
    require(len(criteria) == len(set(criteria)), "duplicate_acceptance_criteria")
    return tuple(criteria)


def validate_result_ref_shape(result_ref: str, worktrack_id: str) -> None:
    match = re.fullmatch(
        r"\.servo/worktrack/([^/#]+)/finished-handback\.ya?ml"
        r"(?:#[A-Za-z0-9][A-Za-z0-9._:/-]*)?",
        result_ref,
    )
    require(match is not None and match.group(1) == worktrack_id, "unstable_result_ref", worktrack_id=worktrack_id, result_ref=result_ref)


def heading_ranges(section: str, pattern: str) -> list[tuple[re.Match[str], int]]:
    headings = list(re.finditer(pattern, mask_fenced_markdown(section), re.MULTILINE))
    return [
        (heading, headings[index + 1].start() if index + 1 < len(headings) else len(section))
        for index, heading in enumerate(headings)
    ]


def parse_worktrack_entries(section: str, criteria: Iterable[str]) -> dict[str, WorktrackEntry]:
    ranges = heading_ranges(section, r"^[ \t]{0,3}###[ \t]+\[([ xX])\][ \t]+([^\r\n]+?)[ \t]*\r?$")
    require(ranges, "missing_worktrack_entries")
    criterion_set = set(criteria)
    entries: dict[str, WorktrackEntry] = {}
    for heading, end in ranges:
        checked = heading.group(1).lower() == "x"
        heading_id = clean_markdown_value(heading.group(2))
        block = section[heading.end() : end]
        fields = parse_known_bullets(block, ENTRY_ALLOWED_FIELDS, f"Worktrack {heading_id}")
        missing = sorted(ENTRY_REQUIRED_FIELDS - fields.keys())
        dependency_fields = {"depends_on", "execution_condition"} & fields.keys()
        if not dependency_fields:
            missing.append("depends_on_or_execution_condition")
        require(
            not missing and len(dependency_fields) == 1,
            "invalid_worktrack_entry_fields",
            worktrack_id=heading_id,
            missing=missing,
            dependency_fields=sorted(dependency_fields),
        )
        worktrack_id = clean_markdown_value(fields["worktrack_id"])
        require(SAFE_ID_RE.fullmatch(worktrack_id) and worktrack_id == heading_id, "invalid_worktrack_id", heading_id=heading_id, worktrack_id=worktrack_id)
        require(worktrack_id not in entries, "duplicate_worktrack", worktrack_id=worktrack_id)
        outcome = clean_markdown_value(fields["outcome"])
        require(outcome and "\n" not in outcome, "invalid_worktrack_entry", worktrack_id=worktrack_id)
        condition = clean_markdown_value(fields["condition"])
        require(condition in ALLOWED_CONDITIONS, "invalid_worktrack_condition", worktrack_id=worktrack_id, condition=condition)
        expected_dependency = {"required": "depends_on", "conditional": "execution_condition"}.get(condition)
        require(
            expected_dependency is None or dependency_fields == {expected_dependency},
            "invalid_worktrack_dependency_form",
            worktrack_id=worktrack_id,
            condition=condition,
            expected=expected_dependency,
            observed=sorted(dependency_fields),
        )
        depends_on = parse_inline_list(fields.get("depends_on", "[]"), "depends_on", worktrack_id)
        execution_condition = fields.get("execution_condition")
        if execution_condition is not None and nullable(execution_condition) is None:
            fail("invalid_worktrack_entry", worktrack_id=worktrack_id)
        covers = parse_inline_list(fields["covers"], "covers", worktrack_id)
        require(covers, "invalid_worktrack_coverage", worktrack_id=worktrack_id)
        unknown_coverage = sorted(set(covers) - criterion_set)
        require(not unknown_coverage, "invalid_worktrack_coverage", worktrack_id=worktrack_id, unknown=unknown_coverage)
        result_ref = nullable(fields["result_ref"])
        if result_ref is not None:
            validate_result_ref_shape(result_ref, worktrack_id)
        require(checked == (result_ref is not None), "checkbox_result_mismatch", worktrack_id=worktrack_id, checked=checked, result_ref=result_ref)
        entries[worktrack_id] = WorktrackEntry(
            worktrack_id=worktrack_id,
            fields={key: clean_markdown_value(value) for key, value in fields.items()},
            depends_on=depends_on,
            covers=covers,
            result_ref=result_ref,
        )

    for entry in entries.values():
        unknown_dependencies = sorted(set(entry.depends_on) - entries.keys())
        require(not unknown_dependencies, "unknown_worktrack_dependency", worktrack_id=entry.worktrack_id, unknown=unknown_dependencies)
        require(entry.worktrack_id not in entry.depends_on, "cyclic_worktrack_dependency", worktrack_id=entry.worktrack_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(worktrack_id: str) -> None:
        require(worktrack_id not in visiting, "cyclic_worktrack_dependency", worktrack_id=worktrack_id)
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


def parse_amendments(section: str, revision: int, worktrack_ids: Iterable[str]) -> tuple[dict[int, dict[str, str]], dict[int, str]]:
    ranges = heading_ranges(section, r"^[ \t]{0,3}###[ \t]+Revision[ \t]+(\d+)[ \t]+Amendment[ \t]*\r?$")
    if revision == 1:
        require(not ranges, "invalid_initial_amendment")
        structured = parse_known_bullets(section, AMENDMENT_ALLOWED_FIELDS, "revision 1 amendment prose")
        require(not structured, "invalid_initial_amendment", observed=sorted(structured))
        return {}, {}
    observed = [int(heading.group(1)) for heading, _ in ranges]
    expected = list(range(2, revision + 1))
    require(observed == expected, "invalid_amendment_history", revision=revision, expected=expected, observed=observed)
    worktrack_set = set(worktrack_ids)
    amendments: dict[int, dict[str, str]] = {}
    blocks: dict[int, str] = {}
    for index, (heading, end) in enumerate(ranges):
        amendment_revision = observed[index]
        fields = parse_known_bullets(section[heading.end() : end], AMENDMENT_ALLOWED_FIELDS, f"Revision {amendment_revision} Amendment")
        missing = sorted(AMENDMENT_REQUIRED_FIELDS - fields.keys())
        require(not missing, "incomplete_amendment", revision=amendment_revision, missing=missing)
        for key in AMENDMENT_REQUIRED_FIELDS:
            require(nullable(fields[key]) is not None, "incomplete_amendment", revision=amendment_revision, field=key)
        require(
            "revision" not in fields
            or clean_markdown_value(fields["revision"]) == str(amendment_revision),
            "invalid_amendment_history",
            heading_revision=amendment_revision,
            field_revision=clean_markdown_value(fields["revision"])
            if "revision" in fields
            else None,
        )
        affected = parse_inline_list(fields["affected_worktracks"], "affected_worktracks", f"revision-{amendment_revision}")
        invalid_affected = sorted(
            value
            for value in affected
            if not SAFE_ID_RE.fullmatch(value) or value not in worktrack_set
        )
        require(affected and not invalid_affected, "invalid_amendment_worktracks", revision=amendment_revision, invalid=invalid_affected)
        amendments[amendment_revision] = {key: clean_markdown_value(value) for key, value in fields.items()}
        # Boundary whitespace and commentary are approved history bytes.
        blocks[amendment_revision] = section[heading.start() : end]
    return amendments, blocks


def parse_final_refs(section: str, milestone_id: str) -> dict[str, str | None]:
    expected = {"milestone_gate_ref", "final_acceptance_ref"}
    fields = parse_known_bullets(section, expected, "Finalization References")
    missing = sorted(expected - fields.keys())
    require(not missing, "missing_final_refs", missing=missing)
    result = {key: nullable(value) for key, value in fields.items()}
    for key, value in result.items():
        if value is None:
            continue
        require(
            re.fullmatch(
                r"\.servo/milestone/[A-Za-z0-9][A-Za-z0-9._-]*\.md"
                r"(?:#[A-Za-z0-9][A-Za-z0-9._:/-]*)?",
                value,
            ),
            "unstable_final_ref",
            milestone_id=milestone_id,
            field=key,
            value=value,
        )
    return result


def parse_baseline_ref(value: str) -> tuple[str, str]:
    require("@" in value, "invalid_baseline_ref")
    branch, checkpoint = value.rsplit("@", 1)
    require(
        branch and not branch.startswith("-") and ".." not in branch and not branch.endswith("/"),
        "invalid_baseline_ref",
    )
    require(FULL_SHA_RE.fullmatch(checkpoint), "invalid_baseline_ref")
    return branch, checkpoint


def parse_document(raw: bytes, mode: str) -> Document:
    require(len(raw) <= MAX_DOCUMENT_BYTES, "document_too_large", max_bytes=MAX_DOCUMENT_BYTES)
    require(b"\x00" not in raw, "invalid_encoding", "document contains NUL bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("invalid_encoding")
    require(not re.search(r"\r(?!\n)", text), "invalid_newlines")
    fields, body = parse_frontmatter(text)
    require(fields["artifact_type"] == "milestone", "invalid_artifact_type")
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
    require(not empty, "empty_frontmatter_fields", fields=empty)
    try:
        updated = datetime.fromisoformat(fields["updated"].replace("Z", "+00:00"))
    except ValueError:
        fail("invalid_updated_timestamp")
    require(updated.tzinfo is not None, "invalid_updated_timestamp")
    milestone_id = fields["milestone_id"]
    require(SAFE_ID_RE.fullmatch(milestone_id), "invalid_milestone_id", milestone_id=milestone_id)
    try:
        revision = int(fields["revision"])
    except ValueError:
        fail("invalid_revision")
    require(revision >= 1, "invalid_revision")
    require(fields["maturity"] == "planned", "non_planned_document")
    require(
        fields["disposition"] in ALLOWED_DISPOSITIONS,
        "invalid_disposition",
        disposition=fields["disposition"],
    )
    require(
        mode != "create" or (revision == 1 and fields["disposition"] == "open"),
        "invalid_create_state",
        revision=revision,
        disposition=fields["disposition"],
    )
    require(mode != "amend" or revision > 1, "invalid_amendment_revision")
    for key in ("milestone_branch", "close_target"):
        branch = fields[key]
        require(
            not branch.startswith("-") and ".." not in branch and not branch.endswith("/"),
            "invalid_branch_name",
            field=key,
            branch=branch,
        )
    source_branch, _ = parse_baseline_ref(fields["baseline_ref"])
    require(
        fields["milestone_branch"] not in {source_branch, fields["close_target"]},
        "invalid_branch_contract",
        milestone_branch=fields["milestone_branch"],
        source_branch=source_branch,
        close_target=fields["close_target"],
    )
    sections = split_sections(body, fields["title"])
    criteria = parse_criteria(sections["Milestone-Level Acceptance Criteria"])
    entries = parse_worktrack_entries(sections["Worktrack Tasklist"], criteria)
    amendments, amendment_blocks = parse_amendments(sections["Amendments"], revision, entries)
    final_refs = parse_final_refs(sections["Finalization References"], milestone_id)
    return Document(
        raw=raw,
        digest=sha256_digest(raw),
        fields=fields,
        milestone_id=milestone_id,
        revision=revision,
        criteria=criteria,
        entries=entries,
        amendments=amendments,
        amendment_blocks=amendment_blocks,
        final_refs=final_refs,
    )


def run_git(
    repo_root: Path, arguments: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    require(
        not check or completed.returncode == 0,
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
    require(repo_root.is_dir() and (repo_root / ".git").exists(), "invalid_repo_root")
    return repo_root


def ensure_safe_milestone_dir(repo_root: Path) -> Path:
    servo_dir = repo_root / ".servo"
    milestone_dir = servo_dir / "milestone"
    for path in (servo_dir, milestone_dir):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            fail("missing_milestone_directory", path=str(path))
        require(
            not stat.S_ISLNK(metadata.st_mode) and stat.S_ISDIR(metadata.st_mode),
            "unsafe_milestone_directory",
            path=str(path),
        )
    require(
        milestone_dir.resolve(strict=True).parent == servo_dir.resolve(strict=True),
        "unsafe_milestone_directory",
    )
    return milestone_dir


def safe_read_regular(path: Path, *, missing_ok: bool) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        fail("missing_file", "required file is missing", path=str(path))
    require(
        not stat.S_ISLNK(metadata.st_mode) and stat.S_ISREG(metadata.st_mode),
        "unsafe_file_type",
        path=str(path),
    )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        fail("unsafe_file_read", path=str(path))
    try:
        opened = os.fstat(descriptor)
        require(
            (opened.st_dev, opened.st_ino) == (metadata.st_dev, metadata.st_ino),
            "unsafe_file_read",
            path=str(path),
        )
        require(stat.S_ISREG(opened.st_mode), "unsafe_file_type", path=str(path))
        require(
            opened.st_size <= MAX_DOCUMENT_BYTES,
            "document_too_large",
            path=str(path),
        )
        chunks: list[bytes] = []
        remaining = MAX_DOCUMENT_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        require(len(data) <= MAX_DOCUMENT_BYTES, "document_too_large", path=str(path))
        return data
    finally:
        os.close(descriptor)


def current_branch(repo_root: Path) -> str | None:
    completed = run_git(repo_root, ["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def read_branch_ref(repo_root: Path, branch: str) -> str | None:
    completed = run_git(repo_root, ["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"], check=False)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value if FULL_SHA_RE.fullmatch(value) else None


def branch_descends_from(repo_root: Path, branch_commit: str, baseline: str) -> bool:
    return run_git(
        repo_root,
        ["merge-base", "--is-ancestor", baseline, branch_commit],
        check=False,
    ).returncode == 0


def validate_stable_ref_target(repo_root: Path, value: str) -> None:
    relative = value.split("#", 1)[0]
    target = repo_root.joinpath(*relative.split("/"))
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        fail("missing_stable_ref", ref=value)
    require(resolved.is_relative_to(repo_root), "unsafe_stable_ref", ref=value)
    safe_read_regular(target, missing_ok=False)


def validate_git_contract(repo_root: Path, document: Document) -> tuple[str, str]:
    stable_refs = [entry.result_ref for entry in document.entries.values()]
    stable_refs.extend(document.final_refs.values())
    for value in stable_refs:
        if value is not None:
            validate_stable_ref_target(repo_root, value)
    source_branch, baseline = parse_baseline_ref(document.fields["baseline_ref"])
    for branch in (
        source_branch,
        document.fields["milestone_branch"],
        document.fields["close_target"],
    ):
        checked = run_git(repo_root, ["check-ref-format", "--branch", branch], check=False)
        require(checked.returncode == 0, "invalid_branch_name", branch=branch)
    require(source_branch != document.fields["milestone_branch"], "invalid_branch_contract")
    resolved = run_git(
        repo_root,
        ["rev-parse", "--verify", f"{baseline}^{{commit}}"],
        check=False,
    )
    require(
        resolved.returncode == 0 and resolved.stdout.strip() == baseline,
        "missing_baseline_commit",
        baseline=baseline,
    )
    source_head = read_branch_ref(repo_root, source_branch)
    require(
        source_head is not None and branch_descends_from(repo_root, source_head, baseline),
        "baseline_branch_conflict",
        source_branch=source_branch,
        baseline=baseline,
        source_head=source_head,
    )
    close_target = document.fields["close_target"]
    require(read_branch_ref(repo_root, close_target) is not None, "missing_close_target", close_target=close_target)
    return source_branch, baseline


def resolve_branch_contract(
    repo_root: Path,
    candidate: Document,
    current: Document | None,
    baseline: str,
    *,
    mutate: bool,
    identical_replay: bool = False,
) -> tuple[str, bool, str]:
    branch = candidate.fields["milestone_branch"]
    existing = read_branch_ref(repo_root, branch)
    contract_changed = current is not None and any(
        current.fields[key] != candidate.fields[key]
        for key in ("milestone_branch", "baseline_ref", "close_target")
    )
    if existing is not None:
        if current is None or contract_changed:
            require(
                existing == baseline,
                "branch_ref_conflict",
                branch=branch,
                expected=baseline,
                actual=existing,
            )
            return "existing_at_baseline", False, baseline
        require(
            branch_descends_from(repo_root, existing, baseline),
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
    require(current is None or contract_changed, "missing_milestone_branch", branch=branch)
    if not mutate:
        return "would_create", False, baseline
    require(current_branch(repo_root) != branch, "unsafe_current_branch", branch=branch)
    created = run_git(
        repo_root,
        ["update-ref", f"refs/heads/{branch}", baseline, "0" * 40],
        check=False,
    )
    require(
        created.returncode == 0,
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
        fail("injected_failure", "test-only failure injection", failure_point=expected)


def enforce_init_authority(
    candidate: Document,
    current: Document | None,
    approval_ref: str | None,
) -> None:
    if candidate.revision > 1:
        amendment = candidate.amendments.get(candidate.revision)
        require(amendment is not None, "incomplete_amendment", revision=candidate.revision)
        assert amendment is not None
        require(
            approval_ref is None or amendment["approval_ref"] == approval_ref,
            "approval_ref_mismatch",
            document_approval_ref=amendment["approval_ref"],
            supplied_approval_ref=approval_ref,
        )
    candidate_results = {
        worktrack_id: entry.result_ref for worktrack_id, entry in candidate.entries.items()
    }
    if current is None:
        newly_accepted = sorted(
            worktrack_id for worktrack_id, result_ref in candidate_results.items() if result_ref is not None
        )
        non_null_final = sorted(key for key, value in candidate.final_refs.items() if value is not None)
        require(
            not newly_accepted,
            "result_authority_violation",
            worktracks=newly_accepted,
        )
        require(
            not non_null_final,
            "final_acceptance_authority_violation",
            final_refs=non_null_final,
        )
        return
    require(candidate.milestone_id == current.milestone_id, "milestone_id_change")
    require(
        current.fields["disposition"] == "open",
        "lifecycle_authority_violation",
        disposition=current.fields["disposition"],
    )
    require(
        candidate.fields["disposition"] == current.fields["disposition"],
        "lifecycle_authority_violation",
        current=current.fields["disposition"],
        candidate=candidate.fields["disposition"],
    )
    for revision, approved_block in current.amendment_blocks.items():
        require(
            candidate.amendment_blocks.get(revision) == approved_block,
            "amendment_history_change",
            revision=revision,
        )
    for worktrack_id, result_ref in candidate_results.items():
        previous = current.entries.get(worktrack_id)
        previous_ref = previous.result_ref if previous is not None else None
        require(
            result_ref == previous_ref,
            "result_authority_violation",
            worktrack_id=worktrack_id,
            previous=previous_ref,
            candidate=result_ref,
        )
    for worktrack_id, entry in current.entries.items():
        if entry.result_ref is None:
            continue
        require(
            worktrack_id in candidate.entries,
            "result_authority_violation",
            worktrack_id=worktrack_id,
        )
        require(
            candidate.entries[worktrack_id].fields == entry.fields,
            "result_authority_violation",
            worktrack_id=worktrack_id,
            reason="accepted Worktrack control fields cannot be reinterpreted",
        )
    require(
        candidate.final_refs == current.final_refs,
        "final_acceptance_authority_violation",
    )


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
    require(
        candidate.milestone_id == current.milestone_id,
        "canonical_identity_conflict",
        current=current.milestone_id,
        candidate=candidate.milestone_id,
    )
    if candidate.revision == current.revision and candidate.raw == current.raw:
        return "already_applied", current
    require(
        candidate.revision != current.revision,
        "same_revision_conflict",
        revision=candidate.revision,
        current_digest=current.digest,
        candidate_digest=candidate.digest,
    )
    require(
        candidate.revision >= current.revision,
        "stale_revision",
        current_revision=current.revision,
        candidate_revision=candidate.revision,
    )
    require(
        candidate.revision <= current.revision + 1,
        "skipped_revision",
        current_revision=current.revision,
        candidate_revision=candidate.revision,
    )
    require(
        mode == "amend",
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
        require(
            expected_revision == 0 and expected_digest == "absent",
            "expected_state_mismatch",
        )
        return
    require(current is not None, "expected_state_mismatch", "current document is missing")
    assert current is not None
    if action == "amend":
        require(
            expected_revision == current.revision and expected_digest == current.digest,
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
    current_state = expected_revision == current.revision and expected_digest == current.digest
    create_prior = (
        current.revision == 1 and expected_revision == 0 and expected_digest == "absent"
    )
    require(
        current_state or create_prior,
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
    candidate = parse_document(safe_read_regular(Path(args.candidate), missing_ok=False) or b"", args.mode)
    target = milestone_dir / f"{candidate.milestone_id}.md"
    current_raw = safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, current_raw, args.mode)
    enforce_init_authority(candidate, current, None)
    _, baseline = validate_git_contract(repo_root, candidate)
    branch_outcome, _, _ = resolve_branch_contract(
        repo_root,
        candidate,
        current,
        baseline,
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
    branch = candidate.fields["milestone_branch"]
    if branch_created and read_branch_ref(repo_root, branch) == branch_baseline:
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
    candidate = parse_document(safe_read_regular(Path(args.candidate), missing_ok=False) or b"", args.mode)
    require(DIGEST_RE.fullmatch(args.approved_digest), "invalid_approved_digest")
    require(
        candidate.digest == args.approved_digest,
        "approval_digest_mismatch",
        approved_digest=args.approved_digest,
        candidate_digest=candidate.digest,
    )
    approval_ref = args.approval_ref.strip()
    require(
        approval_ref and "\n" not in approval_ref and len(approval_ref) <= 512,
        "missing_approval_ref",
    )
    require(
        args.expected_current_digest == "absent"
        or DIGEST_RE.fullmatch(args.expected_current_digest),
        "invalid_expected_digest",
    )

    target = milestone_dir / f"{candidate.milestone_id}.md"
    previous_raw = safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, previous_raw, args.mode)
    validate_expected_state(
        action, candidate, current, args.expected_current_revision, args.expected_current_digest
    )
    enforce_init_authority(candidate, current, approval_ref)
    _, branch_baseline = validate_git_contract(repo_root, candidate)

    original_checkout = current_branch(repo_root)
    branch_created = False
    branch_outcome = "not_attempted"
    temp_path: Path | None = None
    replaced = False
    try:
        branch_outcome, branch_created, branch_baseline = resolve_branch_contract(
            repo_root,
            candidate,
            current,
            branch_baseline,
            mutate=action != "already_applied",
            identical_replay=action == "already_applied",
        )
        inject_failure(args.test_failure_point, "after-branch")

        if action != "already_applied":
            temp_path = write_temp(milestone_dir, candidate.milestone_id, candidate.raw)
            inject_failure(args.test_failure_point, "before-replace")
            latest_raw = safe_read_regular(target, missing_ok=True)
            require(latest_raw == previous_raw, "stale_compare_and_swap")
            os.replace(temp_path, target)
            temp_path = None
            replaced = True
            fsync_directory(milestone_dir)
            inject_failure(args.test_failure_point, "after-replace")

        readback = safe_read_regular(target, missing_ok=False)
        require(
            readback == candidate.raw,
            "stale_compare_and_swap" if action == "already_applied" else "readback_mismatch",
            "canonical readback does not match approved bytes",
        )
        require(current_branch(repo_root) == original_checkout, "checkout_changed")
        # Recheck branch state after persistence; no branch is created here.
        resolve_branch_contract(
            repo_root,
            candidate,
            candidate if action == "already_applied" else current,
            branch_baseline,
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
                    "commit_point": "after_replace" if replaced else "before_replace",
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

    outcome = {"create": "created", "amend": "revised"}.get(action, "already_applied")
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
    parser = argparse.ArgumentParser(description="Check or persist one complete approved Milestone document")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands = {
        "validate": "check complete exact bytes without writes",
        "apply": "persist complete exact approved bytes",
    }
    parsers = {name: subparsers.add_parser(name, help=help_text) for name, help_text in commands.items()}
    for command in parsers.values():
        command.add_argument("--mode", choices=("create", "amend"), required=True)
        command.add_argument("--candidate", required=True)
        command.add_argument("--repo-root", required=True)
    apply = parsers["apply"]
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
    if getattr(args, "test_failure_point", None) and os.environ.get("SERVO_MILESTONE_INIT_ALLOW_TEST_FAILURE") != "1":
        fail("test_failure_not_enabled")
    return validate_command(args) if args.command == "validate" else apply_command(args)


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
