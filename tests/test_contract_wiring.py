"""048 T9: the five tables read the contract; env still overrides it."""

from __future__ import annotations

import pytest

from swarm import contract


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(contract, "REPO_ROOT", tmp_path)
    contract._cached.cache_clear()
    monkeypatch.delenv("SWARM_SCOPE", raising=False)
    monkeypatch.delenv("SWARM_GATE_MAP", raising=False)
    monkeypatch.delenv("SWARM_GATE_COMMANDS", raising=False)
    yield
    contract._cached.cache_clear()


def _yaml(tmp_path, text):
    (tmp_path / "swarm.yaml").write_text(text)


def test_scope_comes_from_the_contract(tmp_path):
    from swarm.tools_guarded import resolve_scope

    assert resolve_scope() == contract.DEFAULT_SCOPE
    _yaml(tmp_path, "scope: [src/, tests/]\n")
    assert resolve_scope() == ("src/", "tests/")


def test_the_env_scope_still_wins(tmp_path, monkeypatch):
    from swarm.tools_guarded import resolve_scope

    _yaml(tmp_path, "scope: [src/]\n")
    monkeypatch.setenv("SWARM_SCOPE", "app/,frontend/")
    assert resolve_scope() == ("app/", "frontend/")


def test_the_affected_gate_map_comes_from_the_contract(tmp_path):
    from swarm.gates import gate_map

    _yaml(
        tmp_path,
        "gate_map:\n"
        "  'src/**': [pytest -q, ruff check .]\n",
    )
    assert gate_map() == [("src/**", ["pytest -q", "ruff check ."])]


def test_the_env_gate_map_still_wins(tmp_path, monkeypatch):
    from swarm.gates import gate_map

    _yaml(tmp_path, "gate_map:\n  'src/**': [pytest -q]\n")
    monkeypatch.setenv("SWARM_GATE_MAP", "app/**=pytest -q;ruff check .")
    assert gate_map() == [("app/**", ["pytest -q", "ruff check ."])]


def test_gate_commands_come_from_the_contract(tmp_path):
    from swarm.flow import gate_commands

    _yaml(tmp_path, "gates: [pytest -q, ruff check .]\n")
    assert gate_commands({}) == ["pytest -q", "ruff check ."]


def test_risk_classes_come_from_the_contract(tmp_path):
    from swarm import risk

    _yaml(
        tmp_path,
        "risk:\n  classes:\n    2: ['src/']\n    3: ['infra/']\n",
    )
    assert risk.classify(["src/app.py"]) == 2
    assert risk.classify(["infra/x.tf"]) == 3
    # Unmapped paths are still control (never flattered as docs)
    assert risk.classify(["whatever.py"]) == 3


def test_harness_specs_come_from_the_contract(tmp_path):
    from swarm.flow import HARNESS_SPECS

    assert HARNESS_SPECS == contract.DEFAULT_HARNESS_SPECS
    _yaml(tmp_path, "harness_specs: [001-x]\n")
    assert contract.current().harness_specs == ("001-x",)


def test_an_installed_package_defaults_to_the_cwd(monkeypatch):
    """site-packages has no pyproject; the caller's cwd is the only sane root."""
    from swarm import paths

    monkeypatch.chdir("/tmp")
    monkeypatch.setattr(paths, "__file__", "/tmp/hq/lib/python3.12/site-packages/swarm/paths.py")
    assert paths._default_root() == __import__("pathlib").Path("/tmp").resolve()