# Read-only delivery status

`bin/status.sh` summarises the dispatch registry and the sent/received ledgers into a table or JSON. It is the script-first half of status reporting: deterministic questions go to the script, and the PM only interprets the result.

## Scope (v1)

| Question | Answered? | Source |
|---|---|---|
| Was the wake sent? | yes | the sent ledger |
| Did the wake arrive in a conversation? | yes, for trusted sources only | the received ledger |
| Is something possibly lost, overdue, or flagged? | yes | send time, registry age, sent/received kinds |
| Did the task succeed or fail? | **no** | needs `done` records and exit codes; v1 does not read them |
| Has the ledger entry advanced? | **no** | needs the tracking item's timeline; v1 does not read it |

v1 answers the delivery half only. `received kind=done` proves the wake arrived; it does not prove the task completed, that the result was accepted, or that the ledger advanced. For completion, read the done record and the log, then check the tracking item. This is the two-layer split from R16: the ledger says how far the task got, the event pool says whether the worker run finished.

## Usage

```bash
bin/status.sh                    # last 7 days, table
bin/status.sh --json             # stable JSON
bin/status.sh --all              # every task
bin/status.sh --days 14          # time window
bin/status.sh --task <task_id>   # one task, ignores the window
bin/status.sh --check            # exit 1 when delivery needs attention
```

- `--all` and `--days` are mutually exclusive; `--days` must be a positive integer.
- `--task` accepts `^[a-z0-9][a-z0-9-]*$` only and never builds a path from it. A missing task prints to stderr and exits 0.
- `--json --check` prints the JSON first, then returns the exit code.
- `--check` covers the window; for a full reconciliation use `--all --check`.
- Historically `unknown` rows can keep `--check` at 1 for a long time. Do not wire it directly as a merge gate; query the current task with `--task` and triage history separately.
- Table order: actionable first, then state order, then age descending. Within the actionable group the order is not urgency.

## Sources (read-only)

| Source | Path | Meaning |
|---|---|---|
| dispatch registry | `$PM_REGISTRY_DIR/<task_id>.json` | the dispatch exists; `started_at`, `host`, `log` |
| sent ledger | `$PM_SENT_LEDGER` (default `$PM_STATE_DIR/handoff-sent.jsonl`) | a wake was sent, not that it arrived |
| received ledger | `$PM_RECEIPTS` (default `$PM_STATE_DIR/handoff-received.jsonl`) | a wake arrived, not that the task completed |

Trusted received sources default to `pm,PM,watchdog` and can be replaced with `PM_STATUS_TRUSTED_SOURCES`. A `source=hook` or unknown source is ignored with a warning, which blocks historical pollution from an older implementation that wrote sent records into the received ledger.

## States

| State | Meaning | Actionable |
|---|---|---|
| `done_received` | a trusted done wake arrived; completion is still unverified | no |
| `failed_recorded` | a trusted `received kind=failed` (legacy task-result receipt); does not mean done arrived | no, visibility only |
| `done_sent` | done sent, under 60 minutes | no |
| `done_overdue` | done sent 60–120 minutes ago, no receipt; the sweep may still catch up | no |
| `done_lost` | done sent at least 120 minutes ago, no receipt; likely lost | yes |
| `orphan` | no registry, but a sent done or a trusted terminal receipt | yes |
| `unconfirmed` | registry exists, no completion evidence; may be running, or the notification path is already broken | no, unless it carries `stale` or a flag |
| `unknown` | corrupt registry, or no registry and only untrusted evidence | yes |

Classification order: corrupt registry → `unknown`; no registry + terminal evidence → `orphan`; registry + trusted terminal receipt → `done_received` / `failed_recorded`; registry + sent done → `done_sent` / `done_overdue` / `done_lost`; registry only → `unconfirmed`.

`done_lost` means "likely lost on the ledger". The PM may have continued the task without writing a receipt with `source=pm`. Follow the hint: read the done record, the log, and the tracking item before calling it an actual loss.

`unconfirmed` does not mean "confirmed still running". `failed_recorded` never triggers `--check`, which covers the delivery path only, not whether a failure was handled.

## Flags

| Flag | Condition | Shown on |
|---|---|---|
| `failed_to_start` | a sent or trusted received record carries that kind | `unconfirmed` only |
| `possibly_hung` | a sent or trusted received record carries that kind | `unconfirmed` only |
| `stale` | `unconfirmed` and dispatched at least 7200 seconds ago | `unconfirmed` only |

Any terminal state suppresses `failed_to_start` and `possibly_hung`; the history remains in the `sent` and `received` arrays. `check_reminder` is reported as the latest event, not as a flag.

## Received kinds

