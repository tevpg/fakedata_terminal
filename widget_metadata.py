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
WIDGET_METADATA_PATH = PACKAGE_DIR / "data" / "widgets.yaml"
KNOWN_MODIFIERS = {"speed", "theme", "text", "color", "direction", "image", "cycle"}
PUBLIC_WIDGETS = {
    "text", "text_wide", "text_scant", "text_spew", "image", "life",
    "bars", "crash", "gauge", "matrix", "orbit", "rotate", "scope", "blocks", "spiral", "sweep", "tunnel",
    "sparkline", "readouts", "blank", "cycle",
}
ALL_WIDGETS = PUBLIC_WIDGETS

_ACTIVE_CONFIG_PATHS: tuple[str, ...] = ()


def set_widget_config_paths(config_paths: tuple[str, ...] | None) -> None:
    global _ACTIVE_CONFIG_PATHS
    _ACTIVE_CONFIG_PATHS = _normalize_config_paths(config_paths)
    _load_widget_metadata_cached.cache_clear()


def _normalize_config_paths(config_paths: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if not config_paths:
        return ()
    normalized = []
    for path in config_paths:
        normalized.append(str(Path(path).expanduser().resolve()))
    return tuple(normalized)


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


def _load_widget_overlay(path: str) -> dict[str, Any]:
    overlay_path = Path(path)
    try:
        with overlay_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError:
        return {}
    if not isinstance(data, dict):
        return {}

    overlay: dict[str, Any] = {}
    defaults = data.get("defaults")
    if isinstance(defaults, dict):
        overlay["defaults"] = defaults
    widgets = data.get("widgets")
    if isinstance(widgets, dict):
        overlay["widgets"] = widgets
    return overlay


def _effective_config_paths(config_paths: tuple[str, ...] | list[str] | None = None) -> tuple[str, ...]:
    normalized = _normalize_config_paths(config_paths)
    if not normalized:
        normalized = _ACTIVE_CONFIG_PATHS

    packaged = str(WIDGET_METADATA_PATH.resolve())
    ordered = [packaged]
    for path in normalized:
        if path == packaged:
            continue
        ordered.append(path)
    return tuple(ordered)


@lru_cache(maxsize=None)
def _load_widget_metadata_cached(effective_paths: tuple[str, ...]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in effective_paths:
        merged = _merge_dicts(merged, _load_widget_overlay(path))
    return merged


def load_widget_metadata(config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    return _load_widget_metadata_cached(_effective_config_paths(config_paths))


def widget_catalog(config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, dict[str, Any]]:
    widgets = load_widget_metadata(config_paths).get("widgets")
    return widgets if isinstance(widgets, dict) else {}


def widget_root_defaults(config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    defaults = load_widget_metadata(config_paths).get("defaults")
    return defaults if isinstance(defaults, dict) else {}


def widget_metadata(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    entry = widget_catalog(config_paths).get(widget)
    return entry if isinstance(entry, dict) else {}


def widget_enabled(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> bool:
    entry = widget_metadata(widget, config_paths)
    enabled = entry.get("enabled")
    return enabled if isinstance(enabled, bool) else True


def public_widget_names() -> list[str]:
    return sorted(PUBLIC_WIDGETS)


def widget_supports(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> list[str]:
    entry = widget_metadata(widget, config_paths)
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
    return []


def widget_defaults(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    entry = widget_metadata(widget, config_paths)
    defaults = entry.get("defaults")
    return defaults if isinstance(defaults, dict) else {}


def widget_timing_defaults(config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    timing = widget_root_defaults(config_paths).get("timing")
    return timing if isinstance(timing, dict) else {}


def widget_timing(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    timing = widget_metadata(widget, config_paths).get("timing")
    return timing if isinstance(timing, dict) else {}


def widget_behavior(widget: str, config_paths: tuple[str, ...] | list[str] | None = None) -> dict[str, Any]:
    behavior = widget_metadata(widget, config_paths).get("behavior")
    return behavior if isinstance(behavior, dict) else {}


def validate_widget_metadata(config_paths: tuple[str, ...] | list[str] | None = None) -> list[str]:
    issues: list[str] = []
    catalog = load_widget_metadata(config_paths)
    if not isinstance(catalog, dict):
        return [f"{WIDGET_METADATA_PATH.name}: root must be a mapping"]

    widgets = catalog.get("widgets")
    if not isinstance(widgets, dict):
        return [f"{WIDGET_METADATA_PATH.name}: widgets must be a mapping"]

    defaults = catalog.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        issues.append(f"{WIDGET_METADATA_PATH.name}: defaults must be a mapping")
    elif isinstance(defaults, dict):
        timing = defaults.get("timing")
        if timing is not None and not isinstance(timing, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: defaults.timing must be a mapping")

    for widget in sorted(ALL_WIDGETS):
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
        timing = entry.get("timing")
        if timing is not None and not isinstance(timing, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.timing must be a mapping")
        behavior = entry.get("behavior")
        if behavior is not None and not isinstance(behavior, dict):
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget}.behavior must be a mapping")

    for widget, entry in widgets.items():
        widget_name = str(widget)
        if widget_name not in ALL_WIDGETS:
            issues.append(f"{WIDGET_METADATA_PATH.name}: widgets.{widget_name} is not a supported widget name")
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
