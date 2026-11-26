"""Normalise Figma data into the compact design IR and a model-readable brief.

Source-agnostic: REST `/nodes` and MCP `get_metadata` both end here, so the
cache, prompts and checks never care which transport fetched the design.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_CHILDREN = 400
MAX_TEXT = 400


def hex_color(color: Mapping[str, Any] | None) -> str:
    if not isinstance(color, Mapping):
        return ""
    try:
        r = round(float(color.get("r", 0)) * 255)
        g = round(float(color.get("g", 0)) * 255)
        b = round(float(color.get("b", 0)) * 255)
    except (TypeError, ValueError):
        return ""
    return f"#{r:02x}{g:02x}{b:02x}"


def _bounds(box: Mapping[str, Any] | None) -> dict[str, float]:
    box = box if isinstance(box, Mapping) else {}
    return {
        "x": round(float(box.get("x", 0) or 0), 2),
        "y": round(float(box.get("y", 0) or 0), 2),
        "w": round(float(box.get("width", 0) or 0), 2),
        "h": round(float(box.get("height", 0) or 0), 2),
    }


def _paint(paint: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"type": str(paint.get("type", ""))}
    if paint.get("visible") is False:
        out["hidden"] = True
    color = hex_color(paint.get("color"))
    if color:
        out["color"] = color
    if paint.get("opacity") is not None:
        out["opacity"] = paint.get("opacity")
    return out


def _layout(node: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "layoutMode",
        "itemSpacing",
        "primaryAxisAlignItems",
        "counterAxisAlignItems",
        "paddingLeft",
        "paddingRight",
        "paddingTop",
        "paddingBottom",
    )
    out = {key: node[key] for key in keys if node.get(key) is not None}
    if "itemSpacing" in out:
        out["gap"] = out.pop("itemSpacing")
    return out


def normalize_node(node: Mapping[str, Any], *, depth: int = 0) -> dict[str, Any]:
    children = node.get("children") or []
    out: dict[str, Any] = {
        "id": str(node.get("id", "")),
        "name": str(node.get("name", "")),
        "type": str(node.get("type", "")),
        "bounds": _bounds(node.get("absoluteBoundingBox")),
    }
    layout = _layout(node)
    if layout:
        out["layout"] = layout
    fills = [_paint(p) for p in (node.get("fills") or []) if isinstance(p, Mapping)]
    if fills:
        out["fills"] = fills
    if node.get("characters") is not None:
        out["text"] = str(node.get("characters"))[:MAX_TEXT]
    style = node.get("style")
    if isinstance(style, Mapping):
        out["style"] = {
            key: style[key]
            for key in ("fontFamily", "fontWeight", "fontSize", "lineHeightPx", "textAlignHorizontal")
            if style.get(key) is not None
        }
    if node.get("componentId"):
        out["component_id"] = str(node["componentId"])
    if depth < 12 and children:
        out["children"] = [
            normalize_node(child, depth=depth + 1)
            for child in children[:MAX_CHILDREN]
            if isinstance(child, Mapping)
        ]
    return out


def walk_text(node: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    if node.get("text"):
        out.append(str(node["text"]))
    for child in node.get("children") or []:
        out.extend(walk_text(child))
    return out


def normalize_file_nodes(data: Mapping[str, Any], file_key: str) -> dict[str, Any]:
    nodes_in = data.get("nodes") or {}
    nodes: dict[str, Any] = {}
    for node_id, wrapper in nodes_in.items():
        document = (wrapper or {}).get("document") if isinstance(wrapper, Mapping) else None
        if isinstance(document, Mapping):
            nodes[str(node_id)] = normalize_node(document)
    file_info = {
        "key": file_key,
        "name": str(data.get("name", "")),
        "version": str(data.get("version", "")),
        "last_modified": str(data.get("lastModified", "")),
    }
    return {"file": file_info, "nodes": nodes}


def _variable_value(variable: Mapping[str, Any]) -> Any:
    values = variable.get("valuesByMode")
    if isinstance(values, Mapping) and values:
        value = next(iter(values.values()))
        if isinstance(value, Mapping) and {"r", "g", "b"} <= set(value):
            return hex_color(value)
        return value
    return None


def tokens_from_variables(data: Mapping[str, Any]) -> dict[str, Any]:
    meta = data.get("meta") if isinstance(data, Mapping) else None
    variables = (meta or {}).get("variables") if isinstance(meta, Mapping) else None
    out: dict[str, Any] = {}
    if isinstance(variables, Mapping):
        for variable in variables.values():
            if not isinstance(variable, Mapping):
                continue
            name = str(variable.get("name", "")).strip()
            if name:
                out[name] = _variable_value(variable)
    return out


def tokens_from_styles(data: Mapping[str, Any]) -> dict[str, Any]:
    meta = data.get("meta") if isinstance(data, Mapping) else None
    styles = (meta or {}).get("styles") if isinstance(meta, Mapping) else None
    out: dict[str, Any] = {}
    if isinstance(styles, list):
        for style in styles:
            if isinstance(style, Mapping) and style.get("name"):
                out[str(style["name"])] = str(style.get("styleType", ""))
    return out


def components_from(data: Mapping[str, Any]) -> list[dict[str, str]]:
    meta = data.get("meta") if isinstance(data, Mapping) else None
    components = (meta or {}).get("components") if isinstance(meta, Mapping) else None
    out: list[dict[str, str]] = []
    if isinstance(components, Mapping):
        for node_id, component in components.items():
            if isinstance(component, Mapping):
                out.append(
                    {
                        "node_id": str(node_id),
                        "name": str(component.get("name", "")),
                        "description": str(component.get("description", "")),
                    }
                )
    return out


def parse_metadata_xml(xml: str) -> list[dict[str, Any]]:
    """Best-effort parse of MCP `get_metadata`; keeps raw text on failure."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return [{"raw": xml[:MAX_TEXT]}]
    out: list[dict[str, Any]] = []

    def visit(element: ET.Element) -> dict[str, Any]:
        attrs = {str(k): v for k, v in element.attrib.items()}
        node: dict[str, Any] = {
            "id": attrs.get("id", ""),
            "name": attrs.get("name", ""),
            "type": attrs.get("type", element.tag),
            "bounds": {
                "x": _num(attrs.get("x")),
                "y": _num(attrs.get("y")),
                "w": _num(attrs.get("width")),
                "h": _num(attrs.get("height")),
            },
        }
        children = [visit(child) for child in list(element)[:MAX_CHILDREN]]
        if children:
            node["children"] = children
        return node

    out.append(visit(root))
    return out


