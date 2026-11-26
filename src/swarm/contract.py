"""The repo contract: what the harness needs to know about its target (048 AC-4).

One file — `<target>/swarm.yaml` — declares the specs directory, the writable
scope, the gate commands, the browser suite, the risk profile, the DB script and
the python venv. **The defaults reproduce today's comfort-walking-router
behaviour**, so the app is a drop-in: no `swarm.yaml` means exactly what the
hard-coded tables said before this module existed.

The five tables this replaces live in `swarm/flow.py` (`HARNESS_SPECS`),
`swarm/tools_guarded.py` (`DEFAULT_SCOPE`), `swarm/gates.py` (`DEFAULT_MAP`) and
`swarm/risk.py` (the path classes). 048 T9 wires them to this loader; until then
`tests/test_contract.py` pins the defaults to those tables so they cannot drift.

    python -m swarm.contract        # print the resolved contract (inspectable)

Parsing is strict enough to catch a typo (`scope: app` — a string, not a list)
but tolerant of unknown keys, so an older factory can read a newer file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from swarm.paths import REPO_ROOT

CONTRACT_FILE = "swarm.yaml"

# Today's behaviour, in one place (048 T9 moves the consumers here).
DEFAULT_SPECS_DIR = "specs/harness"
DEFAULT_SCOPE: tuple[str, ...] = ("src/", "tests/")
# Paths treated as type-checked frontend work (routing, tests-first heuristics).
DEFAULT_FRONTEND_DIRS: tuple[str, ...] = ("src/", "ui/", "lib/")
# Where browser specs live, relative to the target root.
DEFAULT_E2E_ROOT = ""
DEFAULT_E2E_DIR = "e2e"
DEFAULT_LOCK_DIR = ""
DEFAULT_RUNS_DIR = "swarm/runs"
DEFAULT_GATES: tuple[str, ...] = ()
# Affected-gate selection: a glob → the gates that delta can break. Moved here
# from gates.DEFAULT_MAP so the factory and the app share one declaration.
DEFAULT_GATE_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("src/**", ("pytest -q", "ruff check .")),
    ("tests/**", ("pytest -q", "ruff check .")),
)
DEFAULT_E2E = ""
DEFAULT_RISK_PROFILE = "generic"
# Path classes for the risk label (moved from risk.py). Class 3 is always the
# fallback: an unrecognised delta must never look safe.
DEFAULT_RISK_CLASSES: dict[int, tuple[str, ...]] = {
    1: ("tests/", "e2e/"),
    2: ("src/", "lib/"),
    3: (
        "swarm/",
        "specs/",
        ".github/",
        "docker/",
        "requirements",
        "pyproject.toml",
        "auth",
        "migrations",
        "payments",
        "secrets",
        "infra",
    ),
}
DEFAULT_DB_SCRIPT = ""
DEFAULT_PYTHON_VENV = ".venv"
DEFAULT_HARNESS_SPECS: tuple[str, ...] = (
    "009-swarm-harness",
    "012-dark-factory-harness",
    "013-dark-factory-phase-2",
    "015-dark-factory-economics",
    "016-conflict-recovery",
    "017-coder-selfcheck",
    "018-operator-readable-runs",
    "019-scenario-verifier",
    "020-harness-efficiency",
    "021-fix-loop",
    "022-lean-loop",
    "023-parallel-factory",
    "024-earned-autonomy",
    "025-durable-journal",
    "026-run-guards",
    "027-e2e-self-heal",
    "030-operator-runbooks",
    "031-dashboard-update",
    "032-spec-kind",
    "033-planner-coder-chain",
    "034-spec-folders",
)


class ContractError(ValueError):
    """`swarm.yaml` is unreadable or has a value of the wrong type."""


@dataclass(frozen=True)
class Contract:
    root: Path = REPO_ROOT
    specs_dir: str = DEFAULT_SPECS_DIR
    scope: tuple[str, ...] = DEFAULT_SCOPE
    gates: tuple[str, ...] = DEFAULT_GATES
    e2e: str = DEFAULT_E2E
    risk_profile: str = DEFAULT_RISK_PROFILE
    db_script: str = DEFAULT_DB_SCRIPT
    python_venv: str = DEFAULT_PYTHON_VENV
    harness_specs: tuple[str, ...] = DEFAULT_HARNESS_SPECS
    frontend_dirs: tuple[str, ...] = DEFAULT_FRONTEND_DIRS
    e2e_root: str = DEFAULT_E2E_ROOT
    e2e_dir: str = DEFAULT_E2E_DIR
    lock_dir: str = DEFAULT_LOCK_DIR
    runs_dir: str = DEFAULT_RUNS_DIR
    gate_map: tuple[tuple[str, tuple[str, ...]], ...] = DEFAULT_GATE_MAP
    risk_classes: dict[int, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_RISK_CLASSES)
    )
    source: str = "defaults"  # "defaults" | the file it was read from
    extra: dict[str, Any] = field(default_factory=dict)

    def e2e_prefix(self) -> str:
        """The target-relative prefix browser specs live under (`e2e`, or `ui/e2e`)."""
        return "/".join(part for part in (self.e2e_root.strip("/"), self.e2e_dir.strip("/")) if part)

    def e2e_repo_path(self, file: str) -> str:
        """Repo-relative path of a triage file (`e2e/x.spec.ts` → the full path)."""
        return "/".join(
            part for part in (self.e2e_root.strip("/"), str(file).lstrip("/")) if part
        )

    def runs_path(self, root: Path | str | None = None) -> Path:
        """Where run traces live (`harness/runs` in an app, `swarm/runs` here)."""
        base = Path(root) if root is not None else self.root
        return base / self.runs_dir

    def path(self, *parts: str) -> Path:
        """A path inside the target repo."""
        return self.root.joinpath(*parts)


def _as_tuple(raw: Any, key: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        raise ContractError(f"{key} must be a list of strings, not a bare string")
    if not isinstance(raw, (list, tuple)):
        raise ContractError(f"{key} must be a list of strings")
    out: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out)


def _as_str(raw: Any, key: str) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, (str, int, float)):
        raise ContractError(f"{key} must be a string")
    return str(raw).strip()


def load(root: Path | None = None, *, text: str | None = None) -> Contract:
    """Read `swarm.yaml` under `root` (or parse `text`); defaults fill the rest."""
    base = Path(root or REPO_ROOT)
    path = base / CONTRACT_FILE
    raw: dict[str, Any] = {}
    source = "defaults"
    if text is not None:
        raw, source = _parse(text, str(path))
    elif path.is_file():
        try:
            raw, source = _parse(path.read_text(), str(path))
        except OSError as exc:
            raise ContractError(f"cannot read {path}: {exc}") from exc

    known = {
        "specs_dir",
        "scope",
        "gates",
        "e2e",
        "risk",
        "db",
        "python",
        "harness_specs",
    }
    extra = {k: v for k, v in raw.items() if k not in known}

    risk = raw.get("risk") or {}
    db = raw.get("db") or {}
    python = raw.get("python") or {}

    # `e2e` accepts a string or the documented mapping:
    #   e2e: {command: ..., specs: frontend/e2e}   (specs sets root/dir)
    e2e_raw = raw.get("e2e")
    e2e_root = _as_str(raw.get("e2e_root"), "e2e_root")
    e2e_dir = _as_str(raw.get("e2e_dir"), "e2e_dir") or DEFAULT_E2E_DIR
    if isinstance(e2e_raw, dict):
        e2e_command = _as_str(e2e_raw.get("command"), "e2e.command")
        specs = _as_str(e2e_raw.get("specs"), "e2e.specs")
        if specs:
            root, _, directory = specs.rstrip("/").rpartition("/")
            e2e_root = root
            e2e_dir = directory or DEFAULT_E2E_DIR
        e2e_root = _as_str(e2e_raw.get("root"), "e2e.root") or e2e_root
        e2e_dir = _as_str(e2e_raw.get("dir"), "e2e.dir") or e2e_dir
    elif e2e_raw is None or isinstance(e2e_raw, str):
        e2e_command = _as_str(e2e_raw, "e2e")
    else:
        raise ContractError("e2e must be a command string or a mapping with command")
    for key, value in (("risk", risk), ("db", db), ("python", python)):
        if value and not isinstance(value, dict):
            raise ContractError(f"{key} must be a mapping")

    return Contract(
        root=base,
        specs_dir=_as_str(raw.get("specs_dir"), "specs_dir") or DEFAULT_SPECS_DIR,
        scope=_as_tuple(raw.get("scope"), "scope") or DEFAULT_SCOPE,
        gates=_as_tuple(raw.get("gates"), "gates") or DEFAULT_GATES,
        e2e=e2e_command or DEFAULT_E2E,
        risk_profile=_as_str(risk.get("profile"), "risk.profile") or DEFAULT_RISK_PROFILE,
        risk_classes=_risk_classes(risk.get("classes")) or dict(DEFAULT_RISK_CLASSES),
        db_script=_as_str(db.get("script"), "db.script") or DEFAULT_DB_SCRIPT,
        python_venv=_as_str(python.get("venv"), "python.venv") or DEFAULT_PYTHON_VENV,
        harness_specs=_as_tuple(raw.get("harness_specs"), "harness_specs")
        or DEFAULT_HARNESS_SPECS,
        frontend_dirs=_as_tuple(raw.get("frontend_dirs"), "frontend_dirs")
        or DEFAULT_FRONTEND_DIRS,
        e2e_root=e2e_root,
        e2e_dir=e2e_dir,
        lock_dir=_as_str(raw.get("lock_dir"), "lock_dir"),
        runs_dir=_as_str(raw.get("runs_dir"), "runs_dir") or DEFAULT_RUNS_DIR,
        gate_map=_gate_map(raw.get("gate_map")) or DEFAULT_GATE_MAP,
        source=source,
        extra=extra,
    )


def _risk_classes(raw: Any) -> dict[int, tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ContractError("risk.classes must be a mapping of class -> path list")
    out: dict[int, tuple[str, ...]] = {}
    for key, values in raw.items():
        try:
            cls = int(key)
        except (TypeError, ValueError) as exc:
            raise ContractError(f"risk.classes key {key!r} is not an integer") from exc
        if cls not in (1, 2, 3):
            raise ContractError(f"risk.classes key {cls} is not 1, 2 or 3")
        out[cls] = _as_tuple(values, f"risk.classes.{cls}")
    return out


def _gate_map(raw: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ContractError("gate_map must be a mapping of glob -> gate list")
    out: list[tuple[str, tuple[str, ...]]] = []
    for glob, commands in raw.items():
        name = str(glob).strip()
        if not name:
            continue
        out.append((name, _as_tuple(commands, f"gate_map.{name}")))
    return tuple(out)


@lru_cache(maxsize=8)
def _cached(root: str, mtime: float) -> Contract:
    return load(Path(root))


def current(root: Path | None = None) -> Contract:
    """The contract for `root`, cached until `swarm.yaml` changes."""
    base = Path(root or REPO_ROOT)
    path = base / CONTRACT_FILE
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return _cached(str(base), mtime)


def _parse(text: str, where: str) -> tuple[dict[str, Any], str]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - crewai always ships pyyaml
        raise ContractError("pyyaml is required to read swarm.yaml") from exc
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ContractError(f"{where} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{where} must be a mapping at the top level")
    return data, where


def main() -> int:
    contract = load()
    print(f"contract   {contract.source}")
    print(f"root       {contract.root}")
    print(f"specs_dir  {contract.specs_dir}")
    print(f"scope      {', '.join(contract.scope)}")
    print(f"gates      {len(contract.gates)} command(s)" + (f": {contract.gates}" if contract.gates else ""))
    print(f"e2e        {contract.e2e}")
    print(f"risk       {contract.risk_profile}")
    print(f"db         {contract.db_script}")
    print(f"python     {contract.python_venv}")
    print(f"harness    {len(contract.harness_specs)} spec(s)")
    print(f"gate_map   {len(contract.gate_map)} rule(s)")
    print(f"e2e        {contract.e2e_prefix()}")
    print(f"runs       {contract.runs_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())