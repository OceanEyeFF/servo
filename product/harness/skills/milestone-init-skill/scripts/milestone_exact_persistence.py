#!/usr/bin/env python3
"""Symlink-safe reads and exact-byte roll-forward persistence."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn


MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


class PersistenceError(Exception):
    """A deterministic file or persistence failure with located details."""

    def __init__(self, code: str, message: str | None = None, **details: Any) -> None:
        message = message or code.replace("_", " ")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def fail(code: str, message: str | None = None, **details: Any) -> NoReturn:
    raise PersistenceError(code, message, **details)


def require(predicate: object, code: str, message: str | None = None, **details: Any) -> None:
    if not predicate:
        fail(code, message, **details)


@dataclass(frozen=True)
class PersistenceResult:
    replaced: bool
    exact_readback: bool


def safe_read_regular(path: Path, *, missing_ok: bool) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        fail("missing_file", "required file is missing", path=str(path))
    require(
        not stat.S_ISLNK(metadata.st_mode) and stat.S_ISREG(metadata.st_mode),
        "unsafe_file_type",
        path=str(path),
    )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        fail("unsafe_file_read", path=str(path))
    try:
        opened = os.fstat(descriptor)
        require(
            (opened.st_dev, opened.st_ino) == (metadata.st_dev, metadata.st_ino),
            "unsafe_file_read",
            path=str(path),
        )
        require(stat.S_ISREG(opened.st_mode), "unsafe_file_type", path=str(path))
        require(
            opened.st_size <= MAX_DOCUMENT_BYTES,
            "document_too_large",
            path=str(path),
        )
        chunks: list[bytes] = []
        remaining = MAX_DOCUMENT_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        require(len(data) <= MAX_DOCUMENT_BYTES, "document_too_large", path=str(path))
        return data
    finally:
        os.close(descriptor)


def write_temp(milestone_dir: Path, milestone_id: str, raw: bytes) -> Path:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{milestone_id}.",
        suffix=".tmp",
        dir=milestone_dir,
    )
    path = Path(temp_name)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while persisting Milestone document")
            view = view[written:]
        os.fsync(descriptor)
    except Exception:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    os.close(descriptor)
    return path


def fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def inject_failure(point: str | None, expected: str) -> None:
    if point == expected:
        fail("injected_failure", "test-only failure injection", failure_point=expected)


def observed_exact_bytes(target: Path, approved_bytes: bytes) -> bool:
    try:
        return safe_read_regular(target, missing_ok=True) == approved_bytes
    except PersistenceError:
        return False


def verify_exact_bytes(target: Path, approved_bytes: bytes, *, mismatch_code: str) -> None:
    readback = safe_read_regular(target, missing_ok=False)
    require(readback == approved_bytes, mismatch_code, "canonical readback does not match approved bytes")


def persist_exact_bytes(
    target: Path,
    approved_bytes: bytes,
    expected_current_bytes: bytes | None,
    *,
    failure_point: str | None = None,
) -> PersistenceResult:
    """Replace exact bytes; pre-commit failures clean temp, post-commit failures roll forward."""
    temp_path: Path | None = None
    replaced = False
    try:
        temp_path = write_temp(target.parent, target.stem, approved_bytes)
        inject_failure(failure_point, "before-replace")
        latest_raw = safe_read_regular(target, missing_ok=True)
        require(latest_raw == expected_current_bytes, "stale_compare_and_swap")
        os.replace(temp_path, target)
        temp_path = None
        replaced = True
        fsync_directory(target.parent)
        inject_failure(failure_point, "after-replace")
        verify_exact_bytes(target, approved_bytes, mismatch_code="readback_mismatch")
        return PersistenceResult(replaced=True, exact_readback=True)
    except Exception as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        details = {
            "commit_point": "after_replace" if replaced else "before_replace",
            "roll_forward_required": replaced,
            "document_written": observed_exact_bytes(target, approved_bytes),
        }
        if isinstance(exc, PersistenceError):
            exc.details.update(details)
            raise
        fail("transaction_failure", error=str(exc), **details)
