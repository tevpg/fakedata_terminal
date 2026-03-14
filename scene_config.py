"""Load YAML scene definitions, merge overlays, and adapt them to the runtime."""

from __future__ import annotations

from functools import lru_cache
import glob
import os
from pathlib import Path
from typing import Any

import yaml


PACKAGE_DIR = Path(__file__).resolve().parent
LAYOUT_CONFIG_PATH = PACKAGE_DIR / "data" / "layouts.yaml"
SCENE_CONFIG_PATH = PACKAGE_DIR / "data" / "scenes.yaml"
PACKAGE_CONFIG_PATHS = (
    LAYOUT_CONFIG_PATH,
    SCENE_CONFIG_PATH,
)
USER_CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fakedata-terminal" / "scenes.yaml"
PROJECT_CONFIG_NAMES = (
    ".fakedata-terminal.yaml",
    ".fakedata-terminal.yml",
)

TOP_LEVEL_KEYS = {"defaults", "layouts", "scenes", "widgets"}
DEFAULT_KEYS = {"layout", "theme", "speed", "panel_speed", "image", "widget", "colour", "color"}
LAYOUT_KEYS = {"panels", "regions"}
PANEL_KEYS = {"x", "y", "w", "h"}
SCENE_KEYS = {"note", "layout", "theme", "speed", "text", "regions"}
REGION_KEYS = {"widget", "speed", "text", "source_theme", "image", "paths", "path", "glob", "cycle", "colour", "color"}
IMAGE_KEYS = {"paths", "path", "glob"}
CYCLE_KEYS = {"widgets"}
WIDGET_DEFAULT_KEYS = REGION_KEYS - {"widget"}

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
        raise ValueError(f"Scene config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scene config root must be a mapping: {path}")
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


def config_scene_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    scenes = catalog.get("scenes", {})
    if not isinstance(scenes, dict):
        return []
    return list(scenes.keys())


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
    return "+".join(canonical_panels)


def layout_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    return layouts if isinstance(layouts, dict) else {}


def widget_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_scene_catalog(config_paths)
    widgets = catalog.get("widgets", {})
    names = set()
    if isinstance(widgets, dict):
        for key, value in widgets.items():
            if isinstance(value, list):
                names.update(str(item) for item in value)
            elif isinstance(value, dict) and _supported_widget(str(key)):
                names.add(str(key))
    names.update({
        "text", "text_wide", "text_scant", "text_spew", "image", "life",
        "bars", "clock", "matrix", "oscilloscope", "blocks", "sweep", "tunnel",
        "sparkline", "readouts", "blank", "cycle",
    })
    return sorted(names)


