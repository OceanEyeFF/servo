---
title: "servo-installer Release Operation Model"
status: active
updated: 2026-05-06
owner: servo-kernel
last_verified: 2026-05-06
---
# servo-installer Release Operation Model

> 目的：记录已选发布操作模型：GitHub Release `published` 事件加 npm Trusted Publishing。

本页属于 [Governance](./README.md)。

- decision_status: repository-workflow-preflight-implemented
- selected_operation_model: GitHub Release `published` trigger + npm Trusted Publishing via GitHub Actions OIDC
- long_lived_npm_token_required: false
- publish_workflow_implemented: true (`.github/workflows/publish.yml`)
- future_npm_publish_allowed_by_this_page: false

选用 GitHub Actions carrier + GitHub Release `published` trigger + npm Trusted Publishing + 可选 `npm` Environment 保护，在 Release 时保留人工审批并避免长期 npm token。

## Why Release Published

tag push 做 fallback，GitHub Release `published` 为 preferred（显式操作+release notes），main branch auto release 未选用。

## Trusted Publishing Setup

npm 侧配置 provider=GitHub Actions, org=repo owner, repo=本仓库, workflow=`publish.yml`, environment=`npm`（可选）。

## Workflow Shape

`.github/workflows/publish.yml` 只触发于 GitHub Release `published`；grant `id-token: write`，使用 `npm` Environment，npm `11.5.1` + Node `24`，从 `v<package.version>` 解析 channel，要求 Release body 含精确 approval marker，拒绝 prerelease/channel 不匹配，运行本地 publish guard，通过后以 npm provenance 发布。workflow 文件本身为权威。

## Release Procedure

1. Pre-Publish Governance -> 2. Confirm Channel Governance -> 3. Release Standard Flow -> 4. Post-publish npx smoke.

## Approval Boundary

本页选择操作模型，不授权改 version、publish、改 Trusted Publisher 设置或绕过 release-approval worktrack。

## Fallback

Trusted Publishing 受阻时保持手动 publish，仍需 tuple 显式批准且全部 pre-publish 检查通过。
