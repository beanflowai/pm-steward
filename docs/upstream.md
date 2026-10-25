# Upstream baseline

pm-steward is derived from a private instance, `beanflowai/pm-role-workflow`. This page records what was ported and how to compare the two repositories mechanically.

## Baseline

| Item | Value |
|---|---|
| Source repository | `beanflowai/pm-role-workflow` (private) |
| Content baseline | `4b6f325` — main as checked out on 2026-10-25 |
| Recorded | 2026-10-25 |

The port started from a working tree on a side branch cut from that commit, not from a later main. The SHA is recorded here because the first port had no baseline, and "what changed upstream" had to be reconstructed from branch reflogs.

## Synced since

| Upstream change | What moved | Where it landed |
|---|---|---|
| `86f0e45` tracking-item clarifications | no rewrite of active entries; evidence in the timeline; plan vs implementation entry | `core/AGENTS.md` R16, `workflows/requirement-discussion.md` |
| UI baseline record | frozen baseline kept as a timeline entry | `workflows/ui-optimization.md` |
| PR #30 read-only status query | `status.sh`, `pm_status.py`, tests | `bin/`, `tests/`, `docs/status-query.md` |

## Deliberate divergences

- **English only.** The source is Chinese; the port is a rewrite, not a copy.
- **No instance values.** Hostnames, paths, accounts, sheet ids, and project names are replaced by configuration variables.
- **Worker-facing brief.** `templates/brief.md` says "do not commit or push unless this brief explicitly authorizes it". The source says "only if the tracking item grants it", which the worker cannot see; push permission lives in the ledger entry (R16) and R18.
- **Adapters split out.** Runner, host, and review mechanics live in `adapters/`; core rules keep only the contract.
- **Personal-assistant rules excluded.** They are out of scope for a delivery workflow.

## Excluded from the port

- `environment.md`, `projects/`, `config/pm.env` — instance layer.
- `agent-runners-ccx-ccs.md`, `chatgpt-static-review.md` — one instance's runner and review notes; the generalised content is in `adapters/ccs.md` and `adapters/devspace.md`.
- `live-deployment.md`, hook installation scripts, cron definitions — deployment of one instance.

## How to sync

1. `git -C <private> fetch origin`
2. `git -C <private> diff --stat <baseline>..origin/main -- pm-reference pm-role.md workflows templates PORTING.md`
3. Classify each change: core rule (port), adapter mechanic (port to `adapters/`), or instance layer (skip).
4. Update the baseline above only when the remaining diff is empty or every change is listed as a deliberate divergence.
5. Generic changes go to this repository first; the private instance pulls them one-way (see `docs/plans/2026-10-25-packaging.md`).
