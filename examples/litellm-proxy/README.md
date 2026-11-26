# Subscription proxy (Claude Pro/Max, ChatGPT/Codex, GitHub Copilot)

A **subscription** is not an API key. LiteLLM can use one, but only through a
local proxy that owns the sign-in. The factory then sees a normal
OpenAI-compatible endpoint.

## Run

```bash
cp .env.example .env 2>/dev/null || true
docker compose up -d
open http://localhost:4000/ui          # connect GitHub Copilot / Claude / ChatGPT
```

Create a proxy key in the UI (or use `LITELLM_MASTER_KEY`), then point the
harness at the proxy as a generic compatible endpoint:

```bash
# .env
SWARM_PLANNER_MODEL=openai_compatible/claude-sonnet
SWARM_CODER_MODEL=openai_compatible/claude-sonnet
SWARM_REVIEWER_MODEL=openai_compatible/claude-sonnet
SWARM_SENIOR_MODEL=openai_compatible/claude-sonnet
OPENAI_COMPATIBLE_BASE=http://localhost:4000/v1
OPENAI_COMPATIBLE_API_KEY=sk-local-proxy
SWARM_ALLOW_PAID=0                    # the subscription pays; the factory has no $ cost
```

`make swarm-preflight` then validates the alias and `--probe` proves the proxy is
up (`http://localhost:4000/v1/models`).

## Notes

- The proxy is the only place a personal token lives; the factory never sees it.
- Subscription plans have provider-side limits; the queue's wall/dollar caps do
  not apply to a plan, so watch `run.json.usage` for volume.
- `github_copilot/…` also works directly through LiteLLM's device flow (no proxy)
  for a single-user machine; the proxy is the team/backend route.
