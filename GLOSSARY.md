# handleman-hq — Factory Language

The vocabulary of the **factory**: the harness that turns a target repo's specs
into merged, evidence-backed work. The target app's product vocabulary lives in
the app's own glossary; this file defines the harness concepts only.

## The factory and its target

**Factory**:
The published harness that builds a target from its specs.
_Avoid_: swarm, harness (when the repo is meant)

**Target**:
The repo the factory operates on, described by its target contract.
_Avoid_: app (only one kind of target), project

**Package**:
The released distribution of the factory; `hq` is its installed entry point.
_Avoid_: repo, source tree

**Swarm**:
The running set of agent roles that executes the queue.
_Avoid_: factory, team

**Dark factory**:
The autonomous loop that goes from a queued task to a merge without a human in
the middle.
_Avoid_: pipeline, automation

**Spec kind**:
Whether a spec builds the target (`product`, queued) or improves the factory
(`harness`, never queued).
_Avoid_: type, category

## Work intake

**Spec**:
One planned unit of work: `spec.md` (what/why + acceptance criteria), `plan.md`
(approach), `tasks.md` (the queue).
_Avoid_: story, epic

**Acceptance criterion (AC)**:
A single verifiable requirement of a spec, referenced by tasks (`AC-1`, …).
_Avoid_: requirement, goal

**Task**:
One unchecked queue line: an id, the ACs it serves, and a brief.
_Avoid_: job, unit, ticket

**Fix task**:
A task appended for a failing acceptance AC; it has the same shape as a planned
task but exists to repair one criterion.
_Avoid_: bug, retry

**Queue**:
The ordered list of open tasks the swarm may execute.
_Avoid_: backlog, list

