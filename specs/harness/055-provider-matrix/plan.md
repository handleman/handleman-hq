# 055 Provider Matrix — Plan

References `specs/harness/055-provider-matrix/spec.md` AC-1–AC-7 and
`docs/research/providers-2026.md`.

## Approach

One table, four consumers. The registry is data; routing, preflight, pricing
checks and docs generation all read it, so adding a provider is one row plus a
recipe. No behaviour change for the current OpenCode Go profile (its four
prefixes keep their transports).

Order: registry + routing (the silent-fallback bug) → preflight key/base and the
no-key probe → docs → prices. Tests offline throughout.

## Steps

1. **Registry (AC-1/2).** `src/swarm/providers.py`:
   ```python
   @dataclass(frozen=True)
   class Provider:
       name: str; prefixes: tuple[str, ...]; kind: str
       keys: tuple[str, ...]; base_env: str = ""; default_base: str = ""
       catalogue: str = ""      # "" | "public" | "keyed" | "none"
       tools: bool = True; docs: str = ""
       note: str = ""
   PROVIDERS: tuple[Provider, ...] = (...)
   ```
   `resolve(model)` → `Provider | None`; `prefix_of(model)`; `known_prefixes()`.
   `model_config.provider()` delegates; `llms._build` dispatches by `kind`:
   - `native`/`gateway`: `LLM(model=...)` (LiteLLM reads the provider env).
   - `openai_compatible`: `LLM(model=prefix/model, base_url=env, api_key=env,
     custom_openai=True)`; if no base env, LiteLLM's own default.
   - `local`: base from the provider env, `think:false` for Ollama as today.
   - `subscription`: a typed `_ConfigError` pointing at `docs/providers.md`.
   Unknown prefix: error if no `OPENROUTER_API_KEY`, warn + route otherwise.
2. **Key/base validation (AC-3).** In `preflight.check`: for each role model,
   resolve the provider; check at least one key env (or Bedrock/Vertex's
   credential shape, which is checked only for presence of a region/project);
   parse the base URL; verify the id carries the provider prefix (accept the
   bare form only for the four legacy prefixes).
3. **No-key probe (AC-4).** `swarm/providers.py` gains
   `probe(provider, timeout=5)` using `urllib` (already imported in preflight):
   a HEAD/GET on the provider's probe URL; classify 2xx/401/403/404/timeout/5xx
   as above; add the Statuspage JSON for providers that have one
   (`status.openai.com`, `status.anthropic.com`) and public catalogues for
   OpenRouter/SambaNova; probe local providers on their `/api/tags` or
   `/models`. `preflight --probe` and `SWARM_PREFLIGHT_PROBE=1` invoke it; the
   default run stays offline (CI-safe). Results print as a table and are recorded
   in `run.json.preflight` when the flow runs.
4. **Docs (AC-5).** `docs/providers.md`: the matrix, then recipes. Explicit
   "no public temporary key exists" section with the probe semantics and the
   local/subscription alternatives. Link from README, setup, AGENTS and the
   preflight error messages.
5. **Prices (AC-6).** Extend `usage.py` for the first-class families (OpenAI,
   Anthropic, Gemini, Mistral, xAI, DeepSeek, Groq, Together, Fireworks,
   Cerebras, OpenRouter, Go); leave the long tail `unpriced_models` and make
   preflight warn. A test asserts every `native`/`gateway` provider used in the
   example profile has a price row or is intentionally free.
6. **Tests (AC-7).** Golden registry (prefix uniqueness, every prefix resolves,
   no overlaps), routing per prefix, unknown-prefix policy, key/base validation,
   probe classification with a fake opener, and docs completeness (every provider
   appears in `docs/providers.md`).

## Risks

| Risk | Mitigation |
| --- | --- |
| Explicit prefixes break an existing bare-id profile | keep the legacy four prefixes + warn, and validate against the current `.env` in a test |
| The probe makes the suite flaky | mocked opener; network only with `--probe` |
| A provider's catalogue path differs (Perplexity 404) | `catalogue = "none"` + reachability only; documented |
| Price rows go stale | `unpriced_models` + preflight warning; the repo already treats cost as honest-or-none |
| Subscription flows need a proxy | documented as such; never claimed as direct |

## Rollback

Registry additions are data; the unknown-prefix strictness is env-guarded
(`SWARM_STRICT_PREFIXES=0` restores today's silent OpenRouter fallback).
