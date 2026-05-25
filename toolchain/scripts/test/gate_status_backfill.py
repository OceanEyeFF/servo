#!/usr/bin/env python3
"""Backfill closeout gate status into harness state and closeout artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def default_backfill_root(repo_root: Path = REPO_ROOT) -> Path:
    repo_path = repo_root.resolve()
    repo_key = hashlib.sha256(str(repo_path).encode("utf-8")).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / "servo-closeout" / f"{repo_path.name}-{repo_key}"


DEFAULT_BACKFILL_ROOT = default_backfill_root()
DEFAULT_STATE_FILE = DEFAULT_BACKFILL_ROOT / "state" / "harness-task-list.json"
DEFAULT_CLOSEOUT_ROOT = DEFAULT_BACKFILL_ROOT / "closeout"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill a gate result into harness state.")
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--status", required=True, choices=("passed", "failed", "blocked", "partial", "skipped"))
    parser.add_argument("--details", default="{}")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Harness state file to update.",
    )
    parser.add_argument(
        "--closeout-root",
        type=Path,
        default=DEFAULT_CLOSEOUT_ROOT,
        help="Directory used for persisted closeout records.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the intended backfill without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON only.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_state(state: dict, gate: str, status: str, details: dict, workflow_id: str) -> dict:
    same_workflow = state.get("workflow_id") in (None, workflow_id)
    updated_state = dict(state) if same_workflow else {}
    updated_state["workflow_id"] = workflow_id
    updated_state["gates"] = dict(state.get("gates", {})) if same_workflow else {}
    updated_state["gates"][gate] = status
    updated_state["last_backfill"] = {
        "workflow_id": workflow_id,
        "gate": gate,
        "status": status,
        "details": details,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return updated_state


def main() -> int:
    args = parse_args()
    details = json.loads(args.details)
    state = load_json(args.state_file)
    updated_state = update_state(state, args.gate, args.status, details, args.workflow_id)

    closeout_dir = args.closeout_root / args.workflow_id
    gate_record = {
        "workflow_id": args.workflow_id,
        "gate": args.gate,
        "status": args.status,
        "details": details,
        "updated_at": updated_state["last_backfill"]["updated_at"],
    }
    summary_record = {
        "workflow_id": args.workflow_id,
        "gates": updated_state.get("gates", {}),
        "last_backfill": updated_state["last_backfill"],
    }

    write_json(args.state_file, updated_state, args.dry_run)
    write_json(closeout_dir / "gates" / f"{args.gate}.json", gate_record, args.dry_run)
    write_json(closeout_dir / "summary.json", summary_record, args.dry_run)

    payload = {
        "state_file": str(args.state_file),
        "closeout_root": str(closeout_dir),
        "gate_record": gate_record,
        "summary_record": summary_record,
        "dry_run": args.dry_run,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
