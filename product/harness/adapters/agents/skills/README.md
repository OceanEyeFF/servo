# Agents Skill Payloads

Each immediate child directory contains the canonical-copy payload descriptor for one live Skill package. The live set must match `product/harness/skills/`; installer discovery is authoritative.

Installed payloads are package-local, contain no source-repo docs dependency, and use `.agents/skills/<skill-id>/` only as a deploy target. Historical aliases may remain only in an individual live payload's explicit `legacy_target_dirs` cleanup list.
