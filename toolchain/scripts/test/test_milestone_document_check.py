#!/usr/bin/env python3
"""Direct tests for the pure Milestone document/domain checker."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

from toolchain.scripts.test.test_unified_milestone_init import (
    amendment_block,
    milestone_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "milestone-init-skill"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS_DIR))

import milestone_document_check as document_check  # noqa: E402


class MilestoneDocumentCheckTests(unittest.TestCase):
    def assert_check_error(
        self,
        raw: bytes,
        expected_code: str,
        *,
        mode: str = "create",
    ) -> None:
        with self.assertRaises(
            document_check.DocumentCheckError
        ) as raised:
            document_check.parse_document(raw, mode)
        self.assertEqual(raised.exception.code, expected_code)

    def test_flexible_serialization_preserves_exact_opaque_bytes(self) -> None:
        raw = milestone_bytes(
            "a" * 40,
            field_order_variant=True,
            section_order_variant=True,
            preamble="Operator-facing preamble remains ordinary prose.",
            tasklist_commentary=(
                "This explanation follows the structured Worktrack entry."
            ),
            extra_section=(
                "An extra ordinary-prose section has no control authority."
            ),
            newline="\r\n",
            terminal_newline=False,
        )
        parsed = document_check.parse_document(raw, "create")
        self.assertEqual(parsed.raw, raw)
        self.assertEqual(parsed.milestone_id, "MS-TEST-001")
        self.assertEqual(parsed.revision, 1)
        self.assertEqual(parsed.criteria, ("MS-TEST-AC-01",))
        self.assertEqual(list(parsed.entries), ["WT-A"])
        self.assertEqual(
            parsed.digest,
            document_check.sha256_digest(raw),
        )

    def test_domain_graph_and_coverage_fail_closed(self) -> None:
        invalid_cover = milestone_bytes(
            "a" * 40,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "A",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "UNKNOWN",
                    "result_ref": "null",
                }
            ],
        )
        self.assert_check_error(
            invalid_cover,
            "invalid_worktrack_coverage",
        )
        cycle = milestone_bytes(
            "a" * 40,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "A",
                    "condition": "required",
                    "depends_on": "WT-B",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                },
                {
                    "worktrack_id": "WT-B",
                    "checked": False,
                    "outcome": "B",
                    "condition": "required",
                    "depends_on": "WT-A",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                },
            ],
        )
        self.assert_check_error(
            cycle,
            "cyclic_worktrack_dependency",
        )

    def test_init_authority_preserves_result_and_approved_history(self) -> None:
        revision1 = document_check.parse_document(
            milestone_bytes("a" * 40),
            "existing",
        )
        revision2_raw = milestone_bytes(
            "a" * 40,
            revision=2,
            amendments=[
                amendment_block(2, approval_ref="approval-r2")
            ],
        )
        revision2 = document_check.parse_document(
            revision2_raw,
            "amend",
        )
        document_check.enforce_init_authority(
            revision2,
            revision1,
            "approval-r2",
        )

        accepted_result = milestone_bytes(
            "a" * 40,
            revision=2,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": True,
                    "outcome": "Deliver the test contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": (
                        ".servo/worktrack/WT-A/"
                        "finished-handback.yaml"
                    ),
                }
            ],
            amendments=[
                amendment_block(2, approval_ref="approval-r2")
            ],
        )
        candidate = document_check.parse_document(
            accepted_result,
            "amend",
        )
        with self.assertRaises(
            document_check.DocumentCheckError
        ) as raised:
            document_check.enforce_init_authority(
                candidate,
                revision1,
                "approval-r2",
            )
        self.assertEqual(
            raised.exception.code,
            "result_authority_violation",
        )

        altered_history = document_check.parse_document(
            milestone_bytes(
                "a" * 40,
                revision=3,
                amendments=[
                    amendment_block(
                        2,
                        approval_ref="approval-r2",
                        extra_prose="Rewritten approved commentary.",
                    ),
                    amendment_block(3, approval_ref="approval-r3"),
                ],
            ),
            "amend",
        )
        with self.assertRaises(
            document_check.DocumentCheckError
        ) as history_error:
            document_check.enforce_init_authority(
                altered_history,
                revision2,
                "approval-r3",
            )
        self.assertEqual(
            history_error.exception.code,
            "amendment_history_change",
        )

    def test_undeclared_worktrack_entry_fields_fail_closed(self) -> None:
        for marker, field_name in (("-", "branch"), ("*", "branch"), ("+", "phase")):
            raw = milestone_bytes("a" * 40).replace(
                b"- result_ref: `null`\n",
                (
                    f"- result_ref: `null`\n"
                    f"{marker} {field_name}: forbidden\n"
                ).encode(),
            )
            with self.assertRaises(
                document_check.DocumentCheckError
            ) as raised:
                document_check.parse_document(raw, "create")
            error = raised.exception
            self.assertEqual(
                error.code,
                "undeclared_worktrack_entry_field",
            )
            self.assertEqual(error.details["field"], field_name)
            self.assertEqual(
                error.details["context"],
                "Worktrack WT-A",
            )
            self.assertEqual(error.details["line"], 9)

    def test_opaque_entry_prose_and_non_machine_shapes_stay_accepted(self) -> None:
        raw = milestone_bytes(
            "a" * 40,
            tasklist_commentary=(
                "branch: illustrative-only\n"
                "- `current_phase: example`\n"
                "* Branch: example\n"
                "+ current-phase: example\n"
            ),
        )
        parsed = document_check.parse_document(raw, "create")
        self.assertEqual(list(parsed.entries), ["WT-A"])
        self.assertEqual(parsed.raw, raw)

    def test_fenced_undeclared_bullets_stay_opaque(self) -> None:
        raw = milestone_bytes("a" * 40).replace(
            b"- result_ref: `null`\n",
            (
                b"- result_ref: `null`\n\n"
                b"```markdown\n"
                b"- branch: fenced-dash\n"
                b"* branch: fenced-star\n"
                b"+ branch: fenced-plus\n"
                b"```\n"
            ),
        )
        parsed = document_check.parse_document(raw, "create")
        self.assertEqual(list(parsed.entries), ["WT-A"])
        self.assertEqual(parsed.raw, raw)

    def test_checker_has_no_repository_or_persistence_dependency(self) -> None:
        source = Path(document_check.__file__).read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertTrue(
            {
                "milestone_repository",
                "milestone_exact_persistence",
                "milestone_document_transaction",
                "os",
                "subprocess",
                "tempfile",
            }.isdisjoint(imported)
        )
        for forbidden in (
            "os.replace",
            "os.fsync",
            "update-ref",
            "subprocess.run",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
