#!/usr/bin/env python3
"""Integrated tests for the single Milestone Init capability."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "product" / "harness" / "skills" / "milestone-init-skill"
SKILL = PACKAGE_DIR / "SKILL.md"
TEMPLATE = PACKAGE_DIR / "templates" / "milestone.template.md"
WORKER = PACKAGE_DIR / "scripts" / "milestone_document_transaction.py"
CHECKER = PACKAGE_DIR / "scripts" / "milestone_document_check.py"
REPOSITORY = PACKAGE_DIR / "scripts" / "milestone_repository.py"
PERSISTENCE = PACKAGE_DIR / "scripts" / "milestone_exact_persistence.py"


def run(
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            **(env or {}),
        },
    )


def git(repo: Path, *arguments: str) -> str:
    completed = run(["git", *arguments], cwd=repo)
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(arguments)} failed:\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout.strip()


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def amendment_block(
    revision: int,
    *,
    approval_ref: str,
    affected: str = "WT-A",
    extra_prose: str = "",
) -> str:
    suffix = f"\n{extra_prose.rstrip()}\n" if extra_prose else "\n"
    return (
        f"### Revision {revision} Amendment\n\n"
        f"- revision: `{revision}`\n"
        f"- changed: `Revision {revision} approved change`\n"
        f"- reason: `Exercise deterministic amendment handling`\n"
        f"- affected_worktracks: `{affected}`\n"
        f"- evidence_still_valid: `Earlier accepted evidence remains valid`\n"
        f"- evidence_requires_revalidation: `Changed behavior requires validation`\n"
        f"- approval_ref: `{approval_ref}`\n"
        f"{suffix}"
    )


def milestone_bytes(
    baseline: str,
    *,
    milestone_id: str = "MS-TEST-001",
    revision: int = 1,
    goal: str = "Deliver one observable test outcome.",
    entries: list[dict[str, Any]] | None = None,
    criteria: list[str] | None = None,
    amendments: list[str] | None = None,
    gate_ref: str = "null",
    final_ref: str = "null",
    field_order_variant: bool = False,
    section_order_variant: bool = False,
    preamble: str = "",
    tasklist_commentary: str = "",
    extra_section: str = "",
    newline: str = "\n",
    terminal_newline: bool = True,
) -> bytes:
    entries = entries or [
        {
            "worktrack_id": "WT-A",
            "checked": False,
            "outcome": "Deliver the test contribution.",
            "condition": "required",
            "depends_on": "[]",
            "covers": "MS-TEST-AC-01",
            "result_ref": "null",
        }
    ]
    criteria = criteria or ["MS-TEST-AC-01"]
    title = f"{milestone_id}: exact-byte test"
    fields = [
        ("title", f'"{title}"'),
        ("artifact_type", '"milestone"'),
        ("milestone_id", f'"{milestone_id}"'),
        ("revision", str(revision)),
        ("maturity", '"planned"'),
        ("disposition", '"open"'),
        ("updated", '"2026-07-23T00:00:00+00:00"'),
        ("owner", '"test-owner"'),
        ("milestone_kind", '"goal-driven"'),
        ("milestone_branch", f'"ms/{milestone_id}-exact-byte-test"'),
        ("baseline_ref", f'"develop-servo@{baseline}"'),
        ("close_target", '"develop-servo"'),
    ]
    if field_order_variant:
        fields = [
            fields[index]
            for index in (2, 0, 1, 9, 4, 3, 10, 6, 8, 11, 5, 7)
        ]
    frontmatter = ["---", *(f"{key}: {value}" for key, value in fields), "---"]

    task_lines: list[str] = []
    for entry in entries:
        marker = "x" if entry.get("checked") else " "
        worktrack_id = str(entry["worktrack_id"])
        task_lines.extend(
            [
                f"### [{marker}] {worktrack_id}",
                "",
                f"- worktrack_id: `{worktrack_id}`",
                f"- outcome: {entry['outcome']}",
            ]
        )
        if "depends_on" in entry:
            task_lines.append(f"- depends_on: `{entry['depends_on']}`")
        if "execution_condition" in entry:
            task_lines.append(
                f"- execution_condition: {entry['execution_condition']}"
            )
        task_lines.extend(
            [
                f"- condition: `{entry['condition']}`",
                f"- covers: `{entry['covers']}`",
                f"- result_ref: `{entry['result_ref']}`",
                "",
            ]
        )
    if tasklist_commentary:
        task_lines.extend([tasklist_commentary, ""])

    criterion_lines: list[str] = []
    for criterion_id in criteria:
        criterion_lines.extend(
            [
                f"### {criterion_id} — Observable result",
                "",
                f"{criterion_id} must be independently adjudicable.",
                "",
            ]
        )

    amendment_text = (
        "".join(amendments or [])
        if revision > 1
        else "No amendments.\n"
    )
    sections = {
        "Goal": f"{goal}\n",
        "Scope": "- The exact bounded behavior under test.\n",
        "Non-Goals": "- Harness currentness and Worktrack execution.\n",
        "Cross-Worktrack Design Decisions": (
            "- Ordinary prose remains opaque; control fields remain authoritative.\n"
        ),
        "Worktrack Tasklist": "\n".join(task_lines).rstrip() + "\n",
        "Milestone-Level Acceptance Criteria": (
            "\n".join(criterion_lines).rstrip() + "\n"
        ),
        "Amendments": amendment_text,
        "Finalization References": (
            f"- milestone_gate_ref: `{gate_ref}`\n"
            f"- final_acceptance_ref: `{final_ref}`\n"
        ),
    }
    section_names = list(sections)
    if section_order_variant:
        section_names = [
            "Scope",
            "Goal",
            "Milestone-Level Acceptance Criteria",
            "Non-Goals",
            "Worktrack Tasklist",
            "Cross-Worktrack Design Decisions",
            "Finalization References",
            "Amendments",
        ]
    body = [f"# {title}"]
    if preamble:
        body.extend(["", preamble])
    for name in section_names:
        body.extend(["", f"## {name}", "", sections[name].rstrip()])
    if extra_section:
        body.extend(["", "## Operator Commentary", "", extra_section])
    text = "\n".join([*frontmatter, *body])
    if terminal_newline:
        text += "\n"
    if newline != "\n":
        text = text.replace("\n", newline)
    return text.encode("utf-8")


class DisposableRepo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        git(self.root, "init", "-b", "develop-servo")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Milestone Init Test")
        (self.root / "README.md").write_text("baseline\n", encoding="utf-8")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "baseline")
        self.baseline = git(self.root, "rev-parse", "HEAD")
        git(self.root, "switch", "-c", "operator-work")
        (self.root / ".servo" / "milestone").mkdir(parents=True)

    def close(self) -> None:
        self.temp.cleanup()

    def candidate_path(self, raw: bytes, name: str = "candidate.md") -> Path:
        path = self.root / name
        path.write_bytes(raw)
        return path

    def target(self, milestone_id: str = "MS-TEST-001") -> Path:
        return self.root / ".servo" / "milestone" / f"{milestone_id}.md"

    def milestone_branch(self, milestone_id: str = "MS-TEST-001") -> str:
        return f"ms/{milestone_id}-exact-byte-test"


def worker_call(
    repo: DisposableRepo,
    command: str,
    raw: bytes,
    *,
    mode: str,
    approval_ref: str = "approval-test",
    approved_digest: str | None = None,
    expected_revision: int = 0,
    expected_digest: str = "absent",
    failure_point: str | None = None,
    name: str = "candidate.md",
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    candidate = repo.candidate_path(raw, name)
    arguments = [
        sys.executable,
        str(WORKER),
        command,
        "--mode",
        mode,
        "--candidate",
        str(candidate),
        "--repo-root",
        str(repo.root),
    ]
    if command == "apply":
        arguments.extend(
            [
                "--approval-ref",
                approval_ref,
                "--approved-digest",
                approved_digest or digest(raw),
                "--expected-current-revision",
                str(expected_revision),
                "--expected-current-digest",
                expected_digest,
            ]
        )
        if failure_point:
            arguments.extend(["--test-failure-point", failure_point])
    completed = run(
        arguments,
        cwd=repo.root,
        env=(
            {"SERVO_MILESTONE_INIT_ALLOW_TEST_FAILURE": "1"}
            if failure_point
            else None
        ),
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"worker did not emit JSON:\nstdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        ) from exc
    return completed, payload


def worker_call_with_final_read_race(
    repo: DisposableRepo,
    raw: bytes,
    replacement: bytes,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    candidate = repo.candidate_path(raw, "already-applied-race-candidate.md")
    replacement_path = repo.candidate_path(
        replacement,
        "already-applied-race-replacement.bin",
    )
    launcher = """
