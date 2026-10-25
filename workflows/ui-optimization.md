# UI optimization

> Applies to: visual and interaction work on existing screens — layout, styling, responsive behavior, motion. Not new functionality.
> Preconditions: the target and the acceptance baseline are agreed (design file, reference screenshot, or measurable criteria). Open-ended goals go through `requirement-discussion` first.
> End state: the baseline is met, visual and test evidence are complete, the ledger is reconciled. Merge stays with the human.

## Steps

1. **Read the project rules first** — R10. Confirm the front-end repository path, how the dev server starts, and the dispatch entry.
2. **Read the UI source of truth, in priority order** — design tokens first (colors, type scale, spacing); then the project's UI skill or design system; then any general UI guidance the instance provides. On conflict, tokens win; report the conflict per R33.
3. **Open the ledger entry** — R16. Gates must include both visual evidence and test evidence.
4. **Freeze the baseline before implementing** — reference design or screenshot, measurable criteria, and the breakpoint list: 390 (phone), 768 (tablet), 1440 (desktop). Write per breakpoint:
   - phone: touch target size, safe areas, horizontal gestures, in-app browsers, viewport behavior
   - desktop: hover and focus states, wide multi-column layouts, whitespace on large screens
   - shared: contrast, type hierarchy, visual consistency; every color, size, and spacing value must come from a token — no hard-coded values
   Without a baseline, do not implement.
5. **Capture baseline screenshots** — a worker takes them at all three breakpoints with device emulation before any change.
6. **Split** — by page or component, into independently deliverable units (R14).
7. **Implement** — R27, R21, R34. Brief from `templates/brief.md`.
8. **Agent review** — R06 and R07; `ui-reviewer` role per R28.
9. **Second review** — R16. Mandatory when the change touches logic, data, or calculation; optional for a purely visual change. Findings are triaged per R31 and convergence per R32.
10. **Visual walkthrough** — re-capture all three breakpoints after the change, including mobile emulation (viewport, user agent, touch). The PM looks at the images; a second agent reviews them independently. Compare against the baseline and the design.
11. **Tests** — rerun the relevant unit, component, and e2e suites with the project's own entry points. Include mobile interactions (tap targets, horizontal gestures) in e2e. If the instance provides an audit tool, run its accessibility and responsive checks.
12. **Acceptance** — the PM reads the diff, looks at the images, and reruns the tests. Scope drift is reported (R13).
13. **Push and report** — R18; reconcile the checklist first (R16).

## Gates

- The baseline was frozen and recorded before implementation.
- Before and after screenshots exist at 390 / 768 / 1440.
- Second review completed where R16 requires it.
- Visual walkthrough signed off by the PM and a second agent.
- Relevant tests pass.
- No hard-coded color, size, or spacing; the tokens used are listed in the report.
- No horizontal overflow; tap targets meet the project's standard (default: at least 44px).
- A real-device check cannot be replaced by an emulator. If it was not done, the report must say "emulator only" and the human decides whether to accept.

## Autonomy boundaries

- Pure aesthetic judgments with no baseline ("does this look good") are escalated to the human; the PM does not decide.
- Merge, release, and anything external stay with the human (R18).
