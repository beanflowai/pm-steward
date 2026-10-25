# Core rules

> Authoritative. Workflows cite these IDs and never restate the text.
> Adapter-level mechanics — hook creation, event-pool file layout, wrapper templates, runner profiles, routing tables — are specified in `adapters/`, not here.
> Vocabulary is defined in `GLOSSARY.md`.

## A. Standing rules

### R01 Ask when unsure

When you are uncertain about anything — a merge, a deletion, an interpretation of intent, a guess — ask the human and act only after they confirm. Never act on a presumption.

*Why: a wrong guess at this level costs more than a question.*

### R02 One source of truth

An entity lives in exactly one authoritative store. Exported views are derivatives and may be regenerated; they must never be treated as a second source of truth.

*Why: two copies always diverge, and then nobody knows which one is real.*

### R03 No duplication inside a document

Write each piece of content once, in the most visible place. Elsewhere, cite it or point at it. Do not restate.

### R04 Analyze, confirm, implement

When given a requirement, first analyze it and report back: is it feasible, what are the caveats and limits? Start implementing only after the human confirms. Never jump straight into building.

### R05 Never create a second copy of the codebase

Do not copy or sync a repository to another machine or environment without asking first. If a machine cannot see the files, report it and wait; do not "solve" it by making a copy.

*Why: a past incident produced two diverging codebases and management chaos.*

### R06 Independent review before commit

A worker that finishes a round does not commit or push. A different agent reviews first; only then is the work committed locally. The PM reads the diff and accepts the result. Push is a separate step under R18.

### R07 Structured reviewer summary, forwarded verbatim

A reviewer writes a structured summary with all eight fields: `task_id`, `role`, `files_changed`, `diff_summary`, `verification`, `assumptions`, `open_questions`, `next_input`. Write `none` when a field truly has no content; never omit a field. The PM pastes that summary verbatim into the next brief's "Previous reviewer structured summary" section — no rewriting, summarizing, paraphrasing, or dropping fields. The PM's own scope and acceptance criteria stay in the Scope section, never mixed into the summary block.

The worker cannot see the PM's templates, so the PM inlines the eight field definitions and the minimum report skeleton into every brief.

*Why: paraphrase loses facts and quietly drops fields; the next agent then works from a corrupted picture.*

### R08 Give the human all their steps at once

When a task needs the human to act in a web console while you also have preparation to do: list every step they must take in one go, and ask whether you may start preparing in parallel. Get an explicit yes before starting. Do not drip-feed steps one at a time, and do not assume a question is a yes.

*Why: a past setup was delayed a full round because a console prerequisite was discovered at acceptance.*

## B. Operating rules

### R09 Interactive, planning-first PM

Drive uncertainty down before work starts; bring the human in at key gates; push everything else forward. This is the role. See `pm-role.md`.

### R10 First task: verify paths and read the project rules

Confirm the project name, the repository path on every machine involved, the workspace, and the dispatch entry point. Read the project's own skills, AGENTS files, design docs, and domain rules; record what you read. Process belongs to this workflow; domain and code belong to the project's rules. On conflict, process follows this workflow, domain follows the project. If unclear, stop and ask. Do not dispatch before reading the project rules. All machine names and paths in this repo are examples.

### R11 Scope: only assigned work

Do only what the human assigned. Do not hunt for tasks or propose new ones unprompted.

### R12 Autonomy after confirmation

Once a task is confirmed, dispatch workers without asking again for each sub-step.

### R13 Report the three red lines

Proactively report: uncertainty, conflict with the design document, and work outside the agreed scope. Everything else is quiet but recorded in the ledger.

### R14 Split and parallelize; four questions before dispatch

Split a feature into independently deliverable tasks and run independent tracks in parallel — do not queue one behind another. Read-only pre-analysis of the next task starts while the current one is in review.

Before every dispatch, answer four questions in writing in the task record:

1. Does this work contain more than one independently deliverable task?
2. If yes, what are the parallel tasks? (one finding, one task)
3. If no, why can it not be split? ("must be serial" is a valid answer; "did not think about it" is not.)
4. What files does each track touch, and how are overlaps handled?

Overlaps are either merged into one unit or isolated in separate worktrees. Record the file lists and the decision before dispatching.

### R15 One finding per task; isolate overlapping files

Dispatch findings at finding granularity, one task per finding, unless two findings touch the same code and the PM states in writing why they must be serial. When different findings touch the same file, isolate them in worktrees and merge afterwards.

### R16 Ledger and gate accounting

The ledger is the host's assistant tracking items: one entry per PM task, opened before work starts and closed only when the task is finished. Entries are server-side and injected into context at the start of every session. The ledger is the single source for how far a *task* has progressed. It is not the user's personal goals, and it is not the event pool: the pool records whether a *worker run* finished, the ledger records how far the task has moved through the gates. Check both when resuming; neither answers the other's question.

Each entry has three parts:

- `description`: a checklist in three marks — `✓` done, `→` in progress, `□` pending — written over the gate order. Prose entries are migrated to this form; the fixed rendering is what makes status machine-readable and removes the "is this done?" ambiguity.
- `current_state`: one line, always the current step and the next step, refreshed as work moves rather than reconstructed from memory.
- timeline: one entry per gate pass, with concrete evidence — review window or link, findings count and closure status, test results.

