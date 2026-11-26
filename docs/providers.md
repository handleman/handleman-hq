# Providers — plugging in any model API

> Part of the harness documentation. Start at [`../README.md`](../README.md).

The harness routes on the model id's **prefix** (`<prefix>/<model>`, the LiteLLM
convention) and reads the provider's own environment variables. One registry —
[`src/swarm/providers.py`](../src/swarm/providers.py) — decides what exists; this
page tells you what to put in `.env` for each.

**There is no public “temporary” API key from any major provider.** You need an
account for a hosted model, a subscription plan, or a local model. What you can
verify **without registering** is reachability and your base URL — see
[Checking without a key](#checking-without-a-key).

## Choose your route

| You have | Route |
| --- | --- |
| An API key (OpenAI, Anthropic, Gemini, Groq, …) | `prefix/model` + the provider's key env in `.env` |
| A Claude Pro/Max or ChatGPT/Codex plan | a **local LiteLLM proxy**, then point `SWARM_*_MODEL` at the proxy alias |
| GitHub Copilot | `github_copilot/…` with a device-flow login, or a local LiteLLM proxy for teams |
| No account / offline | local `ollama/`, `vllm/`, `lm_studio/` — no key at all |
| Any other OpenAI-compatible endpoint | `openai_compatible/…` + `OPENAI_COMPATIBLE_BASE` |

## The matrix

| Prefix | Provider | Key env | Base override | Notes |
| --- | --- | --- | --- | --- |
| `openai/` | OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` | |
| `anthropic/` | Anthropic (Claude) | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` | Claude on Azure: `azure_ai/claude-*` |
| `gemini/` | Google AI Studio | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | `GEMINI_API_BASE` | free tier with a key |
| `vertex_ai/` | Google Vertex | service account / ADC | — | `VERTEXAI_PROJECT`, `VERTEXAI_LOCATION` |
| `azure/` | Azure OpenAI | `AZURE_API_KEY` | `AZURE_API_BASE` | + `AZURE_API_VERSION`; deployment names |
| `azure_ai/` | Azure AI Foundry | `AZURE_AI_API_KEY` | `AZURE_AI_API_BASE` | Claude and others |
| `bedrock/` | AWS Bedrock | AWS credentials | — | `AWS_REGION_NAME` |
| `mistral/` | Mistral | `MISTRAL_API_KEY` | `MISTRAL_API_BASE` | |
| `xai/` | xAI (Grok) | `XAI_API_KEY` | `XAI_API_BASE` | |
| `deepseek/` | DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` | |
| `groq/` | Groq | `GROQ_API_KEY` | `GROQ_API_BASE` | very fast, free tier |
| `together_ai/` | Together AI | `TOGETHERAI_API_KEY` | — | |
| `fireworks_ai/` | Fireworks | `FIREWORKS_AI_API_KEY` | — | |
| `cerebras/` | Cerebras | `CEREBRAS_API_KEY` | — | |
| `sambanova/` | SambaNova | `SAMBANOVA_API_KEY` | — | public model list |
| `nebius/` | Nebius | `NEBIUS_API_KEY` | — | |
| `hyperbolic/` | Hyperbolic | `HYPERBOLIC_API_KEY` | — | |
| `deepinfra/` | DeepInfra | `DEEPINFRA_API_KEY` | — | |
| `moonshot/` | Moonshot (Kimi) | `MOONSHOT_API_KEY` | — | |
| `minimax/` | MiniMax | `MINIMAX_API_KEY` | — | |
| `dashscope/` | Alibaba Qwen | `DASHSCOPE_API_KEY` | — | |
| `zai/` | Z.AI (GLM) | `ZAI_API_KEY` | — | |
| `cohere/` | Cohere | `COHERE_API_KEY` | — | |
| `perplexity/` | Perplexity | `PERPLEXITYAI_API_KEY` | — | **no tool calling** — not for the queue |
| `huggingface/` | Hugging Face | `HUGGINGFACE_API_KEY` / `HF_TOKEN` | — | router |
| `nvidia_nim/` | NVIDIA NIM | `NVIDIA_NIM_API_KEY` | — | |
| `cloudflare/` | Cloudflare Workers AI | `CLOUDFLARE_API_KEY` | — | + `CLOUDFLARE_ACCOUNT_ID` |
| `openrouter/` | OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_BASE` | aggregator; `:free` ids cost $0 |
| `vercel_ai_gateway/` | Vercel AI Gateway | `VERCEL_AI_GATEWAY_API_KEY` | — | aggregator |
| `opencode-go/` | OpenCode Go | `OPENCODE_GO_API_KEY` | `SWARM_GO_BASE_URL` | the reference profile |
| `zen/` | OpenCode Zen | `OPENCODE_API_KEY` | `SWARM_ZEN_BASE_URL` | |
| `github_copilot/` | GitHub Copilot | device flow / proxy | `GITHUB_COPILOT_API_BASE` | subscription |
| `chatgpt/` | ChatGPT/Codex | local proxy | — | subscription |
| `ollama/` | Ollama | none | `OLLAMA_BASE_URL` | local, no key |
| `vllm/` | vLLM | none | `VLLM_API_BASE` | local/self-hosted |
| `lm_studio/` | LM Studio | none | `LM_STUDIO_API_BASE` | local |
| `llamafile/` | llamafile | none | `LLAMAFILE_API_BASE` | local |
| `openai_compatible/` | any OpenAI-compatible API | `OPENAI_COMPATIBLE_API_KEY` | `OPENAI_COMPATIBLE_BASE` | generic escape hatch |

Prices live in `src/swarm/usage.py`; a paid model with no price row makes cost
`None` (the dollar cap cannot fire) and is named in `unpriced_models`.
`make swarm-preflight` warns about it.

## Recipes

### OpenAI
1. Create a key at <https://platform.openai.com/api-keys>.
2. `.env`:
   ```bash
   SWARM_PLANNER_MODEL=openai/gpt-5
   SWARM_CODER_MODEL=openai/gpt-5
   SWARM_REVIEWER_MODEL=openai/gpt-5-mini
   SWARM_SENIOR_MODEL=openai/gpt-5
   OPENAI_API_KEY=sk-…
   SWARM_ALLOW_PAID=1
   ```
3. `make swarm-preflight` → every id resolves; `make swarm-preflight ARGS=--probe`
   (or `hq preflight --probe`) proves the endpoint is reachable.

### Anthropic (Claude API)
1. Create a key at <https://console.anthropic.com/>.
2. ```bash
   SWARM_REVIEWER_MODEL=anthropic/claude-sonnet-5
   SWARM_VERIFIER_MODEL=anthropic/claude-sonnet-5
   SWARM_SENIOR_MODEL=anthropic/claude-opus-5
   ANTHROPIC_API_KEY=sk-ant-…
   ```
   Use the strongest model for **review/verification** (`docs/model-usage.md`).
3. A Claude Pro/Max **subscription** is not an API key — see [Subscriptions](#subscriptions).

### Google Gemini
1. Key: <https://aistudio.google.com/apikey> (free tier available).
2. ```bash
   SWARM_CODER_MODEL=gemini/gemini-3-pro
   SWARM_REVIEWER_MODEL=gemini/gemini-3-pro
   GEMINI_API_KEY=…
   ```

### Groq
1. Key: <https://console.groq.com/keys>.
2. `SWARM_CODER_MODEL=groq/llama-4-70b`, `GROQ_API_KEY=gsk_…` (fast, good for the
   mechanical roles; keep a reasoning model on review).

### Mistral
`MISTRAL_API_KEY=…`, `SWARM_CODER_MODEL=mistral/mistral-large`. Base override
`MISTRAL_API_BASE` for a private deployment.

### OpenRouter (aggregator, public model list)
1. Key: <https://openrouter.ai/keys>.
2. `SWARM_CODER_MODEL=openrouter/nvidia/nemotron-3.5-super-vl:free`;
   `:free` ids cost $0. Model ids are public: `curl https://openrouter.ai/api/v1/models`
   works **without a key** — the probe uses it.

### Local Ollama (no account at all)
```bash
ollama serve
ollama pull qwen3.5:9b
SWARM_CODER_MODEL=ollama/qwen3.5:9b
SWARM_REVIEWER_MODEL=ollama/swarm-qa:latest
SWARM_ALLOW_PAID=0
```
`make swarm-local` sets the whole profile in one go. Local models are $0 in the
cost ledger; review quality is what your machine can serve (`docs/model-usage.md`).

### Any OpenAI-compatible endpoint (vLLM, LM Studio, a gateway, a proxy)
```bash
SWARM_CODER_MODEL=openai_compatible/my-model
OPENAI_COMPATIBLE_BASE=https://llm.internal/v1
OPENAI_COMPATIBLE_API_KEY=…        # any string if the endpoint does not check
```

## Subscriptions

LiteLLM can use a personal plan instead of an API key, but **only through a local
LiteLLM proxy** (docs.litellm.ai/docs/subscriptions):

- **Claude Pro/Max/Team/Enterprise** — sign in with Claude Code; the proxy relays.
- **ChatGPT/Codex** — sign in with ChatGPT in the client.
- **GitHub Copilot** — `github_copilot/…` works with a device-flow login in the
  Python SDK; teams can use a GitHub App installation. Through a proxy, connect
  GitHub in the proxy dashboard.
- **Cursor CLI** — proxy relay.

Pattern: start the proxy (`litellm --config …`), create a proxy key, then in
`.env` set `SWARM_CODER_MODEL=<proxy alias>` and let the proxy own the
subscription. The factory never sees your personal token.

> If you cannot create a Claude or Copilot account, use a provider key you *can*
> get (OpenRouter has free models), or run locally. The harness does not pretend
> an account exists.

## Checking without a key

No major provider issues a public temporary key. The honest checks:

```bash
make swarm-preflight                 # ids, keys, base URLs, venvs, gates
make swarm-preflight ARGS=--probe    # + key-free reachability per used provider
SWARM_PREFLIGHT_PROBE=1 make swarm-run
```

The probe hits each used provider's base (or public catalogue/local list) and
classifies:

| Verdict | Meaning |
| --- | --- |
| `reachable` | 2xx — the endpoint is up (public catalogue / local list) |
| `auth-required` | 401/403 — up, and a key is expected (normal without one) |
| `wrong-base` | 404/3xx — your `*_API_BASE` points at the wrong place |
| `unreachable` | DNS/TLS/timeout — network, proxy or firewall |
| `incident` | 5xx — the provider is having a bad day (status page when known) |

Public catalogues verified without a key: **OpenRouter** (`/api/v1/models`),
**SambaNova** (`/v1/models`), local **Ollama** (`/api/tags`). The probe uses them
to validate model ids too. Status pages: `status.openai.com`,
`status.anthropic.com`.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `unknown provider prefix` | the id has no registry prefix — use `anthropic/…`, `gemini/…`, … (this is deliberate: no silent OpenRouter fallback) |
| `set ANTHROPIC_API_KEY …` | the prefix resolved but its credential env is empty |
| `the configured key was rejected` | probe got 401/403 **with** a key set — rotate/check the key |
| `wrong-base` | `*_API_BASE` is missing `/v1`, has a typo, or points at a web page |
| `cost unknown` / cap never fires | add a price row in `usage.py` or accept `unpriced_models` |
| a subscription model errors | start a local LiteLLM proxy and point the role at its alias |

`SWARM_STRICT_PREFIXES=0` restores the old “unknown prefix → OpenRouter” fallback;
it exists only for legacy profiles.
