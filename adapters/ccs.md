# ccs (Claude Code runner)

The runner is the coding agent that executes a brief on the worker. The reference is Claude Code driven through a profile switcher, invoked non-interactively.

## The contract

A runner must:

- accept a whole brief as input and run to completion without a human
- edit files and run commands in the repository
- stop at a turn limit instead of running forever
- return a machine-readable result or a log the PM can read
- not commit, merge, or push on its own

## Invocation

```bash
ccs "$PROFILE" --print --output-format json --max-turns "$PM_MAX_TURNS" \
  --dangerously-skip-permissions < "$BRIEF_FILE"
```

- The brief comes from a file. Do not append `</dev/null` after the redirection; it replaces the brief with empty input.
- `--dangerously-skip-permissions` is required for an unattended run. That makes the worker a trusted machine: dedicate it to agents, or run inside a sandbox. Never point it at a laptop with personal credentials.
- `--max-turns` is the safety valve, not a timeout. There is no wall-clock kill (R21); a long tool call can produce no stdout for minutes.

## Profiles

A profile is a named upstream account plus model settings, stored on the worker. Changing a profile file is not enough: a resident proxy process caches the configuration, so restart it after editing. The model names live in the routing table, not in the brief or the workflow (R28).

## Verification

1. Run a one-shot prompt that returns the model name; it must match the routing table entry you selected.
2. Run a prompt that edits a scratch file; confirm the file changed and the JSON result reports success.
3. Run with `--max-turns 1`; confirm it stops and reports the limit instead of hanging.
4. Kill the SSH session; the process must survive (see `ssh.md`).

## Known failures

- **`unrecognized_model`** — the profile points at a model the upstream dropped. Switch per R29; do not retry.
- **Profile inactive** — re-read the routing table before dispatching.
- **Config change ignored** — the proxy is still running with the old settings.
- **Runner missing from the non-interactive `PATH`** — use an absolute path or a login shell.
- **Session killed with exit 143** — the process group was terminated (manual kill, a supervisor, or the launching path). It is not proof of a timeout; triage from the log and the done record.
- **Turn limit reached with work unfinished** — resume the same session when the state cannot move (R30); do not re-dispatch blindly.

## Substitutes

Plain `claude`, `codex`, `aider`, or any CLI agent that runs non-interactively with a turn bound. The requirement is the contract above, not the vendor.
