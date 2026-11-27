# 059 Harness Integrity — Plan

1. **Manual audit.** Extend `DoneEntry` with `manual`/`manual_reason`; parse
   `Swarm-Manual` and the legacy `Swarm-Run: manual-` prefix; write the reason
   in `record.message` and the cache; add `--fail-on-manual` to the report.
2. **Budget isolation.** Add `_discard_partial_task(flow)` using the flow's
   `state.changed_files` and `_revert_paths` (which archives first); call it in
   `run_tasks` before `mark_retry_later` on a per-task cap.
3. **Report consistency.** Move the design evaluation block above
   `write_report` and the fix-task queue; add design issues to
   `SpecReport.failures`; normalise token values through a colour parser.
4. **Covered-by.** Parse `[[covered_by]]`, validate the test file against the
   repo root in `run`, set the AC verdict to `e2e`, include it in coverage, and
   show it in the report. Add tests for valid/missing declarations.
5. **Landing diagnosis.** In the step retry, include the response length and a
   “write the file” hint when the target is a new path and the delta lacks it.
6. **Docs/roadmap.** Record the new reason/trailer/gate in `docs/commits.md`,
   `docs/run-guards.md` and the ROADMAP; link the spec from the factory docs.

## Risks

- The manual flag must not reopen old green entries: legacy entries without a
  reason stay valid; only their presentation changes.
- The budget revert must archive before deleting (the flow already does) and
  must not touch a committed task.
- Colour parsing must not hide a real token mismatch: only compare values that
  both parse as colours; otherwise keep the string comparison.
- `covered_by` must not turn a missing e2e into a pass: the test path is checked
  and the AC is `e2e`, not `pass`.
