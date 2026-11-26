# 057 Figma Design Support — Tasks

One task maps to one AC (small tasks may share an AC). Documentation and the
`swarm.yaml.example` change in the same task that introduces the field.

- [ ] T1 (AC-1, AC-9): **Design package + IR.** Add `src/swarm/design/` with
  `figma.py` (REST client: `X-Figma-Token`, timeout, 429 backoff, content-type
  and `max_bytes` caps), `ir.py` (normalise `/v1/files/{key}/nodes` into the
  compact IR: stable order, text truncation, size cap) and tests against
  recorded fixtures. No live Figma in tests.
- [ ] T2 (AC-1, AC-3): **Atomic cache + lock.** `cache.py` writes
  `designs/<key>/` via temp-dir → replace; `design.lock` records the Figma file
  version, node IDs and sha256 per artifact; a second `sync` without `--force`
  is a no-op; only allowlisted nodes are fetched. Unit tests for lock/hash and
  allowlist rejection.
- [ ] T3 (AC-1, AC-7): **Token safety.** Read `design.token_env` (default
  `FIGMA_TOKEN`) only in `sync`; missing → `design_token_missing`; redact
  `X-Figma-Token`/`access_token` from messages, logs and artifacts. Unit test
  feeds a URL with `access_token` and asserts it is absent everywhere.
- [ ] T4 (AC-2, AC-9): **`hq design sync|check`.** CLI + `python -m swarm.design`;
  `--force`, `--spec`; `check` validates the lock/hashes and every `design.toml`
  node without network or a token. Tests: synced cache + no token still passes
  `check`; tampered hash → `design_stale`.
- [ ] T5 (AC-3, AC-6): **Contract + guards.** `Contract.design` parsing and
  validation in `contract.py`; `design.toml` loader; preflight runs `design
  check` before the first model call; typed reasons `design_missing`,
  `design_stale`, `design_node_missing`. `designs/` added to the out-of-scope
  paths and the delta guard. Docs in `swarm.yaml.example`.
- [ ] T6 (AC-4): **Prompts and run record.** Planner gets the brief and the
  node; coder gets the brief + reference PNG path; verifier gets the reference
  PNG + app screenshots. Prompt tests assert the token and raw Figma URLs are
  absent. `run.json.design = {file_key, node, version, stale}`.
- [ ] T7 (AC-5): **Deterministic design checks.** Browser facts gain computed
  CSS variables and region rects; `design_eval.py` checks tokens (exact),
  regions (`tolerance_px`) and the screenshot diff (pixel fraction ≤ threshold),
  writing diffs to `<run>/design_diff/`. Wire into acceptance and 042;
  `--strict` fails an uncovered design AC and `--selftest` proves a wrong token
  or rect fails.
- [ ] T8 (AC-8): **Docs + OpenCode lane.** `docs/design.md` (contract, cache,
  commands, checks, security, two lanes); `swarm.yaml.example` block; target
  repo `opencode.json` remote MCP entry, `figma-implement` skill and
  `docs/figma.md` (remote/desktop, seats, OAuth via `/mcps`).
- [ ] T9 (AC-10): **Pilot.** Sync one real frame, implement it in a product spec
  on the comfort-walking-router, run the design checks offline, record the
  threshold/result. Release the factory (`v0.6.0`) and pin the app.
- [ ] T10 (AC-9): **Suite.** Factory tests for the IR normaliser, lock, checks,
  redaction and guards; `ruff` + `factory-audit` clean; the full factory suite
  stays green.
