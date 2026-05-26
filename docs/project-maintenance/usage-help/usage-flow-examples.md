---
title: "Usage Flow Examples"
status: active
updated: 2026-05-26
owner: servo-kernel
last_verified: 2026-05-26
---
# Usage Flow Examples

This page lists observed projects that can help operators understand how Servo is used in real repositories. Examples are reference material only; they do not replace this repository's Harness artifact contracts, review/verify gates, or release approval flow.

Use three different weights when reading this page:

- The current Servo repository is the primary public dogfooding reference because it shows Servo managing its own long-running evolution.
- Maintainer-local showcase candidates may be more representative of Harness capability, but they are not public proof until exported, sanitized, or separately documented for outside readers.
- Public lightweight examples are useful because readers can inspect them directly, but they may not show the full Harness capability surface.

## Primary Public Dogfooding Reference

| Project | What It Demonstrates | Notes |
|---|---|---|
| This repository (`vibecoding_autoworkflow` / Servo) | Repeated Servo-managed evolution of Servo itself: Harness artifact contracts, canonical skills, installer packaging, release governance, Milestone/Worktrack execution, Append Request routing, backlog/history hygiene, and pre-release documentation gates. | Use this as the main public showcase for long-running, traceable Servo operation. It is a dogfooding reference, not an independent third-party product case study. |

This repository is the strongest public evidence currently available because the Servo control layer, product source, governance docs, installer flow, and milestone history all evolve together here. It shows more than one-time setup: it shows repeated worktrack execution, gate evidence, release preparation, and runtime-state writeback across multiple iterations.

## Public Lightweight Examples

| Project | What It Demonstrates | Notes |
|---|---|---|
| [OceanEyeFF/reqflow](https://github.com/OceanEyeFF/reqflow) | Servo-managed product development on a lightweight requirement-ticket collaboration app. | Public repository with `.servo/`, project docs, Next.js/TypeScript source, Prisma data layer, and test/build scripts. Use it as an inspectable onboarding example, not as the strongest demonstration of current Harness capability. |

`reqflow` is useful because it is public and simple. Its code delta is relatively small, so it should not be used as the primary evidence that Servo can manage larger, multi-phase project evolution.

## Maintainer-Local Showcase Candidates

| Project | What It Demonstrates | Current Visibility |
|---|---|---|
| `/mnt/f/小游戏/MiniGame1` | A stronger local example of Harness-managed product evolution: Godot active implementation, frozen Node TUI reference, `.aw` to `.servo` migration traces, project docs, upgrade history, runnable game artifacts, and multiple design/evidence layers. | Maintainer-local path. Treat as internal evaluation evidence until a public repository, sanitized case study, or exported docs package is available. |

`MiniGame1` is a better capability demonstration than `reqflow` because it shows a larger product surface and more lifecycle pressure: engine migration decisions, frozen historical implementation, active implementation, artifact/evidence docs, and runtime-state evolution. Since it is currently only a local repository path, public operator docs should describe it as a showcase candidate rather than asking external readers to rely on it.

## How To Use Examples

Read examples as concrete project history, not as portable policy. When applying a pattern from another repository:

1. Start from [quickstart.md](./quickstart.md) or [recommended-usage.md](./recommended-usage.md) for the current supported operator path.
2. Compare the example's `.servo/` state shape with the current [Harness artifact contracts](../../harness/artifact/README.md) before copying any structure. For legacy examples that still include `.aw/`, treat that state as migration history unless the target repository explicitly documents a current `.aw` compatibility boundary.
3. Re-run local install, governance, and worktrack verification in the target repository instead of inheriting the example's evidence.
4. Keep project-specific product decisions, UI choices, stack choices, and database layout out of Servo-level documentation unless they are separately verified as reusable Harness behavior.

## Promotion Rule

An example can become a stronger documented pattern only after a dedicated Worktrack verifies that the behavior is reusable across repositories. Until then, examples stay in `usage-help` as operator-facing reference material.
