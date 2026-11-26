# AGENTS.md — working on handleman-hq

This repo is the **factory**: a spec-driven, model-agnostic agent swarm packaged
for any target repo. The app that exercises it is
[comfort-walking-router](https://github.com/handleman/comfort-walking-router);
it consumes this package — it does not vendor it.

## Rules

- **One source of truth for the target.** `swarm.yaml` (loaded by
  `src/swarm/contract.py`) decides specs dir, scope, gates, e2e, risk, db, the
  python venv and where run traces go (`runs_dir`). Never hardcode a target path in the core; drivers may, and only
  through the contract.
- **Green means evidence.** A task is green only when the reviewer's recorded gate
  exits are 0, the verifier passed and the full suite ran at the final delta.
  A model's prose never decides (`docs/run-guards.md`).
- **Judgement needs reasoning.** Reviewer/verifier get a reasoning model; cheap
  models are for mechanical work. See `docs/model-usage.md` — the rule is backed
  by recorded failures, not taste.
- **Deterministic before paid.** Delta/scope/allowlist guards, e2e triage and the
  acceptance oracle self-test are code with tests; add a test with every guard.
- **Providers are data.** Add one row to `src/swarm/providers.py` and a recipe
  in `docs/providers.md`; never special-case a provider in the flow. An unknown
  prefix is an error (`SWARM_STRICT_PREFIXES=0` is the legacy escape hatch).
- **Spec before code.** Non-trivial changes go through
  `specs/harness/<NNN>-<name>/` (`spec.md` → `plan.md` → `tasks.md`). Small,
  isolated fixes may skip the spec.
- **E2E builds first.** `frontend` aside — a Playwright run must never serve a
  stale `dist/` (054 AC-1); the global setup enforces it.
- **Secrets stay out.** `.env`, keys and tokens never enter the tree; the factory
  audit checks caches, secrets, large blobs and hygiene before a push.

## Commands

```bash
make test          # unit tests (core green with no target tree)
make factory-audit # pre-push: caches, secrets, >1MB blobs, hygiene
make swarm-health  # target app tests + the e2e suite (needs a target)
make swarm-accept  # spec acceptance pass (ARGS="--selftest --strict")
hq --version       # the installed entry point
```

## Where to look

- `README.md` — what it is, quickstart, doc index.
- `docs/how-it-works.md` — roles, phases, the invariant.
- `docs/model-usage.md` — per-role model requirements.
- `docs/run-guards.md` — every deterministic stop and its off switch.
- `docs/testing.md` — unit, browser, replay.
