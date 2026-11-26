"""Figma MCP client (057 AC-13): read-only tools, allowlist, budget and cache.

The remote server is link-based. We expose only the tools that read a design;
the canvas/write tools are never listed to an agent. Each call opens a short
Streamable-HTTP session (the OAuth token is reused), validates the file/node
against the contract, writes images to files, and caches the JSON result so a
retry or the verifier does not call Figma again.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import ImageContent, TextContent

from swarm.design.config import DesignConfig
from swarm.design.oauth import (
    CallbackServer,
    FigmaAuthRequired,
    FileTokenStorage,
    _new_metadata,
    access_token,
    authorize,
)

logger = logging.getLogger(__name__)

READ_TOOLS = (
    "get_metadata",
    "get_design_context",
    "get_screenshot",
    "get_variable_defs",
    "get_code_connect_map",
    "search_design_system",
    "get_libraries",
    "download_assets",
)
WRITE_TOOLS = (
    "use_figma",
    "generate_figma_design",
    "create_new_file",
    "upload_assets",
    "generate_diagram",
    "html_to_figma",
    "generate_image",
    "generate_vector_illustration",
    "create_generative_plugin",
    "update_generative_plugin",
    "create_shader",
    "update_shader",
    "send_code_to_figma",
)


class DesignError(RuntimeError):
    """A typed design-lane failure (tool, budget, schema, response)."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass
class Budget:
    calls: int = 8
    used: int = 0

    def take(self) -> None:
        if self.used >= self.calls:
            raise DesignError("figma_tool_budget", f"{self.calls} calls per task")
        self.used += 1


def tool_args(schema: dict[str, Any], config: DesignConfig, node: str) -> dict[str, Any]:
    """Map our file/node to whatever the tool schema calls them."""
    props = schema.get("properties") if isinstance(schema, dict) else None
    props = props if isinstance(props, dict) else {}
    url = f"https://www.figma.com/design/{config.file_key}?node-id={node.replace(':', '-')}"
    args: dict[str, Any] = {}
    for name in ("url", "link", "figmaUrl", "figma_url", "selection"):
        if name in props:
            args[name] = url
            break
    for name in ("fileKey", "file_key", "key"):
        if name in props:
            args[name] = config.file_key
            break
    for name in ("nodeId", "node_id", "id"):
        if name in props:
            args[name] = node
            break
    if "clientFrameworks" in props:
        args["clientFrameworks"] = "Svelte"
    if "clientLanguages" in props:
        args["clientLanguages"] = "typescript"
    if not args:
        raise DesignError("figma_tool_schema", f"cannot address {node} with this tool")
    return args


def payload_from_result(
    result: Any, *, out_dir: Path, stem: str
) -> dict[str, Any]:
    """Turn a CallToolResult into text + image files (no base64 in prompts)."""
    texts: list[str] = []
    images: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, block in enumerate(getattr(result, "content", []) or []):
        if isinstance(block, TextContent):
            texts.append(block.text)
        elif isinstance(block, ImageContent):
            try:
                raw = base64.b64decode(block.data)
            except (ValueError, TypeError):
                continue
            path = out_dir / f"{stem}-{index}.png"
            path.write_bytes(raw)
            images.append(str(path))
    structured = getattr(result, "structuredContent", None)
    if structured is not None and not texts:
        texts.append(json.dumps(structured)[:200_000])
    return {
        "text": "\n".join(texts)[:400_000],
        "images": images,
        "structured": structured,
        "is_error": bool(getattr(result, "isError", False)),
    }


def cache_key(tool: str, node: str, args: dict[str, Any]) -> str:
    blob = json.dumps({"tool": tool, "node": node, "args": args}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


class McpClient:
    """A small synchronous facade over the async MCP client."""

    def __init__(
        self,
        config: DesignConfig,
        *,
        on_url: Callable[[str], None] | None = None,
        non_interactive: bool = False,
        timeout: float = 120.0,
    ):
        self.config = config
        self.on_url = on_url
        self.non_interactive = non_interactive
        self.timeout = timeout
        self.storage = FileTokenStorage(config.token_path())

    # -- auth -----------------------------------------------------------
    def ensure_token(self) -> None:
        st = self.storage.status()
        if st["authenticated"] and not st["expired"]:
            return
        authorize(
            self.config,
            open_browser=self.config.open_browser,
            on_url=self.on_url,
            non_interactive=self.non_interactive,
        )

    # -- tools ----------------------------------------------------------
    async def _run(self, fn: Callable[[ClientSession], Awaitable[Any]]) -> Any:
        if not access_token(self.config):
            raise FigmaAuthRequired()
        server = CallbackServer()
        redirect = await server.start()

        async def redirect_handler(url: str) -> None:
            raise FigmaAuthRequired(url)

        async def callback_handler() -> tuple[str, str | None]:
            raise FigmaAuthRequired()

        provider = OAuthClientProvider(
            server_url=self.config.mcp_url,
            client_metadata=_new_metadata(redirect),
            storage=self.storage,
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
            timeout=30.0,
        )
        try:
            async with (
                streamablehttp_client(self.config.mcp_url, auth=provider) as (read, write, _),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                return await fn(session)
        finally:
            await server.close()

    def list_tools(self) -> list[str]:
        self.ensure_token()

        async def call(session: ClientSession) -> list[str]:
            result = await session.list_tools()
            return [tool.name for tool in result.tools]

        names = asyncio.run(self._run(call))
        return [name for name in names if name in READ_TOOLS]

    def call(
        self,
        tool: str,
        node: str,
        *,
        extra: dict[str, Any] | None = None,
        cache_dir: Path | None = None,
        budget: Budget | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        if tool not in READ_TOOLS:
            raise DesignError("figma_tool_blocked", tool)
        if node not in self.config.nodes:
            raise DesignError("design_node_missing", node)
        self.ensure_token()
        budget = budget or Budget()
        budget.take()

        async def call_tool(session: ClientSession) -> dict[str, Any]:
            listed = await session.list_tools()
            current = next((t for t in listed.tools if t.name == tool), None)
            if current is None:
                raise DesignError("figma_tool_unavailable", tool)
            args = tool_args(current.inputSchema or {}, self.config, node)
            if extra:
                args.update({k: v for k, v in extra.items() if k in (current.inputSchema or {}).get("properties", {})})
            out_dir = (cache_dir or Path(self.config.dir) / self.config.file_key / "mcp")
            key = cache_key(tool, node, args)
            cached = out_dir / f"{key}.json"
            if cached.is_file() and not force:
                return json.loads(cached.read_text())
            result = await session.call_tool(tool, args)
            payload = payload_from_result(result, out_dir=out_dir, stem=f"{tool}-{node.replace(':', '-')}")
            payload["tool"] = tool
            payload["node"] = node
            payload["args"] = args
            cached.write_text(json.dumps(payload, indent=2, sort_keys=True))
            return payload

        return asyncio.run(self._run(call_tool))