| Kind | Meaning | Counts as done arrived? | Effect |
|---|---|---|---|
| `done` | the current contract: a done wake arrived | yes | `done_received` (`orphan` without a registry) |
| `failed` | legacy task-result receipt, not a wake kind | no | `failed_recorded` (`orphan` without a registry) |
| `possibly_hung` | suspected stall event | no | adds a flag when `unconfirmed` |
| `failed_to_start` | start failure event | no | adds a flag when `unconfirmed` |
| `check_reminder` | log and worktree stopped changing | no | appears in the arrays and as the latest event only |
| anything else | unknown event | no | ignored with a warning |

Multiple trusted terminal receipts take the latest `received_at`; on a tie, `done` wins. `kind=failed` is a legacy form (before 2026-10-21); new receipts are `kind=done` plus a `status` field. v1 keeps handling both.

## Windows and missing data

- Default 7 days; `--all` for everything; `--task` ignores the window.
- Inclusion time is `max(dispatched_at, latest sent.at, latest received.at)`.
- `unknown` is always included.
- All timestamps missing: with a registry, the task is included with `age_secs=null` and a `MISSING_TIMESTAMP` warning; without a registry but with terminal evidence, it is included as `orphan`; without either, it is not listed, only warned.
- The registry filename is the primary key. A mismatched internal `task_id` yields `unknown` plus a warning that names the file; a missing internal id falls back to the filename with a warning.
- A registry read is retried once; a second failure yields `unknown` without affecting other tasks.
- Invalid UTF-8 in a registry (for example, a brief truncated by byte count) is read with `errors="replace"` and a `REGISTRY_ENCODING_REPLACED` warning; `task_id`, `host`, `log`, and `started_at` are still recoverable. Structurally broken JSON stays `unknown`.
- Legacy sent lines that use `received_at` instead of `sent_at` are dropped with a warning.

## JSON example

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-25T12:00:00Z",
  "window_days": 7,
  "coverage": ["registry", "sent", "received"],
  "not_checked": ["done.json", "tracking_item"],
  "counts": {
    "unconfirmed": 1,
    "done_sent": 0,
    "done_overdue": 0,
    "done_lost": 1,
    "done_received": 1,
    "failed_recorded": 1,
    "orphan": 0,
    "unknown": 0
  },
  "tasks": [
    {
      "task_id": "example-task",
      "state": "unconfirmed",
      "actionable": false,
      "flags": [],
      "dispatched_at": "2026-10-25T11:48:00Z",
      "age_secs": 720,
      "host": "<worker>",
      "log": "<worker-log-path>",
      "sent": [{"kind": "check_reminder", "at": "2026-10-25T11:52:00Z"}],
      "received": [],
      "hint": "no receipt != still running"
    }
  ],
  "warnings": []
}
```

- The registry's brief excerpt, notification credentials, and SSH configuration are never output.
- The log path appears only in the JSON `log` field; the table shows the short log line.
- `warnings` contains `code`, `file`, `line`, and `message` only, never the raw record.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | normal, or `--check` found nothing actionable |
| 1 | `--check` found an actionable state or flag |
| 2 | missing configuration, bad arguments, invalid `PM_STATUS_NOW`, or python3 / pm-config.sh unavailable |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PM_STATE_DIR` | required | registry and ledger directory |
| `PM_REGISTRY_DIR` | required | dispatch registry |
| `PM_SENT_LEDGER` | `$PM_STATE_DIR/handoff-sent.jsonl` | sent ledger |
| `PM_RECEIPTS` | `$PM_STATE_DIR/handoff-received.jsonl` | received ledger |
| `PM_STATUS_WINDOW_DAYS` | 7 | default window; `--days` overrides |
| `PM_STATUS_DONE_OVERDUE_SECS` | 3600 | `done_sent` → `done_overdue` |
| `PM_STATUS_DONE_LOST_SECS` | 7200 | `done_overdue` → `done_lost` |
| `PM_STATUS_STALE_SECS` | 7200 | `unconfirmed` + `stale` |
| `PM_STATUS_TRUSTED_SOURCES` | `pm,PM,watchdog` | trusted received sources |
| `PM_STATUS_NOW` | current UTC | injected clock for tests and reconciliation; an invalid value exits 2 |

`status.sh` loads `pm.env` first. Without configuration it fails closed with exit 2 and never falls back to a default state directory. It then uses `env -i` to pass only these variables to Python, so notification credentials, SSH settings, and model keys never enter the query.

## Read-only guarantees

- The registry and both ledgers are opened read-only. No receipt is written, no hook state is changed, no file is removed.
- No SSH, no curl, no notification call.
- Python runs with `-B`, so no `__pycache__` is written.
- Tests cover read-only behaviour, environment isolation, and the absence of network calls:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

## Next

- `--remote` to read done records and add task result and exit code.
- Read hook runtime state to add started evidence.
- Integrate with atomic claims.
- Record `failed` as a legacy kind in the core vocabulary; new receipts must not use it.
