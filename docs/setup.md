# Setup and models

> Part of the swarm harness documentation. Start at [`../README.md`](../README.md).

## Prereqs
- `uv` installed; Python 3.12 available (`uv python list`). System Python 3.14 does NOT work with CrewAI (`>=3.10,<3.14`).
- Ollama serving locally: `ollama serve` + `ollama pull qwen3.5:9b` (default `OLLAMA_BASE_URL=http://localhost:11434`).
- Keys (never commit): root `.env` with `OPENROUTER_API_KEY` (planner/senior `:free` models);
  `OPENCODE_API_KEY` only if you route a role to `zen/*` (Zen's free tier is client-only, so the
  API path is paid — see the model table).

## Setup

From a checkout (development):

```bash
uv venv -p 3.12 .venv
VIRTUAL_ENV="$PWD/.venv" uv pip install -p "$PWD/.venv/bin/python" -e '.[dev]'
cp .env.example .env   # optional overrides (keys stay empty until you fill them)
.venv/bin/hq --version
```

As a dependency of a target repo (the normal case):

```bash
pip install 'handleman-hq[dev] @ git+https://github.com/handleman/handleman-hq@v0.3.3'
cd your-repo && hq init        # writes a starter swarm.yaml
hq preflight                   # every id, fallback, key, venv and gate binary
```

`.env` is read from the directory `hq` runs in (`SWARM_TARGET`), so one harness
venv can drive several repos; the repo declares its shape in `swarm.yaml`.

## Project-agnostic core
The harness does not hardcode a language, framework or app. The target's
`swarm.yaml` declares `specs_dir`, `scope`, `gates` (+ an affected-gate
`gate_map`), `e2e` (command + spec root/dir), `risk` classes, `db`, `python.venv`
and `lock_dir`. Environment overrides (`SWARM_GATE_COMMANDS`, `SWARM_SCOPE`,
`SWARM_GATE_MAP`) win for one run. Drivers (browser suite, acceptance, health,
bench, smoke, corridor probe) live under `swarm.drivers` and read the same
contract; the core has no `app/` or `frontend/` strings.

## Model tiers (`src/swarm/model_config.py` resolves; `llms.py` builds)

> Every supported provider (prefix, key env, base, recipes) is in
> [`providers.md`](providers.md). An unknown prefix is an error by design;
> `preflight --probe` checks reachability without a key.

Current operator profile (**OpenCode Go**, 2026-11-25): every role is a Go model
with tool calling and every fallback is a second Go model, so a provider blip
moves sideways and nothing dials Ollama. Chosen for **cost per green task, not
cost per token**: the measured workhorse carries the bulk roles, the flagship is
reserved for escalation, and the **judgement roles get a reasoning-capable
model** — the cheapest tier belongs on mechanical work.

| Role | Model | $/M in–out | Fallback | $/M in–out |
| --- | --- | --- | --- | --- |
| Implementer | `opencode-go/kimi-k2.7-code` | 0.95–4.00 | `glm-5.3-flash` | 0.15–0.50 |
| Implementer (escalation) | `opencode-go/kimi-k3` | 3.00–15.00 | `deepseek-v4-pro` | 1.32–3.96 |
| Auditor | `opencode-go/qwen3.8-flash` | 0.15–0.47 | `mimo-v2.6-flash` | 0.14–0.28 |
| Visual QA (042/043) | `opencode-go/kimi-k3` | 3.00–15.00 | `claude-haiku-5-5` | 0.10–0.50 |
| Acceptance vision | `opencode-go/gemini-4-argon` | 2.00–10.00 | `claude-haiku-5-5` | 0.10–0.50 |
| Conflict resolver | the implementer model | — | `mimo-v2.6-flash` | 0.14–0.28 |

**Tool roles cannot use the Gemini/Claude Go adapters.** They reject CrewAI's
strict tool schema (`strict function schema` / named participants). Use Kimi
K2.7/K3, GLM or DeepSeek for `SWARM_IMPLEMENTER_MODEL`, `SWARM_AUDITOR_MODEL`
and `SWARM_ESCALATION_MODEL`; preflight rejects those adapters for a tool role.
Gemini 4 Argon remains the vision-only acceptance reader.

