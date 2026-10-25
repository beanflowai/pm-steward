# Stack

Ten capabilities make the loop work. Host, ledger, dispatch, a runner with a model endpoint, and a completion channel are required. Reachability is required only when the worker has no direct route; the rest are quality and convenience. Every capability has a reference implementation and at least one substitute — nothing here is a hard dependency except the shape of the contract.

| # | Capability | What it must provide | Reference | Substitutes | Adapter |
|---|---|---|---|---|---|
| 1 | Bot host | Persistent conversation, wake, hook log/silent, cron, remote shell | Muse | any bot runtime with hooks and scheduled jobs | `adapters/muse.md` |
| 2 | Ledger | Durable task state, re-injected at every session start, per-gate timeline | the host's task board (Goals) | Linear, Notion, SQLite, a JSON file plus a read-first rule | `adapters/ledger.md` |
| 3 | Dispatch | Detached remote launch, log file, PID, registry entry | SSH + `nohup` | Tailscale + SSH, container exec, a cloud job API | `adapters/ssh.md` |
| 4 | Reachability | Reach the worker when it has no public address | Cloudflare Tunnel + Access | Tailscale, WireGuard, a jump host | `adapters/cloudflare-tunnel.md` |
| 5 | Runner | A CLI agent that can edit files, run tests, and stop | Claude Code through ccs profiles | codex CLI, aider, plain `claude` | `adapters/ccs.md` |
| 6 | Model endpoint | An OpenAI- or Anthropic-compatible API | CLIProxyAPI | official APIs, OpenRouter, Bedrock, local vLLM | `adapters/cliproxyapi.md` |
| 7 | Completion channel | Push a wake into the conversation | ntfy + host hook | Slack webhook, queue consumer, chat message | `adapters/ntfy.md` |
| 8 | Routing table | Read model roles at dispatch time | Google Sheets, read-only API | YAML in the instance repo, a database | `adapters/google-sheets.md` |
| 9 | Second reviewer | Independent static review with structured findings | ChatGPT web through DevSpace | an API reviewer, another vendor, a human | `adapters/devspace.md` |
| 10 | Issue tracker | Durable backlog outside the working tree | GitHub issues | any tracker | — |

## The minimum

Five capabilities are enough to run the loop end to end:

1. a host that can hold a conversation and wake it (`adapters/muse.md`)
2. a ledger the bot reads at session start (`adapters/ledger.md`)
3. a way to launch a worker remotely and read its log (`adapters/ssh.md`)
4. a runner with a model endpoint (`adapters/ccs.md`, `adapters/cliproxyapi.md`)
5. a completion channel that wakes the conversation (`adapters/ntfy.md`)

Drop 6–9 and you lose model routing, model diversity, and the second review gate. The workflow still runs; the quality gate is thinner. `MINIMUM.md` walks through the five.

## Prerequisites by capability

| Capability | What the human needs |
|---|---|
| Bot host | Access to a bot that supports hooks and scheduled jobs |
| Ledger | A task-board feature that survives sessions, or a database |
| Dispatch | A worker machine, an SSH key, a user that can run the runner |
| Reachability | Only if the worker is not directly reachable; a Zero Trust account for the reference path |
| Runner | Node plus the runner CLI installed on the worker |
| Model endpoint | API access to at least two model families: one to implement, one to review |
| Completion channel | A push service or a webhook receiver, plus outbound access from the worker |
| Routing table | A Google Cloud project with the Sheets API enabled, or a local file instead |
| Second reviewer | A subscription or API key for a reviewer, or a human reviewer |
| Issue tracker | A repository with issues enabled |

## What is deliberately absent

- No orchestration framework. The PM is one agent with files and a shell; the workers are disposable processes.
- No shared memory between workers. Everything a worker needs is in its brief.
- No dashboard. The ledger and the log are the dashboard.
- No vendor credential recipes. Free credits and borrowed browser sessions change weekly and may violate provider terms; adapters document the interface, not the trick.
