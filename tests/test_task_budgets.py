"""Task budget profiles (060): e2e/visual get 2x, coding 1x."""

from __future__ import annotations

from swarm.budget import profile_multiplier, scaled_caps, task_profile


def test_profiles_from_briefs_and_spec_names() -> None:
    assert task_profile("Add frontend/e2e/build-route.spec.ts") == "e2e"
    assert task_profile("Update Playwright coverage") == "e2e"
    assert task_profile("Capture a screenshot and compare it") == "visual"
    assert task_profile("Implement the map interaction") == "coding"
    assert task_profile("Implement the route", "040-google-maps-layout") == "visual"
    assert task_profile("Write the e2e spec for the design", "041-figma-redesign") == "e2e"


def test_multiplier_defaults_and_floor(monkeypatch) -> None:
    monkeypatch.delenv("SWARM_E2E_CAP_MULTIPLIER", raising=False)
    monkeypatch.delenv("SWARM_VISUAL_CAP_MULTIPLIER", raising=False)
    assert profile_multiplier("coding") == 1.0
    assert profile_multiplier("e2e") == 2.0
    assert profile_multiplier("visual") == 2.0
    monkeypatch.setenv("SWARM_E2E_CAP_MULTIPLIER", "0.5")
    assert profile_multiplier("e2e") == 1.0
    monkeypatch.setenv("SWARM_E2E_CAP_MULTIPLIER", "2.5")
    assert profile_multiplier("e2e") == 2.5


def test_all_six_caps_scale_together() -> None:
    caps = scaled_caps(
        tokens=4_000_000,
        cost=3.0,
        seconds=14_400,
        cost_task=3.0,
        seconds_task=3_600,
        wall=1_800,
        multiplier=2.0,
    )
    assert caps == {
        "tokens": 8_000_000,
        "cost": 6.0,
        "seconds": 28_800,
        "cost_task": 6.0,
        "seconds_task": 7_200,
        "wall": 3_600,
    }


def test_coding_multiplier_leaves_caps_alone() -> None:
    caps = scaled_caps(
        tokens=4_000_000,
        cost=3.0,
        seconds=14_400,
        cost_task=3.0,
        seconds_task=3_600,
        wall=1_800,
        multiplier=1.0,
    )
    assert caps["tokens"] == 4_000_000
    assert caps["cost_task"] == 3.0
