#!/usr/bin/env python3
"""Report-only backlog cleanup compatibility helper.

This helper is intentionally package-local. It does not delegate to source
repo paths or installed deploy targets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DONE_STATUS_MARKERS = ("status: done", "status: resolved", "[done]", "[resolved]")


def count_markers(path: Path) -> dict[str, int | bool | str]:
    if not path.is_file():
        return {
            "path": path.as_posix(),
            "exists": False,
            "worktrack_id_count": 0,
            "done_like_count": 0,
        }
    text = path.read_text(encoding="utf-8")
    return {
        "path": path.as_posix(),
        "exists": True,
        "worktrack_id_count": text.count("worktrack_id:"),
        "done_like_count": sum(text.count(marker) for marker in DONE_STATUS_MARKERS),
    }


def build_report(servo_root: Path, apply: bool) -> dict[str, object]:
    repo_root = servo_root / "repo"
    return {
        "cleanup_type": "backlog_only",
        "report_mode": "blocked_apply" if apply else "dry_run",
        "cleanup_executed": False,
        "apply_requested": apply,
        "apply_allowed": False,
        "block_reason": (
            "legacy worktrack cleanup helper is report-only; use "
            "milestone-cleanup-skill with explicit approval for apply"
            if apply
            else "N/A"
        ),
        "backlog": count_markers(repo_root / "worktrack-backlog.md"),
        "history": count_markers(repo_root / "worktrack-history.md"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servo-root", default=".servo")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(Path(args.servo_root), args.apply)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"cleanup_type: {report['cleanup_type']}")
        print(f"report_mode: {report['report_mode']}")
        print(f"cleanup_executed: {str(report['cleanup_executed']).lower()}")
    return 2 if args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