def widget_defaults_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    catalog = load_scene_catalog(config_paths)
    widgets = catalog.get("widgets", {})
    defaults: dict[str, dict[str, Any]] = {}
    if not isinstance(widgets, dict):
        return defaults
    for key, value in widgets.items():
        widget_name = str(key)
        if not isinstance(value, dict) or not _supported_widget(widget_name):
            continue
        defaults[widget_name] = value
    return defaults


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
    colour = defaults.get("colour")
    if colour is None:
        colour = defaults.get("color")
    layout_name = defaults.get("layout")
    return {
        "layout": canonical_layout_name(layout_name, config_paths) if layout_name is not None else None,
        "theme": defaults.get("theme", "science"),
        "speed": defaults.get("speed", 50),
        "widget": defaults.get("widget"),
        "colour": colour,
        "image": defaults.get("image"),
    }


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
            layout_name = defaults.get("layout")
            if layout_name is not None and canonical_layout_name(layout_name, config_paths) is None:
                issues.append(f"{config_label}: defaults.layout references unknown layout '{layout_name}'")
            widget = defaults.get("widget")
            if widget is not None and not _supported_widget(str(widget)):
                issues.append(f"{config_label}: defaults.widget uses unsupported widget '{widget}'")
            image_spec = defaults.get("image")
            if image_spec is not None and not isinstance(image_spec, dict):
                issues.append(f"{config_label}: defaults.image must be a mapping")
            elif isinstance(image_spec, dict):
                _unknown_keys(image_spec, IMAGE_KEYS, "defaults.image", issues)

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

    scenes = catalog.get("scenes", {})
    if scenes is not None:
        if not isinstance(scenes, dict):
            issues.append(f"{config_label}: scenes must be a mapping")
        else:
            layout_names_set = set(layout_names(config_paths))
            for scene_name, scene_cfg in scenes.items():
                if not isinstance(scene_cfg, dict):
                    issues.append(f"{config_label}: scene '{scene_name}' must be a mapping")
                    continue
                _unknown_keys(scene_cfg, SCENE_KEYS, f"scenes.{scene_name}", issues)
                layout_name = scene_cfg.get("layout")
                if layout_name and canonical_layout_name(layout_name, config_paths) is None:
                    issues.append(f"{config_label}: scene '{scene_name}' references unknown layout '{layout_name}'")
                regions = scene_cfg.get("regions", {})
                if not isinstance(regions, dict):
                    issues.append(f"{config_label}: scene '{scene_name}' regions must be a mapping")
                    continue
                for region_name, region_cfg in regions.items():
                    if not isinstance(region_cfg, dict):
                        issues.append(
                            f"{config_label}: scene '{scene_name}' region '{region_name}' must be a mapping"
                        )
                        continue
                    _unknown_keys(region_cfg, REGION_KEYS, f"scenes.{scene_name}.regions.{region_name}", issues)
                    widget = region_cfg.get("widget")
                    if widget is None:
                        issues.append(
                            f"{config_label}: scene '{scene_name}' region '{region_name}' is missing 'widget'"
                        )
                    elif not _supported_widget(str(widget)):
                        issues.append(
                            f"{config_label}: scene '{scene_name}' region '{region_name}' uses unsupported widget '{widget}'"
                        )
                    cycle_spec = region_cfg.get("cycle")
                    if cycle_spec is not None and not isinstance(cycle_spec, dict):
                        issues.append(
                            f"{config_label}: scene '{scene_name}' region '{region_name}' cycle must be a mapping"
                        )
                    elif isinstance(cycle_spec, dict):
                        _unknown_keys(cycle_spec, CYCLE_KEYS, f"scenes.{scene_name}.regions.{region_name}.cycle", issues)
                        widgets = cycle_spec.get("widgets")
                        if widgets is not None and not isinstance(widgets, list):
                            issues.append(
                                f"{config_label}: scene '{scene_name}' region '{region_name}' cycle.widgets must be a list"
                            )
                        elif isinstance(widgets, list):
                            if str(widget) != "cycle":
                                issues.append(
                                    f"{config_label}: scene '{scene_name}' region '{region_name}' defines cycle.widgets but widget is '{widget}'"
                                )
                            for idx, cycle_widget in enumerate(widgets):
                                cycle_widget_name = str(cycle_widget)
                                if not _supported_widget(cycle_widget_name):
                                    issues.append(
                                        f"{config_label}: scene '{scene_name}' region '{region_name}' cycle.widgets[{idx}] uses unsupported widget '{cycle_widget_name}'"
                                    )
                                elif cycle_widget_name in {"cycle", "blank"}:
                                    issues.append(
                                        f"{config_label}: scene '{scene_name}' region '{region_name}' cycle.widgets[{idx}] may not be '{cycle_widget_name}'"
                                    )
                    image_spec = region_cfg.get("image")
                    if image_spec is not None and not isinstance(image_spec, dict):
                        issues.append(
                            f"{config_label}: scene '{scene_name}' region '{region_name}' image must be a mapping"
                        )
                    elif isinstance(image_spec, dict):
                        _unknown_keys(image_spec, IMAGE_KEYS, f"scenes.{scene_name}.regions.{region_name}.image", issues)

    widgets = catalog.get("widgets", {})
    if widgets is not None:
        if not isinstance(widgets, dict):
            issues.append(f"{config_label}: widgets must be a mapping")
        else:
            for widget_name, widget_cfg in widgets.items():
                widget_name = str(widget_name)
                if isinstance(widget_cfg, list):
                    continue
                if not isinstance(widget_cfg, dict):
                    issues.append(f"{config_label}: widgets.{widget_name} must be a mapping or list")
                    continue
                if not _supported_widget(widget_name):
                    issues.append(f"{config_label}: widgets.{widget_name} is not a supported widget name")
                    continue
                _unknown_keys(widget_cfg, WIDGET_DEFAULT_KEYS, f"widgets.{widget_name}", issues)
                cycle_spec = widget_cfg.get("cycle")
                if cycle_spec is not None and not isinstance(cycle_spec, dict):
                    issues.append(f"{config_label}: widgets.{widget_name}.cycle must be a mapping")
                elif isinstance(cycle_spec, dict):
                    _unknown_keys(cycle_spec, CYCLE_KEYS, f"widgets.{widget_name}.cycle", issues)
                    cycle_widgets = cycle_spec.get("widgets")
                    if cycle_widgets is not None and not isinstance(cycle_widgets, list):
                        issues.append(f"{config_label}: widgets.{widget_name}.cycle.widgets must be a list")
                    elif isinstance(cycle_widgets, list):
                        if widget_name != "cycle":
                            issues.append(
                                f"{config_label}: widgets.{widget_name}.cycle is only valid for widget 'cycle'"
                            )
                        for idx, cycle_widget in enumerate(cycle_widgets):
                            cycle_widget_name = str(cycle_widget)
                            if not _supported_widget(cycle_widget_name):
                                issues.append(
                                    f"{config_label}: widgets.{widget_name}.cycle.widgets[{idx}] uses unsupported widget '{cycle_widget_name}'"
                                )
                            elif cycle_widget_name in {"cycle", "blank"}:
                                issues.append(
                                    f"{config_label}: widgets.{widget_name}.cycle.widgets[{idx}] may not be '{cycle_widget_name}'"
                                )
                image_spec = widget_cfg.get("image")
                if image_spec is not None and not isinstance(image_spec, dict):
                    issues.append(f"{config_label}: widgets.{widget_name}.image must be a mapping")
                elif isinstance(image_spec, dict):
                    _unknown_keys(image_spec, IMAGE_KEYS, f"widgets.{widget_name}.image", issues)

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
    width = 31
    height = 7
    masks = [[0 for _ in range(width)] for _ in range(height)]

    left = 1
    right = 2
    up = 4
    down = 8
    eps = 0.0005

    specs = {
        name: {
            "x0": float(spec["x"]),
            "y0": float(spec["y"]),
            "x1": float(spec["x"]) + float(spec["w"]),
            "y1": float(spec["y"]) + float(spec["h"]),
        }
        for name, spec in panels.items()
    }

    def xmap(value: float) -> int:
        return int(round(value * (width - 1)))

    def ymap(value: float) -> int:
        return int(round(value * (height - 1)))

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

    add_horizontal(0, 0, width - 1)
    add_horizontal(height - 1, 0, width - 1)
    add_vertical(0, 0, height - 1)
    add_vertical(width - 1, 0, height - 1)

    panel_items = list(specs.items())
    for idx, (_, a) in enumerate(panel_items):
        for _, b in panel_items[idx + 1:]:
            if abs(a["x1"] - b["x0"]) <= eps or abs(b["x1"] - a["x0"]) <= eps:
                shared_x = a["x1"] if abs(a["x1"] - b["x0"]) <= eps else b["x1"]
                overlap_y0 = max(a["y0"], b["y0"])
                overlap_y1 = min(a["y1"], b["y1"])
                if overlap_y1 - overlap_y0 > eps:
                    add_vertical(xmap(shared_x), ymap(overlap_y0), ymap(overlap_y1))
            if abs(a["y1"] - b["y0"]) <= eps or abs(b["y1"] - a["y0"]) <= eps:
                shared_y = a["y1"] if abs(a["y1"] - b["y0"]) <= eps else b["y1"]
                overlap_x0 = max(a["x0"], b["x0"])
                overlap_x1 = min(a["x1"], b["x1"])
                if overlap_x1 - overlap_x0 > eps:
                    add_horizontal(ymap(shared_y), xmap(overlap_x0), xmap(overlap_x1))

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
        x0 = xmap(spec["x0"])
        x1 = xmap(spec["x1"])
        y0 = ymap(spec["y0"])
        y1 = ymap(spec["y1"])
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


