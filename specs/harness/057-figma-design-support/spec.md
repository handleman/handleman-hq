# 057 Figma Design Support — Spec (harness)

Status: proposed · Owner: operator · Depends on: 042 (visual phase), 043
(acceptance), 048 (contract), 049/052 (layout), 056 (drivers)

> **Revision 2026-11-26 — MCP is the transport.** The first draft used REST
> only. The operator wants the swarm to behave like OpenCode: when it meets a
> Figma link and no token is stored, it shows an authorization URL, waits for
> the browser redirect, stores the token and continues. The Figma remote MCP
> server supports standard MCP OAuth (discovery + DCR + PKCE), and the Python
> `mcp` SDK (1.30.0, already present via CrewAI) implements it. MCP is now the
> primary transport for **both** lanes; the cache stays as the run's
> deterministic snapshot, and REST remains an optional fallback for headless
> environments. The sections below are updated accordingly.

## What / Why

The operator is preparing a Figma design for the comfort-walking-router. The
queue can already implement prose specs, but nothing in the harness can read a
design file, so a human would have to translate frames into words and then judge
the result by eye. That is exactly the work the dark factory is supposed to own.

Two lanes are needed and they are deliberately different:

- **Operator lane (OpenCode)** — interactive design exploration and one-off
  implementation through Figma's MCP server. A person is present, OAuth is fine,
  the latest tools matter more than reproducibility.
- **Queue lane (harness)** — unattended implementation from a **local,
  gitignored design cache** fetched by one deterministic command. No OAuth
  during a run, no network dependency, no token in a prompt; `designs/` is
  rebuilt by `hq design sync` and never committed.

This spec covers both, but the harness contract only implements the queue lane;
the operator lane is configuration + a skill in the target repo.

## Investigation (2026-11-26)

Facts this design relies on:

- Figma ships a **remote MCP server** at `https://mcp.figma.com/mcp` (OAuth,
  all plans; a Full/Dev seat is recommended, view seats may hit limits) and a
  **desktop server** at `http://127.0.0.1:3845/mcp` (Figma desktop app + Dev/Full
  seat on a paid plan). OpenCode is a listed client with remote/desktop and write
  support.
- The MCP tools relevant to implementation: `get_metadata` (XML outline),
  `get_design_context` (structure + code; React/Tailwind default, other
  frameworks on request), `get_screenshot`, `get_variable_defs`,
  `download_assets` (20 nodes, PNG/JPG/SVG/PDF + original images),
  `get_code_connect_map`, `search_design_system`. Remote calls are link-based and
  need a file key + node ID. The write tools (`use_figma`,
  `generate_figma_design`, …) are out of scope for the queue.
- The **REST API** provides the same source data without an interactive session:
  `GET /v1/files/{key}/nodes?ids=…`, `GET /v1/images/{key}?ids=…&format=png`,
  `GET /v1/files/{key}/variables/local`, `GET /v1/files/{key}/components`,
  `GET /v1/files/{key}/styles`, authorised with `X-Figma-Token` (personal access
  token). Rate limits are plan-dependent and return 429.
- The harness has **no MCP client**. Agents get guarded CrewAI tools
  (`tools_guarded.py`); target-specific work goes through **drivers** (056) —
  JSON-speaking commands declared in `swarm.yaml`. `layout.py` already says a
  future Figma importer writes the same `layout.toml`.

Decision (revised): **MCP for both lanes, with a local, gitignored cache.** The queue
performs the same OAuth flow as the operator on first use (MCP authorization
code + PKCE, loopback redirect, token stored 0600), then reads the design into
the same stable IR and continues offline from the cache. The generated
React/Tailwind code is used as reference only; the coder still writes Svelte.
REST is a **first-class alternative** for CI/headless runs (personal access
token, same cache), not a degraded mode.

## Goals

1. One command (`hq design sync`) turns an allowlisted Figma file/nodes into a
   local design cache (normalized IR, renders, tokens, brief, lock; rebuilt by sync).
2. The planner, coder, verifier and acceptance can implement and verify a frame
   **offline** from that cache; no OAuth, no Figma call during a run.
3. The first Figma use in a run is an **authorization step**, not a failure:
   with no stored token the harness shows the URL, receives the loopback
   callback, stores the token and **continues the same run**; a headless run
   stops with a typed `figma_auth_required` and the same URL.
