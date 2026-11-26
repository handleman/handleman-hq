"""Design-lane configuration (057): one contract block + per-spec frames."""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

NODE_RE = re.compile(r"^\d+:\d+$")
DEFAULT_MCP_URL = "https://mcp.figma.com/mcp"
DEFAULT_TOKEN_FILE = "handleman-hq/figma/oauth.json"


class DesignConfigError(ValueError):
    """The `design:` block or `design.toml` is malformed."""


def _as_str(value: Any, name: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise DesignConfigError(f"design.{name} must be a string")
    return value.strip()


def _nodes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise DesignConfigError("design.nodes must be a list")
    out: list[str] = []
    for raw in value:
        node = str(raw).strip()
        if not NODE_RE.match(node):
            raise DesignConfigError(f"design.nodes entry {node!r} is not a frame id")
        out.append(node)
    return tuple(dict.fromkeys(out))


@dataclass(frozen=True)
class DesignConfig:
    provider: str = "figma"
    transport: str = "auto"
    file_key: str = ""
    nodes: tuple[str, ...] = ()
    token_env: str = "FIGMA_TOKEN"
    dir: str = "designs"
    scale: float = 2.0
    formats: tuple[str, ...] = ("png",)
    max_bytes: int = 20_000_000
    auth_timeout_s: int = 600
    open_browser: bool = True
    token_file: str = ""
    auto_sync: bool = True
    mcp_url: str = DEFAULT_MCP_URL

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> DesignConfig | None:
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise DesignConfigError("design must be a mapping")
        provider = _as_str(raw.get("provider"), "provider", "figma") or "figma"
        if provider != "figma":
            raise DesignConfigError(f"unsupported design provider {provider!r}")
        transport = _as_str(raw.get("transport"), "transport", "auto") or "auto"
        if transport not in {"auto", "mcp", "rest"}:
            raise DesignConfigError("design.transport must be auto, mcp or rest")
        auth = raw.get("auth") or {}
        if not isinstance(auth, Mapping):
            raise DesignConfigError("design.auth must be a mapping")
        formats = raw.get("formats") or ["png"]
        if not isinstance(formats, (list, tuple)):
            raise DesignConfigError("design.formats must be a list")
        try:
            scale = float(raw.get("scale", 2.0) or 2.0)
            max_bytes = int(raw.get("max_bytes", 20_000_000) or 20_000_000)
            timeout = int(auth.get("timeout_s", 600) or 600)
        except (TypeError, ValueError) as exc:
            raise DesignConfigError(f"design numeric field is invalid: {exc}") from exc
        config = cls(
            provider=provider,
            transport=transport,
            file_key=_as_str(raw.get("file_key"), "file_key"),
            nodes=_nodes(raw.get("nodes")),
            token_env=_as_str(raw.get("token_env"), "token_env", "FIGMA_TOKEN") or "FIGMA_TOKEN",
            dir=_as_str(raw.get("dir"), "dir", "designs") or "designs",
            scale=scale,
            formats=tuple(str(f).strip().lower() for f in formats if str(f).strip()),
            max_bytes=max_bytes,
            auth_timeout_s=timeout,
            open_browser=bool(auth.get("open_browser", True)),
            token_file=_as_str(auth.get("token_file"), "auth.token_file"),
            auto_sync=bool(raw.get("auto_sync", True)),
            mcp_url=_as_str(raw.get("mcp_url"), "mcp_url", DEFAULT_MCP_URL) or DEFAULT_MCP_URL,
        )
        if not config.file_key:
            raise DesignConfigError("design.file_key is required")
        if not config.nodes:
            raise DesignConfigError("design.nodes must list at least one frame")
        return config

    def with_nodes(self, extra: tuple[str, ...]) -> DesignConfig:
        return replace(self, nodes=tuple(dict.fromkeys((*self.nodes, *extra))))

    def cache_dir(self, root: Path) -> Path:
        return Path(root) / self.dir / self.file_key

    def token_path(self) -> Path:
        if self.token_file:
            return Path(os.path.expanduser(self.token_file))
        base = os.environ.get("XDG_DATA_HOME", "").strip()
        root = Path(base) if base else Path.home() / ".local" / "share"
        return root / DEFAULT_TOKEN_FILE

    def rest_token(self) -> str:
        return (os.environ.get(self.token_env) or "").strip()


def load_spec_design(spec_dir: Path) -> dict[str, Any] | None:
    """`<spec>/design.toml` — `[figma] file_key/node`, tokens, regions, screenshot."""
    path = Path(spec_dir) / "design.toml"
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise DesignConfigError(f"design.toml is unreadable: {exc}") from exc
    figma = data.get("figma")
    if not isinstance(figma, Mapping):
        raise DesignConfigError("design.toml needs a [figma] table")
    node = _as_str(figma.get("node"), "figma.node")
    if node and not NODE_RE.match(node):
        raise DesignConfigError("design.toml figma.node must look like 12:34")
    return data


def load_design(
    root: Path,
    spec_dir: Path | None = None,
    *,
    mapping: Mapping[str, Any] | None = None,
) -> DesignConfig | None:
    """Merge the contract block with a spec's `[figma]` frame (spec node is additive)."""
    config = DesignConfig.from_mapping(mapping)
    if spec_dir is None:
        return config
    spec = load_spec_design(spec_dir)
    if spec is None:
        return config
    figma = spec["figma"]
    node = str(figma.get("node", "")).strip()
    file_key = str(figma.get("file_key", "")).strip()
    if config is None:
        if not file_key or not node:
            raise DesignConfigError("design.toml needs file_key and node when swarm.yaml has no design block")
        config = DesignConfig(file_key=file_key, nodes=(node,))
    else:
        if file_key and file_key != config.file_key:
            raise DesignConfigError("design.toml file_key differs from swarm.yaml")
        config = config.with_nodes((node,) if node else ())
    return config
