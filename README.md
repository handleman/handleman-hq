# handleman-hq — the dark factory

A spec-driven agent swarm that implements a repo's `specs/` one task at a time
and merges each green task by itself. It is **provider-agnostic** — paid cloud,
free cloud, or all-local Ollama, chosen entirely by `.env` — and **repo-agnostic**
— point it at any checkout with a `swarm.yaml`.

```bash
pipx install "git+https://github.com/handleman/handleman-hq@v0.6.8"
cd your-repo
hq init                           # writes a starter swarm.yaml
hq preflight                      # every model id, fallback, key, gate and design cache
hq run --spec 040 --task T6        # one task; green merges itself
```

New here? Read **[`docs/install.md`](docs/install.md)** — installable-package
setup (pipx/venv), the target contract, Figma, upgrades and troubleshooting.
For a source checkout use `pip install -e '.[dev]'`.

## Why it exists

- **Green means evidence.** A task is green only when the reviewer's recorded gate
  exit codes are 0, the verifier passed, and the full suite was run at the final
  delta. A model's prose never decides.
- **Judgement gets reasoning models.** The reviewer and verifier are the roles
  that can be wrong about evidence; cheap flash models do mechanical work.
  See [`docs/model-usage.md`](docs/model-usage.md).
- **Cheap per green task.** Local and `:free` models are $0 in the cost ledger; a
  paid model without a price makes cost `None` instead of faking a number.
- **The queue heals itself.** A red e2e suite is triaged, repaired inside its
  scope, and re-run; a weakened spec is reverted. Deterministic guards stop a
  loop that would burn money.

## How it works

Each phase is a small CrewAI crew with its own model role; a Flow sequences them
and owns every decision that must not be made by a model — retries, scope, green,
commit. Green comes from gate exit codes queued by QA. Read
[`docs/how-it-works.md`](docs/how-it-works.md) first: the role table, the phase
order, one flow diagram and the invariant behind it.

## The contract (`swarm.yaml`)

The target repo declares what the harness needs: `specs_dir`, `scope`, `gates`
(and an optional affected-gate `gate_map`), `e2e`, `risk`, `db`, `python`. Missing
keys fall back to the factory's own layout, never a neighbouring app tree. Copy
[`swarm.yaml.example`](swarm.yaml.example) and edit.

`python -m swarm.contract` prints the resolved contract; `hq preflight` validates
the model catalogue before the first call.

## Layout

```
src/swarm/          the harness (core + drivers)
tests/              unit tests (core green without any app tree)
docs/               one file per topic
swarm.yaml.example  the contract, every key documented
```

## Design from Figma

The queue implements Figma frames through the remote MCP server — first-run
OAuth prints a URL, waits for the browser callback, stores the token and
continues the same run — or through the REST API with a personal access token.
Both write a committed design cache that the run reads offline. See
[`docs/design.md`](docs/design.md).

## Documentation

- [`GLOSSARY.md`](GLOSSARY.md) — the factory's ubiquitous language (terms, `_Avoid_` lines).
- [`docs/domain-model.md`](docs/domain-model.md) — contexts, aggregates, invariants, lifecycles, code map.
- [`docs/adr/`](docs/adr/) — the hard decisions behind the model.
- [`docs/install.md`](docs/install.md) — **install the package (pipx/venv)**, configure a target, run, upgrade.
- [`docs/how-it-works.md`](docs/how-it-works.md) — roles, phase order, the flow diagram, the invariant.
- [`docs/setup.md`](docs/setup.md) — venv, model tiers/routing, preflight.
- [`docs/model-usage.md`](docs/model-usage.md) — which kind of model each role needs; **review needs reasoning**.
- [`docs/drivers.md`](docs/drivers.md) — declaring the target's e2e/acceptance/smoke/db drivers (JSON protocol, fallback).
- [`docs/providers.md`](docs/providers.md) — every supported provider: prefix, key env, base, recipes, and the key-free reachability probe.
- [`docs/running.md`](docs/running.md) — dashboard, resume rules, escalation.
- [`docs/queue.md`](docs/queue.md) — how tasks are found, reopened, and added.
- [`docs/tools-and-gates.md`](docs/tools-and-gates.md) — guarded tools and who owns gate evidence.
- [`docs/verifier.md`](docs/verifier.md) — the read-only scenario check.
- [`docs/run-guards.md`](docs/run-guards.md) — the deterministic stops and their off switches.
- [`docs/e2e-self-heal.md`](docs/e2e-self-heal.md) — a red suite is triaged, repaired, never weakened.
- [`docs/usage-and-budgets.md`](docs/usage-and-budgets.md) — tokens, cost, caps.
- [`docs/unattended.md`](docs/unattended.md) — overnight runs, tuning, stashes, supervisor.
- [`docs/risk-classes.md`](docs/risk-classes.md) — the risk label and the escape rate.
- [`docs/commits.md`](docs/commits.md) — merge queue, ledger, approval resume, sandbox.
- [`docs/parallel.md`](docs/parallel.md) — parallel attempts in worktrees.
- [`docs/testing.md`](docs/testing.md) — harness tests, browser suite, replay sets.
- [`docs/context-economics.md`](docs/context-economics.md) — prompts, compaction, gate selection, caching.
- [`docs/fix-loop.md`](docs/fix-loop.md) — tests-first, repair budget, telemetry, anti-loop guards.
- [`docs/timing.md`](docs/timing.md) — phase timing, wall budget, timeouts, concurrency.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — traces and what each stop means.
- [`specs/harness/ROADMAP.md`](specs/harness/ROADMAP.md) — the remaining harness order
  (provider matrix, driver relocation, coverage).
- [`docs/model-usage.md`](docs/model-usage.md) — model recommendations per role.

## Status

**v0.4.0** — packaged, contract-driven, provider-agnostic (37 providers, strict
prefixes, key-free probe) and driver-aware: a target declares its e2e/db (and
optionally acceptance/smoke) as JSON-speaking commands, with the packaged
implementation as the fallback. The app consumes it.

## Roadmap

See [`specs/harness/ROADMAP.md`](specs/harness/ROADMAP.md): the provider matrix
(055) first, then moving the drivers into target repos (v0.4), then acceptance
coverage and the per-task visual phase.

## Subscription plans

Claude Pro/Max, ChatGPT/Codex and Copilot are usable through a local LiteLLM
proxy: `make proxy` (and `make proxy-down`). See
[`examples/litellm-proxy/`](examples/litellm-proxy/README.md). API keys plug in
directly ([`docs/providers.md`](docs/providers.md)).

## Contributing

[`AGENTS.md`](AGENTS.md) has the rules for changing the factory: the contract is the
only source of truth, green means recorded evidence, and judgement roles need
reasoning models. `make test` and `make factory-audit` must pass before a push.

## License

MIT — see [`LICENSE`](LICENSE).
