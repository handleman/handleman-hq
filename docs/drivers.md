# Drivers — let the target repo own its e2e, acceptance, smoke and db

> Part of the harness documentation. Start at [`../README.md`](../README.md).

The harness core is target-agnostic. Anything that knows a repo's build system,
browser config or database is a **driver**, and a target declares its own in
`swarm.yaml`. When a driver is not declared, the packaged implementation runs so
existing users keep working.

## Declare

```yaml
drivers:
  e2e: "npm --prefix frontend run test:e2e"
  acceptance: "python -m drivers.acceptance"
  smoke: "python -m drivers.smoke"
  db: "scripts/db.sh"
```

Every key is optional. `run.json.drivers` records the source per phase
(`target` or `packaged`), so a missing driver cannot look green.

## Protocol

A driver is a command run with the target as cwd and `SWARM_DRIVER_PARAMS` set to
a JSON object (`{"specs": ["frontend/e2e/walk-mode.spec.ts"], ...}`). It must
print one JSON object on stdout:

```json
{"ok": true, "exit": 0, "detail": "9 passed / 3 skipped", "artifacts": ["frontend/test-results"]}
```

- `exit` (int) is the authoritative result; a non-zero value is a typed stop.
- `detail` is one line for `run.json` / the dashboard.
- `artifacts` are target-relative paths (screenshots, traces).
- A failing driver **without** JSON is still usable (its exit code + tail are
  kept); a *successful* driver that prints no JSON is `driver_invalid` — silence
  is not evidence.

## Examples

### Playwright (Node)

```bash
# drivers/e2e.sh
#!/bin/sh
npm --prefix frontend run build
exec npx playwright test
```

```yaml
drivers:
  e2e: "./drivers/e2e.sh"
```

### pytest as the “e2e” (Python-only repo)

```bash
#!/bin/sh
# drivers/e2e.sh
python -m pytest e2e -q
```

The suite output is parsed by the harness's Playwright-aware triage only when it
uses Playwright; for another runner, provide JSON `detail` (or keep the packaged
fallback and use `drivers.e2e` only for the browser repo).

### Acceptance and smoke

Move the app-specific runner (`frontend/scripts/acceptance.mjs`, a Playwright
smoke script, an `app` import) into `drivers/` and wrap it:

```yaml
drivers:
  acceptance: "python -m drivers.acceptance"   # prints the result JSON
  smoke: "python -m drivers.smoke"
```

### Database

```yaml
drivers:
  db: "scripts/db.sh"
```

The harness calls `db.sh env|up|down|status|migrate` from the target instead of
assuming a Postgres lifecycle.

## Migration checklist

1. Add `drivers:` one key at a time; run `hq preflight` and one task.
2. Compare `run.json.drivers` before/after: `packaged` → `target` for the phase
   you moved.
3. Keep the packaged fallback until the target's driver has passed a real task.
4. If a driver misbehaves, delete its key — the fallback returns immediately.

## Why not a plugin API?

A command that speaks JSON is language-neutral, testable with a shell one-liner,
and cannot import the harness's internals. More than that is a distribution
problem the factory does not need yet.
