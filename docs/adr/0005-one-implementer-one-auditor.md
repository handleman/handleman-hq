# One implementer and one auditor; the harness owns the gates

The swarm runs one implementer that owns a whole task and plans inside its tool
loop, then the harness itself runs every gate deterministically. A single
read-only auditor judges the recorded gate evidence, the delta and the scenario
against the brief and its acceptance criteria; it merges the old reviewer and
verifier. A red round re-runs the same implementer prompt on an escalation model
tier instead of switching to a senior persona. The per-task planner, the QA
model, the reviewer/verifier split and the senior persona are gone from the v2
path. The v1 flow remains selectable (`SWARM_FLOW_V2=0`) for one release because
rollback must be real; deleting it is a later cleanup. Green still means
evidence: harness executions are recorded under `Harness Gatekeeper`, and
`save_run` re-checks them at the final delta.

**Why:** 242 runs showed a median of one plan step but a paid planner call on
every task, 24% delta-guard stops before any judge, and the coder + senior
families at $12.44 of $14.15. QA's indispensable work was executing gates and
recording evidence, which the harness can do without a model; the verifier's
scenario check is real, but as a separate role it paid a second full context and
handed corrections back to another persona. One whole-task implementer sees the
brief the coder never saw; one auditor keeps judgement independent of the author.

**Considered:** keep the planner but feed it the whole brief (rejected: a median
of one step means the boundary is not doing work); keep QA as a gate runner
(rejected: deterministic execution is cheaper and its evidence is stronger);
keep the verifier separate (rejected: two contexts for one round); a fixed
senior-only implementer (rejected: the corpus shows cheap models do most rounds,
so tier on failure); delete v1 immediately (rejected: the pilot needs an A/B and
a rollback).
