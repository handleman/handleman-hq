"""Pre-push audit for the factory repo (054 AC-5, 048 Phase 7).

`git filter-repo --subdirectory-filter swarm/` keeps only the subtree, so the
repo-root `.gitignore`, `.dockerignore` and LICENSE do not survive. On
2026-11-26 the filtered factory tracked **120 `__pycache__` files** and a
`git add -A` would have published them. This is the gate before any push:

* tracked caches and build output (`__pycache__`, `*.pyc`, `.venv`, `dist/` …)
* tracked secrets (`.env*` except the example, keys, credentials)
* blobs over 1 MB (history bloat / accidental data)
* hygiene files present and the ignore rules that keep the first class out

    python -m swarm.factory_audit [--root DIR]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

MAX_BLOB = 1_000_000

CACHE_PARTS = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".eggs",
)
CACHE_SUFFIXES = (".pyc", ".pyo", ".so", ".dylib", ".whl", ".egg-info")
SECRET_NAMES = (
    ".env",
    "credentials",
    "credentials.json",
    "secrets",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
)
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore")
HYGIENE = (".gitignore", ".dockerignore", "README.md", "pyproject.toml")
IGNORE_MUST_COVER = ("__pycache__", ".venv", ".env")


def _git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=not binary,
        check=False,
    )
    return proc.stdout


def tracked(root: Path) -> list[str]:
    raw = _git(root, "ls-files", "-z", binary=True)
    assert isinstance(raw, bytes)
    return [p for p in raw.decode("utf-8", "replace").split("\0") if p]


def blob_size(root: Path, path: str) -> int:
    raw = _git(root, "cat-file", "-s", f"HEAD:{path}", binary=True)
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    try:
        return int(text.strip() or 0)
    except ValueError:
        return 0


def audit(root: Path | None = None) -> list[str]:
    """Every problem that must block a push; empty means clean."""
    base = Path(root or Path.cwd())
    problems: list[str] = []
    if not (base / ".git").exists():
        return [f"{base} is not a git checkout"]

    files = tracked(base)
    if not files:
        return ["no tracked files (wrong directory?)"]

    for rel in files:
        parts = rel.split("/")
        name = parts[-1]
        if any(part in CACHE_PARTS for part in parts):
            problems.append(f"tracked cache/build path: {rel}")
        elif name.endswith(CACHE_SUFFIXES):
            problems.append(f"tracked binary/cache file: {rel}")
        elif name in SECRET_NAMES or name.endswith(SECRET_SUFFIXES):
            problems.append(f"tracked secret-shaped file: {rel}")
        elif name.startswith(".env.") and name != ".env.example":
            problems.append(f"tracked environment file: {rel}")
        else:
            size = blob_size(base, rel)
            if size > MAX_BLOB:
                problems.append(f"tracked blob over 1 MB: {rel} ({size / 1e6:.1f} MB)")

    for required in HYGIENE:
        if not (base / required).is_file():
            problems.append(f"missing hygiene file: {required}")

    ignore_path = base / ".gitignore"
    if ignore_path.is_file():
        ignore = ignore_path.read_text()
        for pattern in IGNORE_MUST_COVER:
            if pattern not in ignore:
                problems.append(f".gitignore does not cover {pattern}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="factory-audit", description=__doc__)
    parser.add_argument("--root", default=None, help="repo to audit (default: cwd)")
    args = parser.parse_args(argv)
    problems = audit(Path(args.root) if args.root else None)
    if problems:
        print("factory-audit: FAIL")
        for problem in problems:
            print(" -", problem)
        return 1
    print("factory-audit: OK (no caches, secrets, large blobs; hygiene present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())