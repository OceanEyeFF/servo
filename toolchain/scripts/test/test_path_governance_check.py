from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from path_governance_check import (
    CheckReport,
    check_docs_book_inline_paths,
    check_docs_book_reachability,
    check_superseded_doc_routes,
    check_skill_source_traceability,
    check_gitignore,
    check_required_backlinks,
    check_required_entrypoint_links,
    check_required_entrypoints,
)


def write_gitignore(repo_root: Path, lines: list[str]) -> None:
    (repo_root / ".gitignore").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_docs_book_is_required_and_linked_from_entrypoints(tmp_path: Path) -> None:
    write_file(tmp_path / "AGENTS.md", "[docs](./docs/README.md)\n")
    write_file(tmp_path / "README.md", "[docs](./docs/README.md)\n")
    write_file(
        tmp_path / "INDEX.md",
        "[docs](./docs/README.md)\n[book](./docs/book.md)\n",
    )
    write_file(
        tmp_path / "docs/README.md",
        "[book](./book.md)\n[project](./project-maintenance/README.md)\n[harness](./harness/README.md)\n",
    )
    write_file(tmp_path / "docs/book.md", "[AGENTS](../AGENTS.md)\n")
    write_file(tmp_path / "docs/project-maintenance/README.md", "# project\n")
    write_file(tmp_path / "docs/harness/README.md", "# harness\n")

    entry_report = CheckReport()
    check_required_entrypoints(tmp_path, entry_report)
    check_required_entrypoint_links(tmp_path, entry_report)

    backlink_report = CheckReport()
    check_required_backlinks(
        tmp_path,
        backlink_report,
        label="agents-contract",
        target_relative_path="AGENTS.md",
        backlink_paths=["docs/book.md"],
    )

    assert all("docs/book.md" not in failure for failure in entry_report.failures)
    assert backlink_report.failures == []


def test_docs_book_missing_link_is_flagged(tmp_path: Path) -> None:
    write_file(tmp_path / "INDEX.md", "[docs](./docs/README.md)\n")
    write_file(
        tmp_path / "docs/README.md",
        "[project](./project-maintenance/README.md)\n[harness](./harness/README.md)\n",
    )
    write_file(tmp_path / "docs/project-maintenance/README.md", "# project\n")
    write_file(tmp_path / "docs/harness/README.md", "# harness\n")

    report = CheckReport()
    check_required_entrypoint_links(tmp_path, report)

    assert "entrypoint missing document link: INDEX.md -> docs/book.md" in report.failures
    assert "entrypoint missing document link: docs/README.md -> docs/book.md" in report.failures


def test_docs_book_reachability_accepts_docs_linked_from_chapter_entrypoint(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

## Full Reading Order

[Project](./project-maintenance/README.md)
[Governance](./project-maintenance/governance/README.md)
[Policy](./project-maintenance/governance/policy.md)
""",
    )
    write_file(
        tmp_path / "docs/project-maintenance/README.md",
        "[Governance](./governance/README.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/README.md",
        "[Policy](./policy.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/policy.md",
        """---
title: Policy
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Policy
""",
    )

    report = CheckReport()
    check_docs_book_reachability(tmp_path, report)

    assert report.failures == []


def test_docs_book_reachability_resolves_directory_anchor_and_extensionless_links(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

## Full Reading Order

[Project](./project-maintenance/#entry)
[Governance](./project-maintenance/governance/)
[Policy](./project-maintenance/governance/policy#scope)
""",
    )
    write_file(
        tmp_path / "docs/project-maintenance/README.md",
        "[Governance](./governance/)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/README.md",
        "[Policy](./policy#scope)\n[External](https://example.com)\n[Local anchor](#local)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/policy.md",
        """---
title: Policy
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Policy
""",
    )

    report = CheckReport()
    check_docs_book_reachability(tmp_path, report)

    assert report.failures == []


def test_docs_book_explicit_order_flags_doc_only_reached_indirectly(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

## Full Reading Order

[Project](./project-maintenance/README.md)
""",
    )
    write_file(
        tmp_path / "docs/project-maintenance/README.md",
        "[Governance](./governance/README.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/README.md",
        "[Policy](./policy.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/policy.md",
        """---
title: Policy
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Policy
""",
    )

    report = CheckReport()
    check_docs_book_reachability(tmp_path, report)

    assert (
        "docs doc missing from explicit book reading order: "
        "docs/project-maintenance/governance/policy.md "
        "(add it as a direct ordered link in docs/book.md)"
    ) in report.failures


def test_docs_book_explicit_order_ignores_links_outside_full_reading_order(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

## Full Reading Order

[Project](./project-maintenance/README.md)
[Governance](./project-maintenance/governance/README.md)

## Placement Checklist

[Policy](./project-maintenance/governance/policy.md)
""",
    )
    write_file(
        tmp_path / "docs/project-maintenance/README.md",
        "[Governance](./governance/README.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/README.md",
        "[Policy](./policy.md)\n",
    )
    write_file(
        tmp_path / "docs/project-maintenance/governance/policy.md",
        """---
title: Policy
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Policy
""",
    )

    report = CheckReport()
    check_docs_book_reachability(tmp_path, report)

    assert (
        "docs doc missing from explicit book reading order: "
        "docs/project-maintenance/governance/policy.md "
        "(add it as a direct ordered link in docs/book.md)"
    ) in report.failures


