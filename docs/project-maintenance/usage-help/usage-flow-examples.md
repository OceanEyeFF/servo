---
title: "Usage Flow Examples"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# Usage Flow Examples

This page lists observed projects that can help new operators understand how Servo is used in real repositories. These examples are reference material only; they do not replace this repository's Harness artifact contracts, review/verify gates, or release approval flow.

## Example Projects

| Project | What It Demonstrates | Notes |
|---|---|---|
| [OceanEyeFF/reqflow](https://github.com/OceanEyeFF/reqflow) | Servo-managed product development on a lightweight requirement-ticket collaboration app. | Public repository with `.servo/`, project docs, Next.js/TypeScript source, Prisma data layer, and test/build scripts. Use it to inspect how project state and implementation work can coexist in a normal application repo. |

## How To Use Examples

Read examples as concrete project history, not as portable policy. When applying a pattern from another repository:

1. Start from [quickstart.md](./quickstart.md) or [recommended-usage.md](./recommended-usage.md) for the current supported operator path.
2. Compare the example's `.servo/` state shape with the current [Harness artifact contracts](../../harness/artifact/README.md) before copying any structure.
3. Re-run local install, governance, and worktrack verification in the target repository instead of inheriting the example's evidence.
4. Keep project-specific product decisions, UI choices, stack choices, and database layout out of Servo-level documentation unless they are separately verified as reusable Harness behavior.

## Promotion Rule

An example can become a stronger documented pattern only after a dedicated Worktrack verifies that the behavior is reusable across repositories. Until then, examples stay in `usage-help` as operator-facing reference material.
