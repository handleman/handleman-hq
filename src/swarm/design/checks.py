"""Deterministic design checks (057 AC-5): tokens, regions, screenshot diff."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Mapping
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


def _crop(image: Image.Image, x: float, y: float, w: float, h: float) -> Image.Image:
    width, height = image.size
    left = max(0, min(width, round(x)))
    top = max(0, min(height, round(y)))
    right = max(left + 1, min(width, round(x + w)))
    bottom = max(top + 1, min(height, round(y + h)))
    return image.crop((left, top, right, bottom))


def _mask(image: Image.Image, masks: Iterable[Mapping[str, Any]]) -> None:
    """Paint masked areas black on both sides, so they cannot change the score."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    width, height = image.size
    for raw in masks or ():
        rect = _rect(raw) or {}
        x = float(rect.get("x", 0) or 0)
        y = float(rect.get("y", 0) or 0)
        w = float(rect.get("w", 0) or 0)
        h = float(rect.get("h", 0) or 0)
        if w <= 0 or h <= 0:
            continue
        left = max(0, min(width, round(x)))
        top = max(0, min(height, round(y)))
        right = max(left, min(width, round(x + w)))
        bottom = max(top, min(height, round(y + h)))
        if right > left and bottom > top:
            draw.rectangle((left, top, right, bottom), fill=(0, 0, 0))


def _similarity(
    actual: Image.Image,
    baseline: Image.Image,
    entry: Mapping[str, Any],
) -> float:
    """Fraction of matching pixels in the configured region (0..1)."""
    width, height = actual.size
    has_region = any(entry.get(key) is not None for key in ("x", "y", "w", "h"))
    if has_region:
        x = float(entry.get("x", 0) or 0)
        y = float(entry.get("y", 0) or 0)
        w = float(entry.get("w", width) or width)
        h = float(entry.get("h", height) or height)
        actual = _crop(actual, x, y, w, h)
        baseline = _crop(baseline, x, y, w, h)
    masks = entry.get("mask") or []
    if isinstance(masks, Mapping):
        masks = [masks]
    _mask(actual, masks)
    _mask(baseline, masks)
    diff = ImageChops.difference(actual, baseline)
    pixels = list(diff.getdata())
    changed = sum(1 for pixel in pixels if max(pixel) > 12)
    return 1.0 - (changed / max(1, len(pixels)))


def evaluate_visual(
    checks: Mapping[str, Any],
    shots: Mapping[str, str],
    *,
    root: Path,
) -> list[dict[str, Any]]:
    """062: compare the rendered screenshot to the Figma reference by region.

    `shots` is the acceptance screenshot map (`desktop`/`mobile` → path); the
    baseline is a design-cache render. A spec declares `[[visual]]` entries with
    `frame`, `baseline`, optional `x/y/w/h` and `mask`, and `min_similarity`
    (default 0.90). This catches a missing pill or a removed control that the
    token/rect checks cannot see; live map tiles are excluded by region.
    """
    issues: list[dict[str, Any]] = []
    entries = checks.get("visual") or []
    if isinstance(entries, Mapping):
        entries = [entries]
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        frame = str(entry.get("frame", "mobile"))
        label = str(entry.get("id") or frame)
        ac = str(entry.get("ac", DEFAULT_AC))
        actual_value = str(entry.get("actual") or "").strip()
        actual_path = (
            str(Path(root) / actual_value)
            if actual_value
            else (shots or {}).get(frame)
        )
        baseline_value = str(entry.get("baseline") or "").strip()
        raw_threshold = entry.get("min_similarity", 0.90)
        try:
            threshold = float(raw_threshold)
        except (TypeError, ValueError):
            threshold = 0.90
        if threshold > 1.0:
            threshold = threshold / 100.0
        threshold = max(0.0, min(1.0, threshold))
        if not actual_path:
            issues.append(
                {
                    "check": "design_visual",
                    "target": label,
                    "detail": f"no {frame} screenshot",
                    "ac": ac,
                }
            )
            continue
        baseline = Path(root) / baseline_value if baseline_value else Path("")
        if not baseline_value or not baseline.is_file():
            issues.append(
                {
                    "check": "design_visual",
                    "target": label,
                    "detail": f"baseline missing: {baseline_value or '(none)'}",
                    "ac": ac,
                }
            )
            continue
        try:
            with Image.open(Path(actual_path)) as actual_image, Image.open(baseline) as base_image:
                actual = actual_image.convert("RGB")
                reference = base_image.convert("RGB")
                if reference.size != actual.size:
                    reference = reference.resize(actual.size)
                similarity = _similarity(actual, reference, entry)
        except OSError as exc:
            issues.append(
                {
                    "check": "design_visual",
                    "target": label,
                    "detail": f"unreadable: {exc}",
                    "ac": ac,
                }
            )
            continue
        if similarity + 1e-9 < threshold:
            issues.append(
                {
                    "check": "design_visual",
                    "target": label,
                    "detail": f"similarity {similarity:.1%} < {threshold:.1%}",
                    "ac": ac,
                    "similarity": round(similarity, 4),
                    "threshold": threshold,
                }
            )
    return issues


def evaluate(
    checks: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    root: Path,
) -> list[dict[str, Any]]:
    """Token/region/screenshot checks (057); visual parity is `evaluate_visual`."""
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
