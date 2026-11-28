# 061 Swarm v2 — one implementer, one auditor — Spec

Status: approved (2026-11-28); implementation in progress.

## What / Why

The 242-run corpus (see [`evidence.md`](evidence.md)) shows the current four-role
loop spends most of its money and wall clock on work that does not decide the
outcome:

- 95/242 green; 125 `needs_human`. 24% of runs stop on the model-free delta guard
  (`no_delta` 31, `delta_incomplete` 27), before any judge is useful.
- The planner averages **2.3** steps (max 8) but adds a paid call and a cache
  every task; its steps are routinely narrower than the brief.
- The coder family costs **$7.08 / 1052 calls**, the senior family **$5.36 / 81
  runs**, QA **$0.37 / 282 calls**, the verifier **$0.57 / 94 runs**. Planner,
  reviewer and visual roles do not appear in per-role usage at all — the
  reviewer never ran a gate and the verifier blocked 29 runs.
- The QA→coder→QA fix loop and the separate verifier both re-read the same
  delta. The verifier's scenario check is valuable, but as a separate role it
  pays for a second full context and then hands corrections back to a senior
  persona.

The redesign keeps the capability and removes the layers: **one implementer**
receives the whole task and plans inside its own tool loop, the harness runs the
gates deterministically, and **one auditor** merges the reviewer and verifier
(judging the delta, the scenario and the recorded gates). After a failed round
the *same* implementer runs on an escalation model tier. There is no per-task
planner, no QA model, no reviewer/verifier split and no senior persona.

## Evidence

See [`evidence.md`](evidence.md). The short version:

| role family | runs | calls | cost |
| --- | --- | --- | --- |
| coder | 196 | 1052 | $7.08 |
| senior | 81 | 182 | $5.36 |
| verifier | 94 | 152 | $0.57 |
| QA | 114 | 282 | $0.37 |

242 runs, $14.15 total. Plan mean 2.33 steps (max 8). 58 runs stopped on the
delta guard; 29 had a blocked verifier.

## Design

### Roles

| Role | Model | Job | Can make a run green? |
| --- | --- | --- | --- |
| Implementer (primary) | `SWARM_IMPLEMENTER_MODEL`, else `SWARM_CODER_MODEL` | Owns the whole task: reads, plans internally, writes code and tests, loops up to `SWARM_V2_MAX_ITER` tool calls. Runs no gates. | no |
| Implementer (escalation) | `SWARM_ESCALATION_MODEL`, else `SWARM_SENIOR_MODEL` | The same builder and prompt after a red round, fed the gate transcript / audit findings. | no |
| Auditor | `SWARM_AUDITOR_MODEL`, else `SWARM_VERIFIER_MODEL`, `SWARM_REVIEWER_MODEL`, `SWARM_SENIOR_MODEL` | Read-only. Judges the recorded gate evidence, the delta and the scenario against the brief and its ACs; returns grounded `FINDING:`/`STEP:` lines and `VERDICT: PASS/BLOCKED`. | **yes** (with green deterministic gates) |

The deterministic harness owns budgets, scope, the delta guard, gates, e2e
evidence, commits and every typed stop. The auditor never runs a gate and never
edits; corrections after a block are the implementer's next round.

### Loop

1. One implementer crew gets the full task: brief, referenced AC paragraphs,
   plan lines, design brief, scope, and the test-first expectation. It plans
   internally; there is no `STEP n:` planner call and no per-step crew.
2. The harness runs the delta guard, formats, then runs **every configured
   gate** itself, recording each execution in `shell_log.jsonl` under
   `Harness Gatekeeper`. Missing/stale evidence is a red gate, not prose.
3. If a browser spec is required, the harness runs the suite through the
   configured e2e driver and records it before the audit.
4. When every gate is green, the auditor runs once over the gate transcript,
   the delta and the scenario context. `PASS` + green gates ends the loop.
5. A red round (gate, e2e, empty delta or grounded audit block) becomes the next
   implementer's feedback. Round 2 and later run on the escalation model tier.
   The loop stops at `SWARM_V2_MAX_ROUNDS` (default 3), on no progress, on an
   ungrounded audit block, or on any typed budget/wall stop. A `no_delta` round
   is retried on the escalation tier (up to the last round) instead of ending the
   task immediately.
6. `save_run` re-checks the gate evidence at the final delta exactly as v1 did.
   Green still means evidence (ADR 0002).

### Rollout

v2 is the default (`SWARM_FLOW_V2=1`). `SWARM_FLOW_V2=0` runs the v1 flow for one
release, so the target can A/B the pilot and roll back without a reinstall. The
old planner/QA/verifier/senior crews stay in the tree as v1's implementation;
v2 never calls them. Their env ids remain valid; the new v2 ids are optional
aliases so an existing `.env` needs no edit. Deleting the v1 crews and dropping
the legacy required ids is a 0.8 cleanup after the pilot, not part of this
release.

The 060 cap profiles and multipliers remain in force. An evidence-tuned cap set
is a separate decision; this spec records the recommendation in `evidence.md`
but does not change the caps.

## Scope

- `src/swarm/flow.py`: v2 selection, implementer/auditor loop, deterministic
  gate runner, escalation, e2e-before-audit, run.json fields, typed stops.
- `src/swarm/crew.py` / `prompts.py`: implementer and auditor builders, prompts,
  rules, stable prefix.
- `src/swarm/llms.py` / `model_config.py`: v2 model aliases with compat
  resolution and fallbacks.
- `src/swarm/evidence.py` (if needed): accept the harness gate agent.
- Tests: `tests/test_flow_v2.py` plus prompt/model-config/evidence updates.
- Docs: `docs/how-it-works.md`, `docs/reference.md`, `docs/run-guards.md`,
  `docs/setup.md`, `docs/domain-model.md`, `GLOSSARY.md`, ADR 0005, README.
- Release: version 0.7.0, factory suite/ruff/audit, tag, app pin/install.

## Non-goals

- Removing the v1 code path in this release (rollback is required for the
  pilot).
- Changing the cap values; 060 stays authoritative.
- Changing Figma cache handling, e2e screenshot locations or acceptance.
- A new visual model; the optional visual phase (`SWARM_VISUAL_QA`,
  `SWARM_VISUAL_BASE_URL`) stays advisory and unchanged.
- Operator-written app code; the pilot's app work stays queue-owned.

## Acceptance Criteria

- [x] AC-1: **Selection & compatibility.** `SwarmFlow` runs v2 by default and
  v1 when `SWARM_FLOW_V2` is `0/false/no/off`; `run.json.flow.version` records
  the selected flow. Existing `.env` files with only the v1 ids still resolve
  implementer/auditor/escalation models (new ids win when set), and preflight
  validates every v2 id and fallback that is set.
- [x] AC-2: **Whole-task implementer.** One implementer crew receives the full
  brief, referenced ACs, plan lines and design brief; it has read/search/create/
  edit/shell tools and no per-step planner call. A retry reuses the same builder
  with the previous round's gate/audit feedback. Usage is recorded under
  `implementer` / `implementer:escalation`.
- [x] AC-3: **Deterministic gates.** After every implementer round the harness
  runs every configured gate itself, records each execution in
  `shell_log.jsonl` under `Harness Gatekeeper`, and rejects stale/missing
  evidence. The final-delta evidence is re-checked at save time; a green run
  therefore needs no QA agent.
- [x] AC-4: **One auditor.** A read-only auditor judges the gate transcript, the
  delta and the scenario against the brief/ACs, and returns
  `VERDICT: PASS|BLOCKED`. A BLOCKED verdict with no checkable citation is an
  ungrounded stop, not another paid round. No verifier or reviewer crew runs in
  v2.
- [x] AC-5: **Tiered escalation.** Round 1 uses the implementer model; from
  round 2 the same implementer builder/prompt runs on the escalation model,
  bounded by `SWARM_V2_MAX_ROUNDS` (default 3) and by a no-progress check. No
  separate senior persona or crew is created.
- [x] AC-6: **Preserved guards.** Caps, wall budget, delta guard, scope revert,
  e2e evidence (run before the audit when required), approval hold, acceptance
  pass and the optional visual phase behave as in v1; all typed stops still
  record `reason_code`.
- [x] AC-7: **Evidence & rollout docs.** `evidence.md` records the corpus,
  hypothesis and the evidence-tuned cap recommendation; ADR 0005, the glossary,
  domain model, how-it-works, setup and run-guards describe v2 and the rollback.
- [ ] AC-8: **Verification.** Unit/integration tests cover selection, model
  compat, implementer/auditor prompts and builders, harness gate evidence,
  pass/block/escalation rounds, and the absence of planner/QA/verifier calls in
  v2. The factory suite, ruff and `factory-audit` pass; release 0.7.0 is tagged
  and the target pin/install is updated.

## Verification

`pytest tests/test_flow_v2.py tests/test_prompts.py tests/test_model_config.py
tests/test_evidence.py`, then the factory suite, `ruff check .`, and
`python -m swarm.factory_audit`. Pilot: run 042 T2–T4 through the queue with v2
on; compare green rate, delta stops, verifier/auditor blocks, cost, tokens and
wall stops against the v1 baseline.
