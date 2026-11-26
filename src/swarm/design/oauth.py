"""Figma MCP OAuth (057 AC-11/AC-12): first-run authorization and token storage.

The remote Figma MCP server advertises standard MCP authorization
(`https://mcp.figma.com/mcp` → AS `https://api.figma.com`, scope `mcp:connect`,
DCR + PKCE). The `mcp` SDK 1.30 already implements the protocol; this module
supplies the pieces an operator needs:

* a file-backed `TokenStorage` (0600, outside the repo),
* a loopback callback server for the browser redirect,
* `authorize()` — show the URL, wait, exchange, store,
* `status()` / `logout()`.

The token is never printed. A headless run raises `FigmaAuthRequired(url)` with
the same URL instead of blocking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.parse
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from swarm.design.config import DesignConfig

logger = logging.getLogger(__name__)

DEFAULT_CALLBACK_PORT = 8765
CALLBACK_PATH = "/callback"
CALLBACK_HTML = (
    "<!doctype html><meta charset=utf-8><title>Figma authorized</title>"
    "<body style='font-family:system-ui;padding:2rem'>"
    "<h1>Figma authorized</h1><p>You can close this window and return to the swarm.</p>"
)


class FigmaAuthRequired(RuntimeError):
    """No usable token and the caller cannot run the browser flow."""

    def __init__(self, url: str = ""):
        self.url = url
        super().__init__(url or "Figma authorization required")


def _new_metadata(redirect_uri: str) -> OAuthClientMetadata:
    return OAuthClientMetadata(
        redirect_uris=[redirect_uri],  # type: ignore[list-item]
        token_endpoint_auth_method="client_secret_basic",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="mcp:connect",
        client_name="handleman-hq",
    )


class FileTokenStorage:
    """File-backed `mcp` TokenStorage: client info + tokens, 0600, outside the repo."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._read().get("tokens")
        if not isinstance(raw, dict):
            return None
        try:
            return OAuthToken.model_validate(raw)
        except ValueError:
            return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._read()
        data["tokens"] = tokens.model_dump(mode="json")
        if tokens.expires_in:
            data["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=int(tokens.expires_in))
            ).isoformat(timespec="seconds")
        self._write(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._read().get("client_info")
        if not isinstance(raw, dict):
            return None
        try:
            return OAuthClientInformationFull.model_validate(raw)
        except ValueError:
            return None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = self._read()
        data["client_info"] = client_info.model_dump(mode="json")
        self._write(data)

    async def clear_client_info(self) -> None:
        data = self._read()
        data.pop("client_info", None)
        self._write(data)

    def status(self) -> dict[str, Any]:
        data = self._read()
        tokens = data.get("tokens") or {}
        expires_at = data.get("expires_at") or ""
        expired = False
        if expires_at:
            try:
                expired = datetime.fromisoformat(expires_at) <= datetime.now(UTC)
            except ValueError:
                expired = False
        return {
            "path": str(self.path),
            "authenticated": bool(tokens.get("access_token")),
            "expires_at": expires_at,
            "expired": expired,
            "account": data.get("account", ""),
            "resource": data.get("resource", ""),
        }

    def record_account(self, account: str) -> None:
        data = self._read()
        data["account"] = account
        self._write(data)

    def delete(self) -> bool:
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return False


class CallbackServer:
    """A tiny loopback HTTP server that receives Figma's redirect."""

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_CALLBACK_PORT):
        self.host = host
        self.requested_port = port
        self.port = 0
        self._server: asyncio.AbstractServer | None = None
        self._future: asyncio.Future[tuple[str, str | None]] | None = None

    async def start(self) -> str:
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        try:
            self._server = await asyncio.start_server(self._handle, self.host, self.requested_port)
        except OSError:
            self._server = await asyncio.start_server(self._handle, self.host, 0)
        socket = self._server.sockets[0]
        self.port = int(socket.getsockname()[1])
        return f"http://{self.host}:{self.port}{CALLBACK_PATH}"

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = (await reader.readline()).decode("latin-1").strip()
            parts = request.split(" ")
            path = parts[1] if len(parts) > 1 else "/"
            query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
            code = (query.get("code") or [""])[0]
            state = (query.get("state") or [None])[0]
            error = (query.get("error") or [""])[0]
            body = CALLBACK_HTML if code and not error else (
                "<h1>Figma authorization failed</h1><p>" + (error or "missing code") + "</p>"
            )
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                + f"Content-Length: {len(body.encode())}\r\nConnection: close\r\n\r\n".encode()
                + body.encode()
            )
            await writer.drain()
            if self._future and not self._future.done():
                if code and not error:
                    self._future.set_result((code, state))
                else:
                    self._future.set_exception(FigmaAuthRequired(f"authorization failed: {error or 'missing code'}"))
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def wait(self, timeout: float) -> tuple[str, str | None]:
        if self._future is None:
            raise FigmaAuthRequired("callback server was not started")
        return await asyncio.wait_for(self._future, timeout=timeout)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


