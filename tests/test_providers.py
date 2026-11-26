"""055 T1: one provider registry drives routing."""

from __future__ import annotations

from swarm import model_config, providers

REQUIRED = {
    "openai", "anthropic", "gemini", "vertex_ai", "azure", "azure_ai", "bedrock",
    "mistral", "xai", "deepseek", "groq", "together_ai", "fireworks_ai", "cerebras",
    "sambanova", "nebius", "hyperbolic", "deepinfra", "moonshot", "minimax",
    "dashscope", "zai", "cohere", "huggingface", "nvidia_nim", "cloudflare",
    "openrouter", "opencode-go", "zen", "github_copilot", "ollama", "vllm",
    "lm_studio", "openai_compatible",
}


def test_the_registry_is_well_formed():
    names = [p.name for p in providers.PROVIDERS]
    prefixes = list(providers.known_prefixes())
    assert len(names) == len(set(names)), "duplicate provider name"
    assert len(prefixes) == len(set(prefixes)), "duplicate prefix"
    for provider in providers.PROVIDERS:
        assert provider.prefixes, provider.name
        for prefix in provider.prefixes:
            assert prefix.endswith("/"), f"{provider.name}: {prefix!r} must end with /"
        assert provider.kind in {
            "native", "gateway", "local", "subscription", "openai_compatible"
        }, provider.name
        assert provider.docs, f"{provider.name} needs a docs link"
        # credential-shaped providers (bedrock/vertex) document env vars instead
        # of a single key; the rest must name at least one.
        credentialed = provider.kind in {"native", "gateway", "openai_compatible"}
        if credentialed and provider.name not in {"vertex_ai", "bedrock"}:
            assert provider.keys, f"{provider.name} needs a key env"


def test_every_required_provider_is_present():
    names = {p.name for p in providers.PROVIDERS}
    assert REQUIRED <= names, REQUIRED - names


def test_prefixes_route_to_their_provider():
    cases = {
        "openai/gpt-5": "openai",
        "anthropic/claude-sonnet-5": "anthropic",
        "gemini/gemini-3-pro": "gemini",
        "vertex_ai/gemini-3-pro": "vertex_ai",
        "azure/gpt-5": "azure",
        "azure_ai/claude-sonnet-5": "azure_ai",
        "bedrock/anthropic.claude-sonnet-5": "bedrock",
        "mistral/mistral-large": "mistral",
        "xai/grok-5": "xai",
        "deepseek/deepseek-chat": "deepseek",
        "groq/llama-4-70b": "groq",
        "together_ai/llama-4": "together_ai",
        "fireworks_ai/llama-4": "fireworks_ai",
        "cerebras/llama-4": "cerebras",
        "sambanova/llama-4": "sambanova",
        "moonshot/kimi-k2": "moonshot",
        "dashscope/qwen3-coder": "dashscope",
        "zai/glm-5": "zai",
        "cohere/command-a": "cohere",
        "huggingface/meta-llama/Llama-4": "huggingface",
        "nvidia_nim/llama-4": "nvidia_nim",
        "openrouter/nvidia/x:free": "openrouter",
        "opencode-go/glm-5.3-flash": "opencode-go",
        "opencode_go/glm-5.3-flash": "opencode-go",
        "zen/glm-5.3-flash": "zen",
        "github_copilot/claude-sonnet-5": "github_copilot",
        "chatgpt/gpt-5": "chatgpt",
        "ollama/qwen3.5:9b": "ollama",
        "vllm/llama-4": "vllm",
        "lm_studio/llama-4": "lm_studio",
        "openai_compatible/my-model": "openai_compatible",
    }
    for model, expected in cases.items():
        assert providers.resolve(model).name == expected, model
        assert model_config.provider(model) == expected, model


def test_a_bare_id_keeps_the_legacy_openrouter_route():
    assert providers.resolve("gpt-5") is None
    assert model_config.provider("gpt-5") == "openrouter"
    assert model_config.provider("") == "unknown"
    assert model_config.provider("?") == "unknown"


def test_tools_capability_is_declared():
    assert providers.tools_capable("openai")
    assert not providers.tools_capable("perplexity")


def test_key_envs_and_presence():
    assert providers.key_envs("anthropic") == ("ANTHROPIC_API_KEY",)
    assert providers.has_key("anthropic", {"ANTHROPIC_API_KEY": "sk"})
    assert not providers.has_key("anthropic", {"ANTHROPIC_BASE_URL": "x"})
    assert providers.has_key("ollama", {})
    assert not providers.has_key("bedrock", {})


