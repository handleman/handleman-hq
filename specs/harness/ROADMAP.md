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

## Now — v0.4 driver relocation (048 T11–T12) — **design done**

Spec: [`056-driver-relocation/`](056-driver-relocation/) (design only; v0.4 starts at T1).

8. `[ ]` Move `smoke`, `corridor_check`, `db.sh`, the app-specific acceptance
   parts into the **target repos** under `drivers/`; the core calls them through
   `swarm.yaml` commands (`e2e`, `acceptance`, `smoke`, `db`).
9. `[ ]` Keep the packaged defaults working for users who have no drivers
   (the current `swarm.drivers` package stays as the fallback until v0.4 ships).
10. `[ ]` Release **v0.4.0** with a migration note for the app.

## Then — coverage and the visual phase

11. `[ ]` **Acceptance coverage** — write `acceptance.toml` for the 11 older app
    specs (001, 004–008, 010, 011, 014, 029, 035, 036; several are API/infra
    ACs with no browser surface — mark those explicitly).
12. `[ ]` **042 T3/T4** — `_visual_phase` is still a stub; wire the per-task
    visual check into the flow with a deterministic fallback.
13. `[ ]` **048 T20** — full AC pass across both repos (`make swarm-accept
    --selftest --strict` once coverage exists).

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
