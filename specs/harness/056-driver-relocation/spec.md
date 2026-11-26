# 056 Driver Relocation (v0.4) — Spec

Harness spec (control plane; the queue never runs it). Design only.

## Problem

v0.3 isolated the app-shaped code under `swarm/drivers/` so the core is
target-agnostic, but the factory still **ships** those drivers:

- `swarm/drivers/e2e.py` builds the frontend and runs `playwright test` from a
  path the harness assumes (`frontend/`) — the target's build command and config
  location are not contract-declared.
- `swarm/drivers/acceptance.py` + `frontend/scripts/acceptance.mjs` know the app's
  Playwright config and dev server.
- `swarm/drivers/smoke.py` and `corridor_check.py` import `app`.
- `db.sh` is the app's Postgres lifecycle.

A factory user with a Python-only or Go repo must edit the package to get a
browser suite or a smoke check. That defeats the packaging.

## Goal

The **target repo owns its drivers**; the harness invokes them as commands
declared in `swarm.yaml` and parses a documented result. The packaged
`swarm.drivers` becomes a fallback so existing users keep working unchanged.

## Contract extension

```yaml
drivers:
  e2e: "python -m drivers.e2e"            # build + run the suite; JSON on stdout
  acceptance: "python -m drivers.acceptance"
  smoke: "python -m drivers.smoke"
  db: "scripts/db.sh"
```

- Each key is optional. Absent → the packaged implementation is used, with a
  one-line warning in `run.json.drivers`.
- Commands run with the target as cwd and the target's `python.venv` on PATH.
- The harness passes a JSON argument for parameters (`--spec`, `--task`,
  `--base-url`) and reads a JSON result on stdout; a non-zero exit is a typed
  stop, not a crash.

### What moves vs what stays

| Module | v0.4 |
| --- | --- |
| `e2e.py` (build + run the suite) | **moves** — the target's build/test commands are its own |
| `acceptance.py` + `acceptance.mjs` (browser probes, screenshots) | **moves** — target-shaped selectors and server |
| `smoke.py`, `corridor_check.py` (import `app`) | **moves** — by construction app-coupled |
| `db.sh` | **moves** — target infrastructure |
| `e2e_triage.py` (parse Playwright output, classify) | **stays** — the output format is Playwright's, not the app's |
| `e2e_guard.py` (assertion counts, weakening) | **stays** — a policy over spec files |
| `health.py` | **stays, command-driven** — runs the target's test + e2e commands |

## Acceptance criteria

- [ ] **AC-1 (declared drivers).** `swarm.yaml` accepts `drivers.{e2e,acceptance,smoke,db}`;
  an absent key falls back to the packaged implementation and records which was
  used (`run.json.drivers`), so a missing driver is visible, never silent.
- [ ] **AC-2 (no app paths in the core).** `grep -rnE "app/|frontend/" src/swarm`
  excluding `src/swarm/drivers/` stays **0**; the core only calls declared
  commands or the packaged fallback.
- [ ] **AC-3 (stable driver protocol).** Every driver takes JSON parameters and
  returns JSON on stdout with `{ok, exit, detail, artifacts}`; a non-zero exit or
  unparseable JSON is a typed stop (`driver_invalid`), not a traceback. One test
  per driver shape with a fake command.
- [ ] **AC-4 (target templates).** `docs/drivers.md` documents the protocol and
  ships copy-paste examples for a Python repo (`pytest` as the "e2e") and a
  Node repo (Playwright), plus how to keep the packaged fallback.
- [ ] **AC-5 (app migration).** `comfort-walking-router` moves its e2e/acceptance/
  smoke/smoke/db drivers to `drivers/` and declares them; `make e2e`,
  `make swarm-accept`, `make smoke-live`, `make swarm-db-*` still pass. No
  behaviour change in a run that uses the packaged drivers.
- [ ] **AC-6 (regression).** Factory tests, ruff, mypy green; a run with no
  `drivers:` block behaves exactly as v0.3.8 (pinned by a test).

## Non-goals

- Moving the acceptance *checks* format (`acceptance.toml` stays in the spec).
- A plugin API beyond "a command that speaks JSON".
- Removing `swarm.drivers` in v0.4 (it stays as the fallback; removal is v0.5).

## Files

- `src/swarm/contract.py` (drivers block), `src/swarm/flow.py`,
  `src/swarm/drivers/*` (fallbacks), `src/swarm/supervise.py`.
- `docs/drivers.md`, `swarm.yaml.example`, `AGENTS.md`.
- Target repo: `drivers/` + `swarm.yaml`.
- `tests/test_drivers.py`, `tests/test_contract.py`.
