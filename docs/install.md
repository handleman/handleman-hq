# Install the swarm as a package

The harness is a standalone package; the target repo only needs a `swarm.yaml`,
a `.env`, and its own tests. You do **not** copy `src/swarm/` into the app.

## Requirements

- Python **3.12 or 3.13** (`requires-python >=3.12,<3.14`) and `git`.
- The target repo's own toolchain: its Python venv, `pytest`/`ruff`/`mypy` (or
  equivalents), Node/Playwright for an e2e suite, Postgres if it has a DB lane.
- Model/provider keys in the target's `.env` — see
  [`setup.md`](setup.md) and [`providers.md`](providers.md).

## Install the CLI

Recommended (isolated, global `hq`):

```bash
pipx install "git+https://github.com/handleman/handleman-hq@v0.7.0"
hq --version        # hq 0.7.0
```

Or in its own venv:

```bash
python3.12 -m venv ~/.venvs/hq
~/.venvs/hq/bin/pip install "git+https://github.com/handleman/handleman-hq@v0.7.0"
~/.venvs/hq/bin/hq --version
```

Add the dev tools for a source checkout: `"handleman-hq[dev] @ git+https://…@v0.7.0"`.
The package is currently installed from the tagged GitHub release; use a newer
tag when upgrading.

## Point it at a repo

```bash
cd my-app
hq init            # writes a starter swarm.yaml
```

Edit `swarm.yaml` (the harness never guesses the target):

```yaml
specs_dir: specs/product
scope: [src/, tests/, pyproject.toml]
gates: [pytest -q, ruff check .]
e2e:
  command: npm run test:e2e
  specs: e2e
python:
  venv: .venv          # the app's venv, not the harness one
runs_dir: .hq/runs
# drivers:             # optional: the target's own JSON drivers
#   e2e: "./drivers/e2e.sh"
# design:              # optional: Figma lane
#   provider: figma
#   transport: auto
#   file_key: "<key>"
#   nodes: ["12:34"]
```

`.env` holds provider keys and model ids. Then:

```bash
hq preflight       # models, keys, venvs, gates, design cache
```

## Run the queue

Specs live under `specs_dir` as `spec.md` + `plan.md` + `tasks.md`. Tasks are
the unchecked `- [ ] T…` lines.

```bash
hq run             # foreground queue (resumes from the last checkpoint)
hq run --spec 040 --task T6
hq up              # background + dashboard
hq stop
hq report          # ledger
```

A green task merges itself; a failure appends a fix task or stops with a typed
reason. Run one queue at a time.

## Figma (optional)

`transport: auto` is token-first:

```bash
hq figma status    # auto_transport: rest if FIGMA_TOKEN, else mcp
hq figma auth      # MCP only: URL → browser redirect → token stored
hq design sync     # designs/<key>/ (local, gitignored: IR, brief, renders, tokens, lock)
hq design check
hq design brief
```

REST: put `FIGMA_TOKEN=figd_…` in `.env`; no auth command. MCP: the first run
prints an authorization URL, waits for the loopback callback, stores the token
0600, and continues. See [`design.md`](design.md) and
[`figma.md`](https://github.com/handleman/comfort-walking-router/blob/main/docs/figma.md).

## Upgrade

```bash
pipx install --force "git+https://github.com/handleman/handleman-hq@v0.7.0"
# or: ~/.venvs/hq/bin/pip install -U "git+https://…@v0.7.0"
hq --version
```

Re-run `hq preflight` after an upgrade; `swarm.yaml` is backwards-compatible
(unknown keys are tolerated).

## What the package owns (and doesn't)

| The package (`hq`) | The target repo |
| --- | --- |
| the queue, roles, guards, prompts | `swarm.yaml`, specs, `.env` |
| the packaged e2e/acceptance/smoke/db drivers | the app's venv, gates, e2e suite |
| `hq run/up/stop/report/preflight/design/figma` | its own `make` targets, if any |

`make swarm-*` targets are repo sugar, not part of the package. The package
never installs into the app's venv; `python.venv` in `swarm.yaml` tells the
gates which interpreter to use.

## Troubleshooting

- `hq: command not found` — `pipx ensurepath`, reopen the shell.
- `preflight failed: …` — read the typed problems; `hq preflight` prints one
  line per missing key/model/venv/gate.
- `no queue runner` — a legacy target; the packaged runner is used when no
  `harness/run.sh`/`swarm/run.sh` exists.
- `design_missing` / `design_stale` — run `hq design sync`.
- `figma_auth_required: <url>` — open the URL and authorize, re-run; or
  `hq figma auth`.
- More: [`running.md`](running.md), [`queue.md`](queue.md),
  [`run-guards.md`](run-guards.md), [`drivers.md`](drivers.md).
