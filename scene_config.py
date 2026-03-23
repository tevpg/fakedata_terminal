"""Load YAML screen definitions, merge overlays, and adapt them to the runtime."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
import glob
import math
import os
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

try:
    from .runtime_support import COLOUR_CHOICES, normalize_colour_spec
    from .widget_metadata import public_widget_names, widget_defaults as widget_metadata_defaults, widget_enabled, widget_supports
except ImportError:
    from runtime_support import COLOUR_CHOICES, normalize_colour_spec
    from widget_metadata import public_widget_names, widget_defaults as widget_metadata_defaults, widget_enabled, widget_supports


PACKAGE_DIR = Path(__file__).resolve().parent
LAYOUT_CONFIG_PATH = PACKAGE_DIR / "data" / "layouts.yaml"
SCREEN_CONFIG_PATH = PACKAGE_DIR / "data" / "screens.yaml"
WIDGET_CONFIG_PATH = PACKAGE_DIR / "data" / "widgets.yaml"
WIDGET_SHOWCASE_CONFIG_PATH = PACKAGE_DIR / "data" / "widget_showcase.yaml"
PACKAGE_CONFIG_PATHS = (
    LAYOUT_CONFIG_PATH,
    WIDGET_CONFIG_PATH,
    WIDGET_SHOWCASE_CONFIG_PATH,
    SCREEN_CONFIG_PATH,
)
USER_CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fakedata-terminal" / "screens.yaml"
PROJECT_CONFIG_NAMES = (
    ".fakedata-terminal.yaml",
    ".fakedata-terminal.yml",
)

TOP_LEVEL_KEYS = {"defaults", "layouts", "screens", "widget_showcase", "widgets"}
DEFAULT_KEYS = {"theme", "speed", "image", "widget", "colour", "color", "glitch", "direction", "timing"}
LAYOUT_KEYS = {"panels", "regions"}
PANEL_KEYS = {"x", "y", "w", "h"}
SCENE_KEYS = {"note", "layout", "theme", "speed", "density", "text", "regions", "colour", "color", "glitch", "direction"}
REGION_KEYS = {"widget", "speed", "density", "text", "theme", "image", "paths", "path", "glob", "cycle", "colour", "color", "direction"}
IMAGE_KEYS = {"paths", "path", "glob"}
CYCLE_KEYS = {"widgets"}
WIDGET_DEFAULT_KEYS = REGION_KEYS - {"widget"}
WIDGET_SHOWCASE_KEYS = {"pages"}
WIDGET_SHOWCASE_PAGE_KEYS = {
    "widget", "note", "speed", "density", "theme", "text", "colour", "color", "direction", "image", "cycle",
}
CANONICAL_DIRECTION_CHOICES = {"forward", "backward", "random", "none"}
_DIRECTION_ALIASES = {
    "forward": "forward",
    "backward": "backward",
    "random": "random",
    "none": "none",
}
DIRECTION_CHOICES = set(_DIRECTION_ALIASES)
VALID_COLOUR_VALUES = {normalize_colour_spec(choice) for choice in COLOUR_CHOICES}

LEGACY_LAYOUT_ALIASES = {
    "grid_2x2": "2x2",
    "grid_3x3": "3x3",
    "grid_4x3": "4x3",
    "grid_3x2": "3x2",
    "main_2x2_right_stack_3": "L2x2_R3",
    "main_2x2_left_stack_3": "L3_R2x2",
    "left_stack_2_right_grid_3x3": "L2_R3x3",
    "left_stack_3_middle_stack_3_right_stack_2": "L3_M3_R2",
    "left_grid_3x3_right_stack_2": "L3x3_R2",
}

LEGACY_REGION_ALIASES = {
    "2x2": {
        "left": "L",
        "right": "R",
        "top": "T",
        "bottom": "B",
    },
    "3x3": {
        "left": "L",
        "center": "C",
        "right": "R",
        "large_left": "L2",
        "large_right": "R2",
        "top": "T",
        "middle": "M",
        "bottom": "B",
    },
    "4x3": {
        "left": "L",
        "center_left": "C1",
        "center_right": "C2",
        "right": "R",
        "top": "T",
        "middle": "M",
        "bottom": "B",
    },
    "L2x2_R3": {
        "main": "L2x2",
        "right": "R",
        "right_top": "UR",
        "right_mid": "RM",
        "right_bottom": "LR",
    },
    "L3_R2x2": {
        "left": "L",
        "left_top": "UL",
        "left_mid": "LM",
        "left_bottom": "LL",
        "main": "R2x2",
    },
    "L2_R3x3": {
        "left": "L",
        "left_top": "UL",
        "left_bottom": "LL",
        "right": "R",
        "right_left": "R1",
        "right_center": "RC",
        "right_right": "R2",
    },
    "L3_M3_R2": {
        "left": "L",
        "left_top": "UL",
        "left_mid": "LM",
        "left_bottom": "LL",
        "middle": "M",
        "middle_top": "MT",
        "middle_mid": "C",
        "middle_bottom": "MB",
        "right": "R",
        "right_top": "UR",
        "right_bottom": "LR",
    },
    "L3x3_R2": {
        "left": "L",
        "left_left": "L1",
        "left_center": "LC",
        "left_right": "L2",
        "right": "R",
        "right_top": "UR",
        "right_bottom": "LR",
    },
    "3x2": {
        "main": "L2x2",
        "right": "R",
        "right_top": "UR",
        "right_bottom": "LR",
    },
}


def discover_config_paths() -> list[Path]:
    paths = [path for path in PACKAGE_CONFIG_PATHS if path.is_file()]
    if USER_CONFIG_PATH.is_file():
        paths.append(USER_CONFIG_PATH)
    cwd = Path.cwd()
    for name in PROJECT_CONFIG_NAMES:
        candidate = cwd / name
        if candidate.is_file():
            paths.append(candidate)
            break
    return paths


def _normalize_config_paths(config_paths: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if config_paths is None:
        paths = discover_config_paths()
    else:
        paths = [Path(path).expanduser() for path in config_paths]
    normalized = []
    for path in paths:
        resolved = Path(path).resolve()
        normalized.append(str(resolved))
    return tuple(normalized)


def _load_catalog_file(config_path: str) -> dict[str, Any]:
    path = Path(config_path)
    if not path.is_file():
        raise ValueError(f"Screen config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Screen config root must be a mapping: {path}")
    return _normalize_catalog_paths(data, path)


def _merge_catalogs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_catalogs(existing, value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=None)
def load_scene_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    normalized_paths = _normalize_config_paths(config_paths)
    catalog: dict[str, Any] = {}
    for config_path in normalized_paths:
        catalog = _merge_catalogs(catalog, _load_catalog_file(config_path))
    return catalog


def config_screen_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    screens = catalog.get("screens", {})
    if not isinstance(screens, dict):
        return []
    return list(screens.keys())


def config_scene_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return config_screen_names(config_paths)


def layout_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    if not isinstance(layouts, dict):
        return []
    return list(layouts.keys())


def _match_name(value: Any, names: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text in names:
        return text
    folded = text.casefold()
    for name in names:
        name_text = str(name)
        if name_text.casefold() == folded:
            return name_text
    return None


def canonical_layout_name(layout_name: Any, config_paths: tuple[str, ...] | None = None) -> str | None:
    layouts = layout_catalog(config_paths)
    matched = _match_name(layout_name, layouts)
    if matched is not None:
        return matched
    legacy_name = _match_name(layout_name, LEGACY_LAYOUT_ALIASES)
    if legacy_name is None:
        return None
    canonical = LEGACY_LAYOUT_ALIASES[legacy_name]
    return canonical if canonical in layouts else None


def _canonical_panel_name(panel_name: Any, panels: dict[str, Any]) -> str | None:
    return _match_name(panel_name, panels)


def _canonical_region_alias(layout_name: str, region_name: Any, aliases: dict[str, Any]) -> str | None:
    matched = _match_name(region_name, aliases)
    if matched is not None:
        return matched
    legacy_aliases = LEGACY_REGION_ALIASES.get(layout_name, {})
    legacy_name = _match_name(region_name, legacy_aliases)
    if legacy_name is None:
        return None
    canonical = legacy_aliases[legacy_name]
    return canonical if canonical in aliases else None


def normalize_region_expr(layout_name: Any, region_expr: Any,
                          config_paths: tuple[str, ...] | None = None) -> str | None:
    canonical_layout = canonical_layout_name(layout_name, config_paths)
    if canonical_layout is None:
        return None
    layouts = layout_catalog(config_paths)
    layout_cfg = layouts.get(canonical_layout)
    if not isinstance(layout_cfg, dict):
        return None
    return _normalize_region_expr_in_layout(canonical_layout, layout_cfg, region_expr)


def _normalize_region_expr_in_layout(layout_name: str, layout_cfg: dict[str, Any], region_expr: Any) -> str | None:
    panels = layout_cfg.get("panels", {})
    aliases = layout_cfg.get("regions", {})
    alias_name = _canonical_region_alias(layout_name, region_expr, aliases)
    spec = aliases[alias_name] if alias_name is not None else region_expr
    panel_names = [part.strip() for part in str(spec).split("+") if part.strip()]
    if not panel_names:
        return None

    canonical_panels = []
    for panel_name in panel_names:
        canonical_panel = _canonical_panel_name(panel_name, panels)
        if canonical_panel is None:
            return None
        canonical_panels.append(canonical_panel)
    ordered_panels = sorted(
        canonical_panels,
        key=lambda name: (
            float(panels[name].get("y", 0.0)),
            float(panels[name].get("x", 0.0)),
            str(name),
        ),
    )
    return "+".join(ordered_panels)


def layout_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    return layouts if isinstance(layouts, dict) else {}


def widget_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    del config_paths
    return public_widget_names()


def widget_defaults_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    return {
        widget_name: dict(widget_metadata_defaults(widget_name, config_paths))
        for widget_name in public_widget_names()
        if widget_metadata_defaults(widget_name, config_paths)
    }


def widget_showcase_pages(config_paths: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    catalog = load_scene_catalog(config_paths)
    showcase = catalog.get("widget_showcase", {})
    if not isinstance(showcase, dict):
        return []
    pages = showcase.get("pages", [])
    if not isinstance(pages, list):
        return []
    normalized_pages = []
    for page_cfg in pages:
        if isinstance(page_cfg, dict):
            normalized_pages.append(page_cfg)
    return normalized_pages


def default_image_paths(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    defaults = catalog.get("defaults", {})
    if not isinstance(defaults, dict):
        return []
    return _expand_image_spec(defaults.get("image"))


def config_defaults(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    defaults = catalog.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}
    color = defaults.get("color")
    if color is None:
        color = defaults.get("colour")
    return {
        "theme": defaults.get("theme", "science"),
        "speed": defaults.get("speed", 50),
        "widget": defaults.get("widget"),
        "color": color,
        "image": defaults.get("image"),
        "glitch": defaults.get("glitch", 0.0),
        "direction": _direction_value(defaults.get("direction")) or "forward",
    }


def _direction_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return _DIRECTION_ALIASES.get(text)


def _color_value(value: Any) -> str | None:
    if value is None:
        return None
    normalized = normalize_colour_spec(str(value))
    return normalized if normalized in VALID_COLOUR_VALUES else None


def _speed_issues(value: Any, label: str, issues: list[str]) -> None:
    if value is None:
        return
    try:
        number = int(value)
    except (TypeError, ValueError):
        issues.append(f"{label} must be an integer between 1 and 100")
        return
    if not 1 <= number <= 100:
        issues.append(f"{label} must be between 1 and 100")


def _density_issues(value: Any, label: str, issues: list[str]) -> None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        issues.append(f"{label} must be an integer between 1 and 100")
        return
    if not 1 <= number <= 100:
        issues.append(f"{label} must be between 1 and 100")


def _modifier_is_set(value: Any) -> bool:
    return value not in (None, "", [], {})


def _config_key_to_modifier(key: str) -> str | None:
    mapping = {
        "speed": "speed",
        "density": "density",
        "text": "text",
        "theme": "theme",
        "direction": "direction",
        "colour": "color",
        "color": "color",
        "image": "image",
        "paths": "image",
        "path": "image",
        "glob": "image",
        "cycle": "cycle",
    }
    return mapping.get(key)


def _validate_supported_modifiers(widget_name: str, mapping: dict[str, Any], context: str, issues: list[str],
                                  config_paths: tuple[str, ...] | None = None) -> None:
    supported = set(widget_supports(widget_name, config_paths))
    for key, value in mapping.items():
        if key == "widget" or not _modifier_is_set(value):
            continue
        modifier = _config_key_to_modifier(str(key))
        if modifier is None or modifier in supported:
            continue
        issues.append(f"{context} uses unsupported modifier '{key}' for widget '{widget_name}'")


def validate_scene_catalog(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    issues: list[str] = []
    config_label = _config_label(config_paths)
    if not isinstance(catalog, dict):
        return [f"{config_label}: root must be a mapping"]

    _unknown_keys(catalog, TOP_LEVEL_KEYS, config_label, issues)

    defaults = catalog.get("defaults", {})
    if defaults is not None:
        if not isinstance(defaults, dict):
            issues.append(f"{config_label}: defaults must be a mapping")
        else:
            _unknown_keys(defaults, DEFAULT_KEYS, "defaults", issues)
            widget = defaults.get("widget")
            if widget is not None and not _supported_widget(str(widget)):
                issues.append(f"{config_label}: defaults.widget uses unsupported widget '{widget}'")
            elif widget is not None and not widget_enabled(str(widget), config_paths):
                issues.append(f"{config_label}: defaults.widget references disabled widget '{widget}'")
            image_spec = defaults.get("image")
            if image_spec is not None and not isinstance(image_spec, dict):
                issues.append(f"{config_label}: defaults.image must be a mapping")
            elif isinstance(image_spec, dict):
                _unknown_keys(image_spec, IMAGE_KEYS, "defaults.image", issues)
            glitch = defaults.get("glitch")
            if glitch is not None:
                try:
                    glitch_value = float(glitch)
                except (TypeError, ValueError):
                    issues.append(f"{config_label}: defaults.glitch must be a number")
                else:
                    if glitch_value < 0:
                        issues.append(f"{config_label}: defaults.glitch must be >= 0")
            _speed_issues(defaults.get("speed"), f"{config_label}: defaults.speed", issues)
            defaults_color = defaults.get("color", defaults.get("colour"))
            if defaults_color is not None and _color_value(defaults_color) is None:
                issues.append(f"{config_label}: defaults.colour must be a recognized colour name")
            direction = defaults.get("direction")
            if direction is not None and _direction_value(direction) is None:
                issues.append(f"{config_label}: defaults.direction must be one of: forward, backward, random, none")
            timing = defaults.get("timing")
            if timing is not None and not isinstance(timing, dict):
                issues.append(f"{config_label}: defaults.timing must be a mapping")

    layouts = catalog.get("layouts", {})
    if layouts is not None:
        if not isinstance(layouts, dict):
            issues.append(f"{config_label}: layouts must be a mapping")
        else:
            for layout_name, layout_cfg in layouts.items():
                if not isinstance(layout_cfg, dict):
                    issues.append(f"{config_label}: layout '{layout_name}' must be a mapping")
                    continue
                _unknown_keys(layout_cfg, LAYOUT_KEYS, f"layouts.{layout_name}", issues)
                panels = layout_cfg.get("panels", {})
                if not isinstance(panels, dict):
                    issues.append(f"{config_label}: layout '{layout_name}' panels must be a mapping")
                else:
                    for panel_name, panel_cfg in panels.items():
                        if not isinstance(panel_cfg, dict):
                            issues.append(f"{config_label}: layout '{layout_name}' panel '{panel_name}' must be a mapping")
                            continue
                        _unknown_keys(panel_cfg, PANEL_KEYS, f"layouts.{layout_name}.panels.{panel_name}", issues)
                        missing = PANEL_KEYS - set(panel_cfg)
                        if missing:
                            issues.append(
                                f"{config_label}: layout '{layout_name}' panel '{panel_name}' missing keys: {', '.join(sorted(missing))}"
                            )
                regions = layout_cfg.get("regions", {})
                if not isinstance(regions, dict):
                    issues.append(f"{config_label}: layout '{layout_name}' regions must be a mapping")

    screens = catalog.get("screens", {})
    if screens is not None:
        if not isinstance(screens, dict):
            issues.append(f"{config_label}: screens must be a mapping")
        else:
            layout_names_set = set(layout_names(config_paths))
            for scene_name, scene_cfg in screens.items():
                if not isinstance(scene_cfg, dict):
                    issues.append(f"{config_label}: screen '{scene_name}' must be a mapping")
                    continue
                _unknown_keys(scene_cfg, SCENE_KEYS, f"screens.{scene_name}", issues)
                layout_name = scene_cfg.get("layout")
                if layout_name and canonical_layout_name(layout_name, config_paths) is None:
                    issues.append(f"{config_label}: screen '{scene_name}' references unknown layout '{layout_name}'")
                glitch = scene_cfg.get("glitch")
                if glitch is not None:
                    try:
                        glitch_value = float(glitch)
                    except (TypeError, ValueError):
                        issues.append(f"{config_label}: screen '{scene_name}' glitch must be a number")
                    else:
                        if glitch_value < 0:
                            issues.append(f"{config_label}: screen '{scene_name}' glitch must be >= 0")
                _speed_issues(scene_cfg.get("speed"), f"{config_label}: screen '{scene_name}' speed", issues)
                if scene_cfg.get("density") is not None:
                    _density_issues(scene_cfg.get("density"), f"{config_label}: screen '{scene_name}' density", issues)
                scene_color = scene_cfg.get("color", scene_cfg.get("colour"))
                if scene_color is not None and _color_value(scene_color) is None:
                    issues.append(f"{config_label}: screen '{scene_name}' colour must be a recognized colour name")
                direction = scene_cfg.get("direction")
                if direction is not None and _direction_value(direction) is None:
                    issues.append(
                        f"{config_label}: screen '{scene_name}' direction must be one of: forward, backward, random, none"
                    )
                regions = scene_cfg.get("regions", {})
                if not isinstance(regions, dict):
                    issues.append(f"{config_label}: screen '{scene_name}' regions must be a mapping")
                    continue
                for region_name, region_cfg in regions.items():
                    if not isinstance(region_cfg, dict):
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' must be a mapping"
                        )
                        continue
                    _unknown_keys(region_cfg, REGION_KEYS, f"screens.{scene_name}.regions.{region_name}", issues)
                    _speed_issues(region_cfg.get("speed"), f"{config_label}: screen '{scene_name}' region '{region_name}' speed", issues)
                    if region_cfg.get("density") is not None:
                        _density_issues(region_cfg.get("density"), f"{config_label}: screen '{scene_name}' region '{region_name}' density", issues)
                    region_color = region_cfg.get("color", region_cfg.get("colour"))
                    if region_color is not None and _color_value(region_color) is None:
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' colour must be a recognized colour name"
                        )
                    direction = region_cfg.get("direction")
                    if direction is not None and _direction_value(direction) is None:
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' direction must be one of: forward, backward, random, none"
                        )
                    widget = region_cfg.get("widget")
                    if widget is None:
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' is missing 'widget'"
                        )
                    elif not _supported_widget(str(widget)):
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' uses unsupported widget '{widget}'"
                        )
                    elif not widget_enabled(str(widget), config_paths):
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' references disabled widget '{widget}'"
                        )
                    else:
                        _validate_supported_modifiers(
                            str(widget),
                            region_cfg,
                            f"{config_label}: screen '{scene_name}' region '{region_name}'",
                            issues,
                            config_paths,
                        )
                    cycle_spec = region_cfg.get("cycle")
                    if cycle_spec is not None and not isinstance(cycle_spec, dict):
                        issues.append(
                                f"{config_label}: screen '{scene_name}' region '{region_name}' cycle must be a mapping"
                        )
                    elif isinstance(cycle_spec, dict):
                        _unknown_keys(cycle_spec, CYCLE_KEYS, f"screens.{scene_name}.regions.{region_name}.cycle", issues)
                        widgets = cycle_spec.get("widgets")
                        if widgets is not None and not isinstance(widgets, list):
                            issues.append(
                                f"{config_label}: screen '{scene_name}' region '{region_name}' cycle.widgets must be a list"
                            )
                        elif isinstance(widgets, list):
                            if str(widget) != "cycle":
                                issues.append(
                                    f"{config_label}: screen '{scene_name}' region '{region_name}' defines cycle.widgets but widget is '{widget}'"
                                )
                            for idx, cycle_widget in enumerate(widgets):
                                cycle_widget_name = str(cycle_widget)
                                if not _supported_widget(cycle_widget_name):
                                    issues.append(
                                        f"{config_label}: screen '{scene_name}' region '{region_name}' cycle.widgets[{idx}] uses unsupported widget '{cycle_widget_name}'"
                                    )
                                elif not widget_enabled(cycle_widget_name, config_paths):
                                    issues.append(
                                        f"{config_label}: screen '{scene_name}' region '{region_name}' cycle.widgets[{idx}] references disabled widget '{cycle_widget_name}'"
                                    )
                                elif cycle_widget_name in {"cycle", "blank"}:
                                    issues.append(
                                        f"{config_label}: screen '{scene_name}' region '{region_name}' cycle.widgets[{idx}] may not be '{cycle_widget_name}'"
                                    )
                    image_spec = region_cfg.get("image")
                    if image_spec is not None and not isinstance(image_spec, dict):
                        issues.append(
                            f"{config_label}: screen '{scene_name}' region '{region_name}' image must be a mapping"
                        )
                    elif isinstance(image_spec, dict):
                        _unknown_keys(image_spec, IMAGE_KEYS, f"screens.{scene_name}.regions.{region_name}.image", issues)

    widget_showcase = catalog.get("widget_showcase", {})
    if widget_showcase is not None:
        if not isinstance(widget_showcase, dict):
            issues.append(f"{config_label}: widget_showcase must be a mapping")
        else:
            _unknown_keys(widget_showcase, WIDGET_SHOWCASE_KEYS, "widget_showcase", issues)
            pages = widget_showcase.get("pages", [])
            if not isinstance(pages, list):
                issues.append(f"{config_label}: widget_showcase.pages must be a list")
            else:
                for idx, page_cfg in enumerate(pages):
                    context = f"widget_showcase.pages[{idx}]"
                    if not isinstance(page_cfg, dict):
                        issues.append(f"{context} must be a mapping")
                        continue
                    _unknown_keys(page_cfg, WIDGET_SHOWCASE_PAGE_KEYS, context, issues)
                    widget = str(page_cfg.get("widget") or "")
                    if not widget:
                        issues.append(f"{context}.widget must be set")
                        continue
                    if not _supported_widget(widget):
                        issues.append(f"{context}.widget uses unsupported widget '{widget}'")
                        continue
                    if not widget_enabled(widget, config_paths):
                        issues.append(f"{context}.widget references disabled widget '{widget}'")
                    _speed_issues(page_cfg.get("speed"), f"{context}.speed", issues)
                    if page_cfg.get("density") is not None:
                        _density_issues(page_cfg.get("density"), f"{context}.density", issues)
                    theme = page_cfg.get("theme")
                    if theme is not None and str(theme) not in {
                        "hacker", "science", "medicine", "pharmacy", "finance", "space", "military", "navigation", "spaceteam",
                    }:
                        issues.append(f"{context}.theme must be a recognized theme")
                    direction = page_cfg.get("direction")
                    if direction is not None and _direction_value(direction) is None:
                        issues.append(f"{context}.direction must be one of: forward, backward, random, none")
                    note = page_cfg.get("note")
                    if note is not None and not isinstance(note, str):
                        issues.append(f"{context}.note must be a string")
                    text = page_cfg.get("text")
                    if text is not None and not isinstance(text, (str, list)):
                        issues.append(f"{context}.text must be a string or list of strings")
                    elif isinstance(text, list) and any(not isinstance(item, str) for item in text):
                        issues.append(f"{context}.text must be a string or list of strings")
                    page_color = page_cfg.get("color", page_cfg.get("colour"))
                    if page_color is not None and not isinstance(page_color, (str, list)):
                        issues.append(f"{context}.colour must be a string or list of strings")
                    elif isinstance(page_color, list):
                        if any(not isinstance(item, str) for item in page_color):
                            issues.append(f"{context}.colour must be a string or list of strings")
                        elif any(_color_value(item) is None for item in page_color):
                            issues.append(f"{context}.colour contains an unrecognized colour name")
                    elif page_color is not None and _color_value(page_color) is None:
                        issues.append(f"{context}.colour must be a recognized colour name")
                    image_spec = page_cfg.get("image")
                    if image_spec is not None and not isinstance(image_spec, dict):
                        issues.append(f"{context}.image must be a mapping")
                    elif isinstance(image_spec, dict):
                        _unknown_keys(image_spec, IMAGE_KEYS, f"{context}.image", issues)
                    cycle_spec = page_cfg.get("cycle")
                    if cycle_spec is not None and not isinstance(cycle_spec, dict):
                        issues.append(f"{context}.cycle must be a mapping")
                    elif isinstance(cycle_spec, dict):
                        _unknown_keys(cycle_spec, CYCLE_KEYS, f"{context}.cycle", issues)
                        cycle_widgets = cycle_spec.get("widgets")
                        if cycle_widgets is not None and not isinstance(cycle_widgets, list):
                            issues.append(f"{context}.cycle.widgets must be a list")
                    _validate_supported_modifiers(widget, page_cfg, context, issues, config_paths)

    widgets = catalog.get("widgets", {})
    if widgets is not None:
        if not isinstance(widgets, dict):
            issues.append(f"{config_label}: widgets must be a mapping")

    return issues


def _unknown_keys(mapping: dict[str, Any], allowed: set[str], context: str, issues: list[str]) -> None:
    for key in mapping:
        if str(key) not in allowed:
            issues.append(f"{context} has unrecognized key '{key}'")


def format_layout_diagrams(config_paths: tuple[str, ...] | None = None) -> str:
    layouts = layout_catalog(config_paths)
    blocks = []
    for layout_name, layout_cfg in layouts.items():
        blocks.append(_format_single_layout(layout_name, layout_cfg))
    return "\n\n".join(blocks)


def _format_single_layout(layout_name: str, layout_cfg: dict[str, Any]) -> str:
    panels = layout_cfg.get("panels", {})
    regions = layout_cfg.get("regions", {})
    x_bounds = _axis_boundaries(panels, axis="x")
    y_bounds = _axis_boundaries(panels, axis="y")
    x_steps = _axis_step_sizes(x_bounds)
    y_steps = _axis_step_sizes(y_bounds)
    x_positions = _scaled_axis_positions(x_steps, scale=4)
    y_positions = _scaled_axis_positions(y_steps, scale=2)
    width = x_positions[-1] + 1 if x_positions else 1
    height = y_positions[-1] + 1 if y_positions else 1
    masks = [[0 for _ in range(width)] for _ in range(height)]

    left = 1
    right = 2
    up = 4
    down = 8
    eps = 0.0005

    specs = {}
    for name, spec in panels.items():
        x0 = _as_fraction(spec["x"])
        y0 = _as_fraction(spec["y"])
        x1 = x0 + _as_fraction(spec["w"])
        y1 = y0 + _as_fraction(spec["h"])
        specs[name] = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}

    x_lookup = {bound: pos for bound, pos in zip(x_bounds, x_positions)}
    y_lookup = {bound: pos for bound, pos in zip(y_bounds, y_positions)}

    def add_horizontal(y: int, x0: int, x1: int) -> None:
        for x in range(x0, x1 + 1):
            if x > x0:
                masks[y][x] |= left
            if x < x1:
                masks[y][x] |= right

    def add_vertical(x: int, y0: int, y1: int) -> None:
        for y in range(y0, y1 + 1):
            if y > y0:
                masks[y][x] |= up
            if y < y1:
                masks[y][x] |= down

    for spec in specs.values():
        x0 = x_lookup[spec["x0"]]
        x1 = x_lookup[spec["x1"]]
        y0 = y_lookup[spec["y0"]]
        y1 = y_lookup[spec["y1"]]
        add_horizontal(y0, x0, x1)
        add_horizontal(y1, x0, x1)
        add_vertical(x0, y0, y1)
        add_vertical(x1, y0, y1)

    glyphs = {
        left | right: "─",
        up | down: "│",
        right | down: "┌",
        left | down: "┐",
        right | up: "└",
        left | up: "┘",
        left | right | down: "┬",
        left | right | up: "┴",
        right | up | down: "├",
        left | up | down: "┤",
        left | right | up | down: "┼",
    }
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            canvas[y][x] = glyphs.get(masks[y][x], " ")

    for panel_name, spec in specs.items():
        x0 = x_lookup[spec["x0"]]
        x1 = x_lookup[spec["x1"]]
        y0 = y_lookup[spec["y0"]]
        y1 = y_lookup[spec["y1"]]
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        label = panel_name
        start_x = max(x0 + 1, min(cx - len(label) // 2, x1 - len(label)))
        if y0 < cy < y1:
            for i, ch in enumerate(label):
                px = start_x + i
                if x0 < px < x1:
                    canvas[cy][px] = ch

    diagram_lines = [f"Layout: {layout_name}"] + ["".join(row).rstrip() for row in canvas]
    if not regions:
        return "\n".join(diagram_lines)

    name_width = max((len(str(region_name)) for region_name in regions), default=0)
    region_lines = ["Regions:"]
    for region_name, region_spec in regions.items():
        region_lines.append(f"  {str(region_name):<{name_width}}  {region_spec}")

    left_width = max(len(line) for line in diagram_lines)
    row_count = max(len(diagram_lines), len(region_lines))
    lines = []
    for idx in range(row_count):
        left = diagram_lines[idx] if idx < len(diagram_lines) else ""
        right = region_lines[idx] if idx < len(region_lines) else ""
        if right:
            lines.append(f"{left.ljust(left_width)}    {right}".rstrip())
        else:
            lines.append(left)
    return "\n".join(lines)


def _as_fraction(value: Any) -> Fraction:
    try:
        return Fraction(str(value)).limit_denominator(120)
    except (ValueError, ZeroDivisionError):
        return Fraction(float(value)).limit_denominator(120)


def _axis_boundaries(panels: dict[str, Any], *, axis: str) -> list[Fraction]:
    size_key = "w" if axis == "x" else "h"
    boundaries = set()
    for panel_cfg in panels.values():
        if not isinstance(panel_cfg, dict):
            continue
        start = _as_fraction(panel_cfg[axis])
        size = _as_fraction(panel_cfg[size_key])
        boundaries.add(start)
        boundaries.add(start + size)
    return sorted(boundaries)


def _axis_step_sizes(boundaries: list[Fraction]) -> list[int]:
    if len(boundaries) < 2:
        return [1]
    intervals = [boundaries[idx + 1] - boundaries[idx] for idx in range(len(boundaries) - 1)]
    lcm = 1
    for interval in intervals:
        lcm = math.lcm(lcm, interval.denominator)
    return [max(1, int(interval * lcm)) for interval in intervals]


def _scaled_axis_positions(steps: list[int], *, scale: int) -> list[int]:
    positions = [0]
    total = 0
    for step in steps:
        total += max(1, step * scale)
        positions.append(total)
    return positions


def _supported_widget(widget: str) -> bool:
    return widget in public_widget_names()


def _expand_image_spec(image_spec: dict[str, Any] | None) -> list[str]:
    if not image_spec:
        return []
    paths = image_spec.get("paths")
    if isinstance(paths, list):
        return [str(path) for path in paths]
    pattern = image_spec.get("glob")
    if pattern:
        return sorted(glob.glob(str(pattern)))
    single = image_spec.get("path")
    return [str(single)] if single else []


def _region_image_paths(region_cfg: Any) -> list[str]:
    if not isinstance(region_cfg, dict):
        return []
    image_spec = region_cfg.get("image")
    if isinstance(image_spec, dict):
        return _expand_image_spec(image_spec)
    # Allow shorthand image sources directly on the region mapping.
    if any(key in region_cfg for key in ("paths", "glob", "path")):
        return _expand_image_spec(region_cfg)
    return []


def _region_theme(region_cfg: Any) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    value = region_cfg.get("theme")
    return str(value) if value is not None else None


def _first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _modifier_source(region_cfg: Any, key: str) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    sources = region_cfg.get("__modifier_sources__")
    if not isinstance(sources, dict):
        return None
    value = sources.get(key)
    return str(value) if value is not None else None


def _resolve_area_modifiers(widget: str, region_cfg: Any, widget_cfg: dict[str, Any], *,
                            default_color: str | None, screen_density: int | None, screen_direction: str,
                            default_images: list[str]) -> dict[str, Any]:
    speed = region_cfg.get("speed") if isinstance(region_cfg, dict) else None
    if speed is not None:
        speed_source = _modifier_source(region_cfg, "speed") or "region"
    else:
        speed = widget_cfg.get("speed")
        speed_source = "widget_default" if speed is not None else None

    density = region_cfg.get("density") if isinstance(region_cfg, dict) else None
    if density is not None:
        density_source = _modifier_source(region_cfg, "density") or "region"
    else:
        density = widget_cfg.get("density")
        if density is not None:
            density_source = "widget_default"
        else:
            density = screen_density
            density_source = "screen" if density is not None else None

    text = region_cfg.get("text") if isinstance(region_cfg, dict) else None
    if text is not None:
        text_source = _modifier_source(region_cfg, "text") or "region"
    else:
        text = widget_cfg.get("text")
        text_source = "widget_default" if text is not None else None

    theme = _region_theme(region_cfg)
    if theme is not None:
        theme_source = _modifier_source(region_cfg, "theme") or "region"
    else:
        theme = _region_theme(widget_cfg)
        theme_source = "widget_default" if theme is not None else None

    color = _region_color(region_cfg)
    if color is not None:
        color_source = _modifier_source(region_cfg, "color") or "region"
    else:
        color = _region_color(widget_cfg)
        if color is not None:
            color_source = "widget_default"
        else:
            color = default_color
            color_source = "default" if color is not None else None
    if widget == "title_card" and color == "multi":
        color = "multi-bright"

    direction = _region_direction(region_cfg)
    if direction is not None:
        direction_source = _modifier_source(region_cfg, "direction") or "region"
    else:
        direction = _region_direction(widget_cfg)
        if direction is not None:
            direction_source = "widget_default"
        else:
            direction = screen_direction
            direction_source = "screen" if direction is not None else None

    area_images: list[str] = []
    image_source: str | None = None
    if widget == "image":
        area_images = _region_image_paths(region_cfg)
        if not area_images:
            area_images = _region_image_paths(widget_cfg)
            if area_images:
                image_source = "widget_default"
        else:
            image_source = _modifier_source(region_cfg, "image") or "region"
        if not area_images:
            area_images = default_images[:]
            if area_images:
                image_source = "default"

    cycle_widgets: list[str] = []
    cycle_source: str | None = None
    if widget == "cycle":
        cycle_widgets = _region_cycle_widgets(region_cfg) or _region_cycle_widgets(widget_cfg)
        if _region_cycle_widgets(region_cfg):
            cycle_source = _modifier_source(region_cfg, "cycle") or "region"
        elif cycle_widgets:
            cycle_source = "widget_default"

    return {
        "speed": speed,
        "density": density,
        "text": text,
        "theme": theme,
        "color": color,
        "direction": direction,
        "image_paths": area_images,
        "cycle_widgets": cycle_widgets,
        "modifier_sources": {
            "speed": speed_source,
            "density": density_source,
            "text": text_source,
            "theme": theme_source,
            "color": color_source,
            "direction": direction_source,
            "image": image_source,
            "cycle": cycle_source,
        },
    }


def _build_area_definition(*, name: str, widget: str, panels: list[str], rect: dict[str, float], region_cfg: Any,
                           modifiers: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "mode": widget,
        "panels": panels,
        "x": rect["x"],
        "y": rect["y"],
        "w": rect["w"],
        "h": rect["h"],
        "speed": modifiers["speed"],
        "density": modifiers["density"],
        "text": modifiers["text"],
        "theme": modifiers["theme"],
        "colour": modifiers["color"],
        "direction": modifiers["direction"],
        "image_paths": modifiers["image_paths"],
        "cycle_widgets": modifiers["cycle_widgets"],
        "modifier_sources": modifiers["modifier_sources"],
        "allow_inert_modifiers": bool(region_cfg.get("__allow_inert_modifiers__")) if isinstance(region_cfg, dict) else False,
        "label": region_cfg.get("label") if isinstance(region_cfg, dict) else None,
        "unavailable_message": region_cfg.get("unavailable_message") if isinstance(region_cfg, dict) else None,
        "static_lines": region_cfg.get("static_lines") if isinstance(region_cfg, dict) else None,
        "static_align": region_cfg.get("static_align") if isinstance(region_cfg, dict) else None,
    }


def _resolve_screen_runtime_defaults(screen_cfg: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    return {
        "theme": screen_cfg.get("theme", defaults.get("theme", "science")),
        "speed": screen_cfg.get("speed", defaults.get("speed", 50)),
        "density": screen_cfg.get("density"),
        "text": screen_cfg.get("text", ""),
        "glitch": screen_cfg.get("glitch", defaults.get("glitch", 0.0)),
        "default_widget": defaults.get("widget"),
        "default_color": _region_color(screen_cfg) or defaults.get("color"),
        "direction": _region_direction(screen_cfg) or defaults.get("direction", "forward"),
    }


def _resolve_scene_runtime_defaults(scene_cfg: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    return _resolve_screen_runtime_defaults(scene_cfg, defaults)


def _config_label(config_paths: tuple[str, ...] | None) -> str:
    normalized = _normalize_config_paths(config_paths)
    if len(normalized) == 1:
        return Path(normalized[0]).name
    return "merged screen config"


def _resolve_config_path(pathish: Any, base_dir: Path) -> str:
    path = Path(str(pathish)).expanduser()
    if path.is_absolute():
        return str(path.resolve())

    cwd = Path.cwd()
    if len(path.parts) > 1:
        return str((cwd / path).resolve())

    candidates = [
        cwd / path,
        base_dir / path,
        PACKAGE_DIR / "data" / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return str(candidates[0].resolve())


def _resolve_config_glob(patternish: Any, base_dir: Path) -> str:
    pattern = Path(str(patternish)).expanduser()
    if pattern.is_absolute():
        return str(pattern)

    cwd = Path.cwd()
    if len(pattern.parts) > 1:
        return str(cwd / pattern)

    candidates = [
        cwd / pattern,
        base_dir / pattern,
        PACKAGE_DIR / "data" / pattern,
    ]
    for candidate in candidates:
        if glob.glob(str(candidate)):
            return str(candidate)
    return str(candidates[0])


def _normalize_image_mapping(image_spec: Any, base_dir: Path) -> None:
    if not isinstance(image_spec, dict):
        return
    if isinstance(image_spec.get("paths"), list):
        image_spec["paths"] = [_resolve_config_path(path, base_dir) for path in image_spec["paths"]]
    if image_spec.get("path") is not None:
        image_spec["path"] = _resolve_config_path(image_spec["path"], base_dir)
    if image_spec.get("glob") is not None:
        image_spec["glob"] = _resolve_config_glob(image_spec["glob"], base_dir)


def _normalize_catalog_paths(catalog: dict[str, Any], source_path: Path) -> dict[str, Any]:
    base_dir = source_path.parent
    defaults = catalog.get("defaults")
    if isinstance(defaults, dict):
        _normalize_image_mapping(defaults.get("image"), base_dir)
    widgets = catalog.get("widgets")
    if isinstance(widgets, dict):
        for widget_cfg in widgets.values():
            if not isinstance(widget_cfg, dict):
                continue
            defaults_cfg = widget_cfg.get("defaults")
            if isinstance(defaults_cfg, dict):
                if any(key in defaults_cfg for key in ("paths", "path", "glob")):
                    _normalize_image_mapping(defaults_cfg, base_dir)
                _normalize_image_mapping(defaults_cfg.get("image"), base_dir)
    screens = catalog.get("screens")
    if isinstance(screens, dict):
        for scene_cfg in screens.values():
            if not isinstance(scene_cfg, dict):
                continue
            regions = scene_cfg.get("regions")
            if not isinstance(regions, dict):
                continue
            for region_cfg in regions.values():
                if not isinstance(region_cfg, dict):
                    continue
                if any(key in region_cfg for key in ("paths", "path", "glob")):
                    _normalize_image_mapping(region_cfg, base_dir)
                _normalize_image_mapping(region_cfg.get("image"), base_dir)
    widget_showcase = catalog.get("widget_showcase")
    if isinstance(widget_showcase, dict):
        pages = widget_showcase.get("pages")
        if isinstance(pages, list):
            for page_cfg in pages:
                if not isinstance(page_cfg, dict):
                    continue
                if any(key in page_cfg for key in ("paths", "path", "glob")):
                    _normalize_image_mapping(page_cfg, base_dir)
                _normalize_image_mapping(page_cfg.get("image"), base_dir)
    return catalog


def _widget_name(region_cfg: Any) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    widget = region_cfg.get("widget")
    return str(widget) if widget is not None else None


def _region_cycle_widgets(region_cfg: Any) -> list[str]:
    if not isinstance(region_cfg, dict):
        return []
    cycle_spec = region_cfg.get("cycle")
    if not isinstance(cycle_spec, dict):
        return []
    widgets = cycle_spec.get("widgets")
    if not isinstance(widgets, list):
        return []
    return [str(widget) for widget in widgets]


def _region_color(region_cfg: Any) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    value = region_cfg.get("color")
    if value is None:
        value = region_cfg.get("colour")
    return str(value) if value is not None else None


def _region_direction(region_cfg: Any) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    return _direction_value(region_cfg.get("direction"))


def adapt_scene_to_legacy(scene_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    scenes = catalog.get("screens", {})
    defaults = catalog.get("defaults", {})

    if scene_name not in scenes:
        raise KeyError(scene_name)

    scene_cfg = scenes[scene_name]
    if not isinstance(scene_cfg, dict):
        parser.error(f"screen '{scene_name}' must be a mapping in {_config_label(config_paths)}")

    layout = scene_cfg.get("layout")
    regions = scene_cfg.get("regions", {})
    if not isinstance(regions, dict):
        parser.error(f"screen '{scene_name}' regions must be a mapping in {_config_label(config_paths)}")

    scene_speed = scene_cfg.get("speed", defaults.get("speed", 50))
    theme = scene_cfg.get("theme", defaults.get("theme", "science"))
    scene_color = _region_color(scene_cfg) or defaults.get("color", defaults.get("colour"))

    if layout == "full":
        full_cfg = regions.get("full")
        widget = _widget_name(full_cfg)
        if not widget:
            parser.error(f"screen '{scene_name}' uses layout 'full' but has no 'full' widget assignment")
        if not _supported_widget(widget) or widget in {"sparkline", "readouts"}:
            parser.error(f"screen '{scene_name}' uses widget '{widget}', which is not supported by the legacy runtime")
        return {
            "scene_name": scene_name,
            "theme": theme,
            "speed": scene_speed,
            "main_mode": widget,
            "sidebar_mode": "none",
            "main_speed": full_cfg.get("speed") if isinstance(full_cfg, dict) else None,
            "sidebar_speed": None,
            "text": scene_cfg.get("text", ""),
            "colour": scene_color,
            "image_paths": _expand_image_spec(full_cfg.get("image")) if isinstance(full_cfg, dict) else [],
        }

    if layout == "split_left_right":
        left_cfg = regions.get("left")
        right_cfg = regions.get("right")
        left_widget = _widget_name(left_cfg)
        right_widget = _widget_name(right_cfg)
        if not left_widget or not right_widget:
            parser.error(f"screen '{scene_name}' uses layout 'split_left_right' but must define both 'left' and 'right'")
        if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}
                or not _supported_widget(right_widget) or right_widget in {"sparkline", "readouts"}):
            bad = left_widget if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}) else right_widget
            parser.error(f"screen '{scene_name}' uses widget '{bad}', which is not supported by the legacy runtime")
        return {
            "scene_name": scene_name,
            "theme": theme,
            "speed": scene_speed,
            "main_mode": left_widget,
            "sidebar_mode": right_widget,
            "main_speed": left_cfg.get("speed") if isinstance(left_cfg, dict) else None,
            "sidebar_speed": right_cfg.get("speed") if isinstance(right_cfg, dict) else None,
            "text": scene_cfg.get("text", ""),
            "colour": scene_color,
            "image_paths": (
                _expand_image_spec(left_cfg.get("image")) if left_widget == "image" and isinstance(left_cfg, dict) else
                _expand_image_spec(right_cfg.get("image")) if right_widget == "image" and isinstance(right_cfg, dict) else
                []
            ),
        }

    parser.error(
        f"screen '{scene_name}' uses layout '{layout}', which is not yet supported by the current runtime; "
        "currently supported config layouts: full, split_left_right"
    )


def _parse_region_spec(layout_name: str, layout_cfg: dict[str, Any], region_name: str, parser, scene_name: str) -> list[str]:
    normalized = _normalize_region_expr_in_layout(layout_name, layout_cfg, region_name)
    if normalized is None:
        parser.error(f"screen '{scene_name}' references unknown region '{region_name}'")
    panel_names = normalized.split("+")
    if not panel_names:
        parser.error(f"screen '{scene_name}' has empty region spec for '{region_name}'")
    return panel_names


def _rect_for_panels(layout_cfg: dict[str, Any], panel_names: list[str], parser, scene_name: str, region_name: str) -> dict[str, float]:
    panels = layout_cfg.get("panels", {})
    xs = [float(panels[name]["x"]) for name in panel_names]
    ys = [float(panels[name]["y"]) for name in panel_names]
    ws = [float(panels[name]["w"]) for name in panel_names]
    hs = [float(panels[name]["h"]) for name in panel_names]
    x0 = min(xs)
    y0 = min(ys)
    x1 = max(x + w for x, w in zip(xs, ws))
    y1 = max(y + h for y, h in zip(ys, hs))
    covered = 0.0
    for width, height in zip(ws, hs):
        covered += width * height
    bbox = (x1 - x0) * (y1 - y0)
    if abs(covered - bbox) > 0.0005:
        parser.error(
            f"screen '{scene_name}' region '{region_name}' does not resolve to a single rectangle"
        )
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _resolve_runtime_screen(screen_name: str, layout_name: str, layout_cfg: dict[str, Any],
                            regions_cfg: dict[str, Any], parser, *,
                            theme: str, speed: int | float, text: str,
                            glitch: int | float = 0.0,
                            default_widget: str | None = None, default_color: str | None = None,
                            direction: str = "forward", density: int | None = None,
                            config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    if not isinstance(regions_cfg, dict):
        parser.error(f"screen '{screen_name}' regions must be a mapping in {_config_label(config_paths)}")

    default_images = default_image_paths(config_paths)
    widget_defaults = widget_defaults_catalog(config_paths)
    panel_map = layout_cfg.get("panels", {})
    seen = []
    areas = []
    image_paths = []
    screen_direction = _direction_value(direction) or "forward"
    for region_name, region_cfg in regions_cfg.items():
        widget = _widget_name(region_cfg)
        if not widget:
            parser.error(f"screen '{screen_name}' region '{region_name}' has no widget")
        if not _supported_widget(widget):
            parser.error(f"screen '{screen_name}' uses unsupported widget '{widget}'")
        widget_cfg = widget_defaults.get(widget, {})
        panel_names = _parse_region_spec(layout_name, layout_cfg, region_name, parser, screen_name)
        rect = _rect_for_panels(layout_cfg, panel_names, parser, screen_name, region_name)
        modifiers = _resolve_area_modifiers(
            widget,
            region_cfg,
            widget_cfg,
            default_color=default_color,
            screen_density=density,
            screen_direction=screen_direction,
            default_images=default_images,
        )
        area = _build_area_definition(
            name=region_name,
            widget=widget,
            panels=panel_names,
            rect=rect,
            region_cfg=region_cfg,
            modifiers=modifiers,
        )
        overlap = set(panel_names) & set(seen)
        if overlap:
            parser.error(f"screen '{screen_name}' has overlapping panel assignments: {', '.join(sorted(overlap))}")
        seen.extend(panel_names)
        if widget == "image":
            image_paths.extend(area["image_paths"])
        areas.append(area)

    uncovered = [panel_name for panel_name in panel_map if panel_name not in seen]
    if uncovered:
        if not default_widget:
            parser.error(
                f"screen '{screen_name}' leaves panels unassigned ({', '.join(sorted(uncovered))}) and no default widget is configured"
            )
        if not _supported_widget(default_widget):
            parser.error(f"default widget '{default_widget}' is unsupported")
        for panel_name in uncovered:
            panel_cfg = panel_map[panel_name]
            widget_cfg = widget_defaults.get(default_widget, {})
            modifiers = _resolve_area_modifiers(
                default_widget,
                None,
                widget_cfg,
                default_color=default_color,
                screen_density=density,
                screen_direction=screen_direction,
                default_images=default_images,
            )
            areas.append(_build_area_definition(
                name=panel_name,
                widget=default_widget,
                panels=[panel_name],
                rect={
                    "x": float(panel_cfg["x"]),
                    "y": float(panel_cfg["y"]),
                    "w": float(panel_cfg["w"]),
                    "h": float(panel_cfg["h"]),
                },
                region_cfg=None,
                modifiers=modifiers,
            ))
            if default_widget == "image":
                image_paths.extend(modifiers["image_paths"])

    return {
        "screen_name": screen_name,
        "theme": theme,
        "speed": speed,
        "density": density,
        "text": text,
        "glitch": max(0.0, float(glitch)),
        "direction": screen_direction,
        "layout": layout_name,
        "areas": areas,
        "image_paths": image_paths,
    }


def _resolve_runtime_scene(scene_name: str, layout_name: str, layout_cfg: dict[str, Any],
                           regions_cfg: dict[str, Any], parser, *,
                           theme: str, speed: int | float, text: str,
                           glitch: int | float = 0.0,
                           default_widget: str | None = None, default_color: str | None = None,
                           direction: str = "forward", density: int | None = None,
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    return _resolve_runtime_screen(
        scene_name, layout_name, layout_cfg, regions_cfg, parser,
        theme=theme, speed=speed, text=text, glitch=glitch,
        default_widget=default_widget, default_color=default_color, direction=direction, density=density,
        config_paths=config_paths,
    )


def resolve_runtime_layout(layout_name: str, regions_cfg: dict[str, Any], parser, *,
                           scene_name: str = "<cli>", theme: str = "science",
                           speed: int | float = 50, text: str = "",
                           glitch: int | float = 0.0,
                           default_widget: str | None = None, default_color: str | None = None,
                           direction: str = "forward", density: int | None = None,
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    canonical_name = canonical_layout_name(layout_name, config_paths)
    layout_cfg = layouts.get(canonical_name) if canonical_name is not None else None
    if not isinstance(layout_cfg, dict):
        parser.error(f"unknown layout '{layout_name}'")
    return _resolve_runtime_screen(
        scene_name, canonical_name, layout_cfg, regions_cfg, parser,
        theme=theme, speed=speed, text=text, glitch=glitch,
        default_widget=default_widget, default_color=default_color, direction=direction, density=density,
        config_paths=config_paths,
    )


def resolve_config_screen(screen_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    scenes = catalog.get("screens", {})
    defaults = config_defaults(config_paths)

    if screen_name not in scenes:
        raise KeyError(screen_name)

    screen_cfg = scenes[screen_name]
    if not isinstance(screen_cfg, dict):
        parser.error(f"screen '{screen_name}' must be a mapping in {_config_label(config_paths)}")

    layout_name = screen_cfg.get("layout")
    regions_cfg = screen_cfg.get("regions", {})
    resolved = _resolve_screen_runtime_defaults(screen_cfg, defaults)
    return resolve_runtime_layout(
        layout_name,
        regions_cfg,
        parser,
        scene_name=screen_name,
        theme=resolved["theme"],
        speed=resolved["speed"],
        density=resolved["density"],
        text=resolved["text"],
        glitch=resolved["glitch"],
        default_widget=resolved["default_widget"],
        default_color=resolved["default_color"],
        direction=resolved["direction"],
        config_paths=config_paths,
    )


def resolve_config_scene(scene_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    return resolve_config_screen(scene_name, parser, config_paths)
