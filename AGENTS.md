# AGENTS.md

This repository is a PM workflow package: rules, workflows, and templates for a project manager that lives in a chat.

Read in this order:

1. `README.md` — what this is and what you need.
2. `GLOSSARY.md` — the vocabulary. Use these words exactly.
3. `pm-role.md` — the role and its boundaries.
4. `core/AGENTS.md` — the authoritative standing rules.
5. `workflows/` — the task shapes. Each one cites rule IDs and never restates them.
6. `templates/` — the brief and report formats.
7. `adapters/` — how each tool is wired, one file per tool.

Rules live in exactly one place. If a workflow needs a rule, it cites the rule ID; it does not copy the text. When a rule changes, it changes in `core/AGENTS.md` only.

This package is the upstream. An instance keeps its own environment, project profiles, and secrets in a separate repository and pulls this one in one-way. Do not copy the core into the instance.
