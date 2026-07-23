from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SKILLS_DIR = REPO_ROOT / "product" / "harness" / "skills"
ADAPTER_SKILLS_DIR = (
    REPO_ROOT / "product" / "harness" / "adapters" / "agents" / "skills"
)
CLAUDE_ADAPTER_SKILLS_DIR = (
    REPO_ROOT / "product" / "harness" / "adapters" / "claude" / "skills"
)
AW_INSTALLER_SCRIPT = (
    REPO_ROOT / "toolchain" / "scripts" / "deploy" / "bin" / "servo-installer.js"
)
EXPECTED_CANONICAL_SKILLS = {
    path.name
    for path in CANONICAL_SKILLS_DIR.iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
}
EXPECTED_AGENTS_SKILLS = EXPECTED_CANONICAL_SKILLS
EXPECTED_CLAUDE_SKILLS = EXPECTED_CANONICAL_SKILLS
AGENTS_TARGET_DIR_OVERRIDES = {}
CLAUDE_TARGET_DIR_OVERRIDES = {}
AGENTS_LEGACY_TARGET_DIR_OVERRIDES = {
    "worktrack-plan-work-skill": [],
    "worktrack-review-skill": [],
    "repo-init-goal-skill": [
        "harness-set-goal-skill",
        "set-harness-goal-skill",
        "aw-set-harness-goal-skill",
    ],
    "milestone-init-skill": ["init-milestone-skill", "aw-init-milestone-skill"],
    "repo-change-goal-skill": [
        "goal-change-control-skill",
        "servo-repo-change-goal-skill",
        "aw-repo-change-goal-skill",
    ],
    "worktrack-cleanup-skill": ["cleanup-skill", "aw-cleanup-skill"],
    "worktrack-close-skill": ["close-worktrack-skill", "aw-close-worktrack-skill"],
    "worktrack-dispatch-skill": ["dispatch-skills", "aw-dispatch-skills"],
    "worktrack-doc-catch-up-skill": [
        "doc-catch-up-worker-skill",
        "aw-doc-catch-up-worker-skill",
    ],
    "worktrack-gate-skill": ["gate-skill", "aw-gate-skill"],
    "worktrack-generic-worker-skill": [
        "generic-worker-skill",
        "aw-generic-worker-skill",
    ],
    "worktrack-init-skill": ["init-worktrack-skill", "aw-init-worktrack-skill"],
    "worktrack-recover-skill": [
        "recover-worktrack-skill",
        "aw-recover-worktrack-skill",
    ],
    "worktrack-review-evidence-skill": [
        "review-evidence-skill",
        "aw-review-evidence-skill",
    ],
    "worktrack-rule-check-skill": ["rule-check-skill", "aw-rule-check-skill"],
    "worktrack-schedule-skill": [
        "schedule-worktrack-skill",
        "aw-schedule-worktrack-skill",
    ],
    "worktrack-test-evidence-skill": ["test-evidence-skill", "aw-test-evidence-skill"],
}
CLAUDE_LEGACY_TARGET_DIR_OVERRIDES = {
    "worktrack-plan-work-skill": [],
    "worktrack-review-skill": [],
    "harness-skill": ["servo-harness-skill"],
    "repo-init-goal-skill": [
        "harness-set-goal-skill",
        "aw-set-harness-goal-skill",
        "set-harness-goal-skill",
    ],
    "milestone-init-skill": ["aw-init-milestone-skill"],
    "worktrack-cleanup-skill": ["cleanup-skill", "aw-cleanup-skill"],
    "worktrack-close-skill": ["aw-close-worktrack-skill"],
    "worktrack-dispatch-skill": ["aw-dispatch-skills"],
    "worktrack-doc-catch-up-skill": ["aw-doc-catch-up-worker-skill"],
    "worktrack-gate-skill": ["aw-gate-skill"],
    "worktrack-generic-worker-skill": ["aw-generic-worker-skill"],
    "worktrack-init-skill": ["aw-init-worktrack-skill"],
    "worktrack-recover-skill": ["aw-recover-worktrack-skill"],
    "worktrack-review-evidence-skill": ["aw-review-evidence-skill"],
    "worktrack-rule-check-skill": ["aw-rule-check-skill"],
    "worktrack-schedule-skill": ["aw-schedule-worktrack-skill"],
    "worktrack-test-evidence-skill": ["aw-test-evidence-skill"],
}
NORMAL_PATH_REQUIRED_FILES = {
    "harness-skill": {
        "SKILL.md",
        "scripts/autonomy_policy_check.py",
        "scripts/worktrack_round_chain_check.py",
        "scripts/worktrack_setup_check.py",
    },
    "worktrack-plan-work-skill": {"SKILL.md"},
    "worktrack-review-skill": {"SKILL.md"},
    "milestone-init-skill": {
        "SKILL.md",
        "scripts/milestone_document_transaction.py",
        "templates/milestone.template.md",
    },
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_milestone_action_routes(path: Path) -> dict[str, tuple[str, str, str]]:
    routes: dict[str, tuple[str, str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] not in {"create", "amend", "select"}:
            continue
        action, route, owner, approval_boundary = cells
        if action in routes:
            raise AssertionError(f"duplicate milestone action route {action} in {path}")
        routes[action] = (route, owner, approval_boundary)
    return routes


def included_paths_from_payload(payload: dict[str, object]) -> list[str]:
    canonical_dir = payload["canonical_dir"]
    canonical_paths = payload["canonical_paths"]
    assert isinstance(canonical_dir, str)
    assert isinstance(canonical_paths, list)

    canonical_dir_path = PurePosixPath(canonical_dir)
    included_paths: list[str] = []
    for canonical_path in canonical_paths:
        assert isinstance(canonical_path, str)
        included_paths.append(
            PurePosixPath(canonical_path).relative_to(canonical_dir_path).as_posix()
        )
    return included_paths


class AgentsAdapterContractTest(unittest.TestCase):
    def test_agents_adapter_payloads_follow_canonical_copy_contract(self) -> None:
        adapter_skill_dirs = sorted(
            path.name for path in ADAPTER_SKILLS_DIR.iterdir() if path.is_dir()
        )
        self.assertEqual(adapter_skill_dirs, sorted(EXPECTED_AGENTS_SKILLS))

        for skill_id in adapter_skill_dirs:
            payload_path = ADAPTER_SKILLS_DIR / skill_id / "payload.json"

            self.assertTrue(payload_path.is_file(), payload_path)
            self.assertEqual(
                sorted(
                    path.name
                    for path in (ADAPTER_SKILLS_DIR / skill_id).iterdir()
                    if path.is_file()
                ),
                ["payload.json"],
            )

            payload = load_json(payload_path)
            included_paths = included_paths_from_payload(payload)
            canonical_dir = payload["canonical_dir"]
            canonical_paths = payload["canonical_paths"]

            actual_canonical_files = sorted(
                path.relative_to(REPO_ROOT / str(canonical_dir)).as_posix()
                for path in (REPO_ROOT / str(canonical_dir)).rglob("*")
                if path.is_file()
            )
            self.assertEqual(sorted(included_paths), actual_canonical_files)

            self.assertEqual(payload["payload_version"], "agents-skill-payload.v1")
            self.assertEqual(payload["backend"], "agents")
            self.assertEqual(payload["skill_id"], skill_id)
            self.assertEqual(
                payload["canonical_dir"], f"product/harness/skills/{skill_id}"
            )
            self.assertEqual(
                payload["canonical_paths"],
                [f"{canonical_dir}/{path}" for path in included_paths],
            )
            expected_target_dir = AGENTS_TARGET_DIR_OVERRIDES.get(skill_id)
            if expected_target_dir is None:
                self.assertEqual(payload["target_dir"], skill_id)
            else:
                self.assertEqual(payload["target_dir"], expected_target_dir)
            self.assertEqual(
                payload["legacy_target_dirs"],
                AGENTS_LEGACY_TARGET_DIR_OVERRIDES.get(
                    skill_id, [f"servo-{skill_id}", f"aw-{skill_id}"]
                ),
            )
            self.assertEqual(payload["target_entry_name"], "SKILL.md")
            self.assertEqual(payload["payload_policy"], "canonical-copy")
            self.assertEqual(payload["supported_target_scopes"], ["local"])
            self.assertEqual(
                payload["reference_distribution"], "copy-listed-canonical-paths"
            )
            self.assertEqual(
                payload["required_payload_files"],
                [*included_paths, "payload.json", "aw.marker"],
            )
            self.assertNotIn("first_wave_profile", payload)
            self.assertNotIn("first_wave_scope_kind", payload)
            self.assertNotIn("supported_repo_actions", payload)
            self.assertEqual(Path(str(canonical_dir)).name, skill_id)

            for canonical_path in canonical_paths:
                self.assertTrue((REPO_ROOT / canonical_path).is_file(), canonical_path)

    def test_claude_adapter_payloads_follow_canonical_copy_contract(self) -> None:
        adapter_skill_dirs = sorted(
            path.name for path in CLAUDE_ADAPTER_SKILLS_DIR.iterdir() if path.is_dir()
        )
        self.assertEqual(adapter_skill_dirs, sorted(EXPECTED_CLAUDE_SKILLS))

        for skill_id in adapter_skill_dirs:
            payload_path = CLAUDE_ADAPTER_SKILLS_DIR / skill_id / "payload.json"

            self.assertTrue(payload_path.is_file(), payload_path)
            self.assertEqual(
                sorted(
                    path.name
                    for path in (CLAUDE_ADAPTER_SKILLS_DIR / skill_id).iterdir()
                    if path.is_file()
                ),
                ["payload.json"],
            )

            payload = load_json(payload_path)
            included_paths = included_paths_from_payload(payload)
            canonical_dir = payload["canonical_dir"]
            canonical_paths = payload["canonical_paths"]

            actual_canonical_files = sorted(
                path.relative_to(REPO_ROOT / str(canonical_dir)).as_posix()
                for path in (REPO_ROOT / str(canonical_dir)).rglob("*")
                if path.is_file()
            )
            self.assertEqual(sorted(included_paths), actual_canonical_files)

            self.assertEqual(payload["payload_version"], "claude-skill-payload.v1")
            self.assertEqual(payload["backend"], "claude")
            self.assertEqual(payload["skill_id"], skill_id)
            self.assertEqual(
                payload["canonical_dir"], f"product/harness/skills/{skill_id}"
            )
            self.assertEqual(
                payload["canonical_paths"],
                [f"{canonical_dir}/{path}" for path in included_paths],
            )
            self.assertEqual(
                payload["target_dir"],
                CLAUDE_TARGET_DIR_OVERRIDES.get(skill_id, skill_id),
            )
            self.assertEqual(
                payload["legacy_target_dirs"],
                CLAUDE_LEGACY_TARGET_DIR_OVERRIDES.get(skill_id, [f"aw-{skill_id}"]),
            )
            self.assertEqual(payload["target_entry_name"], "SKILL.md")
            self.assertEqual(payload["payload_policy"], "canonical-copy")
            self.assertEqual(payload["supported_target_scopes"], ["local"])
            self.assertEqual(
                payload["reference_distribution"], "copy-listed-canonical-paths"
            )
            self.assertEqual(
                payload["required_payload_files"],
                [*included_paths, "payload.json", "aw.marker"],
            )
            self.assertEqual(Path(str(canonical_dir)).name, skill_id)

            for canonical_path in canonical_paths:
                self.assertTrue((REPO_ROOT / canonical_path).is_file(), canonical_path)

    def test_agents_adapter_target_dirs_are_unique(self) -> None:
        target_dir_to_skills: dict[str, list[str]] = {}

        for skill_dir in sorted(
            path for path in ADAPTER_SKILLS_DIR.iterdir() if path.is_dir()
        ):
            skill_id = skill_dir.name
            payload_path = ADAPTER_SKILLS_DIR / skill_id / "payload.json"

            self.assertTrue(payload_path.is_file(), payload_path)

            payload = load_json(payload_path)
            target_dir = payload["target_dir"]

            self.assertIsInstance(target_dir, str)
            target_dir_to_skills.setdefault(target_dir, []).append(skill_id)

        duplicates = {
            target_dir: sorted(skill_ids)
            for target_dir, skill_ids in target_dir_to_skills.items()
            if len(skill_ids) > 1
        }
        self.assertEqual(
            duplicates,
            {},
            f"duplicate target_dir bindings are not allowed: {duplicates}",
        )

    def test_cleanup_skill_uses_milestone_canonical_identity_with_legacy_compatibility(
        self,
    ) -> None:
        self.assertFalse((ADAPTER_SKILLS_DIR / "cleanup-skill").exists())
        self.assertFalse((CLAUDE_ADAPTER_SKILLS_DIR / "cleanup-skill").exists())

        agents_payload = load_json(
            ADAPTER_SKILLS_DIR / "milestone-cleanup-skill" / "payload.json"
        )
        claude_payload = load_json(
            CLAUDE_ADAPTER_SKILLS_DIR / "milestone-cleanup-skill" / "payload.json"
        )

        for payload in (agents_payload, claude_payload):
            self.assertEqual(payload["skill_id"], "milestone-cleanup-skill")
            self.assertIn(
                "product/harness/skills/milestone-cleanup-skill/scripts/control_state_compact.py",
                payload["canonical_paths"],
            )
            self.assertIn(
                "scripts/control_state_compact.py",
                payload["required_payload_files"],
            )
            self.assertEqual(
                payload["canonical_dir"],
                "product/harness/skills/milestone-cleanup-skill",
            )
            self.assertEqual(payload["target_dir"], "milestone-cleanup-skill")
            self.assertNotIn("worktrack-cleanup-skill", payload["legacy_target_dirs"])
            self.assertNotIn("cleanup-skill", payload["legacy_target_dirs"])
            self.assertNotIn("aw-cleanup-skill", payload["legacy_target_dirs"])

        legacy_agents_payload = load_json(
            ADAPTER_SKILLS_DIR / "worktrack-cleanup-skill" / "payload.json"
        )
        legacy_claude_payload = load_json(
            CLAUDE_ADAPTER_SKILLS_DIR / "worktrack-cleanup-skill" / "payload.json"
        )
        for payload in (legacy_agents_payload, legacy_claude_payload):
            self.assertEqual(payload["skill_id"], "worktrack-cleanup-skill")
            self.assertEqual(payload["target_dir"], "worktrack-cleanup-skill")

    def test_repo_init_goal_agents_payload_includes_default_repo_analysis_template(
        self,
    ) -> None:
        payload = load_json(
            ADAPTER_SKILLS_DIR / "repo-init-goal-skill" / "payload.json"
        )
        canonical_paths = payload["canonical_paths"]
        required_payload_files = payload["required_payload_files"]

        self.assertIsInstance(canonical_paths, list)
        self.assertIsInstance(required_payload_files, list)
        self.assertIn(
            "product/harness/skills/repo-init-goal-skill/assets/repo/analysis.md",
            canonical_paths,
        )
        self.assertIn("assets/repo/analysis.md", required_payload_files)
        self.assertIn(
            "product/harness/skills/repo-init-goal-skill/assets/repo/temporary-understanding.md",
            canonical_paths,
        )
        self.assertIn("assets/repo/temporary-understanding.md", required_payload_files)
        self.assertIn(
            "product/harness/skills/repo-init-goal-skill/scripts/complexity_signal_scanner.py",
            canonical_paths,
        )
        self.assertIn("scripts/complexity_signal_scanner.py", required_payload_files)

        claude_payload = load_json(
            CLAUDE_ADAPTER_SKILLS_DIR / "repo-init-goal-skill" / "payload.json"
        )
        self.assertIn(
            "product/harness/skills/repo-init-goal-skill/scripts/complexity_signal_scanner.py",
            claude_payload["canonical_paths"],
        )
        self.assertIn(
            "scripts/complexity_signal_scanner.py",
            claude_payload["required_payload_files"],
        )

    def test_repo_whats_next_payload_includes_overview_fallback_reference(self) -> None:
        payload = load_json(
            ADAPTER_SKILLS_DIR / "repo-whats-next-skill" / "payload.json"
        )
        canonical_paths = payload["canonical_paths"]
        required_payload_files = payload["required_payload_files"]

        self.assertIsInstance(canonical_paths, list)
        self.assertIsInstance(required_payload_files, list)
        self.assertIn(
            "product/harness/skills/repo-whats-next-skill/references/overview-fallback-mode.md",
            canonical_paths,
        )
        self.assertIn("references/overview-fallback-mode.md", required_payload_files)

    def test_normal_path_payloads_include_explicit_required_files(self) -> None:
        for backend_dir in (ADAPTER_SKILLS_DIR, CLAUDE_ADAPTER_SKILLS_DIR):
            for skill_id, required_files in NORMAL_PATH_REQUIRED_FILES.items():
                payload = load_json(backend_dir / skill_id / "payload.json")
                canonical_dir = payload["canonical_dir"]
                canonical_paths = payload["canonical_paths"]
                payload_files = payload["required_payload_files"]

                self.assertIsInstance(canonical_dir, str)
                self.assertIsInstance(canonical_paths, list)
                self.assertIsInstance(payload_files, list)
                for relative_path in required_files:
                    self.assertIn(
                        f"{canonical_dir}/{relative_path}",
                        canonical_paths,
                        f"{backend_dir.name}/{skill_id} omits {relative_path}",
                    )
                    self.assertIn(
                        relative_path,
                        payload_files,
                        f"{backend_dir.name}/{skill_id} does not require {relative_path}",
                    )

    def test_unified_milestone_init_retires_separate_management_packages(self) -> None:
        self.assertEqual(len(EXPECTED_CANONICAL_SKILLS), 19)
        for retired in ("milestone-pre-intake-skill", "milestone-status-skill"):
            self.assertFalse((CANONICAL_SKILLS_DIR / retired).exists())
            self.assertFalse((ADAPTER_SKILLS_DIR / retired).exists())
            self.assertFalse((CLAUDE_ADAPTER_SKILLS_DIR / retired).exists())

        for backend_dir in (ADAPTER_SKILLS_DIR, CLAUDE_ADAPTER_SKILLS_DIR):
            payload = load_json(backend_dir / "milestone-init-skill" / "payload.json")
            self.assertIn(
                "scripts/milestone_document_transaction.py",
                payload["required_payload_files"],
            )
            self.assertIn(
                "templates/milestone.template.md",
                payload["required_payload_files"],
            )

    def test_unified_milestone_callers_use_direct_harness_observation(self) -> None:
        harness_dir = CANONICAL_SKILLS_DIR / "harness-skill"
        repo_decide = CANONICAL_SKILLS_DIR / "repo-whats-next-skill" / "SKILL.md"
        self.assertFalse(
            (harness_dir / "scripts/pre_milestone_intake_guard.py").exists()
        )
        self.assertFalse((harness_dir / "scripts/writeback_bridge.py").exists())

        caller_paths = (
            harness_dir / "SKILL.md",
            CANONICAL_SKILLS_DIR / "repo-status-skill" / "SKILL.md",
            repo_decide,
            CANONICAL_SKILLS_DIR / "repo-refresh-skill" / "SKILL.md",
            CANONICAL_SKILLS_DIR / "milestone-blackbox-check" / "SKILL.md",
            CANONICAL_SKILLS_DIR / "milestone-whitebox-check" / "SKILL.md",
            CANONICAL_SKILLS_DIR / "milestone-gate" / "SKILL.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in caller_paths)
        self.assertNotIn("milestone-status-skill", combined)
        self.assertNotIn("milestone-pre-intake-skill", combined)
        self.assertNotIn("pre_milestone_intake_guard", combined)
        self.assertNotIn("writeback_bridge.py", combined)
        self.assertIn("直接零写读取 canonical Milestone document", combined)
        self.assertIn("closed contribution facts", combined)

        repo_decide_text = repo_decide.read_text(encoding="utf-8")
        for retired_term in (
            "purpose/worktrack_list",
            "worktrack_list",
            "completion_signals",
            "acceptance_criteria",
            "planned/active milestone",
        ):
            self.assertNotIn(retired_term, repo_decide_text)
        for canonical_term in (
            "canonical Goal",
            "Worktrack Tasklist",
            "Milestone-Level Acceptance Criteria",
            "稳定 refs",
            "suggested_milestone_id",
            "suggested_milestone_ref",
            "target_milestone_id",
            "target_milestone_ref",
            "milestone_purpose_alignment",
        ):
            self.assertIn(canonical_term, repo_decide_text)

    def test_milestone_caller_actions_have_distinct_route_owners(self) -> None:
        expected_routes = {
            "create": (
                "milestone-init-skill",
                "Milestone Init",
                "exact-document-digest",
            ),
            "amend": (
                "milestone-init-skill",
                "Milestone Init",
                "exact-document-digest",
            ),
            "select": (
                "harness-select-milestone",
                "Harness",
                "selection-currentness",
            ),
        }
        callers = (
            CANONICAL_SKILLS_DIR / "repo-whats-next-skill" / "SKILL.md",
            CANONICAL_SKILLS_DIR / "repo-append-request-skill" / "SKILL.md",
        )
        for caller in callers:
            with self.subTest(caller=caller.parent.name):
                self.assertEqual(load_milestone_action_routes(caller), expected_routes)
                caller_text = caller.read_text(encoding="utf-8")
                self.assertIn("discussion-sufficiency admission", caller_text)
                self.assertNotIn("交给统一 Init 继续讨论", caller_text)

        append_template = (
            CANONICAL_SKILLS_DIR
            / "repo-append-request-skill"
            / "templates"
            / "append-request.template.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "milestone_route_owner：Milestone Init / Harness / N/A",
            append_template,
        )
        self.assertIn(
            "approval_boundary：exact-document-digest / selection-currentness / N/A",
            append_template,
        )

    def test_agents_installer_diagnose_json_reports_missing_root_without_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir) / "missing-agents-skills"
            completed = subprocess.run(
                [
                    "node",
                    str(AW_INSTALLER_SCRIPT),
                    "diagnose",
                    "--backend",
                    "agents",
                    "--agents-root",
                    str(target_root),
                    "--json",
                ],
                check=False,
                capture_output=True,
                cwd=temp_dir,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")

        summary = json.loads(completed.stdout)
        self.assertEqual(summary["backend"], "agents")
        self.assertEqual(summary["target_root"], str(target_root))
        self.assertEqual(summary["target_root_status"], "missing")
        self.assertFalse(summary["target_root_exists"])
        self.assertEqual(summary["managed_install_count"], 0)
        self.assertEqual(summary["issue_count"], 1)
        self.assertEqual(summary["issue_codes"], ["missing-target-root"])
        self.assertEqual(summary["issues"][0]["code"], "missing-target-root")

    def test_agents_installer_diagnose_json_reports_wrong_type_target_as_conflict(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir) / "agents-skills"
            target_root.mkdir()
            (target_root / "servo-harness-skill").write_text(
                "not a directory\n", encoding="utf-8"
            )

            completed = subprocess.run(
                [
                    "node",
                    str(AW_INSTALLER_SCRIPT),
                    "diagnose",
                    "--backend",
                    "agents",
                    "--agents-root",
                    str(target_root),
                    "--json",
                ],
                check=False,
                capture_output=True,
                cwd=temp_dir,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")

        summary = json.loads(completed.stdout)
        self.assertIn("missing-target-entry", summary["issue_codes"])


if __name__ == "__main__":
    unittest.main()
