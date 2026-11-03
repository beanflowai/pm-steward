# Google Sheets (routing table)

The routing table is read at dispatch time to pick a model by role and difficulty (R28). A spreadsheet is convenient because a human can edit it without touching a repository; it is not required.

## The contract

One row per profile:

| Column | Meaning |
|---|---|
| `profile` | the runner profile name |
| `model` | the exact model name the endpoint exposes |
| `current_role` | the primary role: architect, coding, reviewer, ui-reviewer |
| `adaptable_roles` | comma-separated fallback roles, including the `research` tag |
| `priority` | integer within a role; lower wins |
| `status` | `active` or anything else; non-active is skipped |
| `provider` | required to prove the reviewer is a different family |
| `ctx_window` | tie-break for research selection |
| `modalities` | what the model accepts (text, image, audio) |

Selection: match the role, ascending priority within it, adaptable roles as fallback, skip non-active, and prefer a dedicated role on a tie. A reviewer must differ from the implementer in `provider` or model line.

## Access

A read-only API key restricted to the Sheets API, stored in the instance configuration — never in this repository and never in a brief. Compose the URL at read time:

```
https://sheets.googleapis.com/v4/spreadsheets/<sheet_id>/values/A1:L1000?key=<key>
```

Always read live. If the request fails, stop and report (R28); do not use a cached copy.

## Verification

1. Fetch the range and confirm nine non-empty header columns.
2. Resolve one role and print the chosen `profile`, `model`, and `provider`.
3. Flip one row's `status` to inactive on a copy of the sheet and confirm it is skipped.
4. Confirm a reviewer selection never returns the implementer's provider.

## Known failures

- **API not enabled** — the Sheets API must be enabled on the Cloud project; the key alone is not enough.
- **Key restricted to the wrong API or referrer** — server-side calls need an API restriction, not an HTTP-referrer restriction.
- **Wrong range** — a shifted column reads as a missing role. Check the header row.
- **Priority stored as text** — sorting becomes lexical (`10` before `2`). Keep the column numeric.
- **Stale cache** — a bot that remembers yesterday's table. Read every dispatch.
- **Rate limits on a busy day** — one read per dispatch, not one per keystroke.

## Substitutes

A YAML or JSON file in the instance repository, or a database. The trade-off is explicit: a file is versioned and reviewable; a sheet is editable by a human without a commit. Either way, the read is live and the failure is closed.
