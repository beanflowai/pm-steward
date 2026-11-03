# ntfy (completion channel)

ntfy carries the realtime nudge from the worker to the conversation. It is not the source of truth: the event pool is. If a message is lost, the sweep still finds the record.

## The contract

- one **topic per instance**; never share a topic between instances
- basic auth, with credentials in a `600` netrc file rather than on the command line
- the **worker** must reach one URL; the **PM** may reach another (the worker's route to a public hostname is not always the same as the PM's)
- message bodies carry only: `started <task_id>`, `done <task_id> <status>`, `check <task_id>`, `progress <task_id>`
- nothing sensitive in the body: no paths, no branch names, no project names

## Wiring

```
~/.config/pm/ntfy/topic        # per instance, unguessable
~/.config/pm/ntfy/url          # used by the PM-side hook
~/.config/pm/ntfy/worker-url   # used by the worker wrapper
~/.config/pm/ntfy/user
~/.config/pm/ntfy/pass
~/.config/pm/ntfy/netrc        # 600, generated from user/pass
```

The worker wrapper gets a per-task netrc rendered at dispatch time and deleted when the task ends.

## Verification

1. Publish a test message from the worker host: `curl --netrc-file "$NETRC" -d 'ping' "$WORKER_URL/$TOPIC"`.
2. Poll from the PM host with `?poll=1&since=<id>` and confirm the message appears.
3. Confirm the hook's dry run is silent when there is nothing new, and that a real ping produces exactly one wake for that task id.
4. Confirm a wrong topic produces no message rather than an error that looks like a completed task.

## Known failures

- **Whitespace in credentials** — the netrc token is split on whitespace and truncated. Reject spaces and tabs at setup.
- **Worker cannot reach the public URL** — the PM's route is not the worker's route. Test from the worker.
- **Shared topic across instances** — every instance wakes on every message; separate the topics.
- **Message expiry** — default retention is around 12 hours. A hook offline longer than that loses the nudge; the pool and the sweep still recover it.
- **Duplicate wakes** — a reused task id (R25) or a hook that did not disable after completion.
- **Public topic guessed** — an unguessable topic plus auth is the minimum; do not treat the topic name as a secret on its own.

## Substitutes

A Slack or Discord webhook with a consumer, an SQS or Redis queue, or email. What matters is a push path from the worker to the conversation, with retries and a durable backstop.