import os
import runpy
import sys
from pathlib import Path

sys.path.insert(0, os.environ["MILESTONE_INIT_SCRIPTS"])
import milestone_exact_persistence as exact_persistence

verify_exact_bytes = exact_persistence.verify_exact_bytes

def replace_before_final_read(target, approved_bytes, *, mismatch_code):
    Path(target).write_bytes(Path(os.environ["RACE_REPLACEMENT"]).read_bytes())
    return verify_exact_bytes(target, approved_bytes, mismatch_code=mismatch_code)

exact_persistence.verify_exact_bytes = replace_before_final_read
sys.argv[0] = os.environ["MILESTONE_INIT_WORKER"]
runpy.run_path(os.environ["MILESTONE_INIT_WORKER"], run_name="__main__")
"""
    completed = run(
        [
            sys.executable,
            "-c",
            launcher,
            "apply",
            "--mode",
            "create",
            "--candidate",
            str(candidate),
            "--repo-root",
            str(repo.root),
            "--approval-ref",
            "approval-test",
            "--approved-digest",
            digest(raw),
            "--expected-current-revision",
            "0",
            "--expected-current-digest",
            "absent",
        ],
        cwd=repo.root,
        env={
            "MILESTONE_INIT_SCRIPTS": str(WORKER.parent),
            "MILESTONE_INIT_WORKER": str(WORKER),
            "RACE_REPLACEMENT": str(replacement_path),
        },
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"raced worker did not emit JSON:\nstdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        ) from exc
    return completed, payload


class UnifiedMilestoneInitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = DisposableRepo()

    def tearDown(self) -> None:
        self.repo.close()

    def assert_failure(
        self,
        raw: bytes,
        expected_status: str,
        *,
        mode: str = "create",
    ) -> dict[str, Any]:
        completed, payload = worker_call(
            self.repo,
            "validate",
            raw,
            mode=mode,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(payload["status"], expected_status)
        self.assertIn(payload["signal"], {"invalid", "conflict", "blocked"})
        self.assertEqual(payload["writes"], [])
        return payload

    def test_skill_contract_keeps_admission_and_authorship_with_llm(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        description = next(
            line.removeprefix("description:").strip()
            for line in frontmatter.splitlines()
            if line.startswith("description:")
        )
        for phrase in (
            "讨论充分性",
            "LLM",
            "preview",
            "SHA-256 approval",
            "worker",
            "exact-byte",
            "init_not_ready",
            "milestone_ready",
            ".servo/milestone/{milestone_id}.md",
        ):
            self.assertIn(phrase, description)
        self.assertIn("signal: init_not_ready", text)
        self.assertIn("The LLM writes the complete document", text)
        self.assertIn("must not", text)
        self.assertIn("single Harness writer per workspace", text)
        self.assertIn("successful `os.replace`", text)
        self.assertIn("never restores old bytes", text)
        self.assertIn("there is no document rollback", text.lower())
        worker_text = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("init_not_ready", worker_text)
        self.assertNotIn("DocumentLock", worker_text)
        self.assertNotIn("lock_path", worker_text)
        self.assertNotIn("rollback", worker_text.lower())
        self.assertNotIn("restore_document", worker_text)
        self.assertNotIn("time.sleep", worker_text)
        self.assertNotIn("repaired_document", worker_text)
        self.assertLessEqual(len(worker_text.splitlines()), 1300)

    def test_template_style_candidate_validates_without_writes(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        completed, payload = worker_call(
            self.repo,
            "validate",
            raw,
            mode="create",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["signal"], "proposal_ready")
        self.assertEqual(payload["preview_digest"], digest(raw))
        self.assertEqual(payload["proposed_action"], "create")
        self.assertEqual(payload["branch_outcome"], "would_create")
        self.assertEqual(payload["writes"], [])
        self.assertFalse(self.repo.target().exists())
        branch_probe = subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/heads/{self.repo.milestone_branch()}",
            ],
            cwd=self.repo.root,
            check=False,
        )
        self.assertEqual(branch_probe.returncode, 1)

    def test_linked_git_worktree_is_a_supported_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as linked_parent:
            linked_root = Path(linked_parent) / "linked-worktree"
            git(
                self.repo.root,
                "worktree",
                "add",
                "--detach",
                str(linked_root),
                self.repo.baseline,
            )
            try:
                (linked_root / ".servo" / "milestone").mkdir(parents=True)
                raw = milestone_bytes(self.repo.baseline)
                candidate = linked_root / "candidate.md"
                candidate.write_bytes(raw)
                completed = run(
                    [
                        sys.executable,
                        str(WORKER),
                        "validate",
                        "--mode",
                        "create",
                        "--candidate",
                        str(candidate),
                        "--repo-root",
                        str(linked_root),
                    ],
                    cwd=linked_root,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual(payload["signal"], "proposal_ready")
                self.assertEqual(payload["writes"], [])
            finally:
                git(
                    self.repo.root,
                    "worktree",
                    "remove",
                    "--force",
                    str(linked_root),
                )

    def test_flexible_markdown_is_preserved_as_exact_bytes(self) -> None:
        raw = milestone_bytes(
            self.repo.baseline,
            field_order_variant=True,
            section_order_variant=True,
            preamble="This approved preamble is ordinary prose.",
            tasklist_commentary=(
                "This commentary follows the last entry and remains opaque."
            ),
            extra_section="Additional approved prose is legal.",
            newline="\r\n",
            terminal_newline=False,
        )
        checked, preview = worker_call(
            self.repo,
            "validate",
            raw,
            mode="create",
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        applied, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            approved_digest=preview["preview_digest"],
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(result["status"], "created")
        self.assertEqual(self.repo.target().read_bytes(), raw)
        self.assertNotIn("repaired_document", result)

    def test_fenced_markdown_is_opaque_to_all_document_controls(self) -> None:
        raw = milestone_bytes(
            self.repo.baseline,
            tasklist_commentary=(
                "```markdown\n"
                "## Goal\n"
                "### [x] WT-GHOST\n\n"
                "- worktrack_id: `WT-GHOST`\n"
                "- depends_on: `[]`\n"
                "- condition: `required`\n"
                "- covers: `MS-TEST-AC-99`\n"
                "- result_ref: `.servo/worktrack/WT-GHOST/finished-handback.yaml`\n"
                "```"
            ),
        )
        raw = raw.replace(
            b"MS-TEST-AC-01 must be independently adjudicable.\n",
            (
                b"MS-TEST-AC-01 must be independently adjudicable.\n\n"
                b"~~~markdown\n"
                b"### MS-TEST-AC-99 - fenced example\n\n"
                b"This is not a declared acceptance criterion.\n"
                b"~~~\n"
            ),
        ).replace(
            b"- final_acceptance_ref: `null`\n",
            (
                b"- final_acceptance_ref: `null`\n\n"
                b"```yaml\n"
                b"- milestone_gate_ref: `.servo/milestone/fenced-example.md`\n"
                b"```\n"
            ),
        )
        completed, payload = worker_call(
            self.repo,
            "validate",
            raw,
            mode="create",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["control_summary"]["worktrack_ids"], ["WT-A"])
        self.assertEqual(
            payload["control_summary"]["acceptance_ids"],
            ["MS-TEST-AC-01"],
        )
        self.assertEqual(payload["writes"], [])

        canonical = milestone_bytes(self.repo.baseline)
        prefix, separator, body = canonical.partition(b"---\n# ")
        self.assertEqual(separator, b"---\n# ")
        fenced_only = prefix + b"---\n```markdown\n# " + body + b"```\n"
        self.assert_failure(fenced_only, "invalid_document_envelope")

    def test_markdown_code_span_lists_are_control_equivalent(self) -> None:
        raw = milestone_bytes(
            self.repo.baseline,
            criteria=["MS-TEST-AC-01", "MS-TEST-AC-02"],
        ).replace(
            b"- covers: `MS-TEST-AC-01`\n",
            b"- covers: `MS-TEST-AC-01`, `MS-TEST-AC-02`\n",
        )
        completed, payload = worker_call(
            self.repo,
            "validate",
            raw,
            mode="create",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            payload["control_summary"]["acceptance_ids"],
            ["MS-TEST-AC-01", "MS-TEST-AC-02"],
        )
        self.assertEqual(payload["writes"], [])

    def test_domain_validation_rejects_duplicate_ids_and_bad_edges(self) -> None:
        duplicate_criteria = milestone_bytes(
            self.repo.baseline,
            criteria=["MS-TEST-AC-01", "MS-TEST-AC-01"],
        )
        self.assert_failure(duplicate_criteria, "duplicate_acceptance_criteria")

        invalid_cover = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MISSING-AC",
                    "result_ref": "null",
                }
            ],
        )
        self.assert_failure(invalid_cover, "invalid_worktrack_coverage")

        missing_dependency = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "WT-MISSING",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                }
            ],
        )
        self.assert_failure(missing_dependency, "unknown_worktrack_dependency")

        self_dependency = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "WT-A",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                }
            ],
        )
        self.assert_failure(self_dependency, "cyclic_worktrack_dependency")

        cycle = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": False,
                    "outcome": "First.",
                    "condition": "required",
                    "depends_on": "WT-B",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                },
                {
                    "worktrack_id": "WT-B",
                    "checked": False,
                    "outcome": "Second.",
                    "condition": "required",
                    "depends_on": "WT-A",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                },
            ],
        )
        self.assert_failure(cycle, "cyclic_worktrack_dependency")

    def test_domain_validation_rejects_control_and_authority_violations(self) -> None:
        malformed_id = milestone_bytes(
            self.repo.baseline,
            milestone_id="../escape",
        )
        self.assert_failure(malformed_id, "invalid_milestone_id")

        unknown_frontmatter = milestone_bytes(self.repo.baseline).replace(
            b'owner: "test-owner"\n',
            b'owner: "test-owner"\nactive_milestone_ref: "forbidden"\n',
        )
        self.assert_failure(unknown_frontmatter, "runtime_state_in_document")

        checked_without_result = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": True,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": "null",
                }
            ],
        )
        self.assert_failure(checked_without_result, "checkbox_result_mismatch")

        handback = (
            self.repo.root
            / ".servo"
            / "worktrack"
            / "WT-A"
            / "finished-handback.yaml"
        )
        handback.parent.mkdir(parents=True)
        handback.write_text("worktrack_id: WT-A\n", encoding="utf-8")
        create_with_result = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": True,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": (
                        ".servo/worktrack/WT-A/finished-handback.yaml"
                    ),
                }
            ],
        )
        self.assert_failure(create_with_result, "result_authority_violation")

        final_artifact = self.repo.root / ".servo" / "milestone" / "gate.md"
        final_artifact.write_text("gate\n", encoding="utf-8")
        create_with_final = milestone_bytes(
            self.repo.baseline,
            gate_ref=".servo/milestone/gate.md",
        )
        self.assert_failure(
            create_with_final,
            "final_acceptance_authority_violation",
        )

    def test_create_and_safe_repeat_use_exact_bytes_and_zero_write_replay(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        original_checkout = git(self.repo.root, "branch", "--show-current")
        applied, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(result["signal"], "milestone_ready")
        self.assertEqual(result["status"], "created")
        self.assertEqual(self.repo.target().read_bytes(), raw)
        self.assertEqual(
            git(self.repo.root, "rev-parse", self.repo.milestone_branch()),
            self.repo.baseline,
        )
        self.assertEqual(
            git(self.repo.root, "branch", "--show-current"),
            original_checkout,
        )
        self.assertEqual(
            result["writes"],
            [
                f"refs/heads/{self.repo.milestone_branch()}",
                ".servo/milestone/MS-TEST-001.md",
            ],
        )
        replayed, replay = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            expected_revision=0,
            expected_digest="absent",
            name="same-approved-candidate.md",
        )
        self.assertEqual(replayed.returncode, 0, replayed.stderr)
        self.assertEqual(replay["status"], "already_applied")
        self.assertEqual(replay["writes"], [])
        self.assertFalse(
            list((self.repo.root / ".servo" / "milestone").glob("*.lock"))
        )
        self.assertFalse(
            list((self.repo.root / ".servo" / "milestone").glob(".*.tmp"))
        )

    def test_already_applied_final_read_race_reports_no_durable_candidate_write(
        self,
    ) -> None:
        raw = milestone_bytes(self.repo.baseline)
        applied, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(result["status"], "created")

        replacement = b"canonical target changed before final exact readback\n"
        raced, failure = worker_call_with_final_read_race(
            self.repo,
            raw,
            replacement,
        )

        self.assertEqual(raced.returncode, 2, raced.stderr)
        self.assertEqual(failure["signal"], "conflict")
        self.assertEqual(failure["status"], "stale_compare_and_swap")
        self.assertEqual(failure["writes"], [])
        self.assertEqual(failure["details"]["commit_point"], "before_replace")
        self.assertFalse(failure["details"]["roll_forward_required"])
        self.assertEqual(self.repo.target().read_bytes(), replacement)
        self.assertNotEqual(self.repo.target().read_bytes(), raw)

    def test_digest_and_expected_state_fail_before_persistence(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        wrong_digest, digest_result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            approved_digest="sha256:" + "0" * 64,
        )
        self.assertEqual(wrong_digest.returncode, 2)
        self.assertEqual(digest_result["status"], "approval_digest_mismatch")
        self.assertEqual(digest_result["writes"], [])
        self.assertFalse(self.repo.target().exists())

        stale, stale_result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            expected_revision=1,
            expected_digest=digest(raw),
        )
        self.assertEqual(stale.returncode, 2)
        self.assertEqual(stale_result["signal"], "conflict")
        self.assertEqual(stale_result["status"], "expected_state_mismatch")
        self.assertEqual(stale_result["writes"], [])
        self.assertFalse(self.repo.target().exists())

    def test_amend_and_safe_repeat_preserve_exact_prior_history(self) -> None:
        revision1 = milestone_bytes(self.repo.baseline)
        first, first_result = worker_call(
            self.repo,
            "apply",
            revision1,
            mode="create",
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        revision1_digest = first_result["canonical_digest"]
        revision2_block = amendment_block(
            2,
            approval_ref="approval-r2",
            extra_prose="Approved revision-two commentary.",
        )
        revision2 = milestone_bytes(
            self.repo.baseline,
            revision=2,
            goal="Deliver the amended observable outcome.",
            amendments=[revision2_block],
        )
        amended, result = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=1,
            expected_digest=revision1_digest,
        )
        self.assertEqual(amended.returncode, 0, amended.stderr)
        self.assertEqual(result["status"], "revised")
        self.assertEqual(result["writes"], [".servo/milestone/MS-TEST-001.md"])
        self.assertEqual(self.repo.target().read_bytes(), revision2)

        wrong_prior, wrong_prior_result = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=1,
            expected_digest="sha256:" + "0" * 64,
            name="revision2-wrong-prior-replay.md",
        )
        self.assertEqual(wrong_prior.returncode, 2)
        self.assertEqual(wrong_prior_result["signal"], "conflict")
        self.assertEqual(wrong_prior_result["status"], "stale_compare_and_swap")
        self.assertEqual(wrong_prior_result["writes"], [])
        self.assertEqual(self.repo.target().read_bytes(), revision2)

        replayed, replay = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=2,
            expected_digest=digest(revision2),
            name="revision2-replay.md",
        )
        self.assertEqual(replayed.returncode, 0, replayed.stderr)
        self.assertEqual(replay["status"], "already_applied")
        self.assertEqual(replay["writes"], [])

        revision3 = milestone_bytes(
            self.repo.baseline,
            revision=3,
            goal="Deliver the revision-three outcome.",
            amendments=[
                revision2_block + "\n",
                amendment_block(3, approval_ref="approval-r3"),
            ],
        )
        valid, preview = worker_call(
            self.repo,
            "validate",
            revision3,
            mode="amend",
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(preview["proposed_action"], "amend")

        rewritten_prior = revision3.replace(
            b"- reason: `Exercise deterministic amendment handling`\n",
            b"- reason:  `Exercise deterministic amendment handling`\n",
            1,
        )
        self.assert_failure(
            rewritten_prior,
            "amendment_history_change",
            mode="amend",
        )

    def test_result_and_final_refs_must_be_preserved_on_amend(self) -> None:
        handback = (
            self.repo.root
            / ".servo"
            / "worktrack"
            / "WT-A"
            / "finished-handback.yaml"
        )
        handback.parent.mkdir(parents=True)
        handback.write_text("worktrack_id: WT-A\n", encoding="utf-8")
        gate = self.repo.root / ".servo" / "milestone" / "MS-TEST-gate.md"
        final = self.repo.root / ".servo" / "milestone" / "MS-TEST-final.md"
        gate.write_text("gate\n", encoding="utf-8")
        final.write_text("final\n", encoding="utf-8")
        accepted_current = milestone_bytes(
            self.repo.baseline,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": True,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": (
                        ".servo/worktrack/WT-A/finished-handback.yaml"
                    ),
                }
            ],
            gate_ref=".servo/milestone/MS-TEST-gate.md",
            final_ref=".servo/milestone/MS-TEST-final.md",
        )
        self.repo.target().write_bytes(accepted_current)
        git(
            self.repo.root,
            "branch",
            self.repo.milestone_branch(),
            self.repo.baseline,
        )
        preserved = milestone_bytes(
            self.repo.baseline,
            revision=2,
            entries=[
                {
                    "worktrack_id": "WT-A",
                    "checked": True,
                    "outcome": "Contribution.",
                    "condition": "required",
                    "depends_on": "[]",
                    "covers": "MS-TEST-AC-01",
                    "result_ref": (
                        ".servo/worktrack/WT-A/finished-handback.yaml"
                    ),
                }
            ],
            amendments=[
                amendment_block(2, approval_ref="approval-r2")
            ],
            gate_ref=".servo/milestone/MS-TEST-gate.md",
            final_ref=".servo/milestone/MS-TEST-final.md",
        )
        checked, preview = worker_call(
            self.repo,
            "validate",
            preserved,
            mode="amend",
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(preview["proposed_action"], "amend")

        removed_result = preserved.replace(
            b"### [x] WT-A",
            b"### [ ] WT-A",
        ).replace(
            b"`.servo/worktrack/WT-A/finished-handback.yaml`",
            b"`null`",
        )
        self.assert_failure(
            removed_result,
            "result_authority_violation",
            mode="amend",
        )
        reinterpreted_result = preserved.replace(
            b"- outcome: Contribution.\n",
            b"- outcome: Reinterpreted contribution.\n",
        )
        self.assert_failure(
            reinterpreted_result,
            "result_authority_violation",
            mode="amend",
        )
        changed_final = preserved.replace(
            b"`.servo/milestone/MS-TEST-final.md`",
            b"`null`",
        )
        self.assert_failure(
            changed_final,
            "final_acceptance_authority_violation",
            mode="amend",
        )

    def test_pre_replace_failure_keeps_document_and_retains_legal_branch(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        failed, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            failure_point="before-replace",
        )
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(result["status"], "injected_failure")
        self.assertEqual(result["details"]["commit_point"], "before_replace")
        self.assertFalse(result["details"]["roll_forward_required"])
        self.assertFalse(self.repo.target().exists())
        self.assertEqual(
            git(self.repo.root, "rev-parse", self.repo.milestone_branch()),
            self.repo.baseline,
        )
        self.assertEqual(
            result["writes"],
            [f"refs/heads/{self.repo.milestone_branch()}"],
        )
        self.assertFalse(
            list((self.repo.root / ".servo" / "milestone").glob(".*.tmp"))
        )

        retry, retry_result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            name="retry.md",
        )
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertEqual(retry_result["status"], "created")
        self.assertEqual(retry_result["branch_outcome"], "existing_at_baseline")
        self.assertEqual(
            retry_result["writes"],
            [".servo/milestone/MS-TEST-001.md"],
        )

    def test_post_replace_failure_rolls_forward_to_already_applied(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        failed, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            failure_point="after-replace",
        )
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(result["status"], "injected_failure")
        self.assertEqual(result["details"]["commit_point"], "after_replace")
        self.assertTrue(result["details"]["roll_forward_required"])
        self.assertEqual(self.repo.target().read_bytes(), raw)
        self.assertEqual(
            result["writes"],
            [
                f"refs/heads/{self.repo.milestone_branch()}",
                ".servo/milestone/MS-TEST-001.md",
            ],
        )

        replayed, replay = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
            expected_revision=0,
            expected_digest="absent",
            name="post-replace-safe-repeat.md",
        )
        self.assertEqual(replayed.returncode, 0, replayed.stderr)
        self.assertEqual(replay["status"], "already_applied")
        self.assertEqual(replay["writes"], [])
        self.assertEqual(self.repo.target().read_bytes(), raw)

    def test_amend_failure_boundaries_preserve_then_roll_forward(self) -> None:
        revision1 = milestone_bytes(self.repo.baseline)
        created, created_result = worker_call(
            self.repo,
            "apply",
            revision1,
            mode="create",
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        revision1_digest = created_result["canonical_digest"]
        revision2 = milestone_bytes(
            self.repo.baseline,
            revision=2,
            goal="Deliver the approved revision-two outcome.",
            amendments=[amendment_block(2, approval_ref="approval-r2")],
        )

        before, before_result = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=1,
            expected_digest=revision1_digest,
            failure_point="before-replace",
            name="amend-before-replace.md",
        )
        self.assertEqual(before.returncode, 2)
        self.assertEqual(before_result["details"]["commit_point"], "before_replace")
        self.assertEqual(before_result["writes"], [])
        self.assertEqual(self.repo.target().read_bytes(), revision1)

        after, after_result = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=1,
            expected_digest=revision1_digest,
            failure_point="after-replace",
            name="amend-after-replace.md",
        )
        self.assertEqual(after.returncode, 2)
        self.assertEqual(after_result["details"]["commit_point"], "after_replace")
        self.assertTrue(after_result["details"]["roll_forward_required"])
        self.assertEqual(
            after_result["writes"],
            [".servo/milestone/MS-TEST-001.md"],
        )
        self.assertEqual(self.repo.target().read_bytes(), revision2)

        replayed, replay = worker_call(
            self.repo,
            "apply",
            revision2,
            mode="amend",
            approval_ref="approval-r2",
            expected_revision=2,
            expected_digest=digest(revision2),
            name="amend-safe-repeat.md",
        )
        self.assertEqual(replayed.returncode, 0, replayed.stderr)
        self.assertEqual(replay["status"], "already_applied")
        self.assertEqual(replay["writes"], [])

    def test_branch_existing_correct_is_reused_and_wrong_ref_conflicts(self) -> None:
        raw = milestone_bytes(self.repo.baseline)
        git(
            self.repo.root,
            "branch",
            self.repo.milestone_branch(),
            self.repo.baseline,
        )
        applied, result = worker_call(
            self.repo,
            "apply",
            raw,
            mode="create",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(result["branch_outcome"], "existing_at_baseline")
        self.assertEqual(result["writes"], [".servo/milestone/MS-TEST-001.md"])

        other = DisposableRepo()
        try:
            wrong_raw = milestone_bytes(other.baseline)
            (other.root / "wrong.txt").write_text("wrong\n", encoding="utf-8")
            git(other.root, "add", "wrong.txt")
            git(other.root, "commit", "-m", "wrong branch checkpoint")
            wrong_head = git(other.root, "rev-parse", "HEAD")
            git(
                other.root,
                "branch",
                other.milestone_branch(),
                wrong_head,
            )
            checked, conflict = worker_call(
                other,
                "validate",
                wrong_raw,
                mode="create",
            )
            self.assertEqual(checked.returncode, 2)
            self.assertEqual(conflict["signal"], "conflict")
            self.assertEqual(conflict["status"], "branch_ref_conflict")
            self.assertEqual(conflict["writes"], [])
        finally:
            other.close()

    def test_same_revision_conflict_and_skipped_revision_fail_closed(self) -> None:
        revision1 = milestone_bytes(self.repo.baseline)
        applied, first = worker_call(
            self.repo,
            "apply",
            revision1,
            mode="create",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        changed_same_revision = milestone_bytes(
            self.repo.baseline,
            goal="Different bytes at the same revision.",
        )
        self.assert_failure(
            changed_same_revision,
            "same_revision_conflict",
            mode="create",
        )
        skipped = milestone_bytes(
            self.repo.baseline,
            revision=3,
            amendments=[
                amendment_block(2, approval_ref="approval-r2"),
                amendment_block(3, approval_ref="approval-r3"),
            ],
        )
        self.assert_failure(skipped, "skipped_revision", mode="amend")
        self.assertEqual(self.repo.target().read_bytes(), revision1)
        self.assertEqual(first["canonical_digest"], digest(revision1))

    def test_template_and_worker_are_package_local_and_self_contained(self) -> None:
        self.assertTrue(SKILL.is_file())
        self.assertTrue(TEMPLATE.is_file())
        self.assertTrue(WORKER.is_file())
        self.assertTrue(CHECKER.is_file())
        self.assertTrue(REPOSITORY.is_file())
        self.assertTrue(PERSISTENCE.is_file())
        template = TEMPLATE.read_text(encoding="utf-8")
        for section in (
            "## Goal",
            "## Scope",
            "## Non-Goals",
            "## Cross-Worktrack Design Decisions",
            "## Worktrack Tasklist",
            "## Milestone-Level Acceptance Criteria",
            "## Amendments",
            "## Finalization References",
        ):
            self.assertIn(section, template)
        self.assertNotIn(".agents/", SKILL.read_text(encoding="utf-8"))
        self.assertNotIn(".claude/", WORKER.read_text(encoding="utf-8"))
        worker_source = WORKER.read_text(encoding="utf-8")
        for component in (
            "milestone_document_check",
            "milestone_repository",
            "milestone_exact_persistence",
        ):
            self.assertIn(f"import {component}", worker_source)


if __name__ == "__main__":
    unittest.main()
