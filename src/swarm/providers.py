"""One registry of model providers (055 AC-1).

Routing, preflight, pricing checks and the docs all read this table. A provider
is one row: its prefix(es), the environment variables that carry its credential
and base URL, the transport kind, whether a catalogue can be listed, and whether
it can call tools.

Prefixes follow LiteLLM (`<prefix>/<model>`, docs.litellm.ai/docs/providers),
with two harness aliases: `opencode-go/` (the harness's historical id) and
`zen/` (OpenCode Zen).

Kinds:

* ``native`` — LiteLLM knows the provider; it reads its own env vars.
* ``gateway`` — an aggregator that needs an explicit base URL/key (OpenRouter,
  OpenCode Go/Zen).
* ``local`` — no key; the base URL comes from the environment.
* ``subscription`` — a personal plan, usable only through a local LiteLLM proxy
  (Claude Pro/Max, ChatGPT/Codex) or a device flow (GitHub Copilot).
* ``openai_compatible`` — any endpoint that speaks the OpenAI API.

`catalogue` says how model ids can be checked: ``public`` (no key needed),
``keyed`` (a key is needed), ``none`` (no list endpoint worth calling).
"""

from __future__ import annotations

from dataclasses import dataclass

LITELLM_DOCS = "https://docs.litellm.ai/docs/providers/"


@dataclass(frozen=True)
class Provider:
    name: str
    prefixes: tuple[str, ...]
    kind: str
    keys: tuple[str, ...] = ()
    base_env: str = ""
    default_base: str = ""
    catalogue: str = "none"
    probe_suffix: str = "/models"
    tools: bool = True
    docs: str = ""
    note: str = ""

    def matches(self, model: str) -> bool:
        return any(str(model).startswith(prefix) for prefix in self.prefixes)


def _p(
    name: str,
    prefix: str,
    key: str,
    *,
    kind: str = "native",
    base_env: str = "",
    default_base: str = "",
    catalogue: str = "keyed",
    probe_suffix: str = "/models",
    tools: bool = True,
    docs: str = "",
    note: str = "",
    extra_prefixes: tuple[str, ...] = (),
    extra_keys: tuple[str, ...] = (),
) -> Provider:
    return Provider(
        name=name,
        prefixes=(prefix, *extra_prefixes),
        kind=kind,
        keys=(key, *extra_keys) if key else (),
        base_env=base_env,
        default_base=default_base,
        catalogue=catalogue,
        probe_suffix=probe_suffix,
        tools=tools,
        docs=docs or f"{LITELLM_DOCS}{name}",
        note=note,
    )


