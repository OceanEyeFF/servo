from __future__ import annotations

import argparse
import sys


def evaluate_pr_branch(
    *,
    base_ref: str,
    head_ref: str,
    base_repo: str,
    head_repo: str,
    protected_base: str,
    allowed_head: str,
) -> tuple[bool, str]:
    if base_ref != protected_base:
        return True, f"PR base {base_ref!r} is not protected baseline {protected_base!r}; branch guard skipped"

    if head_repo != base_repo:
        return (
            False,
            (
                f"PRs targeting {protected_base!r} must come from the canonical repo {base_repo!r}; "
                f"got head repo {head_repo!r}"
            ),
        )

    if head_ref != allowed_head:
        return (
            False,
            (
                f"PRs targeting {protected_base!r} must use head branch {allowed_head!r}; "
                f"got {head_ref!r}"
            ),
        )

    return True, f"PR branch policy passed: {head_repo}:{head_ref} -> {base_ref}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard protected-baseline PR source branch policy.")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--base-repo", required=True)
    parser.add_argument("--head-repo", required=True)
    parser.add_argument("--protected-base", default="master")
    parser.add_argument("--allowed-head", default="develop")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ok, message = evaluate_pr_branch(
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        base_repo=args.base_repo,
        head_repo=args.head_repo,
        protected_base=args.protected_base,
        allowed_head=args.allowed_head,
    )
    stream = sys.stdout if ok else sys.stderr
    print(message, file=stream)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
