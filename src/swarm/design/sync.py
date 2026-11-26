"""Design sync/check (057): MCP with first-run OAuth, or REST parity."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from swarm.design import ir, oauth
from swarm.design.cache import check_cache, read_brief, write_cache
from swarm.design.config import DesignConfig, DesignConfigError, load_design
from swarm.design.mcp import Budget, DesignError, McpClient
from swarm.design.rest import RestClient

logger = logging.getLogger(__name__)

UrlCallback = Callable[[str], None]


def _load_env(root: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(root) / ".env")
    except ImportError:  # dotenv is optional in a minimal install
        pass


def resolve(
    root: Path, *, mapping: Mapping[str, Any] | None = None, spec_dir: Path | None = None
) -> DesignConfig | None:
    _load_env(root)
    return load_design(root, spec_dir, mapping=mapping)


def choose_transport(config: DesignConfig, requested: str = "") -> str:
    transport = (requested or config.transport or "auto").strip().lower()
    if transport in {"mcp", "rest"}:
        return transport
    if transport != "auto":
        raise DesignConfigError("transport must be auto, mcp or rest")
    if oauth.status(config)["authenticated"]:
        return "mcp"
    if config.rest_token():
        return "rest"
    return "mcp"


def _mcp_tokens(client: McpClient, node: str, budget: Budget, cache: Path) -> dict[str, Any]:
    try:
        payload = client.call("get_variable_defs", node, budget=budget, cache_dir=cache)
    except DesignError:
        return {}
    text = str(payload.get("text") or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return {"raw": text[:20000]}
    return data if isinstance(data, dict) else {"raw": data}


def _image_from_payload(payload: Mapping[str, Any], config: DesignConfig) -> bytes:
    images = payload.get("images") or []
    if images:
        try:
            return Path(str(images[0])).read_bytes()
        except OSError:
            return b""
    text = str(payload.get("text") or "").strip()
    if text.startswith("http"):
        import httpx

        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(text)
                if response.status_code == 200 and len(response.content) <= config.max_bytes:
                    return response.content
        except httpx.HTTPError:
            return b""
    return b""


def _sync_mcp(
    root: Path,
    config: DesignConfig,
    *,
    on_url: UrlCallback | None,
    non_interactive: bool,
) -> dict[str, Any]:
    client = McpClient(config, on_url=on_url, non_interactive=non_interactive)
    client.ensure_token()
    budget = Budget(calls=max(8, len(config.nodes) * 4))
    artifacts: dict[str, bytes | str] = {}
    nodes_ir: dict[str, Any] = {}
    tokens: dict[str, Any] = {}
    metadata_blob: list[str] = []
    with tempfile.TemporaryDirectory() as tool_cache:
        cache = Path(tool_cache)
        for node in config.nodes:
            meta = client.call("get_metadata", node, budget=budget, cache_dir=cache)
            text = str(meta.get("text") or "")
            metadata_blob.append(text)
            parsed = ir.parse_metadata_xml(text)
            entry = parsed[0] if parsed else {"id": node}
            entry.setdefault("id", node)
            nodes_ir[node] = entry
            prefix = node.replace(":", "-")
            artifacts[f"{prefix}.json"] = json.dumps(entry, indent=2, sort_keys=True)
            tokens.update(_mcp_tokens(client, node, budget, cache))
            try:
                shot = client.call("get_screenshot", node, budget=budget, cache_dir=cache)
                image = _image_from_payload(shot, config)
                if image:
                    artifacts[f"{prefix}.png"] = image
            except DesignError as exc:
                logger.debug("figma: screenshot unavailable for %s: %s", node, exc)
            try:
                context = client.call("get_design_context", node, budget=budget, cache_dir=cache)
                artifacts[f"design-context/{prefix}.txt"] = str(context.get("text") or "")[:200000]
            except DesignError as exc:
                logger.debug("figma: design context unavailable for %s: %s", node, exc)
        for cached_tool in cache.rglob("*.json"):
            artifacts[f"mcp/{cached_tool.name}"] = cached_tool.read_text()
    file_info = {
        "key": config.file_key,
        "name": config.file_key,
        "version": "mcp:" + hashlib.sha256("\n".join(metadata_blob).encode()).hexdigest()[:16],
    }
    index = {
        "transport": "mcp",
        "file": file_info,
        "nodes": list(nodes_ir),
        "tokens": tokens,
    }
    artifacts["index.json"] = json.dumps(index, indent=2, sort_keys=True)
    artifacts["tokens.json"] = json.dumps(tokens, indent=2, sort_keys=True)
    artifacts["design-brief.md"] = ir.brief(
        file_info=file_info,
        nodes=nodes_ir,
        tokens=tokens,
        transport="mcp",
    )
    target = write_cache(
        root,
        config,
        artifacts,
        file_version=file_info["version"],
        transport="mcp",
    )
    return {
        "ok": True,
        "transport": "mcp",
        "dir": str(target),
        "nodes": list(nodes_ir),
        "version": file_info["version"],
    }


def _sync_rest(root: Path, config: DesignConfig) -> dict[str, Any]:
    client = RestClient(config)
    artifacts, version, _tokens, components = client.fetch()
    target = write_cache(root, config, artifacts, file_version=version, transport="rest")
    return {
        "ok": True,
        "transport": "rest",
        "dir": str(target),
        "nodes": list(config.nodes),
        "version": version,
        "components": components,
    }


def sync(
    root: Path,
    config: DesignConfig,
    *,
    force: bool = False,
    transport: str = "",
    on_url: UrlCallback | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    _load_env(root)
    current = check_cache(root, config)
    if current["ok"] and not force:
        return {
            "ok": True,
            "transport": "cached",
            "dir": current["detail"],
            "nodes": list(config.nodes),
            "version": (current.get("lock") or {}).get("file_version", ""),
        }
    chosen = choose_transport(config, transport)
    if chosen == "rest":
        return _sync_rest(root, config)
    return _sync_mcp(root, config, on_url=on_url, non_interactive=non_interactive)


def check(
    root: Path, config: DesignConfig, *, spec_dir: Path | None = None
) -> dict[str, Any]:
    spec_nodes: tuple[str, ...] = ()
    if spec_dir is not None:
        data = load_design(root, spec_dir, mapping=None)
        if data is not None:
            spec_nodes = tuple(n for n in data.nodes if n not in config.nodes)
    return check_cache(root, config, spec_nodes=spec_nodes)


def ensure(
    root: Path,
    config: DesignConfig,
    *,
    spec_dir: Path | None = None,
    on_url: UrlCallback | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    """Check the cache; sync (and authenticate) when it is missing/stale."""
    if spec_dir is not None:
        from swarm.design.config import load_spec_design

        spec = load_spec_design(spec_dir) or {}
        node = str((spec.get("figma") or {}).get("node", "")).strip()
        if node and node not in config.nodes:
            config = config.with_nodes((node,))
    current = check(root, config, spec_dir=spec_dir)
    if current["ok"]:
        return {**current, "synced": False}
    if not config.auto_sync:
        return current
    result = sync(
        root,
        config,
        on_url=on_url,
        non_interactive=non_interactive,
    )
    return {**result, "synced": True}


def brief_for(root: Path, config: DesignConfig, *, limit: int = 8000) -> str:
    return read_brief(config.cache_dir(root), limit=limit)


def status(config: DesignConfig) -> dict[str, Any]:
    st = oauth.status(config)
    st.update({"transport": config.transport, "file_key": config.file_key, "nodes": list(config.nodes)})
    return st


def brief_for_spec(root: Path, spec_dir: str | Path) -> str:
    """The prompt block for a spec's design, if it declares one."""
    from swarm import contract as contract_mod

    contract = contract_mod.current(root)
    if not contract.design:
        return ""
    try:
        config = load_design(root, Path(spec_dir), mapping=contract.design)
    except DesignConfigError:
        return ""
    if config is None:
        return ""
    text = read_brief(config.cache_dir(root), limit=6000)
    if not text:
        return (
            "## Design reference (Figma)\n\n"
            "The design cache is missing; run `hq design sync` before implementing.\n"
        )
    return "## Design reference (Figma)\n\n" + text