#!/usr/bin/env python3
"""Direct tests for Milestone Init repository/path/branch contracts."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

from toolchain.scripts.test.test_unified_milestone_init import (
    DisposableRepo,
    git,
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

import milestone_repository as repository  # noqa: E402


class MilestoneRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = DisposableRepo()

    def tearDown(self) -> None:
        self.repo.close()

    def validate_contract(self) -> repository.GitContract:
        return repository.validate_git_contract(
            self.repo.root,
            source_branch="develop-servo",
            baseline=self.repo.baseline,
            milestone_branch=self.repo.milestone_branch(),
            close_target="develop-servo",
            stable_refs=[],
        )

    def test_safe_root_directory_and_git_contract(self) -> None:
        root = repository.ensure_safe_repo_root(str(self.repo.root))
        milestone_dir = repository.ensure_safe_milestone_dir(root)
        self.assertEqual(
            milestone_dir,
            self.repo.root / ".servo" / "milestone",
        )
        contract = self.validate_contract()
        self.assertEqual(contract.source_branch, "develop-servo")
        self.assertEqual(contract.baseline, self.repo.baseline)

    def test_absent_branch_materializes_idempotently(self) -> None:
        contract = self.validate_contract()
        created = repository.resolve_branch_contract(
            self.repo.root,
            milestone_branch=self.repo.milestone_branch(),
            current_exists=False,
            contract_changed=False,
            baseline=contract.baseline,
            mutate=True,
        )
        self.assertEqual(created.outcome, "created")
        self.assertTrue(created.created)
        self.assertEqual(
            repository.read_branch_ref(
                self.repo.root,
                self.repo.milestone_branch(),
            ),
            self.repo.baseline,
        )
        replay = repository.resolve_branch_contract(
            self.repo.root,
            milestone_branch=self.repo.milestone_branch(),
            current_exists=False,
            contract_changed=False,
            baseline=contract.baseline,
            mutate=True,
        )
        self.assertEqual(replay.outcome, "existing_at_baseline")
        self.assertFalse(replay.created)

    def test_existing_descendant_reuses_and_wrong_ref_conflicts(self) -> None:
        contract = self.validate_contract()
        (self.repo.root / "descendant.txt").write_text(
            "descendant\n",
            encoding="utf-8",
        )
        git(self.repo.root, "add", "descendant.txt")
        git(self.repo.root, "commit", "-m", "descendant")
        descendant = git(self.repo.root, "rev-parse", "HEAD")
        git(
            self.repo.root,
            "branch",
            self.repo.milestone_branch(),
            descendant,
        )
        reused = repository.resolve_branch_contract(
            self.repo.root,
            milestone_branch=self.repo.milestone_branch(),
            current_exists=True,
            contract_changed=False,
            baseline=contract.baseline,
            mutate=False,
        )
        self.assertEqual(reused.outcome, "existing_descendant")

        with self.assertRaises(repository.RepositoryError) as raised:
            repository.resolve_branch_contract(
                self.repo.root,
                milestone_branch=self.repo.milestone_branch(),
                current_exists=False,
                contract_changed=False,
                baseline=contract.baseline,
                mutate=False,
            )
        self.assertEqual(raised.exception.code, "branch_ref_conflict")

    def test_stable_refs_are_bounded_regular_repo_paths(self) -> None:
        handback = (
            self.repo.root
            / ".servo"
            / "worktrack"
            / "WT-A"
            / "finished-handback.yaml"
        )
        handback.parent.mkdir(parents=True)
        handback.write_text("worktrack_id: WT-A\n", encoding="utf-8")
        contract = repository.validate_git_contract(
            self.repo.root,
            source_branch="develop-servo",
            baseline=self.repo.baseline,
            milestone_branch=self.repo.milestone_branch(),
            close_target="develop-servo",
            stable_refs=[
                ".servo/worktrack/WT-A/finished-handback.yaml"
            ],
        )
        self.assertEqual(contract.baseline, self.repo.baseline)
        handback.write_bytes(
            b"x" * (repository.MAX_STABLE_REF_BYTES + 1)
        )
        with self.assertRaises(repository.RepositoryError) as raised:
            repository.validate_git_contract(
                self.repo.root,
                source_branch="develop-servo",
                baseline=self.repo.baseline,
                milestone_branch=self.repo.milestone_branch(),
                close_target="develop-servo",
                stable_refs=[
                    ".servo/worktrack/WT-A/"
                    "finished-handback.yaml"
                ],
            )
        self.assertEqual(
            raised.exception.code,
            "document_too_large",
        )

    def test_repository_has_no_domain_or_persistence_dependency(self) -> None:
        source = Path(repository.__file__).read_text(encoding="utf-8")
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
                "milestone_exact_persistence",
                "milestone_document_transaction",
                "tempfile",
            }.isdisjoint(imported)
        )
        for forbidden in (
            "parse_document",
            "parse_worktrack",
            "os.replace",
            "mkstemp",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
