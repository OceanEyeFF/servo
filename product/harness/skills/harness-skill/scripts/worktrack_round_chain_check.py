#!/usr/bin/env python3
"""Validate the Candidate Worktrack round chain without mutating it."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ROUND_YAML = re.compile(r"^worktrack-r(\d{3})\.yaml$")
REVIEW_COMMENT = re.compile(r"^worktrack-r(\d{3})-review-comment\.md$")
KEY_VALUE_LINE = re.compile(
    r"^([ \t]*)(?:(-[ \t]+))?([A-Za-z_][A-Za-z0-9_-]*):"
    r"(?:[ \t]*(.*?))?[ \t]*$"
)
ROUND_STRUCTURAL_FIELDS = frozenset(
    {"worktrack_id", "round_id", "previous_round", "review_comment_ref"}
)
COMMENT_STRUCTURAL_FIELDS = frozenset(
    {"worktrack_id", "reviewed_round", "next_round"}
)


def resolve_repo_root() -> tuple[Path | None, str]:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None, (
            completed.stderr.strip()
            or "current directory is not inside a Git repository"
        )
    return Path(completed.stdout.strip()).resolve(), ""


def clean_scalar(raw: str) -> str:
    return raw.split("#", 1)[0].strip().strip("`\"'")


def structural_values(
    content: str,
    *,
    required_fields: tuple[str, ...],
    structural_fields: frozenset[str],
    context: str,
    blockers: list[str],
    exact_fields: bool = False,
) -> dict[str, str]:
    values: dict[str, str] = {}
    seen_top_level: set[str] = set()

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = KEY_VALUE_LINE.fullmatch(line)
        if match is None:
            if exact_fields:
                append_unique(
                    blockers,
                    f"{context}: invalid frontmatter line {line_number}",
                )
            continue

        indent, sequence_marker, field, raw_value = match.groups()
        if exact_fields and field not in structural_fields:
            append_unique(
                blockers,
                f"{context}: unexpected frontmatter field {field}",
            )
            continue
        if field not in structural_fields:
            continue
        if indent or sequence_marker:
            append_unique(
                blockers,
                f"{context}: {field} must be a top-level field",
            )
            continue
        if field in seen_top_level:
            append_unique(
                blockers,
                f"{context}: duplicate top-level field {field}",
            )
            continue

        seen_top_level.add(field)
        value = clean_scalar(raw_value or "")
        if not value:
            append_unique(blockers, f"{context}: {field} must not be empty")
            continue
        values[field] = value

    for field in required_fields:
        if field not in seen_top_level:
            append_unique(
                blockers,
                f"{context}: missing top-level field {field}",
            )

    return values


def frontmatter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    return ""


def round_name(index: int) -> str:
    return f"R{index:03d}"


def round_yaml_name(index: int) -> str:
    return f"worktrack-r{index:03d}.yaml"


def review_comment_name(index: int) -> str:
    return f"worktrack-r{index:03d}-review-comment.md"


def runtime_ref(worktrack_id: str, name: str) -> str:
    return f".servo/tmp/{worktrack_id}/{name}"


def append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def validate_round_yaml(
    path: Path,
    *,
    worktrack_id: str,
    index: int,
    blockers: list[str],
) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        append_unique(blockers, f"cannot read {path.name}: {exc}")
        return

    required_fields = ("worktrack_id", "round_id")
    if index > 0:
        required_fields += ("previous_round", "review_comment_ref")
    values = structural_values(
        content,
        required_fields=required_fields,
        structural_fields=ROUND_STRUCTURAL_FIELDS,
        context=path.name,
        blockers=blockers,
    )

    expected_round = round_name(index)
    if values.get("worktrack_id") and values["worktrack_id"] != worktrack_id:
        append_unique(blockers, f"{path.name}: worktrack_id mismatch")
    if values.get("round_id") and values["round_id"] != expected_round:
        append_unique(blockers, f"{path.name}: round_id must be {expected_round}")

    if index == 0:
        return

    expected_previous = round_name(index - 1)
    if values.get("previous_round") and values["previous_round"] != expected_previous:
        append_unique(
            blockers,
            f"{path.name}: previous_round must be {expected_previous}",
        )
    expected_comment = runtime_ref(worktrack_id, review_comment_name(index))
    if (
        values.get("review_comment_ref")
        and values["review_comment_ref"] != expected_comment
    ):
        append_unique(
            blockers,
            f"{path.name}: review_comment_ref must be {expected_comment}",
        )


def validate_review_comment(
    path: Path,
    *,
    worktrack_id: str,
    index: int,
    blockers: list[str],
) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        append_unique(blockers, f"cannot read {path.name}: {exc}")
        return

    metadata = frontmatter(content)
    if not metadata:
        append_unique(blockers, f"{path.name}: YAML frontmatter is required")
        return
    values = structural_values(
        metadata,
        required_fields=("worktrack_id", "reviewed_round", "next_round"),
        structural_fields=COMMENT_STRUCTURAL_FIELDS,
        context=path.name,
        blockers=blockers,
        exact_fields=True,
    )
    if values.get("worktrack_id") and values["worktrack_id"] != worktrack_id:
        append_unique(blockers, f"{path.name}: worktrack_id mismatch")

    expected_reviewed = round_name(index - 1)
    expected_next = round_name(index)
    if values.get("reviewed_round") and values["reviewed_round"] != expected_reviewed:
        append_unique(
            blockers,
            f"{path.name}: reviewed_round must be {expected_reviewed}",
        )
    if values.get("next_round") and values["next_round"] != expected_next:
        append_unique(
            blockers,
            f"{path.name}: next_round must be {expected_next}",
        )


def discover_round_files(
    runtime_dir: Path, blockers: list[str]
) -> tuple[dict[int, Path], dict[int, Path]]:
    round_files: dict[int, Path] = {}
    comment_files: dict[int, Path] = {}

    try:
        entries = sorted(runtime_dir.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        append_unique(blockers, f"cannot inspect runtime directory: {exc}")
        return round_files, comment_files

    for entry in entries:
        if not entry.is_file():
            continue
        lowered = entry.name.lower()
        round_match = ROUND_YAML.fullmatch(lowered)
        comment_match = REVIEW_COMMENT.fullmatch(lowered)
        if not round_match and not comment_match:
            if lowered.startswith("worktrack-r"):
                append_unique(blockers, f"unexpected round-chain filename: {entry.name}")
            continue
        if entry.name != lowered:
            append_unique(blockers, f"round-chain filename must be lowercase: {entry.name}")

        match = round_match or comment_match
        assert match is not None
        index = int(match.group(1))
        target = round_files if round_match else comment_files
        if index in target:
            append_unique(blockers, f"duplicate round-chain index: R{index:03d}")
            continue
        target[index] = entry

    return round_files, comment_files


def check_chain(worktrack_id: str, expect: str) -> dict[str, object]:
    blockers: list[str] = []
    repo_root, root_error = resolve_repo_root()
    if repo_root is None:
        append_unique(blockers, root_error)

    if not SAFE_ID.fullmatch(worktrack_id):
        append_unique(
            blockers,
            "worktrack_id must use only letters, numbers, dot, underscore, or hyphen",
        )

    runtime_dir = (
        repo_root / f".servo/tmp/{worktrack_id}"
        if repo_root and SAFE_ID.fullmatch(worktrack_id)
        else Path()
    )
    if repo_root and SAFE_ID.fullmatch(worktrack_id) and not runtime_dir.is_dir():
        append_unique(blockers, f"runtime directory is missing: {runtime_dir}")

    round_files: dict[int, Path] = {}
    comment_files: dict[int, Path] = {}
    if runtime_dir.is_dir():
        round_files, comment_files = discover_round_files(runtime_dir, blockers)

    current_index = -1
    pending_index = 0
    terminal = "invalid"

    if 0 in comment_files:
        append_unique(blockers, "R000 cannot have a review-comment file")
    if 0 not in round_files:
        append_unique(blockers, "worktrack-r000.yaml is required")
    else:
        validate_round_yaml(
            round_files[0],
            worktrack_id=worktrack_id,
            index=0,
            blockers=blockers,
        )
        current_index = 0

        while True:
            pending_index = current_index + 1
            comment = comment_files.get(pending_index)
            round_yaml = round_files.get(pending_index)

            if comment is None:
                if round_yaml is not None:
                    append_unique(
                        blockers,
                        f"{round_yaml.name}: matching review comment is missing",
                    )
                terminal = "review"
                break

            validate_review_comment(
                comment,
                worktrack_id=worktrack_id,
                index=pending_index,
                blockers=blockers,
            )
            if round_yaml is None:
                terminal = "redo"
                break

            validate_round_yaml(
                round_yaml,
                worktrack_id=worktrack_id,
                index=pending_index,
                blockers=blockers,
            )
            current_index = pending_index

    all_indices = set(round_files) | set(comment_files)
    for index in sorted(item for item in all_indices if item > pending_index):
        append_unique(
            blockers,
            f"round chain has a gap before {round_name(index)}",
        )

    if expect == "review" and terminal != "review":
        append_unique(blockers, "round chain is not ready for Review")
    if expect == "redo" and terminal != "redo":
        append_unique(blockers, "round chain is not ready for redo")

    latest_round = round_name(current_index) if current_index >= 0 else None
    next_round = round_name(pending_index)
    latest_ref = (
        runtime_ref(worktrack_id, round_yaml_name(current_index))
        if current_index >= 0
        else None
    )

    return {
        "valid": not blockers,
        "blocked": bool(blockers),
        "blocked_why": blockers,
        "worktrack_id": worktrack_id,
        "expect": expect,
        "latest_round": latest_round,
        "next_round": next_round,
        "latest_round_ref": latest_ref,
        "expected_review_comment_ref": runtime_ref(
            worktrack_id, review_comment_name(pending_index)
        ),
        "expected_round_ref": runtime_ref(
            worktrack_id, round_yaml_name(pending_index)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Candidate Worktrack round-chain structure"
    )
    parser.add_argument("--worktrack-id", required=True)
    parser.add_argument("--expect", required=True, choices=["review", "redo"])
    args = parser.parse_args()

    result = check_chain(args.worktrack_id, args.expect)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1 if result["blocked"] else 0)


if __name__ == "__main__":
    main()
