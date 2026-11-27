"""Per-task budget profiles (060).

The coding caps are one size; e2e and visual/screenshot tasks are the expensive
tail in the run data (see `specs/harness/060-task-budgets/evidence.md`). This
module classifies a task from its brief/spec name and scales the six caps. The
default multiplier is 2.0; `SWARM_E2E_CAP_MULTIPLIER` and
`SWARM_VISUAL_CAP_MULTIPLIER` override it (never below 1.0).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

PROFILES = ("coding", "e2e", "visual")
DEFAULT_MULTIPLIER = 2.0
PROFILE_ENV = {
    "e2e": "SWARM_E2E_CAP_MULTIPLIER",
    "visual": "SWARM_VISUAL_CAP_MULTIPLIER",
}

_E2E_RE = re.compile(r"\b(e2e|playwright|browser spec|\.spec\.ts)\b", re.IGNORECASE)
_VISUAL_RE = re.compile(
    r"\b(screenshot|visual|design|figma|layout|acceptance|snapshot)\b",
    re.IGNORECASE,
)


def task_profile(brief: str, spec_name: str = "") -> str:
    """`e2e` | `visual` | `coding`; e2e wins when a brief matches both."""
    text = f"{spec_name} {brief}"
    if _E2E_RE.search(text):
        return "e2e"
    if _VISUAL_RE.search(text):
        return "visual"
    return "coding"


def profile_multiplier(
    profile: str, env: Mapping[str, str] | None = None
) -> float:
    """The cap multiplier for a profile; coding is always 1.0."""
    name = PROFILE_ENV.get(profile)
    if name is None:
        return 1.0
    source = os.environ if env is None else env
    raw = source.get(name, DEFAULT_MULTIPLIER)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = DEFAULT_MULTIPLIER
    return max(1.0, value)


def scaled_caps(
    *,
    tokens: int,
    cost: float,
    seconds: int,
    cost_task: float,
    seconds_task: int,
    wall: int,
    multiplier: float,
) -> dict[str, Any]:
    """Scale all six caps (and the wall) by the profile multiplier."""
    if multiplier == 1.0:
        return {
            "tokens": tokens,
            "cost": cost,
            "seconds": seconds,
            "cost_task": cost_task,
            "seconds_task": seconds_task,
            "wall": wall,
        }
    return {
        "tokens": round(tokens * multiplier),
        "cost": cost * multiplier,
        "seconds": round(seconds * multiplier),
        "cost_task": cost_task * multiplier,
        "seconds_task": round(seconds_task * multiplier),
        "wall": round(wall * multiplier),
    }
