---
title: "Plan / Task Queue: WT-20260520-servo-external-rename"
artifact_type: plan-task-queue
worktrack_id: WT-20260520-servo-external-rename
baseline_ref: develop-aw@94a570044eb651fa2f1aa9ecef3cdb119bc2f537
updated: 2026-05-20T19:22:00+08:00
---

# Plan / Task Queue

## Queue

- [ ] **T1**: GitHub repo rename `servo` → `servo` (via `gh repo rename`)
- [ ] **T2**: Update root `package.json` name to `servo-installer` + update deploy `package.json`
- [ ] **T3**: Update README.md: title, description, install commands
- [ ] **T4**: Update INDEX.md: project name references
- [ ] **T5**: Update AGENTS.md: project name references  
- [ ] **T6**: Update docs/book.md, docs/README.md
- [ ] **T7**: Update operator-facing docs (quickstart, usage-help, deploy README)
- [ ] **T8**: Update snapshot-status.md, milestone-backlog.md baseline_ref
- [ ] **T9**: Validation: grep for old names, governance checks
- [ ] **T10**: Prepare npm publish (requires npm login)
