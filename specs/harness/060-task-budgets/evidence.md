# Evidence — e2e/visual task budgets

Sampled from the comfort-walking-router `harness/runs/*/run.json` (the task's
`usage` plus its `tasks.md` brief) on 2026-11-27. Task type is derived from the
brief/spec name (the same classifier the release ships); 126 coding, 52 e2e and
64 visual runs had usage.

| profile | n | cost p90 | cost max | tokens p90 | tokens max | seconds p90 | seconds max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| coding | 126 | $0.13 | $0.25 | 824k | 1.68M | 1793 | 4915 |
| e2e | 52 | $0.26 | $1.53 | 972k | 2.16M | 1110 | 2105 |
| visual | 64 | $0.04 | $0.69 | 622k | 1.38M | 926 | 1415 |

Notable runs:

- `041-figma-redesign T4` — 2.16M tokens, $0.73, hit the old 2M token cap.
- `041-figma-redesign T2` — $1.07, 1.21M tokens, hit the old $1 task cap.
- `041-figma-redesign T5` — $0.40, 1.38M tokens, 1800s wall budget (visual).
- `042-map-destination-build-flow T4` — $1.53, 1.10M tokens, e2e test authoring
  (failed no-delta; the cap was not the cause).
- `040 T6 / T25` — e2e runs at $0.73/1.2M and $0.26/1.2M.

## Policy

The coding profile is the operator's base (currently $3 / 4M / 3600s / 1800s
wall). e2e and visual profile = **2×** the base:

| profile | cost/task | tokens | task seconds | wall | headroom vs max |
| --- | --- | --- | --- | --- | --- |
| coding | $3 | 4M | 3600 | 1800 | 12× / 2.4× / 0.7×* |
| e2e | $6 | 8M | 7200 | 3600 | 3.9× / 3.7× / 3.4× |
| visual | $6 | 8M | 7200 | 3600 | 8.7× / 5.8× / 5.1× |

\* coding's 3600s task cap is below the one 4915s outlier (a local run); the wall
budget is the effective guard. The e2e/visual 2× is not a claim that those
tasks are always bigger; it keeps the same headroom policy for the measured
tail. The multiplier is configurable because a target can be cheaper or more
expensive.
