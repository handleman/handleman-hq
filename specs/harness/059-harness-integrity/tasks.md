# 059 Harness Integrity — Tasks

- [x] T1 (AC-1): Add manual metadata to the done ledger (`done.py`), the
  `Swarm-Manual` trailer and `--reason` to `record.py`, and the manual
  share/`--fail-on-manual` gate to `report.py`; tests for trailer, cache, legacy
  prefix and gate.
- [x] T2 (AC-2): Add `_discard_partial_task` and call it in `run_tasks` before a
  per-task-cap `retry_later`; unit-test the archive/revert call and the queue
  continuation.
- [x] T3 (AC-3): Move design evaluation before `write_report`/fix tasks in
  `drivers/acceptance.py`; add design issues to `failures`; normalise colours in
  `design/checks.py`; tests for a FAIL report with design facts and `#fff`.
- [x] T4 (AC-4): Add `[[covered_by]]` parsing/validation to the acceptance
  report, the `e2e` verdict and coverage; tests for valid and missing tests.
- [x] T5 (AC-5): Make the “did not land” retry name the response size and the
  write action; verify the message in the flow tests/logic.
- [x] T6 (AC-1..AC-5): Update `docs/commits.md`, `docs/run-guards.md`, the
  ROADMAP and the factory doc index; run the factory suite.