def _supported_widget(widget: str) -> bool:
    return widget in {
        "text", "text_wide", "text_scant", "text_spew", "image", "life",
        "bars", "clock", "matrix", "oscilloscope", "blocks", "sweep", "tunnel",
        "sparkline", "readouts", "blank", "cycle",
    }


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


def _config_label(config_paths: tuple[str, ...] | None) -> str:
    normalized = _normalize_config_paths(config_paths)
    if len(normalized) == 1:
        return Path(normalized[0]).name
    return "merged scene config"


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
            if any(key in widget_cfg for key in ("paths", "path", "glob")):
                _normalize_image_mapping(widget_cfg, base_dir)
            _normalize_image_mapping(widget_cfg.get("image"), base_dir)
    scenes = catalog.get("scenes")
    if isinstance(scenes, dict):
        for scene_cfg in scenes.values():
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


def _region_colour(region_cfg: Any) -> str | None:
    if not isinstance(region_cfg, dict):
        return None
    value = region_cfg.get("colour")
    if value is None:
        value = region_cfg.get("color")
    return str(value) if value is not None else None


def adapt_scene_to_legacy(scene_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    scenes = catalog.get("scenes", {})
    defaults = catalog.get("defaults", {})

    if scene_name not in scenes:
        raise KeyError(scene_name)

    scene_cfg = scenes[scene_name]
    if not isinstance(scene_cfg, dict):
        parser.error(f"scene '{scene_name}' must be a mapping in {_config_label(config_paths)}")

    layout = scene_cfg.get("layout")
    regions = scene_cfg.get("regions", {})
    if not isinstance(regions, dict):
        parser.error(f"scene '{scene_name}' regions must be a mapping in {_config_label(config_paths)}")

    scene_speed = scene_cfg.get("speed", defaults.get("speed", 50))
    theme = scene_cfg.get("theme", defaults.get("theme", "science"))

    if layout == "full":
        full_cfg = regions.get("full")
        widget = _widget_name(full_cfg)
        if not widget:
            parser.error(f"scene '{scene_name}' uses layout 'full' but has no 'full' widget assignment")
        if not _supported_widget(widget) or widget in {"sparkline", "readouts"}:
            parser.error(f"scene '{scene_name}' uses widget '{widget}', which is not supported by the legacy runtime")
        return {
            "scene_name": scene_name,
            "theme": theme,
            "speed": scene_speed,
            "main_mode": widget,
            "sidebar_mode": "none",
            "main_speed": full_cfg.get("speed") if isinstance(full_cfg, dict) else None,
            "sidebar_speed": None,
            "text": scene_cfg.get("text", ""),
            "image_paths": _expand_image_spec(full_cfg.get("image")) if isinstance(full_cfg, dict) else [],
        }

    if layout == "split_left_right":
        left_cfg = regions.get("left")
        right_cfg = regions.get("right")
        left_widget = _widget_name(left_cfg)
        right_widget = _widget_name(right_cfg)
        if not left_widget or not right_widget:
            parser.error(f"scene '{scene_name}' uses layout 'split_left_right' but must define both 'left' and 'right'")
        if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}
                or not _supported_widget(right_widget) or right_widget in {"sparkline", "readouts"}):
            bad = left_widget if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}) else right_widget
            parser.error(f"scene '{scene_name}' uses widget '{bad}', which is not supported by the legacy runtime")
        return {
            "scene_name": scene_name,
            "theme": theme,
            "speed": scene_speed,
            "main_mode": left_widget,
            "sidebar_mode": right_widget,
            "main_speed": left_cfg.get("speed") if isinstance(left_cfg, dict) else None,
            "sidebar_speed": right_cfg.get("speed") if isinstance(right_cfg, dict) else None,
            "text": scene_cfg.get("text", ""),
            "image_paths": (
                _expand_image_spec(left_cfg.get("image")) if left_widget == "image" and isinstance(left_cfg, dict) else
                _expand_image_spec(right_cfg.get("image")) if right_widget == "image" and isinstance(right_cfg, dict) else
                []
            ),
        }

    parser.error(
        f"scene '{scene_name}' uses layout '{layout}', which is not yet supported by the current runtime; "
        "currently supported config layouts: full, split_left_right"
    )


