# Agent brief — <task_id>

## Context

- Project / repo:
- Branch / base:
- Workdir:
- Runner / model:
- Why now:
- Prior coder report / branch (pointer only; the reviewer summary goes in the verbatim block below):

## Previous reviewer structured summary (verbatim)

The PM pastes the previous reviewer structured summary here verbatim, without rewriting, summarizing, paraphrasing, or dropping fields. PM instructions stay in Scope and Constraints, separately, and are never mixed into this block. Reviewer content belongs only here, not in Context. If a field is missing or blank, the PM returns it to the reviewer to complete; `none` is valid when a field truly has no content. First round or no previous review: write `N/A`; do not ship the placeholder.

<paste the previous reviewer structured summary verbatim>

## Scope

- Goal:
- In scope:
- Non-goals:
- Acceptance criteria:
- Tests / evidence required:
- Stop conditions:
- Report format: reviewer reports must include at minimum these sections; definitions follow `templates/report.md`, which is authoritative:
  - `## Status`: done | blocked | failed | needs decision
  - `## Reviewer structured summary` (all 8 fields; write `none` for fields with no content):
    - task_id: reviewed task id (not the review task id)
    - role: reviewer | ui-reviewer
    - files_changed: files changed in the reviewed diff; none if none
    - diff_summary: change summary, no full diff
    - verification: checks/commands actually run and results; none if none
    - assumptions: assumptions behind the review; none if none
    - open_questions: unresolved questions for PM; none if none
    - next_input: inputs/pointers the next agent needs (branch, commit, log path); this review's own changes/handoff stay in `## Changes` / `## Handoff`; none if none
  - `## Findings`: open / closed / deferred to issues
  - `## Handoff`: this review task's own hook / task id, done record or log, next step

## Constraints

- Use a fresh agent: include all context here; do not rely on `--continue` / `--resume`.
- Do not expand scope; report anything outside it instead of fixing it.
- Never merge. Push only if the task authorizes it.
- If blocked, stop and report the exact blocker.
- Write commands step by step, one action per command; do not chain steps with `&&`, do not use subshells, do not combine an action and its self-check into one command (R26).

## References

- Design doc:
- Related issues:
- Skills / project docs:
