#!/usr/bin/env python3
"""Run lightweight governance checks for path layout and AGENTS-based routing."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_CONTRACT_DOC = "AGENTS.md"
DOCS_BOOK = "docs/book.md"
PROJECT_MAINTENANCE_README = "docs/project-maintenance/README.md"
HARNESS_README = "docs/harness/README.md"
SKILL_SOURCE_ROOT = "product/harness/skills"
SKILL_SOURCE_README = "product/harness/skills/README.md"
SKILL_CATALOG_README = "docs/harness/catalog/README.md"
DEFAULT_SCAN_PATHS = [
    "README.md",
    "INDEX.md",
    "AGENTS.md",
    ".nav/README.md",
    "docs",
    "product",
    "toolchain",
]
REQUIRED_ENTRY_PATHS = [
    "AGENTS.md",
    "README.md",
    "INDEX.md",
    "docs/README.md",
    "docs/book.md",
    PROJECT_MAINTENANCE_README,
    HARNESS_README,
    "docs/harness/foundations/README.md",
    "docs/harness/foundations/Harness指导思想.md",
    "docs/harness/foundations/Harness运行协议.md",
    "docs/harness/scope/README.md",
    "docs/harness/artifact/README.md",
    "docs/harness/catalog/README.md",
    "docs/harness/catalog/supervisor.md",
    "docs/harness/catalog/repo.md",
    "docs/harness/catalog/worktrack.md",
    "docs/harness/artifact/repo/README.md",
    "docs/harness/artifact/repo/goal-charter.md",
    "docs/harness/artifact/repo/snapshot-status.md",
    "docs/harness/artifact/worktrack/README.md",
    "docs/harness/artifact/worktrack/contract.md",
    "docs/harness/artifact/worktrack/plan-task-queue.md",
    "docs/harness/artifact/worktrack/gate-evidence.md",
    "docs/harness/artifact/control/README.md",
    "docs/harness/artifact/control/control-state.md",
    "docs/harness/artifact/control/goal-change-request.md",
    "docs/harness/workflow-families/README.md",
    "docs/harness/workflow-families/repo-evolution/README.md",
    "docs/project-maintenance/foundations/README.md",
    "docs/project-maintenance/governance/README.md",
    "docs/project-maintenance/deploy/README.md",
    "docs/project-maintenance/testing/README.md",
    "docs/project-maintenance/usage-help/README.md",
    "docs/project-maintenance/governance/path-governance-checks.md",
    "docs/project-maintenance/foundations/root-directory-layering.md",
    "toolchain/toolchain-layering.md",
    "product/README.md",
    "product/harness/README.md",
    "product/harness/skills/README.md",
    "product/harness/adapters/README.md",
    "toolchain/README.md",
    "toolchain/scripts/README.md",
    "toolchain/scripts/test/README.md",
]
AGENTS_CONTRACT_BACKLINK_PATHS = [
    "AGENTS.md",
    "README.md",
    "INDEX.md",
    "docs/README.md",
    "docs/book.md",
    PROJECT_MAINTENANCE_README,
    HARNESS_README,
    "docs/project-maintenance/foundations/README.md",
    "docs/project-maintenance/governance/path-governance-checks.md",
    ".nav/README.md",
]
ENTRYPOINT_LINK_RULES = {
    "AGENTS.md": [
        "docs/README.md",
    ],
    "README.md": [
        "docs/README.md",
    ],
    "INDEX.md": [
        "docs/README.md",
        "docs/book.md",
    ],
    "docs/README.md": [
        "docs/book.md",
        PROJECT_MAINTENANCE_README,
        HARNESS_README,
    ],
    HARNESS_README: [
        "docs/harness/foundations/README.md",
        "docs/harness/scope/README.md",
        "docs/harness/artifact/README.md",
        "docs/harness/catalog/README.md",
        "docs/harness/workflow-families/README.md",
        AGENTS_CONTRACT_DOC,
    ],
    "docs/harness/catalog/README.md": [
        "docs/harness/catalog/supervisor.md",
        "docs/harness/catalog/repo.md",
        "docs/harness/catalog/worktrack.md",
        "docs/harness/catalog/milestone-status-skill.md",
        "docs/harness/catalog/skill-impact-matrix.md",
        "docs/harness/foundations/Harness指导思想.md",
        "docs/harness/foundations/Harness运行协议.md",
        "product/harness/skills/README.md",
    ],
    "docs/harness/foundations/README.md": [
        "docs/harness/foundations/Harness指导思想.md",
        "docs/harness/foundations/Harness运行协议.md",
        "docs/harness/foundations/skill-common-constraints.md",
    ],
    "docs/harness/scope/README.md": [
        "docs/harness/scope/repo-scope.md",
        "docs/harness/scope/worktrack-scope.md",
    ],
    "docs/harness/artifact/README.md": [
        "docs/harness/artifact/repo/README.md",
        "docs/harness/artifact/worktrack/README.md",
        "docs/harness/artifact/control/README.md",
    ],
    "docs/harness/artifact/repo/README.md": [
        "docs/harness/artifact/repo/discovery-input.md",
        "docs/harness/artifact/repo/goal-charter.md",
        "docs/harness/artifact/repo/repo-analysis.md",
        "docs/harness/artifact/repo/snapshot-status.md",
        "docs/harness/artifact/repo/worktrack-backlog.md",
    ],
    "docs/harness/artifact/worktrack/README.md": [
        "docs/harness/artifact/worktrack/contract.md",
        "docs/harness/artifact/worktrack/plan-task-queue.md",
        "docs/harness/artifact/worktrack/gate-evidence.md",
        "docs/harness/artifact/worktrack/dispatch-packet.md",
    ],
    "docs/harness/artifact/control/README.md": [
        "docs/harness/artifact/control/append-request.md",
        "docs/harness/artifact/control/control-state.md",
        "docs/harness/artifact/control/goal-change-request.md",
        "docs/harness/artifact/control/milestone.md",
        "docs/harness/artifact/control/node-type-registry.md",
    ],
    "docs/harness/workflow-families/README.md": [
        "docs/harness/workflow-families/repo-evolution/README.md",
    ],
    "docs/harness/workflow-families/repo-evolution/README.md": [
        "docs/harness/workflow-families/repo-evolution/standard-worktrack.md",
        "docs/harness/workflow-families/repo-evolution/policy-profiles.md",
    ],
    PROJECT_MAINTENANCE_README: [
        "docs/project-maintenance/foundations/README.md",
        "docs/project-maintenance/governance/README.md",
        "docs/project-maintenance/deploy/README.md",
        "docs/project-maintenance/testing/README.md",
        "docs/project-maintenance/usage-help/README.md",
    ],
    "docs/project-maintenance/foundations/README.md": [
        "docs/project-maintenance/foundations/root-directory-layering.md",
        "toolchain/toolchain-layering.md",
        AGENTS_CONTRACT_DOC,
    ],
    "docs/project-maintenance/governance/README.md": [
        "docs/project-maintenance/governance/review-verify-handbook.md",
        "docs/project-maintenance/governance/path-governance-checks.md",
        "docs/project-maintenance/governance/branch-pr-governance.md",
        "docs/project-maintenance/governance/global-language-style.md",
    ],
    "docs/project-maintenance/deploy/README.md": [
        "docs/project-maintenance/deploy/deploy-runbook.md",
        "docs/project-maintenance/deploy/skill-deployment-maintenance.md",
        "docs/project-maintenance/deploy/deploy-mapping-spec.md",
        "docs/project-maintenance/deploy/distribution-entrypoint-contract.md",
        "docs/project-maintenance/deploy/existing-code-adoption.md",
        "docs/project-maintenance/deploy/payload-provenance-trust-boundary.md",
    ],
    "docs/project-maintenance/testing/README.md": [
        "docs/project-maintenance/testing/python-script-test-execution.md",
        "docs/project-maintenance/testing/npx-command-test-execution.md",
        "docs/project-maintenance/testing/codex-post-deploy-behavior-tests.md",
        "docs/project-maintenance/testing/claude-post-deploy-behavior-tests.md",
    ],
    "docs/project-maintenance/usage-help/README.md": [
        "docs/project-maintenance/usage-help/codex.md",
        "docs/project-maintenance/usage-help/claude.md",
    ],
    "product/README.md": [
        "product/harness/README.md",
    ],
    "product/harness/README.md": [
        "docs/harness/README.md",
        "product/harness/skills/README.md",
        "product/harness/adapters/README.md",
    ],
}
REQUIRED_GITIGNORE_ENTRIES = [
    ".servo/",
    ".agents/",
    ".claude/",
    ".autoworkflow/",
    ".spec-workflow/",
    "**/__pycache__/",
    ".pytest_cache/",
    "*.pyc",
    "*.pyo",
]
FRONTMATTER_REQUIRED_KEYS = [
    "title",
    "status",
    "updated",
    "owner",
    "last_verified",
]
STATUS_RULES = [
    ("docs/project-maintenance/", {"active", "draft", "superseded"}),
    ("docs/harness/", {"active", "draft", "superseded"}),
]
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HISTORICAL_REFERENCE_HEADINGS = {
    "retained historical references",
    "historical references",
}
DEPLOY_TARGET_PREFIXES = (
    ".agents/",
    ".claude/",
)


@dataclass
class CheckReport:
    failures: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def add_failure(self, message: str) -> None:
        self.failures.append(message)

    def add_info(self, message: str) -> None:
        self.infos.append(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AGENTS routing contract, main entrypoints, and lightweight markdown links."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Override the repository root used for checks.",
    )
    parser.add_argument(
        "--scan-path",
        action="append",
        default=[],
        help="Additional file or directory to scan for markdown relative links.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable text.",
    )
    return parser.parse_args()


def iter_markdown_files(repo_root: Path, scan_paths: list[str]) -> list[Path]:
    markdown_files: list[Path] = []
    seen: set[Path] = set()
    for raw_path in scan_paths:
        path = repo_root / raw_path
        if not path.exists():
            continue
        if path.is_dir():
            candidates = sorted(path.rglob("*.md"))
        else:
            candidates = [path]
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                markdown_files.append(candidate)
    return markdown_files


def iter_relative_markdown_targets(text: str) -> list[str]:
    targets: list[str] = []
    for match in MARKDOWN_LINK_RE.findall(text):
        target = match.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        if not target:
            continue
        if target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
            continue
        if "://" in target:
            continue
        path_part = target.split("#", 1)[0].strip()
        if not path_part:
            continue
        targets.append(path_part)
    return targets


def normalize_markdown_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if not target:
        return None
    if target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
        return None
    if "://" in target:
        return None
    path_part = target.split("#", 1)[0].strip()
    return path_part or None


def iter_relative_markdown_target_matches(text: str) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for match in MARKDOWN_LINK_RE.finditer(text):
        target = normalize_markdown_target(match.group(1))
        if target is not None:
            targets.append((target, match.start()))
    return targets


def normalize_heading_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def markdown_section_text(text: str, heading: str) -> str | None:
    target_heading = normalize_heading_text(heading)
    lines = text.splitlines()
    section_start: int | None = None
    section_level: int | None = None

    for index, line in enumerate(lines):
        match = MARKDOWN_HEADING_RE.match(line.strip())
        if match is None:
            continue
        heading_text = normalize_heading_text(match.group(2).rstrip("#").strip())
        if heading_text == target_heading:
            section_start = index + 1
            section_level = len(match.group(1))
            break

    if section_start is None or section_level is None:
        return None

    section_end = len(lines)
    for index in range(section_start, len(lines)):
        match = MARKDOWN_HEADING_RE.match(lines[index].strip())
        if match is not None and len(match.group(1)) <= section_level:
            section_end = index
            break

    return "\n".join(lines[section_start:section_end])


def is_within_named_heading_section(
    text: str,
    char_offset: int,
    allowed_headings: set[str],
) -> bool:
    lines = text.splitlines(keepends=True)
    line_starts: list[int] = []
    current_offset = 0
    for line in lines:
        line_starts.append(current_offset)
        current_offset += len(line)

    for index, line in enumerate(lines):
        match = MARKDOWN_HEADING_RE.match(line.strip())
        if match is None:
            continue
        heading_text = normalize_heading_text(match.group(2).rstrip("#").strip())
        if heading_text not in allowed_headings:
            continue

        heading_level = len(match.group(1))
        section_start = line_starts[index] + len(line)
        section_end = len(text)
        for next_index in range(index + 1, len(lines)):
            next_match = MARKDOWN_HEADING_RE.match(lines[next_index].strip())
            if next_match is not None and len(next_match.group(1)) <= heading_level:
                section_end = line_starts[next_index]
                break
        if section_start <= char_offset < section_end:
            return True
    return False


def resolve_markdown_target(markdown_file: Path, repo_root: Path, target: str) -> Path:
    if target.startswith("/"):
        return (repo_root / target.lstrip("/")).resolve()
    return (markdown_file.parent / target).resolve()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def to_relative_posix(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def docs_status_by_path(repo_root: Path) -> dict[Path, str]:
    statuses: dict[Path, str] = {}
    for doc_path in iter_substantive_docs(repo_root):
        frontmatter = parse_frontmatter(doc_path.read_text(encoding="utf-8"))
        if frontmatter is None:
            continue
        status = frontmatter.get("status", "").strip()
        if status:
            statuses[doc_path.resolve()] = status
    return statuses


def check_markdown_links(repo_root: Path, report: CheckReport, scan_paths: list[str]) -> None:
    markdown_files = iter_markdown_files(repo_root, scan_paths)
    checked_links = 0
    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for target in iter_relative_markdown_targets(text):
            checked_links += 1
            resolved = resolve_markdown_target(markdown_file, repo_root, target)
            if not resolved.exists():
                relative_file = markdown_file.relative_to(repo_root)
                report.add_failure(f"broken markdown link: {relative_file} -> {target}")
    report.add_info(f"checked {checked_links} markdown relative links")


def file_links_to(repo_root: Path, markdown_file: Path, target_relative_path: str) -> bool:
    target_path = (repo_root / target_relative_path).resolve()
    text = markdown_file.read_text(encoding="utf-8")
    if target_relative_path in text or target_path.name in text:
        return True
    for target in iter_relative_markdown_targets(text):
        if resolve_markdown_target(markdown_file, repo_root, target) == target_path:
            return True
    return False


def check_required_entrypoints(repo_root: Path, report: CheckReport) -> None:
    for relative_path in REQUIRED_ENTRY_PATHS:
        if not (repo_root / relative_path).exists():
            report.add_failure(f"missing required entrypoint: {relative_path}")
    report.add_info(f"checked {len(REQUIRED_ENTRY_PATHS)} required entrypoints")


def check_required_backlinks(
    repo_root: Path,
    report: CheckReport,
    *,
    label: str,
    target_relative_path: str,
    backlink_paths: list[str],
) -> None:
    for relative_path in backlink_paths:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing {label} backlink consumer: {relative_path}")
            continue
        if not file_links_to(repo_root, path, target_relative_path):
            report.add_failure(
                f"missing {label} backlink: {relative_path} -> {target_relative_path}"
            )
    report.add_info(f"checked {len(backlink_paths)} {label} backlinks")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None

    frontmatter: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            return frontmatter
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return None


def iter_substantive_docs(repo_root: Path) -> list[Path]:
    docs_root = repo_root / "docs"
    return sorted(path for path in docs_root.rglob("*.md") if path.name != "README.md")


def iter_docs_reading_order_docs(repo_root: Path) -> list[Path]:
    docs_root = repo_root / "docs"
    book_path = (repo_root / DOCS_BOOK).resolve()
    return sorted(
        path
        for path in docs_root.rglob("*.md")
        if path.resolve() != book_path
    )


def docs_markdown_target_node(repo_root: Path, resolved_target: Path) -> Path | None:
    docs_root = (repo_root / "docs").resolve()
    if not is_relative_to(resolved_target, docs_root):
        return None

    if resolved_target.is_dir():
        readme = resolved_target / "README.md"
        if readme.exists():
            return readme.resolve()
        return None

    if resolved_target.suffix == ".md" and resolved_target.exists():
        return resolved_target.resolve()

    markdown_candidate = resolved_target.with_suffix(".md")
    if markdown_candidate.exists():
        return markdown_candidate.resolve()

    return None


def reachable_docs_from_book_spine(repo_root: Path) -> set[Path]:
    book_path = (repo_root / DOCS_BOOK).resolve()
    if not book_path.exists():
        return set()

    reachable: set[Path] = set()
    pending = [book_path]
    while pending:
        markdown_file = pending.pop()
        if markdown_file in reachable:
            continue
        reachable.add(markdown_file)

        text = markdown_file.read_text(encoding="utf-8")
        for target in iter_relative_markdown_targets(text):
            resolved = resolve_markdown_target(markdown_file, repo_root, target)
            next_node = docs_markdown_target_node(repo_root, resolved)
            if next_node is not None and next_node not in reachable:
                pending.append(next_node)

    return reachable


def docs_book_explicit_order_targets(repo_root: Path) -> set[Path]:
    book_path = (repo_root / DOCS_BOOK).resolve()
    if not book_path.exists():
        return set()

    explicit_targets: set[Path] = set()
    text = book_path.read_text(encoding="utf-8")
    full_reading_order = markdown_section_text(text, "Full Reading Order")
    if full_reading_order is None:
        return set()

    for target in iter_relative_markdown_targets(full_reading_order):
        resolved = resolve_markdown_target(book_path, repo_root, target)
        target_node = docs_markdown_target_node(repo_root, resolved)
        if target_node is not None and target_node != book_path:
            explicit_targets.add(target_node)
    return explicit_targets


def is_docs_book_inline_path_token(token: str) -> bool:
    if not token:
        return False
    if any(marker in token for marker in ("*", "?", "[", "]", "{", "}", "|", "\n")):
        return False
    if token.startswith(("#", "http://", "https://", "mailto:", "tel:")):
        return False
    if " " in token:
        return False
    return token.endswith("/") or "/" in token or token.endswith(".md")


def resolve_docs_book_inline_path(repo_root: Path, token: str) -> Path:
    cleaned = token.strip()
    if cleaned.startswith("/"):
        return repo_root / cleaned.lstrip("/")
    if cleaned.startswith(("../", "./")):
        return (repo_root / "docs" / cleaned).resolve()
    if cleaned.startswith(
        (
            ".",
            "docs/",
            "product/",
            "toolchain/",
            "tools/",
            "AGENTS.md",
            "INDEX.md",
            "README.md",
        )
    ):
        return repo_root / cleaned.rstrip("/")
    return repo_root / "docs" / cleaned.rstrip("/")


def check_docs_book_inline_paths(repo_root: Path, report: CheckReport) -> None:
    book_path = repo_root / DOCS_BOOK
    if not book_path.exists():
        report.add_info("checked 0 docs book inline path references")
        return

    checked_paths = 0
    text = book_path.read_text(encoding="utf-8")
    for match in INLINE_CODE_RE.findall(text):
        token = match.strip()
        if not is_docs_book_inline_path_token(token):
            continue
        checked_paths += 1
        resolved = resolve_docs_book_inline_path(repo_root, token)
        if not resolved.exists():
            report.add_failure(
                f"docs book references missing current path: {token}"
            )
    report.add_info(f"checked {checked_paths} docs book inline path references")


def check_superseded_doc_routes(repo_root: Path, report: CheckReport) -> None:
    statuses = docs_status_by_path(repo_root)
    superseded_docs = {
        path for path, status in statuses.items() if status == "superseded"
    }
    if not superseded_docs:
        report.add_info("checked 0 superseded docs route references")
        return

    docs_root = repo_root / "docs"
    route_docs = sorted(
        path
        for path in docs_root.rglob("*.md")
        if path.name == "README.md" or path == repo_root / DOCS_BOOK
    )
    checked_links = 0
    for route_doc in route_docs:
        text = route_doc.read_text(encoding="utf-8")
        for target, offset in iter_relative_markdown_target_matches(text):
            resolved = resolve_markdown_target(route_doc, repo_root, target)
            target_node = docs_markdown_target_node(repo_root, resolved)
            if target_node is None or target_node not in superseded_docs:
                continue
            checked_links += 1
            if not is_within_named_heading_section(
                text,
                offset,
                HISTORICAL_REFERENCE_HEADINGS,
            ):
                report.add_failure(
                    "superseded doc linked outside retained historical references: "
                    f"{to_relative_posix(route_doc, repo_root)} -> "
                    f"{to_relative_posix(target_node, repo_root)}"
                )

    report.add_info(f"checked {checked_links} superseded docs route references")


def canonical_skill_source_dirs(repo_root: Path) -> list[Path]:
    skills_root = repo_root / SKILL_SOURCE_ROOT
    if not skills_root.exists():
        return []
    return sorted(
        path.resolve()
        for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    )


def split_markdown_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or "|" not in stripped[1:]:
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def resolved_markdown_targets_in_table_column(
    repo_root: Path,
    markdown_file: Path,
    heading: str,
    column_index: int,
) -> set[Path]:
    text = markdown_file.read_text(encoding="utf-8")
    section = markdown_section_text(text, heading)
    if section is None:
        return set()

    targets: set[Path] = set()
    for line in section.splitlines():
        cells = split_markdown_table_row(line)
        if cells is None or column_index >= len(cells):
            continue
        for target in iter_relative_markdown_targets(cells[column_index]):
            targets.add(resolve_markdown_target(markdown_file, repo_root, target))
    return targets


def markdown_target_relative_to_repo(
    repo_root: Path,
    markdown_file: Path,
    target: str,
) -> str | None:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    try:
        base = markdown_file.parent.relative_to(repo_root).as_posix()
    except ValueError:
        return None
    return posixpath.normpath(posixpath.join(base, target))


def deploy_target_links_in_section(
    repo_root: Path,
    markdown_file: Path,
    heading: str,
) -> set[str]:
    text = markdown_file.read_text(encoding="utf-8")
    section = markdown_section_text(text, heading)
    if section is None:
        return set()

    deploy_targets: set[str] = set()
    for target in iter_relative_markdown_targets(section):
        relative = markdown_target_relative_to_repo(repo_root, markdown_file, target)
        if relative is None:
            continue
        normalized = relative.rstrip("/") + "/"
        if normalized.startswith(DEPLOY_TARGET_PREFIXES):
            deploy_targets.add(relative.rstrip("/"))
    return deploy_targets


def check_skill_source_traceability(repo_root: Path, report: CheckReport) -> None:
    skill_dirs = canonical_skill_source_dirs(repo_root)
    if not skill_dirs:
        report.add_info("checked 0 canonical skill source traceability entries")
        return

    source_readme = repo_root / SKILL_SOURCE_README
    catalog_readme = repo_root / SKILL_CATALOG_README
    if not source_readme.exists():
        report.add_failure(f"missing skill source README: {SKILL_SOURCE_README}")
        report.add_info(f"checked {len(skill_dirs)} canonical skill source traceability entries")
        return
    if not catalog_readme.exists():
        report.add_failure(f"missing skill catalog README: {SKILL_CATALOG_README}")
        report.add_info(f"checked {len(skill_dirs)} canonical skill source traceability entries")
        return

    source_owner_targets = resolved_markdown_targets_in_table_column(
        repo_root,
        source_readme,
        "Docs Owner Traceability",
        0,
    )
    catalog_source_targets = resolved_markdown_targets_in_table_column(
        repo_root,
        catalog_readme,
        "Canonical Source Traceability",
        1,
    )

    if not source_owner_targets:
        report.add_failure(
            f"missing Docs Owner Traceability section or links: {SKILL_SOURCE_README}"
        )
    if not catalog_source_targets:
        report.add_failure(
            f"missing Canonical Source Traceability section or links: {SKILL_CATALOG_README}"
        )

    deploy_targets = deploy_target_links_in_section(
        repo_root,
        source_readme,
        "Docs Owner Traceability",
    ) | deploy_target_links_in_section(
        repo_root,
        catalog_readme,
        "Canonical Source Traceability",
    )
    for target in sorted(deploy_targets):
        report.add_failure(
            "skill traceability points to deploy target instead of canonical source/docs: "
            f"{target}"
        )

    for skill_dir in skill_dirs:
        if skill_dir not in source_owner_targets:
            report.add_failure(
                "skill source missing docs owner traceability: "
                f"{to_relative_posix(skill_dir, repo_root)}"
            )
        if skill_dir not in catalog_source_targets:
            report.add_failure(
                "catalog traceability missing canonical skill source: "
                f"{to_relative_posix(skill_dir, repo_root)}"
            )

    report.add_info(f"checked {len(skill_dirs)} canonical skill source traceability entries")


def check_docs_book_reachability(repo_root: Path, report: CheckReport) -> None:
    book_path = repo_root / DOCS_BOOK
    docs_files = iter_substantive_docs(repo_root)
    explicit_order_files = iter_docs_reading_order_docs(repo_root)
    if not book_path.exists():
        report.add_failure(f"missing docs book spine: {DOCS_BOOK}")
        report.add_info(f"checked {len(docs_files)} docs book-spine reachability targets")
        report.add_info(
            f"checked {len(explicit_order_files)} docs explicit reading-order targets"
        )
        return

    book_text = book_path.read_text(encoding="utf-8")
    if markdown_section_text(book_text, "Full Reading Order") is None:
        report.add_failure(f"missing docs book Full Reading Order section: {DOCS_BOOK}")

    reachable = reachable_docs_from_book_spine(repo_root)
    for doc_path in docs_files:
        if doc_path.resolve() not in reachable:
            relative_path = to_relative_posix(doc_path, repo_root)
            report.add_failure(
                "docs doc not reachable from book spine: "
                f"{relative_path} (link it from {DOCS_BOOK} or the nearest chapter entrypoint)"
            )

    explicit_targets = docs_book_explicit_order_targets(repo_root)
    for doc_path in explicit_order_files:
        if doc_path.resolve() not in explicit_targets:
            relative_path = to_relative_posix(doc_path, repo_root)
            report.add_failure(
                "docs doc missing from explicit book reading order: "
                f"{relative_path} (add it as a direct ordered link in {DOCS_BOOK})"
            )

    report.add_info(f"checked {len(docs_files)} docs book-spine reachability targets")
    report.add_info(
        f"checked {len(explicit_order_files)} docs explicit reading-order targets"
    )


def expected_statuses(relative_path: str) -> set[str] | None:
    for prefix, statuses in STATUS_RULES:
        if relative_path.startswith(prefix):
            return statuses
    return None


def check_docs_frontmatter(repo_root: Path, report: CheckReport) -> None:
    docs_files = iter_substantive_docs(repo_root)
    for doc_path in docs_files:
        relative_path = to_relative_posix(doc_path, repo_root)
        text = doc_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)

        if frontmatter is None:
            report.add_failure(f"missing frontmatter: {relative_path}")
            continue

        missing_keys = [
            key for key in FRONTMATTER_REQUIRED_KEYS if not frontmatter.get(key, "").strip()
        ]
        if missing_keys:
            report.add_failure(
                f"missing frontmatter fields: {relative_path} -> {', '.join(missing_keys)}"
            )

        for date_key in ("updated", "last_verified"):
            value = frontmatter.get(date_key, "")
            if value and not DATE_RE.match(value):
                report.add_failure(
                    f"invalid {date_key} value: {relative_path} -> {value}"
                )

        expected = expected_statuses(relative_path)
        status = frontmatter.get("status", "")
        if expected is not None and status not in expected:
            allowed = ", ".join(sorted(expected))
            report.add_failure(
                f"unexpected status for {relative_path}: {status or '<missing>'} "
                f"(expected one of: {allowed})"
            )

    report.add_info(f"checked {len(docs_files)} docs substantive frontmatter blocks")


def check_required_entrypoint_links(repo_root: Path, report: CheckReport) -> None:
    for readme_path, target_paths in ENTRYPOINT_LINK_RULES.items():
        readme = repo_root / readme_path
        if not readme.exists():
            report.add_failure(f"missing entrypoint for link check: {readme_path}")
            continue
        for target_path in target_paths:
            if not file_links_to(repo_root, readme, target_path):
                report.add_failure(
                    f"entrypoint missing document link: {readme_path} -> {target_path}"
                )

    report.add_info(f"checked {len(ENTRYPOINT_LINK_RULES)} entrypoint link groups")


def check_gitignore(repo_root: Path, report: CheckReport) -> None:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        report.add_failure("missing .gitignore")
        return
    lines = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        if entry not in lines:
            report.add_failure(f"missing .gitignore entry: {entry}")
    report.add_info(f"checked {len(REQUIRED_GITIGNORE_ENTRIES)} .gitignore entries")


_INFO_TOTAL_RE = re.compile(r"checked (\d+)")


def _build_checks_payload(reports: dict[str, CheckReport]) -> dict:
    checks: dict[str, dict] = {}
    for cat, cat_report in reports.items():
        total = 0
        for info in cat_report.infos:
            m = _INFO_TOTAL_RE.match(info)
            if m:
                total += int(m.group(1))
        failed = len(cat_report.failures)
        checks[cat] = {
            "passed": total - failed,
            "failed": failed,
            "errors": cat_report.failures,
        }
    return checks


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()

    reports = {
        "relative_links": CheckReport(),
        "entrypoints": CheckReport(),
        "frontmatter": CheckReport(),
        "book_spine": CheckReport(),
    }

    scan_paths = DEFAULT_SCAN_PATHS + args.scan_path
    check_markdown_links(repo_root, reports["relative_links"], scan_paths)
    check_required_entrypoints(repo_root, reports["entrypoints"])
    check_required_backlinks(
        repo_root,
        reports["entrypoints"],
        label="agents-contract",
        target_relative_path=AGENTS_CONTRACT_DOC,
        backlink_paths=AGENTS_CONTRACT_BACKLINK_PATHS,
    )
    check_docs_frontmatter(repo_root, reports["frontmatter"])
    check_docs_book_reachability(repo_root, reports["book_spine"])
    check_docs_book_inline_paths(repo_root, reports["book_spine"])
    check_superseded_doc_routes(repo_root, reports["book_spine"])
    check_skill_source_traceability(repo_root, reports["book_spine"])
    check_required_entrypoint_links(repo_root, reports["entrypoints"])
    check_gitignore(repo_root, reports["entrypoints"])

    all_failures: list[str] = []
    all_infos: list[str] = []
    for cat_report in reports.values():
        all_failures.extend(cat_report.failures)
        all_infos.extend(cat_report.infos)

    checks = _build_checks_payload(reports)
    total_passed = sum(c["passed"] for c in checks.values())
    total_failed = sum(c["failed"] for c in checks.values())

    if args.json:
        payload = {
            "status": "pass" if not all_failures else "fail",
            "checks": checks,
            "summary": (
                f"{total_passed} passed, {total_failed} failed "
                f"across {len(checks)} categories"
            ),
        }
        print(json.dumps(payload, indent=2))
    else:
        for info in all_infos:
            print(f"info: {info}")
        if all_failures:
            print("governance checks failed:")
            for failure in all_failures:
                print(f"- {failure}")
        else:
            print("governance checks passed")
    return 0 if not all_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
