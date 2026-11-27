# 059 Harness Integrity — Spec

Status: implemented (2026-11-28).

## What / Why

The comfort-walking-router 041/042 session exposed four places where the harness
told a green story the evidence did not support:

- operator-written feature code and e2e tests were recorded manually, passed
  acceptance, and looked swarm-built;
- a per-task budget stop continued the queue with the failed task's uncommitted
  delta still in the worktree, so the next task ran on a partial tree;
- the acceptance `.md` could say **PASS** while the CLI exited **FAIL** because
  design checks ran after the report was written, and `#fff` did not equal
  `#ffffff`;
- a spec could hide an interaction behind `not_applicable` with no named test.

This spec makes those failures visible and gives them a typed treatment.

## Scope

- Manual completion: record a reason, parse the existing `manual-` run prefix,
  report the manual share, and add a release gate.
- Per-task budget isolation: revert the capped task's delta before the queue
  continues.
- Acceptance consistency: evaluate design issues before writing the report;
  include them in fix tasks; normalise CSS colours semantically.
- `covered_by`: a declared e2e oracle is validated and reported as such, not
  hidden as N/A.
- Coder file-landing diagnosis: say when the model returned content but did not
  write the named new file.

## Non-goals

- Replacing `swarm.record` (manual completion remains legitimate for small
  operator work; it must be honest).
- Reworking the model profile or the design lane's token extraction (059 stays
  about integrity).
- Changing a target's specs or acceptance files.

## Acceptance Criteria

- [x] AC-1: **Manual completions are visible.** `swarm.record` writes
  `Swarm-Manual: <reason>`; the done ledger carries `manual`/`manual_reason`
  (and recognises legacy `Swarm-Run: manual-…`); `hq report` prints the manual
  share and `--fail-on-manual` exits non-zero. Unit tests cover the trailer,
  ledger, legacy prefix and report gate.
- [x] AC-2: **A task cap cannot leak a delta.** When a per-task budget stop
  continues the queue (015 AC-6), the task's uncommitted changed files are
  archived and reverted before the next task starts. The helper is unit-tested
  and the queue still continues.
- [x] AC-3: **The report and the verdict agree.** Design checks run before
  `write_report`; design issues are included in the report, the fix tasks and
  the verdict; CSS colour values compare semantically (`#fff` = `#ffffff`).
- [x] AC-4: **An e2e oracle is declared, not hidden.** `acceptance.toml` accepts
  `[[covered_by]] ac = "AC-1" test = "…"`; a missing test is a strict config
  error, a valid one reports the AC as `E2E` and covers it without pretending a
  selector ran.
- [x] AC-5: **A non-landing coder is diagnosable.** The step retry message names
  the missing target, the response size and the write action, instead of only
  “did not land”.

## Verification

`make test` (factory suite), `make lint`/`typecheck`, and the new unit tests for
done/record/report/acceptance/design/flow. The app's acceptance/design specs are
the consumer; this spec changes no target files.
