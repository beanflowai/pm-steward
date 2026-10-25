# DevSpace (second reviewer)

The second reviewer is an independent static review after the local commit (R16). The reference implementation is a browsing session in a separate chat product, pointed at the branch through a development workspace.

## Why a browser session

It gives a genuinely separate context and a different model family from the runner, at the cost of depending on a login and a browser automation layer. That is why it is a gate with a fallback, not the core of the workflow.

## The contract

The reviewer must be able to:

- open the repository at the task branch and read the full diff
- read the design document and the brief, to judge scope
- produce findings as structured text: severity, file, line, and why
- **not run tests** — static review only; dynamic verification belongs to the runner and the PM

## Wiring

Per task, record in the ledger entry:

- the project or conversation the review happens in
- the workspace mention that maps to the repository
- the repository path **on the machine that hosts the branch** — the two machines may mount the same project at different paths

Paste the diff or point at the branch; keep the prompt identical when you compare two model families, or the comparison is noise.

## Verification

1. Ask for a review of a deliberately flawed one-file diff; confirm it reports the flaw with a location.
2. Confirm it does not attempt to run commands or tests.
3. Confirm it read the right branch: ask it to quote the commit under review.
4. Repeat with the same prompt through a second family; agreement raises confidence, disagreement goes to the human.

## Known failures

- **Login expired** — the gate stops. Report it; do not silently skip the gate.
- **Wrong workspace** — the review reads another repository or another branch. Always confirm the commit hash.
- **Reviewer runs tests** — the prompt must forbid it; a browser reviewer is not the dynamic gate.
- **Path mismatch** — the branch lives on the other machine; the workspace points at a path that does not have it.
- **Deprecated agent mode** — the older CLI agent mode in this stack is retired. Use the workspace and the browser loop, not the abandoned automation.
- **Unbounded findings** — apply R32; the tail is theoretical edge cases.

## Out of scope

How to obtain or reuse a web session is not documented here. It is fragile, changes without notice, and may violate provider terms. Use an account you are entitled to; if you cannot, use an API reviewer or a human.

## Substitutes

An API-based reviewer from another provider, a local model, or a human reviewer. The gate needs independence and structure, not a specific product.
