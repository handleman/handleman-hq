# Provider research — the LLM market, prefixes, and what can be checked without a key

**Date:** 2026-11-26 · **Scope:** every provider a factory user might have, what
the harness supports today, and what can be verified without registering.

## Today's support (the gap)

`swarm/model_config.py` knows exactly four prefixes:

| Prefix | Provider | Transport |
| --- | --- | --- |
| `ollama/` | local Ollama | OpenAI-compatible at `OLLAMA_BASE_URL` |
| `zen/` | OpenCode Zen | OpenAI-compatible gateway |
| `opencode-go/` | OpenCode Go | OpenAI-compatible gateway |
| `openrouter/` | OpenRouter | OpenAI-compatible (`OPENROUTER_BASE`) |
| *anything else* | **OpenRouter** (silent fallback) | — |

So an Anthropic, Gemini, Groq or Copilot id is routed to OpenRouter today, where
the user's OpenRouter key (maybe empty) is used — a confusing 401 rather than
"you need `ANTHROPIC_API_KEY` and an `anthropic/` prefix". `swarm/llms.py` only
builds custom clients for `ollama/`, `zen/`, `opencode-go/`; everything else is
constructed as an OpenRouter `LLM(model=...)`.

## LiteLLM's canonical prefixes (the transport we already ship)

The harness calls models through `crewai` → `litellm`, which routes on
`<prefix>/<model>`. From the LiteLLM provider index (docs.litellm.ai/docs/providers,
fetched 2026-11-26), the prefixes relevant to a coding agent are:

| Prefix | Provider | Key env (LiteLLM) | Base override | OpenAI-compatible API | Notes |
| --- | --- | --- | --- | --- | --- |
| `openai/` | OpenAI | `OPENAI_API_KEY` | `OPENAI_API_BASE` | yes (native) | also Azure-style `openai/` with a custom base |
| `anthropic/` | Anthropic (Claude) | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` / `ANTHROPIC_BASE_URL` | `/chat/completions` translated to `/v1/messages` | Claude also via `azure_ai/claude-*` |
| `gemini/` | Google AI Studio | `GEMINI_API_KEY` | `GEMINI_API_BASE` | yes (`/v1beta/openai/`) | free tier exists, key required |
| `vertex_ai/` | Google Vertex | `VERTEXAI_PROJECT`, `VERTEXAI_LOCATION`, ADC | — | yes | service account / workload identity |
| `azure/` | Azure OpenAI | `AZURE_API_KEY` | `AZURE_API_BASE`, `AZURE_API_VERSION` | yes | deployment names, not model names |
| `azure_ai/` | Azure AI Foundry | `AZURE_AI_API_KEY` | `AZURE_AI_API_BASE` | yes | Claude and others on Foundry |
| `bedrock/` | AWS Bedrock | AWS credentials (`AWS_*`), `AWS_REGION_NAME` | — | yes | SigV4; no key string |
| `mistral/` | Mistral | `MISTRAL_API_KEY` | `MISTRAL_API_BASE` | yes | |
| `xai/` | xAI (Grok) | `XAI_API_KEY` | `XAI_API_BASE` | yes | |
| `deepseek/` | DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API_BASE` | yes | |
| `groq/` | Groq | `GROQ_API_KEY` | `GROQ_API_BASE` | yes | very fast, free tier |
| `together_ai/` | Together AI | `TOGETHERAI_API_KEY` | — | yes | |
| `fireworks_ai/` | Fireworks | `FIREWORKS_AI_API_KEY` | — | yes | |
| `cerebras/` | Cerebras | `CEREBRAS_API_KEY` | — | yes | fast inference |
| `sambanova/` | SambaNova | `SAMBANOVA_API_KEY` | — | yes | public model list |
| `nebius/` | Nebius AI Studio | `NEBIUS_API_KEY` | — | yes | |
| `hyperbolic/` | Hyperbolic | `HYPERBOLIC_API_KEY` | — | yes | |
| `deepinfra/` | DeepInfra | `DEEPINFRA_API_KEY` | — | yes | |
| `moonshot/` | Moonshot (Kimi) | `MOONSHOT_API_KEY` | — | yes | |
| `minimax/` | MiniMax | `MINIMAX_API_KEY` | — | yes | |
| `dashscope/` | Alibaba Qwen | `DASHSCOPE_API_KEY` | — | yes | |
| `qwencloud/` | QwenCloud | provider-specific | — | yes | new in 2026 |
| `zai/` | Z.AI (Zhipu/GLM) | `ZAI_API_KEY` | — | yes | |
| `cohere/` | Cohere | `COHERE_API_KEY` | — | yes (`/v2`) | |
| `perplexity/` | Perplexity | `PERPLEXITYAI_API_KEY` | — | yes | chat only, no tools — not for the queue |
| `huggingface/` | Hugging Face | `HUGGINGFACE_API_KEY` / `HF_TOKEN` | — | yes (router) | |
| `nvidia_nim/` | NVIDIA NIM | `NVIDIA_NIM_API_KEY` | — | yes | |
| `cloudflare/` | Cloudflare Workers AI | `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` | — | yes | |
| `openrouter/` | OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_BASE` | yes | aggregator; public model list |
| `ollama/` | Ollama | none | `OLLAMA_BASE_URL` | yes | local; no key |
| `vllm/` | vLLM | optional | `VLLM_API_BASE` | yes | local/self-hosted |
| `lm_studio/` | LM Studio | none | `LM_STUDIO_API_BASE` | yes | local |
| `openai/` + base | any OpenAI-compatible endpoint | `OPENAI_API_KEY` | `OPENAI_API_BASE` | yes | the generic escape hatch |
| `custom_openai/` | custom provider registered by the gateway | — | — | yes | proxy-side |

Not coding-agent material, but present: image/video/audio providers, vector
stores, rerankers — out of scope.

## Subscriptions (Claude Pro/Max, ChatGPT/Codex, Copilot, Cursor)

LiteLLM supports using a *subscription* instead of an API key, but **only through
a local LiteLLM proxy** (docs.litellm.ai/docs/subscriptions):

- **Claude** (Pro/Max/Team/Enterprise): sign in with Claude Code, proxy relays.
- **ChatGPT/Codex**: sign in with ChatGPT in the client.
- **GitHub Copilot**: OAuth device flow (direct SDK too) or a GitHub App
  installation token; prefix `github_copilot/`, base `https://api.githubcopilot.com`.
