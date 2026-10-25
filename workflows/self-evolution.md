# Self-evolution

> Applies to: turning repeated failures, reusable patterns, or explicit corrections into rules or skills, instead of leaving them in one conversation.
> Preconditions: verifiable evidence exists — task records, briefs, diffs, commits, or the human's own correction. No evidence, no rule.
> End state: a rule or skill confirmed by the human and written to the authoritative source, then exercised on the next similar task. Unconfirmed drafts do not take effect and are not auto-loaded.

## Steps

1. **Read the project rules first** — R10.
2. **Collect evidence** — task records, briefs, diffs, commits, tests, failure evidence, and the human's exact words. Collect first; do not conclude. If time is short, write "diagnose each one first".
   - **End-of-task sweep**: before reporting a task done, scan its brief, reviewer summaries, findings, and corrections for anything worth extracting. If there is a candidate, draft it with problem, evidence pointers, scope, and where it would land. If not, write "nothing extractable" in the timeline. This sweep is part of closing the ledger (R16).
3. **Find the pattern** — separate one-off events from reusable patterns. Two occurrences of the same pattern, or one explicit correction, justifies a candidate. One isolated event with no correction does not. State the applicable scope (project, task type) so a rule does not leak into the wrong project.
4. **Draft the rule or skill** — each draft states: the problem, the evidence (task id, commit, where the correction was said), the scope, when it does not apply, and how to verify it. A skill does one thing. No secrets, tokens, personal data, or production configuration.
   - **Anti-bloat**: prefer a targeted patch over a rewrite. Write the lesson, not the log: keep the reusable rule plus one sentence of why, without the incident narrative. If a rule or skill file exceeds roughly 200 lines or contains repeated sections, produce a compression or merge candidate. Those candidates go through the same approval queue; never rewrite or delete a file automatically.
5. **Propose and wait** — present the candidate and wait for explicit confirmation. Before confirmation, do not edit `core/AGENTS.md`, do not edit workflows, and do not auto-load anything. The PM never rewrites its own authority rules on its own.
   - **Approval queue**: candidates live outside the repository, one file per candidate, with exactly three states: pending, approved, rejected. Only approved candidates move to step 6. The instance's environment profile defines where the queue lives; if it is undefined, stop and ask.
6. **Land it** — after confirmation, write it to the right place: general PM rules to `core/AGENTS.md`; task shapes to `workflows/`; project domain rules to the project's own skill, not into this workflow. The commit message records the evidence source so the change can be reverted.
   - **Ledger of landed rules**: append one line per landing — date, task id, evidence pointer, file and commit, verification status (pending / verified / sent back). Git history remains the authority; the ledger is only an index.
7. **Verify on the next similar task** — the next task of that type must cite the new rule, and the ledger timeline records which rules were cited. If the rule did not reduce rework, send it back to step 3; do not keep it out of inertia.
8. **Curate periodically** — merge duplicates, archive expired rules (model withdrawn, tool retired), fix conflicts. Report contradictions as uncertainty (R33). Archive superseded skills; history stays in git.
   - Curator triggers, any one of which starts a review: monthly; every N tasks (initial N = 3); or any rule unused across three consecutive tasks of its applicable type.
   - Only tasks whose rule-citation list was recorded count in the denominator. Unrecorded citations do not count as "unused".
   - Rules pinned by the human are exempt from archive and merge suggestions. The pin, its confirmation source, and a unique identifier for the rule are recorded in the landing ledger.

## Gates

- Every rule has an evidence chain.
- The applicable scope is written; cross-project use is justified explicitly, never assumed.
- The human confirmed; nothing was auto-loaded before that.
- A conflict with an existing rule was reported, not overwritten.
- No secrets, tokens, personal data, or production configuration.

## Autonomy boundaries

- Collecting, extracting, and drafting run unattended.
- Landing, editing `core/AGENTS.md`, and editing workflows always stop for confirmation.
- The PM never grants itself more autonomy; that always requires the human.
- Merge, release, and anything external stay with the human (R18); this workflow does not perform them.
