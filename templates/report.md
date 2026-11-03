# Task report — <task_id>

## Status

done | blocked | failed | needs decision

## Summary

Non-reviewer reports fill this. Reviewer reports may delete it and use the reviewer structured summary below instead.

## Reviewer structured summary

Required for reviewer reports only; non-reviewer reports delete this section. Fill all 8 fields; write `none` when a field truly has no content, and never omit a field. Summary only: no full reasoning, no log text, no full diff. Put only the next agent's pointers (branch, commit, log path) in `next_input`; this report's own changes and handoff stay in `## Changes` / `## Handoff`.

- task_id: reviewed task id (not the review task id)
- role: `reviewer` or `ui-reviewer`
- files_changed: files changed in the reviewed diff; `none` if none
- diff_summary: change summary, no full diff
- verification: checks/commands actually run and results; `none` if none
- assumptions: assumptions behind the review; `none` if none
- open_questions: unresolved questions for PM; `none` if none
- next_input: inputs/pointers the next agent needs (branch, commit, log path); this review's own changes/handoff stay in `## Changes` / `## Handoff`; `none` if none

## Changes

- Files / branches:
- Commit(s):
- Scope drift:

## Tests / evidence

- Commands:
- Results:
- Visual evidence (if UI):

## Findings

- Open:
- Closed:
- Deferred to issues:

## Risks / decisions

## Handoff

This review task's own hook/log, receipt, and next step. Next-agent pointers belong in `next_input`.

- Hook / task id:
- done record or log:
- received receipt written: yes | no
- Next step:
