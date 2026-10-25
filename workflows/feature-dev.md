# Feature development

> Applies to: new functionality with a design document.
> Preconditions: the design document has passed review and the human has confirmed implementation.
> End state: accepted work on a task branch, pushed, with the ledger reconciled.

## Steps

1. **Read the project rules first** — R10. Confirm the project name, repository paths on every machine involved, and the dispatch entry point.
2. **Open the ledger entry** — R16. The checklist covers every gate; each pass gets a timeline entry with evidence.
3. **Split and plan parallel tracks** — R14, including the four pre-dispatch questions in writing.
4. **Dispatch** — R27 preflight, then R21 for detachment and monitoring. Brief from `templates/brief.md`. Model selection per R28 with the coding role; follow the project's own skills.
5. **Agent review** — R06 and R07. A different agent, a different model family. Findings go back to step 4, with the reviewer summary pasted verbatim into the fix brief (R30).
6. **Local commit** — only after the agent review passes. The worker does not commit; the commit happens at this gate.
7. **Second review** — the static review gate defined by the instance's adapter. Findings are triaged per R31 and convergence per R32.
8. **Acceptance** — read the diff yourself and rerun the checks independently. Scope drift is a defect (R13).
9. **Final push** — R18. Task branch only; merge stays with the human.
10. **Report** — reconcile every checklist item first (R16).

## Gates

- Agent review passed, from a different model family than the implementer.
- Second review passed, or its findings were fixed or explicitly deferred to issues.
- The PM read the diff and reran the tests; the evidence is in the ledger.
- Every checklist item is closed.

## Autonomy boundaries

- The loop runs unattended after the plan is confirmed (R18).
- Stop for: a design conflict, a destructive operation outside the push authority, the second reviewer losing access, or quota exhaustion.
- Merge, release, and anything external stay with the human (R18).
