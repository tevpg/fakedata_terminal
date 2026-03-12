"""Load YAML style definitions, merge overlays, and adapt them to the runtime."""

from __future__ import annotations

from functools import lru_cache
import glob
import os
from pathlib import Path
from typing import Any

import yaml


PACKAGE_DIR = Path(__file__).resolve().parent
STYLE_CONFIG_PATH = PACKAGE_DIR / "data" / "styles.yaml"
USER_CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fakedata-terminal" / "styles.yaml"
PROJECT_CONFIG_NAMES = (
    ".fakedata-terminal.yaml",
    ".fakedata-terminal.yml",
)

TOP_LEVEL_KEYS = {"defaults", "layouts", "styles", "widgets"}
DEFAULT_KEYS = {"vocab", "speed", "panel_speed", "image"}
LAYOUT_KEYS = {"panels", "regions"}
PANEL_KEYS = {"x", "y", "w", "h"}
STYLE_KEYS = {"note", "layout", "vocab", "speed", "text", "regions"}
REGION_KEYS = {"widget", "speed", "title", "source_vocab", "image", "paths", "path", "glob", "cycle"}
IMAGE_KEYS = {"paths", "path", "glob"}
CYCLE_KEYS = {"widgets"}


def discover_config_paths() -> list[Path]:
    paths = [STYLE_CONFIG_PATH]
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
        raise ValueError(f"Style config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Style config root must be a mapping: {path}")
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
def load_style_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    normalized_paths = _normalize_config_paths(config_paths)
    catalog: dict[str, Any] = {}
    for config_path in normalized_paths:
        catalog = _merge_catalogs(catalog, _load_catalog_file(config_path))
    return catalog


def config_style_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_style_catalog(config_paths)
    styles = catalog.get("styles", {})
    if not isinstance(styles, dict):
        return []
    return list(styles.keys())


def layout_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_style_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    if not isinstance(layouts, dict):
        return []
    return list(layouts.keys())


