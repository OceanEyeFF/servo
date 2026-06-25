#!/usr/bin/env python3
"""Validate markdown Repo Analysis artifacts for required contract fields."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO_ANALYSIS_PATHS = (
    REPO_ROOT / "product" / ".servo_template" / "repo" / "analysis.md",
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "harness-set-goal-skill"
    / "assets"
    / "repo"
    / "analysis.md",
)
REQUIRED_FIELDS_BY_SECTION = {
    "Metadata": (
        "repo",
        "baseline_branch",
        "baseline_ref",
        "updated",
        "analysis_status",
    ),
    "Facts": ("facts",),
    "Inferences": ("inferences",),
    "Unknowns": ("unknowns",),
    "Main Contradiction": ("current_main_contradiction", "main_aspect"),
    "Priority Judgment": (
        "current_highest_priority",
        "long_term_highest_priority",
        "do_not_do_now",
    ),
    "Routing Projection": (
        "recommended_repo_action",
        "recommended_next_route",
        "suggested_node_type",
        "continuation_ready",
        "continuation_blockers",
    ),
    "Writeback Eligibility": ("writeback_eligibility",),
}
SECTION_PATTERN = re.compile(r"^## (?P<name>.+?)\s*$")


@dataclass(frozen=True)
class ContractIssue:
    path: Path
    code: str
    detail: str


def parse_sections(markdown_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in markdown_text.splitlines():
        match = SECTION_PATTERN.match(line)
        if match:
            current_section = match.group("name")
            sections.setdefault(current_section, [])
            continue
        if current_section is not None:
            sections[current_section].append(line)
    return sections


def section_has_keyed_field(section_lines: list[str], field_name: str) -> bool:
    field_pattern = re.compile(rf"^\s*-\s+{re.escape(field_name)}\s*:")
    return any(field_pattern.match(line) for line in section_lines)


def validate_repo_analysis(path: Path) -> list[ContractIssue]:
    try:
        markdown_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [
            ContractIssue(
                path=path,
                code="missing-repo-analysis-file",
                detail="Repo Analysis markdown file does not exist",
            )
        ]

    sections = parse_sections(markdown_text)
    issues: list[ContractIssue] = []
    for section_name, required_fields in REQUIRED_FIELDS_BY_SECTION.items():
        section_lines = sections.get(section_name)
        if section_lines is None:
            issues.append(
                ContractIssue(
                    path=path,
                    code="missing-repo-analysis-section",
                    detail=f"missing required section: {section_name}",
                )
            )
            continue
        for field_name in required_fields:
            if not section_has_keyed_field(section_lines, field_name):
                issues.append(
                    ContractIssue(
                        path=path,
                        code="missing-repo-analysis-field",
                        detail=f"missing required field {field_name} in section {section_name}",
                    )
                )
    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Repo Analysis markdown required sections and fields."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Repo Analysis markdown files to validate. Defaults to canonical templates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = args.paths or list(DEFAULT_REPO_ANALYSIS_PATHS)

    issues: list[ContractIssue] = []
    for path in paths:
        issues.extend(validate_repo_analysis(path))

    if issues:
        print(f"repo analysis contract check failed: {len(issues)} issue(s)", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.code}: {issue.path} ({issue.detail})", file=sys.stderr)
        return 1

    print(f"repo analysis contract check passed for {len(paths)} file(s)")
    for path in paths:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
