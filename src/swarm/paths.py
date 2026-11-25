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

# Repo root of a source checkout in the factory layout: <root>/src/swarm/paths.py
_SOURCE_ROOT = Path(__file__).resolve().parents[2]


def target_root() -> Path:
    """SWARM_TARGET when set (the CLI), else the checkout root."""
    raw = os.getenv("SWARM_TARGET", "").strip()
    return Path(raw).expanduser().resolve() if raw else _SOURCE_ROOT


REPO_ROOT = target_root()
