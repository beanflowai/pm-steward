# Requirement discussion

> Applies to: open-ended questions, ideas, or "should we improve X" requests that have no agreed plan yet.
> Not for: explicit instructions (check this out, investigate this error, fix this known bug) — those run directly, with confirmation as needed.
> Preconditions: none. This workflow sits in front of the implementation workflows.
> End state: a plan the human has explicitly confirmed, or an explicit "don't do it / observe first" conclusion.

## Steps

1. **Read the project rules first** — R10. Then define the problem.
2. **Define the problem** — turn what the human said into a problem statement: current state, pain or goal. Align on what is actually being solved. If the definition is unclear, ask; do not guess.
3. **Research** — read the code, query the data, find existing approaches. Resolve every precondition the plan will depend on: is the tool available, is the permission reachable, has feasibility been proven? Read-only: create no files, change no configuration, touch no machine.
   - Fact-scanning research follows R28's research tag and produces evidence with pointers.
   - Qualitative judgment, option comparison, and plan drafting go to the architect role, or to the PM when the scope is small.
4. **Propose** — alternatives with the reason each was rejected, the recommendation, the affected scope, risks, things explicitly not done, and how it will be verified. Never hand over a plan built on unresolved preconditions.
5. **Wait for confirmation** — an explicit yes is required. If the human pushes back, revise. Do not slide into implementation or into dividing up the work.
6. **Record and hand off** — record the confirmed plan as a design document. When it enters implementation, open a ledger entry for that implementation task. A "don't do it" conclusion gets a short note for later.

## Gates

- The proposal has all five parts: problem, alternatives, recommendation, not-doing list, verification. Missing one is not done.
- Every judgment has evidence (a code location, data), not intuition.
- Every precondition is resolved; if one is open, go back to research.
- Nothing starts before explicit confirmation.

## Autonomy boundaries

- Research runs unattended. The plan always stops for confirmation, and the work split is not discussed before that.
- Merge, release, and anything external stay with the human (R18).