- **Cursor CLI**: proxy relay.

Implication: a user without an API key can still run the factory by starting a
local LiteLLM proxy, pointing `SWARM_<ROLE>_MODEL` at the proxy alias, and using
a proxy key. The factory should document this as a first-class path, not pretend
`anthropic/` works without a key.

## What can be verified without registering (evidence, 2026-11-26)

Probed with `curl` from a clean machine, no credentials:

| Endpoint | Status without a key | Meaning |
| --- | --- | --- |
| `https://openrouter.ai/api/v1/models` | **200** | public catalogue — a real no-key check |
| `https://api.sambanova.ai/v1/models` | **200** | public catalogue |
| `http://localhost:11434/api/tags` | **200** (Ollama running) | local provider reachable, no key |
| `https://api.openai.com/v1/models` | 403 | reachable, auth required |
| `https://api.anthropic.com/v1/models` | 403 | reachable, auth required |
| `https://api.groq.com/openai/v1/models` | 403 | reachable, auth required |
| `https://generativelanguage.googleapis.com/v1beta/models` | 403 | reachable, auth required |
| `https://api.githubcopilot.com/models` | 403 | reachable, auth required |
| `https://api.x.ai/v1/models` / `cerebras` / `cohere` | 403 | reachable, auth required |
| `https://api.mistral.ai/v1/models`, `deepseek`, `together`, `fireworks`, `moonshot` | 401 | reachable, auth required |
| `https://api.perplexity.ai/models` | 404 | wrong path; catalogue is elsewhere |
| `https://status.openai.com/api/v2/status.json` | 200 | public status API |
| `https://status.anthropic.com/api/v2/status.json` | 200 | public status API |

**Conclusion:** there is **no major provider that issues a public, temporary
"dev" API key** to unregistered users. The honest no-key checks are:

1. **Reachability probe** (DNS + TLS + one HTTP request): 2xx = reachable;
   401/403 = reachable but auth required; 404 = wrong base path; timeout/DNS =
   unreachable. This catches a wrong `*_API_BASE`, a blocked network, and a dead
   provider **before** a paid run, and never needs a key.
2. **Public catalogues** where they exist (OpenRouter, SambaNova, local Ollama):
   the probe can also validate model ids without a key there.
3. **Status pages** (Statuspage API, public) to say "provider incident" rather
   than "your key is wrong".
4. **Local providers** (Ollama, vLLM, LM Studio) need no registration at all —
   the only fully offline path.

## What this means for the factory

- A **provider registry** must replace the four-prefix table and the silent
  OpenRouter fallback: prefix → provider kind, key env(s), base env, catalogue
  endpoint, docs URL, whether tools are supported, and price-table presence.
- `preflight` must validate keys/base URLs **and** run the no-key reachability
  probe, with a clear verdict per provider used by a role (`ok`, `no-key`,
  `wrong-base`, `unreachable`, `incident`).
- Docs must give a per-provider recipe (where to get the key, what to put in
  `.env`, which model ids work) plus the subscription route via a local proxy.
- Pricing must cover the supported families or name the model in
  `unpriced_models`; a paid model without a price intentionally disables the
  dollar cap, so it must be loud.

## Sources

- LiteLLM provider index and per-provider pages (providers/openai, /anthropic,
  /gemini, /groq, /bedrock, /azure, /vertex, /ollama, /openrouter,
  /github_copilot): https://docs.litellm.ai/docs/providers (fetched 2026-11-26).
- LiteLLM AI subscriptions (Claude/ChatGPT/Copilot/Cursor via proxy):
  https://docs.litellm.ai/docs/subscriptions
- LiteLLM models & pricing: https://models.litellm.ai
- Live HTTP probes recorded in the table above (2026-11-26).
