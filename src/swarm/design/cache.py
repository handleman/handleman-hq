"""Atomic design cache + lock (057 AC-1/AC-6)."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from swarm.design.config import DesignConfig

LOCK = "design.lock"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_cache(
    root: Path,
    config: DesignConfig,
    artifacts: Mapping[str, bytes | str],
    *,
    file_version: str = "",
    transport: str = "",
) -> Path:
    """Write `designs/<key>/` atomically; the lock is written last."""
    target = config.cache_dir(root)
    tmp = target.with_name(target.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    try:
        for rel, payload in artifacts.items():
            data = payload.encode() if isinstance(payload, str) else payload
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            hashes[rel] = _sha(data)
        lock = {
            "file_key": config.file_key,
            "transport": transport or config.transport,
            "file_version": file_version,
            "nodes": list(config.nodes),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "hashes": hashes,
        }
        (tmp / LOCK).write_text(json.dumps(lock, indent=2, sort_keys=True))
        if target.exists():
            shutil.rmtree(target)
        tmp.replace(target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def load_lock(root: Path, config: DesignConfig) -> dict[str, Any] | None:
    path = config.cache_dir(root) / LOCK
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def check_cache(
    root: Path, config: DesignConfig, *, spec_nodes: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Verify the cache exists, covers the allowlist and its hashes match."""
    target = config.cache_dir(root)
    if not target.is_dir():
        return {"ok": False, "code": "design_missing", "detail": str(target), "lock": None}
    lock = load_lock(root, config)
    if lock is None:
        return {"ok": False, "code": "design_missing", "detail": LOCK, "lock": None}
    missing = [node for node in (*config.nodes, *spec_nodes) if node not in (lock.get("nodes") or [])]
    if missing:
        return {
            "ok": False,
            "code": "design_node_missing",
            "detail": ", ".join(missing),
            "lock": lock,
        }
    for rel, digest in (lock.get("hashes") or {}).items():
        path = target / rel
        try:
            current = _sha(path.read_bytes())
        except OSError:
            return {"ok": False, "code": "design_stale", "detail": rel, "lock": lock}
        if current != digest:
            return {"ok": False, "code": "design_stale", "detail": rel, "lock": lock}
    return {"ok": True, "code": "", "detail": str(target), "lock": lock}


def read_node(target: Path, node: str) -> dict[str, Any] | None:
    try:
        data = json.loads((target / f"{node.replace(':', '-')}.json").read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def brief_path(target: Path) -> Path:
    return target / "design-brief.md"


def read_brief(target: Path, *, limit: int = 8000) -> str:
    try:
        return brief_path(target).read_text()[:limit]
    except OSError:
        return ""
