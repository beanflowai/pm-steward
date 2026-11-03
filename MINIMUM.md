# Minimum working setup

Five capabilities, in order. Each step ends with a check; do not start the next step until it passes. Everything else in `STACK.md` is optional.

The scripts in `bin/` implement this path. If your host differs, replace the adapter, not the workflow. For a fully specified Muse-based combination, see `builds/muse.md`.

**What you can skip here:** the routing table, model diversity, the second reviewer, and a tunnel. Skip them and the loop still runs; the review gate is thinner. Add them once the loop is boring.

## 0. One worker machine

A machine or VM dedicated to agents — not your laptop, because the runner will have permission to run commands without prompts.

It needs: `git`, `python3`, `bash`, `curl`, the runner CLI, and a repository you are willing to reset.

```bash
ssh <worker> 'command -v git python3 curl; <runner> --version'
```

Expect a path for each, and a version from the runner. A missing `python3` is the most common failure on minimal images.

## 1. Host and ledger

Pick a bot host that can hold a conversation, wake it from an external event, run a scheduled job, and reach the worker (see `adapters/muse.md`). Pick a ledger that is re-read at every session start (`adapters/ledger.md`).

Check: write one ledger entry by hand, restart the session, and ask the bot for the task status. It must answer from the entry, including the next step, without being told where to look.

## 2. Configuration

```bash
cp config/pm.env.example config/pm.env
$EDITOR config/pm.env        # fill in the worker, runner, paths, completion channel
source bin/pm-config.sh && pm_load_config .
./bin/smoke-test.sh
```

Loading the config puts `PM_TASK_DIR` and the other paths in your shell for the commands below. The smoke test checks syntax, configuration, template rendering, dead links, and that no obvious secret is committed; it does not dispatch anything. Set `PM_SMOKE_DENY` to your own hostnames and usernames if you want it to catch those too.

Check: the smoke test exits 0.

## 3. Dispatch a no-op task

Write a brief that asks the worker to create one file and stop:

```bash
mkdir -p "$PM_TASK_DIR/hello-001"
cat > "$PM_TASK_DIR/hello-001/brief.md" <<'EOF'
# Agent brief — hello-001

Create a file named hello.txt in the workdir containing the word ok. Do not commit, do not push.
Report with Status, Changes, and Handoff.
EOF
```

Dry run first:

```bash
PM_CHECK=1 ./bin/dispatch.sh --task-id hello-001 \
  --brief "$PM_TASK_DIR/hello-001/brief.md" --workdir /path/to/repo
```

Then dispatch for real (same command without `PM_CHECK=1`).

Check, in this order:

1. the registry entry exists on the PM host and names `host`, `workdir`, and `log`
2. the wrapper wrote a `started` record on the worker
3. the log file exists and grows
4. the worker wrote `done` with `status=done` and `exit_code=0`
5. `hello.txt` exists in the workdir

## 4. Completion channel

Set up the push channel (`adapters/ntfy.md`), then create the per-task hook **before** the next dispatch — it must be built, dry-run silently, enabled, and listed. If your host adapter provides a hook-creation command, put it in `PM_HOOK_CREATE_CMD`; dispatch runs it before the launch and aborts if it fails. Dispatch ships a per-task netrc to the worker and deletes it when the task ends.

Check: rerun the no-op task. A `done` ping arrives, the hook wakes the conversation that started the task, and the PM writes a receipt.

`./bin/status.sh --task hello-001` should report `done_received` (or `done_sent` before the wake), and `./bin/status.sh --check` should exit 0.

If the ping is lost, the sweep still finds the `done` record. Run `./bin/sweep.sh` and confirm it reports the task.

## 5. Run the loop once

Take a small real task and follow `workflows/feature-dev.md`. At minimum:

1. the ledger entry exists before dispatch
2. one worker implements, a second agent reviews
3. the local commit happens only after that review
4. the PM reads the diff and reruns the check itself
5. the branch is pushed, `main` untouched, the human merges

Check: the reviewer report has all eight fields, and the PM's own command output is in the ledger.

## What you cannot skip

- The ledger is read at session start. Without it you have a chatbot, not a manager.
- Completion wakes the conversation. Without it you will poll, and polling lies when a connection drops.
- The PM verifies. Without it you are trusting an agent's summary of its own work.
