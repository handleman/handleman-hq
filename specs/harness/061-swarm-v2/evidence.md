# Evidence — swarm v2

Sampled from the comfort-walking-router `harness/runs/*/run.json` on 2026-11-28
(the same corpus 059/060 used). 242 runs with a run record; statuses and role
usage are taken from `run.json`, not from the event stream, so a killed run with
no record is not counted.

## Outcomes

| status | runs |
| --- | --- |
| green | 95 |
| needs_human | 125 |
| budget_exhausted | 10 |
| crew_error | 10 |
| preflight_failed | 1 |
| interrupted | 1 |

Reason codes on non-green runs:

| reason | runs |
| --- | --- |
| `no_delta` | 31 |
| `delta_incomplete` | 27 |
| `verifier_blocked` | 19 |
| (no reason recorded) | 16 |
| `wall_budget` | 11 |
| `budget_exhausted` | 10 |
| `e2e_unclassified` | 8 |
| `no_progress` | 6 |
| `correction_reverted` | 5 |
| `crew_error` | 3 |
| `reviewer_blocked` | 3 |
| `reviewer_no_verdict` | 2 |
| other | 5 |

The delta guard alone is **58/242 (24%)**: those runs never reached a useful
judge. The verifier blocked **29** runs; 19 were the recorded reason, the rest
were repaired or superseded by another stop.

## Cost by role family

Role ids are grouped by the prefix before `:` (`coder:fix1` → coder).

| family | runs | calls | cost | tokens |
| --- | --- | --- | --- | --- |
| coder | 196 | 1052 | $7.08 | 33.3M |
| senior | 81 | 182 | $5.36 | 16.4M |
| verifier | 94 | 152 | $0.57 | 9.3M |
| QA | 114 | 282 | $0.37 | 9.9M |
| e2e | 1 | 3 | $0.05 | 0.3M |
| **total run cost** | | | **$14.15** | |

`planner`, `reviewer` and `visual` **do not appear** in per-role usage: the
planner's spend is folded into the first timed phase but its role id never
reached `usage.by_role`, the reviewer verdict was produced by the QA role, and
no visual run spent tokens.

## Planning and work shape

- `plan_steps`: mean **2.33**, median **1**, max **8**.
- 184/242 runs record at least one coder step; the largest step index is 8.
- 81 runs used a senior crew; 94 used a verifier; 114 used QA.
- 34 verifier blocks/repairs across the senior paths (the `senior:verify*` roles
  are 59 of the senior family's 81 runs).

The planner is not the bottleneck it was designed to be: a median of one step
means the implementer is already working at task scale, and a paid planning call
plus a plan cache sits in front of every task.

## Hypothesis

1. Give the implementer the whole task and let it plan inside its tool loop.
   Remove the planner call and the micro-step boundaries that hide parts of the
   brief from the coder.
2. Run the gates deterministically after each attempt. QA's only indispensable
   job was executing gates and recording evidence; the harness can do that
   itself, and `save_run` already re-checks the final delta.
3. Merge the verifier into one read-only auditor that sees the gate transcript
   and the scenario, so a scenario gap and a gate failure share one feedback
   channel and one round.
4. Escalate the *model tier* on a failed round instead of switching persona.
   The senior family already costs 38% of the corpus ($5.36); the persona adds
   nothing the same prompt with a stronger model does not.

Expected effects: one fewer paid call per task (planner), one fewer context per
round (verifier), fewer fix rounds because the implementer saw the whole brief,
and a clearer failure record (`flow.version`, implementer rounds, auditor
verdicts).

## Task-type caps (existing 060, unchanged)

The 060 classifier on the same corpus gives **126 coding / 52 e2e / 64 visual**
runs (060's `evidence.md` says 180/47/15 — its counts were taken with a
different classifier and are corrected here; the cap decision is unaffected).

| profile | n | cost p90 / max | tokens p90 / max | seconds p90 / max |
| --- | --- | --- | --- | --- |
| coding | 126 | $0.126 / $0.246 | 824k / 1.68M | 1793 / 4915 |
| e2e | 52 | $0.263 / $1.531 | 972k / 2.16M | 1110 / 2105 |
| visual | 64 | $0.037 / $0.686 | 622k / 1.38M | 926 / 1415 |

The 060 caps ($3 / 4M / 3600s coding, 2× the tails) stay in force for this
release. An evidence-tuned set would be:

| profile | cost/task | tokens | task seconds | headroom vs max |
| --- | --- | --- | --- | --- |
| coding | $1.00 | 3.5M | 5400 | 4.1× / 2.1× / 1.1× |
| e2e | $3.00 | 4.5M | 3600 | 2.0× / 2.1× / 1.7× |
| visual | $1.50 | 3.0M | 3000 | 2.2× / 2.2× / 2.1× |

The recommendation is recorded, not implemented: it needs its own spec and a
decision about the total 4 h budget. The pilot runs on the 060 caps so a v2
result is comparable with the v1 corpus.

## Pilot log

- **2026-11-28, 042 T2 (v0.7.0):** first v2 run, `needs_human` / `no_delta`.
  One implementer round, 31 LLM calls, 280k prompt tokens, $0.044, 98 s; it
  read the tree and answered that everything was "landed in App.svelte" with an
  empty git delta, and the delta guard stopped the task before the escalation
  tier could run. Fixes in v0.7.1: a no-delta round now feeds back exactly what
  the harness saw and retries on the escalation tier (the last round still stops
  `no_delta`); the implementer is told to land early, retry a non-unique
  `Repo Edit`, and prove the write with `git diff --stat`; the iteration budget
  is 60. The same task is the re-run.

## Limits

- The corpus is one target and one model profile (OpenCode Go); the role costs
  are not generalisable to a local or a different paid tier.
- Reason codes are the harness's own labels; `no_delta` includes briefs that
  were already satisfied and deliberately changed nothing.
- The v2 green rate is a pilot result, not this evidence; this document records
  why the design was chosen, and the pilot records whether it worked.
