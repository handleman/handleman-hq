"""048 T8: one file declares what the harness knows about the target repo."""

from __future__ import annotations

import pytest

from swarm import contract


def test_the_factory_defaults_are_generic():
    """No `swarm.yaml` means the factory's own layout, never a neighbouring app."""
    c = contract.Contract()
    assert c.source == "defaults"
    assert c.specs_dir == "specs/harness"
    assert c.scope == ("src/", "tests/")
    assert c.e2e == ""
    assert c.db_script == ""
    assert c.python_venv == ".venv"


def test_the_app_contract_reproduces_the_old_tables(app_contract):
    """A target repo declares its shape; the app's file mirrors the old tables."""
    c = contract.current()
    assert c.source.endswith("swarm.yaml")
    assert c.specs_dir == "specs/product"
    assert "app/" in c.scope and "frontend/" in c.scope
    assert ("app/**", ("pytest -q", "ruff check .", "mypy app tests")) in c.gate_map
    assert c.e2e == "npm --prefix frontend run test:e2e"
    assert c.db_script == "swarm/db.sh"


def test_a_missing_file_is_the_defaults(tmp_path):
    c = contract.load(tmp_path)
    assert c.source == "defaults"
    assert c.scope == contract.DEFAULT_SCOPE


def test_yaml_overrides_every_field(tmp_path):
    (tmp_path / "swarm.yaml").write_text(
        "specs_dir: specs/harness\n"
        "scope: [src/, tests/]\n"
        "gates: [pytest -q, ruff check .]\n"
        "e2e: make e2e\n"
        "risk:\n  profile: generic\n"
        "db:\n  script: scripts/db.sh\n"
        "python:\n  venv: .venv\n"
        "harness_specs: [001-x]\n"
    )
    c = contract.load(tmp_path)
    assert c.source.endswith("swarm.yaml")
    assert c.specs_dir == "specs/harness"
    assert c.scope == ("src/", "tests/")
    assert c.gates == ("pytest -q", "ruff check .")
    assert c.e2e == "make e2e"
    assert c.risk_profile == "generic"
    assert c.db_script == "scripts/db.sh"
    assert c.harness_specs == ("001-x",)


def test_a_partial_file_keeps_the_other_defaults(tmp_path):
    (tmp_path / "swarm.yaml").write_text("scope: [src/]\n")
    c = contract.load(tmp_path)
    assert c.scope == ("src/",)
    assert c.specs_dir == contract.DEFAULT_SPECS_DIR
    assert c.harness_specs == contract.DEFAULT_HARNESS_SPECS


def test_unknown_keys_are_kept_not_fatal(tmp_path):
    (tmp_path / "swarm.yaml").write_text("future_key: 1\nscope: [src/]\n")
    c = contract.load(tmp_path)
    assert c.extra == {"future_key": 1}


def test_a_bare_string_scope_is_a_typo_not_a_scope(tmp_path):
    (tmp_path / "swarm.yaml").write_text("scope: app/\n")
    with pytest.raises(contract.ContractError, match="list of strings"):
        contract.load(tmp_path)


def test_broken_yaml_is_a_typed_error(tmp_path):
    (tmp_path / "swarm.yaml").write_text("scope: [unterminated\n")
    with pytest.raises(contract.ContractError, match="not valid YAML"):
        contract.load(tmp_path)


def test_a_non_mapping_file_is_rejected(tmp_path):
    (tmp_path / "swarm.yaml").write_text("- just\n- a list\n")
    with pytest.raises(contract.ContractError, match="mapping"):
        contract.load(tmp_path)


def test_paths_resolve_inside_the_target(tmp_path):
    c = contract.load(tmp_path)
    assert c.path("app", "main.py") == tmp_path / "app" / "main.py"


def test_the_cli_prints_the_resolved_contract(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(contract, "REPO_ROOT", tmp_path)
    (tmp_path / "swarm.yaml").write_text("specs_dir: specs/harness\n")
    assert contract.main() == 0
    out = capsys.readouterr().out
    assert "specs/harness" in out and "harness" in out
