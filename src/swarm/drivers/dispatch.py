"""Run a target's drivers as commands (056 AC-1/AC-3).

The target declares `drivers.{e2e,acceptance,smoke,db}` in `swarm.yaml`. Each is
a command that receives JSON parameters in `SWARM_DRIVER_PARAMS` and returns
JSON on stdout:

    {"ok": true, "exit": 0, "detail": "9 passed / 3 skipped", "artifacts": []}

An absent key falls back to the packaged implementation, and the source is
recorded so a silently missing driver cannot look green. A bad exit or
unparseable output is a typed `DriverError`, not a traceback.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swarm import contract


@dataclass
class DriverResult:
    kind: str
    source: str  # "target" | "packaged"
    exit: int
    detail: str = ""
    tail: str = ""
    artifacts: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit == 0

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "ok": self.ok,
            "exit": self.exit,
            "detail": self.detail,
            "artifacts": list(self.artifacts),
        }


class DriverError(RuntimeError):
    """A declared driver could not be run or returned an unusable result."""


def _parse(stdout: str) -> dict[str, Any] | None:
    text = (stdout or "").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        data = json.loads(text[start:])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def run(
    kind: str,
    params: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    timeout: float = 600.0,
    env: dict[str, str] | None = None,
) -> DriverResult:
    """Run `kind` from the target, or the packaged fallback when undeclared."""
    base = Path(root or contract.current().root)
    declared = contract.current(base).drivers.get(kind, "")
    if declared:
        return _run_command(kind, declared, params or {}, base, timeout, env)
    return _packaged(kind, params or {}, base, timeout)


def _run_command(
    kind: str,
    command: str,
    params: dict[str, Any],
    root: Path,
    timeout: float,
    extra_env: dict[str, str] | None,
) -> DriverResult:
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    env["SWARM_DRIVER_PARAMS"] = json.dumps(params)
    try:
        proc = subprocess.run(
            shlex.split(command),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DriverError(f"{kind} driver could not run: {exc}") from exc
    stdout, stderr = proc.stdout or "", proc.stderr or ""
    data = _parse(stdout)
    if data is None and proc.returncode not in (0,):
        # A failing driver without JSON still has a usable exit code; keep the
        # tail so triage/evidence can read it.
        return DriverResult(kind, "target", proc.returncode, tail=(stdout + stderr)[-8000:])
    if data is None and proc.returncode == 0:
        raise DriverError(
            f"{kind} driver printed no JSON result (see docs/drivers.md)"
        )
    exit_code = int(data.get("exit", proc.returncode))
    return DriverResult(
        kind,
        "target",
        exit_code,
        detail=str(data.get("detail", "")),
        tail=str(data.get("tail", "")) or (stdout + stderr)[-8000:],
        artifacts=[str(a) for a in (data.get("artifacts") or [])],
    )


def _packaged(kind: str, params: dict[str, Any], root: Path, timeout: float) -> DriverResult:
    """The v0.3 behaviour, kept as the fallback."""
    if kind == "e2e":
        return _packaged_e2e(params, root)
    if kind == "acceptance":
        from swarm.drivers import acceptance

        result = acceptance.run(
            repo=root,
            specs=params.get("specs") or None,
            queue=bool(params.get("queue", False)),
            build=bool(params.get("build", True)),
            base_url=params.get("base_url"),
            log=lambda _m: None,
        )
        return DriverResult(
            "acceptance",
            "packaged",
            result.exit_code,
            detail=result.verdict,
            artifacts=[str(s) for r in result.reports for s in (r.shots.values() if r.shots else [])],
        )
    raise DriverError(
        f"no {kind} driver declared in swarm.yaml and no packaged implementation "
        "(docs/drivers.md)"
    )


def _packaged_e2e(params: dict[str, Any], root: Path) -> DriverResult:

    frontend = Path(root) / "frontend"
    specs = [str(s) for s in (params.get("specs") or [])]
    try:
        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        suite = subprocess.run(
            ["npx", "playwright", "test", *specs],
            cwd=frontend,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DriverError(f"e2e launch failed: {exc}") from exc
    code = int(suite.returncode)
    tail = suite.stdout + suite.stderr
    if build.returncode != 0:
        code = int(build.returncode)
        tail = build.stdout + build.stderr + "\n" + tail
    detail = "e2e suite"
    return DriverResult("e2e", "packaged", code, detail=detail, tail=tail[-8000:])


__all__ = ["DriverError", "DriverResult", "run"]
