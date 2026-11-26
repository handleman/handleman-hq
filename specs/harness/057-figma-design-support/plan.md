# 057 Figma Design Support — Plan

## Architecture

```
Figma file ──(REST, token)──► hq design sync ──► designs/<key>/ (committed)
                                                   │  IR + PNG + tokens + brief + lock
                                                   ▼
                                    planner / coder / verifier / design checks
                                                   │
OpenCode operator ──(MCP, OAuth)──► Figma MCP ─────┘  (human lane, not in the queue)
```

Two independent transports, one shared source of truth (the Figma file). The
queue never performs OAuth; the operator lane never writes the cache by hand.

## Phases

### Phase 1 — Contract, IR and sync (AC-1, AC-3, AC-7, AC-9)

- Add `design:` to `contract.py` (`Contract.design: dict`), strict enough to
  catch a typo, tolerant of unknown keys.
- New `src/swarm/design/` package:
  - `figma.py` — REST client (`X-Figma-Token`, timeouts, 429 backoff, size caps,
    redaction).
  - `ir.py` — normalise `/nodes` JSON into the compact IR (stable order, text
    truncation, capped size).
  - `cache.py` — atomic temp-dir → replace; `design.lock` with version + hashes.
  - `brief.py` — derive `design-brief.md` from the IR/tokens.
- `hq design sync|check` (CLI, also `python -m swarm.design`).
- Tests with **recorded JSON fixtures** (no live Figma in tests); a redaction
  test for `access_token`/`X-Figma-Token`.

Verification: `pytest tests/test_design_*.py`, `ruff`, `factory-audit`.

### Phase 2 — Queue wiring (AC-2, AC-3, AC-4, AC-6)

- `design.toml` loader (node, tokens, regions, screenshot) next to `layout.toml`.
- Preflight: token presence + `design check` (typed reasons) before the first
  model call.
- Planner prompt: brief + node scope; coder prompt: brief + reference PNG path;
  verifier: reference PNG + app screenshots.
- Add `designs/` to the immutable/out-of-scope paths; `run.json.design`.
- Offline test: cache present, token unset → planning/checks still work.

Verification: prompt tests (no token/URL), guard tests, a dry flow with a stub
model.

### Phase 3 — Deterministic design checks (AC-5)

- Extend the browser facts payload with computed CSS variables and region rects
  (the existing `.mjs` runner).
- `design_eval.py`: tokens (exact), regions (`tolerance_px`), screenshot diff
  (pixel fraction ≤ threshold), diff images in `<run>/design_diff/`.
- Wire into acceptance and the 042 visual phase; `--strict` (uncovered design AC
  fatal) and `--selftest` (mutate a token/region, expect failure).
- Report columns in `acceptance.md`; the vision note stays advisory.

Verification: evaluator unit tests; a deliberate wrong token/rect fails;
`--selftest` reports OK; diffs written.

### Phase 4 — Docs and OpenCode lane (AC-8)

- `docs/design.md`: contract, cache, commands, checks, security, two lanes.
- `swarm.yaml.example` `design:` block.
- Target repo: `opencode.json` remote MCP entry, `figma-implement` skill,
  `docs/figma.md` (operator + queue lane, auth, seats, desktop fallback).

Verification: docs links, `opencode mcp list`, the skill is discovered.

### Phase 5 — Pilot and release (AC-10, AC-2)

- Sync one real frame from the comfort-walking-router design; implement it in a
  feature spec; design checks green (or a reported threshold) with the stand
  offline.
- Release the factory (`v0.6.0`), pin the app, record the cache in git.

## Risks

| Risk | Mitigation |
| --- | --- |
| Figma OAuth cannot run unattended | REST token + committed cache; OAuth only in OpenCode |
| Token leaks into prompts/logs | token read only in `sync`; redaction test; never a prompt field |
| Design drifts from code | `design.lock` version + `design_stale`; `hq design sync` in the operator loop |
| Screenshot diff is noisy (fonts/AA) | threshold + region/token checks first; diffs are evidence, not the only gate |
| IR grows too large | per-node truncation, size caps, `get_metadata`-style outline first |
| Coder edits the cache | `designs/` out-of-scope; sync is the only writer, atomic |
| Free-tier rate limits | cache by version; 429 backoff; `--force` explicit |

## Definition of done

All ACs checked; factory tests/ruff/audit green; a pilot frame implemented from a
cache with no network during the run; docs merged in both repos.
