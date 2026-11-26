"""042: the per-task visual phase is advisory, recorded, and never the gate."""

from __future__ import annotations

import types

from swarm import flow
from swarm.drivers import visual


def _stub(tmp_path):
    stub = types.SimpleNamespace(
        run_dir=tmp_path,
        state=types.SimpleNamespace(visual={}),
    )
    stub._visual_phase = types.MethodType(flow.SwarmFlow._visual_phase, stub)
    return stub


def test_off_switch_records_the_reason(tmp_path):
    import os

    stub = _stub(tmp_path)
    old = os.environ.get("SWARM_VISUAL_QA")
    os.environ["SWARM_VISUAL_QA"] = "0"
    try:
        out = stub._visual_phase()
    finally:
        if old is None:
            os.environ.pop("SWARM_VISUAL_QA", None)
        else:
            os.environ["SWARM_VISUAL_QA"] = old
    assert out["checked"] is False and "off" in out["reason"]


def test_no_base_url_skips_with_a_reason(tmp_path, monkeypatch):
    monkeypatch.delenv("SWARM_VISUAL_QA", raising=False)
    monkeypatch.delenv("SWARM_VISUAL_BASE_URL", raising=False)
    out = _stub(tmp_path)._visual_phase()
    assert out["checked"] is False and "BASE_URL" in out["reason"]


def test_a_broken_page_is_recorded_not_fatal(tmp_path, monkeypatch):
    monkeypatch.delenv("SWARM_VISUAL_QA", raising=False)
    monkeypatch.setenv("SWARM_VISUAL_BASE_URL", "http://localhost:5173")
    fact = visual.VisualFact(map_tile_count=0, start_form_count=0, end_form_count=0)
    monkeypatch.setattr(visual, "run_visual_check", lambda **kw: fact)
    monkeypatch.setattr(visual, "save_visual_report", lambda f, run_dir: run_dir / "visual_qa" / "v.json")
    out = _stub(tmp_path)._visual_phase()
    assert out["checked"] is True and out["ok"] is False
    assert out["tiles"] == 0


def test_a_running_stand_records_ok(tmp_path, monkeypatch):
    monkeypatch.delenv("SWARM_VISUAL_QA", raising=False)
    monkeypatch.setenv("SWARM_VISUAL_BASE_URL", "http://localhost:5173")
    fact = visual.VisualFact(map_tile_count=24, start_form_count=1, end_form_count=1,
                             top_card_button_count=2)
    monkeypatch.setattr(visual, "run_visual_check", lambda **kw: fact)
    monkeypatch.setattr(visual, "save_visual_report", lambda f, run_dir: run_dir / "visual_qa" / "v.json")
    out = _stub(tmp_path)._visual_phase()
    assert out["ok"] is True and out["tiles"] == 24


def test_a_failure_is_recorded_and_never_raised(tmp_path, monkeypatch):
    monkeypatch.delenv("SWARM_VISUAL_QA", raising=False)
    monkeypatch.setenv("SWARM_VISUAL_BASE_URL", "http://localhost:5173")

    def boom(**kw):
        raise RuntimeError("server down")

    monkeypatch.setattr(visual, "run_visual_check", boom)
    out = _stub(tmp_path)._visual_phase()
    assert out["checked"] is False and "server down" in out["error"]
