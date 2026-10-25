# Muse — reference host

Muse is the reference implementation of the bot host, not a dependency. Any runtime that provides the five interfaces below can replace it.

## The contract

| Interface | What it must do | Used by |
|---|---|---|
| Persistent conversation | Keep identity and context across sessions | Everything |
| Wake | Push a message into the conversation that owns a hook, from an external event | Completion, sweep |
| Hook log / silent | Record a hook run's outcome, and support a dry run that changes nothing | Every hook |
| Per-hook state | Store a cursor and flags per hook, not globally | Completion |
| Disable after run | Let a hook remove itself | Completion |
| Cron | Run a prompt or script on a schedule | Sweep |
| Remote shell | Run commands on a worker and read the output | Dispatch |

Per-hook state is the one interface that is easy to get wrong: a shared cursor makes two instances steal each other's events.

## Wiring

Hook scripts talk to a shim, never to the host API directly. Point `PM_HOOK_RUNTIME` at the shim; it exports the functions the scripts call:

```bash
# PM_HOOK_RUNTIME=~/hooks/scripts/muse-runtime.sh
wake()              { muse wake --reason "$1" --payload "$2"; }
log_event()         { muse hook-log --message "$1" --data "$2"; }
silent()            { muse hook-silent --message "$1" --data "$2"; }
state_get()         { muse hook-state get --hook "$HOOK_ID" --key "$1"; }
state_set()         { muse hook-state set --hook "$HOOK_ID" --key "$1" --value "$2"; }
disable_after_run() { muse hook-disable "$HOOK_ID"; }
```

The host must also export the hook id, its state directory, and a dry-run flag. A dry run must be silent, must not wake, and must not write receipts.

## Verification

1. Create a hook with an obviously invalid trigger; the dry run must be silent and name the reason (`no new task events` or equivalent).
2. Enable it and confirm it appears as enabled.
3. Push a test event; confirm the wake lands in the conversation that created the hook, not in a side panel or a general inbox.
4. Confirm a completed hook disables itself, and that a stalled notice leaves it enabled.

## Known failures

- **Dry run wakes.** The runtime is running the real path. Fix the runtime, not the script.
- **Wake arrives in the wrong window.** Delivery must be pinned when the hook is created, not resolved at wake time.
- **Shared cursor.** Two tasks interfere. Per-hook state is mandatory.
- **Hook survives completion.** Duplicate wakes on the next task; check disable-after-run.

## Substitutes

Any bot runtime with background events and scheduled jobs: a Slack or Telegram bot with a queue consumer, a chat product with webhooks, or an agent runtime with cron. If it has no wake primitive, add one: a queue with a consumer that posts into the conversation is enough.
