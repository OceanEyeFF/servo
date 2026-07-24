#!/usr/bin/env python3
"""Public CLI orchestration for exact approved Milestone document transactions."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, NoReturn

import milestone_document_check as document_check
import milestone_exact_persistence as exact_persistence
import milestone_repository as repository


DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class TransactionError(Exception):
    """A deterministic public failure with located details."""

    def __init__(self, code: str, message: str | None = None, **details: Any) -> None:
        message = message or code.replace("_", " ")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def fail(code: str, message: str | None = None, **details: Any) -> NoReturn:
    raise TransactionError(code, message, **details)


def require(predicate: object, code: str, message: str | None = None, **details: Any) -> None:
    """Fail with one public diagnostic unless a deterministic condition holds."""
    if not predicate:
        fail(code, message, **details)


CONFLICT_ERROR_CODES = set(
    """amend_mode_required amendment_history_change baseline_branch_conflict
    branch_contract_conflict branch_ref_conflict branch_ref_race canonical_identity_conflict
    expected_state_mismatch missing_current_document missing_milestone_branch
    same_revision_conflict skipped_revision stale_compare_and_swap stale_revision""".split()
)
BLOCKED_ERROR_CODES = set(
    """checkout_changed final_acceptance_authority_violation git_error injected_failure
    invalid_repo_root lifecycle_authority_violation milestone_id_change missing_approval_ref
    missing_baseline_commit missing_close_target missing_milestone_directory readback_mismatch
    result_authority_violation test_failure_not_enabled transaction_failure unsafe_current_branch
    unsafe_file_read unsafe_file_type unsafe_milestone_directory unsafe_stable_ref""".split()
)


def signal_for_error(code: str) -> str:
    return "conflict" if code in CONFLICT_ERROR_CODES else "blocked" if code in BLOCKED_ERROR_CODES else "invalid"


PUBLIC_ERRORS = (
    TransactionError,
    document_check.DocumentCheckError,
    repository.RepositoryError,
    exact_persistence.PersistenceError,
)


def json_out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def classify_candidate(
    candidate: document_check.Document,
    current_raw: bytes | None,
    mode: str,
) -> tuple[str, document_check.Document | None]:
    if current_raw is None:
        if mode == "amend":
            fail("missing_current_document")
        return "create", None
    current = document_check.parse_document(current_raw, "existing")
    require(
        candidate.milestone_id == current.milestone_id,
        "canonical_identity_conflict",
        current=current.milestone_id,
        candidate=candidate.milestone_id,
    )
    if candidate.revision == current.revision and candidate.raw == current.raw:
        return "already_applied", current
    require(
        candidate.revision != current.revision,
        "same_revision_conflict",
        revision=candidate.revision,
        current_digest=current.digest,
        candidate_digest=candidate.digest,
    )
    require(
        candidate.revision >= current.revision,
        "stale_revision",
        current_revision=current.revision,
        candidate_revision=candidate.revision,
    )
    require(
        candidate.revision <= current.revision + 1,
        "skipped_revision",
        current_revision=current.revision,
        candidate_revision=candidate.revision,
    )
    require(
        mode == "amend",
        "amend_mode_required",
        current_revision=current.revision,
        candidate_revision=candidate.revision,
    )
    return "amend", current


def validate_expected_state(
    action: str,
    candidate: document_check.Document,
    current: document_check.Document | None,
    expected_revision: int,
    expected_digest: str,
) -> None:
    if action == "create":
        require(
            expected_revision == 0 and expected_digest == "absent",
            "expected_state_mismatch",
        )
        return
    require(current is not None, "expected_state_mismatch", "current document is missing")
    assert current is not None
    if action == "amend":
        require(
            expected_revision == current.revision and expected_digest == current.digest,
            "stale_compare_and_swap",
            expected_revision=expected_revision,
            actual_revision=current.revision,
            expected_digest=expected_digest,
            actual_digest=current.digest,
        )
        return
    # Safe repeat accepts a verifiable now-current state. Revision-1 create may
    # also replay its only legal prior state (absence). A prior amend digest is
    # not retained by this stateless exact-byte worker, so accepting one by shape
    # alone would bypass expected-state validation; callers must reread current
    # state before an amend roll-forward retry.
    current_state = expected_revision == current.revision and expected_digest == current.digest
    create_prior = (
        current.revision == 1 and expected_revision == 0 and expected_digest == "absent"
    )
    require(
        current_state or create_prior,
        "stale_compare_and_swap",
        expected_revision=expected_revision,
        actual_revision=current.revision,
        expected_digest=expected_digest,
        actual_digest=current.digest,
        candidate_digest=candidate.digest,
    )


def control_summary(document: document_check.Document) -> dict[str, Any]:
    return {
        "milestone_id": document.milestone_id,
        "revision": document.revision,
        "maturity": document.fields["maturity"],
        "disposition": document.fields["disposition"],
        "worktrack_ids": list(document.entries),
        "acceptance_ids": list(document.criteria),
        "amendment_revisions": sorted(document.amendments),
        "milestone_branch": document.fields["milestone_branch"],
        "baseline_ref": document.fields["baseline_ref"],
        "close_target": document.fields["close_target"],
    }


def _stable_refs(document: document_check.Document) -> list[str]:
    values = [entry.result_ref for entry in document.entries.values() if entry.result_ref is not None]
    values.extend(value for value in document.final_refs.values() if value is not None)
    return values


def _branch_contract_changed(candidate: document_check.Document, current: document_check.Document | None) -> bool:
    return current is not None and any(
        current.fields[key] != candidate.fields[key]
        for key in ("milestone_branch", "baseline_ref", "close_target")
    )


def _resolve_branch(
    repo_root: Path,
    candidate: document_check.Document,
    current: document_check.Document | None,
    baseline: str,
    *,
    mutate: bool,
    identical_replay: bool,
) -> repository.BranchResolution:
    return repository.resolve_branch_contract(
        repo_root,
        milestone_branch=candidate.fields["milestone_branch"],
        current_exists=current is not None,
        contract_changed=_branch_contract_changed(candidate, current),
        baseline=baseline,
        mutate=mutate,
        identical_replay=identical_replay,
    )


def _load_candidate(candidate_path: str, mode: str) -> document_check.Document:
    raw = exact_persistence.safe_read_regular(Path(candidate_path), missing_ok=False)
    assert raw is not None
    return document_check.parse_document(raw, mode)


def _git_contract(repo_root: Path, candidate: document_check.Document) -> repository.GitContract:
    return repository.validate_git_contract(
        repo_root,
        source_branch=candidate.source_branch,
        baseline=candidate.baseline,
        milestone_branch=candidate.fields["milestone_branch"],
        close_target=candidate.fields["close_target"],
        stable_refs=_stable_refs(candidate),
    )


def validate_command(args: argparse.Namespace) -> int:
    repo_root = repository.ensure_safe_repo_root(args.repo_root)
    milestone_dir = repository.ensure_safe_milestone_dir(repo_root)
    candidate = _load_candidate(args.candidate, args.mode)
    target = milestone_dir / f"{candidate.milestone_id}.md"
    current_raw = exact_persistence.safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, current_raw, args.mode)
    document_check.enforce_init_authority(candidate, current, None)
    contract = _git_contract(repo_root, candidate)
    branch = _resolve_branch(
        repo_root,
        candidate,
        current,
        contract.baseline,
        mutate=False,
        identical_replay=action == "already_applied",
    )
    json_out(
        {
            "signal": "proposal_ready",
            "status": "valid",
            "mode": args.mode,
            "milestone_id": candidate.milestone_id,
            "revision": candidate.revision,
            "canonical_ref": str(target.relative_to(repo_root)),
            "preview_digest": candidate.digest,
            "current_revision": current.revision if current else 0,
            "current_digest": current.digest if current else "absent",
            "proposed_action": action,
            "branch_outcome": branch.outcome,
            "control_summary": control_summary(candidate),
            "writes": [],
        }
    )
    return 0


def _durable_writes_after_failure(
    repo_root: Path,
    target: Path,
    candidate: document_check.Document,
    *,
    branch_created: bool,
    branch_baseline: str,
    document_durable: bool,
) -> list[str]:
    writes: list[str] = []
    branch = candidate.fields["milestone_branch"]
    if branch_created and repository.read_branch_ref(repo_root, branch) == branch_baseline:
        writes.append(f"refs/heads/{branch}")
    if document_durable:
        writes.append(str(target.relative_to(repo_root)))
    return writes


def _attach_failure_context(
    exc: Exception,
    repo_root: Path,
    target: Path,
    candidate: document_check.Document,
    *,
    branch_created: bool,
    branch_baseline: str,
    document_replaced: bool,
) -> NoReturn:
    if isinstance(exc, PUBLIC_ERRORS):
        details = exc.details
        if "document_written" in details:
            document_durable = bool(details.pop("document_written"))
        else:
            document_durable = exact_persistence.observed_exact_bytes(target, candidate.raw)
        details.setdefault("commit_point", "after_replace" if document_replaced else "before_replace")
        details.setdefault("roll_forward_required", document_replaced)
        details["writes"] = _durable_writes_after_failure(
            repo_root,
            target,
            candidate,
            branch_created=branch_created,
            branch_baseline=branch_baseline,
            document_durable=document_durable,
        )
        raise exc
    document_durable = exact_persistence.observed_exact_bytes(target, candidate.raw)
    fail(
        "transaction_failure",
        error=str(exc),
        commit_point="after_replace" if document_replaced else "before_replace",
        roll_forward_required=document_replaced,
        writes=_durable_writes_after_failure(
            repo_root,
            target,
            candidate,
            branch_created=branch_created,
            branch_baseline=branch_baseline,
            document_durable=document_durable,
        ),
    )


def _inject_after_branch(point: str | None) -> None:
    if point == "after-branch":
        fail("injected_failure", "test-only failure injection", failure_point="after-branch")


def apply_command(args: argparse.Namespace) -> int:
    repo_root = repository.ensure_safe_repo_root(args.repo_root)
    milestone_dir = repository.ensure_safe_milestone_dir(repo_root)
    candidate = _load_candidate(args.candidate, args.mode)
    require(DIGEST_RE.fullmatch(args.approved_digest), "invalid_approved_digest")
    require(
        candidate.digest == args.approved_digest,
        "approval_digest_mismatch",
        approved_digest=args.approved_digest,
        candidate_digest=candidate.digest,
    )
    approval_ref = args.approval_ref.strip()
    require(approval_ref and "\n" not in approval_ref and len(approval_ref) <= 512, "missing_approval_ref")
    require(
        args.expected_current_digest == "absent" or DIGEST_RE.fullmatch(args.expected_current_digest),
        "invalid_expected_digest",
    )

    target = milestone_dir / f"{candidate.milestone_id}.md"
    previous_raw = exact_persistence.safe_read_regular(target, missing_ok=True)
    action, current = classify_candidate(candidate, previous_raw, args.mode)
    validate_expected_state(action, candidate, current, args.expected_current_revision, args.expected_current_digest)
    document_check.enforce_init_authority(candidate, current, approval_ref)
    contract = _git_contract(repo_root, candidate)
    original_checkout = repository.current_branch(repo_root)
    branch = repository.BranchResolution("not_attempted", False, contract.baseline)
    document_replaced = False
    try:
        branch = _resolve_branch(
            repo_root,
            candidate,
            current,
            contract.baseline,
            mutate=action != "already_applied",
            identical_replay=action == "already_applied",
        )
        _inject_after_branch(args.test_failure_point)
        if action == "already_applied":
            exact_persistence.verify_exact_bytes(target, candidate.raw, mismatch_code="stale_compare_and_swap")
        else:
            persisted = exact_persistence.persist_exact_bytes(
                target,
                candidate.raw,
                previous_raw,
                failure_point=args.test_failure_point,
            )
            document_replaced = persisted.replaced
        require(repository.current_branch(repo_root) == original_checkout, "checkout_changed")
        recheck_current = candidate if action == "already_applied" else current
        _resolve_branch(
            repo_root,
            candidate,
            recheck_current,
            branch.baseline,
            mutate=False,
            identical_replay=action == "already_applied",
        )
    except Exception as exc:
        _attach_failure_context(
            exc,
            repo_root,
            target,
            candidate,
            branch_created=branch.created,
            branch_baseline=branch.baseline,
            document_replaced=document_replaced,
        )

    outcome = {"create": "created", "amend": "revised"}.get(action, "already_applied")
    writes: list[str] = []
    if branch.created:
        writes.append(f"refs/heads/{candidate.fields['milestone_branch']}")
    if action != "already_applied":
        writes.append(str(target.relative_to(repo_root)))
    json_out(
        {
            "signal": "milestone_ready",
            "status": outcome,
            "transaction_outcome": outcome,
            "mode": args.mode,
            "milestone_id": candidate.milestone_id,
            "revision": candidate.revision,
            "canonical_ref": str(target.relative_to(repo_root)),
            "canonical_digest": candidate.digest,
            "approval_ref": approval_ref,
            "branch_outcome": branch.outcome,
            "writes": writes,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check or persist one complete approved Milestone document")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands = {"validate": "check complete exact bytes without writes", "apply": "persist complete exact approved bytes"}
    parsers = {name: subparsers.add_parser(name, help=help_text) for name, help_text in commands.items()}
    for command in parsers.values():
        command.add_argument("--mode", choices=("create", "amend"), required=True)
        command.add_argument("--candidate", required=True)
        command.add_argument("--repo-root", required=True)
    apply = parsers["apply"]
    apply.add_argument("--approval-ref", required=True)
    apply.add_argument("--approved-digest", required=True)
    apply.add_argument("--expected-current-revision", type=int, required=True)
    apply.add_argument("--expected-current-digest", required=True)
    apply.add_argument(
        "--test-failure-point",
        choices=("after-branch", "before-replace", "after-replace"),
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, "test_failure_point", None) and os.environ.get("SERVO_MILESTONE_INIT_ALLOW_TEST_FAILURE") != "1":
        fail("test_failure_not_enabled")
    return validate_command(args) if args.command == "validate" else apply_command(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PUBLIC_ERRORS as exc:
        details = dict(exc.details)
        writes = details.pop("writes", [])
        json_out(
            {
                "signal": signal_for_error(exc.code),
                "status": exc.code,
                "reason": exc.message,
                "details": details,
                "writes": writes,
            }
        )
        raise SystemExit(2)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        json_out({"signal": "blocked", "status": "internal_error", "reason": str(exc), "writes": []})
        raise SystemExit(3)
