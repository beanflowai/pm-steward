# CLIProxyAPI (model endpoint)

A proxy that exposes upstream model accounts behind one OpenAI- or Anthropic-compatible API, so the runner can switch models by changing a profile instead of the code.

## The contract

- an **OpenAI-compatible** base URL (`/v1/chat/completions`, `/v1/models`)
- or an **Anthropic Messages** base URL — note that the runner appends `/v1/messages`, so the configured base must not already include `/v1`
- one key or account per upstream, resolved by the profile
- model names that match the routing table

That is the whole contract. How the upstream accounts are obtained is out of scope: free credits and borrowed sessions change weekly and may violate provider terms. Use accounts you are entitled to.

## Wiring

The endpoint belongs in the runner profile on the worker, not in this repository:

```
base_url = https://<your-proxy-host>/v1        # OpenAI-compatible
base_url = https://<your-proxy-host>           # Anthropic Messages (no /v1)
models   = <names listed in the routing table>
```

Keep keys in the worker's profile files or a secret store, never in the instance repository, never in a brief.

## Verification

1. `curl -sS "$BASE/v1/models" -H "Authorization: Bearer $KEY"` lists the expected names.
2. A one-shot completion with the exact model name from the routing table returns 200.
3. The runner's reported model matches the table entry, not a default.
4. With the two families you intend to use, confirm one reviewer call succeeds from the other family.

## Known failures

- **`/v1` duplicated or missing** — the two protocols differ; check the configured base before the model.
- **Model name mismatch** — the table says one alias, the proxy exposes another. Fix the table, not the brief.
- **Quota exhausted** — a known model cause; switch per R29 instead of retrying.
- **Resident proxy caches old config** — restart it after any profile change.
- **Upstream silently changes a model** — the table is read live for this reason; never cache it.
- **Timeout with no response** — check the proxy and upstream separately; the runner will not tell you which one hung.

## Substitutes

Official vendor APIs, OpenRouter, Bedrock, or a local server (vLLM, llama.cpp). Any endpoint that speaks one of the two protocols and exposes a stable model name works; the routing table absorbs the difference.