4. Design fidelity becomes deterministic where possible: computed tokens, region
   bounds, and a thresholded screenshot diff join the existing gates; the vision
   model stays advisory.
5. A stale or missing design cache is a typed stop, not a silent freehand
   implementation.
6. The OpenCode operator lane is documented and shareable in the target repo
   (MCP entry + skill + doc), with no secret in git.

## Non-goals

- Writing to Figma from the queue or from the harness (no canvas writes).
- Perfect pixel parity for arbitrary fonts/assets; the diff is thresholded and
  reports, it does not block on antialiasing noise.
- Replacing `layout.toml`, the 042 visual phase or the 043 acceptance report.
- Providers other than Figma in the first release (the IR is source-agnostic so
  a Penpot/Sketch importer can reuse it).
- Auto-generating the whole task list from a frame tree without a planner; the
  planner still owns scope and AC mapping.

## Contract (`swarm.yaml`)

New optional block; absent means no design lane (today's behaviour):

```yaml
design:
  provider: figma
  transport: auto                # auto (default) | mcp | rest
  # auto is token-first: FIGMA_TOKEN present -> REST; absent -> MCP OAuth.
  file_key: "<key from /design/<key>/...>"
  nodes: ["12:34", "56:78"]      # allowlist; no other node may enter a prompt
  token_env: FIGMA_TOKEN         # REST fallback only; default
  dir: designs/                  # local, gitignored
  scale: 2                       # render scale for reference PNGs
  formats: [png]                 # png|svg per frame (optional)
  max_bytes: 20000000            # per response/asset cap
  auth:
    timeout_s: 600               # how long the loopback waits for the browser
    open_browser: true           # best-effort; the URL is always printed
    token_file: ""               # default: $XDG_DATA_HOME/handleman-hq/figma/oauth.json
```

Parsing rules: unknown keys tolerated; `file_key` and a non-empty `nodes` list
are required when the block exists; `nodes` entries must match `^\d+:\d+$`;
`provider` must be `figma` in this release. `Contract.design` is a typed dict;
`hq preflight` reports it and validates the token when it is set.

A spec opts in with `design.toml`:

```toml
[figma]
file_key = "<key>"
node = "12:34"                   # the frame this spec implements

[[token]]
name = "--color-primary"
value = "#1d4ed8"

[[region]]
id = "top-card"
selector = "[data-testid='top-card']"
frame = "12:34"
tolerance_px = 2

[screenshot]
frame = "desktop"                # which cached render / viewport
baseline = "designs/<key>/12:34.png"
threshold = 0.02                 # fraction of differing pixels
```

## Transport: MCP with first-run OAuth

Figma's remote server advertises standard MCP authorization (verified
2026-11-26):

```
resource      https://mcp.figma.com/mcp
AS metadata   https://api.figma.com/.well-known/oauth-authorization-server
authorize     https://www.figma.com/oauth/mcp
token         https://api.figma.com/v1/oauth/token
register      https://api.figma.com/v1/oauth/mcp/register   (DCR)
PKCE          S256 · state required · scope mcp:connect
Bearer        resource_metadata="https://mcp.figma.com/.well-known/oauth-protected-resource"
```

The **`mcp` Python SDK 1.30.0** (already pulled in by CrewAI) provides
`OAuthClientProvider(server_url, client_metadata, storage, redirect_handler,
callback_handler, timeout)` and `streamablehttp_client(url, auth=provider)`.
We use them rather than hand-rolling OAuth:

- `OAuthClientMetadata(redirect_uris=["http://127.0.0.1:<port>/callback"],
  token_endpoint_auth_method="client_secret_basic", scope="mcp:connect",
  client_name="handleman-hq")`.
- `redirect_handler(url)` writes `run.json.auth.url`, prints a boxed URL in the
  human log and (best effort) opens the browser.
- `callback_handler()` receives `(code, state)` from a loopback HTTP server
  bound to `127.0.0.1` (default port 8765, fallback to an ephemeral port; DCR
  registers the chosen URI), validates `state`, and returns it to the SDK.
