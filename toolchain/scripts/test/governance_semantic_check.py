#!/usr/bin/env python3
"""Run minimal semantic governance checks for key docs handoffs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from cache_scan_policy import CACHE_SCAN_ROOTS
except ModuleNotFoundError:
    from toolchain.scripts.test.cache_scan_policy import CACHE_SCAN_ROOTS
from path_governance_check import REQUIRED_GITIGNORE_ENTRIES, iter_relative_markdown_targets, resolve_markdown_target


REPO_ROOT = Path(__file__).resolve().parents[3]
FOUNDATIONS_DIR = "docs/project-maintenance/foundations"
REQUIRED_TEMPLATE_PATHS = [
    "docs/harness/artifact/worktrack/contract.md",
    "docs/harness/artifact/worktrack/plan-task-queue.md",
    "docs/harness/artifact/worktrack/gate-evidence.md",
    "docs/harness/artifact/worktrack/debug-evidence.md",
]
REQUIRED_HANDOFF_LINKS = {
    "product/README.md": [
        "product/harness/README.md",
    ],
    "toolchain/toolchain-layering.md": [
        "toolchain/scripts/README.md",
    ],
    "docs/harness/README.md": [
        "docs/harness/foundations/README.md",
        "docs/harness/artifact/README.md",
        "docs/harness/workflow-families/README.md",
        "product/harness/README.md",
    ],
    "product/harness/README.md": [
        "docs/harness/README.md",
        "product/harness/skills/README.md",
        "product/harness/adapters/README.md",
    ],
    "docs/harness/artifact/worktrack/README.md": [
        "docs/harness/artifact/worktrack/contract.md",
        "docs/harness/artifact/worktrack/plan-task-queue.md",
        "docs/harness/artifact/worktrack/gate-evidence.md",
        "docs/harness/artifact/worktrack/debug-evidence.md",
    ],
}
FOUNDATIONS_AUTHORITY_STEMS = [
    "root-directory-layering",
]
OUTDATED_PLACEHOLDER_PHRASES = {
    "docs/harness/README.md": [
        "已验证的 legacy skills 已降级为可回收资产；当前 repo 不再保留独立的 harness skill/source 分区",
    ],
    "docs/harness/workflow-families/README.md": [
        "当前这些 workflow family 先固定在文档真相层；仓库内不再保留独立的 `product/harness/` workflow/profile source 分区。",
    ],
    "toolchain/toolchain-layering.md": [
        "`research/` 与 `evals/` 保留为预留位，只有在方案重新准入后才继续扩展。",
    ],
    "toolchain/scripts/README.md": [
        "`research/`：预留给后续准入的最小研究脚本",
    ],
}
RETIRED_ENTRYPOINT_REFERENCES = {
    "AGENTS.md": [
        "docs/harness/adjacent-systems/memory-side/",
        "docs/harness/adjacent-systems/memory-side/layer-boundary.md",
        "docs/harness/adjacent-systems/memory-side/overview.md",
        "docs/harness/adjacent-systems/memory-side/skill-agent-model.md",
        "docs/harness/adjacent-systems/task-interface/",
        "product/memory-side/README.md",
        "product/memory-side/skills/",
        "product/task-interface/README.md",
        "product/task-interface/skills/",
    ],
    "docs/README.md": [
        "docs/harness/adjacent-systems/memory-side/",
        "docs/harness/adjacent-systems/memory-side/layer-boundary.md",
        "docs/harness/adjacent-systems/memory-side/overview.md",
        "docs/harness/adjacent-systems/memory-side/skill-agent-model.md",
        "docs/harness/adjacent-systems/task-interface/",
    ],
    "docs/harness/README.md": [
        "docs/harness/adjacent-systems/memory-side/",
        "docs/harness/adjacent-systems/memory-side/layer-boundary.md",
        "docs/harness/adjacent-systems/memory-side/overview.md",
        "docs/harness/adjacent-systems/memory-side/skill-agent-model.md",
        "docs/harness/adjacent-systems/task-interface/",
    ],
}
CANONICAL_SKILL_GLOBS = [
    "product/*/skills/*/SKILL.md",
]
ADAPTER_SKILL_GLOBS = [
    "product/*/adapters/*/skills/*/SKILL.md",
]
CANONICAL_SKILL_FORBIDDEN_HEADINGS = [
    "## Canonical Source",
    "## Backend Notes",
    "## Deploy Target",
]
THIN_WRAPPER_REQUIRED_HEADINGS = [
    "## Canonical Source",
    "## Backend Notes",
    "## Deploy Target",
]
THIN_WRAPPER_FORBIDDEN_HEADINGS = [
    "## Execution Rules",
    "## Output Contract",
]
APPEND_REQUEST_CONTRACT_PATHS = [
    "docs/harness/artifact/control/append-request.md",
    "docs/harness/workflow-families/repo-evolution/append-request-routing.md",
    "product/harness/skills/repo-append-request-skill/SKILL.md",
    "product/harness/skills/repo-append-request-skill/templates/append-request.template.md",
]
PATH_GOVERNANCE_CHECKS_DOC = "docs/project-maintenance/governance/path-governance-checks.md"
REVIEW_VERIFY_HANDBOOK_DOC = "docs/project-maintenance/governance/review-verify-handbook.md"
TOOLCHAIN_TEST_README_DOC = "toolchain/scripts/test/README.md"
CODEX_HARNESS_MANUAL_RUNBOOK_DOC = (
    "docs/project-maintenance/testing/codex-post-deploy-behavior-tests.md"
)
SUBAGENT_DEFAULT_CONTRACT_PATHS = [
    "product/harness/skills/harness-skill/SKILL.md",
    "product/harness/skills/dispatch-skills/SKILL.md",
    "product/harness/skills/set-harness-goal-skill/SKILL.md",
    "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
    "product/.aw_template/control-state.md",
    "docs/harness/artifact/control/control-state.md",
    "docs/harness/artifact/worktrack/contract.md",
    "docs/harness/foundations/Harness运行协议.md",
    "docs/harness/catalog/worktrack.md",
]
EXECUTION_POLICY_TEMPLATE_REFERENCE_PATHS = [
    "product/harness/skills/set-harness-goal-skill/assets/worktrack/contract.md",
    "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
    "product/.aw_template/worktrack/contract.md",
]
AGENTS_ADAPTER_SKILLS_DIR = "product/harness/adapters/agents/skills"
MANUAL_RUNBOOK_AGENTS_SKILL_COUNT_RE = re.compile(
    r"当前 `agents` install 已包含全部 (?P<count>\d+) 个 skills"
)
CLOSEOUT_ACCEPTANCE_GATE_STEPS = [
    "scope_gate",
    "spec_gate",
    "static_gate",
    "cache_gate",
    "test_gate",
    "smoke_gate",
]
ARTIFACT_SKILL_ALIGNMENTS = [
    {
        "contract": "docs/harness/artifact/worktrack/contract.md",
        "skill": "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
        "label": "contract.md ↔ init-worktrack-skill template",
        "fields": [
            "node_type",
            "baseline_form",
            "merge_required",
            "gate_criteria",
            "if_interrupted_strategy",
            "runtime_dispatch_mode",
        ],
    },
    {
        "contract": "docs/harness/artifact/worktrack/gate-evidence.md",
        "skill": "product/harness/skills/gate-skill/SKILL.md",
        "label": "gate-evidence.md ↔ gate-skill",
        "fields": [
            "verdict",
            "review_dimensions",
        ],
    },
    {
        "contract": "docs/harness/artifact/worktrack/plan-task-queue.md",
        "skill": "product/harness/skills/schedule-worktrack-skill/SKILL.md",
        "label": "plan-task-queue.md ↔ schedule-worktrack-skill",
        "fields": [
            "task_id",
            "status",
            "priority",
            "depends_on",
            "acceptance",
        ],
    },
]
ORPHAN_DOC_EXCLUDED_DIRS = [
    "docs/archive/",
    "docs/ideas/",
]
ORPHAN_REFERENCE_SOURCES = [
    "CLAUDE.md",
    "AGENTS.md",
]
ORPHAN_SKILL_REFERENCE_GLOBS = [
    "product/harness/skills/**/SKILL.md",
]
SUBAGENT_DEFAULT_REQUIRED_TERMS = [
    "默认",
    "SubAgent",
    "权限边界",
    "Dispatch Decision Policy",
    "subagent_dispatch_mode",
    "subagent_dispatch_mode_override_scope",
    "worktrack-contract-primary",
    "global-override",
    "runtime_dispatch_mode",
    "auto",
    "delegated",
    "current-carrier",
    "runtime fallback",
    "dispatch package unsafe",
]
EXECUTION_POLICY_TEMPLATE_REQUIRED_TERMS = [
    "Execution Policy canonical semantics are not repeated here",
    "execution_policy_contract_ref",
    "docs/harness/artifact/worktrack/contract.md#execution-policy",
    "runtime_dispatch_mode",
    "dispatch_mode_source",
    "allowed_values",
    "fallback_reason_required",
]
EXECUTION_POLICY_TEMPLATE_FORBIDDEN_PHRASES = [
    "控制本 worktrack 的执行载体选择。`auto` 按 Dispatch Decision Policy",
    "默认 scaffold 中 `.aw/control-state.md` 的 `subagent_dispatch_mode_override_scope",
]
DISPATCH_CONTEXT_CONTRACT_PATHS = [
    "docs/harness/artifact/worktrack/dispatch-packet.md",
    "product/harness/skills/dispatch-skills/SKILL.md",
    "product/harness/skills/schedule-worktrack-skill/SKILL.md",
    "product/harness/skills/generic-worker-skill/SKILL.md",
]
DISPATCH_CONTEXT_REQUIRED_TERMS = [
    "shared_fact_pack",
    "context_budget",
    "must_read",
    "may_read",
    "do_not_read",
]
RUNTIME_DISPATCH_PROFILE_CONTRACT_PATHS = [
    "docs/harness/foundations/dispatch-decision-policy.md",
    "docs/harness/foundations/runtime-dispatch-contract.md",
    "docs/harness/artifact/worktrack/dispatch-packet.md",
    "docs/harness/artifact/control/control-state.md",
    "product/harness/skills/harness-skill/SKILL.md",
    "product/harness/skills/dispatch-skills/SKILL.md",
    "product/harness/skills/set-harness-goal-skill/assets/control-state.md",
    "product/.aw_template/control-state.md",
]
RUNTIME_DISPATCH_PROFILE_REQUIRED_TERMS = [
    "runtime_dispatch_profile",
    "backend_runtime",
    "model_family",
    "subagent_dispatch_shell",
    "runtime_supports_subagent",
    "subagent_permission_state",
    "permission_allows_delegation",
    "dispatch_package_safety",
    "delegation_attempted",
    "attempted_carrier",
    "carrier_decision",
    "fallback_reason",
]
RUNTIME_DISPATCH_PROFILE_COMPATIBILITY_TERMS = [
    "ClaudeCodeCLI",
    "Deepseek",
    "runtime fallback",
    "permission blocked",
    "dispatch package unsafe",
]
REVIEW_EVIDENCE_FOUR_LANE_CONTRACT_PATHS = [
    "product/harness/skills/review-evidence-skill/SKILL.md",
    "docs/harness/catalog/worktrack.md",
    "product/harness/skills/set-harness-goal-skill/assets/worktrack/gate-evidence.md",
    "docs/harness/artifact/worktrack/gate-evidence.md",
]
REVIEW_EVIDENCE_FOUR_LANE_REQUIRED_TERMS = [
    "review_profile",
    "light",
    "standard",
    "risky",
    "deep",
    "并行",
    "SubAgent",
    "fallback",
    "static-semantic-review",
    "test-review",
    "project-security-review",
    "complexity-performance-review",
    "静态语义解释",
    "测试 review",
    "security review",
    "代码复杂度和性能 review",
]
DEBUG_EVIDENCE_CONTRACT_PATHS = [
    "docs/harness/artifact/worktrack/debug-evidence.md",
]
DEBUG_EVIDENCE_REQUIRED_TERMS = [
    "source_logs",
    "symptom",
    "reproduction_steps",
    "observed_error",
    "root_cause_hypothesis",
    "confirmed_facts",
    "discarded_hypotheses",
    "remaining_unknowns",
    "next_debug_action",
    "Raw Log Boundary",
]
DECISION_TRACEABILITY_CONTRACT_PATHS = [
    "docs/harness/artifact/repo/decision-log.md",
    "docs/harness/artifact/repo/worktrack-backlog.md",
]
DECISION_LOG_REQUIRED_TERMS = [
    "decision_id",
    "date",
    "status",
    "accepted",
    "superseded",
    "rejected",
    "context",
    "decision",
    "alternatives_considered",
    "why_not_chosen",
    "consequences",
    "affected_artifacts",
    "related_worktracks",
    "related_commits",
    "supersedes",
]
WORKTRACK_BACKLOG_TRACEABILITY_REQUIRED_TERMS = [
    "decision_refs",
]
CLOSEOUT_RECORD_CONTRACT_PATHS = [
    "docs/harness/artifact/worktrack/README.md",
    "product/harness/skills/close-worktrack-skill/SKILL.md",
]
CLOSEOUT_RECORD_REQUIRED_TERMS = [
    "closeout_record",
    "worktrack_id",
    "branch",
    "base_ref",
    "head_ref",
    "merge_commit",
    "pr",
    "files_changed",
    "acceptance_result",
    "gate_verdict",
    "evidence_refs",
    "decision_refs",
    "docs_updated",
    "snapshot_refreshed",
    "backlog_updated",
    "cleanup_done",
    "remaining_risks",
    "next_repo_scope_action",
]
REPO_WHATS_NEXT_OVERVIEW_FALLBACK_CONTRACT_PATHS = [
    "product/harness/skills/repo-whats-next-skill/SKILL.md",
    "product/harness/skills/repo-whats-next-skill/references/overview-fallback-mode.md",
    "docs/harness/catalog/repo.md",
]
REPO_WHATS_NEXT_OVERVIEW_FALLBACK_REQUIRED_TERMS = [
    "overview fallback",
    "project-dialectic-planning-skill",
    "candidate_worktracks",
    "top_candidate",
    "Facts / Inferences / Unknowns",
    "不创建工作追踪",
    "不改变 Harness 控制状态",
]
WORKTRACK_INTAKE_REVIEW_CONTRACT_PATHS = [
    "product/harness/skills/harness-skill/SKILL.md",
    "product/harness/skills/repo-whats-next-skill/SKILL.md",
    "product/harness/skills/init-worktrack-skill/SKILL.md",
    "docs/harness/scope/repo-scope.md",
    "docs/harness/foundations/runtime-control-loop.md",
    "docs/harness/artifact/worktrack/contract.md",
]
WORKTRACK_INTAKE_REVIEW_TEMPLATE_PATHS = [
    "product/harness/skills/init-worktrack-skill/templates/contract.template.md",
    "product/harness/skills/set-harness-goal-skill/assets/worktrack/contract.md",
    "product/.aw_template/worktrack/contract.md",
]
WORKTRACK_INTAKE_REVIEW_REQUIRED_TERMS = [
    "worktrack_intake_review",
    "repo_fundamentals",
    "snapshot_freshness",
    "milestone_purpose_alignment",
    "historical_conflict_risk",
    "worktrack_adjustment_recommendations",
    "add_remove_worktrack_recommendations",
    "intake_review_verdict",
    "ready_for_worktrack_init",
]
WORKTRACK_INTAKE_REVIEW_VERDICTS = [
    "ready_for_worktrack_init",
    "refresh_required",
    "adjust_worktracks",
    "blocked",
]
APPEND_REQUEST_REQUIRED_TERMS = [
    "approval_required",
    "continuation_ready",
    "continuation_blockers",
]
APPEND_REQUEST_MODES = [
    "append-feature",
    "append-design",
]
APPEND_REQUEST_CLASSIFICATIONS = [
    "goal change",
    "new worktrack",
    "scope expansion",
    "design-only",
    "design-then-implementation",
]
ROOT_TOOL_SHIM_GLOB = "tools/*.py"
BYTECODE_FREE_COMMAND_GLOBS = [
    "AGENTS.md",
    "docs/project-maintenance/**/*.md",
    "product/harness/skills/**/*.md",
    "toolchain/scripts/deploy/README.md",
]
BYTECODE_FREE_COMMAND_EXCLUDED_PATTERNS = (
    re.compile(
        r"docs/project-maintenance/testing/"
        r"codex-harness-manual-run-continuous-\d{4}-\d{2}-\d{2}\.md"
    ),
)
AGENTS_ROUTE_CONTRACT_PATH = "AGENTS.md"
AGENTS_ROUTE_REQUIRED_TERMS = [
    "## Default Boot",
    "INDEX.md",
    "当前任务对应的一个局部入口",
    "仅当任务命中对应边界时才扩读",
    "do_not_read_yet",
    ".aw/",
]
AGENTS_ROUTE_FORBIDDEN_TERMS = [
    "## Read First",
]
REPO_PYTHON_COMMAND_RE = re.compile(
    r"\bpython(?:3)?\s+(?:"
    r"-m\s+(?:pytest|unittest)\b|"
    r"(?:toolchain/scripts|tools|scripts/deploy_aw\.py|product/harness/skills)/"
    r")"
)


@dataclass
class SemanticReport:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def add_failure(self, message: str) -> None:
        self.failures.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.infos.append(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate minimal semantic governance handoffs.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def to_relative_posix(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def collect_repo_relative_markdown_links(repo_root: Path, relative_path: str) -> set[str]:
    markdown_file = repo_root / relative_path
    text = markdown_file.read_text(encoding="utf-8")
    resolved_targets: set[str] = set()
    for target in iter_relative_markdown_targets(text):
        resolved = resolve_markdown_target(markdown_file, repo_root, target)
        try:
            resolved_targets.add(to_relative_posix(resolved, repo_root))
        except ValueError:
            continue
    return resolved_targets


def markdown_headings_outside_code_fences(text: str) -> set[str]:
    headings: set[str] = set()
    in_code_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if stripped.startswith("#"):
            marker, _, title = stripped.partition(" ")
            if marker and set(marker) == {"#"} and title:
                headings.add(stripped)
    return headings


def check_required_templates(repo_root: Path, report: SemanticReport) -> None:
    missing = [path for path in REQUIRED_TEMPLATE_PATHS if not (repo_root / path).exists()]
    for path in missing:
        report.add_failure(f"missing required governance template: {path}")
    report.add_info(f"checked {len(REQUIRED_TEMPLATE_PATHS)} required governance templates")


def check_required_handoffs(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for source, expected_targets in REQUIRED_HANDOFF_LINKS.items():
        if not (repo_root / source).exists():
            report.add_failure(f"missing handoff source document: {source}")
            continue
        resolved_targets = collect_repo_relative_markdown_links(repo_root, source)
        for target in expected_targets:
            checked += 1
            if target not in resolved_targets:
                report.add_failure(f"missing semantic handoff link: {source} -> {target}")
    report.add_info(f"checked {checked} semantic handoff links")


def check_foundations_authority_shadows(repo_root: Path, report: SemanticReport) -> None:
    foundations_dir = repo_root / FOUNDATIONS_DIR
    checked = 0
    for stem in FOUNDATIONS_AUTHORITY_STEMS:
        checked += 1
        matches = sorted(path.name for path in foundations_dir.glob(f"{stem}*.md"))
        canonical_name = f"{stem}.md"
        extras = [name for name in matches if name != canonical_name]
        if canonical_name not in matches:
            report.add_failure(f"missing foundations authority document: {FOUNDATIONS_DIR}/{canonical_name}")
        if extras:
            report.add_failure(
                f"shadow authority documents found for {canonical_name}: {', '.join(extras)}"
            )
    report.add_info(f"checked {checked} foundations authority slots for shadow files")


def check_outdated_placeholder_phrases(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path, phrases in OUTDATED_PLACEHOLDER_PHRASES.items():
        if not (repo_root / relative_path).exists():
            report.add_failure(f"missing semantic phrase source document: {relative_path}")
            continue
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        for phrase in phrases:
            checked += 1
            if phrase in text:
                report.add_failure(f"outdated placeholder wording still present in {relative_path}")
    report.add_info(f"checked {checked} outdated placeholder phrases")


def check_retired_entrypoint_references(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path, retired_references in RETIRED_ENTRYPOINT_REFERENCES.items():
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing retired entrypoint scan source: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for retired_reference in retired_references:
            checked += 1
            if retired_reference in text:
                report.add_failure(
                    "retired entrypoint reference still present: "
                    f"{relative_path} -> {retired_reference}"
                )
    report.add_info(f"checked {checked} retired entrypoint references")


def iter_adapter_skill_files(repo_root: Path) -> list[Path]:
    adapter_files: list[Path] = []
    seen: set[Path] = set()
    for pattern in ADAPTER_SKILL_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path not in seen:
                seen.add(path)
                adapter_files.append(path)
    return adapter_files


def iter_canonical_skill_files(repo_root: Path) -> list[Path]:
    canonical_files: list[Path] = []
    seen: set[Path] = set()
    for pattern in CANONICAL_SKILL_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path not in seen:
                seen.add(path)
                canonical_files.append(path)
    return canonical_files


def check_canonical_skill_packages_are_minimal(repo_root: Path, report: SemanticReport) -> None:
    canonical_files = iter_canonical_skill_files(repo_root)
    if not canonical_files:
        report.add_failure("missing canonical skill packages under product/*/skills/*/SKILL.md")
        return

    checked = 0
    for canonical_file in canonical_files:
        checked += 1
        relative_path = to_relative_posix(canonical_file, repo_root)
        text = canonical_file.read_text(encoding="utf-8")

        if not text.lstrip().startswith("---"):
            report.add_failure(f"canonical skill missing frontmatter block: {relative_path}")
        if "\n# " not in text and not text.lstrip().startswith("# "):
            report.add_failure(f"canonical skill missing H1 title: {relative_path}")

        headings = markdown_headings_outside_code_fences(text)
        for heading in CANONICAL_SKILL_FORBIDDEN_HEADINGS:
            if heading in headings:
                report.add_failure(
                    f"canonical skill leaked adapter-style section {heading!r}: {relative_path}"
                )

        if "references/entrypoints.md" in text:
            report.add_failure(
                f"canonical skill still references deprecated references/entrypoints.md: {relative_path}"
            )

        references_path = canonical_file.parent / "references/entrypoints.md"
        if references_path.exists():
            report.add_failure(
                f"canonical skill still contains deprecated references/entrypoints.md file: {relative_path}"
            )

    report.add_info(f"checked {checked} canonical skill packages for minimal executable shape")


def check_adapter_wrappers_are_thin(repo_root: Path, report: SemanticReport) -> None:
    adapter_files = iter_adapter_skill_files(repo_root)
    if not adapter_files:
        report.add_info("checked 0 adapter wrappers for thin-shell structure")
        return

    checked = 0
    for adapter_file in adapter_files:
        checked += 1
        relative_path = to_relative_posix(adapter_file, repo_root)
        text = adapter_file.read_text(encoding="utf-8")
        headings = markdown_headings_outside_code_fences(text)
        for heading in THIN_WRAPPER_REQUIRED_HEADINGS:
            if heading not in headings:
                report.add_failure(
                    f"adapter wrapper missing required thin-shell heading {heading!r}: {relative_path}"
                )
        for heading in THIN_WRAPPER_FORBIDDEN_HEADINGS:
            if heading in headings:
                report.add_failure(
                    f"adapter wrapper still contains forbidden duplicated section {heading!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} adapter wrappers for thin-shell structure")


def check_append_request_contract_terms(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in APPEND_REQUEST_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing append request contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in APPEND_REQUEST_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"append request contract missing required term {term!r}: {relative_path}"
                )

    for relative_path in APPEND_REQUEST_CONTRACT_PATHS[:3]:
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for mode in APPEND_REQUEST_MODES:
            if mode not in text:
                report.add_failure(
                    f"append request contract missing mode {mode!r}: {relative_path}"
                )
        for classification in APPEND_REQUEST_CLASSIFICATIONS:
            if classification not in text:
                report.add_failure(
                    f"append request contract missing classification {classification!r}: {relative_path}"
                )

    report.add_info(f"checked {checked} append request contract sources")


def iter_bytecode_free_command_files(repo_root: Path) -> list[Path]:
    command_files: list[Path] = []
    seen: set[Path] = set()
    for pattern in BYTECODE_FREE_COMMAND_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                command_files.append(path)
    return command_files


def is_bytecode_free_command_excluded(relative_path: str) -> bool:
    return any(pattern.fullmatch(relative_path) for pattern in BYTECODE_FREE_COMMAND_EXCLUDED_PATTERNS)


def check_repo_python_commands_are_bytecode_free(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for command_file in iter_bytecode_free_command_files(repo_root):
        relative_path = to_relative_posix(command_file, repo_root)
        if is_bytecode_free_command_excluded(relative_path):
            continue

        for line_number, line in enumerate(command_file.read_text(encoding="utf-8").splitlines(), 1):
            for match in REPO_PYTHON_COMMAND_RE.finditer(line):
                checked += 1
                prefix_window = line[max(0, match.start() - 48) : match.start()]
                if "PYTHONDONTWRITEBYTECODE=1" not in prefix_window:
                    report.add_failure(
                        "repo Python command must set PYTHONDONTWRITEBYTECODE=1: "
                        f"{relative_path}:{line_number}"
                    )
    report.add_info(f"checked {checked} repo Python command examples for bytecode-free invocation")


def check_root_tool_shims_disable_bytecode(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for shim_path in sorted(repo_root.glob(ROOT_TOOL_SHIM_GLOB)):
        if not shim_path.is_file():
            continue
        checked += 1
        relative_path = to_relative_posix(shim_path, repo_root)
        text = shim_path.read_text(encoding="utf-8")
        toolchain_import_index = text.find("from toolchain.")
        if toolchain_import_index == -1:
            continue
        guard_index = text.find("sys.dont_write_bytecode = True")
        if guard_index == -1 or guard_index > toolchain_import_index:
            report.add_failure(
                "root tool shim must disable bytecode before importing toolchain modules: "
                f"{relative_path}"
            )
    report.add_info(f"checked {checked} root tool shims for bytecode guard ordering")


def check_agents_route_slimming_contract(repo_root: Path, report: SemanticReport) -> None:
    agents_path = repo_root / AGENTS_ROUTE_CONTRACT_PATH
    if not agents_path.exists():
        report.add_failure(f"missing AGENTS route contract: {AGENTS_ROUTE_CONTRACT_PATH}")
        return

    text = agents_path.read_text(encoding="utf-8")
    for term in AGENTS_ROUTE_REQUIRED_TERMS:
        if term not in text:
            report.add_failure(
                f"AGENTS route slimming contract missing required term {term!r}: "
                f"{AGENTS_ROUTE_CONTRACT_PATH}"
            )
    for term in AGENTS_ROUTE_FORBIDDEN_TERMS:
        if term in text:
            report.add_failure(
                f"AGENTS route slimming contract still has fixed preload heading {term!r}: "
                f"{AGENTS_ROUTE_CONTRACT_PATH}"
            )
    report.add_info("checked AGENTS route slimming contract")


def check_path_governance_docs_list_gitignore_entries(repo_root: Path, report: SemanticReport) -> None:
    doc_path = repo_root / PATH_GOVERNANCE_CHECKS_DOC
    if not doc_path.exists():
        report.add_failure(f"missing path governance checks document: {PATH_GOVERNANCE_CHECKS_DOC}")
        return

    text = doc_path.read_text(encoding="utf-8")
    checked = 0
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        checked += 1
        if f"`{entry}`" not in text:
            report.add_failure(
                f"path governance docs missing required .gitignore entry {entry!r}: "
                f"{PATH_GOVERNANCE_CHECKS_DOC}"
            )
    report.add_info(f"checked {checked} documented .gitignore governance entries")


def check_review_verify_docs_list_closeout_steps(repo_root: Path, report: SemanticReport) -> None:
    doc_path = repo_root / REVIEW_VERIFY_HANDBOOK_DOC
    if not doc_path.exists():
        report.add_failure(f"missing review/verify handbook: {REVIEW_VERIFY_HANDBOOK_DOC}")
        return

    text = doc_path.read_text(encoding="utf-8")
    checked = 0
    for step in CLOSEOUT_ACCEPTANCE_GATE_STEPS:
        checked += 1
        if step not in text:
            report.add_failure(
                f"review/verify handbook missing closeout gate step {step!r}: "
                f"{REVIEW_VERIFY_HANDBOOK_DOC}"
            )
    report.add_info(f"checked {checked} documented closeout gate steps")


def check_docs_list_closeout_cache_roots(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in (REVIEW_VERIFY_HANDBOOK_DOC, TOOLCHAIN_TEST_README_DOC):
        doc_path = repo_root / relative_path
        if not doc_path.exists():
            report.add_failure(f"missing closeout cache root document: {relative_path}")
            continue
        text = doc_path.read_text(encoding="utf-8")
        for root in CACHE_SCAN_ROOTS:
            checked += 1
            if f"`{root}/`" not in text:
                report.add_failure(f"document missing closeout cache root {root!r}: {relative_path}")
    report.add_info(f"checked {checked} documented closeout cache roots")


def count_agents_adapter_payload_skills(repo_root: Path, report: SemanticReport) -> int | None:
    skills_dir = repo_root / AGENTS_ADAPTER_SKILLS_DIR
    if not skills_dir.is_dir():
        report.add_failure(f"missing agents adapter skills directory: {AGENTS_ADAPTER_SKILLS_DIR}")
        return None

    count = 0
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        payload_path = child / "payload.json"
        if payload_path.is_file():
            count += 1
    if count == 0:
        report.add_failure(f"agents adapter skills directory has no payload sources: {AGENTS_ADAPTER_SKILLS_DIR}")
        return None
    return count


def check_manual_runbook_agents_skill_count(repo_root: Path, report: SemanticReport) -> None:
    expected_count = count_agents_adapter_payload_skills(repo_root, report)
    doc_path = repo_root / CODEX_HARNESS_MANUAL_RUNBOOK_DOC
    if not doc_path.exists():
        report.add_failure(f"missing Codex Harness manual runbook: {CODEX_HARNESS_MANUAL_RUNBOOK_DOC}")
        return

    text = doc_path.read_text(encoding="utf-8")
    match = MANUAL_RUNBOOK_AGENTS_SKILL_COUNT_RE.search(text)
    if match is None:
        report.add_failure(
            "Codex Harness manual runbook missing agents skill count claim: "
            f"{CODEX_HARNESS_MANUAL_RUNBOOK_DOC}"
        )
        return

    documented_count = int(match.group("count"))
    if expected_count is not None and documented_count != expected_count:
        report.add_failure(
            "Codex Harness manual runbook agents skill count mismatch: "
            f"{CODEX_HARNESS_MANUAL_RUNBOOK_DOC} documents {documented_count}, "
            f"adapter payload source has {expected_count}"
        )
    report.add_info("checked Codex Harness manual runbook agents skill count")


def check_subagent_dispatch_default_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in SUBAGENT_DEFAULT_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing SubAgent default contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in SUBAGENT_DEFAULT_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"SubAgent default contract missing required term {term!r}: {relative_path}"
                )
    for relative_path in EXECUTION_POLICY_TEMPLATE_REFERENCE_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing execution policy template reference source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in EXECUTION_POLICY_TEMPLATE_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"execution policy template missing canonical reference term {term!r}: {relative_path}"
                )
        for phrase in EXECUTION_POLICY_TEMPLATE_FORBIDDEN_PHRASES:
            if phrase in text:
                report.add_failure(
                    f"execution policy template duplicates canonical prose: {relative_path}"
                )
    report.add_info(f"checked {checked} SubAgent default dispatch contract sources")


def check_dispatch_context_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in DISPATCH_CONTEXT_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing dispatch context contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in DISPATCH_CONTEXT_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"dispatch context contract missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} dispatch context contract sources")


def check_runtime_dispatch_profile_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in RUNTIME_DISPATCH_PROFILE_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing runtime dispatch profile source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in RUNTIME_DISPATCH_PROFILE_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"runtime dispatch profile contract missing required term {term!r}: {relative_path}"
                )
        if relative_path in {
            "docs/harness/foundations/dispatch-decision-policy.md",
            "docs/harness/foundations/runtime-dispatch-contract.md",
            "docs/harness/artifact/worktrack/dispatch-packet.md",
            "product/harness/skills/harness-skill/SKILL.md",
            "product/harness/skills/dispatch-skills/SKILL.md",
        }:
            for term in RUNTIME_DISPATCH_PROFILE_COMPATIBILITY_TERMS:
                if term not in text:
                    report.add_failure(
                        "runtime dispatch profile contract missing compatibility term "
                        f"{term!r}: {relative_path}"
                    )
    report.add_info(f"checked {checked} runtime dispatch profile contract sources")


def check_review_evidence_four_lane_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in REVIEW_EVIDENCE_FOUR_LANE_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing review evidence four-lane contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in REVIEW_EVIDENCE_FOUR_LANE_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"review evidence four-lane contract missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} review evidence four-lane contract sources")


def check_debug_evidence_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in DEBUG_EVIDENCE_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing debug evidence contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in DEBUG_EVIDENCE_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"debug evidence contract missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} debug evidence contract sources")


def check_decision_traceability_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    decision_log_path = repo_root / DECISION_TRACEABILITY_CONTRACT_PATHS[0]
    if not decision_log_path.exists():
        report.add_failure(
            f"missing decision traceability contract source: {DECISION_TRACEABILITY_CONTRACT_PATHS[0]}"
        )
    else:
        checked += 1
        text = decision_log_path.read_text(encoding="utf-8")
        for term in DECISION_LOG_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"decision log contract missing required term {term!r}: "
                    f"{DECISION_TRACEABILITY_CONTRACT_PATHS[0]}"
                )

    backlog_path = repo_root / DECISION_TRACEABILITY_CONTRACT_PATHS[1]
    if not backlog_path.exists():
        report.add_failure(
            f"missing decision traceability contract source: {DECISION_TRACEABILITY_CONTRACT_PATHS[1]}"
        )
    else:
        checked += 1
        text = backlog_path.read_text(encoding="utf-8")
        for term in WORKTRACK_BACKLOG_TRACEABILITY_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"worktrack backlog traceability missing required term {term!r}: "
                    f"{DECISION_TRACEABILITY_CONTRACT_PATHS[1]}"
                )
    report.add_info(f"checked {checked} decision traceability contract sources")


def check_closeout_record_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in CLOSEOUT_RECORD_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing closeout record contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in CLOSEOUT_RECORD_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"closeout record contract missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} closeout record contract sources")


def check_repo_whats_next_overview_fallback_contract(
    repo_root: Path, report: SemanticReport
) -> None:
    checked = 0
    for relative_path in REPO_WHATS_NEXT_OVERVIEW_FALLBACK_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing repo whats-next overview fallback source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in REPO_WHATS_NEXT_OVERVIEW_FALLBACK_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"repo whats-next overview fallback missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} repo whats-next overview fallback sources")


def check_worktrack_intake_review_contract(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for relative_path in WORKTRACK_INTAKE_REVIEW_CONTRACT_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing worktrack intake review contract source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in WORKTRACK_INTAKE_REVIEW_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"worktrack intake review contract missing required term {term!r}: {relative_path}"
                )
        for verdict in WORKTRACK_INTAKE_REVIEW_VERDICTS:
            if verdict not in text:
                report.add_failure(
                    f"worktrack intake review contract missing verdict {verdict!r}: {relative_path}"
                )

    for relative_path in WORKTRACK_INTAKE_REVIEW_TEMPLATE_PATHS:
        path = repo_root / relative_path
        if not path.exists():
            report.add_failure(f"missing worktrack intake review template source: {relative_path}")
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for term in WORKTRACK_INTAKE_REVIEW_REQUIRED_TERMS:
            if term not in text:
                report.add_failure(
                    f"worktrack intake review template missing required term {term!r}: {relative_path}"
                )
    report.add_info(f"checked {checked} worktrack intake review contract sources")


def _field_name_in_text(field: str, text: str) -> bool:
    """Check if a field name is referenced in text, with flexible matching."""
    if field in text:
        return True
    if field.lower() in text.lower():
        return True
    alt = field.replace("_", " ")
    if alt.lower() in text.lower():
        return True
    return False


def check_artifact_skill_alignment(repo_root: Path, report: SemanticReport) -> None:
    checked = 0
    for entry in ARTIFACT_SKILL_ALIGNMENTS:
        contract_path = entry["contract"]
        skill_path = entry["skill"]
        label = entry["label"]
        fields = entry["fields"]

        skill_file = repo_root / skill_path
        if not skill_file.exists():
            report.add_failure(f"artifact skill alignment: missing skill file: {skill_path}")
            continue

        checked += 1
        skill_text = skill_file.read_text(encoding="utf-8")
        aligned = 0
        missing: list[str] = []
        for field in fields:
            if _field_name_in_text(field, skill_text):
                aligned += 1
            else:
                missing.append(field)

        if missing:
            for field in missing:
                report.add_warning(f"artifact skill alignment: {label}: {contract_path} defines '{field}' but {skill_path} does not reference it (may use Chinese equivalent)")
        report.add_info(f"  {label}: {aligned}/{len(fields)} fields aligned")

    report.add_info(f"checked {checked} artifact contracts for skill alignment")


def _parse_control_state(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_milestone_pipeline = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_milestone_pipeline = line.strip() == "## Milestone Pipeline"
            continue
        if not in_milestone_pipeline:
            continue
        stripped = line.strip()
        for key in ("active_milestone", "milestone_status", "milestone_pipeline_summary"):
            prefix = f"- {key}:"
            if stripped.startswith(prefix):
                fields[key] = stripped.removeprefix(prefix).strip()
    return fields


def _parse_pipeline_summary(value: str) -> dict[str, int] | None:
    summary: dict[str, int] = {}
    for status in ("planned", "active", "completed", "superseded"):
        match = re.search(rf"\b{status}\s*=\s*(\d+)\b", value)
        if match is None:
            return None
        summary[status] = int(match.group(1))
    return summary


def _parse_milestone_backlog(text: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_worktrack_list = False

    for line in text.splitlines():
        if line.startswith("- milestone_id:"):
            if current is not None:
                entries.append(current)
            current = {
                "milestone_id": line.split(":", 1)[1].strip(),
                "status": "",
                "worktrack_list": [],
                "accepted": False,
            }
            in_worktrack_list = False
            continue

        if current is None:
            continue

        stripped = line.strip()
        if line.startswith("  - "):
            in_worktrack_list = stripped.startswith("- worktrack_list:")
            if stripped.startswith("- status:"):
                current["status"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- verdict:") and "accepted" in stripped:
                current["accepted"] = True
            elif stripped.startswith("- acceptance:"):
                current["accepted"] = True
            continue

        if in_worktrack_list and line.startswith("    - "):
            worktracks = current["worktrack_list"]
            assert isinstance(worktracks, list)
            worktracks.append(stripped.removeprefix("- ").strip())

    if current is not None:
        entries.append(current)
    return entries


def check_runtime_artifact_consistency(repo_root: Path, report: SemanticReport) -> None:
    aw_dir = repo_root / ".aw"
    if not aw_dir.exists():
        report.add_info("checked 0 runtime artifacts for consistency, .aw/ directory missing")
        return

    control_path = aw_dir / "control-state.md"
    milestone_backlog_path = aw_dir / "repo/milestone-backlog.md"
    if not control_path.exists() or not milestone_backlog_path.exists():
        report.add_info("checked 0 runtime artifacts for consistency, control-state or milestone backlog missing")
        return

    control_text = control_path.read_text(encoding="utf-8")
    backlog_text = milestone_backlog_path.read_text(encoding="utf-8")
    control = _parse_control_state(control_text)
    entries = _parse_milestone_backlog(backlog_text)
    if not entries:
        report.add_failure("runtime artifact consistency: milestone backlog has no parseable entries")
        return

    counts = {status: 0 for status in ("planned", "active", "completed", "superseded")}
    active_entries: list[dict[str, object]] = []
    by_id: dict[str, dict[str, object]] = {}
    for entry in entries:
        milestone_id = str(entry["milestone_id"])
        by_id[milestone_id] = entry
        status = str(entry.get("status", ""))
        if status in counts:
            counts[status] += 1
        if status == "active":
            active_entries.append(entry)
        if status in {"completed", "superseded"} or entry.get("accepted") is True:
            worktracks = entry.get("worktrack_list", [])
            if isinstance(worktracks, list):
                stale = [
                    str(worktrack)
                    for worktrack in worktracks
                    if re.search(r"\((planned|active)\)", str(worktrack))
                ]
                if stale:
                    report.add_failure(
                        "runtime artifact consistency: completed/accepted milestone "
                        f"{milestone_id} has unfinished worktrack markers: {', '.join(stale)}"
                    )

    if len(active_entries) > 1:
        report.add_failure("runtime artifact consistency: milestone backlog has multiple active milestones")

    active_milestone = control.get("active_milestone", "")
    milestone_status = control.get("milestone_status", "")
    if active_milestone and active_milestone != "none":
        active_entry = by_id.get(active_milestone)
        if active_entry is None:
            report.add_failure(
                "runtime artifact consistency: control-state active_milestone "
                f"{active_milestone} is missing from milestone backlog"
            )
        elif active_entry.get("status") != "active":
            report.add_failure(
                "runtime artifact consistency: control-state active_milestone "
                f"{active_milestone} points to non-active milestone status {active_entry.get('status')!r}"
            )
        elif milestone_status and milestone_status != "active":
            report.add_failure(
                "runtime artifact consistency: control-state milestone_status does not match active milestone"
            )
    elif active_entries:
        report.add_failure(
            "runtime artifact consistency: milestone backlog has active milestone but control-state active_milestone is none"
        )

    summary = _parse_pipeline_summary(control.get("milestone_pipeline_summary", ""))
    if summary is None:
        report.add_failure("runtime artifact consistency: control-state milestone_pipeline_summary is missing or malformed")
    elif summary != counts:
        report.add_failure(
            "runtime artifact consistency: milestone_pipeline_summary mismatch: "
            f"control-state={summary}, backlog={counts}"
        )

    report.add_info(f"checked {len(entries)} runtime milestone entries for consistency")


def _is_readme_or_excluded(rel_path: str) -> bool:
    """Check if a doc path is a README, in archive/, or in ideas/."""
    if rel_path.endswith("/README.md"):
        return True
    if rel_path == "docs/README.md":
        return True
    for excluded_dir in ORPHAN_DOC_EXCLUDED_DIRS:
        if rel_path.startswith(excluded_dir):
            return True
    return False


def _collect_docs_referenced_targets(repo_root: Path) -> tuple[set[str], list[str]]:
    """Collect all relative markdown link targets from reference sources.

    Scans: all docs/**/*.md, root reference sources, and canonical skills.
    Returns a tuple of (referenced targets, substantive doc paths).
    The second element eliminates the need for a separate rglob in
    ``check_orphan_docs``.
    """
    referenced: set[str] = set()
    all_docs: list[str] = []

    # Scan all .md files under docs/
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for md_file in sorted(docs_dir.rglob("*.md")):
            try:
                rel = to_relative_posix(md_file, repo_root)
            except ValueError:
                continue
            if not _is_readme_or_excluded(rel):
                all_docs.append(rel)
            try:
                targets = collect_repo_relative_markdown_links(repo_root, rel)
            except Exception:
                continue
            referenced.update(targets)

    # Scan root reference sources (CLAUDE.md, AGENTS.md)
    for source in ORPHAN_REFERENCE_SOURCES:
        source_path = repo_root / source
        if source_path.is_file():
            try:
                targets = collect_repo_relative_markdown_links(repo_root, source)
            except Exception:
                continue
            referenced.update(targets)

    # Scan canonical skill bodies. A doc referenced only by a canonical skill is
    # still reachable operator-facing truth and must not be reported as orphaned.
    for glob_pattern in ORPHAN_SKILL_REFERENCE_GLOBS:
        for source_path in sorted(repo_root.glob(glob_pattern)):
            if not source_path.is_file():
                continue
            try:
                source = to_relative_posix(source_path, repo_root)
            except ValueError:
                continue
            try:
                targets = collect_repo_relative_markdown_links(repo_root, source)
            except Exception:
                continue
            referenced.update(targets)

    return referenced, all_docs


def check_orphan_docs(repo_root: Path, report: SemanticReport) -> None:
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        report.add_info("checked 0 docs for orphan status, docs/ directory missing")
        return

    # Single traversal: collects both referenced targets and substantive doc paths
    referenced, all_docs = _collect_docs_referenced_targets(repo_root)

    if not all_docs:
        report.add_info("checked 0 docs for orphan status, no substantive docs found")
        return

    # Find orphans: docs not referenced by any source
    orphans: list[str] = []
    for doc_rel in all_docs:
        if doc_rel not in referenced:
            orphans.append(doc_rel)

    if orphans:
        report.add_failure(f"{len(orphans)} orphan docs found:")
        for doc_rel in orphans:
            report.add_failure(f"  {doc_rel} (0 references)")
    report.add_info(f"checked {len(all_docs)} docs for orphan status, {len(orphans)} orphans found")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    report = SemanticReport()
    check_required_templates(repo_root, report)
    check_required_handoffs(repo_root, report)
    check_foundations_authority_shadows(repo_root, report)
    check_outdated_placeholder_phrases(repo_root, report)
    check_retired_entrypoint_references(repo_root, report)
    check_canonical_skill_packages_are_minimal(repo_root, report)
    check_adapter_wrappers_are_thin(repo_root, report)
    check_append_request_contract_terms(repo_root, report)
    check_repo_python_commands_are_bytecode_free(repo_root, report)
    check_root_tool_shims_disable_bytecode(repo_root, report)
    check_agents_route_slimming_contract(repo_root, report)
    check_path_governance_docs_list_gitignore_entries(repo_root, report)
    check_review_verify_docs_list_closeout_steps(repo_root, report)
    check_docs_list_closeout_cache_roots(repo_root, report)
    check_manual_runbook_agents_skill_count(repo_root, report)
    check_subagent_dispatch_default_contract(repo_root, report)
    check_dispatch_context_contract(repo_root, report)
    check_runtime_dispatch_profile_contract(repo_root, report)
    check_review_evidence_four_lane_contract(repo_root, report)
    check_debug_evidence_contract(repo_root, report)
    check_decision_traceability_contract(repo_root, report)
    check_closeout_record_contract(repo_root, report)
    check_repo_whats_next_overview_fallback_contract(repo_root, report)
    check_worktrack_intake_review_contract(repo_root, report)
    check_artifact_skill_alignment(repo_root, report)
    check_runtime_artifact_consistency(repo_root, report)
    check_orphan_docs(repo_root, report)

    payload = {
        "passed": not report.failures,
        "failures": report.failures,
        "warnings": report.warnings,
        "infos": report.infos,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for info in report.infos:
            print(f"info: {info}")
        for warning in report.warnings:
            print(f"warn: {warning}")
        if report.failures:
            for failure in report.failures:
                print(f"failure: {failure}")
        else:
            print("governance semantic checks passed")

    return 0 if not report.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
