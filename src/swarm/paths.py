"""Where the harness operates (048 AC-4: the target repo, not the factory).

`hq` sets `SWARM_TARGET` to the directory it was invoked in; `python -m swarm.*`
keeps working from a checkout (the source root, so unit tests and the app's
`make swarm-*` targets behave as before).

This is the one place that decides; modules import `REPO_ROOT` from here instead
of each computing `Path(__file__).parent.parent` (which pointed at `src/` after
the src-layout move and broke every write).
"""

from __future__ import annotations

import os
from pathlib import Path


def _default_root() -> Path:
    """The checkout root when this is a source tree, else the caller's cwd.

    An installed package resolves to site-packages, where running from cwd is
    the only sensible default (`hq` passes SWARM_TARGET explicitly, so the CLI
    is unaffected either way; this keeps `python -m swarm.*` usable).
    """
    try:
        root = Path(__file__).resolve().parents[2]
    except IndexError:
        return Path.cwd()
    if (root / "pyproject.toml").is_file() and (
        (root / "src" / "swarm").is_dir() or (root / "swarm").is_dir()
    ):
        return root
    return Path.cwd()


# Repo root of a source checkout in the factory layout: <root>/src/swarm/paths.py
_SOURCE_ROOT = _default_root()


def target_root() -> Path:
    """SWARM_TARGET when set (the CLI), else the checkout root."""
    raw = os.getenv("SWARM_TARGET", "").strip()
    return Path(raw).expanduser().resolve() if raw else _SOURCE_ROOT


REPO_ROOT = target_root()
