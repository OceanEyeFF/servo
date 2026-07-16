# Harness Product Source

`product/harness/` is the canonical executable source root for Harness.

- [skills/README.md](./skills/README.md) defines package invariants and the canonical Skill inventory.
- [adapters/README.md](./adapters/README.md) defines backend payload ownership.
- [Harness指导思想.md](../../docs/harness/foundations/Harness指导思想.md) is the only long-lived Harness doctrine document.

Operational behavior belongs to each Skill package. Repo-local `.agents/` and `.claude/` directories are deploy targets and must not be edited as source.
