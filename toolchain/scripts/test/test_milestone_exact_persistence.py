#!/usr/bin/env python3
"""Direct tests for Milestone Init exact-byte persistence."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path


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

import milestone_exact_persistence as persistence  # noqa: E402


class MilestoneExactPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "MS-TEST-001.md"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_and_replace_preserve_exact_bytes(self) -> None:
        first = b"first exact bytes\r\nwithout terminal LF"
        created = persistence.persist_exact_bytes(
            self.target,
            first,
            None,
        )
        self.assertTrue(created.replaced)
        self.assertTrue(created.exact_readback)
        self.assertEqual(
            persistence.safe_read_regular(
                self.target,
                missing_ok=False,
            ),
            first,
        )

        second = b"second exact bytes\n"
        revised = persistence.persist_exact_bytes(
            self.target,
            second,
            first,
        )
        self.assertTrue(revised.replaced)
        self.assertEqual(self.target.read_bytes(), second)

    def test_failure_before_replace_preserves_old_and_cleans_temp(self) -> None:
        old = b"old\n"
        new = b"new\n"
        self.target.write_bytes(old)
        with self.assertRaises(
            persistence.PersistenceError
        ) as raised:
            persistence.persist_exact_bytes(
                self.target,
                new,
                old,
                failure_point="before-replace",
            )
        self.assertEqual(raised.exception.code, "injected_failure")
        self.assertEqual(
            raised.exception.details["commit_point"],
            "before_replace",
        )
        self.assertFalse(
            raised.exception.details["roll_forward_required"]
        )
        self.assertFalse(
            raised.exception.details["document_written"]
        )
        self.assertEqual(self.target.read_bytes(), old)
        self.assertEqual(
            list(self.root.glob(".MS-TEST-001.*.tmp")),
            [],
        )

    def test_failure_after_replace_rolls_forward(self) -> None:
        old = b"old\n"
        new = b"new\n"
        self.target.write_bytes(old)
        with self.assertRaises(
            persistence.PersistenceError
        ) as raised:
            persistence.persist_exact_bytes(
                self.target,
                new,
                old,
                failure_point="after-replace",
            )
        self.assertEqual(raised.exception.code, "injected_failure")
        self.assertEqual(
            raised.exception.details["commit_point"],
            "after_replace",
        )
        self.assertTrue(
            raised.exception.details["roll_forward_required"]
        )
        self.assertTrue(
            raised.exception.details["document_written"]
        )
        self.assertEqual(self.target.read_bytes(), new)

    def test_final_reread_rejects_stale_expected_state(self) -> None:
        self.target.write_bytes(b"current\n")
        with self.assertRaises(
            persistence.PersistenceError
        ) as raised:
            persistence.persist_exact_bytes(
                self.target,
                b"candidate\n",
                b"stale\n",
            )
        self.assertEqual(
            raised.exception.code,
            "stale_compare_and_swap",
        )
        self.assertEqual(self.target.read_bytes(), b"current\n")

    def test_persistence_has_no_domain_or_git_dependency(self) -> None:
        source = Path(persistence.__file__).read_text(
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
                "milestone_document_check",
                "milestone_repository",
                "milestone_document_transaction",
                "subprocess",
            }.isdisjoint(imported)
        )
        for forbidden in (
            "parse_document",
            "acceptance",
            "covers",
            "update-ref",
            "git ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