# First-class providers a coding agent can use. Order is display order; prefix
# matching is exact (`azure/` does not match `azure_ai/`).
PROVIDERS: tuple[Provider, ...] = (
    _p("openai", "openai/", "OPENAI_API_KEY", base_env="OPENAI_API_BASE",
       default_base="https://api.openai.com/v1"),
    _p("anthropic", "anthropic/", "ANTHROPIC_API_KEY", base_env="ANTHROPIC_API_BASE",
       default_base="https://api.anthropic.com",
       note="Claude API; Azure Foundry uses azure_ai/claude-*"),
    _p("gemini", "gemini/", "GEMINI_API_KEY", base_env="GEMINI_API_BASE",
       default_base="https://generativelanguage.googleapis.com",
       probe_suffix="/v1beta/models",
       extra_keys=("GOOGLE_API_KEY",), note="Google AI Studio, free tier with a key"),
    _p("vertex_ai", "vertex_ai/", "", kind="native", catalogue="none",
       note="service-account/ADC: VERTEXAI_PROJECT + VERTEXAI_LOCATION"),
    _p("azure", "azure/", "AZURE_API_KEY", base_env="AZURE_API_BASE",
       catalogue="deployment", note="deployment names + AZURE_API_VERSION"),
    _p("azure_ai", "azure_ai/", "AZURE_AI_API_KEY", base_env="AZURE_AI_API_BASE",
       note="Azure AI Foundry (Claude and others)"),
    _p("bedrock", "bedrock/", "", catalogue="none",
       note="AWS credentials (AWS_ACCESS_KEY_ID / PROFILE) + AWS_REGION_NAME"),
    _p("mistral", "mistral/", "MISTRAL_API_KEY", base_env="MISTRAL_API_BASE",
       default_base="https://api.mistral.ai/v1"),
    _p("xai", "xai/", "XAI_API_KEY", base_env="XAI_API_BASE",
       default_base="https://api.x.ai/v1"),
    _p("deepseek", "deepseek/", "DEEPSEEK_API_KEY", base_env="DEEPSEEK_API_BASE",
       default_base="https://api.deepseek.com"),
    _p("groq", "groq/", "GROQ_API_KEY", base_env="GROQ_API_BASE",
       default_base="https://api.groq.com/openai/v1"),
    _p("together_ai", "together_ai/", "TOGETHERAI_API_KEY",
       default_base="https://api.together.xyz/v1", extra_prefixes=("togetherai/",)),
    _p("fireworks_ai", "fireworks_ai/", "FIREWORKS_AI_API_KEY",
       default_base="https://api.fireworks.ai/inference/v1"),
    _p("cerebras", "cerebras/", "CEREBRAS_API_KEY",
       default_base="https://api.cerebras.ai/v1"),
    _p("sambanova", "sambanova/", "SAMBANOVA_API_KEY",
       default_base="https://api.sambanova.ai/v1", catalogue="public"),
    _p("nebius", "nebius/", "NEBIUS_API_KEY",
       default_base="https://api.studio.nebius.ai/v1"),
    _p("hyperbolic", "hyperbolic/", "HYPERBOLIC_API_KEY",
       default_base="https://api.hyperbolic.xyz/v1"),
    _p("deepinfra", "deepinfra/", "DEEPINFRA_API_KEY",
       default_base="https://api.deepinfra.com/v1/openai"),
    _p("moonshot", "moonshot/", "MOONSHOT_API_KEY",
       default_base="https://api.moonshot.ai/v1"),
    _p("minimax", "minimax/", "MINIMAX_API_KEY",
       default_base="https://api.minimax.io/v1"),
    _p("dashscope", "dashscope/", "DASHSCOPE_API_KEY",
       default_base="https://dashscope.aliyuncs.com/compatible-mode/v1"),
    _p("zai", "zai/", "ZAI_API_KEY", default_base="https://api.z.ai/api/paas/v4"),
    _p("cohere", "cohere/", "COHERE_API_KEY", default_base="https://api.cohere.com"),
    _p("perplexity", "perplexity/", "PERPLEXITYAI_API_KEY", tools=False,
       default_base="https://api.perplexity.ai", catalogue="none",
       note="chat only — no tool calling, so not usable for the queue"),
    _p("huggingface", "huggingface/", "HUGGINGFACE_API_KEY",
       default_base="https://router.huggingface.co/v1", extra_keys=("HF_TOKEN",)),
    _p("nvidia_nim", "nvidia_nim/", "NVIDIA_NIM_API_KEY",
       default_base="https://integrate.api.nvidia.com/v1"),
    _p("cloudflare", "cloudflare/", "CLOUDFLARE_API_KEY",
       base_env="CLOUDFLARE_ACCOUNT_ID", catalogue="none",
       note="Workers AI; needs CLOUDFLARE_ACCOUNT_ID"),
    _p("openrouter", "openrouter/", "OPENROUTER_API_KEY", kind="gateway",
       base_env="OPENROUTER_BASE", default_base="https://openrouter.ai/api/v1",
       catalogue="public", note="aggregator; :free ids cost $0"),
    _p("opencode-go", "opencode-go/", "OPENCODE_GO_API_KEY", kind="gateway",
       base_env="SWARM_GO_BASE_URL", default_base="https://opencode.ai/zen/go/v1",
       catalogue="keyed", extra_prefixes=("opencode_go/",),
       extra_keys=("OPENCODE_API_KEY",), docs="https://github.com/handleman/handleman-hq"),
    _p("zen", "zen/", "OPENCODE_API_KEY", kind="gateway",
       base_env="SWARM_ZEN_BASE_URL", default_base="https://opencode.ai/zen/v1",
       catalogue="keyed", docs="https://github.com/handleman/handleman-hq"),
    _p("vercel_ai_gateway", "vercel_ai_gateway/", "VERCEL_AI_GATEWAY_API_KEY",
       kind="gateway", catalogue="keyed"),
    _p("github_copilot", "github_copilot/", "", kind="subscription",
       base_env="GITHUB_COPILOT_API_BASE", default_base="https://api.githubcopilot.com",
       catalogue="none", docs=f"{LITELLM_DOCS}github_copilot",
       note="device flow / GitHub App; through a local LiteLLM proxy for teams"),
    _p("chatgpt", "chatgpt/", "", kind="subscription", catalogue="none",
       docs=f"{LITELLM_DOCS}chatgpt",
       note="ChatGPT/Codex plan — via a local LiteLLM proxy"),
    _p("ollama", "ollama/", "", kind="local", base_env="OLLAMA_BASE_URL",
       default_base="http://localhost:11434", catalogue="public",
       note="no key; /api/tags lists models"),
    _p("vllm", "vllm/", "", kind="local", base_env="VLLM_API_BASE",
       default_base="http://localhost:8000/v1", catalogue="public"),
    _p("lm_studio", "lm_studio/", "", kind="local", base_env="LM_STUDIO_API_BASE",
       default_base="http://localhost:1234/v1", catalogue="public"),
    _p("llamafile", "llamafile/", "", kind="local", base_env="LLAMAFILE_API_BASE",
       default_base="http://localhost:8080/v1", catalogue="public"),
    _p("openai_compatible", "openai_compatible/", "OPENAI_COMPATIBLE_API_KEY",
       kind="openai_compatible", base_env="OPENAI_COMPATIBLE_BASE",
       catalogue="keyed", note="any endpoint that speaks the OpenAI API"),
)