**Plan** (a task's):
The approach the coder follows; it may be authored, cached from an earlier run,
or derived from the brief.
_Avoid_: steps, checklist

**Built product spec**:
A product spec that is complete enough for the acceptance pass: a spec, a plan,
tasks, and at least one implemented task.
_Avoid_: delivered spec

## Contract and boundaries

**Target contract**:
The single declaration of where a target's specs, scope, gates, browser suite,
drivers, design lane, risk profile and run traces live.
_Avoid_: config, settings

**Target root**:
The directory `hq` is invoked in; relative contract paths resolve from it.
_Avoid_: workspace, project root

**Scope**:
The paths a coder may write for a task.
_Avoid_: permissions, write set

**Gate**:
A verification command whose exit code is evidence. Gates include non-test
checks such as lint and type-check.
_Avoid_: check, test (a test is one kind of gate)

**Gate map**:
A rule that selects the gates a delta can break; an unmapped path selects all of
them.
_Avoid_: pipeline, matrix

**Delta**:
The files a run changed, attributed to that run only.
_Avoid_: diff, changeset

**Final delta**:
The delta at the moment the run is saved; evidence must be taken at this delta.
_Avoid_: last diff

**Out-of-scope revert**:
Changed files outside the task scope are reverted before the run can be saved.
_Avoid_: rollback (that is a whole-run operation)

**Guarded Shell**:
The argv-only, allowlisted shell an agent gets; it is the only way an agent runs
commands. In v2 the harness uses it too, as the `Harness Gatekeeper`.
_Avoid_: terminal, bash

**Driver**:
A target-owned command that performs one harness phase (e2e, acceptance, smoke,
db) and reports its result as JSON.
_Avoid_: script, plugin

**Packaged driver**:
The factory's fallback implementation of a driver when the target declares none.
_Avoid_: default driver, builtin

**Driver source**:
Whether a phase ran the target's driver or the packaged one; recorded so a
missing driver cannot look green.
_Avoid_: mode

## Execution and roles

**Run**:
One execution of one task, from kickoff to a terminal status.
_Avoid_: pilot, session, job

**Pilot**:
The foreground queue process that performs runs until the queue is empty or a
stop condition is reached.
_Avoid_: run (a run is one task), session

**Supervisor**:
The process that restarts runs, parks exhausted tasks, and runs the acceptance
hook after green feature tasks.
_Avoid_: daemon, orchestrator

**Retry later**:
A task parked after exhausting its attempts; the queue moves on and the operator
or a later supervisor run can pick it up again.
_Avoid_: failed, blocked

**Exhausted**:
A task that reached the supervisor's attempt limit and was parked.
_Avoid_: dead, aborted

**Round cap**:
The supervisor's bound on how many rounds it will start before stopping.
_Avoid_: limit, budget

**Role**:
A model-backed agent with one job: implementer, auditor, visual, acceptance. The
v1 planner, coder, QA, reviewer, verifier and senior are legacy (rollback only).
_Avoid_: agent (one role), worker

**Implementer**:
The v2 role that owns a whole task: it reads the spec and real modules, plans
inside its own tool loop, and lands code and tests. It runs no gates.
_Avoid_: coder (v1's micro-step role), developer

**Auditor**:
The v2 read-only role that judges the harness-recorded gates, the delta and the
scenario against the brief and its ACs, then declares PASS or BLOCKED. It merges
the v1 reviewer and verifier.
_Avoid_: QA, reviewer, verifier (v1 terms)

**Escalation tier**:
The stronger model the same implementer prompt runs on after a rejected round.
It is a model choice, not a persona.
_Avoid_: senior (the v1 persona)

**Conflict resolver**:
The role that resolves a merge or stash conflict inside the task's scope. It
uses the implementer's model and no separate configured role.
_Avoid_: merger

**Round**:
One implementer pass plus the deterministic gates (and, when green, one audit).
A rejected round's evidence feeds the next round, which runs on the escalation
tier.
_Avoid_: fix round, retry

**Correction**:
(v1) A verifier-driven repair plan executed in steps, guarded so it cannot
regress a passing build. v2 folds this into the implementer round.
_Avoid_: fix round

**Acceptance hook**:
The per-feature acceptance pass the supervisor runs after a green feature task.
_Avoid_: final gate (that is the whole batch)

## Evidence and green

**Green**:
A task whose gates passed, the auditor passed, and whose delta was saved and
committed.
_Avoid_: done (done is the ledger state), complete

**Done**:
A green task with a valid done-ledger entry whose task and spec hashes still
match.
_Avoid_: green, checked

**Done ledger**:
The durable record that a task is done: commit trailers, with a cache fallback
for shallow history.
_Avoid_: history, task list

**Manual completion**:
A task recorded by an operator with a reason, not by a green run; it is marked
in the ledger and surfaced by the report.
_Avoid_: handoff, hack, exception

**Covered-by declaration**:
An acceptance criterion proven by a named e2e test instead of a selector probe.
_Avoid_: skipped AC, N/A (that is no browser surface)

**Task hash**:
A hash of a task's id, brief and AC refs; changing any of them makes a previous
done entry invalid.
_Avoid_: checksum

**Spec hash**:
A hash of a spec's `spec.md` and `plan.md`; editing either reopens its done
tasks, while ticking `tasks.md` does not.
_Avoid_: plan hash

**Evidence**:
The recorded gate exit codes and transcript produced at the final delta.
_Avoid_: proof, report

**Stale evidence**:
Gate evidence taken before the last change to the delta; it cannot make a task
green.
_Avoid_: old test run

**Typed stop**:
A run that ended for a named reason instead of an exception.
_Avoid_: failure, crash

**Reason code**:
The canonical name of a typed stop.
_Avoid_: error, message

**Judge**:
A model whose verdict gates green (v2: the auditor); a judge that cannot answer
fails closed.
_Avoid_: critic

**Off switch**:
The environment setting that disables one guard for diagnosis; it is not a
policy.
_Avoid_: feature flag

## Acceptance and design verification

**Acceptance pass**:
The final greenlight that drives every built product spec in a real browser and
scores each AC.
_Avoid_: e2e suite (that is per-task gate evidence)

**AC check**:
A deterministic browser probe for one AC.
_Avoid_: test case

**N/A declaration**:
A spec's explicit statement that an AC has no browser surface; it is a
declaration, not an unverified AC.
_Avoid_: skipped, ignored

**Unverified**:
An AC with neither a check nor an N/A declaration.
_Avoid_: failed

**Oracle self-test**:
A mutation pass that proves every AC check can fail; a check that still passes
after its target is removed fails the spec.
_Avoid_: mutation test

**Live-only AC**:
An AC that only the live lane can verify (real provider, database or public
deployment) and that declares a live check instead of a hermetic one.
_Avoid_: manual AC

**Hermetic pass**:
The strict acceptance run with fixtures and no database.
_Avoid_: offline pass

**Live lane**:
The opt-in acceptance run against real providers, the local database and the
public deployment.
_Avoid_: production run

**Layout contract**:
The declared regions, controls and viewport expectations a page must satisfy.
_Avoid_: layout test

**Design check**:
A deterministic comparison of computed tokens, region bounds or a screenshot
against the cached design.
_Avoid_: visual QA (that is the advisory screenshot review)

**Visual phase**:
The per-run screenshot/DOM record whose verdict is advisory and never flips
green.
_Avoid_: acceptance

## Ops and recovery

**Preflight**:
The checks that run before the first model call: models, keys, venvs, gates,
drivers, design cache.
_Avoid_: bootstrap, setup

**Health**:
The target's test plus browser suite run as a stand check.
_Avoid_: smoke (that is one driver)

**Factory audit**:
The pre-push hygiene check for caches, secrets, large blobs and missing files.
_Avoid_: lint

**Run record**:
The durable JSON account of one run: status, delta, evidence, usage, acceptance,
design.
_Avoid_: log

**Run directory**:
The artifacts of one run: record, events, prompts, gate output, screenshots.
_Avoid_: workspace

**Run report**:
The dashboard/ledger view over run records.
_Avoid_: analytics

**Crash checkpoint**:
The periodic plan/step record that lets a killed run resume.
_Avoid_: snapshot

**Worktree**:
An isolated checkout used for a parallel attempt.
_Avoid_: branch

**Parallel attempt**:
One of several worktrees racing the same task; the best delta wins.
_Avoid_: retry

**Stash**:
A preserved unrelated change that is archived before the queue starts.
_Avoid_: backup

**Sandbox**:
The optional container an agent runs inside.
_Avoid_: jail

## Providers and models

**Model profile**:
The provider/role mix a run uses, chosen entirely by the operator's environment.
_Avoid_: config, settings

**Task budget profile**:
The multiplier applied to a task's caps by its work type — coding, e2e or
visual/screenshot.
_Avoid_: model profile (that is the provider mix), quota

**Fallback**:
The model tried when a role's primary model is unavailable or fails; every role
may declare one.
_Avoid_: backup

**Provider registry**:
The one table of providers: prefix, key, base URL and capabilities.
_Avoid_: adapter list

**Provider prefix**:
The `provider/` part of a model id that routes it to a provider.
_Avoid_: namespace

**Strict prefixes**:
The rule that an unknown provider prefix is an error rather than a silent
OpenRouter fallback.
_Avoid_: validation

**Key-free probe**:
A reachability check that sends no key.
_Avoid_: ping

**Provider audit**:
The command that probes every registry entry and reports drift.
_Avoid_: health check

**Cost ledger**:
The per-model usage and cost account in a run record.
_Avoid_: invoice

## Design lane

**Design lane**:
The optional path that reads a Figma design into a cache and verifies the
implementation against it.
_Avoid_: Figma integration

**Design cache**:
The local, disposable snapshot of the frames, tokens, brief and reference
renders the run reads; `hq design sync` rebuilds it and the target gitignores
it.
_Avoid_: download, committed artifact

**Design IR**:
The normalized, source-agnostic tree of a frame (bounds, layout, fills, text,
children).
_Avoid_: design JSON

**Design brief**:
The model-readable summary of a cached design, injected into planner/coder
prompts.
_Avoid_: spec

**Design lock**:
The record of the design version, allowlisted nodes and artifact hashes that
makes staleness detectable.
_Avoid_: cache key

**Design node**:
A Figma frame or layer id; only allowlisted nodes may enter a prompt.
_Avoid_: frame (a frame is one kind of node)

**Design transport**:
The way a design is fetched: MCP or REST.
_Avoid_: provider

**Token-first**:
The `auto` rule: an API token present means REST; absent means MCP OAuth.
_Avoid_: fallback chain

**MCP OAuth**:
The first-run authorization of the remote Figma MCP server (discovery, dynamic
registration, PKCE, loopback redirect).
_Avoid_: login

**Awaiting auth**:
A run that needs Figma but has no usable token: it shows the authorization URL
and waits, or stops typed when non-interactive.
_Avoid_: blocked

**Read-only tools**:
The allowlisted MCP tools an agent may call; canvas/write tools are never
exposed.
_Avoid_: MCP tools
