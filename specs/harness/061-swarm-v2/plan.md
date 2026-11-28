# 061 Swarm v2 — Plan

1. **Selection.** Add `flow_v2_enabled()` (`SWARM_FLOW_V2`, default on) and
   `flow_version()`; record `flow.version` in `run.json` and the run state.
   The v2 branch returns before the v1 planner block, so v1 stays byte-for-byte
   reachable with the switch off.
2. **Models.** Add `implementer`, `auditor` and `escalation` aliases in
   `model_config.ROLES` as optional roles with compat sources
   (`SWARM_CODER_MODEL`, `SWARM_VERIFIER_MODEL`/`SWARM_REVIEWER_MODEL`,
   `SWARM_SENIOR_MODEL`). `resolve_models` fills the alias from the first set
   source. `llms.implementer_llm(escalated=…)` and `llms.auditor_llm()` build
   them with the same paid guard, cache hints and per-role fallback chain.
   Preflight validates the aliases and their fallbacks when set, and shows the
   resolved source.
3. **Prompts.** Add `IMPLEMENTER_RULES` (whole task, own plan, test-first, no
   gates, land files) and `AUDITOR_RULES` (read-only, judge gates + scenario,
   grounded findings). `stable_prefix` gives the implementer ACs + plan lines +
   design brief; the auditor is a scenario prompt. Add `implementer_prompt` and
   `auditor_prompt` with volatile feedback last.
4. **Crews.** `build_implementer_crew(spec_dir, task, round_no, feedback,
   escalated)` uses `_tools(allow_gates=False)` and `SWARM_V2_MAX_ITER`
   (default 30). `build_auditor_crew(spec_dir, task, context_text)` uses
   `FullFileReadTool`, `SearchTool` and `Guarded Shell` with `allow_gates=False`
   (roles `implementer`/`auditor`), no write tools.
5. **Deterministic gates.** Add `_v2_gate_run(changed)`: revert out-of-scope
   edits, run `_pre_qa_style`, execute every configured gate through
   `ShellTool(agent_role="Harness Gatekeeper")`, read the evidence at the
   current hash, run the sole-style formatter and re-run when it changed files,
   then set `self._evidence_agents = ("Harness Gatekeeper",)`.
6. **The loop.** `_run_crew_v2(task, kickoff)`:
   - one implementer round per attempt, `implementer` then
     `implementer:escalation`;
   - delta guard with the same typed `_DeltaStop`;
   - `_v2_gate_run`; if required, `_run_e2e_deterministically` and treat a red
     suite as a red round;
   - when all gates pass, one auditor crew; parse `reviewer_verdict`; PASS ends;
     a grounded BLOCKED feeds the next round; an ungrounded block stops;
   - no-progress check on the delta signature; bounded by
     `SWARM_V2_MAX_ROUNDS`;
   - record `state.gates`, `state.transcript`, `review_verdict`, `review_text`,
     `state.implementer` (rounds, escalations), `state.auditor` (verdict,
     findings, grounded), and `flow.version`.
7. **Preserved paths.** Keep the existing `save_run`/`gate` listeners, e2e
   guards, approval, acceptance, visual phase, cap scaling, wall/budget checks
   and typed stops. The v2 branch is inside the existing `try`, so the typed
   handlers are shared. `_review` remains for the e2e repair path only.
8. **Tests.** New `tests/test_flow_v2.py`: selection, model compat, prompt and
   builder shape, harness gate evidence accepted at the current hash, one
   implementer + auditor on PASS, escalation on a red round, grounded vs
   ungrounded blocks, and no planner/QA/verifier builder in v2. Update the
   role-table and prompt tests.
9. **Docs and release.** ADR 0005, GLOSSARY/domain-model entries, how-it-works
   roles/flow, setup/run-guards knobs, README. Bump to 0.7.0, run the suite,
   ruff and `factory-audit`, tag, then update the app pin/install and pilot
   042 T2–T4.

## Risks

- **A full-task implementer may run out of context or iterations.** Mitigate
  with a 30-call cap, a compact feedback block (failing gates first, bounded),
  and the existing crew timeout. The pilot measures it.
- **The harness now runs gates; evidence attribution must follow.** The
  `Harness Gatekeeper` agent is added to the evidence allowlist and to
  `_evidence_agents`; a missing record is red, never prose.
- **Auditor and implementer sharing a model** would let the author approve its
  own work. The alias defaults to the verifier/reviewer/senior brain, and the
  auditor is read-only; the pilot checks `usage.by_role` for distinct models.
- **Rollback must be real.** The v1 branch is untouched and selected by
  `SWARM_FLOW_V2=0`; a test asserts both paths are selectable.
- **Caps are unchanged.** A v2 run is compared on the 060 profile; an
  evidence-tuned cap set is a follow-up decision.
