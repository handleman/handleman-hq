"""Deterministic design checks (057 AC-5): tokens, regions, screenshot diff."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageColor

DEFAULT_AC = "AC-D"


class DesignCheckError(ValueError):
    pass


def load_checks(spec_dir: Path) -> dict[str, Any] | None:
    path = Path(spec_dir) / "design.toml"
    if not path.is_file():
        return None
    try:
        return tomllib.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise DesignCheckError(f"design.toml is unreadable: {exc}") from exc


def _norm(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if text.startswith("#") and len(text) in {4, 7, 9}:
        return text.lower()
    return " ".join(text.split())


_RGB_RE = re.compile(
    r"^rgba?\(\s*(\d{1,3})[ ,]+(\d{1,3})[ ,]+(\d{1,3})(?:\s*[,/]\s*([0-9.]+))?\s*\)$",
    re.IGNORECASE,
)


def _color(value: Any) -> tuple[int, ...] | None:
    """Parse a CSS colour into RGBA; None when the value is not a colour."""
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        rgb = ImageColor.getrgb(text)
    except (ValueError, TypeError):
        match = _RGB_RE.match(text)
        if not match:
            return None
        rgb = tuple(int(part) for part in match.groups()[:3])
        alpha = match.group(4)
        if alpha is not None:
            rgb = rgb + (round(float(alpha) * 255),)
    if len(rgb) == 3:
        return tuple(int(channel) for channel in rgb) + (255,)
    return tuple(int(channel) for channel in rgb)


def _same_value(expected: Any, actual: Any) -> bool:
    """Compare tokens semantically: shorthand hex/rgb colours are equal."""
    if _norm(expected) == _norm(actual):
        return True
    left = _color(expected)
    right = _color(actual)
    return left is not None and right is not None and left == right


def _rect(value: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        return {key: float(value.get(key, 0) or 0) for key in ("x", "y", "w", "h")}
    except (TypeError, ValueError):
        return None


def _diff_fraction(baseline: Path, actual: Path) -> float:
    with Image.open(baseline) as left, Image.open(actual) as right:
        a = left.convert("RGB")
        b = right.convert("RGB")
        if a.size != b.size:
            b = b.resize(a.size)
        diff = ImageChops.difference(a, b)
        pixels = list(diff.getdata())
    changed = sum(1 for pixel in pixels if max(pixel) > 12)
    return changed / max(1, len(pixels))


def evaluate(
    checks: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    root: Path,
) -> list[dict[str, Any]]:
    """`facts` = {"tokens": {name: value}, "regions": {id: rect}, "screenshots": {frame: path}}."""
    issues: list[dict[str, Any]] = []
    tokens = facts.get("tokens") or {}
    for entry in checks.get("token") or []:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", "")).strip()
        expected = entry.get("value")
        actual = tokens.get(name)
        if actual is None:
            issues.append(
                {"check": "design_token", "target": name, "detail": "not found", "ac": str(entry.get("ac", DEFAULT_AC))}
            )
        elif not _same_value(expected, actual):
            issues.append(
                {
                    "check": "design_token",
                    "target": name,
                    "detail": f"{actual!r} != {expected!r}",
                    "ac": str(entry.get("ac", DEFAULT_AC)),
                }
            )
    regions = facts.get("regions") or {}
    for entry in checks.get("region") or []:
        if not isinstance(entry, Mapping):
            continue
        rid = str(entry.get("id", "")).strip()
        actual = _rect(regions.get(rid))
        ac = str(entry.get("ac", DEFAULT_AC))
        if actual is None:
            issues.append({"check": "design_region", "target": rid, "detail": "not found", "ac": ac})
            continue
        expected = _rect({key: entry.get(key) for key in ("x", "y", "w", "h")}) if any(
            entry.get(key) is not None for key in ("x", "y", "w", "h")
        ) else None
        if expected is None:
            continue
        tol = float(entry.get("tolerance_px", 2) or 2)
        delta = max(abs(actual[key] - expected[key]) for key in ("x", "y", "w", "h"))
        if delta > tol:
            issues.append(
                {
                    "check": "design_region",
                    "target": rid,
                    "detail": f"delta {delta:.1f}px > {tol}px ({actual} vs {expected})",
                    "ac": ac,
                }
            )
    shot = checks.get("screenshot") or {}
    if isinstance(shot, Mapping) and shot.get("baseline"):
        frame = str(shot.get("frame", "desktop"))
        actual_path = (facts.get("screenshots") or {}).get(frame)
        baseline = Path(root) / str(shot["baseline"])
        ac = str(shot.get("ac", DEFAULT_AC))
        if not actual_path:
            issues.append({"check": "design_screenshot", "target": frame, "detail": "no screenshot", "ac": ac})
        elif not baseline.is_file():
            issues.append(
                {"check": "design_screenshot", "target": str(baseline), "detail": "baseline missing", "ac": ac}
            )
        else:
            try:
                fraction = _diff_fraction(baseline, Path(actual_path))
            except OSError as exc:
                issues.append(
                    {"check": "design_screenshot", "target": frame, "detail": f"unreadable: {exc}", "ac": ac}
                )
            else:
                threshold = float(shot.get("threshold", 0.02) or 0.02)
                if fraction > threshold:
                    issues.append(
                        {
                            "check": "design_screenshot",
                            "target": frame,
                            "detail": f"{fraction:.2%} > {threshold:.2%}",
                            "ac": ac,
                        }
                    )
    return issues
