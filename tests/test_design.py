"""057: Figma design lane — config, cache, IR, REST, OAuth storage, checks."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from swarm.design import checks, ir, oauth
from swarm.design.cache import check_cache, write_cache
from swarm.design.config import DesignConfig, DesignConfigError, load_design
from swarm.design.mcp import (
    READ_TOOLS,
    WRITE_TOOLS,
    Budget,
    DesignError,
    payload_from_result,
    tool_args,
)
from swarm.design.rest import RestClient, RestError


def _config(**overrides) -> DesignConfig:
    base = {"file_key": "abc", "nodes": ("1:2",), "token_env": "TEST_FIGMA_TOKEN"}
    base.update(overrides)
    return DesignConfig(**base)  # type: ignore[arg-type]


def _png(color: str) -> bytes:
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color).save(buffer, format="PNG")
    return buffer.getvalue()


# --- config -----------------------------------------------------------------


def test_design_config_validates_and_dedupes_nodes():
    config = DesignConfig.from_mapping(
        {"file_key": "abc", "nodes": ["1:2", "1:2", "3:4"], "transport": "rest"}
    )
    assert config is not None
    assert config.nodes == ("1:2", "3:4")
    assert config.transport == "rest"


@pytest.mark.parametrize(
    "raw",
    [
        {"nodes": ["1:2"]},
        {"file_key": "abc"},
        {"file_key": "abc", "nodes": ["nope"]},
        {"file_key": "abc", "nodes": ["1:2"], "transport": "smtp"},
        {"file_key": "abc", "nodes": ["1:2"], "provider": "penpot"},
    ],
)
def test_design_config_rejects_bad_blocks(raw):
    with pytest.raises(DesignConfigError):
        DesignConfig.from_mapping(raw)


def test_design_spec_merges_its_node(tmp_path):
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "design.toml").write_text('[figma]\nfile_key = "abc"\nnode = "3:4"\n')
    config = load_design(tmp_path, spec, mapping={"file_key": "abc", "nodes": ["1:2"]})
    assert config is not None
    assert config.nodes == ("1:2", "3:4")


def test_design_spec_cannot_change_the_file_key(tmp_path):
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "design.toml").write_text('[figma]\nfile_key = "other"\nnode = "3:4"\n')
    with pytest.raises(DesignConfigError):
        load_design(tmp_path, spec, mapping={"file_key": "abc", "nodes": ["1:2"]})


# --- cache ------------------------------------------------------------------


def test_cache_round_trips_and_reports_a_tampered_file(tmp_path):
    config = _config()
    write_cache(tmp_path, config, {"1-2.json": "{}", "design-brief.md": "# x"}, file_version="v1")
    assert check_cache(tmp_path, config)["ok"]
    (config.cache_dir(tmp_path) / "1-2.json").write_text("{ }")
    result = check_cache(tmp_path, config)
    assert not result["ok"] and result["code"] == "design_stale"


def test_cache_missing_node(tmp_path):
    config = _config()
    write_cache(tmp_path, config, {"design-brief.md": "# x"}, file_version="v1")
    result = check_cache(tmp_path, config, spec_nodes=("9:9",))
    assert result["code"] == "design_node_missing"


# --- IR ---------------------------------------------------------------------


def test_normalize_nodes_and_tokens():
    data = {
        "name": "Demo",
        "version": "42",
        "nodes": {
            "1:2": {
                "document": {
                    "id": "1:2",
                    "name": "Plan",
                    "type": "FRAME",
                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 390, "height": 844},
                    "layoutMode": "VERTICAL",
                    "itemSpacing": 12,
                    "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}],
                    "children": [{"id": "1:3", "name": "Title", "type": "TEXT", "characters": "Hello"}],
                }
            }
        },
    }
    normalized = ir.normalize_file_nodes(data, "abc")
    node = normalized["nodes"]["1:2"]
    assert node["bounds"] == {"x": 0.0, "y": 0.0, "w": 390.0, "h": 844.0}
    assert node["fills"][0]["color"] == "#ffffff"
    assert ir.walk_text(node) == ["Hello"]
    variables = {
        "meta": {
            "variables": {
                "v1": {"name": "color/primary", "valuesByMode": {"m": {"r": 0.1, "g": 0.2, "b": 0.3}}}
            }
        }
    }
    assert ir.tokens_from_variables(variables) == {"color/primary": "#1a334c"}


def test_metadata_xml_is_tolerant():
    parsed = ir.parse_metadata_xml('<frame id="1:2" name="Plan" x="0" y="0" width="10" height="20" />')
    assert parsed[0]["id"] == "1:2"
    assert parsed[0]["bounds"]["w"] == 10.0
    assert ir.parse_metadata_xml("not xml")[0]["raw"].startswith("not")


# --- REST -------------------------------------------------------------------


def _rest_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/nodes"):
        return httpx.Response(
            200,
            json={
                "name": "Demo",
                "version": "7",
                "nodes": {
                    "1:2": {
                        "document": {
                            "id": "1:2",
                            "name": "Plan",
                            "type": "FRAME",
                            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 10, "height": 20},
                        }
                    }
                },
            },
        )
    if path.endswith("/variables/local"):
        return httpx.Response(200, json={"meta": {"variables": {}}})
    if path.endswith("/styles"):
        return httpx.Response(200, json={"meta": {"styles": []}})
    if path.endswith("/components"):
        return httpx.Response(200, json={"meta": {"components": {}}})
    if path.endswith("/images/abc"):
        return httpx.Response(200, json={"images": {"1:2": "https://img.test/1-2.png"}})
    if request.url.host == "img.test":
        return httpx.Response(200, content=_png("#ffffff"))
    return httpx.Response(404)


def test_rest_fetch_writes_the_same_cache(tmp_path):
    config = _config()
    client = httpx.Client(transport=httpx.MockTransport(_rest_handler))
    artifacts, version, _tokens, _components = RestClient(config, token="t", client=client).fetch()
    assert version == "7"
    index = json.loads(artifacts["index.json"])
    assert index["transport"] == "rest"
    assert "1-2.png" in artifacts
    assert "design-brief.md" in artifacts
    write_cache(tmp_path, config, artifacts, file_version=version, transport="rest")
    assert check_cache(tmp_path, config)["ok"]


def test_rest_requires_a_token():
    with pytest.raises(RestError, match="figma_token_missing"):
        RestClient(_config(), token="")


# --- OAuth storage ----------------------------------------------------------


def test_token_storage_round_trip_and_mode(tmp_path):
    from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

    storage = oauth.FileTokenStorage(tmp_path / "oauth.json")
    token = OAuthToken(access_token="secret", expires_in=3600, scope="mcp:connect")
    client = OAuthClientInformationFull(client_id="cid", client_secret="csecret", redirect_uris=["http://127.0.0.1:8765/callback"])  # type: ignore[list-item]

    import asyncio

    asyncio.run(storage.set_tokens(token))
    asyncio.run(storage.set_client_info(client))
    assert asyncio.run(storage.get_tokens()).access_token == "secret"  # type: ignore[union-attr]
    assert asyncio.run(storage.get_client_info()).client_id == "cid"  # type: ignore[union-attr]
    status = storage.status()
    assert status["authenticated"] and not status["expired"]
    assert oct((tmp_path / "oauth.json").stat().st_mode & 0o777) == "0o600"
    assert storage.delete()


# --- MCP helpers ------------------------------------------------------------


def test_tool_args_map_to_the_schema():
    schema = {
        "properties": {
            "url": {"type": "string"},
            "clientFrameworks": {"type": "string"},
            "clientLanguages": {"type": "string"},
        }
    }
    args = tool_args(schema, _config(), "1:2")
    assert args["url"].endswith("node-id=1-2")
    assert args["clientFrameworks"] == "Svelte"


def test_tool_args_refuses_an_unaddressable_tool():
    with pytest.raises(DesignError, match="figma_tool_schema"):
        tool_args({"properties": {"mystery": {}}}, _config(), "1:2")


def test_payload_saves_images_to_files(tmp_path):
    from mcp.types import ImageContent, TextContent

    class Result:
        content = (TextContent(type="text", text="hello"), ImageContent(type="image", data="aGVsbG8=", mimeType="image/png"))
        structuredContent = None
        isError = False

    payload = payload_from_result(Result(), out_dir=tmp_path, stem="shot")
    assert payload["text"] == "hello"
    assert Path(payload["images"][0]).read_bytes() == b"hello"


def test_write_tools_are_not_read_tools():
    assert not set(WRITE_TOOLS) & set(READ_TOOLS)
    assert "use_figma" in WRITE_TOOLS


def test_budget_blocks_after_the_limit():
    budget = Budget(calls=1)
    budget.take()
    with pytest.raises(DesignError, match="figma_tool_budget"):
        budget.take()


# --- design checks ----------------------------------------------------------


def test_design_checks_tokens_regions_and_screenshot(tmp_path):
    baseline = tmp_path / "base.png"
    same = tmp_path / "same.png"
    other = tmp_path / "other.png"
    baseline.write_bytes(_png("#ffffff"))
    same.write_bytes(_png("#ffffff"))
    other.write_bytes(_png("#000000"))
    table = {
        "token": [{"name": "--color-bg", "value": "#ffffff", "ac": "AC-1"}],
        "region": [{"id": "card", "x": 10, "y": 20, "w": 100, "h": 50, "tolerance_px": 2, "ac": "AC-2"}],
        "screenshot": {"frame": "desktop", "baseline": "base.png", "threshold": 0.01, "ac": "AC-3"},
    }
    facts = {
        "tokens": {"--color-bg": "#ffffff"},
        "regions": {"card": {"x": 11, "y": 20, "w": 100, "h": 50}},
        "screenshots": {"desktop": str(same)},
    }
    assert checks.evaluate(table, facts, root=tmp_path) == []
    facts["tokens"]["--color-bg"] = "#000000"
    facts["regions"]["card"]["x"] = 40
    facts["screenshots"]["desktop"] = str(other)
    issues = checks.evaluate(table, facts, root=tmp_path)
    assert {issue["check"] for issue in issues} == {"design_token", "design_region", "design_screenshot"}


def test_browser_plan_includes_design_entries(tmp_path):
    from swarm.drivers.acceptance import browser_plan

    spec = tmp_path / "001-x"
    spec.mkdir()
    (spec / "spec.md").write_text("# X\n")
    (spec / "design.toml").write_text(
        '[figma]\nfile_key = "abc"\nnode = "1:2"\n\n'
        '[[token]]\nname = "--color-bg"\nvalue = "#ffffff"\n\n'
        '[[region]]\nid = "card"\nselector = ".card"\n'
    )
    plan = browser_plan([spec], base_url="http://x/", out_dir=tmp_path / "out")
    assert plan["design"][0]["spec"] == "001-x"
    assert plan["design"][0]["tokens"] == ["--color-bg"]
    assert plan["design"][0]["regions"][0]["selector"] == ".card"


def test_design_issues_fail_the_report():
    from swarm.drivers.acceptance import SpecReport

    report = SpecReport(spec="x", title="x", criteria=[], checks=[])
    report.ac_verdicts["AC-1"] = {"verdict": "pass"}
    assert report.verdict == "PASS"
    report.design_issues = [
        {"check": "design_token", "target": "--x", "detail": "wrong", "ac": "AC-D"}
    ]
    assert report.verdict == "FAIL"


def test_the_design_cache_is_out_of_coder_scope():
    from swarm.tools_guarded import in_scope

    assert not in_scope("designs/abc/1-2.json", ("designs/",))
    assert in_scope("frontend/src/App.svelte", ("frontend/",))


def test_auto_uses_rest_when_the_api_token_is_present(monkeypatch, tmp_path):
    from swarm.design.sync import choose_transport

    monkeypatch.setenv("TEST_FIGMA_TOKEN", "figd_test")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "state"))
    assert choose_transport(_config()) == "rest"


def test_auto_uses_mcp_without_the_api_token(monkeypatch, tmp_path):
    from swarm.design.sync import choose_transport

    monkeypatch.delenv("TEST_FIGMA_TOKEN", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "state"))
    assert choose_transport(_config()) == "mcp"