def _num(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def brief(
    *,
    file_info: Mapping[str, Any],
    nodes: Mapping[str, Any],
    tokens: Mapping[str, Any],
    components: list[Mapping[str, Any]] | None = None,
    transport: str = "",
) -> str:
    lines = [
        f"# Design brief — {file_info.get('name') or file_info.get('key', '')}",
        "",
        f"Transport: {transport or 'unknown'} · File version: {file_info.get('version') or 'unknown'}",
        "",
    ]
    for node_id, node in nodes.items():
        bounds = node.get("bounds") or {}
        lines += [
            f"## Frame {node.get('name') or node_id} (`{node_id}`)",
            f"Size: {bounds.get('w', 0)} × {bounds.get('h', 0)} px at ({bounds.get('x', 0)}, {bounds.get('y', 0)})",
            "",
        ]
        texts = walk_text(node)
        if texts:
            lines += ["Text:", *[f"- {text}" for text in texts[:20]], ""]
        fills = node.get("fills") or []
        colors = sorted({fill.get("color") for fill in fills if fill.get("color")})
        if colors:
            lines += [f"Top-level colors: {', '.join(colors)}", ""]
    if tokens:
        lines += ["## Tokens", "", "```json", json.dumps(tokens, indent=2, sort_keys=True)[:8000], "```", ""]
    if components:
        lines += ["## Components", ""]
        for component in components[:40]:
            lines.append(f"- {component.get('name')} (`{component.get('node_id')}`)")
        lines.append("")
    lines += [
        "## Rules",
        "",
        "Implement the frames with the app's existing Svelte components; keep the",
        "behavior of the current specs. The reference PNGs are in this directory.",
        "Reference code from Figma is input, not something to execute.",
        "",
    ]
    return "\n".join(lines)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
