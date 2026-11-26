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
DEFAULT_SPECS_DIR = "specs/product"
DEFAULT_SCOPE: tuple[str, ...] = (
    "app/",
    "frontend/",
    "tests/",
    "contracts/",
    "requirements-dev.txt",
    "requirements.txt",
    "pyproject.toml",
    ".gitignore",
)
DEFAULT_GATES: tuple[str, ...] = ()
# Affected-gate selection: a glob → the gates that delta can break. Moved here
# from gates.DEFAULT_MAP so the factory and the app share one declaration.
DEFAULT_GATE_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("app/**", ("pytest -q", "ruff check .", "mypy app tests")),
    ("tests/**", ("pytest -q", "ruff check .", "mypy app tests")),
    ("contracts/**", ("pytest -q",)),
    (
        "frontend/**",
        (
            "npm --prefix frontend run check",
            "npm --prefix frontend run lint",
            "npm --prefix frontend test -- --run",
        ),
    ),
)
DEFAULT_E2E = "npm --prefix frontend run test:e2e"
DEFAULT_RISK_PROFILE = "comfort-walking-router"
# Path classes for the risk label (moved from risk.py). Class 3 is always the
# fallback: an unrecognised delta must never look safe.
DEFAULT_RISK_CLASSES: dict[int, tuple[str, ...]] = {
    1: ("tests/", "frontend/e2e/", "e2e/"),
    2: ("app/", "frontend/src/", "frontend/lib/", "contracts/"),
    3: (
        "swarm/",
        "specs/",
        ".github/",
        "docker/",
        "requirements",
        "pyproject.toml",
        "app/auth",
        "auth",
        "migrations",
        "payments",
        "secrets",
        "infra",
    ),
}
DEFAULT_DB_SCRIPT = "swarm/db.sh"
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
    gate_map: tuple[tuple[str, tuple[str, ...]], ...] = DEFAULT_GATE_MAP
    risk_classes: dict[int, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_RISK_CLASSES)
    )
    source: str = "defaults"  # "defaults" | the file it was read from
    extra: dict[str, Any] = field(default_factory=dict)

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
    for key, value in (("risk", risk), ("db", db), ("python", python)):
        if value and not isinstance(value, dict):
            raise ContractError(f"{key} must be a mapping")

    return Contract(
        root=base,
        specs_dir=_as_str(raw.get("specs_dir"), "specs_dir") or DEFAULT_SPECS_DIR,
        scope=_as_tuple(raw.get("scope"), "scope") or DEFAULT_SCOPE,
        gates=_as_tuple(raw.get("gates"), "gates") or DEFAULT_GATES,
        e2e=_as_str(raw.get("e2e"), "e2e") or DEFAULT_E2E,
        risk_profile=_as_str(risk.get("profile"), "risk.profile") or DEFAULT_RISK_PROFILE,
        risk_classes=_risk_classes(risk.get("classes")) or dict(DEFAULT_RISK_CLASSES),
        db_script=_as_str(db.get("script"), "db.script") or DEFAULT_DB_SCRIPT,
        python_venv=_as_str(python.get("venv"), "python.venv") or DEFAULT_PYTHON_VENV,
        harness_specs=_as_tuple(raw.get("harness_specs"), "harness_specs")
        or DEFAULT_HARNESS_SPECS,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
