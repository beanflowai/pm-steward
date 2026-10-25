# Glossary

Every document in this repo uses these words with exactly these meanings.

**PM (steward)** — the bot that runs the project. It plans, dispatches, keeps the ledger, and accepts or rejects work. It does not merge, release, or decide product direction.

**Task** — one independently deliverable unit of work. It has exactly one immutable **task id**, written in lowercase kebab-case.

**Brief** — the file handed to a worker. It carries context, scope, constraints, acceptance criteria, and the report format. A worker sees only the brief and the repository; it never reads the PM's private notes.

**Worker** — a coding agent that executes one brief on one machine. Workers are stateless and disposable. A worker never merges.

**Reviewer** — an agent that reads a diff independently. A reviewer is always a different model family from the implementer, and it reports in the structured summary, not in prose.

**Second reviewer** — the separate static review after the local commit: a browser session, an API, or a human. It is a gate, not a substitute for the agent reviewer.

**Ledger** — the durable record of what to do and how far each task has progressed through the gates. It is re-read at the start of every session. Chat history is never the ledger.

**Gate** — one mandatory checkpoint in the loop: implement, agent review, local commit, second review, fix rounds, acceptance, push, report. Each pass is recorded in the ledger with evidence.

**Dispatch** — launching a worker on a remote machine so it survives the launching session: detached process, log file, recorded PID, registry entry.

**Registry** — the dispatch record: task id, host, working directory, log path, start time. It is the authority for where a task ran and where its log lives.

**Event pool** — the durable `started` and `done` records written by the dispatch and worker sides.

**Hook** — a host-side subscription that watches the event pool and pushes a message into the chat when a task finishes, stalls, or fails to start. Hooks are per task and remove themselves when they are done.

**Wake** — the message a hook pushes into the conversation. It carries a payload, including the log path. The PM reacts to a wake instead of polling.

**Receipt** — the PM's record that a wake actually arrived in the conversation. Sent and received are separate ledgers; a hook having sent a wake does not prove it arrived.

**Scope drift** — any change outside the brief's stated scope. It is a defect to report, not a bonus to accept.
