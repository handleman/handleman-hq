# 060 Task Budgets — Plan

1. Add `swarm/budget.py` with `task_profile` and `profile_multiplier`.
2. In `SwarmFlow.__init__`, load the task brief/spec name (via
   `spec_loader`), classify, and scale `_max_tokens`, `_max_cost`,
   `_max_seconds`, `_max_cost_task`, `_max_seconds_task` and `_wall_budget`.
   Record `profile`/`cap_multiplier` in `run.json.budget`.
3. Default the e2e/visual multipliers to 2.0; read
   `SWARM_E2E_CAP_MULTIPLIER` / `SWARM_VISUAL_CAP_MULTIPLIER`; never below 1.0.
4. Document the evidence and knobs in `docs/setup.md` and
   `docs/run-guards.md`; add the env to the app's `.env`/`.env.example`.
5. Unit-test the classifier, the multiplier, and the six-cap scaling with a
   small fake flow; run the factory suite, ruff and audit.

## Risks

- A brief that mentions e2e while doing mostly coding gets the e2e profile; that
  is a cap increase only, so the cost is headroom, not behaviour.
- The scaling must happen before the first `bounded.run_bounded` call; the
  constructor is the only place.
- Local runs (`SWARM_MAX_TOKENS=0` for local) must not be scaled to a non-zero
  cap.
