---
name: milestone-init-skill
description: 当 Harness 需要判断自然语言目标与讨论材料是否足以形成 Milestone，并在充分时由 LLM 编写、预览、批准和安全创建或 amendment 唯一 canonical Milestone document 时使用；它不负责持续漫谈、Harness currentness、Worktrack runtime 或 Milestone 状态投影。
---

# Milestone Init

## Outcome

Consume one explicit create/amend handoff and return exactly one of:

- non-persistent `init_not_ready` when material discussion gaps remain; or
- `milestone_ready` after a complete LLM-authored candidate is previewed,
  approved by exact digest, deterministically checked, and safely persisted.

The planned document at `.servo/milestone/<milestone_id>.md` is the sole
canonical owner of Milestone business truth. Init is stateless between
invocations. It does not recover a full conversation or create a discussion
artifact, draft document, backlog truth, progress counter, or status projection.

## Ownership boundary

The Skill and its LLM carrier own:

- discussion-sufficiency admission;
- Goal, Scope, Non-Goals, cross-Worktrack decisions and constraints;
- Milestone-level acceptance and declarative Worktrack TodoList authoring;
- all content organization and formatting regulation before preview;
- exact candidate preview and digest binding;
- deterministic document-contract validation;
- approval-bound exact-byte persistence and one stable handoff.

Harness owns `active_milestone_ref`, currentness, selection, routing, live
checkout observations, Worktrack dispatch, accepted `result_ref` registration,
Gate/final refs, and lifecycle transitions. Each Worktrack owns its immutable
initial requirement and execution/review/close state.

Init never selects or initializes a Worktrack, changes Harness currentness,
accepts or removes evidence, advances the Pipeline, runs Gate, publishes,
pushes, opens a PR, touches a remote, or performs destructive work.

## Invocation input

Harness transfers explicit text rather than pre-solving Init's job:

- `intent`: `create` or `amend`;
- the current goal and relevant discussion text, summary, or candidate material;
- for amend, the existing canonical Milestone ref;
- necessary repo, branch, expected-state, and authority context.

Harness may state that discussion appears sufficient, but Init makes the final
admission decision. Harness must not be required to pre-extract a complete Goal,
Scope, acceptance model, or TodoList. The carrier consumes only context supplied
in this invocation; recommendations and prior drafts are material, not approval.

## Discussion-sufficiency admission

Information is sufficient only when a faithful Milestone can be formed without
inventing a material decision. The supplied context must support:

- one intelligible Milestone-level outcome and purpose;
- scope, non-goals, permissions, and cross-Worktrack constraints;
- independently adjudicable Milestone-level acceptance criteria;
- coherent minimal Worktrack outcomes, conditions, dependencies, and coverage;
- create/amend identity and a safe stable branch contract;
- for amend, the change, reason, affected Worktracks, evidence continuity and
  revalidation, and approval boundary.

Markdown formatting, heading order, blank lines, and wording polish are not
admission gaps. Ambiguity that materially changes Goal, Scope, acceptance,
permissions, or orchestration is a gap.

When insufficient, return:

```yaml
signal: init_not_ready
status: insufficient_discussion
missing_information:
  - <material gap>
why_it_matters:
  - <effect on Goal, Scope, acceptance, or Worktrack orchestration>
discussion_directions:
  - <focused direction for ordinary follow-up discussion>
writes: []
```

Then stop. Do not preview a candidate, compute an approval digest, create a
branch or draft, or mutate control state. Continued discussion is ordinary
Programmer/LLM conversation outside this Skill. A later invocation receives
newly explicit context; no resumable discussion state exists.

## LLM authoring and output regulation

The LLM writes the complete document. Use
`templates/milestone.template.md` as the preferred output skeleton for create,
but do not treat it as the only legal Markdown serialization.

Before preview, the LLM resolves all chosen formatting, headings, entry shape,
and prose placement. The package-local script must not:

- write or complete Milestone content from a partial document;
- invent Goal, Scope, acceptance, decisions, or Worktracks;
- add missing sections or defaults;
- repair, normalize, reorder, or reserialize prose;
- return a corrected document.

Once exact bytes are previewed and approved, neither the Skill nor the worker
may alter them.

The document carries identity, revision, planned maturity/disposition, owner and
kind, stable branch contract, Goal, Scope, Non-Goals, approved cross-Worktrack
decisions, unique acceptance criteria, TodoList, amendment history, and
finalization refs.

Each Worktrack entry is only an index:

- `worktrack_id`;
- one-sentence `outcome`;
- `depends_on` or concrete `execution_condition`;
- `condition`: `required`, `conditional`, `deferred`, or `superseded`;
- `covers`;
- `result_ref`;
- optional concise `boundary_hint`.

Do not copy Worktrack scope deltas, exit checks, write surfaces, commands,
branches/checkpoints, task queues, round/recovery state, Review/Close state,
carrier, or current phase into an entry. `[x]` is valid exactly when the same
entry has a concrete stable Harness-accepted `result_ref`.

