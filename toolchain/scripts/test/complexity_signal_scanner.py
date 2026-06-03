#!/usr/bin/env python3
"""Repo-local wrapper for the distributable complexity signal scanner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SCANNER = (
    REPO_ROOT
    / "product"
    / "harness"
    / "skills"
    / "set-harness-goal-skill"
    / "scripts"
    / "complexity_signal_scanner.py"
)

_spec = importlib.util.spec_from_file_location(
    "servo_complexity_signal_scanner",
    CANONICAL_SCANNER,
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load complexity signal scanner: {CANONICAL_SCANNER}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

EVIDENCE_DISCLAIMER = _module.EVIDENCE_DISCLAIMER
scan_repo = _module.scan_repo
main = _module.main


if __name__ == "__main__":
    raise SystemExit(main())
