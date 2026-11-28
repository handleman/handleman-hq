# 061 Swarm v2 — Tasks

- [ ] T1 (AC-1): Add flow selection (`SWARM_FLOW_V2`, default on), record
  `flow.version` in the run, and keep `SWARM_FLOW_V2=0` on the v1 path. Add the
  implementer/auditor/escalation model aliases with compat resolution and
  preflight validation when set.
- [ ] T2 (AC-2): Add implementer prompt/rules/crew (whole brief + ACs + plan +
  design, read/search/create/edit/shell, no gates) and the retry feedback path;
  record usage under `implementer` / `implementer:escalation`.
- [ ] T3 (AC-3): Add `_v2_gate_run`: run every configured gate through
  `Harness Gatekeeper`, record evidence at the current hash, handle the
  sole-style formatter, and make final-delta evidence green without QA.
- [ ] T4 (AC-4): Add the auditor prompt/rules/crew (read-only, gate transcript +
  scenario context, grounded FINDING/STEP, VERDICT) and the ungrounded-block
  stop; no verifier/reviewer call in v2.
- [ ] T5 (AC-5): Add `_run_crew_v2` with tiered escalation, bounded rounds, the
  no-progress check, e2e-before-audit, delta guard and the shared typed stops.
- [ ] T6 (AC-6): Verify the preserved guards: caps/wall, scope revert, approval,
  acceptance, visual phase and reason codes. Record the implementer/auditor
  summary in `run.json`.
- [ ] T7 (AC-7): Add `evidence.md` and ADR 0005; update GLOSSARY, domain model,
  how-it-works, setup, run-guards and README with v2 and the rollback.
- [ ] T8 (AC-8): Add the v2 tests (selection, model compat, prompts/builders,
  gate evidence, PASS/escalation/block/un ground) and update role/prompt tests;
  run the factory suite, ruff and `factory-audit`; release 0.7.0 and update the
  app pin/install.
- [ ] T9 (pilot): Run 042 T2–T4 through the queue on v2, record the comparison
  in `specs/product/042-map-destination-build-flow/` and decide the cap follow-up
  from the result.
