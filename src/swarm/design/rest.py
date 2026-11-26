"""Figma REST transport (057 AC-14): raw nodes/images/variables, no browser.

Used by `transport: rest` (or `auto` with `FIGMA_TOKEN`). It writes exactly the
same cache as the MCP transport, so the IR, brief, prompts and checks do not
know which path fetched the design.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from swarm.design import ir
from swarm.design.config import DesignConfig

logger = logging.getLogger(__name__)

API = "https://api.figma.com"


class RestError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class RestClient:
    def __init__(
        self,
        config: DesignConfig,
        *,
        token: str = "",
        client: httpx.Client | None = None,
    ):
        self.config = config
        self.token = token or config.rest_token()
        if not self.token:
            raise RestError("figma_token_missing", config.token_env)
        self._client = client

    def _request(self, client: httpx.Client, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"X-Figma-Token": self.token, "Accept": "application/json"}
        for attempt in range(3):
            response = client.get(API + path, headers=headers, **kwargs)
            if response.status_code != 429:
                return response
            retry = float(response.headers.get("Retry-After", "2") or 2)
            time.sleep(min(30.0, retry * (attempt + 1)))
        return response

    def fetch(self) -> tuple[dict[str, bytes | str], str, dict[str, Any], list[dict[str, str]]]:
        ids = ",".join(self.config.nodes)
        own = self._client is None
        client = self._client or httpx.Client(timeout=60.0, follow_redirects=True)
        artifacts: dict[str, bytes | str] = {}
        try:
            nodes_resp = self._request(client, f"/v1/files/{self.config.file_key}/nodes", params={"ids": ids})
            if nodes_resp.status_code != 200:
                raise RestError("figma_rest_failed", f"nodes {nodes_resp.status_code}: {nodes_resp.text[:200]}")
            data = nodes_resp.json()
            normalized = ir.normalize_file_nodes(data, self.config.file_key)
            tokens: dict[str, Any] = {}
            components: list[dict[str, str]] = []
            variables_resp = self._request(client, f"/v1/files/{self.config.file_key}/variables/local")
            if variables_resp.status_code == 200:
                tokens.update(ir.tokens_from_variables(variables_resp.json()))
            styles_resp = self._request(client, f"/v1/files/{self.config.file_key}/styles")
            if styles_resp.status_code == 200:
                tokens.update(ir.tokens_from_styles(styles_resp.json()))
            components_resp = self._request(client, f"/v1/files/{self.config.file_key}/components")
            if components_resp.status_code == 200:
                components = ir.components_from(components_resp.json())
            for node_id, node in normalized["nodes"].items():
                artifacts[f"{node_id.replace(':', '-')}.json"] = json.dumps(node, indent=2, sort_keys=True)
            images_resp = self._request(
                client,
                f"/v1/images/{self.config.file_key}",
                params={"ids": ids, "format": "png", "scale": self.config.scale},
            )
            if images_resp.status_code == 200:
                for node_id, url in (images_resp.json().get("images") or {}).items():
                    if not url:
                        continue
                    with client.stream("GET", url) as download:
                        download.raise_for_status()
                        chunks: list[bytes] = []
                        size = 0
                        for chunk in download.iter_bytes():
                            size += len(chunk)
                            if size > self.config.max_bytes:
                                raise RestError("figma_asset_too_large", node_id)
                            chunks.append(chunk)
                    artifacts[f"{str(node_id).replace(':', '-')}.png"] = b"".join(chunks)
            index = {
                "transport": "rest",
                "file": normalized["file"],
                "nodes": list(normalized["nodes"]),
                "components": components,
                "tokens": tokens,
            }
            artifacts["index.json"] = json.dumps(index, indent=2, sort_keys=True)
            artifacts["tokens.json"] = json.dumps(tokens, indent=2, sort_keys=True)
            artifacts["design-brief.md"] = ir.brief(
                file_info=normalized["file"],
                nodes=normalized["nodes"],
                tokens=tokens,
                components=components,
                transport="rest",
            )
            return artifacts, str(normalized["file"].get("version", "")), tokens, components
        finally:
            if own:
                client.close()
