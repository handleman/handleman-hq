# 060 Task Budgets — Tasks

- [x] T1 (AC-1): Add `evidence.md` with the sampled profile table, notable
  runs and the 2× headroom calculation.
- [x] T2 (AC-2): Add `swarm/budget.py` (`task_profile`, `profile_multiplier`)
  and unit tests for e2e/visual/coding and the env override/floor.
- [x] T3 (AC-3): Scale the six caps and the wall budget in
  `SwarmFlow.__init__` from the task profile; never scale the local zero-token
  mode.
- [x] T4 (AC-4): Record `profile`/`cap_multiplier` in `run.json.budget`; document
  the evidence and env knobs; set the app's multipliers.
- [x] T5 (AC-5): Add the scaling unit test; factory suite, ruff and
  `factory-audit` green; bump the release.
