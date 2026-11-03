# Adapters

One file per tool. Each adapter answers: what the tool does in the loop, prerequisites (account, subscription, machine), configuration variables, wiring steps, a verification command, known failures, and what can replace it.

Adapters: [muse](muse.md), [ledger](ledger.md), [ssh](ssh.md), [cloudflare-tunnel](cloudflare-tunnel.md), [ccs](ccs.md), [cliproxyapi](cliproxyapi.md), [ntfy](ntfy.md), [google-sheets](google-sheets.md), [devspace](devspace.md). The hourly sweep runs on the host's cron and is documented with the completion adapter.

## The host contract

Any bot host can replace the reference one if it provides five interfaces:

| Interface | What it must do |
|---|---|
| Persistent conversation | Keep the same identity and context across sessions |
| Wake | Push a message into a conversation from an external event |
| Hook log / silent | Record a hook run, and allow a no-op dry run |
| Cron | Run a prompt or script on a schedule |
| Remote shell | Run commands on a worker machine and read their output |

The PM's state never lives in the host's memory. It lives in the ledger and the event pool. That is what makes the host replaceable.

## Rules for writing an adapter

- Document the interface, not the vendor's credential dance. Free credits and borrowed browser sessions change weekly and may violate provider terms; they do not belong in an adapter.
- Never include real hostnames, accounts, keys, or project names.
- Every known-failure entry must come from an observed failure, not imagination.
- State what can replace the tool. An adapter that only works with one vendor is a lock-in, not a recipe.
