from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLISH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish.yml"
RELEASE_METADATA_SCRIPT = REPO_ROOT / "toolchain" / "scripts" / "deploy" / "bin" / "resolve-release-metadata.js"


def read_publish_workflow() -> str:
    return PUBLISH_WORKFLOW.read_text(encoding="utf-8")


def test_publish_workflow_uses_release_published_trigger_and_oidc() -> None:
    workflow = read_publish_workflow()

    assert "release:" in workflow
    assert "types: [published]" in workflow
    assert re.search(r"\bid-token:\s*write\b", workflow)
    assert re.search(r"\bcontents:\s*read\b", workflow)
    assert "persist-credentials: false" in workflow
    assert "concurrency:" in workflow
    assert "servo-installer-publish-${{ github.event.release.tag_name }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert re.search(r"\btimeout-minutes:\s*30\b", workflow)


def test_publish_workflow_uses_npm_environment_and_registry() -> None:
    workflow = read_publish_workflow()

    assert re.search(r"\benvironment:\s*npm\b", workflow)
    assert 'registry-url: "https://registry.npmjs.org/"' in workflow
    assert 'node-version: "24"' in workflow
    assert "expected_npm_integrity=" in workflow
    assert "npm view npm@11.5.1 dist.integrity" in workflow
    assert "npm install -g npm@11.5.1" in workflow
    assert "npm publish --provenance --access public --tag \"$SERVO_INSTALLER_RELEASE_CHANNEL\"" in workflow


def test_publish_workflow_resolves_and_checks_release_metadata_before_publish() -> None:
    workflow = read_publish_workflow()
    resolver = RELEASE_METADATA_SCRIPT.read_text(encoding="utf-8")

    assert "SERVO_INSTALLER_RELEASE_GIT_TAG" in resolver
    assert "SERVO_INSTALLER_RELEASE_CHANNEL" in resolver
    assert resolver.count("appendFileSync(") == 1
    assert 'const { deriveReleaseChannelFromTag, semverPattern } = require("./check-root-publish.js");' in resolver
    assert "const semverPattern =" not in resolver
    assert "GITHUB_RELEASE_TAG" in workflow
    assert "GITHUB_RELEASE_BODY" in workflow
    assert "NPM_CONFIG_TAG" in workflow
    assert "servo-installer-publish-approved:" in resolver
    assert "node toolchain/scripts/deploy/bin/resolve-release-metadata.js" in workflow
    assert "node toolchain/scripts/deploy/bin/check-root-publish.js" in workflow


def test_publish_workflow_runs_pre_publish_validation_gates() -> None:
    workflow = read_publish_workflow()

    required_commands = [
        "python toolchain/scripts/test/folder_logic_check.py",
        "python toolchain/scripts/test/path_governance_check.py",
        "python toolchain/scripts/test/governance_semantic_check.py",
        "python -m pip install --requirement .github/requirements-ci.txt",
        "python -m pytest toolchain/scripts/test",
        "npm --prefix toolchain/scripts/deploy run smoke --silent",
        "npm --prefix toolchain/scripts/deploy test --silent",
        "npm pack --dry-run --json",
        "npm run publish:dry-run --silent",
    ]

    for command in required_commands:
        assert command in workflow


def run_release_metadata_case(case: dict[str, object]) -> subprocess.CompletedProcess[str]:
    script = (
        "const { deriveReleaseMetadata } = require('./toolchain/scripts/deploy/bin/resolve-release-metadata.js');"
        "const input = JSON.parse(process.argv[1]);"
        "try { console.log(JSON.stringify(deriveReleaseMetadata(input))); }"
        "catch (error) { console.error(error.message); process.exit(1); }"
    )
    return subprocess.run(
        ["node", "-e", script, "--", json.dumps(case)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_release_metadata_resolver_accepts_rc_stable_and_canary_shapes() -> None:
    cases = [
        {
            "version": "1.2.3-rc.1",
            "releaseTag": "v1.2.3-rc.1",
            "releasePrerelease": "TRUE",
            "releaseBody": "servo-installer-publish-approved: v1.2.3-rc.1",
            "expected": '"releaseChannel":"next"',
        },
        {
            "version": "1.2.3",
            "releaseTag": "v1.2.3",
            "releasePrerelease": "False",
            "releaseBody": "servo-installer-publish-approved: v1.2.3",
            "expected": '"releaseChannel":"latest"',
        },
        {
            "version": "1.2.3-canary.1",
            "releaseTag": "v1.2.3-canary.1",
            "releasePrerelease": True,
            "releaseBody": "servo-installer-publish-approved: v1.2.3-canary.1",
            "expected": '"releaseChannel":"canary"',
        },
    ]

    for case in cases:
        expected = str(case["expected"])
        input_case = {key: value for key, value in case.items() if key != "expected"}
        completed = run_release_metadata_case(input_case)
        assert completed.returncode == 0, completed.stderr
        assert expected in completed.stdout


def test_release_metadata_resolver_formats_github_env_as_single_block() -> None:
    script = (
        "const { formatGithubEnv } = require('./toolchain/scripts/deploy/bin/resolve-release-metadata.js');"
        "console.log(JSON.stringify(formatGithubEnv({"
        "releaseTag:'v1.2.3-rc.1',releaseChannel:'next',npmConfigTag:'next'})));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == (
        "SERVO_INSTALLER_RELEASE_GIT_TAG=v1.2.3-rc.1\n"
        "SERVO_INSTALLER_RELEASE_CHANNEL=next\n"
        "NPM_CONFIG_TAG=next\n"
    )


def test_publish_guard_run_checks_throws_instead_of_exiting() -> None:
    script = (
        "const { runChecks, semverPattern } = require('./toolchain/scripts/deploy/bin/check-root-publish.js');"
        "try { runChecks([{ test: () => false, message: () => 'expected failure' }]); }"
        "catch (error) { console.log(error.message); }"
        "console.log(semverPattern.test('1.2.3-rc.1') ? 'semver-ok' : 'semver-fail');"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "expected failure\nsemver-ok\n"


def test_release_metadata_resolver_rejects_unsafe_shapes() -> None:
    cases = [
        (
            {
                "version": "1.2.3-rc.1",
                "releaseTag": "v1.2.3",
                "releasePrerelease": True,
                "releaseBody": "servo-installer-publish-approved: v1.2.3",
            },
            "must match package version",
        ),
        (
            {
                "version": "1.2.3",
                "releaseTag": "v1.2.3",
                "releasePrerelease": True,
                "releaseBody": "servo-installer-publish-approved: v1.2.3",
            },
            "cannot publish to latest",
        ),
        (
            {
                "version": "1.2.3-rc.1",
                "releaseTag": "v1.2.3-rc.1",
                "releasePrerelease": False,
                "releaseBody": "servo-installer-publish-approved: v1.2.3-rc.1",
            },
            "cannot publish prerelease channel",
        ),
        (
            {
                "version": "1.2.3-preview.1",
                "releaseTag": "v1.2.3-preview.1",
                "releasePrerelease": True,
                "releaseBody": "servo-installer-publish-approved: v1.2.3-preview.1",
            },
            "does not map to a release channel",
        ),
        (
            {
                "version": "1.2.3-rc.1",
                "releaseTag": "v1.2.3-rc.1",
                "releasePrerelease": True,
                "releaseBody": "release notes without approval marker",
            },
            "explicit approval marker",
        ),
    ]

    for case, expected_error in cases:
        completed = run_release_metadata_case(case)
        assert completed.returncode == 1
        assert expected_error in completed.stderr
