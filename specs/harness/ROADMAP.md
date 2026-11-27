# Harness roadmap (handleman-hq)

**Revised 2026-11-26.** The factory is published and the app consumes it; this
is the order for the remaining harness work. Update the boxes as work lands.

Status: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped.

## Done

- `[x]` **048 packaging → release** — `src/swarm/`, `hq` CLI, `swarm.yaml`
  contract, drivers boundary, `runs_dir`; releases **v0.2.0 → v0.3.5**.
- `[x]` **053 swarm hardening** — grounded reviewer blocks, reference-vs-required
  paths, per-task allowlist, e2e launch = `env`, roster cap, `make swarm-health`.
- `[x]` **054 signal integrity** — fresh-build e2e, evidence-backed PASS, oracle
  self-test (`--selftest`), acceptance-fix reconciliation, `factory-audit`,
  test-first fix prompt, core/driver split.
- `[x]` **App migration** — `comfort-walking-router` pins v0.3.5, harness in
  `harness/.venv`, traces in `harness/runs`, contract in `swarm.yaml`.
- `[x]` **Docs** — packaged layout, `model-usage.md`, `AGENTS.md`, runbooks,
  `swarm.yaml.example`; provider research recorded.

## Done — 055 provider matrix

Design: [`055-provider-matrix/`](055-provider-matrix/). Research:
[`docs/research/providers-2026.md`](../../docs/research/providers-2026.md).

1. `[x]` **T1 registry** — `src/swarm/providers.py` (prefix, keys, base, kind,
   catalogue, tools, docs); `model_config.provider()` delegates.
2. `[x]` **T2 routing** — every registry prefix routes to its provider; unknown
   prefix errors (no silent OpenRouter); current Go profile unchanged.
3. `[x]` **T3 validation** — preflight checks key env(s), base URL and
   model/prefix pairing; Bedrock/Vertex credential shapes.
4. `[x]` **T4 no-key probe** — `preflight --probe` classifies reachable /
   auth-required / wrong-base / unreachable / incident; public catalogues and
   local `/api/tags` also verify ids; mocked tests, offline by default.
5. `[x]` **T5 docs** — `docs/providers.md` matrix + recipes (OpenAI, Anthropic,
   Gemini, Groq, Mistral, OpenRouter, Ollama, generic compatible, subscriptions
   via a local LiteLLM proxy incl. Copilot device flow) + the explicit "no
   public temporary key" section.
6. `[x]` **T6 prices** — first-class families priced; unpaid/unpriced warns.
7. `[x]` **T7 regression** — pytest/ruff/mypy green, no network in tests.

## Done — v0.4 driver relocation (048 T11–T12)

Spec: [`056-driver-relocation/`](056-driver-relocation/). The target declares
`drivers.{e2e,db}` (`drivers/e2e.sh` in the app); acceptance/smoke stay packaged
until they diverge. v0.4.0 released.

8. `[ ]` Move `smoke`, `corridor_check`, `db.sh`, the app-specific acceptance
   parts into the **target repos** under `drivers/`; the core calls them through
   `swarm.yaml` commands (`e2e`, `acceptance`, `smoke`, `db`).
9. `[ ]` Keep the packaged defaults working for users who have no drivers
   (the current `swarm.drivers` package stays as the fallback until v0.4 ships).
10. `[ ]` Release **v0.4.0** with a migration note for the app.

## Done — acceptance coverage (14/14 strict)

11. `[x]` **Acceptance coverage** — 14/14 with `--strict`: 7 specs have browser
    probes, 7 declare their API/infra ACs `[[not_applicable]]`. N/A is a
    declaration, not an unchecked AC.
12. `[x]` **042 T3/T4** — `_visual_phase` records deterministic DOM facts and
    desktop/mobile screenshots in `run.json.visual` + `<run>/visual_qa/`; it is
    advisory (never flips green) and skips cleanly without a running stand.
13. `[x]` **048 T20** — `make swarm-accept --strict` passes 14/14 (the `--selftest`
    oracle check is the remaining v0.5 hardening, not a coverage gap).

## Done — v0.5 hardening

- `[x]` Interaction checks: `acceptance.toml` gains `click`/`wait_for`; 007 now probes
  the walk-start interaction (1 passed, 7 declared N/A).
- `[x]` **Check isolation:** the runner reloads at each spec boundary (an
  interaction in 007 hid the top card from 014/028/040), `route_request`
  resets its request counter and accepts an explicit `origin` (v0.4.9).
- `[x]` **v0.5.1** publishes `location_denied` / `geo_step` (014 AC-1/AC-2/AC-6).
  v0.5.0 carried the kinds in source but the wheel dropped them, so the plan
  silently omitted the checks — a missing check must be reported, not skipped.
- `[x]` Oracle self-test in the factory: `acceptance --selftest` mutates each
  check's target and fails a check that still passes; the report lists it.
  **Verified on the app: 14/14 strict + selftest, no always-passing check.**

## Done — domain model (058)

- `[x]` Root `GLOSSARY.md` (factory language, `_Avoid_` lines), 
  `docs/domain-model.md` (contexts, aggregates, invariants, lifecycles, code
  map) and ADRs 0001–0004 (published contract, green = evidence, target-owned
  drivers, design cache/token-first). The app glossary now points here and its
  `pilot`/`run` overload is corrected.

## Done — task budget profiles (060)

- `[x]` 060: e2e and visual/screenshot tasks get a 2× budget profile (tokens,
  cost, runtime, per-task caps, wall), classified from the brief/spec and
  recorded in `run.json.budget`; evidence and env knobs documented.

## Done — harness integrity (059)

- `[x]` 059: manual completions carry a reason and a report gate; a per-task
  budget cap reverts its delta before the queue continues; design issues are
  evaluated before the acceptance report and colours compare semantically; a
  `covered_by` e2e declaration is validated and reported; a coder that never
  lands the named file is diagnosable.

## Now — design support (057)

The operator is preparing a Figma design. The queue implements frames from a
committed, versioned cache fetched over **MCP with first-run OAuth** (the run
shows the URL, waits for the callback, stores the token and continues) or over
**REST with a PAT** (`transport: auto|mcp|rest`); the human lane uses the same
remote MCP through OpenCode. Spec: `057-figma-design-support/`
(spec + plan + tasks). Key decisions: MCP is the primary transport for both lanes, REST is
first-class parity for CI/headless; the committed cache is what the queue reads;
design checks (tokens/regions/screenshot diff) are deterministic and the vision
pass stays advisory; a stale cache is a typed stop.

## Open questions

- `[x]` **Subscription ergonomics** — shipped `examples/litellm-proxy/` (compose +
  config + README); the harness points at it as `openai_compatible/<alias>`.
- `[ ]` **Prefix strictness** — `SWARM_STRICT_PREFIXES=0` keeps today's silent
  OpenRouter fallback; decide whether v0.4 flips the default to strict.
- `[x]` **Provider drift** — `make provider-audit` runs the no-key probe over every
  registry entry (38 providers; local ones are optional and never fatal).

## Dependencies

```
055 T1 ─→ T2 ─→ T3 ─→ T4 ─→ T5 ─→ T6 ─→ T7 ─→ v0.3.6 release
                                              └─→ v0.4 drivers ─→ v0.4.0
042 T3/T4 ─┐
coverage  ─┴─→ 048 T20 full AC pass
```