def test_docs_book_reachability_flags_unreachable_substantive_doc(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

## Full Reading Order

[Project](./project-maintenance/README.md)
""",
    )
    write_file(tmp_path / "docs/project-maintenance/README.md", "# Project\n")
    write_file(
        tmp_path / "docs/project-maintenance/governance/orphan.md",
        """---
title: Orphan
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Orphan
""",
    )

    report = CheckReport()
    check_docs_book_reachability(tmp_path, report)

    assert (
        "docs doc not reachable from book spine: "
        "docs/project-maintenance/governance/orphan.md "
        "(link it from docs/book.md or the nearest chapter entrypoint)"
    ) in report.failures
    assert (
        "docs doc missing from explicit book reading order: "
        "docs/project-maintenance/governance/orphan.md "
        "(add it as a direct ordered link in docs/book.md)"
    ) in report.failures


def test_docs_book_inline_paths_flags_missing_current_path(tmp_path: Path) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

`docs/missing/` should not be listed as current.
""",
    )

    report = CheckReport()
    check_docs_book_inline_paths(tmp_path, report)

    assert "docs book references missing current path: docs/missing/" in report.failures


def test_docs_book_inline_paths_accepts_current_root_and_docs_paths(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "AGENTS.md", "# Agents\n")
    write_file(tmp_path / "docs/README.md", "# Docs\n")
    write_file(tmp_path / "docs/project-maintenance/README.md", "# Project\n")
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-14
owner: test
last_verified: 2026-05-14
---
# Docs Book

`AGENTS.md`, `docs/README.md`, and `project-maintenance/` exist.
`docs/**/*.md` is a glob pattern, not a concrete path reference.
""",
    )

    report = CheckReport()
    check_docs_book_inline_paths(tmp_path, report)

    assert report.failures == []


def test_superseded_doc_routes_accept_retained_historical_section(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-16
owner: test
last_verified: 2026-05-16
---
# Docs Book

## Full Reading Order

[Current](./harness/current.md)

## Retained Historical References

[Old](./harness/old.md)
""",
    )
    write_file(
        tmp_path / "docs/harness/README.md",
        """# Harness

## Retained Historical References

[Old](./old.md)
""",
    )
    write_file(
        tmp_path / "docs/harness/current.md",
        """---
title: Current
status: active
updated: 2026-05-16
owner: test
last_verified: 2026-05-16
---
# Current
""",
    )
    write_file(
        tmp_path / "docs/harness/old.md",
        """---
title: Old
status: superseded
updated: 2026-05-16
owner: test
last_verified: 2026-05-16
---
# Old
""",
    )

    report = CheckReport()
    check_superseded_doc_routes(tmp_path, report)

    assert report.failures == []


def test_superseded_doc_routes_flag_current_route_link(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path / "docs/book.md",
        """---
title: Docs Book
status: active
updated: 2026-05-16
owner: test
last_verified: 2026-05-16
---
# Docs Book

## Full Reading Order

[Old](./harness/old.md)
""",
    )
    write_file(
        tmp_path / "docs/harness/README.md",
        """# Harness

[Old](./old.md)
""",
    )
    write_file(
        tmp_path / "docs/harness/old.md",
        """---
title: Old
status: superseded
updated: 2026-05-16
owner: test
last_verified: 2026-05-16
---
# Old
""",
    )

    report = CheckReport()
    check_superseded_doc_routes(tmp_path, report)

    assert (
        "superseded doc linked outside retained historical references: "
        "docs/book.md -> docs/harness/old.md"
    ) in report.failures
    assert (
        "superseded doc linked outside retained historical references: "
        "docs/harness/README.md -> docs/harness/old.md"
    ) in report.failures


def test_skill_source_traceability_accepts_bidirectional_mapping(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "product/harness/skills/alpha-skill/SKILL.md", "# Alpha\n")
    write_file(tmp_path / "product/harness/skills/beta-skill/SKILL.md", "# Beta\n")
    write_file(
        tmp_path / "product/harness/skills/README.md",
        """# Skills

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [alpha-skill/](./alpha-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
| [beta-skill/](./beta-skill/) | [docs/harness/catalog/worktrack.md](../../../docs/harness/catalog/worktrack.md) |
""",
    )
    write_file(
        tmp_path / "docs/harness/catalog/README.md",
        """# Catalog

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
| [repo.md](./repo.md) | [alpha-skill](../../../product/harness/skills/alpha-skill/) |
| [worktrack.md](./worktrack.md) | [beta-skill](../../../product/harness/skills/beta-skill/) |
""",
    )
    write_file(tmp_path / "docs/harness/catalog/repo.md", "# Repo\n")
    write_file(tmp_path / "docs/harness/catalog/worktrack.md", "# Worktrack\n")

    report = CheckReport()
    check_skill_source_traceability(tmp_path, report)

    assert report.failures == []


