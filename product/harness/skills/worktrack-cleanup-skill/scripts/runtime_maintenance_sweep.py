#!/usr/bin/env python3
"""Report-first maintenance sweep for .servo runtime artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SERVO_REF_PATTERN = re.compile(r"(?<![A-Za-z0-9_./-])\.servo/[A-Za-z0-9_./#@:-]+")
FIELD_PATTERN = re.compile(r"^\s*-\s*([A-Za-z0-9_.-]+)\s*:\s*(.*)$")
WORKTRACK_ID_PATTERN = re.compile(r"^\s*-\s*worktrack_id\s*:\s*(.+?)\s*$")
MILESTONE_ID_PATTERN = re.compile(r"^\s*-\s*milestone_id\s*:\s*(.+?)\s*$")
STATUS_PATTERN = re.compile(r"^\s*-\s*status\s*:\s*(.+?)\s*$")
PRIMARY_MILESTONE_ARTIFACT_PATTERN = re.compile(
    r"^MS-(?:\d{8}-\d{3}|\d{3}|LEGACY)\.md$"
)
TEXT_FILE_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}
DONE_STATUSES = {"done", "completed", "resolved", "closed"}
LIVE_MILESTONE_STATUSES = {"planned", "active"}
HISTORY_MILESTONE_STATUSES = {"completed", "superseded"}
ALL_MILESTONE_STATUSES = LIVE_MILESTONE_STATUSES | HISTORY_MILESTONE_STATUSES
TEMP_MARKERS = ("discovery", "scratch", "tmp", "temp", "temporary")
LIFECYCLE_TERMS = (
    "promoted",
    "retired",
    "archived",
    "archive_path",
    "preserved",
    "superseded",
    "stale",
    "expired",
    "closeout",
    "evidence_ref",
)
ENTRYPOINT_FILES = {
    ".servo/control-state.md",
    ".servo/control-state-repo.md",
    ".servo/control-state-wt.md",
    ".servo/operator-config.md",
}
ENTRYPOINT_PREFIXES = (
    ".servo/repo/",
    ".servo/milestone/",
    ".servo/worktrack/",
)
EXPECTED_TOP_LEVEL_DIRS = {
    "archive",
    "history",
    "milestone",
    "repo",
    "worktrack",
}


@dataclass(frozen=True)
class Finding:
    finding_type: str
    severity: str
    path: str
    message: str
    evidence: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "type": self.finding_type,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "evidence": self.evidence,
        }


def normalize_ref(raw_ref: str) -> str:
    ref = raw_ref.strip().rstrip(".,;:)]}'\"`")
    ref = ref.split("#", 1)[0]
    ref = re.sub(r"(\.[A-Za-z0-9]+):\d+(?:-\d+)?$", r"\1", ref)
    return ref


def looks_like_file_ref(ref: str) -> bool:
    suffix = Path(ref).suffix.lower()
    return suffix in TEXT_FILE_SUFFIXES


def repo_ref(path: Path, servo_root: Path) -> str:
    return f".servo/{path.relative_to(servo_root).as_posix()}"


def resolve_ref(ref: str, repo_root: Path) -> Path:
    return repo_root / ref


def text_files(servo_root: Path) -> list[Path]:
    return sorted(
        path
        for path in servo_root.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_FILE_SUFFIXES
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_refs(text: str) -> set[str]:
    return {normalize_ref(match.group(0)) for match in SERVO_REF_PATTERN.finditer(text)}


def parse_fields(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = FIELD_PATTERN.match(line)
        if match:
            key = match.group(1)
            value = match.group(2).strip().strip('"').strip("'")
            fields.setdefault(key, []).append(value)
    return fields


def parse_worktrack_backlog(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []

    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in read_text(path).splitlines():
        worktrack_match = WORKTRACK_ID_PATTERN.match(line)
        if worktrack_match:
            if current:
                entries.append(current)
            current = {"worktrack_id": worktrack_match.group(1).strip()}
            continue

        if current is None:
            continue

        milestone_match = MILESTONE_ID_PATTERN.match(line)
        status_match = STATUS_PATTERN.match(line)
        field_match = FIELD_PATTERN.match(line)
        if milestone_match:
            current["milestone_id"] = milestone_match.group(1).strip()
        elif status_match:
            current["status"] = status_match.group(1).strip()
        elif field_match:
            current[field_match.group(1)] = field_match.group(2).strip()

    if current:
        entries.append(current)
    return entries


def parse_milestone_backlog(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []

    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_worktrack_list = False
    for line in read_text(path).splitlines():
        if line.startswith("- milestone_id:"):
            if current:
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
            elif stripped.startswith("- continuation_state:"):
                current["continuation_state"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- milestone_branch:"):
                current["milestone_branch"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- verdict:") and "accepted" in stripped:
                current["accepted"] = True
            elif stripped.startswith("- acceptance:"):
                current["accepted"] = True
            continue

        if in_worktrack_list and line.startswith("    - "):
            worktracks = current["worktrack_list"]
            assert isinstance(worktracks, list)
            worktracks.append(stripped.removeprefix("- ").strip())

    if current:
        entries.append(current)
    return entries


def parse_control_pipeline_fields(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    fields: dict[str, str] = {}
    current_section = ""
    for line in read_text(path).splitlines():
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            continue
        if current_section != "Milestone Pipeline":
            continue
        stripped = line.strip()
        for key in ("active_milestone", "milestone_status", "milestone_pipeline_summary"):
            prefix = f"- {key}:"
            if stripped.startswith(prefix):
                fields[key] = stripped.removeprefix(prefix).strip()
    return fields


def parse_primary_milestone_artifacts(servo_root: Path) -> dict[str, dict[str, str]]:
    milestone_dir = servo_root / "milestone"
    artifacts: dict[str, dict[str, str]] = {}
    if not milestone_dir.is_dir():
        return artifacts

    for path in sorted(milestone_dir.glob("MS-*.md")):
        if not PRIMARY_MILESTONE_ARTIFACT_PATTERN.fullmatch(path.name):
            continue
        milestone_id = path.stem
        status = ""
        for line in read_text(path).splitlines():
            stripped = line.strip()
            if stripped.startswith("milestone_id:") and milestone_id == path.stem:
                milestone_id = stripped.split(":", 1)[1].strip().strip('"')
            elif stripped.startswith("status:") and not status:
                status = stripped.split(":", 1)[1].strip().strip('"')
        artifacts[milestone_id] = {
            "milestone_id": milestone_id,
            "status": status,
            "path": repo_ref(path, servo_root),
        }
    return artifacts


def is_entrypoint(ref: str) -> bool:
    return ref in ENTRYPOINT_FILES or any(ref.startswith(prefix) for prefix in ENTRYPOINT_PREFIXES)


def top_level_dir(ref: str) -> str:
    parts = ref.split("/")
    if len(parts) >= 3:
        return parts[1]
    return ""


def find_stale_refs(
    *,
    repo_root: Path,
    refs_by_file: dict[str, set[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    for source_ref, refs in refs_by_file.items():
        for ref in sorted(refs):
            if "*" in ref or "..." in ref:
                continue
            if not looks_like_file_ref(ref):
                continue
            if not resolve_ref(ref, repo_root).exists():
                findings.append(
                    Finding(
                        finding_type="stale_reference",
                        severity="medium",
                        path=source_ref,
                        message=f"Reference points to a missing .servo artifact: {ref}",
                        evidence={"missing_ref": ref},
                    )
                )
    return findings


def find_rolling_evidence_reuse(entries: Sequence[dict[str, object]]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in entries:
        status = str(entry.get("status", "")).strip().lower()
        evidence_ref = str(entry.get("evidence_ref", "")).strip()
        if status not in DONE_STATUSES:
            continue
        if not evidence_ref.startswith(".servo/worktrack/gate-evidence.md"):
            continue

        stable_refs = (
            str(entry.get("closeout_record_ref", "")).strip(),
            str(entry.get("closeout_evidence_bundle_ref", "")).strip(),
            str(entry.get("snapshot_ref", "")).strip(),
            str(entry.get("archive_ref", "")).strip(),
        )
        bundle_status = str(entry.get("closeout_bundle_status", "")).strip().lower()
        has_stable_ref = any(ref and ref != "N/A" for ref in stable_refs)
        has_complete_bundle = bundle_status in {"complete", "snapshot_complete", "archived"}
        if not has_stable_ref and not has_complete_bundle:
            findings.append(
                Finding(
                    finding_type="rolling_evidence_reuse",
                    severity="high",
                    path=".servo/repo/worktrack-backlog.md",
                    message=(
                        "Closed Worktrack references rolling .servo/worktrack/gate-evidence.md "
                        "without a stable closeout record, bundle, snapshot, or archive ref."
                    ),
                    evidence={
                        "worktrack_id": entry.get("worktrack_id", "unknown"),
                        "evidence_ref": evidence_ref,
                    },
                )
            )
    return findings


def find_orphans(
    *,
    inventory: set[str],
    referenced: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    for ref in sorted(inventory):
        if ref in referenced or is_entrypoint(ref):
            continue
        top_dir = top_level_dir(ref)
        if top_dir not in EXPECTED_TOP_LEVEL_DIRS:
            findings.append(
                Finding(
                    finding_type="orphan_artifact",
                    severity="medium",
                    path=ref,
                    message="Artifact is outside recognized .servo runtime layers and is not referenced.",
                    evidence={"top_level_dir": top_dir or "root"},
                )
            )
        elif ref.startswith(".servo/archive/") and not is_archive_manifest_or_referenced(ref, referenced):
            findings.append(
                Finding(
                    finding_type="orphan_archive_artifact",
                    severity="low",
                    path=ref,
                    message="Archived artifact is not referenced and is not an archive manifest.",
                    evidence={"archive_ref": ref},
                )
            )
    return findings


def is_archive_manifest_or_referenced(ref: str, referenced: set[str]) -> bool:
    name = Path(ref).name
    return ref in referenced or name in {"archive-manifest.md", "manifest.md"}


def find_temporary_lifecycle_gaps(
    *,
    file_texts: dict[str, str],
    referenced: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    for ref, text in sorted(file_texts.items()):
        normalized = ref.lower()
        if not any(marker in normalized for marker in TEMP_MARKERS):
            continue
        if ref in referenced:
            continue
        lowered_text = text.lower()
        if any(term in lowered_text for term in LIFECYCLE_TERMS):
            continue
        findings.append(
            Finding(
                finding_type="temporary_lifecycle_gap",
                severity="medium",
                path=ref,
                message=(
                    "Temporary discovery/evidence artifact is not referenced and does not "
                    "declare promoted, retired, archived, preserved, stale, or expired status."
                ),
                evidence={"lifecycle_terms_found": []},
            )
        )
    return findings


def find_prose_only_execution_evidence(file_texts: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    for ref, text in sorted(file_texts.items()):
        lowered = text.lower()
        mentions_execution_output = (
            "subagent" in lowered
            or "command-output" in lowered
            or "command output" in lowered
        )
        if not mentions_execution_output:
            continue
        refs = extract_refs(text)
        has_execution_ref = any(
            candidate.startswith(".servo/archive/subagent/")
            or candidate.startswith(".servo/archive/command-output/")
            or "/subagent/" in candidate
            or "/command-output/" in candidate
            for candidate in refs
        )
        if not has_execution_ref and ("raw output" in lowered or "command output" in lowered):
            findings.append(
                Finding(
                    finding_type="prose_only_execution_evidence",
                    severity="low",
                    path=ref,
                    message=(
                        "SubAgent or command-output evidence is described in prose without "
                        "a concrete runtime artifact reference."
                    ),
                    evidence={"execution_ref_found": False},
                )
            )
    return findings


def find_milestone_backlog_history_gaps(
    *,
    servo_root: Path,
    live_entries: Sequence[dict[str, object]],
    history_entries: Sequence[dict[str, object]],
) -> list[Finding]:
    findings: list[Finding] = []
    live_by_id = {str(entry.get("milestone_id", "")): entry for entry in live_entries}
    history_by_id = {str(entry.get("milestone_id", "")): entry for entry in history_entries}
    artifacts = parse_primary_milestone_artifacts(servo_root)

    for milestone_id, entry in sorted(live_by_id.items()):
        status = str(entry.get("status", "")).strip()
        if status and status not in ALL_MILESTONE_STATUSES:
            findings.append(
                Finding(
                    finding_type="milestone_invalid_status",
                    severity="high",
                    path=".servo/repo/milestone-backlog.md",
                    message=(
                        f"Live milestone backlog entry {milestone_id} uses invalid primary "
                        f"status {status!r}; use continuation_state for waiting/paused semantics."
                    ),
                    evidence={"milestone_id": milestone_id, "status": status},
                )
            )
        if status in HISTORY_MILESTONE_STATUSES:
            findings.append(
                Finding(
                    finding_type="milestone_live_history_status",
                    severity="high",
                    path=".servo/repo/milestone-backlog.md",
                    message=(
                        f"Live milestone backlog contains history status {status!r} "
                        f"for {milestone_id}; move it to milestone-history."
                    ),
                    evidence={"milestone_id": milestone_id, "status": status},
                )
            )
            if milestone_id not in history_by_id:
                findings.append(
                    Finding(
                        finding_type="milestone_missing_history_record",
                        severity="high",
                        path=".servo/repo/milestone-history.md",
                        message=(
                            f"Completed/superseded milestone {milestone_id} is not recorded "
                            "in milestone-history."
                        ),
                        evidence={"milestone_id": milestone_id, "source": "live_backlog"},
                    )
                )

    for milestone_id, entry in sorted(history_by_id.items()):
        status = str(entry.get("status", "")).strip()
        if milestone_id in live_by_id:
            findings.append(
                Finding(
                    finding_type="milestone_live_history_overlap",
                    severity="high",
                    path=".servo/repo/milestone-history.md",
                    message=f"Milestone {milestone_id} exists in both live backlog and history.",
                    evidence={"milestone_id": milestone_id},
                )
            )
        if status and status not in ALL_MILESTONE_STATUSES:
            findings.append(
                Finding(
                    finding_type="milestone_invalid_status",
                    severity="high",
                    path=".servo/repo/milestone-history.md",
                    message=(
                        f"Milestone-history entry {milestone_id} uses invalid primary "
                        f"status {status!r}; use continuation_state for waiting/paused semantics."
                    ),
                    evidence={"milestone_id": milestone_id, "status": status},
                )
            )
        if status in LIVE_MILESTONE_STATUSES:
            findings.append(
                Finding(
                    finding_type="milestone_history_live_status",
                    severity="high",
                    path=".servo/repo/milestone-history.md",
                    message=(
                        f"Milestone-history contains live status {status!r} for {milestone_id}; "
                        "keep planned/active entries in milestone-backlog."
                    ),
                    evidence={"milestone_id": milestone_id, "status": status},
                )
            )
        if status in HISTORY_MILESTONE_STATUSES or entry.get("accepted") is True:
            worktracks = entry.get("worktrack_list", [])
            if isinstance(worktracks, list):
                stale_markers = [
                    str(worktrack)
                    for worktrack in worktracks
                    if re.search(r"\((planned|active)\)", str(worktrack))
                ]
                if stale_markers:
                    findings.append(
                        Finding(
                            finding_type="milestone_history_unfinished_worktrack_marker",
                            severity="medium",
                            path=".servo/repo/milestone-history.md",
                            message=(
                                f"Completed/accepted milestone {milestone_id} retains "
                                "planned/active worktrack markers."
                            ),
                            evidence={
                                "milestone_id": milestone_id,
                                "worktrack_markers": stale_markers,
                            },
                        )
                    )

    for milestone_id, artifact in sorted(artifacts.items()):
        status = str(artifact.get("status", "")).strip()
        live_status = str(live_by_id.get(milestone_id, {}).get("status", "")).strip()
        already_reported_from_live = live_status in HISTORY_MILESTONE_STATUSES
        if (
            status in HISTORY_MILESTONE_STATUSES
            and milestone_id not in history_by_id
            and not already_reported_from_live
        ):
            findings.append(
                Finding(
                    finding_type="milestone_missing_history_record",
                    severity="medium",
                    path=str(artifact.get("path", ".servo/milestone")),
                    message=(
                        f"Completed/superseded milestone artifact {milestone_id} has no "
                        "milestone-history entry."
                    ),
                    evidence={"milestone_id": milestone_id, "source": "milestone_artifact"},
                )
            )

    control = parse_control_pipeline_fields(servo_root / "control-state.md")
    active_milestone = control.get("active_milestone", "")
    if active_milestone and active_milestone != "none":
        live_entry = live_by_id.get(active_milestone)
        if live_entry is None:
            findings.append(
                Finding(
                    finding_type="milestone_active_pointer_stale",
                    severity="high",
                    path=".servo/control-state.md",
                    message=(
                        f"control-state active_milestone {active_milestone} is not present "
                        "as a live milestone-backlog entry."
                    ),
                    evidence={"active_milestone": active_milestone},
                )
            )
        elif str(live_entry.get("status", "")).strip() != "active":
            findings.append(
                Finding(
                    finding_type="milestone_active_pointer_non_active",
                    severity="high",
                    path=".servo/control-state.md",
                    message=(
                        f"control-state active_milestone {active_milestone} points to "
                        f"live status {live_entry.get('status')!r}, not 'active'."
                    ),
                    evidence={
                        "active_milestone": active_milestone,
                        "status": live_entry.get("status", ""),
                    },
                )
            )

    return findings


def sweep(servo_root: Path) -> dict[str, object]:
    servo_root = servo_root.resolve()
    repo_root = servo_root.parent
    files = text_files(servo_root)
    file_texts = {repo_ref(path, servo_root): read_text(path) for path in files}
    refs_by_file = {ref: extract_refs(text) for ref, text in file_texts.items()}
    referenced = {ref for refs in refs_by_file.values() for ref in refs}
    inventory = set(file_texts)
    worktrack_entries = parse_worktrack_backlog(servo_root / "repo" / "worktrack-backlog.md")
    milestone_live_entries = parse_milestone_backlog(
        servo_root / "repo" / "milestone-backlog.md"
    )
    milestone_history_entries = parse_milestone_backlog(
        servo_root / "repo" / "milestone-history.md"
    )

    findings: list[Finding] = []
    findings.extend(find_stale_refs(repo_root=repo_root, refs_by_file=refs_by_file))
    findings.extend(find_rolling_evidence_reuse(worktrack_entries))
    findings.extend(find_orphans(inventory=inventory, referenced=referenced))
    findings.extend(find_temporary_lifecycle_gaps(file_texts=file_texts, referenced=referenced))
    findings.extend(find_prose_only_execution_evidence(file_texts))
    findings.extend(
        find_milestone_backlog_history_gaps(
            servo_root=servo_root,
            live_entries=milestone_live_entries,
            history_entries=milestone_history_entries,
        )
    )

    finding_dicts = [finding.as_dict() for finding in findings]
    counts_by_type: dict[str, int] = {}
    counts_by_severity: dict[str, int] = {}
    for finding in finding_dicts:
        finding_type = str(finding["type"])
        severity = str(finding["severity"])
        counts_by_type[finding_type] = counts_by_type.get(finding_type, 0) + 1
        counts_by_severity[severity] = counts_by_severity.get(severity, 0) + 1

    return {
        "servo_root": f".servo" if servo_root.name == ".servo" else servo_root.as_posix(),
        "mode": "report",
        "cleanup_executed": False,
        "artifact_count": len(inventory),
        "referenced_artifact_count": len(referenced),
        "worktrack_entry_count": len(worktrack_entries),
        "milestone_entry_count": len(milestone_live_entries)
        + len(milestone_history_entries),
        "finding_count": len(finding_dicts),
        "counts_by_type": counts_by_type,
        "counts_by_severity": counts_by_severity,
        "findings": finding_dicts,
        "recommendations": [
            "Review findings before any archive, move, or deletion action.",
            "Generate stable snapshots or closeout bundles before relying on rolling Worktrack evidence.",
            "Promote only verified long-term facts into docs; keep runtime records under .servo lifecycle control.",
        ],
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servo-root", default=".servo", help="Path to the .servo root")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when findings are reported",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    servo_root = Path(args.servo_root)
    if not servo_root.is_dir():
        payload = {
            "mode": "report",
            "cleanup_executed": False,
            "blocked": True,
            "errors": [f"servo root does not exist: {servo_root.as_posix()}"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    report = sweep(servo_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "runtime maintenance sweep: "
            f"{report['finding_count']} findings across {report['artifact_count']} artifacts"
        )
        for finding in report["findings"]:
            print(f"- [{finding['severity']}] {finding['type']}: {finding['path']}")

    if args.fail_on_findings and report["finding_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
