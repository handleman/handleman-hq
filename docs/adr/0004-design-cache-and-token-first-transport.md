# Figma is fetched at sync time into a committed cache; the transport is token-first

The design lane reads Figma through MCP (first-run OAuth) or the REST API (a
personal access token), and both write the same committed cache (IR, brief,
renders, tokens, lock). The run itself reads only the cache: an unattended night
must not need an OAuth session, and a design that changed under a run must be a
typed stop, not a silent surprise. `auto` is token-first — a present
`FIGMA_TOKEN` selects REST, otherwise MCP OAuth — because an explicit API token
is the operator's deliberate choice. Deterministic token/region/screenshot
checks gate; the vision pass stays advisory.

**Considered:** live MCP calls during every run (rejected: interactive OAuth,
non-determinism), REST-only (rejected: no Code Connect/latest tools), no cache
(rejected: no offline/auditable run), screenshot diff as the only check
(rejected: noisy on fonts/AA).
