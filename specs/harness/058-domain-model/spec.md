# 058 Domain Model for the Factory — Spec

Status: implemented · Owner: operator

## What / Why

The factory's language is spread across `docs/` and the target app's glossary. A
new contributor (or a model) cannot reliably tell a **run** from a **pilot**, a
**gate** from **evidence**, a **reviewer** from a **verifier**, or a **driver**
from a **script**. That ambiguity is a real defect source: it produced the
`pilot`/`run` mix-up, a "green" that meant "committed", and acceptance checks
that looked covered because the term "check" was overloaded.

This spec makes the factory's domain model explicit: one glossary, one
structural model, and ADRs for the decisions that are hard to reverse.

## Scope

- `GLOSSARY.md` at the factory root — the ubiquitous language.
- `docs/domain-model.md` — bounded contexts, aggregates, invariants,
  lifecycles, events, boundaries, and the code/doc map.
- `docs/adr/0001…0004` — the hard decisions (publication/contract, green =
  evidence, target-owned drivers, design cache/token-first transport).
- Links from `README.md`, `AGENTS.md`, and the target app's glossary.
- Correct the app glossary's `pilot`/`run` overload in the same change.

## Non-goals

- Changing behaviour, gates or commands.
- Documenting general programming concepts.
- Duplicating the product vocabulary of the comfort-walking-router.
- Turning the glossary into a spec or a scratch pad.

## Acceptance Criteria

- [x] AC-1: **Glossary.** Every bounded context has terms with tight definitions
  and `_Avoid_` lines; no file paths, code identifiers or implementation
  decisions; the target's product terms are not duplicated.
- [x] AC-2: **Model.** `docs/domain-model.md` names the contexts, aggregates
  (contract, spec, task, run, evidence, acceptance, done, design snapshot,
  profile), the invariants, the task/run/design/acceptance lifecycles, the
  events, the boundaries and a code/doc map.
- [x] AC-3: **Decisions.** Four ADRs record the publication/contract split,
  green = evidence, target-owned drivers, and the design cache/token-first
  transport, each with the real alternatives and consequences.
- [x] AC-4: **Discoverability.** The README documentation list, `AGENTS.md` and
  the app glossary point at the glossary, the model and the ADRs.
- [x] AC-5: **Consistency.** `run` vs `pilot`, `green` vs `done`, QA vs
  reviewer, gate vs test, acceptance vs e2e, design check vs visual phase are
  resolved once and used that way; the factory suite and `factory-audit` stay
  green (docs-only change).

## Open questions

- Should the target app keep its harness summary or defer entirely to this
  glossary? It currently keeps a short summary with a link; revisit if the two
  drift.
