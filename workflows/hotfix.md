# Hotfix

> Applies to: urgent bugs in a live project.
> Preconditions: the bug is reported and reproducible, or the reproduction is the first step.
> End state: the smallest correct fix, accepted, pushed on a task branch; merge stays with the human.

## Steps

1. **Read the project rules first** — R10.
2. **Open the ledger entry** — R16. Gates: reproduce, diagnose, fix, agent review, local commit, second review, acceptance, push, report.
3. **Reproduce, then find the root cause** — no fix before a reproduced failure.
4. **Diagnose every failure sample** — R19. If time is short, write "diagnose each one first" into the brief.
5. **Fix minimally** — R34. Brief from `templates/brief.md`; dispatch per R27 and R21; coding role per R28.
6. **Agent review** — R06 and R07, a different model family. A failed review returns to step 5 with the summary pasted verbatim. Urgency does not skip a gate.
7. **Local commit** — after the agent review passes.
8. **Second review and findings triage** — R31 and R32.
9. **Acceptance** — rerun the affected tests and confirm no regression.
10. **Final push** — R18, task branch only.
11. **Report** — reconcile the checklist first (R16).

## Gates

- Reproduction recorded before the fix.
- Each failure sample has a stated cause, or the brief says "diagnose each one first".
- The diff stays inside the fix scope.
- Tests pass, including the regression check.
- Agent review and second review both passed or were explicitly handled.

## Autonomy boundaries

- Everything runs unattended after confirmation; urgency never removes a gate.
- Merge, release, and anything external stay with the human (R18).
