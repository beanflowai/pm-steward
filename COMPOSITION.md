# Composition

The workflow is a sequence of stages. Each stage needs specific tools wired together; a missing wire shows up as a specific failure, not as a vague slowdown. This page is the index: every stage points at the rule, the adapter, and the check that proves the wiring works.

| Stage | Input | Tools | What the tools must guarantee | Typical failure | Verification |
|---|---|---|---|---|---|
| Plan | A task from the human | bot, ledger, project rules | The ledger entry exists before work starts; the project rules were read (R10, R16) | Work starts from chat memory instead of the ledger | The entry lists the current and next step |
| Select model | Task type and difficulty | routing table, runner profiles | Two model families are reachable, and the table is read live (R28) | A cached model name that no longer exists | Fetch the table and resolve one role to a profile |
| Dispatch | A brief | SSH, dispatch script, wrapper template, completion channel | The launch survives the session; host and log path are recorded (R21, R22, R27) | The task dies with the SSH session, or the wake points at the wrong log | Registry has `host` and `log`; a `started` record exists |
| Execute | The brief | worker, runner, model endpoint | The worker changes only the repo, and reports in the structured format (R07) | The worker commits or merges on its own | The report has all eight fields; the diff is on the task branch |
| Monitor | Log and worktree | wrapper loop, completion channel | A stall produces a reminder, never a kill (R21) | A timer kills a slow but healthy task | One `check` reminder per stall, one `progress` when it resumes |
| Wake | Completion event | event pool, hook, host | The wake reaches the conversation that started the task (R22, R24) | The done record exists but nobody acts on it | A received receipt, then a ledger timeline entry |
| Review | A diff | a different model family, report template | The reviewer is independent and its 8-field summary is forwarded verbatim (R06, R07) | The implementer reviews its own work | Reviewer provider differs from the implementer's |
| Second review | A local commit | browser session or API reviewer | Findings are structured and triaged by ownership first (R16, R31) | Review expands forever into theoretical edge cases | Findings are closed, deferred, or accepted; R32 applied |
| Accept | Branch and evidence | PM, git, test runner | The PM reruns the checks and reads the diff (R18) | "Tests pass" is taken from the worker's word | The PM's own command output is in the ledger |
| Push | Accepted branch | git, host | Task branch only, fast-forward only (R18) | A push to `main` or a forced update | `git ls-remote` shows the task branch, not `main` |
| Report | Reconciled ledger | ledger, chat | Every checklist item is closed with evidence (R16) | "Done" reported with open items | The checklist has no pending or in-progress marks |
| Resume | A new session | ledger, event pool, registry, sweep | The books are reconciled before the first sentence (R17) | The bot continues a stale mental state and reports yesterday's status | Unclaimed `done` records are continued; receipts match acts |

## Wiring order

Build in this order; each step is verifiable before the next depends on it:

1. **Ledger** — write one entry by hand and read it back in a new session.
2. **Dispatch** — launch a trivial task that only writes a file, detached, and read its log.
3. **Completion** — make that task produce a `done` record and a wake; confirm the wake arrives.
4. **Runner and model** — run the same trivial task through the coding agent.
5. **Review** — run a second model family against a trivial diff and collect the 8-field summary.
6. **Routing and second review** — add the table and the static reviewer only after the loop runs.

Steps 1–4 are `MINIMUM.md`. Steps 5–6 are the quality gates in `workflows/feature-dev.md`.

## Reference scripts

`bin/` is a working starting point, not a product. Each script maps to one stage:

| Script | Stage | What it owns |
|---|---|---|
| `bin/pm-config.sh` | all | configuration precedence and input validation |
| `bin/render.py` | dispatch | fills the wrapper template and fails closed on a missing value |
| `bin/dispatch.sh` | dispatch | registry, render, ship, detached launch, optional hook creation |
| `bin/worker-wrapper.sh.template` | execute, monitor, wake | started and done records, completion pings, stall reminder |
| `bin/sweep.sh` | resume | read-only reconciliation of registry, pool, and receipts |
| `bin/smoke-test.sh` | verification | syntax, config, rendering, leaks, language, links; `--live` touches the worker |

What the scripts deliberately do not do: they do not merge, they do not write to `main`, and they do not kill a running task.

## Why the order matters

Every stage hands the next stage a file, a record, or a receipt. If a stage's artifact is missing, the next stage fails in a way that looks like a different problem: a missing registry entry looks like a lost log; a missing receipt looks like a dropped wake; a missing ledger entry looks like the bot forgot. Check the artifact before diagnosing the stage.