def _parse_region_spec(layout_name: str, layout_cfg: dict[str, Any], region_name: str, parser, scene_name: str) -> list[str]:
    normalized = _normalize_region_expr_in_layout(layout_name, layout_cfg, region_name)
    if normalized is None:
        parser.error(f"scene '{scene_name}' references unknown region '{region_name}'")
    panel_names = normalized.split("+")
    if not panel_names:
        parser.error(f"scene '{scene_name}' has empty region spec for '{region_name}'")
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
            f"scene '{scene_name}' region '{region_name}' does not resolve to a single rectangle"
        )
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _resolve_runtime_scene(scene_name: str, layout_name: str, layout_cfg: dict[str, Any],
                           regions_cfg: dict[str, Any], parser, *,
                           theme: str, speed: int | float, text: str,
                           default_widget: str | None = None, default_colour: str | None = None,
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    if not isinstance(regions_cfg, dict):
        parser.error(f"scene '{scene_name}' regions must be a mapping in {_config_label(config_paths)}")

    default_images = default_image_paths(config_paths)
    widget_defaults = widget_defaults_catalog(config_paths)
    panel_map = layout_cfg.get("panels", {})
    seen = []
    areas = []
    image_paths = []
    for region_name, region_cfg in regions_cfg.items():
        widget = _widget_name(region_cfg)
        if not widget:
            parser.error(f"scene '{scene_name}' region '{region_name}' has no widget")
        if not _supported_widget(widget):
            parser.error(f"scene '{scene_name}' uses unsupported widget '{widget}'")
        widget_cfg = widget_defaults.get(widget, {})
        panel_names = _parse_region_spec(layout_name, layout_cfg, region_name, parser, scene_name)
        rect = _rect_for_panels(layout_cfg, panel_names, parser, scene_name, region_name)
        area_images = []
        if widget == "image" and isinstance(region_cfg, dict):
            area_images = _region_image_paths(region_cfg)
        if widget == "image" and not area_images:
            area_images = _region_image_paths(widget_cfg)
        if widget == "image" and not area_images:
            area_images = default_images[:]
        area = {
            "name": region_name,
            "mode": widget,
            "panels": panel_names,
            "x": rect["x"],
            "y": rect["y"],
            "w": rect["w"],
            "h": rect["h"],
            "speed": (
                region_cfg.get("speed")
                if isinstance(region_cfg, dict) and region_cfg.get("speed") is not None
                else widget_cfg.get("speed")
            ),
            "text": (
                region_cfg.get("text")
                if isinstance(region_cfg, dict) and region_cfg.get("text") is not None
                else widget_cfg.get("text")
            ),
            "theme": (
                region_cfg.get("source_theme")
                if isinstance(region_cfg, dict) and region_cfg.get("source_theme") is not None
                else widget_cfg.get("source_theme")
            ),
            "colour": _region_colour(region_cfg) or _region_colour(widget_cfg) or default_colour,
            "image_paths": area_images,
            "cycle_widgets": (
                _region_cycle_widgets(region_cfg) or _region_cycle_widgets(widget_cfg)
            ) if widget == "cycle" else [],
            "label": region_cfg.get("label") if isinstance(region_cfg, dict) else None,
            "unavailable_message": region_cfg.get("unavailable_message") if isinstance(region_cfg, dict) else None,
            "static_lines": region_cfg.get("static_lines") if isinstance(region_cfg, dict) else None,
            "static_align": region_cfg.get("static_align") if isinstance(region_cfg, dict) else None,
        }
        overlap = set(panel_names) & set(seen)
        if overlap:
            parser.error(f"scene '{scene_name}' has overlapping panel assignments: {', '.join(sorted(overlap))}")
        seen.extend(panel_names)
        if widget == "image":
            image_paths.extend(area["image_paths"])
        areas.append(area)

    uncovered = [panel_name for panel_name in panel_map if panel_name not in seen]
    if uncovered:
        if not default_widget:
            parser.error(
                f"scene '{scene_name}' leaves panels unassigned ({', '.join(sorted(uncovered))}) and no default widget is configured"
            )
        if not _supported_widget(default_widget):
            parser.error(f"default widget '{default_widget}' is unsupported")
        for panel_name in uncovered:
            panel_cfg = panel_map[panel_name]
            widget_cfg = widget_defaults.get(default_widget, {})
            area_images = _region_image_paths(widget_cfg) if default_widget == "image" else []
            if default_widget == "image" and not area_images:
                area_images = default_images[:]
            areas.append({
                "name": panel_name,
                "mode": default_widget,
                "panels": [panel_name],
                "x": float(panel_cfg["x"]),
                "y": float(panel_cfg["y"]),
                "w": float(panel_cfg["w"]),
                "h": float(panel_cfg["h"]),
                "speed": widget_cfg.get("speed"),
                "text": widget_cfg.get("text"),
                "theme": widget_cfg.get("source_theme"),
                "colour": _region_colour(widget_cfg) or default_colour,
                "image_paths": area_images,
                "cycle_widgets": _region_cycle_widgets(widget_cfg) if default_widget == "cycle" else [],
                "label": None,
                "unavailable_message": None,
                "static_lines": None,
                "static_align": None,
            })
            if default_widget == "image":
                image_paths.extend(area_images)

    return {
        "scene_name": scene_name,
        "theme": theme,
        "speed": speed,
        "text": text,
        "layout": layout_name,
        "areas": areas,
        "image_paths": image_paths,
    }


def resolve_runtime_layout(layout_name: str, regions_cfg: dict[str, Any], parser, *,
                           scene_name: str = "<cli>", theme: str = "science",
                           speed: int | float = 50, text: str = "",
                           default_widget: str | None = None, default_colour: str | None = None,
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    canonical_name = canonical_layout_name(layout_name, config_paths)
    layout_cfg = layouts.get(canonical_name) if canonical_name is not None else None
    if not isinstance(layout_cfg, dict):
        parser.error(f"unknown layout '{layout_name}'")
    return _resolve_runtime_scene(
        scene_name, canonical_name, layout_cfg, regions_cfg, parser,
        theme=theme, speed=speed, text=text,
        default_widget=default_widget, default_colour=default_colour,
        config_paths=config_paths,
    )


def resolve_config_scene(scene_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_scene_catalog(config_paths)
    scenes = catalog.get("scenes", {})
    defaults = config_defaults(config_paths)

    if scene_name not in scenes:
        raise KeyError(scene_name)

    scene_cfg = scenes[scene_name]
    if not isinstance(scene_cfg, dict):
        parser.error(f"scene '{scene_name}' must be a mapping in {_config_label(config_paths)}")

    layout_name = scene_cfg.get("layout")
    regions_cfg = scene_cfg.get("regions", {})
    return resolve_runtime_layout(
        layout_name,
        regions_cfg,
        parser,
        scene_name=scene_name,
        theme=scene_cfg.get("theme", defaults.get("theme", "science")),
        speed=scene_cfg.get("speed", defaults.get("speed", 50)),
        text=scene_cfg.get("text", ""),
        default_widget=defaults.get("widget"),
        default_colour=defaults.get("colour"),
        config_paths=config_paths,
    )
