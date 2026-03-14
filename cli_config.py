"""CLI parsing and startup banner helpers for FakeData Terminal."""

import argparse
import math
import os
import sys

try:
    from .scene_config import (
        config_defaults,
        config_scene_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        resolve_config_scene,
        resolve_runtime_layout,
        validate_scene_catalog,
        widget_names,
    )
except ImportError:
    from scene_config import (
        config_defaults,
        config_scene_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        resolve_config_scene,
        resolve_runtime_layout,
        validate_scene_catalog,
        widget_names,
    )


DEFAULT_THEME = "science"
THEME_CHOICES = [
    "hacker", "science", "medicine", "pharmacy", "finance",
    "space", "military", "navigation", "spaceteam",
]
COLOUR_CHOICES = [
    "red", "orange", "amber", "yellow", "green", "lime", "cyan", "blue",
    "magenta", "purple", "pink", "white", "grey", "multi",
]
COLOUR_HELP = ", ".join(COLOUR_CHOICES)


def _ansi_colour_label(name: str) -> str:
    if not sys.stdout.isatty():
        return name
    codes = {
        "red": "\033[31m",
        "orange": "\033[38;5;208m",
        "amber": "\033[38;5;172m",
        "yellow": "\033[93m",
        "green": "\033[32m",
        "lime": "\033[92m",
        "cyan": "\033[36m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "purple": "\033[38;5;141m",
        "pink": "\033[38;5;213m",
        "white": "\033[97m",
        "grey": "\033[38;5;245m",
        "multi": "\033[1m",
    }
    reset = "\033[0m"
    return f"{codes.get(name, '')}{name}{reset}"


def _scene_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return config_scene_names(config_paths)


def _layout_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return layout_names(config_paths)


def _build_parser(config_paths: tuple[str, ...] | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FakeData Terminal — cinematic terminal data display. "
            "Load the packaged config, then local overlays, then apply CLI overrides. "
            "Use --scene for a preset, or --layout plus --panel-widget overrides to build a screen explicitly. "
            "Run --demo for a quick tour of widgets, themes, layouts, and scenes."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s --list\n"
            "  %(prog)s --config ./lab.yaml --list\n"
            "  %(prog)s --layouts\n"
            "  %(prog)s --demo\n"
            "  %(prog)s --scene test1\n"
            "  %(prog)s --config ~/.config/fakedata-terminal/scenes.yaml --scene lab\n"
            "  %(prog)s --layout grid_2x2 --panel-widget p1=life --panel-widget p2=blank --panel-widget p3=text --panel-widget p4=clock\n"
            "  %(prog)s --scene test1 --panel-widget p4=matrix --panel-speed p4=80\n"
            "  %(prog)s --layout grid_3x3 --panel-widget large_left=image --panel-widget right=clock "
            "--panel-image large_left=geom_07_diamond_lattice.png --panel-image large_left=geom_33_torus.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List configured scenes, layouts, widgets, and colours in columns, then exit.")
    parser.add_argument(
        "--config", action="append", default=[], metavar="PATH",
        help=("Load an extra config overlay. Repeatable. Relative image paths inside that file are "
              "resolved relative to the file itself."))
    parser.add_argument(
        "--layouts", action="store_true",
        help="Show configured layouts as fixed-size box diagrams, with their defined regions, then exit.")
    parser.add_argument(
        "--demo", action="store_true",
        help="Browse a quick tour of widgets, themes, layouts, and configured scenes.")
    parser.add_argument(
        "--scene", type=str, default=None, choices=_scene_choices(config_paths),
        help="Config-defined scene preset.")
    parser.add_argument(
        "--layout", type=str, default=None, choices=_layout_choices(config_paths),
        help="Explicit layout for the generalized panel runtime.")
    parser.add_argument(
        "--theme", type=str, default=None, choices=THEME_CHOICES,
        help=f"Theme. Defaults to {DEFAULT_THEME} unless a scene supplies one.")
    parser.add_argument(
        "--panel-widget", action="append", default=[], metavar="REGION=WIDGET",
        help="Assign a widget to a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-speed", action="append", default=[], metavar="REGION=N",
        help="Override speed for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-title", action="append", default=[], metavar="REGION=TEXT",
        help="Override title for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-theme", action="append", default=[], metavar="REGION=THEME",
        help="Override theme for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-colour", "--panel-color", action="append", default=[], metavar="REGION=VALUE",
        help=f"Override colour for a specific region or panel group. Repeatable. Recognized: {COLOUR_HELP}.")
    parser.add_argument(
        "--panel-image", action="append", default=[], metavar="REGION=PATH",
        help="Add an image path for a specific image region. Repeatable.")
    parser.add_argument(
        "--default-speed", type=int, default=None, metavar="N",
        help="Default speed 1 (slowest) to 100 (no delay) for panels without a panel-specific speed.")
    parser.add_argument(
        "--default-colour", "--default-color", type=str, default=None, metavar="VALUE",
        help=f"Default colour for panels without a panel-specific colour. Recognized: {COLOUR_HELP}.")
    parser.add_argument(
        "--default-widget", type=str, default=None, metavar="WIDGET",
        help="Default widget for panels that are not assigned explicitly.")
    parser.add_argument(
        "--life-max", type=int, default=200, metavar="N",
        help="Maximum iterations before life mode reseeds. Default 200.")
    parser.add_argument(
        "--theme-text", type=str, default=None, metavar="MSG",
        help="Message to inject into text-based widgets.")
    parser.add_argument(
        "--image", nargs="+", default=None, metavar="PATH",
        help="Global image paths fallback for image widgets lacking region-specific image sources.")
    parser.add_argument(
        "--glitch", type=float, default=0.0, const=5.0, nargs="?", metavar="N",
        help=("Glitch interval in seconds. Every ~N seconds a rectangular region "
              "of the display is briefly corrupted then restored. "
              "0 = disabled (default). --glitch alone defaults to 5s."))
    return parser


def _print_list(config_paths: tuple[str, ...] | None = None) -> None:
    for line in _format_catalog_columns(config_paths or (), colourize=True):
        print(line)


def _print_layouts(config_paths: tuple[str, ...] | None = None) -> None:
    print(format_layout_diagrams(config_paths))

def _showcase_widget_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    names = [name for name in widget_names(config_paths) if name != "blank"]
    return names


def _widget_unavailable_reason(widget: str, image_paths: list[str], image_module, image_checker) -> str | None:
    if widget != "image":
        return None
    if not image_paths:
        return "No images configured"
    if image_module is None:
        return "Pillow not installed"
    if not image_checker():
        return "jp2a not installed"
    return None


def _widget_attribute_names(widget: str) -> list[str]:
    widget_attrs = {
        "bars": ["speed", "theme"],
        "blank": [],
        "blocks": ["speed"],
        "clock": ["speed", "colour"],
        "cycle": ["speed", "theme", "colour", "cycle"],
        "image": ["speed", "image"],
        "life": ["speed"],
        "matrix": ["speed"],
        "oscilloscope": ["speed", "theme"],
        "readouts": ["theme", "title", "colour"],
        "sparkline": ["speed", "theme", "colour"],
        "sweep": ["speed"],
        "text": ["speed", "theme", "theme-text"],
        "text_scant": ["speed", "theme", "theme-text"],
        "text_spew": ["speed", "theme", "theme-text"],
        "text_wide": ["speed", "theme", "theme-text"],
        "tunnel": ["speed", "colour"],
    }
    return widget_attrs.get(widget, ["speed"])


def _format_widget_catalog_entry(widget: str) -> str:
    attrs = ",".join(_widget_attribute_names(widget))
    return f"{widget} [{attrs}]"


def _format_catalog_columns(config_paths: tuple[str, ...], *, colourize: bool = False) -> list[str]:
    widgets = [_format_widget_catalog_entry(name) for name in widget_names(config_paths)]
    layouts = layout_names(config_paths)
    themes = THEME_CHOICES[:]
    scenes = config_scene_names(config_paths)
    colours = [_ansi_colour_label(name) for name in COLOUR_CHOICES] if colourize else COLOUR_CHOICES[:]
    columns = [
        ("Scenes", scenes),
        ("Layouts", layouts),
        ("Widgets", widgets),
        ("Themes", themes),
        ("Colours", colours),
    ]
    widths = []
    for heading, values in columns:
        longest = max([len(heading), *(len(value) for value in values)] or [len(heading)])
        widths.append(longest + 2)
    height = max(len(values) for _, values in columns)
    lines = []
    heading_line = "    ".join(f"{heading:<{widths[idx]}}" for idx, (heading, _) in enumerate(columns))
    rule_line = "    ".join("-" * (widths[idx] - 1) for idx in range(len(columns)))
    lines.extend([heading_line.rstrip(), rule_line.rstrip(), ""])
    for row in range(height):
        parts = []
        for idx, (_, values) in enumerate(columns):
            entry = values[row] if row < len(values) else ""
            parts.append(f"{entry:<{widths[idx]}}")
        lines.append("    ".join(parts).rstrip())
    lines.extend(["", "Config files:"])
    lines.extend(str(path) for path in config_paths)
    defaults = config_defaults(config_paths)
    default_colour = defaults.get("colour")
    if colourize and default_colour:
        default_colour = _ansi_colour_label(str(default_colour))
    lines.extend([
        "",
        "Configured defaults:",
        f"layout: {defaults.get('layout') if defaults.get('layout') is not None else '(none)'}",
        f"speed: {defaults.get('speed', 50)}",
        f"colour: {default_colour if default_colour is not None else '(none)'}",
        f"widget: {defaults.get('widget') if defaults.get('widget') is not None else '(none)'}",
    ])
    return lines


def _build_intro_scene(theme: str, speed: int, parser, config_paths: tuple[str, ...]) -> dict:
    runtime = resolve_runtime_layout(
        "full",
        {"full": {"widget": "blank"}},
        parser,
        scene_name="<demo:intro>",
        theme=theme,
        speed=speed,
        text="",
        config_paths=config_paths,
    )
    runtime["areas"][0]["static_lines"] = [
        "FakeData Terminal is a curses-based dashboard generator for animated, fake telemetry and operator screens.",
        "This demo pages through the available widgets, themes, layouts, scenes, and active config files.",
        "",
        *_format_catalog_columns(config_paths),
    ]
    return runtime


def _static_blank_region(lines: list[str], *, align: str = "center") -> dict:
    return {
        "widget": "blank",
        "static_lines": lines,
        "static_align": align,
    }


def _build_widget_scenes(theme: str, speed: int, text: str, image_paths: list[str], parser,
                         image_module, image_checker,
                         config_paths: tuple[str, ...]) -> list[dict]:
    widgets = _showcase_widget_names(config_paths)
    if not widgets:
        parser.error("--demo found no widgets to show")

    scenes = []
    region_keys = ["p1+p2+p4+p5", "p3+p6", "p7", "p8+p9"]
    for widget in widgets:
        unavailable = _widget_unavailable_reason(widget, image_paths, image_module, image_checker)
        if widget == "cycle":
            region_cfg = _static_blank_region([
                "cycle",
                "",
                "Rotates one panel through a configured widget list.",
                "Use widget: cycle with cycle.widgets in scene config",
                "or assign it to a region from the CLI.",
            ])
            regions_cfg = {region_key: dict(region_cfg) for region_key in region_keys}
        elif unavailable:
            region_cfg = _static_blank_region([widget, "", unavailable])
            regions_cfg = {region_key: dict(region_cfg) for region_key in region_keys}
        else:
            region_cfg = {"widget": widget}
            if widget == "image":
                region_cfg["image"] = {"paths": image_paths[:]}
            regions_cfg = {region_key: dict(region_cfg) for region_key in region_keys}
        runtime = resolve_runtime_layout(
            "grid_3x3",
            regions_cfg,
            parser,
            scene_name=f"<demo:widgets:{widget}>",
            theme=theme,
            speed=speed,
            text=text,
            config_paths=config_paths,
        )
        runtime["showcase_header_lines"] = [f"widget: {widget}"]
        scenes.append(runtime)
    return scenes


def _build_theme_scenes(speed: int, text: str, parser, config_paths: tuple[str, ...]) -> list[dict]:
    scenes = []
    for theme_name in THEME_CHOICES:
        runtime = resolve_runtime_layout(
            "grid_3x3",
            {
                "left": {"widget": "text"},
                "center": {"widget": "text_wide"},
                "p7": {"widget": "readouts"},
                "p8+p9": {"widget": "text_scant"},
            },
            parser,
            scene_name=f"<demo:theme:{theme_name}>",
            theme=theme_name,
            speed=speed,
            text=text,
            config_paths=config_paths,
        )
        runtime["showcase_header_lines"] = [f"theme: {theme_name}"]
        scenes.append(runtime)
    return scenes


def _build_layout_scenes(theme: str, speed: int, parser, config_paths: tuple[str, ...]) -> list[dict]:
    scenes = []
    layouts = layout_catalog(config_paths)
    for layout_name, layout_cfg in layouts.items():
        panels = layout_cfg.get("panels", {})
        regions_cfg = {
            panel_name: _static_blank_region([panel_name])
            for panel_name in panels
        }
        runtime = resolve_runtime_layout(
            layout_name,
            regions_cfg,
            parser,
            scene_name=f"<demo:layout:{layout_name}>",
            theme=theme,
            speed=speed,
            text="",
            config_paths=config_paths,
        )
        runtime["showcase_header_lines"] = [
            f"layout: {layout_name}",
            "(adjacent panels can be combined)",
        ]
        scenes.append(runtime)
    return scenes


def _build_scene_scenes(parser, config_paths: tuple[str, ...]) -> list[dict]:
    scenes = []
    for scene_name in config_scene_names(config_paths):
        runtime = resolve_config_scene(scene_name, parser, config_paths)
        runtime["showcase_header_lines"] = [f"scene: {scene_name}"]
        scenes.append(runtime)
    return scenes


def _build_demo_showcase(theme: str, speed: int, text: str, image_paths: list[str], parser,
                         image_module, image_checker,
                         config_paths: tuple[str, ...] | None = None) -> dict:
    resolved_paths = config_paths or ()
    scenes = [_build_intro_scene(theme, speed, parser, resolved_paths)]
    scenes.extend(_build_widget_scenes(theme, speed, text, image_paths, parser, image_module, image_checker, resolved_paths))
    scenes.extend(_build_theme_scenes(speed, text, parser, resolved_paths))
    scenes.extend(_build_layout_scenes(theme, speed, parser, resolved_paths))
    scenes.extend(_build_scene_scenes(parser, resolved_paths))
    initial = scenes[0]
    return {
        "active": True,
        "scenes": scenes,
        "idx": 0,
        "next": float("inf"),
        "pair_duration": 10.0,
        "done": False,
        "initial": initial,
    }


def _parse_equals(expr: str, parser, flag_name: str) -> tuple[str, str]:
    if "=" not in expr:
        parser.error(f"{flag_name} expects NAME=VALUE, got '{expr}'")
    left, right = expr.split("=", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        parser.error(f"{flag_name} expects NAME=VALUE, got '{expr}'")
    return left, right


def _normalize_region_key(layout_name: str, region_expr: str, parser, flag_name: str,
                          config_paths: tuple[str, ...] | None = None) -> str:
    layouts = layout_catalog(config_paths)
    layout_cfg = layouts.get(layout_name)
    if not isinstance(layout_cfg, dict):
        parser.error(f"unknown layout '{layout_name}'")
    panels = layout_cfg.get("panels", {})
    aliases = layout_cfg.get("regions", {})

    spec = aliases.get(region_expr, region_expr)
    panel_names = [part.strip() for part in str(spec).split("+") if part.strip()]
    if not panel_names:
        parser.error(f"{flag_name} references an empty region '{region_expr}'")
    for panel_name in panel_names:
        if panel_name not in panels:
            parser.error(f"{flag_name} references unknown panel '{panel_name}' in region '{region_expr}'")
    return "+".join(panel_names)


def _apply_panel_widget_overrides(base_scene: dict | None, panel_widgets: list[str], panel_speeds: list[str],
                            panel_titles: list[str], panel_themes: list[str], panel_colours: list[str], panel_images: list[str],
                            parser, *, layout_name: str, scene_name: str, theme: str,
                            speed: int, text: str, default_widget: str | None, default_colour: str | None,
                            config_paths: tuple[str, ...] | None = None) -> dict:
    regions_cfg = {}
    if base_scene:
        for area in base_scene["areas"]:
            region_key = "+".join(area["panels"])
            entry = {"widget": area["mode"]}
            if area.get("speed") is not None:
                entry["speed"] = area["speed"]
            if area.get("title"):
                entry["title"] = area["title"]
            if area.get("theme"):
                entry["source_theme"] = area["theme"]
            if area.get("colour"):
                entry["colour"] = area["colour"]
            if area.get("image_paths"):
                entry["image"] = {"paths": area["image_paths"][:]}
            if area.get("cycle_widgets"):
                entry["cycle"] = {"widgets": area["cycle_widgets"][:]}
            regions_cfg[region_key] = entry

    for item in panel_widgets:
        target, widget = _parse_equals(item, parser, "--panel-widget")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-widget", config_paths)
        target_panels = set(normalized_target.split("+"))
        to_delete = []
        for existing_key in list(regions_cfg):
            existing_panels = set(existing_key.split("+"))
            overlap = existing_panels & target_panels
            if not overlap:
                continue
            if existing_panels == target_panels:
                to_delete.append(existing_key)
                continue
            if existing_panels < target_panels:
                to_delete.append(existing_key)
                continue
            if target_panels < existing_panels:
                parser.error(
                    f"--panel-widget {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
            else:
                parser.error(
                    f"--panel-widget {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
        for existing_key in to_delete:
            del regions_cfg[existing_key]
        current = regions_cfg.get(normalized_target, {})
        current["widget"] = widget
        regions_cfg[normalized_target] = current

    for item in panel_speeds:
        target, speed_text = _parse_equals(item, parser, "--panel-speed")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-speed", config_paths)
        try:
            panel_speed = int(speed_text)
        except ValueError:
            parser.error(f"--panel-speed expects an integer speed, got '{speed_text}'")
        if not 1 <= panel_speed <= 100:
            parser.error("--panel-speed must be between 1 and 100")
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-speed target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["speed"] = panel_speed

    for item in panel_titles:
        target, title_text = _parse_equals(item, parser, "--panel-title")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-title", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-title target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["title"] = title_text

    for item in panel_themes:
        target, theme_name = _parse_equals(item, parser, "--panel-theme")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-theme", config_paths)
        if theme_name not in THEME_CHOICES:
            parser.error(f"--panel-theme must be one of: {', '.join(THEME_CHOICES)}")
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-theme target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["source_theme"] = theme_name

    for item in panel_colours:
        target, colour_name = _parse_equals(item, parser, "--panel-colour")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-colour", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-colour target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["colour"] = colour_name

    for item in panel_images:
        target, image_path = _parse_equals(item, parser, "--panel-image")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-image", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-image target '{target}' has no matching assignment")
        if regions_cfg[normalized_target].get("widget") != "image":
            parser.error(f"--panel-image target '{target}' is not assigned to widget 'image'")
        image_cfg = regions_cfg[normalized_target].setdefault("image", {})
        image_cfg.setdefault("paths", []).append(image_path)

    return resolve_runtime_layout(
        layout_name,
        regions_cfg,
        parser,
        scene_name=scene_name,
        theme=theme,
        speed=speed,
        text=text,
        default_widget=default_widget,
        default_colour=default_colour,
        config_paths=config_paths,
    )


def _resolve_config_paths(raw_argv: list[str]) -> tuple[str, ...]:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", action="append", default=[], metavar="PATH")
    config_args, _ = config_parser.parse_known_args(raw_argv)
    ordered_paths = [str(path) for path in discover_config_paths()] + config_args.config
    deduped = []
    seen = set()
    for path in ordered_paths:
        expanded = os.path.abspath(os.path.expanduser(path))
        if expanded in seen:
            continue
        seen.add(expanded)
        deduped.append(expanded)
    return tuple(deduped)


def prepare_runtime_config(argv, image_module, image_checker, demo_scenes):
    del demo_scenes
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    config_paths = _resolve_config_paths(raw_argv)
    parser = _build_parser(config_paths)

    args = parser.parse_args(raw_argv)

    issues = validate_scene_catalog(config_paths)
    if issues:
        parser.error("scenes.yaml validation failed:\n  " + "\n  ".join(issues))

    if args.list:
        _print_list(config_paths)
        raise SystemExit(0)

    if args.layouts:
        _print_layouts(config_paths)
        raise SystemExit(0)

    if args.demo and (args.scene is not None or args.layout is not None or args.panel_widget or args.panel_speed or args.panel_title or args.panel_theme or args.panel_colour or args.panel_image or args.default_speed is not None or args.default_colour is not None or args.default_widget is not None):
        parser.error("--demo is a standalone showcase mode; do not combine it with --scene, --layout, or panel overrides")

    if not args.demo and args.scene is None and args.layout is None and config_defaults(config_paths).get("layout") is None:
        parser.error("specify either --scene, --layout, or --demo, or configure defaults.layout")

    speed_explicit = any(a == "--default-speed" or a.startswith("--default-speed=") for a in raw_argv)
    colour_explicit = any(a in {"--default-colour", "--default-color"} or a.startswith("--default-colour=") or a.startswith("--default-color=") for a in raw_argv)
    widget_explicit = any(a == "--default-widget" or a.startswith("--default-widget=") for a in raw_argv)
    text_explicit = any(a == "--theme-text" or a.startswith("--theme-text=") for a in raw_argv)
    image_explicit = any(a == "--image" or a.startswith("--image=") for a in raw_argv)

    configured_defaults = config_defaults(config_paths)
    default_images = default_image_paths(config_paths)
    image_paths = []
    if args.image is not None and len(args.image) < 1:
        parser.error("--image expects at least one file path")
    if image_explicit and args.image:
        for raw_path in args.image:
            path = os.path.abspath(os.path.expanduser(raw_path))
            if not os.path.isfile(path):
                parser.error(f"image file not found: {raw_path}")
            image_paths.append(path)

    runtime_speed = args.default_speed if speed_explicit and args.default_speed is not None else configured_defaults.get("speed", 50)
    runtime_text = args.theme_text.strip() if text_explicit and args.theme_text is not None else ""
    runtime_theme = args.theme or configured_defaults.get("theme", DEFAULT_THEME)
    runtime_default_colour = args.default_colour if colour_explicit and args.default_colour is not None else configured_defaults.get("colour")
    runtime_default_widget = args.default_widget if widget_explicit and args.default_widget is not None else configured_defaults.get("widget")
    widget_showcase = {"active": False, "scenes": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

    if not image_explicit:
        image_paths = default_images[:]

    if args.demo:
        widget_showcase = _build_demo_showcase(
            runtime_theme,
            runtime_speed,
            runtime_text,
            image_paths,
            parser,
            image_module,
            image_checker,
            config_paths,
        )
        config_scene_runtime = widget_showcase["initial"]
        runtime_layout_name = config_scene_runtime["layout"]
    else:
        base_runtime = resolve_config_scene(args.scene, parser, config_paths) if args.scene else None
        runtime_layout_name = args.layout or (base_runtime["layout"] if base_runtime else configured_defaults.get("layout"))
        if not runtime_layout_name:
            parser.error("no layout available")

        runtime_theme = args.theme or (base_runtime["theme"] if base_runtime else configured_defaults.get("theme", DEFAULT_THEME))
        runtime_speed = args.default_speed if speed_explicit and args.default_speed is not None else (base_runtime["speed"] if base_runtime else configured_defaults.get("speed", 50))
        runtime_text = args.theme_text.strip() if text_explicit and args.theme_text is not None else (base_runtime["text"] if base_runtime else "")

        has_cli_overrides = bool(
            args.layout or args.panel_widget or args.panel_speed or args.panel_title or args.panel_theme or args.panel_colour or args.panel_image or args.theme or speed_explicit or colour_explicit or widget_explicit
        )
        if base_runtime is None or has_cli_overrides:
            config_scene_runtime = _apply_panel_widget_overrides(
                base_runtime if (base_runtime and not args.layout) else None,
                args.panel_widget,
                args.panel_speed,
                args.panel_title,
                args.panel_theme,
                args.panel_colour,
                args.panel_image,
                parser,
                layout_name=runtime_layout_name,
                scene_name=args.scene or f"<cli:{runtime_layout_name}>",
                theme=runtime_theme,
                speed=runtime_speed,
                text=runtime_text,
                default_widget=runtime_default_widget,
                default_colour=runtime_default_colour,
                config_paths=config_paths,
            )
        else:
            config_scene_runtime = base_runtime

    if runtime_default_colour is not None:
        for area in config_scene_runtime["areas"]:
            if not area.get("colour"):
                area["colour"] = runtime_default_colour

    if runtime_speed is None:
        runtime_speed = config_scene_runtime["speed"]

    if not 1 <= runtime_speed <= 100:
        parser.error("--default-speed must be between 1 and 100")
    if runtime_default_widget is not None and runtime_default_widget not in widget_names(config_paths):
        parser.error(f"--default-widget must be one of: {', '.join(widget_names(config_paths))}")
    if args.life_max < 1:
        parser.error("--life-max must be at least 1")

    image_sources = config_scene_runtime["image_paths"] if not image_explicit else image_paths
    image_mode_active = any(area["mode"] == "image" for area in config_scene_runtime["areas"])
    if args.demo:
        image_mode_active = any(
            area["mode"] == "image"
            for scene in widget_showcase["scenes"]
            for area in scene["areas"]
        )
    if image_mode_active and not image_paths and not any(area.get("image_paths") for area in config_scene_runtime["areas"]):
        parser.error("image mode requires --image PATH [PATH ...] or --panel-image REGION=PATH")
    if image_mode_active and image_module is None:
        parser.error("image mode requires Pillow to be installed")
    if image_mode_active and not image_checker():
        parser.error("image mode requires jp2a to be installed")

    return {
        "speed": runtime_speed,
        "main_speed": runtime_speed,
        "sidebar_speed": runtime_speed,
        "life_max": args.life_max,
        "theme_text": runtime_text,
        "main_mode": None,
        "sidebar_mode": None,
        "theme": config_scene_runtime["theme"],
        "scene_name": "<demo>" if args.demo else (args.scene or f"<cli:{runtime_layout_name}>"),
        "themes": THEME_CHOICES[:],
        "config_scene": config_scene_runtime,
        "layout_name": config_scene_runtime["layout"],
        "area_summary": ", ".join(f"{area['name']}={area['mode']}" for area in config_scene_runtime["areas"]),
        "demo_state": {"active": False, "scenes": [], "idx": 0, "scene": None, "next": float("inf"), "done": False},
        "widget_showcase": widget_showcase,
        "glitch_interval": max(0.0, args.glitch if args.glitch is not None else 0.0),
        "image_paths": image_sources,
        "configured_defaults": configured_defaults,
        "default_colour": runtime_default_colour,
        "default_widget": runtime_default_widget,
    }


def _show_delay(speed: int) -> str:
    if speed >= 100:
        return "no delay (flat-out)"
    lo, hi = math.log(0.004), math.log(1.0)
    delay = math.exp(hi + (speed - 1) / 98 * (lo - hi))
    return f"~{delay:.3f} s/line centre"


def show_startup_banner(script_name: str, config: dict) -> None:
    bold = "\033[1m"
    cyan = "\033[36m"
    dim = "\033[2m"
    reset = "\033[0m"

    print(reset)
    print(f"  {cyan}{script_name}{reset}  —  FakeData Terminal")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {bold}speed{reset}  : default {config['speed']}/100", end="")
    print(f"  ({_show_delay(config['speed'])})")
    print(f"  {bold}scene{reset}  : {config['scene_name']}")
    print(f"  {bold}theme{reset}  : {config['theme']}")
    if config.get("default_colour") is not None:
        print(f"  {bold}colour{reset} : default {config['default_colour']}")
    if config.get("default_widget") is not None:
        print(f"  {bold}widget{reset} : default {config['default_widget']}")
    if config["image_paths"]:
        label = "image" if len(config["image_paths"]) == 1 else "images"
        print(f"  {bold}{label}{reset} : {', '.join(config['image_paths'])}")
    if config["theme_text"]:
        print(f"  {bold}theme text{reset} : '{config['theme_text']}'")
    else:
        print(f"  {bold}theme text{reset} : (none)")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {bold}layout{reset} : {config['layout_name']}")
    if config["area_summary"]:
        print(f"  {bold}areas{reset}  : {config['area_summary']}")
    glitch_str = f"every ~{config['glitch_interval']:.1f}s" if config["glitch_interval"] > 0 else "off"
    print(f"  {bold}glitch{reset} : {glitch_str}")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {dim}Press Q or Ctrl-C to quit  |  Space to pause  |  + / - to change speed live{reset}")
    print()
