from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_SKILLS_DIR = REPO_ROOT / "product" / "harness" / "adapters" / "agents" / "skills"
CLAUDE_ADAPTER_SKILLS_DIR = REPO_ROOT / "product" / "harness" / "adapters" / "claude" / "skills"
AW_INSTALLER_SCRIPT = REPO_ROOT / "toolchain" / "scripts" / "deploy" / "bin" / "servo-installer.js"
EXPECTED_AGENTS_SKILLS = {
    "close-worktrack-skill",
    "dispatch-skills",
    "doc-catch-up-worker-skill",
    "gate-skill",
    "generic-worker-skill",
    "harness-skill",
    "init-milestone-skill",
    "init-worktrack-skill",
    "milestone-status-skill",
    "pre-milestone-intake-skill",
    "recover-worktrack-skill",
    "repo-append-request-skill",
    "repo-change-goal-skill",
    "repo-refresh-skill",
    "repo-status-skill",
    "repo-whats-next-skill",
    "review-evidence-skill",
    "rule-check-skill",
    "schedule-worktrack-skill",
    "set-harness-goal-skill",
    "servo-cleanup-skill",
    "test-evidence-skill",
    "worktrack-status-skill",
}
EXPECTED_CLAUDE_SKILLS = {
    *EXPECTED_AGENTS_SKILLS,
}
AGENTS_TARGET_DIR_OVERRIDES = {
    "harness-skill": "servo-harness-skill",
    "set-harness-goal-skill": "servo-set-harness-goal-skill",
    "servo-cleanup-skill": "servo-cleanup-skill",
}
CLAUDE_TARGET_DIR_OVERRIDES = {
    "set-harness-goal-skill": "servo-set-harness-goal-skill",
    "servo-cleanup-skill": "servo-cleanup-skill",
}
AGENTS_LEGACY_TARGET_DIR_OVERRIDES = {
    "harness-skill": ["harness-skill"],
    "repo-change-goal-skill": [
        "goal-change-control-skill",
        "repo-change-goal-skill",
        "aw-repo-change-goal-skill",
    ],
    "servo-cleanup-skill": ["cleanup-skill", "aw-cleanup-skill"],
}
CLAUDE_LEGACY_TARGET_DIR_OVERRIDES = {
    "harness-skill": ["servo-harness-skill"],
    "set-harness-goal-skill": ["aw-set-harness-goal-skill", "set-harness-goal-skill"],
    "servo-cleanup-skill": ["cleanup-skill", "aw-cleanup-skill"],
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def included_paths_from_payload(payload: dict[str, object]) -> list[str]:
    canonical_dir = payload["canonical_dir"]
    canonical_paths = payload["canonical_paths"]
    assert isinstance(canonical_dir, str)
    assert isinstance(canonical_paths, list)

    canonical_dir_path = PurePosixPath(canonical_dir)
    included_paths: list[str] = []
    for canonical_path in canonical_paths:
        assert isinstance(canonical_path, str)
        included_paths.append(PurePosixPath(canonical_path).relative_to(canonical_dir_path).as_posix())
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
                sorted(path.name for path in (ADAPTER_SKILLS_DIR / skill_id).iterdir() if path.is_file()),
                ["payload.json"],
            )

            payload = load_json(payload_path)
            included_paths = included_paths_from_payload(payload)
            canonical_dir = payload["canonical_dir"]
            canonical_paths = payload["canonical_paths"]

            self.assertEqual(payload["payload_version"], "agents-skill-payload.v1")
            self.assertEqual(payload["backend"], "agents")
            self.assertEqual(payload["skill_id"], skill_id)
            self.assertEqual(payload["canonical_dir"], f"product/harness/skills/{skill_id}")
            self.assertEqual(payload["canonical_paths"], [f"{canonical_dir}/{path}" for path in included_paths])
            expected_target_dir = AGENTS_TARGET_DIR_OVERRIDES.get(skill_id)
            if expected_target_dir is None:
                self.assertEqual(payload["target_dir"], f"servo-{skill_id}")
            else:
                self.assertEqual(payload["target_dir"], expected_target_dir)
            self.assertEqual(
                payload["legacy_target_dirs"],
                AGENTS_LEGACY_TARGET_DIR_OVERRIDES.get(skill_id, [skill_id, f"aw-{skill_id}"]),
            )
            self.assertEqual(payload["target_entry_name"], "SKILL.md")
            self.assertEqual(payload["payload_policy"], "canonical-copy")
            self.assertEqual(payload["supported_target_scopes"], ["local"])
            self.assertEqual(payload["reference_distribution"], "copy-listed-canonical-paths")
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

            self.assertEqual(payload["payload_version"], "claude-skill-payload.v1")
            self.assertEqual(payload["backend"], "claude")
            self.assertEqual(payload["skill_id"], skill_id)
            self.assertEqual(payload["canonical_dir"], f"product/harness/skills/{skill_id}")
            self.assertEqual(payload["canonical_paths"], [f"{canonical_dir}/{path}" for path in included_paths])
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
            self.assertEqual(payload["reference_distribution"], "copy-listed-canonical-paths")
            self.assertEqual(
                payload["required_payload_files"],
                [*included_paths, "payload.json", "aw.marker"],
            )
            self.assertEqual(Path(str(canonical_dir)).name, skill_id)

            for canonical_path in canonical_paths:
                self.assertTrue((REPO_ROOT / canonical_path).is_file(), canonical_path)

    def test_agents_adapter_target_dirs_are_unique(self) -> None:
        target_dir_to_skills: dict[str, list[str]] = {}

        for skill_dir in sorted(path for path in ADAPTER_SKILLS_DIR.iterdir() if path.is_dir()):
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

    def test_cleanup_skill_uses_servo_qualified_identity(self) -> None:
        self.assertFalse((ADAPTER_SKILLS_DIR / "cleanup-skill").exists())
        self.assertFalse((CLAUDE_ADAPTER_SKILLS_DIR / "cleanup-skill").exists())

        agents_payload = load_json(ADAPTER_SKILLS_DIR / "servo-cleanup-skill" / "payload.json")
        claude_payload = load_json(CLAUDE_ADAPTER_SKILLS_DIR / "servo-cleanup-skill" / "payload.json")

        for payload in (agents_payload, claude_payload):
            self.assertEqual(payload["skill_id"], "servo-cleanup-skill")
            self.assertEqual(payload["canonical_dir"], "product/harness/skills/servo-cleanup-skill")
            self.assertEqual(payload["target_dir"], "servo-cleanup-skill")
            self.assertIn("cleanup-skill", payload["legacy_target_dirs"])
            self.assertIn("aw-cleanup-skill", payload["legacy_target_dirs"])

    def test_set_harness_goal_agents_payload_includes_default_repo_analysis_template(self) -> None:
        payload = load_json(
            ADAPTER_SKILLS_DIR / "set-harness-goal-skill" / "payload.json"
        )
        canonical_paths = payload["canonical_paths"]
        required_payload_files = payload["required_payload_files"]

        self.assertIsInstance(canonical_paths, list)
        self.assertIsInstance(required_payload_files, list)
        self.assertIn(
            "product/harness/skills/set-harness-goal-skill/assets/repo/analysis.md",
            canonical_paths,
        )
        self.assertIn("assets/repo/analysis.md", required_payload_files)
        self.assertIn(
            "product/harness/skills/set-harness-goal-skill/assets/repo/temporary-understanding.md",
            canonical_paths,
        )
        self.assertIn("assets/repo/temporary-understanding.md", required_payload_files)
        self.assertIn(
            "product/harness/skills/set-harness-goal-skill/scripts/complexity_signal_scanner.py",
            canonical_paths,
        )
        self.assertIn("scripts/complexity_signal_scanner.py", required_payload_files)

        claude_payload = load_json(
            CLAUDE_ADAPTER_SKILLS_DIR / "set-harness-goal-skill" / "payload.json"
        )
        self.assertIn(
            "product/harness/skills/set-harness-goal-skill/scripts/complexity_signal_scanner.py",
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

    def test_agents_installer_diagnose_json_reports_missing_root_without_failure(self) -> None:
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

    def test_agents_installer_diagnose_json_reports_wrong_type_target_as_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_root = Path(temp_dir) / "agents-skills"
            target_root.mkdir()
            (target_root / "servo-harness-skill").write_text("not a directory\n", encoding="utf-8")

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
        self.assertIn("wrong-target-entry-type", summary["issue_codes"])
        self.assertGreater(summary["conflict_count"], 0)
        self.assertTrue(
            any(issue["code"] == "wrong-target-entry-type" for issue in summary["conflicts"]),
            summary["conflicts"],
        )

if __name__ == "__main__":
    unittest.main()
