---
title: "Plan / Task Queue: WT-20260520-servo-npm-release-prep"
artifact_type: plan-task-queue
worktrack_id: WT-20260520-servo-npm-release-prep
baseline_ref: develop-aw@b321349
updated: 2026-05-20T23:00:00+08:00
---

# Plan / Task Queue

## Queue

- [x] **T1**: Bump version 0.5.1-rc.1 → 0.5.2 for servo-installer inaugural release (commit `25797bc`)
- [x] **T2**: Remove private flag from deploy package.json (commit `cdfef9e`)
- [x] **T3**: Fix description + bump to 0.5.3 after unpublish (commit `f8e3aaa`)
- [x] **T4**: AW_INSTALLER_/AW_HARNESS_ → SERVO_INSTALLER_/SERVO_HARNESS_ env vars (commit `f8076d1`)
- [x] **T5**: Rename deploy_aw.js → deploy_servo.js + fix link
- [x] **T6**: awInstallerRelease → servoInstallerRelease metadata field
- [!] **T7**: npm publish servo-installer@0.5.3 (blocked: 24h CD until 2026-05-21 14:30 UTC, then requires registry publish + npx smoke evidence)
- [~] **T8**: Deprecate aw-installer on npm (done manually by programmer on web)