- `TokenStorage` is file-backed at `$XDG_DATA_HOME/handleman-hq/figma/oauth.json`
  (0600), holding the DCR client info and access/refresh tokens. It is never in
  the repo, never in a prompt, never in `run.json`.
- Expired access tokens refresh silently; `invalid_grant` drops the token and
  re-runs the authorization step.

### First-run flow (the operator's requirement)

1. A run needs Figma (a `design:` block or a spec's `design.toml`) and the token
   file is absent/expired.
2. **Before any model call**, the harness enters `awaiting_auth`: it prints the
   URL (`https://www.figma.com/oauth/mcp?...`), records it in
   `run.json.auth`, and waits (`auth.timeout_s`, default 10 min).
3. The user authorizes in the browser; Figma redirects to
   `http://127.0.0.1:<port>/callback?code=…&state=…`.
4. The callback server returns the code, the SDK exchanges it, the token is
   stored 0600, and the **same run continues** (design fetch → planner).
5. No callback before the timeout → `figma_auth_timeout`; the URL stays in the
   record and a re-run retries. `--non-interactive` (`SWARM_NONINTERACTIVE=1`)
   fails immediately with `figma_auth_required` and the URL.
6. Remote host: document `ssh -L <port>:127.0.0.1:<port>` or `hq figma auth
   --paste` (paste the redirect URL; parse `code`/`state`) for a browser on
   another machine.

### MCP session and tools

- Connect with `streamablehttp_client` + `ClientSession`; initialize, then call
  tools. The harness is synchronous, so each call opens a short session (the
  OAuth provider/token is reused); a persistent session is an optimisation.
- **Read-only allowlist** exposed to the coder/verifier:
  `get_metadata`, `get_design_context`, `get_screenshot`, `get_variable_defs`,
  `download_assets`, `get_code_connect_map`, `search_design_system`,
  `get_libraries`. Everything else — especially `use_figma`,
  `generate_figma_design`, `create_new_file`, `upload_assets` — is not exposed.
- Arguments are validated against the allowlisted `file_key`/nodes; the model
  cannot introduce a URL. Tool outputs are untrusted data; generated code is
  reference, never executed.
- Calls are budgeted per task (default 8) and cached under
  `designs/<key>/mcp/<tool>-<node>-<hash>.json` (+ images), so a retry or the
  verifier does not call Figma again. Base64 images are written to files and
  only the path enters the prompt.
- `hq figma status` reports token presence/expiry/account (`whoami`), never the
  token; `hq figma logout` deletes it.

### REST transport (first-class, not just a fallback)

Figma's **official REST API** is a supported transport alongside MCP. It is not
something Figma "proposes" instead of MCP; it is the raw HTTP API the MCP server
itself is built on, and it is the right choice for CI/headless:

- `GET /v1/files/{key}/nodes?ids=…` — file/node JSON (the IR source)
- `GET /v1/images/{key}?ids=…&format=png&scale=…` — reference renders
- `GET /v1/files/{key}/variables/local` — variables (plan-dependent)
- `GET /v1/files/{key}/components`, `/styles` — component/style inventory
- Auth: `X-Figma-Token` personal access token, or a Figma OAuth app with REST
  scopes (`Authorization: Bearer`). **The MCP OAuth token is not a REST token**:
  it is issued for `mcp:connect`/the MCP resource, so REST needs its own
  `FIGMA_TOKEN` (or its own OAuth app).

`transport: rest` (or `auto` with only `FIGMA_TOKEN`) writes the **same cache**
as MCP, so the IR, brief, prompts, checks and offline behaviour are identical.

| | MCP | REST |
| --- | --- | --- |
| Auth | OAuth (DCR + PKCE), interactive first run | Personal access token (or REST OAuth app) |
| Data | tools: metadata, design context/code, variables, screenshots, assets, Code Connect, comments | raw nodes, images, variables, components, styles |
| `get_design_context` (React/Tailwind code) | yes | no |
| Code Connect mappings | yes (`get_code_connect_map`) | no (CLI is separate) |
| CI/headless | needs a browser callback (or paste) | yes, token only |
| Output | same design cache | same design cache |

`auto` (default) is token-first: check `token_env` (`FIGMA_TOKEN`); if it is
present, use REST. If it is absent, switch to MCP and start the first-run OAuth.
A stored MCP token does not override an explicit API token. The operator can
force either with `transport: mcp|rest` or `--transport`. Both are first-class;
neither is deprecated.

## Design cache (local, gitignored, the only thing the queue reads)

```
designs/<file-key>/
  index.json        # {"file": {...version}, "nodes": [...], "tokens": {...}}
  <node>.json       # one allowlisted frame (normalized IR)
  <node>.png        # reference render at `scale`
  tokens.json       # variables + styles (colors, spacing, type)
  design-brief.md   # human/model-readable brief: tree, text, tokens, components
  design.lock       # file version, node IDs, sha256 of every artifact
```

IR per node (minimum, source-agnostic):

```json
{
  "id": "12:34",
  "name": "Plan / desktop",
  "type": "FRAME",
  "bounds": {"x": 0, "y": 0, "w": 1280, "h": 800},
  "layout": {"mode": "VERTICAL", "gap": 12, "padding": [16, 16, 16, 16]},
  "fills": [{"type": "SOLID", "color": "#ffffff"}],
  "characters": null,
  "children": [ ... ],
  "components": [{"name": "TopSearchCard", "node_id": "..."}]
}
```

Rules: stable ordering, no Figma-only blobs, text truncated per node, total IR
size capped; the brief is derived from the IR, never hand-written.

## Command

```
hq design sync [--force] [--spec <substring>]
hq design check            # cache matches the configured version/lock
```

`sync`:

1. Read the contract; require `FIGMA_TOKEN` (via `token_env`) — missing is
   `design_token_missing`, not a crash.
2. `GET /v1/files/{key}/nodes?ids=<allowlist>`; also fetch `variables/local`
   when the plan allows it, else `styles` + `components` (degrade, never fail the
   sync for a missing optional endpoint).
3. `GET /v1/images/{key}?ids=<allowlist>&format=png&scale=<scale>`; download the
   returned URLs (short-lived), cap size, verify content type.
4. Write the cache atomically (temp dir → replace), then `design.lock` with the
   file `version`, node IDs and sha256 hashes.
5. Print a one-line summary (`synced 2 frames, 4 tokens, 1.2 MB`) and the cache
   path. Never print the token or a URL containing it.
6. `--force` refetches; otherwise a matching lock is a no-op.

`check` verifies the lock hashes and that every `design.toml` node exists; it is
what preflight/the queue call. Failure reasons: `design_missing`,
`design_stale`, `design_node_missing`, `design_token_missing`.

## Queue integration

- **Preflight**: when `design:` exists, validate the token (presence only) and
  run `design check`; a stale cache blocks the run before an LLM call.
- **Planner**: `plan_prompt` includes `designs/<key>/design-brief.md` for the
  spec's node; one task per frame/section; the brief is context, the spec is the
  source of truth. Do not let the planner invent frames outside the allowlist.
- **Coder**: the brief, the node JSON path and the reference PNG path are in the
  prompt; assets are already in `designs/` (copy into the frontend, never edit the
  cache). `designs/` is excluded from the coder scope by the contract guard.
- **Verifier / QA**: receives the reference PNG and the app screenshots; the
  vision verdict is advisory, the deterministic checks below are not.
- **Run record**: `run.json.design = {"file_key", "node", "version", "stale":
  false}`; a task that names a design node but has no cache fails with
  `design_missing` before any code is written.

## Design checks (deterministic)

The acceptance/visual browser runner gains a design facts section; the harness
evaluates it:

- **Tokens**: each `[[token]]` must equal the computed CSS custom property on
  `:root` (exact string, whitespace-normalised). Fail: `design_token`.
- **Regions**: the element's rect must match the frame's scaled bounds within
  `tolerance_px`; report the delta. Fail: `design_region`.
- **Screenshot**: pixel diff of the app screenshot vs the cached reference at the
  same viewport, fraction of differing pixels ≤ `threshold`. Diffs are written to
  `<run>/design_diff/` for review. Fail: `design_screenshot`.
- `--strict` makes a missing design check fatal (like an uncovered AC);
  `--selftest` mutates a token/region and proves the check can fail.

Vision remains advisory; it explains a diff, it does not decide green.

## Security and limits

- `FIGMA_TOKEN` lives in `.env`/env, is read only by `sync`, and is redacted from
  logs, `run.json`, prompts and artifacts.
- File key and nodes come from the operator's `swarm.yaml`/`design.toml`; model
  output cannot add a URL or node.
- `designs/` is read-only during a run; `sync` is the only writer and uses
  atomic replace.
- Downloads are capped (`max_bytes`), content-type checked, and never extracted
  or executed.
- 429s back off with jitter; a sync is idempotent per file version.
- No Figma write tools are called by the harness.

## OpenCode operator lane (target repo)

Not part of the harness code, but shipped as documentation:

- `opencode.json` declares `figma` as a remote MCP server
  (`https://mcp.figma.com/mcp`); auth is OAuth via `/mcps` (no secret in git).
- A `figma-implement` skill: frame link → `get_metadata` →
  `get_design_context` (ask for Svelte/plain HTML) + `get_screenshot` +
  `get_variable_defs` → map to existing components/tokens → implement → verify.
- Desktop fallback (`http://127.0.0.1:3845/mcp`) documented for Dev/Full seats.
- Code Connect is optional; use it when the file has mappings.

## Acceptance Criteria

- **AC-1 — Sync.** `hq design sync` fetches the configured file/nodes and writes
  the cache layout above, atomically, with a `design.lock` containing the Figma
  file version and sha256 hashes. A second run without `--force` is a no-op.
- **AC-2 — Offline.** With the cache present, the planner/coder/acceptance run
  without a Figma token or network; a run with `FIGMA_TOKEN` unset still passes
  the design checks.
- **AC-3 — Allowlist.** Only nodes in `swarm.yaml`/`design.toml` are fetched or
  put in a prompt; an unknown node is `design_node_missing` and no LLM is called.
- **AC-4 — Prompts.** The planner/coder prompt includes the brief and reference
  PNG path for the task's node; the token and raw Figma URLs are absent.
- **AC-5 — Checks.** Token, region and screenshot checks are deterministic;
  `--strict` fails an uncovered design AC and `--selftest` proves each check can
  fail.
- **AC-6 — Stale.** A lock/version mismatch is a typed `design_stale` stop, and
  `hq design check` reports it without running a model.
- **AC-7 — Secret safety.** No token appears in `run.json`, prompts, logs or
  artifacts; the redaction test covers URLs with `access_token`.
- **AC-8 — Docs.** `docs/design.md` documents the contract, cache, commands,
  checks and the OpenCode lane; `swarm.yaml.example` has the block.
- **AC-9 — Tests.** Unit tests cover the IR normaliser, the lock/hash, the
  allowlist, the checks and redaction; the factory suite stays green.
- **AC-11 — First-run OAuth.** With no stored token, a run that needs Figma
  prints a working authorization URL, receives the loopback callback, exchanges
  the code, stores the token 0600 and continues the same run. A timeout is
  `figma_auth_timeout`; `--non-interactive` is `figma_auth_required` with the
  URL. `hq figma auth/status/logout` manage it; the token is never logged.
- **AC-12 — Refresh.** An expired access token refreshes silently; an invalid
  refresh drops the token and re-prompts. `hq figma status` reports expiry
  without printing the secret.
- **AC-13 — Read-only tools.** The MCP allowlist exposes only read tools; write
  tools are absent; the file/node allowlist is enforced on arguments; calls are
  budgeted and cached; base64 images become files.
- **AC-14 — REST parity.** `transport: rest` with `FIGMA_TOKEN` writes a cache
  that produces the same IR/brief/checks; `auto` selects it when no MCP token is
  present. The MCP token is not reused for REST.
- **AC-15 — Target pilot.** The comfort-walking-router implements one frame from
  a cached design with the design checks green (or an honest, reported
  threshold), proving the lane end-to-end.

## Open questions

1. Which Figma plan/seat will the operator use? The remote MCP is available on
   all plans but a Full/Dev seat avoids limits; the desktop server needs a paid
   plan.
2. Does the design rely on a component library / Code Connect? If yes, map the
   components before writing code; otherwise the coder recreates them.
3. Fonts: which families are licensed, and should they be self-hosted or system
   fallbacks?
4. Is dark mode / a second breakpoint in scope for the first design?
5. Does the acceptance screenshot diff run in the hermetic stand (recommended)
   or only in the live lane?
