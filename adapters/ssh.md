# SSH dispatch

Dispatch means: launch a worker on another machine so that it survives the launching session, and record where it ran and where its log is.

## The contract

On the worker:

- a login user with an SSH key, no interactive password
- the runner on the non-interactive `PATH`
- the repository checked out at the workdir, on the task branch
- a writable log directory
- outbound access to the completion channel

At dispatch time the PM writes:

- a rendered worker wrapper to the worker
- the brief to a path the wrapper reads
- `<task_id>.started.json` in the event pool
- `<task_id>.json` in the dispatch registry: `host`, `workdir`, `log`, `started_at`

## Launch shape

```bash
ssh "$PM_WORKER_SSH_TARGET" "cat > '$remote_wrapper'" < "$rendered_wrapper"
ssh "$PM_WORKER_SSH_TARGET" "cd '$workdir' && nohup bash '$remote_wrapper' > /dev/null 2>&1 & echo \$!"
```

Validate every remote path: no quotes, no newlines, an absolute path. The wrapper writes its own log and its own `done` record; do not rely on the SSH channel for either.

## Verification

1. `ssh "$PM_WORKER_SSH_TARGET" 'command -v "$PM_RUNNER_BIN"'` returns a path.
2. Launch a task that writes one file and exits; the registry and `started` record exist.
3. Kill the local SSH session immediately after launch; the task still finishes and writes its `done` record.
4. Read the log using the registry's `log` value, verbatim.

## Known failures

- **Child dies with the session.** Missing `nohup`/`setsid`, or a command started in the foreground.
- **Runner not on the non-interactive PATH.** Node installs under a version manager are a common cause; use an absolute path or a login shell.
- **Stdin hang.** Run `runner ... < "$brief"` from a file. Do not append `</dev/null` after the redirection; it replaces the brief with empty input.
- **Quoting breakage.** A workdir or branch with spaces or quotes. Reject it at dispatch.
- **Wrong workdir.** The branch exists but the checkout is on another branch. Verify the branch before launch.
- **Log path invented from the task id.** The registry's `host` and `log` are the only contract (R23).

## Substitutes

Tailscale or WireGuard plus SSH, container `exec` with a detached command, or a cloud job API. The requirement is not SSH: it is detached execution plus a durable log and a recorded location.