## Deterministic document check

`scripts/milestone_document_transaction.py` treats the document as:

1. flexible Markdown carrying explicit machine-control fields and opaque prose;
2. strict Milestone domain invariants over those control fields; and
3. immutable approved bytes for persistence.

Reasonable field/section order, ordinary whitespace and blank-line variation,
revision-1 amendment wording, amendment field order, commentary, and additional
prose sections are not business failures. Existing approved documents use the
same generic parser; there is no Milestone-specific compatibility profile.
Amend never reformats existing content, and earlier amendment blocks remain
byte-for-byte unchanged.

The checker deterministically enforces:

- path-safe `milestone_id`, one title-matching H1, required control fields and
  core sections;
- create as revision 1, `maturity: planned`, `disposition: open`;
- planned disposition values `open`, `finished`, and `superseded`, while Init
  may amend only open truth;
- unique acceptance and Worktrack IDs;
- every entry has valid non-empty `covers`;
- valid dependency IDs, one dependency form, no self-edge or cycle;
- checkbox/result agreement and stable result/final ref shapes and targets;
- contiguous amendment history through the current revision;
- amendment change, reason, affected Worktracks, evidence continuity,
  revalidation, and approval control fields;
- exact preservation of prior approved amendment blocks;
- no Init addition, replacement, removal, acceptance, or reinterpretation of
  Worktrack result refs or their accepted entry control fields;
- no Gate/final-ref or lifecycle/currentness mutation.

Not every acceptance criterion must already be covered by a currently eligible
entry merely to make its prose legal. Every declared entry's own `covers` values
must resolve.

Validation returns validity, exact digest, located errors, necessary read-only
control summary, and `writes: []`. It never returns repaired bytes.

## Preview and approval

Place the complete candidate in an ephemeral caller-controlled path outside
canonical `.servo/milestone/`, then run the package-local worker in `validate`
mode for `create` or `amend`.

Validation is zero-write and returns `proposal_ready`, `preview_digest`, current
revision/digest, proposed action, branch outcome, and `writes: []`.

Show the complete exact candidate and digest with its acceptance, TodoList,
material unresolved decisions, and authority boundary. Stop until the
Programmer explicitly approves that exact digest. Approval of a summary, older
draft, conversation, or different digest is insufficient.

## Approval-bound persistence and handoff

Apply consumes:

- the exact approved candidate bytes and `sha256:<64-hex>` digest;
- a concrete approval ref;
- the expected current revision and digest (`0`/`absent` for create);
- the repo and stable branch context.

The action classification is:

- no current document plus create intent: `create`;
- current plus exactly one revision and amend intent: `amend`;
- exact same ID, revision, digest, and bytes: `already_applied`;
- same revision with different bytes, stale/skipped revision, changed create,
  missing current amend, or identity mismatch: `conflict`.

The supported runtime has a single Harness writer per workspace. Concurrent Init
writers that bypass Harness are unsupported. Expected-state checks discover a
stale candidate; they are not a lock or a multi-writer protocol.

For every successful action the worker:

1. verifies approval digest/ref and parses the complete candidate;
2. reads current canonical bytes and validates expected state and Init authority;
3. validates or idempotently materializes the approved branch contract without
   changing checkout;
4. for create/amend, writes and fsyncs one temporary file;
5. rereads current bytes immediately before replacement;
6. uses atomic `os.replace`, fsyncs the directory, and reads back exact bytes;
7. returns the stable result and actual durable `writes`.

`already_applied` still verifies digest/current byte equality, expected-state
safe-repeat semantics, Init authority, branch contract, checkout, and readback.
It performs no document write.

The commit point is successful `os.replace`:

- failure before replacement leaves canonical bytes unchanged and removes only
  this invocation's temporary file;
- failure after replacement never restores old bytes; a later invocation reads
  exact candidate equality and converges through `already_applied`;
- a branch created at the approved baseline is retained if later document work
  fails and is reused on retry;
- an existing conforming branch is reused and a wrong ref is a conflict;
- there is no document rollback, branch rollback, lock file, ownership check,
  contention path, recovery window, delay marker, or concurrent recovery matrix.

Successful create, amend, or safe repeat returns only
`signal: milestone_ready`, status `created | revised | already_applied`,
identity/revision, canonical ref/digest, approval ref, branch/transaction
outcome, and truthful writes. Return it to Harness and stop.

Other public signals are `invalid`, `conflict`, and `blocked`. Failures include
stable status, reason, located details, and truthful durable writes. They never
claim repair or rollback.

## Resources

- `templates/milestone.template.md`: preferred LLM authoring skeleton.
- `scripts/milestone_document_transaction.py`: deterministic checker and
  exact-byte single-writer roll-forward persistence worker.

Both are package-local. There is no separate Pre-intake, Grill Me, Status,
schema, ledger, authoring engine, discussion-state artifact, or dependency on
source-repo docs, `.agents`, `.claude`, or historical conversations.
