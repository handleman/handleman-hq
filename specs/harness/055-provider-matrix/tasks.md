# 055 Provider Matrix — Tasks

Each task maps to one acceptance criterion.

- [ ] T1 (AC-1): `swarm/providers.py` registry (name, prefixes, kind, key envs, base env/default, catalogue, tools, docs) + `resolve()`/`known_prefixes()`; `model_config.provider()` delegates; golden tests.
- [ ] T2 (AC-2): `llms._build` dispatches by provider kind; every registry prefix routes to its provider; unknown prefix errors without an OpenRouter key (warns with one; `SWARM_STRICT_PREFIXES=0` restores the old fallback). The current Go profile resolves byte-identically.
- [ ] T3 (AC-3): preflight validates key env(s), base URL shape and the model/prefix pairing for every role; Bedrock/Vertex credential shapes described; messages name the env var and the docs anchor.
- [ ] T4 (AC-4): no-key probe — `preflight --probe` / `SWARM_PREFLIGHT_PROBE=1` classifies reachable / auth-required / wrong-base / unreachable / incident; public catalogues (OpenRouter, SambaNova) and local `/api/tags` also verify ids; mocked-HTTP tests; default stays offline.
- [ ] T5 (AC-5): `docs/providers.md` matrix + recipes (OpenAI, Anthropic, Gemini, Groq, Mistral, OpenRouter, Ollama, generic compatible, subscriptions via local LiteLLM proxy incl. Copilot device flow); explicit "no public temporary key" section; linked from README/setup/AGENTS and preflight errors.
- [ ] T6 (AC-6): `usage.py` prices for the first-class families; preflight warns on an unpriced paid model; test keeps the example profile fully priced or intentionally free.
- [ ] T7 (AC-7): pytest/ruff/mypy green, no network in the suite; one test per AC; `docs/` links valid.