The v1 ids (`SWARM_PLANNER_MODEL`, `SWARM_CODER_MODEL`, `SWARM_REVIEWER_MODEL`,
`SWARM_SENIOR_MODEL`, `SWARM_VERIFIER_MODEL`) still work: v2's implementer
inherits the coder id, the auditor the verifier/reviewer/senior brain, and the
escalation tier the senior id. Set `SWARM_IMPLEMENTER_MODEL`,
`SWARM_AUDITOR_MODEL` and `SWARM_ESCALATION_MODEL` (and their `_FALLBACK_MODEL`
pairs) only when you want a different id from the v1 role. Preflight validates
whichever ids are set, so a typo fails before the first call.

Why this split: the coder writes most tokens, so it keeps the flash tier with the
best measured green rate in this repo (`glm-5.3-flash`: 111–271 s and
$0.0075–0.0288 per task on three shapes, see below). **Do not put the cheapest
tier on a judgement role.** On 2026-11-25 the reviewer was `mimo-v2.6-flash`
(0.14–0.28, the cheapest) and blocked T23 with cause `test` while every recorded
gate was green, the verifier passed, and no `pytest` had run — an ungrounded
block that burnt a fix round and parked the task. Switching the reviewer to
`qwen3.8-flash` (the verifier's model) let the same work pass. A reviewer that
can be wrong is not cheap at any price; judgement is reasoning work. Escalation
is rare and short, so
`deepseek-v4-pro` (flagship coding, no vision) is cheaper in expectation than
paying a second fix round on a flash model. `hy4-flash-free` gives the vision
roles a $0 tier with image understanding; `claude-haiku-5-5` is the paid
fallback. Contributor/stealth tiers (`muse-spark-*-contributor`,
`iceman-*-free`) are excluded: they train on the traffic.

`preflight` checks every id against the live Go catalogue
(`SWARM_GO_BASE_URL/models`) before the first call, so a typo fails in seconds
instead of mid-task. `src/swarm/usage.py` carries the prices (peak rate where a
multiplier exists) so `SWARM_MAX_COST_PER_TASK` stays meaningful.

### Alternative profile: free OpenRouter tiers (2026-11-22, quota-capped)

Free, tool-capable OpenRouter models with local Ollama fallbacks; the account-wide
free wall is 1000 requests/day (resets 03:00 local), and the first 429 switches
the whole run to the fallbacks. Roles were `nemotron-3.5-super-vl:free`
(planner/coder), `nemotron-3.5-lightning:free` (reviewer),
`nemotron-3-ultra-550b-a55b:free` (senior/verifier), with `ollama/swarm-coder`
and `ollama/swarm-qa` as fallbacks, with free vision models on OpenRouter
(`nemotron-3.5-super-vl`, fallback `gemma-4-31b-it`).

### Local profile (Ollama) — supported, and the fastest way to check versatility

The harness does not require a cloud provider. `make swarm-local` overrides every
role for one run, and this block makes it the default in `.env`:

```
SWARM_PLANNER_MODEL=ollama/swarm-coder:latest
SWARM_CODER_MODEL=ollama/swarm-coder:latest
SWARM_REVIEWER_MODEL=ollama/swarm-qa:latest
SWARM_SENIOR_MODEL=ollama/swarm-coder:latest
SWARM_VERIFIER_MODEL=ollama/swarm-qa:latest
SWARM_VISUAL_MODEL=ollama/swarm-qa:latest      # text-only: vision checks degrade to advisory
SWARM_LOCAL_FALLBACK_MODEL=ollama/swarm-coder:latest
SWARM_ALLOW_PAID=0
```

What changes automatically, with no code edit:

- **Routing** — `ollama/*` goes to `OLLAMA_BASE_URL` (default
  `http://localhost:11434`), `think:false` forced; no key needed.
- **Preflight** — checks the model is actually pulled (`/api/tags`) instead of a
  provider catalogue, and tells you the missing name.
- **Timeouts** — one knob per profile: `SWARM_LOCAL_CREW_TIMEOUT_SECONDS`
  (default **900 s** per crew call — a 64k-context on-device step can exceed
  5 min) for a local profile, `SWARM_CREW_TIMEOUT_SECONDS` (default 300 s) for
  cloud. They are independent, so switching profiles never inherits the other
  side's cap; `SWARM_OLLAMA_TIMEOUT_SECONDS` (default 1800) bounds one generation.
- **Cost** — every `ollama/*` model is $0 in `src/swarm/usage.py`, so `run.json.cost`
  is a real `0.0`, not `null`.
- **Guard** — `SWARM_ALLOW_PAID=0` keeps a paid id from being dialled; local ids
  never need the paid opt-in.

A **hybrid** profile is just the same knobs mixed: paid coder, local reviewer,
free-cloud planner. The only rule is that each fallback must be servable — the
first provider-wide failure switches *that* role to its own fallback, so a hybrid
run degrades per role instead of collapsing.

### Go caveats and the earlier Go pairing (2026-11-15)

Local Ollama off (`SWARM_LOCAL_FIRST=0`), one subscription key serves every role,
and each role falls back to a second Go model:
`opencode-go/glm-5.3-flash` (fallback `opencode-go/qwen3.8-flash`) for
planner/coder/reviewer/verifier/senior at $0.15/$0.50 per M. Note that
`opencode-go/qwen3.8-flash` is **not** an OpenRouter model id — only use it with
the Go prefix and key.

`opencode-go/*` is its own routing prefix: `OPENCODE_GO_API_KEY` (or
`OPENCODE_API_KEY`) against `SWARM_GO_BASE_URL`
(default `https://opencode.ai/inference/go/openai/v1`), with the client
`User-Agent` and an `x-opencode-session` header that the Go gateway asks for
(it drives routing and prompt caching). Model ids are the bare console ids
(`glm-5.3-flash`, `qwen3.8-flash`, `deepseek-v4.1-flash`, `kimi-k2.7-code`, …);
prices live in `src/swarm/usage.py`, so `run.json.cost` stays a number.

Two Go caveats seen on 2026-11-15: `deepseek-v4.1-flash` is region-blocked until
the workspace privacy setting is **Global** (Settings › Privacy › Regions), and
its price is peak/off-peak — the table stores the peak rate so the per-task cap
never under-reads.

Measured on 2026-11-15 with `make swarm-bench-live` (three task shapes, all
green, 0 fix rounds): **backend logic** `004-weather-sun-T2` 111 s / 131 s,
$0.0075, 43.5k prompt (20.7k cached) — versus 384 s / $0.0161 on the Zen profile;
**backend/schema** `005-saved-routes-T2` 145 s, $0.0126, 50.2k prompt;
**frontend store/component** `007-live-position-T6` 271 s, $0.0288, 128.7k prompt
(74.6k cached), 7 gates. Three cases, not a benchmark.

The earlier cloud-only profile (2026-11-14) was DeepSeek on OpenRouter for the
planner and `zen/glm-5.3-flash` for the four tool roles; it still works if the
Go subscription is absent.

The free Nvidia roles worked all day until OpenRouter's **1000 free requests/day**
limit hit (`429 free-models-per-day-high-balance`). With no free fallback left,
the operator pointed reviewer/verifier/senior at the paid Zen model instead of
waiting for the reset; `SWARM_ALLOW_PAID=1` now also covers those roles (an
explicit `allow_paid` argument still wins). With a healthy free tier, set them
back to `:free` ids — the code defaults are free-only.

Offline variant (no keys, slowest): `make swarm-local` sets every role to Ollama —
coder `swarm-coder`, reviewer `swarm-qa` (Qwen3.5 9B, 262k ctx). The 2026-11-08
free-first defaults were planner `nemotron-3.5-super-vl:free`, local coder/QA and
the free ultra senior. The free Nvidia planner returned 503 "content safety
screening is temporarily unavailable" for ~7 minutes (2026-11-14, 014-T6), which
is why the planner is now paid DeepSeek.

On a quota/429 the flow switches that role to `SWARM_<ROLE>_FALLBACK_MODEL`
(default `SWARM_LOCAL_FALLBACK_MODEL`, still `ollama/swarm-coder:latest` in code;
the operator `.env` points it at `zen/glm-5.3-flash` because local is off), then retries.

Free/cheap menu (re-checked live with a tool-call probe; ids churn, so run
`make swarm-preflight` before trusting them):
- OpenRouter `:free` tool-capable: `nvidia/nemotron-3.5-super-vl:free`,
  `nvidia/nemotron-3-ultra-550b-a55b:free`, `recursive/flint-v1.0:free`,
  `cohere/north-mini-code:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`.
  (`google/gemma-4-*:free` was upstream-429; `nvidia/nemotron-3.5-lightning:free` did not
  emit tool calls. The old planner id `nemotron-3-super-120b-a12b:free` is gone.)
- Ollama local: `swarm-coder`/`swarm-qa` (Qwen3.5 9B, 262k ctx), `qwen3.5:9b`,
  `qwen35-agent`, `llama3.2:1b` (tools work but emits malformed args — not a coder).
- Zen: **free models are client-only** (`FreeUsageLimitError` when called with an API key);
  paid models work from the API — `deepseek-v4.1-flash` (~$0.00002/call) and
  `glm-5.3-flash` are the cheapest. `gpt-5.4-nano` and `beam-free` are region-blocked (DE).

Paid models are hard-blocked: any non-`:free`/non-local/non-`-free` id raises `PermissionError`
unless `SWARM_ALLOW_PAID=1` in env. Override ids via env, never in code.

Model prefixes route automatically: `ollama/*` → local Ollama, `zen/*` → OpenCode Zen
(`custom_openai` gateway; `SWARM_ZEN_BASE_URL` must stop at `/v1` — the SDK appends
`/chat/completions`, a full URL gives 404).

## Local Postgres (005 saved routes)

```bash
make swarm-db-up       # colima + comfort-pg, wait, migrate, print the export
make swarm-db-status
make swarm-db-down     # COLIMA=1 also stops colima
```

While the container runs, `make test`, `make e2e`, `make swarm-run`, `make up`,
`make swarm-bench-live` and `make swarm-replay*` get `DATABASE_URL` automatically
(`$(DB_ENV)` in the Makefile) — the app reads the environment at import, not
`.env`. Without it, the 005 repository tests and the three `preferences` e2e
specs skip. `make swarm-preflight` prints the database line but never fails on it.

## Preflight (before the first LLM call)
```bash
make swarm-preflight                              # roles/models, keys, Ollama pull, cloud lists, venvs, gates
.venv/bin/python -m swarm.preflight --offline   # skip provider model-list requests
```
`run_crew` runs the same checks automatically and stops with `preflight_failed` if any fail
(`SWARM_SKIP_PREFLIGHT=1` bypasses). This is 012 T12.

Coder image: `ollama/Modelfile` (`FROM qwen3.5:9b`, temp 0, `num_ctx 65536`,
baked SYSTEM discipline). Use it via `SWARM_CODER_MODEL=ollama/swarm-coder:latest`.
Verified 2026-10-10: builds offline from local blobs, native tool calls work
(with the harness's `think:false`). Tune `num_ctx`/SYSTEM in the Modelfile and rebuild.

### Task budget profiles (060)

The per-task caps are classified by work type: **coding** (base), **e2e** and
**visual** (screenshot/design/acceptance tasks). e2e/visual scale the six caps
by 2.0 by default: `SWARM_MAX_TOKENS`, `SWARM_MAX_COST_USD`,
`SWARM_MAX_RUNTIME_SECONDS`, `SWARM_MAX_COST_PER_TASK`,
`SWARM_MAX_SECONDS_PER_TASK` and `SWARM_TASK_WALL_BUDGET`. The evidence (p90/max
of the app's 180 coding, 47 e2e and 15 visual runs) is in
[`specs/harness/060-task-budgets/evidence.md`](../specs/harness/060-task-budgets/evidence.md).
Override with `SWARM_E2E_CAP_MULTIPLIER` / `SWARM_VISUAL_CAP_MULTIPLIER` (floor
1.0); `run.json.budget.profile` and `cap_multiplier` record what ran.

### Swarm v2 (061)

v2 is the default: one whole-task implementer, deterministic harness gates, one
read-only auditor. The knobs are:

| Env | Default | Job |
| --- | --- | --- |
| `SWARM_FLOW_V2` | `1` | `0/false/no/off` runs the v1 planner/QA/verifier sequence |
| `SWARM_V2_MAX_ROUNDS` | `3` | implementer rounds before `needs_human` |
| `SWARM_V2_MAX_ITER` | `60` | tool-call budget for one implementer round |
| `SWARM_V2_AUDITOR_MAX_ITER` | `10` | tool-call budget for the auditor |
| `SWARM_V2_CREW_TIMEOUT_SECONDS` | `900` | hard cap for one implementer/auditor crew call |
| `SWARM_IMPLEMENTER_MODEL` | coder id | primary implementer tier |
| `SWARM_ESCALATION_MODEL` | senior id | tier used from round 2 |
| `SWARM_AUDITOR_MODEL` | verifier/reviewer/senior | the judgement model |

`run.json.flow` records `version`, the implementer rounds/escalations and the
auditor verdicts. Usage is attributed to `implementer`,
`implementer:escalation` and `auditor`, so the dashboard and `hq report` can
compare the tiers. v2 has no per-step checkpoint: a killed v2 task restarts from
its first round (the done ledger and the delta guard still prevent a false
green). The design and evidence are in
[`specs/harness/061-swarm-v2/`](../specs/harness/061-swarm-v2/) and
[ADR 0005](adr/0005-one-implementer-one-auditor.md).
