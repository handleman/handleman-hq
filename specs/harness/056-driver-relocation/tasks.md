# 056 Driver Relocation (v0.4) — Tasks

Each task maps to one acceptance criterion. Design only until v0.4 starts.

- [x] T1 (AC-1): `swarm.yaml` `drivers.{e2e,acceptance,smoke,db}` parsed into `Contract.drivers`; absent falls back to the packaged implementation and `run.json.drivers` names the source.
- [x] T2 (AC-3): `swarm/drivers/dispatch.py` — JSON params in, `{ok,exit,detail,artifacts}` out; invalid output/exit is a typed stop; one test per shape with a fake command.
- [x] T3 (AC-2): flow/self-heal/health/smoke/db call dispatch; the core keeps triage/guard/evidence; the app-path grep stays 0.
- [x] T4 (AC-4): `docs/drivers.md` protocol + Playwright/pytest/shell examples + fallback rule.
- [ ] T5 (AC-5): app migrates its four drivers to `drivers/` and declares them; `make e2e`, `make swarm-accept`, `make smoke-live`, `make swarm-db-*` pass.
- [x] T6 (AC-6): no-`drivers:` run is byte-for-behaviour v0.3.8; pytest/ruff/mypy green.
