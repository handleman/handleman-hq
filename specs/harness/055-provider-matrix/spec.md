# 055 Provider Matrix — Spec

Harness spec (control plane; the queue never runs it). Research:
[`docs/research/providers-2026.md`](../../docs/research/providers-2026.md).

## Problem

The harness routes on four prefixes (`ollama/`, `zen/`, `opencode-go/`,
`openrouter/`) and sends **everything else to OpenRouter**. A user who has an
Anthropic, Gemini, Groq or Copilot key gets a 401 from the wrong provider instead
of "set `ANTHROPIC_API_KEY` and write `anthropic/claude-…`". The provider's own
transport (LiteLLM) already supports ~40 prefixes; only the harness's registry,
key validation, docs and pricing lag.

Two operator realities:

1. **They may not be able to register everywhere.** Claude and GitHub Copilot
   signups fail for some users; the factory must be honest about what works
   without an account (local Ollama/vLLM/LM Studio; a local LiteLLM proxy for
   subscriptions; no-key reachability + public catalogues) and not fake evidence.
2. **A wrong key/base must fail before a paid run.** Today `preflight` checks the
   OpenRouter/Go/Ollama catalogues only; other providers are unvalidated, and a
   typo in a base URL surfaces mid-task.

## Goal

One provider registry drives routing, key/base validation, the reachability
probe, pricing expectations and the docs, so a user can plug any popular
provider's key with clear instructions — and can verify connectivity and base
URLs **without registering anywhere**.

## Acceptance criteria

- [ ] **AC-1 (one registry).** A single `swarm/providers.py` table declares every
  supported provider: name, prefixes, kind (native / OpenAI-compatible / local /
  gateway / subscription), key env names, base-URL env, default base, catalogue
  endpoint (public, keyed, or none), docs URL, tool-calling support. `provider()`
  and `preflight` read it; a test pins the table and its completeness.
- [ ] **AC-2 (routing is explicit).** `SWARM_<ROLE>_MODEL=prefix/model` routes to
  that provider for every entry in the registry (OpenAI, Anthropic, Gemini,
  Vertex, Azure, Bedrock, Mistral, xAI, DeepSeek, Groq, Together, Fireworks,
  Cerebras, SambaNova, Nebius, Hyperbolic, DeepInfra, Moonshot, MiniMax,
  DashScope, Z.AI, Cohere, Perplexity, HuggingFace, NVIDIA NIM, Cloudflare,
  OpenRouter, Copilot, local Ollama/vLLM/LM Studio). An unknown prefix with no
  OpenRouter key is a **preflight error naming the valid prefixes**, never a
  silent OpenRouter call; with an OpenRouter key it warns (back-compat).
- [ ] **AC-3 (key/base validation).** For every provider a role uses, preflight
  checks the key env(s) are set, the base URL (if any) parses as https/http, and
  the model id has that provider's prefix (a `claude-…` id under `anthropic/` is
  fine; a bare one is rejected with the correct example). Bedrock/Vertex
  credential shapes are described, not invented.
- [ ] **AC-4 (no-key connectivity probe).** `preflight --probe` (and
  `SWARM_PREFLIGHT_PROBE=1`) performs a key-free reachability check per used
  provider and classifies: `reachable` (2xx), `auth-required` (401/403 — reachable
  and expected without a key), `wrong-base` (404/3xx loop), `unreachable`
  (DNS/timeout/TLS), `incident` (5xx plus the public status page when available).
  Public catalogues (OpenRouter, SambaNova) and local providers (`ollama`
  `/api/tags`, vLLM/LM Studio `/models`) also verify model ids. No provider is
  claimed to issue a public temporary key; the docs say so explicitly. The probe
  runs in tests against mocked HTTP and never in the unit suite otherwise.
- [ ] **AC-5 (docs a user can follow).** `docs/providers.md` has a matrix (prefix,
  key env, base env, model examples, free tier / subscription, tools) and
  step-by-step recipes: OpenAI, Anthropic/Claude, Google Gemini, Groq, Mistral,
  OpenRouter (including the public no-key model check), local Ollama, a generic
  OpenAI-compatible endpoint, and subscriptions (Claude Pro/Max, ChatGPT/Codex,
  Copilot) via a **local LiteLLM proxy** including Copilot's device flow. Each
  recipe says where to create the key and what to put in `.env`.
- [ ] **AC-6 (honest cost).** `usage.py` covers the supported families' current
  prices (or names the model in `unpriced_models`), and preflight warns when a paid
  model has no price (the dollar cap cannot fire). A `make prices`/table check
  keeps the price map complete for the registry's first-class providers.
- [ ] **AC-7 (offline tests, no behaviour change for the current profile).**
  `pytest`, `ruff`, `mypy` green; the existing Go profile resolves exactly as
  before; no test makes a real network call.

## Non-goals

- Image/audio/video/vector-store providers.
- Registering accounts or storing secrets for the user.
- Claiming a provider works when only its reachability was probed.
- Perplexity for the queue (no tool calling).

## Files

- `src/swarm/providers.py` (new registry), `src/swarm/model_config.py`,
  `src/swarm/llms.py`, `src/swarm/preflight.py`.
- `src/swarm/usage.py` (prices / `unpriced_models`).
- `docs/providers.md` (new), `docs/setup.md`, `swarm.yaml.example`,
  `AGENTS.md`, `README.md`.
- `tests/test_providers.py`, `tests/test_preflight.py`, `tests/test_llms_routing.py`.
