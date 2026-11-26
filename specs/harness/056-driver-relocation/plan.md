# 056 Driver Relocation (v0.4) — Plan

References `specs/harness/056-driver-relocation/spec.md` AC-1–AC-6.

## Approach

Introduce the driver block as **data**, keep the packaged implementation as the
fallback, then move the app's drivers in its own repo. Every step is behaviour
preserving when no `drivers:` block is present, so the change can land before the
app migrates.

## Steps

1. **Contract (AC-1).** `Contract.drivers: dict[str, str]` from
   `drivers: {e2e, acceptance, smoke, db}` (each optional, a command string).
   Validate: a string, no shell metacharacters beyond a normal command line.
2. **Dispatch (AC-3).** `swarm/drivers/dispatch.py`:
   ```python
   def run(kind, *, params, timeout) -> DriverResult
   ```
   - declared command → `subprocess.run(shlex.split(cmd) + ["--params", json], ...)`,
     parse stdout JSON, exit code; invalid output → typed stop.
   - absent → import the packaged implementation (`e2e.main`, `acceptance.run`,
     `smoke.main`, `db`), same result shape.
   - record `{kind, source: "target"|"packaged", exit}` in `run.json.drivers`.
3. **Flow wiring (AC-1/2).** `_run_e2e_deterministically`, `_e2e_self_heal`'s
   runner, the acceptance call in `supervise`, the health check and smoke/db
   targets call `dispatch.run`. The core keeps triage/guard/evidence; only the
   runner is a command.
4. **Protocol + docs (AC-3/4).** `docs/drivers.md`: parameters JSON, result JSON,
   exit codes, examples (Playwright, pytest-as-e2e, a shell db script), the
   fallback rule, and how to migrate a repo incrementally.
5. **App migration (AC-5).** In `comfort-walking-router`: `drivers/e2e.py`,
   `drivers/acceptance.py`, `drivers/smoke.py`, `drivers/db.sh`; `swarm.yaml`
   `drivers:` block; Makefile targets unchanged; verify e2e/acceptance/smoke/db.
6. **Regression (AC-6).** A test builds a run with no `drivers:` and asserts the
   packaged path is used; a test with a fake command asserts the JSON protocol
   and the typed stops.

## Risks

| Risk | Mitigation |
| --- | --- |
| The app's driver scripts drift from the harness expectations | the JSON protocol is versioned in `docs/drivers.md`; a factory test pins it |
| A user's driver hangs | the same crew/timeout budgets apply; the dispatch uses a bounded timeout |
| Two sources of truth during migration | `run.json.drivers` records which was used per phase |
| Acceptance screenshots live in the app | the result JSON returns artifact paths relative to the target |

## Rollback

If a target declares a broken driver, remove the `drivers:` key (the packaged
fallback is used) without touching the harness; the dispatch records the source.