def _print_url(url: str) -> None:
    print("\n" + "=" * 78)
    print("Figma authorization required. Open this URL and approve access:")
    print(url)
    print("Waiting for the browser redirect (Ctrl-C to abort)...")
    print("=" * 78 + "\n", flush=True)


async def _authorize(
    config: DesignConfig,
    *,
    open_browser: bool = True,
    timeout: float | None = None,
    on_url: Callable[[str], None] | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    storage = FileTokenStorage(config.token_path())
    status = storage.status()
    if status["authenticated"] and not status["expired"]:
        return status

    timeout = float(timeout or config.auth_timeout_s)
    server = CallbackServer()
    redirect = await server.start()
    info = await storage.get_client_info()
    if info and redirect not in [str(u) for u in (info.redirect_uris or [])]:
        # A different loopback port needs a fresh DCR registration.
        await storage.clear_client_info()

    opened = {"done": False}

    async def redirect_handler(url: str) -> None:
        if non_interactive:
            raise FigmaAuthRequired(url)
        _print_url(url)
        if on_url is not None:
            try:
                on_url(url)
            except Exception as exc:  # noqa: BLE001 - reporting must not break auth
                logger.debug("figma: on_url callback failed: %s", exc)
        if open_browser and not opened["done"]:
            opened["done"] = True
            try:
                webbrowser.open(url)
            except Exception as exc:  # noqa: BLE001 - headless/no browser
                logger.debug("figma: could not open the browser: %s", exc)

    async def callback_handler() -> tuple[str, str | None]:
        return await server.wait(timeout)

    provider = OAuthClientProvider(
        server_url=config.mcp_url,
        client_metadata=_new_metadata(redirect),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
        timeout=timeout,
    )
    try:
        async with streamablehttp_client(config.mcp_url, auth=provider) as (read, write, _):
            from mcp import ClientSession

            async with ClientSession(read, write) as session:
                await session.initialize()
        data = storage._read()
        data.update(
            {
                "resource": config.mcp_url,
                "authorized_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
        storage._write(data)
        return storage.status()
    finally:
        await server.close()


def authorize(
    config: DesignConfig,
    *,
    open_browser: bool = True,
    timeout: float | None = None,
    on_url: Callable[[str], None] | None = None,
    non_interactive: bool = False,
) -> dict[str, Any]:
    """Run the OAuth flow (blocking) and return the token status."""
    return asyncio.run(
        _authorize(
            config,
            open_browser=open_browser,
            timeout=timeout,
            on_url=on_url,
            non_interactive=non_interactive,
        )
    )


def status(config: DesignConfig) -> dict[str, Any]:
    return FileTokenStorage(config.token_path()).status()


def logout(config: DesignConfig) -> bool:
    return FileTokenStorage(config.token_path()).delete()


def access_token(config: DesignConfig) -> str | None:
    """The stored access token, if present (used only by the MCP client)."""
    path = config.token_path()
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    token = (data.get("tokens") or {}).get("access_token")
    return str(token) if token else None


def token_age_seconds(config: DesignConfig) -> float | None:
    st = status(config)
    when = st.get("expires_at")
    if not when:
        return None
    try:
        return (datetime.fromisoformat(when) - datetime.now(UTC)).total_seconds()
    except ValueError:
        return None
