# Ledger

The ledger is the durable record of what to do and how far each task has progressed. It is the reason a stateless chat can run a project.

## The contract

- **Durable**: survives sessions, context compaction, and a change of runtime.
- **Re-injected**: available at the start of every session without being asked for.
- **Structured**: one entry per task with a checklist, the current step, the next step, and a timeline of gate passes.
- **Append-only for evidence**: gate entries are added, not edited. A correction is a new entry that references the old one.

Injection belongs to the host, not to the tracker. A tracker does not put itself into the context; the host does, or the bot is instructed to read it. Keep those two properties separate when choosing a substitute, because they fail differently: storage failure loses history, injection failure loses presence.

Minimum fields per entry:

| Field | Content |
|---|---|
| task id | the immutable id, matching the registry |
| checklist | done / in progress / pending, one line per gate |
| current state | the current step and the next step |
| timeline | one line per gate pass, with a pointer to its evidence |
| push permission | defaults to yes; exceptions stated |
| links | brief, branch, review window, log |

## Reference implementation

The reference host's task board (Goals). It persists server-side and is re-injected into context at every session start, which is the property that makes it a ledger rather than a note.

## Substitutes

- Linear, Notion, or a database — plus a hard rule that the bot reads the entry before doing anything, because none of them re-inject automatically.
- A JSON file in the instance repository — plus the same read-first rule, and a sweep that warns when an entry has not been touched.

The substitute is acceptable only if the read-first rule is written down. Without it, the bot will work from chat memory and you will not notice until a resume.

## Verification

1. Write an entry by hand.
2. Start a new session and ask for the task status.
3. The bot must answer from the entry, including the next step, without being told where to look.
4. Close one gate and confirm the timeline gained one line with evidence.

## Known failures

- **Chat scrollback used as state.** The classic failure. A compacted context silently forgets, and the bot reports a stale state with confidence.
- **Two ledgers.** A task card plus the task board. They diverge; see R02.
- **Checklist recomputed from memory.** The checklist is read, not reconstructed.
- **Gate marked done without evidence.** The timeline entry must point at a diff, a review, or a command output.
