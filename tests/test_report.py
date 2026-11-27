"""The report exposes manual completions and can gate a release on them (059)."""

from __future__ import annotations

from swarm import report
from swarm.done import DoneEntry


def test_report_prints_the_manual_share(monkeypatch, capsys):
    monkeypatch.setattr(report, "collect", list)
    monkeypatch.setattr(
        "swarm.done.done_entries",
        lambda: {
            "001-example-app/T1": DoneEntry(task_hash="a", manual=True, manual_reason="by hand"),
            "001-example-app/T2": DoneEntry(task_hash="b"),
        },
    )
    assert report.main([]) == 0
    out = capsys.readouterr().out
    assert "manual completions: 1/2" in out
    assert "001-example-app/T1" in out
    assert "by hand" in out


def test_fail_on_manual_is_a_release_gate(monkeypatch):
    monkeypatch.setattr(report, "collect", list)
    monkeypatch.setattr(
        "swarm.done.done_entries",
        lambda: {"001-example-app/T1": DoneEntry(task_hash="a", manual=True)},
    )
    assert report.main(["--fail-on-manual"]) == 1


def test_fail_on_manual_passes_when_none_are_manual(monkeypatch):
    monkeypatch.setattr(report, "collect", list)
    monkeypatch.setattr(
        "swarm.done.done_entries",
        lambda: {"001-example-app/T1": DoneEntry(task_hash="a")},
    )
    assert report.main(["--fail-on-manual"]) == 0