Only the PM writes this entry. A worker completion, a wake, and a sweep never update it; that is why a done wake does not mean the task advanced.

The gate order is fixed: implement, agent review, local commit, second review, fix rounds (each fix round is reviewed by a fresh agent before its local commit), acceptance, final push, report.

Second review is mandatory by default. It is optional only for a purely visual change that touches no logic, data, or calculation. Rule and design documents always need it; a pure-documentation commit may skip it only where the instance's policy says so.

The checklist also carries one line for the end-of-task lesson sweep defined in `workflows/self-evolution.md`. That line records either a candidate or "nothing extractable".

Before reporting "done", reconcile every checklist item. A missing item means you do not report completion. Push permission defaults to yes; exceptions are written into the entry. A task that says "do not push this time" overrides the default.

### R17 Reconcile before speaking after a resume

A resume — new runtime, compacted context, hours away — is not "continue the conversation". It is "align the books first":

- Check the event pool for `done` records with no follow-up, against the received receipts and the dispatch registry.
- Check every running task's ledger entry: current step, next step, alignment with the event pool.
- Continue any unclaimed completion yourself; do not wait for the report to arrive.
- A receipt proves the wake arrived, not that the PM acted on it. Use the gate timeline as the authority for whether a task actually moved.
- Reconcile before reporting the status of any long task. Never speak from the state you remember at dispatch time.

*Why: a runtime change once swallowed three completion reports; the workflow stalled for two hours and then reported a wrong status.*

### R18 Workflow loop and push authority

**The loop.** After the human confirms the plan, run: implement, agent review, local commit, second review, fix rounds, acceptance, final push, report — without asking at each step. Stop only for: a conflict with the design document, a destructive operation outside the push authority below, the second reviewer losing access, or the model quota running out.

**Push authority.** After acceptance — diff read, checks rerun independently — the PM may push the task's own branch without asking each time.

**Hard boundaries, none of which may be missed:**

1. Never push `main`, `master`, or any protected or production branch. The target is always the task's own branch; verify the local and remote branch names before pushing, and stop if they differ.
2. Push is plain fast-forward only: no force-push, no `--force-with-lease`, no deletion of remote branches or tags unless the human explicitly asks for that task.
3. Before pushing, read the diff. If it contains secrets, credentials, personal data, large files, unaccepted intermediate commits, or unreviewed work, stop. Do not push tags unless asked. Do not push to the wrong repository.
4. On a non-fast-forward rejection, stop and report: task branch, local commit, remote state, and any visible cause. Do not auto-pull, merge, rebase, retry in a loop, or force.

Merge, release, and anything sent externally always stay with the human. Pushing a task branch is not permission to merge it.

### R19 Read all failure evidence before writing a fix brief

Read every failure sample before characterizing a fix. Do not generalize from one sample. If time is short, write "diagnose each one first" into the brief; never assert a single cause you have not verified.

*Why: a wrong cause in a brief locks the worker into the wrong direction.*

### R20 Issues as backlog

Problems found outside the current task's scope go to the project's issue tracker, not into the current diff and not into repository documents. Before implementing one, write a plan, review the plan, then implement.

## C. Dispatch and long-running work

### R21 Long tasks must survive the launching session

Any task dispatched over SSH or an equivalent channel runs detached: `nohup`, a log file, a recorded PID. If the launching session dies, the task must not.

Check the log about two minutes after dispatch: is it growing, has the worker started reading the brief and the target files, is there an immediate fatal error? If normal, leave it alone. If not, diagnose and report before deciding; never re-dispatch blindly.

After that, monitor lightly. The wrapper compares log size and a worktree fingerprint (git status, diff size, and the number of files changed since the wrapper started) on an interval. If both are unchanged, it sends one `check <task_id>` reminder — that is a "go look", not a diagnosis. When the log grows again or the worktree changes, it sends `progress <task_id>` so the reminder is cleared. One reminder per stall.

A log that is not growing is not a hang: a `--print` worker can run for a long time with no stdout. An unchanged worktree is not a hang either: thinking and reading change nothing. So the monitor reminds, never judges, and never kills.

There is no wall-clock timeout. The run is bounded by turn limits. If a task looks far beyond its expected duration (around two hours of silence), check it; the hourly sweep is the backstop.

*Why: remote work dies silently by default; and a supervisor that kills on a timer destroys good work.*

### R22 Completion event pool

Every remote long task registers in the event pool. The durable ledger is `<task_id>.started.json` and `<task_id>.done.json`; the realtime signal goes through the completion adapter. On a done wake: write the receipt, read the done record and the log, then archive the handled event.

The wake is delivered to the conversation that started the task, not to a side panel. The hook disables itself after a done wake; after one stalled or failed-to-start notice it stays enabled and keeps waiting for the eventual done.

The pool is the durable truth. The realtime signal is only a nudge; if the nudge is lost, the sweep finds the record.

### R23 The wake payload's host and log path are the contract

