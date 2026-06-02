# Complex Project Entry Gate

> This is the template source for `.servo/repo/complex-project-entry-gate.md`. It records repo-init / existing-code-adoption complex-project gate evidence as runtime evidence. It is a Milestone-side blocking gate, not fixed heavy mode. Scanner output is evidence, not verdict.

## Metadata

- repo:
- owner:
- updated:
- adoption_mode:
- gate_id:
- complex_project_entry_gate:
- target_repo:
- target_milestone_id:
- trigger_source: repo-init
- generated_by:
- gate_truth_status:

## Trigger Signals

- trigger_conditions: pending_observed_signal_review

> Candidate trigger vocabulary includes weak-doc, large_repo, multi_service, migration_or_data_risk, deploy_or_network_surface, destructive_or_secret_surface, and authority_boundary_unclear. Record only observed signals in trigger_conditions.

- scanner_evidence_ref:
- scanner_command: PYTHONDONTWRITEBYTECODE=1 python3 toolchain/scripts/test/complexity_signal_scanner.py --repo <repo> --json
- scanner_output_role: scanner output is evidence, not verdict
- complexity_signals:
- thresholds:
- confidence:

## Project Understanding

- project_understanding:
- service_workflow_boundary:
- core_directories:
- generated_or_low_trust_paths:
- verification_authority:
- unknowns:

## Operator Safety Policy

- operator_safety_policy:
  - docker_compose_permission: pending_programmer_confirmation
  - database_migration_permission: pending_programmer_confirmation
  - deploy_network_permission: pending_programmer_confirmation
  - destructive_cleanup_permission: pending_programmer_confirmation
  - secrets_policy: pending_programmer_confirmation
  - protected_paths: pending_programmer_confirmation
  - protected_branches: pending_programmer_confirmation
  - allowed_high_risk_command_modes: pending_programmer_confirmation

## Dialog Review Questions

- dialog_review_questions:
  - id: CG1
  - question:
  - why_it_matters:
  - recommended_answer:
  - tradeoff:
  - blocks_ready:

## Boundary Before Confirmation

- allowed_before_confirmation: read_only_discovery_and_scanner_evidence_collection
- forbidden_before_confirmation: milestone_activation_worktrack_derivation_high_risk_commands_deploy_database_destructive_or_secret_operations
- not_fixed_heavy_mode: true

## Verdict

- entry_verdict: blocked
- milestone_blocking_decision: block_derive_worktrack
- reinforcement_milestone_recommendation: pending_operator_review
- evidence_refs:

## Handoff

- recommended_next_route:
- handoff_to_init_milestone:
- handoff_summary:
