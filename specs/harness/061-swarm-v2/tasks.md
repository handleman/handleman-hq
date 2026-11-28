# 061 Swarm v2 — Tasks

- [x] T1 (AC-1): Add flow selection (`SWARM_FLOW_V2`, default on), record
  `flow.version` in the run, and keep `SWARM_FLOW_V2=0` on the v1 path. Add the
  implementer/auditor/escalation model aliases with compat resolution and
  preflight validation when set.
- [x] T2 (AC-2): Add implementer prompt/rules/crew (whole brief + ACs + plan +
  design, read/search/create/edit/shell, no gates) and the retry feedback path;
  record usage under `implementer` / `implementer:escalation`.
- [x] T3 (AC-3): Add `_v2_gate_run`: run every configured gate through
  `Harness Gatekeeper`, record evidence at the current hash, handle the
  sole-style formatter, and make final-delta evidence green without QA.
- [x] T4 (AC-4): Add the auditor prompt/rules/crew (read-only, gate transcript +
  scenario context, grounded FINDING/STEP, VERDICT) and the ungrounded-block
  stop; no verifier/reviewer call in v2.
- [x] T5 (AC-5): Add `_run_crew_v2` with tiered escalation, bounded rounds, the
  no-progress check, e2e-before-audit, delta guard and the shared typed stops.
- [x] T6 (AC-6): Verify the preserved guards: caps/wall, scope revert, approval,
  acceptance, visual phase and reason codes. Record the implementer/auditor
  summary in `run.json`.
- [x] T7 (AC-7): Add `evidence.md` and ADR 0005; update GLOSSARY, domain model,
  how-it-works, setup, run-guards and README with v2 and the rollback.
- [x] T8 (AC-8): Add the v2 tests (selection, model compat, prompts/builders,
  gate evidence, PASS/escalation/block/un ground) and update role/prompt tests;
  run the factory suite, ruff and `factory-audit`; release 0.7.0 and update the
  app pin/install.
- [x] T9 (pilot): 042 T2/T3 green on v2; T4 (e2e) was operator-completed after
the swarm e2e was unusable. The comparison is in `evidence.md`: the 060 caps
stay (T2 cost $2.03; the proposed $1 coding cap is rejected), and v1 remains
the fallback for small UI edits until v2 routing is tuned.