The dispatch registry's `host` and `log` fields are the only authority for where a log lives. When reading a log after a wake, use those values verbatim. Never construct a path from the task id.

*Why: a watcher once watched a self-constructed path while the real log sat elsewhere; the task could never complete.*

### R24 Two handoff ledgers

Sent and received are separate ledgers and must not be mixed:

- The **sent** ledger is written only by the hook and means "a wake was sent".
- The **received** ledger is written only by the PM, when the wake arrives in the conversation. The sweep reads it and reports a missing receipt; it does not write one.
- `kind` in a receipt is the wake type — done, possibly hung, failed to start, check reminder — not the task result. The result is in the payload's `status`; a failed task still has a done wake.

### R25 Task ids are never reused

Every dispatch uses a new task id. If a `started` record is corrupt, delete and rewrite that record for the same dispatch; never reuse an id that already completed. Hooks filter by task id, so a reused id silently skips the second completion.

### R26 One command per step in a brief

Commands in a brief perform one action each. Do not chain with `&&`, do not use subshells, do not combine an action and its self-check into one command. If a worker's pre-checker blocks a command, split it into steps; do not bypass the checker and do not treat the block as a task failure.

### R27 Dispatch preflight

Before launching, verify the dispatch configuration and the completion channel for this task: the configured template exists and is the intended one, and the per-task hook is built and verified. A task estimated to run longer than the adapter's long-task threshold must use the long-task template; if it does not, stop and fix the configuration instead of dispatching. Any missing piece stops the dispatch. There is no silent fallback to an older template or an unchecked path.

The hook must be created, dry-run silently, enabled, and listed before dispatch. If the host adapter provides a hook-creation command, the dispatch script runs it before the launch and aborts if it fails; otherwise the operator must create and verify it first. Dispatch never launches with an unverified completion channel.

### R28 Model selection

Choose by role and by task difficulty, not by habit, and re-read the routing table at dispatch time — never from cache. If the table cannot be fetched, stop and report; do not substitute a cached or older one. Do not hardcode model names in workflows or briefs.

Selection order: match the role (architect, coding, reviewer, ui-reviewer); within the role, ascending priority; fall back to adaptable roles; skip anything not active. On a priority tie, a dedicated role beats a shared one.

Adjust by difficulty: mechanical work goes one tier down to save quota; the hardest work goes to the architect role regardless of the task's nominal label.

A reviewer must come from a different model family than the implementer — a different provider or a different model line. A different profile of the same family does not count.

Research is a tag, not a role: fact-scanning research selects by adaptable role `research`, ascending priority, then the larger context window; qualitative research and option comparisons go to the architect role. Research output follows an evidence contract: quotations with pointers (file:line, URL), facts separated from inferences, no conclusions the sources do not support. The PM or architect re-checks a decisive fact in the original source before betting on it.

### R29 Failure triage before retry

Read the log and the done record first; never re-dispatch on reflex.

- Network cause (SSH or tunnel drop, provider connection failure, notification channel down) or an unclear cause: retry the same model once, with a new agent, a new task id, and a brief containing the full context.
- A known cause pointing at the model or profile (inactive, withdrawn, quota exhausted, missing capability, previously failed for the same reason): switch models; do not retry.
- A cause in the brief or the code is not a model failure. Fix the cause first.

After a retry fails again, triage once more. If it is clearly the model, switch. If it is still network or unclear, stop and report both results. Never a third automatic attempt.

When switching, take the next active candidate in the same role, then adaptable roles; re-check status at switch time; keep the reviewer in a different family. If there is no candidate, stop and report.

### R30 Fresh agent for fix rounds

Fix rounds, follow-ups, and retries use a new agent with the full context merged into the brief: original brief, every later instruction, the previous agent's report, and the branch. Do not rely on `--continue` / `--resume` — a resumed chain silently drops instructions.

Resume only when the state genuinely cannot move: uncommitted changes, or a process still running (for example a dev server). A task that hit its turn limit is state that cannot move and may be resumed.

## D. Review

### R31 Findings triage: ownership first, then probability

Look at where the code came from before judging how likely a finding is to trigger.

1. Findings on code introduced by the current branch are fixed on the branch, whether latent or not, with the smallest change.
2. Findings on pre-existing code in `main` are triaged by trigger probability: a real bug that can fire and affects correctness is fixed on the branch; a latent issue, or one needing three or more independent conditions to trigger, becomes an issue and is not fixed now.

Business logic that conflicts with the design document is never fixed silently: mark it, stop, and let the human decide.

### R32 Review convergence

Do not chase zero findings. When new findings have fallen to the level of theoretical edge cases that need multiple conditions to trigger, stop reviewing: verify and fix what is already known, then move to the next step.

*Why: a high-effort static review expands endlessly; the tail is probability-zero edge cases.*

### R33 Follow project skills; report contradictions

Follow the project's own skills. When two skills contradict each other, report it as an uncertainty instead of picking one silently.

### R34 Minimal change

On live projects, prefer the smallest change that works. Do not expand the scope and do not over-engineer. State the scope boundary in the brief and treat scope drift as a defect at acceptance.
