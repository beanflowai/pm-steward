# Glossary

Every document in this repo uses these words with exactly these meanings.

**PM (steward)** — the bot that runs the project. It plans, dispatches, keeps the ledger, and accepts or rejects work. It does not merge, release, or decide product direction.

**Task** — one independently deliverable unit of work, dispatched once, with exactly one immutable **task id** in lowercase kebab-case. A feature is split into tasks; each task has its own ledger entry.

**Brief** — the file handed to a worker. It carries context, scope, constraints, acceptance criteria, and the report format. A worker sees only the brief and the repository; it never reads the PM's private notes.

**Worker** — a coding agent that executes one brief on one machine. Workers are stateless and disposable. A worker never merges.

**Reviewer** — an agent that reads a diff independently. A reviewer is always a different model family from the implementer, and it reports in the structured summary, not in prose.

**Second reviewer** — the separate static review after the local commit: a browser session, an API, or a human. It is a gate, not a substitute for the agent reviewer.

**Ledger** — the host's assistant tracking items: one per PM task, server-side, injected into context at the start of every session. It holds the gate checklist, the current pulse, and the evidence timeline. It is not the user's personal goals, and it is not the event pool: the ledger says how far the task has moved, the pool says whether the worker run finished. A workspace note such as `GOAL.md` may mirror an entry when it is created; it is not live and never the ledger.

**Gate** — one mandatory checkpoint in the loop: implement, agent review, local commit, second review, fix rounds, acceptance, push, report. Each pass is recorded in the ledger with evidence.

**Dispatch** — launching a worker on a remote machine so it survives the launching session: detached process, log file, recorded PID, registry entry.

**Registry** — the dispatch record: task id, host, working directory, log path, start time. It is the authority for where a task ran and where its log lives.

**Event pool** — the durable `started` and `done` records written by the dispatch and worker sides.

**Sweep** — the periodic backstop that compares the event pool, the registry, and the received receipts, so a lost wake is still found. It supplements the hooks; it does not replace them.

**Hook** — a host-side subscription that watches the event pool and pushes a message into the chat when a task finishes, stalls, or fails to start. Hooks are per task and remove themselves when they are done.

**Wake** — the message a hook pushes into the conversation. It carries a payload, including the log path. The PM reacts to a wake instead of polling.

**Receipt** — the PM's record that a wake actually arrived in the conversation. Sent and received are separate ledgers; a hook having sent a wake does not prove it arrived.

**Scope drift** — any change outside the brief's stated scope. It is a defect to report, not a bonus to accept.
