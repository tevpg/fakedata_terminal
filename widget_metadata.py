"""Widget metadata loader for capability/help validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import subprocess
import sys
from typing import Any

if sys.platform == "win32":
    try:
        import yaml
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml"],
            stdout=subprocess.DEVNULL,
        )
        import yaml
else:
    import yaml


PACKAGE_DIR = Path(__file__).resolve().parent
WIDGET_METADATA_PATH = PACKAGE_DIR / "widgets.yaml"
KNOWN_MODIFIERS = {"speed", "theme", "text", "color", "direction", "image", "cycle"}
PUBLIC_WIDGETS = {
    "text", "text_wide", "text_scant", "text_spew", "image", "life",
    "bars", "gauge", "matrix", "scope", "blocks", "sweep", "tunnel",
    "sparkline", "readouts", "blank", "cycle",
}
INTERNAL_WIDGETS = {"gauges"}
ALL_WIDGETS = PUBLIC_WIDGETS | INTERNAL_WIDGETS
LEGACY_SUPPORTS = {
    "bars": ["speed", "theme", "text"],
    "blank": ["text", "color"],
    "blocks": ["speed", "color", "direction", "text"],
    "cycle": ["speed", "theme", "color", "cycle"],
    "gauge": ["speed", "color", "text", "direction"],
    "gauges": ["speed", "theme", "text", "color"],
    "image": ["speed", "image"],
    "life": ["speed", "color"],
    "matrix": ["speed"],
    "readouts": ["theme", "text", "color"],
    "scope": ["speed", "theme", "text", "direction"],
    "sparkline": ["speed", "theme", "text", "direction"],
    "sweep": ["speed"],
    "text": ["speed", "theme", "text", "direction"],
    "text_scant": ["speed", "theme", "text", "direction"],
    "text_spew": ["speed", "theme", "text"],
    "text_wide": ["speed", "theme", "text", "direction"],
    "tunnel": ["speed", "color", "text", "direction"],
}


@lru_cache(maxsize=1)
def load_widget_metadata() -> dict[str, Any]:
    try:
        with WIDGET_METADATA_PATH.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError:
        data = {}
    return data if isinstance(data, dict) else {}


def widget_catalog() -> dict[str, dict[str, Any]]:
    widgets = load_widget_metadata().get("widgets")
    return widgets if isinstance(widgets, dict) else {}


def widget_metadata(widget: str) -> dict[str, Any]:
    entry = widget_catalog().get(widget)
    return entry if isinstance(entry, dict) else {}


def widget_enabled(widget: str) -> bool:
    entry = widget_metadata(widget)
    enabled = entry.get("enabled")
    return enabled if isinstance(enabled, bool) else True


def widget_supports(widget: str) -> list[str]:
    entry = widget_metadata(widget)
    supports = entry.get("supports")
    if isinstance(supports, list):
        normalized: list[str] = []
        seen = set()
        for item in supports:
            name = str(item).strip().lower()
            if name not in KNOWN_MODIFIERS or name in seen:
                continue
            seen.add(name)
            normalized.append(name)
        if normalized:
            return normalized
    return LEGACY_SUPPORTS.get(widget, ["speed"])


def validate_widget_metadata() -> list[str]:
    issues: list[str] = []
    catalog = load_widget_metadata()
    if not isinstance(catalog, dict):
        return [f"{WIDGET_METADATA_PATH.name}: root must be a mapping"]

    widgets = catalog.get("widgets")
    if not isinstance(widgets, dict):
        return [f"{WIDGET_METADATA_PATH.name}: widgets must be a mapping"]

    for widget in sorted(PUBLIC_WIDGETS):
        entry = widgets.get(widget)
        if not isinstance(entry, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget} must be a mapping")
            continue
        if not isinstance(entry.get("enabled"), bool):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.enabled must be true or false")
        supports = entry.get("supports")
        if not isinstance(supports, list) or not supports:
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.supports must be a non-empty list")
        elif any(str(item).strip().lower() not in KNOWN_MODIFIERS for item in supports):
            issues.append(
                f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.supports contains an unknown modifier"
            )
        defaults = entry.get("defaults")
        if defaults is not None and not isinstance(defaults, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.defaults must be a mapping")

    for widget, entry in widgets.items():
        widget_name = str(widget)
        if widget_name not in ALL_WIDGETS:
            continue
        if not isinstance(entry, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget_name} must be a mapping")
            continue
        supports = entry.get("supports")
        if supports is not None and not isinstance(supports, list):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget_name}.supports must be a list")
        defaults = entry.get("defaults")
        if defaults is not None and not isinstance(defaults, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget_name}.defaults must be a mapping")

    return issues
