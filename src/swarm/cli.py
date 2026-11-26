"""`hq` — the factory entry point (048 AC-3).

Thin by design: every command is the module the app already ran by hand, with
`SWARM_TARGET` set to the directory `hq` was invoked in (so the core reads the
app's `swarm.yaml`, specs and gates from there, never from the factory).

    hq init                 write a starter swarm.yaml in this repo
    hq run [--spec S --task T]...
    hq preflight            validate models/keys/catalogues/venvs
    hq report               the ledger dashboard
    hq bench ...            the replay benchmark
    hq up / stop / dash     supervise / stop / dashboard the queue
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from pathlib import Path


def _version() -> str:
    try:
        return _dist_version("handleman-hq")
    except PackageNotFoundError:
        return "0.2.0"


def _forward(module: str, args: list[str], *, target: Path | None = None) -> int:
    env = dict(os.environ)
    if target is not None:
        env["SWARM_TARGET"] = str(target.resolve())
    return subprocess.call([sys.executable, "-m", module, *args], env=env)


_STARTER = """\
# swarm.yaml — what the harness needs to know about this repo (048 AC-4).
specs_dir: specs/product
scope:
  - src/
  - tests/
gates:
  - pytest -q
  - ruff check .
e2e:
  command: npm run test:e2e
risk:
  profile: my-app
db:
  script: scripts/db.sh
python:
  venv: .venv
"""


def _init(target: Path) -> int:
    path = target / "swarm.yaml"
    if path.exists():
        print(f"{path} already exists — left untouched")
        return 0
    path.write_text(_STARTER)
    print(f"wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="hq", description=__doc__)
    parser.add_argument("--version", action="store_true", help="print the harness version")
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="run the queue (arguments pass to swarm.flow)")
    run.add_argument("rest", nargs=argparse.REMAINDER)
    for name, text in (
        ("preflight", "validate models/keys/venvs"),
        ("report", "the ledger dashboard"),
        ("bench", "the replay benchmark"),
    ):
        child = sub.add_parser(name, help=text)
        child.add_argument("rest", nargs=argparse.REMAINDER)
    init = sub.add_parser("init", help="write a starter swarm.yaml")
    init.add_argument("rest", nargs=argparse.REMAINDER)
    for name, text in (
        ("up", "start the queue and attach the dashboard"),
        ("stop", "stop the running queue"),
        ("dash", "attach the dashboard"),
    ):
        sub.add_parser(name, help=text)

    args = parser.parse_args(argv)
    if args.version or not args.command:
        print(f"hq {_version()}")
        return 0

    target = Path.cwd()
    if args.command == "init":
        return _init(target)
    if args.command == "run":
        return _forward("swarm.flow", args.rest, target=target)
    if args.command == "preflight":
        return _forward("swarm.preflight", args.rest, target=target)
    if args.command == "report":
        return _forward("swarm.report", args.rest, target=target)
    if args.command == "bench":
        return _forward("swarm.drivers.bench", args.rest, target=target)
    script = target / "swarm" / f"{args.command}.sh"
    if not script.is_file():
        print(
            f"hq {args.command}: {script} not found — run `hq {args.command}` in the "
            "repo that owns the queue scripts",
            file=sys.stderr,
        )
        return 1
    return subprocess.call([str(script)], cwd=target)


if __name__ == "__main__":
    raise SystemExit(main())