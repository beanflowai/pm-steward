# pm-steward packaging plan

- Date: 2026-10-25
- Status: draft, pending review
- Target repo: https://github.com/beanflowai/pm-steward (public)
- Source instance: private `pm-role-workflow` (stays private; its history is not published)
- Progress (2026-10-25): M1 shipped to `main`; M2 and M3 shipped on `docs/m2-core-docs`; M4 reference scripts are in place but have not been exercised against a real worker yet; M5 waits for a real run transcript.

## 1. Goals and non-goals

**Goal**: let someone replicate their own bot PM and use it for autonomous development. The deliverable is the workflow *and* the tool instructions together, with the workflow told as a composition of tools by stage.

**Non-goals**:

- Not a multi-agent orchestration framework, not a hosted service, not a replacement for Git or an issue tracker.
- No instructions for obtaining free model credits or web-session tokens (fragile, and subject to provider terms).
- No promise of support for every host; only the host contract is promised.

## 2. Two repos, one source of truth

The public and private repos must not each keep a copy of the core rules. That creates two copies immediately, and they drift. A past incident in this project produced two diverging codebases exactly that way.

| Repo | Role | Contents |
|---|---|---|
| public `pm-steward` | **sole upstream** for the generic core | role definition, core rules, workflows, templates, adapters, generic scripts, docs |
| private `pm-role-workflow` | instance layer and live deployment | `environment.md`, `projects/`, `config/pm.env`, live deployment and runtime files |

Sync rules:

1. Changes to generic rules go to the public repo **first**, then upgrade the private instance. Once the layout is adopted (open question 3), the private instance pulls the core one-way into `vendor/core/` or a submodule.
2. Instance changes never flow back. If a lesson turns out to be general, extract it as an anonymous rule and submit it separately.
3. One temporary exception: an urgent fix for a live failure may land privately first, but must flow back to the public repo the same day, with the reason recorded.
4. **Bootstrap exception**: the initial extraction in M2 is a one-time private → public migration. It is not a precedent for later edits.
5. Run the consistency check in section 6 after every upgrade; the only differences allowed are the instance-layer files listed in section 3.

## 3. Public / private boundary

**Public**: `pm-role.md`, the generic core rules, `workflows/`, `templates/`, adapters, genericized scripts, `config/pm.env.example` (sanitized), README / STACK / COMPOSITION / MINIMUM / GLOSSARY / PORTING.

**Private only**:

- `environment.md` (real hosts, paths, runner details)
- `projects/*.md` (client project profiles)
- `config/pm.env` and any real configuration value
- live deployment details (install scripts, real hook paths)

**Out of scope by design**: personal-assistant preference rules. They were removed from the private repo and must not be added here; the public project is a delivery workflow, not a general assistant.

**Pre-publication cleanup** — these appear in the private repo today and also in its git history:

- hostnames, usernames, SSH aliases
- internal and self-hosted domains, ntfy topics
- Google Sheet ids and any API key
- client and internal project names
- commit author and committer addresses (use a GitHub noreply identity)
- identifying details inside lesson entries: keep the *why* behind each rule, remove company, people and machine names. Keep dates; they show how the rules evolved.

**History**: the public repo starts from an empty repo (its current state). Do not push the private history.

## 4. Document skeleton

| File | Question it must answer | Acceptance |
|---|---|---|
| `README.md` | what this is, why the scaffolding is necessary, the minimum you need | a stranger can say "it runs the project inside a chat" after three minutes |
| `GLOSSARY.md` | brief, wake, hook, task id, ledger, event pool, worker, reviewer | each term has one definition, used consistently everywhere |
| `STACK.md` | per capability: reference implementation, substitutes, account prerequisites | every item is replaceable, and the replacement's verification is written down |
| `COMPOSITION.md` | stage × tool matrix, each cell pointing at an adapter | every stage has at least one runnable verification command |
| `MINIMUM.md` | shortest path from zero to a first dispatched task | on a fresh machine, following only this document, a hello-world task is dispatched and collected |
| `config/pm.env.example` | every variable the scripts read, with placeholders | no real values; the smoke test passes with it |
| `PORTING.md` | what to change when swapping host or machine | no real values; everything points at `config` variables |
| `adapters/*.md` | per tool: prerequisites, config variables, wiring, verification, known failures, substitutes | a new reader can configure it unaided; failure entries come from real incidents |

First adapters: `muse`, `cloudflare-tunnel`, `google-sheets`, `cliproxyapi`, `ccs`, `ntfy`, `devspace`.

**Adapter writing constraints**:

- `muse` is written as a **host contract** (persistent conversation, wake, hook-log, cron, remote shell — five interfaces). Muse is only the reference implementation.
- `cliproxyapi` and `devspace` document the interface only (any OpenAI-compatible `base_url`; any reviewer that produces structured findings). No instructions for obtaining credits or web tokens.

## 5. Milestones

| Milestone | Content | Done when |
|---|---|---|
| M1 (this one) | LICENSE, README, this plan | first commit pushed; secret scan clean, including git metadata |
| M2 | `pm-role.md`, core rules, workflows, templates, `GLOSSARY.md` — **translated to English, not copied** | stable rule IDs R01–R34 exist and map to the private rule inventory; no instance identifiers; all links resolve |
| M3 | `STACK.md`, `COMPOSITION.md`, first adapter (`muse`) | an independent implementer can write a stub that answers all five host interfaces from the doc alone |
| M4 | `MINIMUM.md`, `config/pm.env.example`, genericized scripts, smoke test | a blank environment dispatches and collects one task by following `MINIMUM.md` |
| M5 | a real run example (redacted transcript or recording) | the transcript shows task → wake → review → acceptance without unexplained steps |

Each milestone is committed separately, after one independent review.

**M2 is a rewrite, not a copy.** The source documents are Chinese; the public docs are English-only. Translation must preserve rule IDs (stable names), not wording, so the consistency check can compare structure rather than text.

## 6. Acceptance

- **Secret scan**: grep the working tree for real domains, hostnames, emails, sheet ids, keys; also check commit author/committer metadata; then run gitleaks.
- **Rule parity**: compare by rule ID and file inventory once the private instance adopts the public IDs on its first pull. Until then, check the ID range against the private rule inventory by title. Text will differ because the public copy is translated; missing or extra rules are failures.
- **Link check**: every internal link resolves to an existing file.
- **Replication test** (from M4): follow `MINIMUM.md` from zero in a blank environment and dispatch plus collect one task.
- **Terminology**: the words in `GLOSSARY.md` mean the same thing in every document.

## 7. Risks

| Risk | Mitigation |
|---|---|
| If Muse cannot be obtained publicly, replicators stall at step one | write the host as a contract; Muse is a reference only; README never implies a dependency |
| Free-credit and web-token setups are unstable and carry terms-of-service risk | document the interface only |
| The two repos drift | one-way sync plus a rule-parity check after every upgrade |
| Translation silently drops or alters rules | rule-ID parity check; translation reviewed as a rule change, not a copy edit |
| Maintenance cost grows | ship README and the minimum path first; add adapters as they are used |
| Rules detached from their incidents become dogma | keep one sentence of *why* per rule, de-identified |

## 8. Open questions

1. LICENSE holder is `beanflowai` for now; change to a legal name or organization?
2. Should a de-identified transcript of a real run be published? It is the highest-value artifact and also the most expensive to clean.
3. When should the private repo move to the `vendor/core/` or submodule layout? Recommendation: after M2, so the move and the rewrite do not happen at the same time.
