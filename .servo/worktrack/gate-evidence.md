---
title: "Gate Evidence - WT-20260520-runtime-dispatch-profile-claude-deepseek"
artifact_type: "gate-evidence"
generated_from: "init-worktrack-skill"
updated: "2026-05-20"
owner: "servo-kernel"
---

# Gate Evidence

## Control Signal

- worktrack_id: WT-20260520-runtime-dispatch-profile-claude-deepseek
- evidence_status: gate-passed
- current_phase: closing
- gate_verdict: pass
- recommended_next_route: WorktrackScope.Close
- continuation_ready: true
- approval_required: false

## Review Evidence

- lane_status: completed
- lane_verdict: pass
- ready_for_gate: true
- reviewer: current-carrier
- findings:
  - Dispatch policy now requires `runtime_dispatch_profile` and attempt/fallback evidence.
  - Runtime dispatch contract separates policy-based current-carrier selection from runtime inability to delegate.
  - Dispatch packet schema records backend_runtime, model_family, subagent shell availability, permission state, package safety, delegation_attempted, attempted_carrier, carrier_decision, and fallback_reason.
  - ClaudeCodeCLI / Deepseek compatibility lane now requires explicit capability and fallback evidence instead of silent current-carrier fallback.
- residual_findings: []

## Validation Evidence

- lane_status: completed
- lane_verdict: pass
- ready_for_gate: true
- validation:
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest toolchain/scripts/test/test_governance_semantic_check.py -q`: 57 passed
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/governance_semantic_check.py --json`: passed with retained alignment warnings
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/path_governance_check.py`: passed
  - `PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/folder_logic_check.py`: passed
  - `git diff --check`: passed

## Policy Evidence

- lane_status: completed
- lane_verdict: pass
- ready_for_gate: true
- policy_summary: |
  - Change stayed inside approved WT3 scope.
  - No deploy target edits, package/release changes, destructive operations, or broad system config changes.
  - The change does not force all `auto` dispatches to delegate; it requires observable capability, attempt, and fallback evidence.

## Gate Judgment

- implementation_gate: pass
- validation_gate: pass
- policy_gate: pass
- overall_verdict: pass
- acceptance_criteria:
  - AC-RDP-001: pass
  - AC-RDP-002: pass
  - AC-RDP-003: pass
  - AC-RDP-004: pass
  - AC-RDP-005: pass
  - AC-RDP-006: pass
- allowed_next_routes:
  - WorktrackScope.Close
- recommended_next_route: WorktrackScope.Close
- approval_required: false