def layout_catalog(config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_style_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    return layouts if isinstance(layouts, dict) else {}


def widget_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_style_catalog(config_paths)
    widgets = catalog.get("widgets", {})
    names = set()
    if isinstance(widgets, dict):
        for value in widgets.values():
            if isinstance(value, list):
                names.update(str(item) for item in value)
    names.update({
        "text", "text_wide", "text_scant", "text_spew", "image", "life",
        "bars", "clock", "matrix", "oscilloscope", "blocks", "sweep",
        "sparkline", "readouts", "blank", "cycle",
    })
    return sorted(names)


def default_image_paths(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_style_catalog(config_paths)
    defaults = catalog.get("defaults", {})
    if not isinstance(defaults, dict):
        return []
    return _expand_image_spec(defaults.get("image"))


def validate_style_catalog(config_paths: tuple[str, ...] | None = None) -> list[str]:
    catalog = load_style_catalog(config_paths)
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

    styles = catalog.get("styles", {})
    if styles is not None:
        if not isinstance(styles, dict):
            issues.append(f"{config_label}: styles must be a mapping")
        else:
            layout_names_set = set(layout_names(config_paths))
            for style_name, style_cfg in styles.items():
                if not isinstance(style_cfg, dict):
                    issues.append(f"{config_label}: style '{style_name}' must be a mapping")
                    continue
                _unknown_keys(style_cfg, STYLE_KEYS, f"styles.{style_name}", issues)
                layout_name = style_cfg.get("layout")
                if layout_name and layout_name not in layout_names_set:
                    issues.append(f"{config_label}: style '{style_name}' references unknown layout '{layout_name}'")
                regions = style_cfg.get("regions", {})
                if not isinstance(regions, dict):
                    issues.append(f"{config_label}: style '{style_name}' regions must be a mapping")
                    continue
                for region_name, region_cfg in regions.items():
                    if not isinstance(region_cfg, dict):
                        issues.append(
                            f"{config_label}: style '{style_name}' region '{region_name}' must be a mapping"
                        )
                        continue
                    _unknown_keys(region_cfg, REGION_KEYS, f"styles.{style_name}.regions.{region_name}", issues)
                    widget = region_cfg.get("widget")
                    if widget is None:
                        issues.append(
                            f"{config_label}: style '{style_name}' region '{region_name}' is missing 'widget'"
                        )
                    elif not _supported_widget(str(widget)):
                        issues.append(
                            f"{config_label}: style '{style_name}' region '{region_name}' uses unsupported widget '{widget}'"
                        )
                    cycle_spec = region_cfg.get("cycle")
                    if cycle_spec is not None and not isinstance(cycle_spec, dict):
                        issues.append(
                            f"{config_label}: style '{style_name}' region '{region_name}' cycle must be a mapping"
                        )
                    elif isinstance(cycle_spec, dict):
                        _unknown_keys(cycle_spec, CYCLE_KEYS, f"styles.{style_name}.regions.{region_name}.cycle", issues)
                        widgets = cycle_spec.get("widgets")
                        if widgets is not None and not isinstance(widgets, list):
                            issues.append(
                                f"{config_label}: style '{style_name}' region '{region_name}' cycle.widgets must be a list"
                            )
                        elif isinstance(widgets, list):
                            if str(widget) != "cycle":
                                issues.append(
                                    f"{config_label}: style '{style_name}' region '{region_name}' defines cycle.widgets but widget is '{widget}'"
                                )
                            for idx, cycle_widget in enumerate(widgets):
                                cycle_widget_name = str(cycle_widget)
                                if not _supported_widget(cycle_widget_name):
                                    issues.append(
                                        f"{config_label}: style '{style_name}' region '{region_name}' cycle.widgets[{idx}] uses unsupported widget '{cycle_widget_name}'"
                                    )
                                elif cycle_widget_name in {"cycle", "blank"}:
                                    issues.append(
                                        f"{config_label}: style '{style_name}' region '{region_name}' cycle.widgets[{idx}] may not be '{cycle_widget_name}'"
                                    )
                    image_spec = region_cfg.get("image")
                    if image_spec is not None and not isinstance(image_spec, dict):
                        issues.append(
                            f"{config_label}: style '{style_name}' region '{region_name}' image must be a mapping"
                        )
                    elif isinstance(image_spec, dict):
                        _unknown_keys(image_spec, IMAGE_KEYS, f"styles.{style_name}.regions.{region_name}.image", issues)

    widgets = catalog.get("widgets", {})
    if widgets is not None and not isinstance(widgets, dict):
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

    lines = [f"Layout: {layout_name}"] + ["".join(row).rstrip() for row in canvas]
    if regions:
        lines.append("Regions:")
        for region_name, region_spec in regions.items():
            lines.append(f"  {region_name}: {region_spec}")
    return "\n".join(lines)


def _supported_widget(widget: str) -> bool:
    return widget in {
        "text", "text_wide", "text_scant", "text_spew", "image", "life",
        "bars", "clock", "matrix", "oscilloscope", "blocks", "sweep",
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
    return "merged style config"


def _resolve_config_path(pathish: Any, base_dir: Path) -> str:
    path = Path(str(pathish)).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _normalize_image_mapping(image_spec: Any, base_dir: Path) -> None:
    if not isinstance(image_spec, dict):
        return
    if isinstance(image_spec.get("paths"), list):
        image_spec["paths"] = [_resolve_config_path(path, base_dir) for path in image_spec["paths"]]
    if image_spec.get("path") is not None:
        image_spec["path"] = _resolve_config_path(image_spec["path"], base_dir)
    if image_spec.get("glob") is not None:
        image_spec["glob"] = _resolve_config_path(image_spec["glob"], base_dir)


def _normalize_catalog_paths(catalog: dict[str, Any], source_path: Path) -> dict[str, Any]:
    base_dir = source_path.parent
    defaults = catalog.get("defaults")
    if isinstance(defaults, dict):
        _normalize_image_mapping(defaults.get("image"), base_dir)
    styles = catalog.get("styles")
    if isinstance(styles, dict):
        for style_cfg in styles.values():
            if not isinstance(style_cfg, dict):
                continue
            regions = style_cfg.get("regions")
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


def adapt_style_to_legacy(style_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_style_catalog(config_paths)
    styles = catalog.get("styles", {})
    defaults = catalog.get("defaults", {})

    if style_name not in styles:
        raise KeyError(style_name)

    style_cfg = styles[style_name]
    if not isinstance(style_cfg, dict):
        parser.error(f"style '{style_name}' must be a mapping in {_config_label(config_paths)}")

    layout = style_cfg.get("layout")
    regions = style_cfg.get("regions", {})
    if not isinstance(regions, dict):
        parser.error(f"style '{style_name}' regions must be a mapping in {_config_label(config_paths)}")

    style_speed = style_cfg.get("speed", defaults.get("speed", 50))
    vocab = style_cfg.get("vocab", defaults.get("vocab", "science"))

    if layout == "full":
        full_cfg = regions.get("full")
        widget = _widget_name(full_cfg)
        if not widget:
            parser.error(f"style '{style_name}' uses layout 'full' but has no 'full' widget assignment")
        if not _supported_widget(widget) or widget in {"sparkline", "readouts"}:
            parser.error(f"style '{style_name}' uses widget '{widget}', which is not supported by the legacy runtime")
        return {
            "style_name": style_name,
            "vocab": vocab,
            "speed": style_speed,
            "main_mode": widget,
            "sidebar_mode": "none",
            "main_speed": full_cfg.get("speed") if isinstance(full_cfg, dict) else None,
            "sidebar_speed": None,
            "text": style_cfg.get("text", ""),
            "image_paths": _expand_image_spec(full_cfg.get("image")) if isinstance(full_cfg, dict) else [],
        }

    if layout == "split_left_right":
        left_cfg = regions.get("left")
        right_cfg = regions.get("right")
        left_widget = _widget_name(left_cfg)
        right_widget = _widget_name(right_cfg)
        if not left_widget or not right_widget:
            parser.error(f"style '{style_name}' uses layout 'split_left_right' but must define both 'left' and 'right'")
        if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}
                or not _supported_widget(right_widget) or right_widget in {"sparkline", "readouts"}):
            bad = left_widget if (not _supported_widget(left_widget) or left_widget in {"sparkline", "readouts"}) else right_widget
            parser.error(f"style '{style_name}' uses widget '{bad}', which is not supported by the legacy runtime")
        return {
            "style_name": style_name,
            "vocab": vocab,
            "speed": style_speed,
            "main_mode": left_widget,
            "sidebar_mode": right_widget,
            "main_speed": left_cfg.get("speed") if isinstance(left_cfg, dict) else None,
            "sidebar_speed": right_cfg.get("speed") if isinstance(right_cfg, dict) else None,
            "text": style_cfg.get("text", ""),
            "image_paths": (
                _expand_image_spec(left_cfg.get("image")) if left_widget == "image" and isinstance(left_cfg, dict) else
                _expand_image_spec(right_cfg.get("image")) if right_widget == "image" and isinstance(right_cfg, dict) else
                []
            ),
        }

    parser.error(
        f"style '{style_name}' uses layout '{layout}', which is not yet supported by the current runtime; "
        "currently supported config layouts: full, split_left_right"
    )


def _parse_region_spec(layout_cfg: dict[str, Any], region_name: str, parser, style_name: str) -> list[str]:
    panels = layout_cfg.get("panels", {})
    aliases = layout_cfg.get("regions", {})
    if region_name in aliases:
        spec = aliases[region_name]
    else:
        spec = region_name
    panel_names = [part.strip() for part in str(spec).split("+") if part.strip()]
    if not panel_names:
        parser.error(f"style '{style_name}' has empty region spec for '{region_name}'")
    for panel_name in panel_names:
        if panel_name not in panels:
            parser.error(f"style '{style_name}' references unknown panel '{panel_name}' in region '{region_name}'")
    return panel_names


def _rect_for_panels(layout_cfg: dict[str, Any], panel_names: list[str], parser, style_name: str, region_name: str) -> dict[str, float]:
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
            f"style '{style_name}' region '{region_name}' does not resolve to a single rectangle"
        )
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _resolve_runtime_style(style_name: str, layout_name: str, layout_cfg: dict[str, Any],
                           regions_cfg: dict[str, Any], parser, *,
                           vocab: str, speed: int | float, text: str,
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    if not isinstance(regions_cfg, dict):
        parser.error(f"style '{style_name}' regions must be a mapping in {STYLE_CONFIG_PATH.name}")

    default_images = default_image_paths(config_paths)
    seen = []
    areas = []
    image_paths = []
    for region_name, region_cfg in regions_cfg.items():
        widget = _widget_name(region_cfg)
        if not widget:
            parser.error(f"style '{style_name}' region '{region_name}' has no widget")
        if not _supported_widget(widget):
            parser.error(f"style '{style_name}' uses unsupported widget '{widget}'")
        panel_names = _parse_region_spec(layout_cfg, region_name, parser, style_name)
        rect = _rect_for_panels(layout_cfg, panel_names, parser, style_name, region_name)
        area_images = []
        if widget == "image" and isinstance(region_cfg, dict):
            area_images = _region_image_paths(region_cfg)
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
            "speed": region_cfg.get("speed") if isinstance(region_cfg, dict) else None,
            "title": region_cfg.get("title") if isinstance(region_cfg, dict) else None,
            "vocab": region_cfg.get("source_vocab") if isinstance(region_cfg, dict) else None,
            "image_paths": area_images,
            "cycle_widgets": _region_cycle_widgets(region_cfg) if widget == "cycle" else [],
        }
        overlap = set(panel_names) & set(seen)
        if overlap:
            parser.error(f"style '{style_name}' has overlapping panel assignments: {', '.join(sorted(overlap))}")
        seen.extend(panel_names)
        if widget == "image":
            image_paths.extend(area["image_paths"])
        areas.append(area)

    return {
        "style_name": style_name,
        "vocab": vocab,
        "speed": speed,
        "text": text,
        "layout": layout_name,
        "areas": areas,
        "image_paths": image_paths,
    }


def resolve_runtime_layout(layout_name: str, regions_cfg: dict[str, Any], parser, *,
                           style_name: str = "<cli>", vocab: str = "science",
                           speed: int | float = 50, text: str = "",
                           config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_style_catalog(config_paths)
    layouts = catalog.get("layouts", {})
    layout_cfg = layouts.get(layout_name)
    if not isinstance(layout_cfg, dict):
        parser.error(f"unknown layout '{layout_name}'")
    return _resolve_runtime_style(
        style_name, layout_name, layout_cfg, regions_cfg, parser,
        vocab=vocab, speed=speed, text=text,
        config_paths=config_paths,
    )


def resolve_config_style(style_name: str, parser, config_paths: tuple[str, ...] | None = None) -> dict[str, Any]:
    catalog = load_style_catalog(config_paths)
    styles = catalog.get("styles", {})
    defaults = catalog.get("defaults", {})

    if style_name not in styles:
        raise KeyError(style_name)

    style_cfg = styles[style_name]
    if not isinstance(style_cfg, dict):
        parser.error(f"style '{style_name}' must be a mapping in {_config_label(config_paths)}")

    layout_name = style_cfg.get("layout")
    regions_cfg = style_cfg.get("regions", {})
    return resolve_runtime_layout(
        layout_name,
        regions_cfg,
        parser,
        style_name=style_name,
        vocab=style_cfg.get("vocab", defaults.get("vocab", "science")),
        speed=style_cfg.get("speed", defaults.get("speed", 50)),
        text=style_cfg.get("text", ""),
    )