def test_skill_source_traceability_flags_missing_source_backlink(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "product/harness/skills/alpha-skill/SKILL.md", "# Alpha\n")
    write_file(tmp_path / "product/harness/skills/beta-skill/SKILL.md", "# Beta\n")
    write_file(
        tmp_path / "product/harness/skills/README.md",
        """# Skills

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [alpha-skill/](./alpha-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
""",
    )
    write_file(
        tmp_path / "docs/harness/catalog/README.md",
        """# Catalog

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
| [repo.md](./repo.md) | [alpha-skill](../../../product/harness/skills/alpha-skill/) |
| [worktrack.md](./worktrack.md) | [beta-skill](../../../product/harness/skills/beta-skill/) |
""",
    )
    write_file(tmp_path / "docs/harness/catalog/repo.md", "# Repo\n")
    write_file(tmp_path / "docs/harness/catalog/worktrack.md", "# Worktrack\n")

    report = CheckReport()
    check_skill_source_traceability(tmp_path, report)

    assert (
        "skill source missing docs owner traceability: "
        "product/harness/skills/beta-skill"
    ) in report.failures


def test_skill_source_traceability_flags_missing_catalog_mapping(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "product/harness/skills/alpha-skill/SKILL.md", "# Alpha\n")
    write_file(
        tmp_path / "product/harness/skills/README.md",
        """# Skills

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [alpha-skill/](./alpha-skill/) | [docs/harness/catalog/repo.md](../../../docs/harness/catalog/repo.md) |
""",
    )
    write_file(
        tmp_path / "docs/harness/catalog/README.md",
        """# Catalog

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
""",
    )
    write_file(tmp_path / "docs/harness/catalog/repo.md", "# Repo\n")

    report = CheckReport()
    check_skill_source_traceability(tmp_path, report)

    assert (
        "catalog traceability missing canonical skill source: "
        "product/harness/skills/alpha-skill"
    ) in report.failures


def test_skill_source_traceability_rejects_skill_links_in_wrong_columns(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "product/harness/skills/alpha-skill/SKILL.md", "# Alpha\n")
    write_file(
        tmp_path / "product/harness/skills/README.md",
        """# Skills

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [docs owner](../../../docs/harness/catalog/repo.md) | [alpha-skill/](./alpha-skill/) |
""",
    )
    write_file(
        tmp_path / "docs/harness/catalog/README.md",
        """# Catalog

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
| [alpha-skill](../../../product/harness/skills/alpha-skill/) | [repo.md](./repo.md) |
""",
    )
    write_file(tmp_path / "docs/harness/catalog/repo.md", "# Repo\n")

    report = CheckReport()
    check_skill_source_traceability(tmp_path, report)

    assert (
        "skill source missing docs owner traceability: "
        "product/harness/skills/alpha-skill"
    ) in report.failures
    assert (
        "catalog traceability missing canonical skill source: "
        "product/harness/skills/alpha-skill"
    ) in report.failures


def test_skill_source_traceability_flags_deploy_target_links(
    tmp_path: Path,
) -> None:
    write_file(tmp_path / "product/harness/skills/alpha-skill/SKILL.md", "# Alpha\n")
    write_file(
        tmp_path / "product/harness/skills/README.md",
        """# Skills

## Docs Owner Traceability

| Canonical source | Docs/catalog owner |
|------------------|--------------------|
| [alpha-skill/](./alpha-skill/) | [deploy copy](../../../.claude/skills/alpha-skill/) |
""",
    )
    write_file(
        tmp_path / "docs/harness/catalog/README.md",
        """# Catalog

## Canonical Source Traceability

| Catalog surface | Canonical executable source |
|-----------------|-----------------------------|
| [deploy copy](../../../.agents/skills/alpha-skill/) | [alpha-skill](../../../product/harness/skills/alpha-skill/) |
""",
    )

    report = CheckReport()
    check_skill_source_traceability(tmp_path, report)

    assert (
        "skill traceability points to deploy target instead of canonical source/docs: "
        ".agents/skills/alpha-skill"
    ) in report.failures
    assert (
        "skill traceability points to deploy target instead of canonical source/docs: "
        ".claude/skills/alpha-skill"
    ) in report.failures


def test_check_gitignore_accepts_required_cache_entries(tmp_path: Path) -> None:
    write_gitignore(
        tmp_path,
        [
            ".servo/",
            ".agents/",
            ".claude/",
            ".autoworkflow/",
            ".spec-workflow/",
            ".logs/",
            "**/__pycache__/",
            ".pytest_cache/",
            "*.pyc",
            "*.pyo",
        ],
    )

    report = CheckReport()
    check_gitignore(tmp_path, report)

    assert report.failures == []


def test_check_gitignore_flags_missing_cache_entry(tmp_path: Path) -> None:
    write_gitignore(
        tmp_path,
        [
            ".servo/",
            ".agents/",
            ".claude/",
            ".autoworkflow/",
            ".spec-workflow/",
            ".logs/",
            "**/__pycache__/",
            "*.pyc",
            "*.pyo",
        ],
    )

    report = CheckReport()
    check_gitignore(tmp_path, report)

    assert "missing .gitignore entry: .pytest_cache/" in report.failures
