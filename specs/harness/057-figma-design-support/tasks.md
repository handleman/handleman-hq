# 057 Figma Design Support — Tasks

One task maps to one AC (small tasks may share an AC). Documentation and the
`swarm.yaml.example` change in the same task that introduces the field.

- [x] T1 (AC-11, AC-12): **OAuth + token storage.** `src/swarm/design/oauth.py`
  using `mcp` 1.30 `OAuthClientProvider` + a file-backed `TokenStorage`
  (`$XDG_DATA_HOME/handleman-hq/figma/oauth.json`, 0600): DCR client info,
  access/refresh tokens, expiry, silent refresh, `invalid_grant` → re-auth.
  `hq figma auth|status|logout`; `--non-interactive` → `figma_auth_required`
  with the URL. Tests use a fake authorization server; the token never appears
  in output.
- [x] T2 (AC-11): **First-run resume.** Loopback callback server on
  `127.0.0.1:8765` (ephemeral fallback), `state` validation, browser open
  best-effort, URL in the human log + `run.json.auth.url`, timeout
  (`figma_auth_timeout`). Before any model call, the run enters `awaiting_auth`
  and **continues in the same process** after the callback. `--paste` parses a
  pasted redirect URL. Test: no token → URL → callback → token stored → run
  proceeds.
- [x] T3 (AC-13): **MCP client + read-only tools.** `streamablehttp_client` +
  `ClientSession`; initialize/list_tools; expose only `get_metadata`,
  `get_design_context`, `get_screenshot`, `get_variable_defs`,
  `download_assets`, `get_code_connect_map`, `search_design_system`,
  `get_libraries`. Block write/unknown tools. Validate file/node against the
  allowlist; per-task budget (8); size caps; cache results under
  `designs/<key>/mcp/`; base64 images → files. Mock MCP server tests.
- [x] T4 (AC-14): **REST transport + auto.** `src/swarm/design/rest.py` with
  `X-Figma-Token`: `/nodes`, `/images`, `variables/local`, `components`,
  `styles`; timeouts, 429 backoff, size caps; the same IR/cache. `transport:
  mcp|rest|auto` (`auto`: `FIGMA_TOKEN` → REST; else MCP OAuth). The MCP token is never sent to REST. Fixture tests prove the same
  brief/IR shape from both.
- [x] T5 (AC-1, AC-3, AC-9): **Sync + lock.** `hq design sync|check` over either
  transport: atomic temp-dir → replace, `design.lock` (Figma version + node ids
  + sha256), no-op when current, `--force`, `--spec`; unknown node →
  `design_node_missing`; tampered hash → `design_stale`. Unit tests.
- [x] T6 (AC-3, AC-6): **Contract + guards.** `Contract.design` parsing
  (`provider`, `transport`, `file_key`, `nodes`, `dir`, `auth`), `design.toml`
  loader, preflight `design check` + auth readiness before the first model
  call, `designs/` out of coder scope, typed reasons. Docs in
  `swarm.yaml.example`.
- [x] T7 (AC-4): **Prompts and run record.** Planner: brief + node. Coder:
  brief + reference PNG + read tools. Verifier: reference PNG + app screenshots.
  Prompt tests assert no token/URL. `run.json.design` and `run.json.auth`.
- [x] T8 (AC-5): **Deterministic checks.** Browser facts gain computed CSS
  variables + region rects; `design_eval.py` checks tokens (exact), regions
  (`tolerance_px`), screenshot diff (fraction ≤ threshold) with diffs in
  `<run>/design_diff/`; wire into acceptance + 042; `--strict`/`--selftest`.
- [x] T9 (AC-8): **Docs.** Factory `docs/design.md` (transports, OAuth, cache,
  commands, checks, security, headless/SSH); `swarm.yaml.example`; target repo
  `opencode.json` + `figma-implement` skill + `docs/figma.md` (both transports).
- [ ] T10 (AC-15): **Pilot + release — pending the design file.** Sync one real frame via MCP (first-run
  OAuth) and one via REST; implement the frame in a product spec with the design
  checks offline; release `v0.6.0` and pin the app.
- [x] T11 (AC-9): **Suite.** Tests for OAuth/storage, MCP allowlist/budget,
  REST parity, sync/lock, guards, checks and redaction; `ruff` +
  `factory-audit`; the full suite stays green.
