# 057 Figma Design Support — Spec (harness)

Status: proposed · Owner: operator · Depends on: 042 (visual phase), 043
(acceptance), 048 (contract), 049/052 (layout), 056 (drivers)

## What / Why

The operator is preparing a Figma design for the comfort-walking-router. The
queue can already implement prose specs, but nothing in the harness can read a
design file, so a human would have to translate frames into words and then judge
the result by eye. That is exactly the work the dark factory is supposed to own.

Two lanes are needed and they are deliberately different:

- **Operator lane (OpenCode)** — interactive design exploration and one-off
  implementation through Figma's MCP server. A person is present, OAuth is fine,
  the latest tools matter more than reproducibility.
- **Queue lane (harness)** — unattended implementation from a **committed,
  versioned design cache** fetched by one deterministic command. No OAuth during
  a run, no network dependency, no token in a prompt.

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

Decision: **MCP for the human, REST + cache for the queue.** MCP's OAuth cannot
run inside an unattended flow, and its generated React/Tailwind code is the wrong
input for a Svelte app. The raw IR + variables + reference renders are stable,
reviewable and offline.

## Goals

1. One command (`hq design sync`) turns an allowlisted Figma file/nodes into a
   committed design cache (normalized IR, renders, tokens, brief, lock).
2. The planner, coder, verifier and acceptance can implement and verify a frame
   **offline** from that cache; no OAuth, no Figma call during a run.
3. Design fidelity becomes deterministic where possible: computed tokens, region
   bounds, and a thresholded screenshot diff join the existing gates; the vision
   model stays advisory.
4. A stale or missing design cache is a typed stop, not a silent freehand
   implementation.
5. The OpenCode operator lane is documented and shareable in the target repo
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
  file_key: "<key from /design/<key>/...>"
  nodes: ["12:34", "56:78"]      # allowlist; no other node may enter a prompt
  token_env: FIGMA_TOKEN         # default
  dir: designs/                  # committed cache
  scale: 2                       # render scale for reference PNGs
  formats: [png]                 # png|svg per frame (optional)
  max_bytes: 20000000            # per response/asset cap
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

## Design cache (committed, the only thing the queue reads)

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
- **AC-10 — Target pilot.** The comfort-walking-router implements one frame from
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
