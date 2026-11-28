"""061 Swarm v2: one implementer, deterministic gates, one auditor."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from swarm import crew, flow
from swarm.evidence import gate_evidence
from swarm.spec_loader import SpecTask

# ---- selection ------------------------------------------------------------


def test_v2_is_the_default_and_can_be_switched_off():
    assert flow.flow_v2_enabled({}) is True
    assert flow.flow_version({}) == "v2"
    for value in ("0", "false", "no", "off", "OFF"):
        assert flow.flow_v2_enabled({"SWARM_FLOW_V2": value}) is False
        assert flow.flow_version({"SWARM_FLOW_V2": value}) == "v1"


def test_the_run_state_records_the_version():
    state = flow.SwarmState()
    assert state.flow_version == "v1"
    assert state.implementer == {} and state.auditor == {}


# ---- harness gate evidence ------------------------------------------------


def test_harness_gatekeeper_evidence_is_accepted_at_the_current_hash():
    executions = [
        {
            "agent": "Harness Gatekeeper",
            "argv": ["pytest", "-q"],
            "exit": 0,
            "changed_after": "hash-1",
            "tail": "3 passed",
        },
        {
            "agent": "QA Gatekeeper",
            "argv": ["ruff", "check", "."],
            "exit": 0,
            "changed_after": "hash-1",
            "tail": "ok",
        },
    ]
    gates, _, missing = gate_evidence(
        executions=executions,
        commands=["pytest -q", "ruff check ."],
        current_hash="hash-1",
        agents=("Harness Gatekeeper",),
    )
    assert gates == {"pytest -q": 0}
    assert missing == ["ruff check ."]
    # A stale record is missing, never green.
    gates, _, missing = gate_evidence(
        executions=executions,
        commands=["pytest -q"],
        current_hash="hash-2",
        agents=("Harness Gatekeeper",),
    )
    assert gates == {} and missing == ["pytest -q"]


# ---- the v2 loop ----------------------------------------------------------


class _Flow:
    """The parts of SwarmFlow the v2 loop touches, without a real run."""

    def __init__(self, gates, outputs, log):
        self._state = flow.SwarmState(spec_dir="001-example-app", task_id="T1")
        self._state.brief = "Add `app/x.py`."
        self._spec_dir = "001-example-app"
        self._baseline = {}
        self._evidence_agents = None
        self._step_paths = []
        self._allow_cache = None
        self.run_dir = "/tmp/v2-run"
        self._gate_sequence = list(gates)
        self._outputs = list(outputs)
        self.log = log
        self._sig = 0
        self.gate_selections = []

    @property
    def state(self):
        return self._state

    def _run_cost(self):
        return 0.0

    def _in_scope_paths(self, paths):
        return list(paths)

    def _revert_out_of_scope(self, paths):
        return []

    def _delta_signature(self):
        self._sig += 1
        return f"sig-{self._sig}"

    def _v2_gate_run(self, changed):
        gates = self._gate_sequence.pop(0)
        return (
            list(changed),
            dict(gates),
            "\n".join(f"$ {c}\nexit={v}\n" for c, v in gates.items()),
            [c for c, v in gates.items() if v != 0],
        )

    def _v2_e2e_round(self, changed):
        return ""

    def _v2_audit_context(self, task, changed, transcript):
        return "GATE EVIDENCE"

    def _qa_report(self, gates, transcript, changed, missing):
        return {
            "version": 2,
            "verdict": "blocked",
            "reason": "harness gate evidence",
            "changed_files": list(changed),
            "missing": list(missing),
            "gates": [
                {"command": c, "exit": v, "tail": "", "errors": []}
                for c, v in gates.items()
            ],
        }

    def _v2_reject_report(self, gates, transcript, changed, missing):
        from swarm.evidence import report_text

        return report_text(self._qa_report(gates, transcript, changed, missing))

    def _v2_delta_feedback(self, record):
        return flow.SwarmFlow._v2_delta_feedback(self, record)

    def _record_gate_selection(self, *args):
        self.gate_selections.append(args)

    def _record_best_delta(self, gates):
        pass

    def _kickoff(self, build, *, role="", step=None, guard_budget=True):
        self.log["roles"].append(role)
        built = build()
        self.log["crews"].append(built)
        return built, self._outputs.pop(0)


@pytest.fixture(autouse=True)
def _delta_guard_off(monkeypatch):
    monkeypatch.setenv("SWARM_DELTA_GUARD", "0")
    # The gate runner injects run_delta; the fake loop does not read the tree.
    monkeypatch.setattr("swarm.tools_guarded.run_delta", lambda baseline: ["app/x.py"])


def _task():
    return SpecTask(id="T1", ac_refs=("AC-1",), brief="Add `app/x.py`.")


def _run(fake, monkeypatch):
    # The real method binds to SwarmFlow; borrow it unbound on the fake object.
    monkeypatch.setattr(flow, "REPO_ROOT", SimpleNamespace())
    return flow.SwarmFlow._run_crew_v2(fake, _task())


def test_one_implementer_and_one_auditor_can_pass(monkeypatch):
    log = {"roles": [], "crews": []}
    fake = _Flow(
        gates=[{"pytest -q": 0}],
        outputs=["implemented", "VERDICT: PASS"],
        log=log,
    )
    _run(fake, monkeypatch)
    assert log["roles"] == ["implementer", "auditor"]
    assert fake.state.flow_version == "v2"
    assert fake.state.review_verdict == "pass"
    assert fake.state.implementer["rounds"] == 1
    assert fake.state.auditor["verdicts"] == ["pass"]
    assert fake.state.auditor["blocked"] is False
    # The implementer is the whole-task builder with no gate tool.
    implementer = log["crews"][0].agents[0]
    assert implementer.role == "Implementer"
    assert not any(getattr(tool, "allow_gates", False) for tool in implementer.tools)
    auditor = log["crews"][1].agents[0]
    assert auditor.role == "Auditor"
    assert not any(getattr(tool, "allow_gates", False) for tool in auditor.tools)


def test_a_red_round_escalates_the_model_tier_and_a_grounded_block_retries(monkeypatch):
    log = {"roles": [], "crews": []}
    fake = _Flow(
        gates=[{"pytest -q": 1}, {"pytest -q": 0}, {"pytest -q": 0}],
        outputs=[
            "first attempt",
            "second attempt",
            "FINDING: app/x.py:1 — the value is missing\nVERDICT: BLOCKED",
            "third attempt",
            "VERDICT: PASS",
        ],
        log=log,
    )
    _run(fake, monkeypatch)
    assert log["roles"] == [
        "implementer",
        "implementer:escalation",
        "auditor",
        "implementer:escalation",
        "auditor",
    ]
    assert fake.state.implementer["rounds"] == 3
    assert fake.state.implementer["escalations"] == 2
    assert fake.state.auditor["verdicts"] == ["blocked", "pass"]
    assert fake.state.review_verdict == "pass"
    # The first implementer is the cheap tier; every later one is escalation.
    assert log["crews"][0].agents[0].llm.model != log["crews"][1].agents[0].llm.model


def test_a_no_delta_round_escalates_instead_of_stopping(monkeypatch):
    """042-T2: the first v2 pilot claimed a landing with an empty delta."""
    log = {"roles": [], "crews": []}
    fake = _Flow(
        gates=[{"pytest -q": 0}],
        outputs=["I landed everything", "implemented", "VERDICT: PASS"],
        log=log,
    )
    calls = {"n": 0}

    def record(brief, changed, root):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"reason": "no_delta", "changed": [], "named": ["App.svelte"], "missing": []}
        return {"reason": "", "changed": ["app/x.py"], "named": [], "missing": []}

    monkeypatch.setenv("SWARM_DELTA_GUARD", "1")
    monkeypatch.setattr("swarm.guards.delta_record", record)
    _run(fake, monkeypatch)
    assert log["roles"] == ["implementer", "implementer:escalation", "auditor"]
    assert fake.state.implementer["no_delta_rounds"] == 1
    assert fake.state.review_verdict == "pass"


def test_an_ungrounded_block_stops_without_another_paid_round(monkeypatch):
    log = {"roles": [], "crews": []}
    fake = _Flow(
        gates=[{"pytest -q": 0}],
        outputs=["implemented", "The code looks wrong to me.\nVERDICT: BLOCKED"],
        log=log,
    )
    _run(fake, monkeypatch)
    assert log["roles"] == ["implementer", "auditor"]
    assert fake.state.ungrounded_block is True
    assert fake.state.review_verdict == "blocked"
    assert fake.state.implementer["rounds"] == 1


def test_v2_never_calls_the_planner_qa_or_verifier(monkeypatch):
    """The v2 path imports only the implementer and auditor builders."""
    def boom(*args, **kwargs):
        raise AssertionError("a v1 role was built in v2")

    monkeypatch.setattr(crew, "build_plan_crew", boom)
    monkeypatch.setattr(crew, "build_review_crew", boom)
    monkeypatch.setattr(crew, "build_verify_crew", boom)
    log = {"roles": [], "crews": []}
    fake = _Flow(
        gates=[{"pytest -q": 0}],
        outputs=["implemented", "VERDICT: PASS"],
        log=log,
    )
    _run(fake, monkeypatch)
    assert fake.state.review_verdict == "pass"


def test_a_failed_implementer_call_escalates_instead_of_crashing(monkeypatch):
    """A provider/tool-schema failure is a rejected round, not crew_error."""
    log = {"roles": [], "crews": []}

    class _FailFirst(_Flow):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.calls = 0

        def _kickoff(self, build, *, role="", step=None, guard_budget=True):
            self.calls += 1
            if self.calls == 1:
                raise SystemExit("provider rejected the tool schema")
            return super()._kickoff(
                build, role=role, step=step, guard_budget=guard_budget
            )

    fake = _FailFirst(
        gates=[{"pytest -q": 0}],
        outputs=["implemented", "VERDICT: PASS"],
        log=log,
    )
    _run(fake, monkeypatch)
    assert log["roles"] == ["implementer:escalation", "auditor"]
    assert fake.state.implementer["call_failures"] == 1
    assert fake.state.review_verdict == "pass"


def test_crew_contract_errors_are_non_retryable():
    """Gemini/Claude schema and unparseable CrewAI output must not be retried 3x."""
    assert flow._crew_contract_error(
        Exception(
            "tools[0].function.strict: google cannot guarantee OpenAI strict function schema semantics"
        )
    )
    assert flow._crew_contract_error(
        Exception("anthropic-messages cannot preserve named conversation participants")
    )
    assert flow._crew_contract_error(
        Exception("PydanticSerializationUnexpectedValue: output")
    )
    assert not flow._crew_contract_error(Exception("connection timed out"))