def test_probe_url_uses_public_catalogues_and_local_lists():
    assert providers.probe_url("openrouter", {}) == "https://openrouter.ai/api/v1/models"
    assert providers.probe_url("opencode-go", {}) == "https://opencode.ai/zen/go/v1/models"
    assert providers.probe_url("sambanova", {}) == "https://api.sambanova.ai/v1/models"
    assert providers.probe_url("ollama", {}) == "http://localhost:11434/api/tags"
    assert providers.probe_url("vllm", {}) == "http://localhost:8000/v1/models"
    # a base override is honoured, so a wrong base is caught
    assert (
        providers.probe_url("anthropic", {"ANTHROPIC_API_BASE": "https://proxy.internal"})
        == "https://proxy.internal/models"
    )


def test_the_legacy_prefix_alias_still_imports():
    assert ("opencode-go/", "opencode-go") in model_config.PROVIDER_PREFIXES
    assert ("openrouter/", "openrouter") in model_config.PROVIDER_PREFIXES


# ---- T2: dispatch by provider kind --------------------------------------


def _fake_llm(monkeypatch):
    from swarm import llms

    monkeypatch.setenv("SWARM_ALLOW_PAID", "1")
    calls: list[dict] = []

    def fake(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(llms, "LLM", fake)
    return llms, calls


def test_an_unknown_prefix_is_an_error_by_default(monkeypatch):
    import pytest

    llms, _ = _fake_llm(monkeypatch)
    monkeypatch.delenv("SWARM_STRICT_PREFIXES", raising=False)
    with pytest.raises(SystemExit, match="unknown provider prefix"):
        llms._build("mystery/model", temperature=0, allow_paid=True)


def test_the_legacy_fallback_survives_with_the_switch_off(monkeypatch):
    llms, calls = _fake_llm(monkeypatch)
    monkeypatch.setenv("SWARM_STRICT_PREFIXES", "0")
    monkeypatch.setenv("SWARM_PROMPT_CACHE", "0")
    llms._build("mystery/model", temperature=0, allow_paid=True)
    assert calls[0]["base_url"].startswith("https://openrouter.ai")


def test_a_subscription_provider_points_at_the_proxy(monkeypatch):
    import pytest

    llms, _ = _fake_llm(monkeypatch)
    with pytest.raises(SystemExit, match="subscription"):
        llms._build("github_copilot/claude-sonnet-5", temperature=0, allow_paid=True)


def test_a_native_provider_lets_litellm_route(monkeypatch):
    llms, calls = _fake_llm(monkeypatch)
    llms._build("anthropic/claude-sonnet-5", temperature=0, allow_paid=True)
    assert calls[0]["model"] == "anthropic/claude-sonnet-5"
    assert "base_url" not in calls[0]


def test_an_openai_compatible_endpoint_needs_and_uses_its_base(monkeypatch):
    import pytest

    llms, calls = _fake_llm(monkeypatch)
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE", raising=False)
    with pytest.raises(SystemExit, match="OPENAI_COMPATIBLE_BASE"):
        llms._build("openai_compatible/my-model", temperature=0, allow_paid=True)
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE", "https://llm.internal/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "k")
    llms._build("openai_compatible/my-model", temperature=0, allow_paid=True)
    assert calls[0]["base_url"] == "https://llm.internal/v1"
    assert calls[0]["model"] == "my-model"
    assert calls[0]["custom_openai"] is True


def test_a_local_provider_uses_its_base_without_a_key(monkeypatch):
    llms, calls = _fake_llm(monkeypatch)
    monkeypatch.setenv("LM_STUDIO_API_BASE", "http://localhost:1234/v1")
    llms._build("lm_studio/llama-4", temperature=0, allow_paid=True)
    assert calls[0]["api_base"] == "http://localhost:1234/v1"


# ---- T5/T6: docs cover the registry; prices are honest -------------------


def test_every_provider_is_documented():
    from pathlib import Path

    doc = Path(__file__).resolve().parents[1] / "docs" / "providers.md"
    text = doc.read_text()
    for provider in providers.PROVIDERS:
        assert provider.prefixes[0] in text, f"{provider.name} missing from docs/providers.md"


def test_an_unpriced_paid_model_is_named():
    from swarm import preflight

    warnings = preflight.price_warnings(
        {
            "SWARM_CODER_MODEL": "anthropic/claude-sonnet-5",
            "SWARM_PLANNER_MODEL": "ollama/qwen3.5:9b",
        }
    )
    assert any("claude-sonnet-5" in w and "no price row" in w for w in warnings)
    assert not any("ollama" in w for w in warnings)
