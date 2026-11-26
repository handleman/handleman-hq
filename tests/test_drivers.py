"""056: target drivers are commands that speak JSON; absent = packaged fallback."""

from __future__ import annotations

import pytest

from swarm import contract
from swarm.drivers import dispatch


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(contract, "REPO_ROOT", tmp_path)
    contract._cached.cache_clear()
    yield
    contract._cached.cache_clear()


def _yaml(tmp_path, body: str):
    script = tmp_path / "driver.sh"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(0o755)
    (tmp_path / "swarm.yaml").write_text("drivers:\n  e2e: ./driver.sh\n")


def test_a_declared_driver_runs_with_json_params(tmp_path):
    _yaml(
        tmp_path,
        "python3 -c 'import json,os; p=json.loads(os.environ[\"SWARM_DRIVER_PARAMS\"]); "
        "print(json.dumps({\"exit\": 0, \"detail\": \"got \" + str(len(p.get(\"specs\", [])))}))'",
    )
    result = dispatch.run("e2e", {"specs": ["a", "b"]}, root=tmp_path)
    assert result.ok and result.source == "target"
    assert result.detail == "got 2"


def test_a_successful_driver_without_json_is_invalid(tmp_path):
    _yaml(tmp_path, "python3 -c 'print(\"not json\")'")
    with pytest.raises(dispatch.DriverError, match="no JSON"):
        dispatch.run("e2e", root=tmp_path)


def test_a_failing_driver_without_json_keeps_its_tail(tmp_path):
    _yaml(tmp_path, "python3 -c 'import sys; print(\"boom\"); sys.exit(2)'")
    result = dispatch.run("e2e", root=tmp_path)
    assert result.exit == 2 and "boom" in result.tail


def test_an_undeclared_kind_falls_back_to_packaged(monkeypatch, tmp_path):
    calls: list[dict] = []
    real = dispatch._packaged_e2e

    def fake(params, root):
        calls.append(params)
        return dispatch.DriverResult("e2e", "packaged", 0, tail="9 passed")

    monkeypatch.setattr(dispatch, "_packaged_e2e", fake)
    result = dispatch.run("e2e", {"specs": ["x"]}, root=tmp_path)
    assert result.source == "packaged" and calls == [{"specs": ["x"]}]
    monkeypatch.setattr(dispatch, "_packaged_e2e", real)


def test_an_undeclared_unknown_kind_is_a_typed_error(tmp_path):
    with pytest.raises(dispatch.DriverError, match="no .* driver"):
        dispatch.run("smoke", root=tmp_path)


def test_the_contract_parses_the_drivers_block(tmp_path):
    (tmp_path / "swarm.yaml").write_text(
        'drivers:\n  e2e: "make e2e"\n  db: "scripts/db.sh"\n'
    )
    c = contract.load(tmp_path)
    assert c.drivers == {"e2e": "make e2e", "db": "scripts/db.sh"}


def test_a_non_mapping_drivers_block_is_rejected(tmp_path):
    (tmp_path / "swarm.yaml").write_text("drivers: [a, b]\n")
    with pytest.raises(contract.ContractError, match="mapping"):
        contract.load(tmp_path)
