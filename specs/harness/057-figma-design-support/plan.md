# 057 Figma Design Support — Plan

## Architecture

```
Figma file
  ├──(MCP, OAuth: DCR + PKCE)──► mcp SDK 1.30 · read-only tools
  └──(REST, FIGMA_TOKEN)───────► raw nodes/images/variables
                     └──► hq design sync ──► designs/<key>/ (committed)
                                                │ IR · PNG · tokens · brief · lock
                                                ▼
                                  planner / coder / verifier / design checks
                                                │
OpenCode operator ──(MCP, OAuth via /mcps)──────┘  (human lane, same file)
```

Both transports write the same cache. `transport: auto` is token-first:
`FIGMA_TOKEN` present → REST; absent → MCP with the first-run OAuth prompt. The cache
is what the queue reads; Figma is contacted only by `hq design sync`/auth.

## Phases

### Phase 1 — MCP client, OAuth and token storage (AC-11, AC-12, AC-13)

- `src/swarm/design/mcp.py`: connect with `streamablehttp_client` +
  `ClientSession`; initialize; `list_tools`; call only the read allowlist.
- `src/swarm/design/oauth.py`: `OAuthClientProvider` + a file-backed
  `TokenStorage` (`$XDG_DATA_HOME/handleman-hq/figma/oauth.json`, 0600), DCR
  client info, access/refresh tokens, refresh/`invalid_grant` handling.
- Loopback callback server (127.0.0.1:8765, ephemeral fallback), `state`
  validation, `redirect_handler` → boxed URL + `run.json.auth.url`, browser
  open best-effort, timeout, `--paste` fallback.
- `hq figma auth|status|logout`; `--non-interactive` typed failures.
- Read-only tool adapter: argument allowlist (file/node), per-task budget,
  response size cap, results cached under `designs/<key>/mcp/`, base64 images to
  files.

Verification: mock MCP server + fake AS in tests (no live Figma in the suite);
token file is never printed; a stored token reconnects without a prompt.

### Phase 2 — REST transport parity (AC-14)

- `src/swarm/design/rest.py`: `X-Figma-Token`; `/nodes`, `/images`,
  `variables/local`, `components`, `styles`; timeouts, 429 backoff, size caps.
- The same normaliser/cache; `transport: rest|mcp|auto`; `auto` selection rules
  (MCP token → MCP; else `FIGMA_TOKEN` → REST; else OAuth prompt).
- Tests with recorded fixtures; a REST cache and an MCP cache produce the same
  brief/IR shape.

### Phase 3 — Sync, queue state and prompts (AC-1–AC-4, AC-6)

- `hq design sync|check`: atomic cache + `design.lock` (file version + hashes),
  no-op when current, typed `design_*` reasons.
- `design.toml` loader (node, tokens, regions, screenshot).
- Preflight: `design check` + auth readiness before the first model call.
- `awaiting_auth` state: print/record the URL, wait, then **resume the same
  run**; the supervisor treats it as a wait, not a model failure.
- Prompts: planner gets the brief/node; coder gets the brief + reference PNG +
  the read tools; verifier gets the reference PNG + app screenshots. Prompt
  tests assert no token/URL.
- `run.json.design` + `run.json.auth`; `designs/` is out of coder scope.

### Phase 4 — Deterministic design checks (AC-5)

- Browser facts: computed CSS variables + region rects.
- `design_eval.py`: tokens (exact), regions (`tolerance_px`), screenshot diff
  (fraction ≤ threshold), diffs in `<run>/design_diff/`.
- Wire into acceptance + 042; `--strict`/`--selftest`; vision stays advisory.

### Phase 5 — Docs and pilot (AC-8, AC-15)

- `docs/design.md` (factory): transports, OAuth, cache, commands, checks,
  security, headless.
- Target repo: `opencode.json` MCP entry + `figma-implement` skill +
  `docs/figma.md` (both transports; MCP for operator, MCP/REST for queue).
- Pilot one real frame; release `v0.6.0`; pin the app.

## Risks

| Risk | Mitigation |
| --- | --- |
| OAuth needs a browser callback | loopback + URL in the run record; `--paste`; SSH forward; REST fallback |
| Token leaks | file 0600 outside the repo; never in prompts/run.json/logs; redaction tests |
| MCP token confused with REST | separate storage; the MCP token is not sent to REST; `auto` rules |
| Design drifts | `design.lock` version + `design_stale` |
| Screenshot noise | token/region checks first; threshold + reported diffs |
| Tool-loop cost | read allowlist, budget, cache, short sessions |
| Coder edits the cache | `designs/` out of scope; sync is the only writer |
| Rate limits | cache by version; 429 backoff; `--force` explicit |

## Definition of done

All ACs checked; first-run OAuth demonstrated (URL → callback → token → resume);
REST parity proven with a `FIGMA_TOKEN`; factory tests/ruff/audit green; a pilot
frame implemented from the cache with no network during the run; docs in both
repos.
