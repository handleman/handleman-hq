# Design from Figma (057)

The queue implements frames from Figma through **MCP with first-run OAuth** or
the **REST API** (personal access token). Both write the same committed cache;
the run itself reads only that cache.

## Two transports

| | MCP | REST |
| --- | --- | --- |
| Auth | OAuth on first use (DCR + PKCE, loopback redirect) | `FIGMA_TOKEN` personal access token |
| Data | read tools: metadata, design context, variables, screenshots, assets, Code Connect | raw nodes, images, variables, components, styles |
| Best for | the same workflow as OpenCode, latest tools | CI/headless, no browser callback |

`transport: auto` (default) picks MCP when a token is stored, REST when
`FIGMA_TOKEN` is set, and otherwise starts the MCP OAuth prompt. The MCP token
is scoped to `mcp:connect` and is **not** a REST token.

## Contract

```yaml
design:
  provider: figma
  transport: auto               # auto | mcp | rest
  file_key: "<key from /design/<key>/...>"
  nodes: ["12:34", "56:78"]     # only these frames may enter prompts
  token_env: FIGMA_TOKEN        # REST only
  dir: designs/                 # committed cache
  scale: 2
  auth:
    timeout_s: 600
    open_browser: true
```

A spec opts in with `design.toml` (frame + checks):

```toml
[figma]
file_key = "<key>"
node = "12:34"

[[token]]
name = "--color-primary"
value = "#1d4ed8"
ac = "AC-1"

[[region]]
id = "top-card"
selector = "[data-testid='top-card']"
x = 12
y = 12
w = 1256
h = 96
tolerance_px = 2
ac = "AC-2"

[screenshot]
frame = "desktop"
baseline = "designs/<key>/12-34.png"
threshold = 0.02
ac = "AC-3"
```

## Commands

```bash
hq figma status                 # token presence/expiry (never the token)
hq figma auth                   # first run: URL -> browser -> token -> done
hq figma logout

hq design sync [--force] [--spec 041] [--transport mcp|rest]
hq design check  [--spec 041]
hq design brief  [--spec 041]
hq design verify --spec 041 --facts facts.json
```

`hq design sync` writes atomically:

```
designs/<file-key>/
  index.json        # transport, file (key/name/version), nodes, tokens
  <node>.json       # normalized IR (bounds, layout, fills, text, children)
  <node>.png        # reference render (REST) or MCP screenshot
  tokens.json       # variables + styles
  design-brief.md   # planner/coder-readable brief
  design-context/   # MCP get_design_context output (reference only)
  design.lock       # version + node ids + sha256 per artifact
```

## First run (the queue meets a Figma link)

1. A run needs design data and no token is stored.
2. Preflight (or the flow, if preflight is skipped) runs `design ensure`:
   it prints an authorization URL and records it in `run.json.design`.
3. The user opens the URL; Figma redirects to `http://127.0.0.1:8765/callback`.
4. The harness exchanges the code (PKCE), stores the token at
   `$XDG_DATA_HOME/handleman-hq/figma/oauth.json` (0600), and **continues the
   same run**.
5. No callback in `auth.timeout_s` → `figma_auth_required` with the URL.
   `SWARM_NONINTERACTIVE=1` fails immediately with the URL.
6. Remote host: `ssh -L 8765:127.0.0.1:8765` or `hq figma auth --paste`.

An expired token refreshes silently; an invalid refresh drops it and re-prompts.

## What the queue gets

- The planner/coder prompt includes `design-brief.md` for the spec.
- `designs/` is **out of coder scope**; only `hq design sync` writes it.
- The coder may call the read-only MCP tools (metadata, design context,
  variables, screenshots, assets, Code Connect) with an allowlist, a per-task
  budget and a per-node cache; write/canvas tools are never exposed.
- The acceptance runner collects computed CSS variables, region rects and
  screenshots for `design.toml` (`hq design verify` is the same evaluator).
- `run.json.design` records file/nodes/transport/sync status.

## Security

- OAuth tokens live outside the repo, 0600, and never enter a prompt,
  `run.json` or a log. REST tokens are read only by the sync command.
- File key and nodes come from the contract/`design.toml`, not model output.
- `designs/` is immutable during a run; sync is atomic.
- MCP tools are read-only; generated code is reference, never executed.
- Downloads are size-capped; 429s back off; sync is a no-op when the lock is
  current.

## Troubleshooting

- `figma_auth_required: <url>` — open the URL, authorize, retry; or run
  `hq figma auth`.
- `figma_auth_timeout` — the browser redirect did not arrive; check the port,
  SSH forwarding or use `--paste`.
- `design_stale` — the cache hash no longer matches; run `hq design sync
  --force`.
- `design_node_missing` — the spec's `design.toml` node is not in the contract;
  add it to `design.nodes`.
- `figma_token_missing` (REST) — set `FIGMA_TOKEN` or use MCP.
- `design_region` false positives on mobile — declare the region at the
  reference viewport or adjust `tolerance_px`.