_BY_NAME: dict[str, Provider] = {p.name: p for p in PROVIDERS}


def resolve(model: str) -> Provider | None:
    """The provider a model id routes to, or None for a bare/unknown id."""
    text = str(model or "").strip()
    if not text:
        return None
    for provider in PROVIDERS:
        if provider.matches(text):
            return provider
    return None


def prefix_of(model: str) -> str:
    """The matched prefix (`openai/`), or "" for a bare id."""
    provider = resolve(model)
    if provider is None:
        return ""
    for prefix in provider.prefixes:
        if str(model).startswith(prefix):
            return prefix
    return ""


def by_name(name: str) -> Provider | None:
    return _BY_NAME.get(str(name or "").strip())


def known_prefixes() -> tuple[str, ...]:
    return tuple(prefix for provider in PROVIDERS for prefix in provider.prefixes)


def prefixes() -> tuple[tuple[str, str], ...]:
    """(prefix, provider name) pairs, for `model_config.PROVIDER_PREFIXES`."""
    return tuple(
        (prefix, provider.name) for provider in PROVIDERS for prefix in provider.prefixes
    )


def tools_capable(name: str) -> bool:
    provider = by_name(name)
    return bool(provider and provider.tools)


def key_envs(name: str) -> tuple[str, ...]:
    provider = by_name(name)
    return tuple(provider.keys) if provider else ()


def has_key(name: str, env: dict[str, str] | None = None) -> bool:
    """A credential is present, or the provider needs none (local).

    Subscriptions (Copilot/ChatGPT) are authenticated by a device flow or a local
    proxy, not by a key env, so they report False here and preflight points at
    the subscription route.
    """
    import os

    provider = by_name(name)
    if provider is None:
        return False
    if provider.kind == "local":
        return True
    source = os.environ if env is None else env
    return any(str(source.get(var, "")).strip() for var in provider.keys)


def probe_url(name: str, env: dict[str, str] | None = None) -> str:
    """The URL a key-free reachability probe should hit (055 AC-4).

    Local providers expose a public list; public catalogues are used when known;
    otherwise the provider's base URL is probed (401/403 = reachable, auth
    required). A base env override wins so a wrong base is caught.
    """
    import os

    source = os.environ if env is None else env
    provider = by_name(name)
    if provider is None:
        return ""
    base = str(source.get(provider.base_env, "")).strip() if provider.base_env else ""
    base = (base or provider.default_base).rstrip("/")
    if provider.kind == "local":
        return f"{base}/api/tags" if provider.name == "ollama" else f"{base}/models"
    if provider.catalogue in {"public", "keyed"}:
        # A list endpoint answers 401/403 without a key — the signal we want.
        return f"{base}{provider.probe_suffix}"
    return base or ""


def field_defaults(provider: Provider) -> dict[str, object]:  # pragma: no cover - debug
    return {
        "name": provider.name,
        "prefixes": provider.prefixes,
        "kind": provider.kind,
        "keys": provider.keys,
        "base_env": provider.base_env,
        "catalogue": provider.catalogue,
    }
