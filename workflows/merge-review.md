# Merge review

> Applies to: the check before a branch goes live.
> End state: a summary report handed to the human. The merge itself is manual (R18).
> Preconditions: the branch is pushed and the task's own gates have passed.

## Steps

1. **Read the project rules first** — R10. Confirm the project, the branch name, the machine the branch lives on, and the repository path.
2. **Read the full diff** — the PM reads `main..<branch>` end to end.
3. **Second review** — mandatory; never skipped on judgment. Runs through the instance's second-reviewer adapter.
4. **Close e2e gaps** — compare the design document against the tests and fill the gaps. Mandatory.
5. **Run the tests** — independently rerun the relevant suites.
6. **Hand the summary to the human** — findings and their closure status, e2e gaps and how they were closed, and the full diff. Wait for the merge instruction.
7. **Dispatch findings fixes** (only after the human confirms) — one finding per task, parallel (R15). Brief from `templates/brief.md`. If an earlier agent review produced a structured summary, paste it verbatim into the brief (R07); if there is none, do not invent one. Preflight per R27, dispatch per R21, coding role per R28.
8. **Re-check after fixes** — return to steps 3 and 5, update the summary, and hand it over again. "Fixes dispatched" is not "closed".

## Gates

- Full diff read by the PM.
- Second review completed.
- e2e gaps closed or explicitly deferred by the human.
- Tests rerun after the last fix.
- Every finding is open with an owner, closed with evidence, or deferred to an issue.

## Autonomy boundaries

- The PM never merges. The human merges.
- A disputed finding may be re-run through another model family with the same prompt; agreement raises confidence, disagreement goes to the human.
