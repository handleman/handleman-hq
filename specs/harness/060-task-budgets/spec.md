# 060 Task Budgets by Work Type — Spec

Status: implemented (2026-11-28).

## What / Why

The per-task caps are one size for every task. The comfort-walking-router run
data shows e2e and visual/screenshot tasks are the expensive tail: their cost
p90 is 2.9–4.1× a coding task, and the e2e maximum is 10.9× the coding p90.
A single coding cap either blocks a legitimate e2e/visual task or leaves the
coding cap needlessly high. These tasks should get a larger profile, never a
smaller one.

## Evidence (app runs, 2026-11-27)

See [`evidence.md`](evidence.md). Summary:

| profile | n | cost p90 / max | tokens p90 / max | seconds p90 / max |
| --- | --- | --- | --- | --- |
| coding | 180 | $0.14 / $0.25 | 851k / 1.68M | 1663 / 4915 |
| e2e | 47 | $0.58 / $1.53 | 972k / 2.16M | 1110 / 1802 |
| visual | 15 | $0.40 / $0.69 | 857k / 1.38M | 1074 / 1415 |

The e2e/visual tails are real (041 T4 hit the old 2M token cap at 2.16M tokens;
the T2 cost cap at $1.06; the T5 wall clock at 1800s). A **2×** profile of the
coding caps ($3→$6, 4M→8M, 3600→7200s, wall 1800→3600s) gives 3.7–8.7× the
observed e2e/visual maxima. That is the optimal policy: keep the coding cap
tight, double it for the two tails, and record which profile ran.

## Scope

- A small classifier (`swarm/budget.py`) for `coding`, `e2e`, `visual` from the
  task brief and spec name:
  - e2e: `e2e`, `playwright`, `browser spec`, `.spec.ts`;
  - visual: `screenshot`, `visual`, `design`, `figma`, `layout`, `acceptance`,
    `snapshot` (e2e wins when both match);
  - coding: everything else.
- `SwarmFlow` reads the base caps, then scales tokens, total cost, total
  runtime, per-task cost, per-task seconds and the task wall budget by the
  profile multiplier. The default is **2.0**; `SWARM_E2E_CAP_MULTIPLIER` and
  `SWARM_VISUAL_CAP_MULTIPLIER` override it (floor 1.0).
- `run.json.budget` records `profile` and `cap_multiplier`; docs describe the
  evidence and the env knobs.
- The target's `.env` sets the multipliers; the coding caps stay the operator's
  base.

## Non-goals

- Changing the model profile or the acceptance vision's model.
- Scaling the coding profile or making any cap smaller.
- Per-task caps inside a spec's target contract (the env remains the source).
- Capping the acceptance/live lane; its model is separate (`SWARM_ACCEPT_MODEL`).

## Acceptance Criteria

- [x] AC-1: **Evidence.** `evidence.md` records the sampled runs, the p90/max
  per profile and the 2× choice with the headroom calculation.
- [x] AC-2: **Classification.** `task_profile` maps e2e and visual briefs/spec
  names correctly (e2e wins a mixed brief); coding is the default.
- [x] AC-3: **Caps.** An e2e/visual `SwarmFlow` scales all six caps by the
  multiplier (default 2.0, env override, floor 1.0); a coding task is unchanged.
- [x] AC-4: **Observability.** `run.json.budget` reports the profile and
  multiplier; `docs/setup.md`/`docs/run-guards.md` document the knobs and the
  evidence; a target `.env` can set the multipliers.
- [x] AC-5: **Verification.** Unit tests for the classifier/multiplier and the
  six-cap scaling; the factory suite, ruff and audit stay green.

## Verification

`pytest tests/test_task_budgets.py`, the factory suite (957+ tests), ruff and
`factory-audit`. The app pins the release and sets both multipliers to 2.
