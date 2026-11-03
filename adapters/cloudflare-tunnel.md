# Cloudflare Tunnel

Use this only when the worker or the event-pool host has no public address. It is reachability, not part of the workflow.

## What it does here

Two independent uses, which are often confused:

1. **SSH through Access** — the PM reaches the worker with `cloudflared access ssh --hostname %h`.
2. **HTTP exposure** — a service such as the ntfy server is published on a hostname so the worker and the PM can reach it over HTTPS.

## Wiring

SSH, on the PM host:

```
Host <worker-alias>
  HostName <public-hostname>
  User <user>
  ProxyCommand <absolute-path-to-cloudflared> access ssh --hostname %h
```

Keep the binary path absolute (`PM_CLOUDFLARED_BIN`). Hooks and cron run with a different `PATH` than an interactive shell; a bare `cloudflared` will work in your terminal and fail in the hook.

The Access application must authorize the PM's identity for the SSH hostname, and the worker must have the tunnel connector running.

## Verification

```
ssh -o ProxyCommand="$PM_CLOUDFLARED_BIN access ssh --hostname %h" <user>@<public-hostname> 'echo ok'
```

Then run the same command from the hook's environment, not your shell. A tunnel that works interactively and fails in cron is usually the binary path or a missing browser-based auth session.

## Known failures

- **`websocket: bad handshake`** — the connector or the Access policy changed. Check the tunnel status first, not the SSH config.
- **Works in the terminal, fails in the hook** — `PATH`, or an expired Access session that the browser refreshed for you.
- **Hostname mismatch** — the `HostName` in the SSH config must match the Access application, including the subdomain.
- **Tunnel up, origin down** — the connector is fine but the local service is not listening.

## Caveats

Do not make the hook depend on an SSH poll. A tunnel can be up while a single connection is unhealthy, and a polling loop turns that into a blind spot. Use a push channel for completion (see `ntfy.md`) and keep SSH for reading logs on demand.

## Substitutes

Tailscale or WireGuard (a private network instead of a proxy), a jump host, or ngrok. Any of them is fine as long as the PM, the worker, and the completion channel can all reach each other.
