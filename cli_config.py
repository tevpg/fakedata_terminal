"""CLI parsing and startup banner helpers for FakeData Terminal."""

import argparse
import math
import os
import re
import shutil
import sys

try:
    from .runtime_support import COLOUR_CATALOG_COLUMNS, COLOUR_CHOICES, ansi_colour_label, normalize_colour_spec
    from .scene_config import (
        _direction_value,
        config_defaults,
        canonical_layout_name,
        config_scene_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        normalize_region_expr,
        resolve_config_scene,
        resolve_runtime_layout,
        validate_scene_catalog,
        widget_names,
    )
    from .widget_metadata import validate_widget_metadata, widget_supports
except ImportError:
    from runtime_support import COLOUR_CATALOG_COLUMNS, COLOUR_CHOICES, ansi_colour_label, normalize_colour_spec
    from scene_config import (
        _direction_value,
        config_defaults,
        canonical_layout_name,
        config_scene_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        normalize_region_expr,
        resolve_config_scene,
        resolve_runtime_layout,
        validate_scene_catalog,
        widget_names,
    )
    from widget_metadata import validate_widget_metadata, widget_supports


DEFAULT_THEME = "science"
IMAGE_DEPENDENCY_MESSAGE = "image dependencies not met"
THEME_CHOICES = [
    "hacker", "science", "medicine", "pharmacy", "finance",
    "space", "military", "navigation", "spaceteam",
]
COLOUR_HELP = ", ".join(COLOUR_CHOICES)
CANONICAL_DIRECTION_CHOICES = ["forward", "backward", "random", "none"]
DIRECTION_CHOICES = ["forward", "backward", "random", "none"]
DIRECTION_HELP = ", ".join(CANONICAL_DIRECTION_CHOICES)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _screen_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return config_scene_names(config_paths)


def _layout_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return layout_names(config_paths)


def _build_parser(config_paths: tuple[str, ...] | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FakeData Terminal — cinematic terminal data display. "
            "Load the packaged config, then local overlays, then apply CLI overrides. "
            "Use --screen for a preset, or --screen-layout plus --region-widget overrides to build a screen explicitly. "
            "Run --widgets to browse the widget showcase, "
            "or --screens to browse only the configured screen pages."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s --list\n"
            "  %(prog)s --config ./lab.yaml --list\n"
            "  %(prog)s --layouts\n"
            "  %(prog)s --widgets\n"
            "  %(prog)s --screens\n"
            "  %(prog)s --screen test1\n"
            "  %(prog)s --config ~/.config/fakedata-terminal/screens.yaml --screen lab\n"
            "  %(prog)s --screen-layout 2x2 --region-widget P1=life --region-widget P2=blank --region-widget P3=text --region-widget P4=gauge\n"
            "  %(prog)s --screen test1 --region-widget P4=matrix --region-speed P4=80\n"
            "  %(prog)s --screen-layout 3x3 --region-widget L2=image --region-widget R=gauge "
            "--region-image L2=geom_07_diamond_lattice.png --region-image L2=geom_33_torus.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List configured screens, layouts, widgets, and colours in columns, then exit.")
    parser.add_argument(
        "--config", action="append", default=[], metavar="PATH",
        help=("Load an extra config overlay. Repeatable. Relative image paths inside that file are "
              "resolved relative to the file itself."))
    parser.add_argument(
        "--layouts", action="store_true",
        help="Show configured layouts as fixed-size box diagrams, with their defined regions, then exit.")
    parser.add_argument(
        "--widgets", action="store_true",
        help="Browse the widget showcase.")
    parser.add_argument(
        "--screens", action="store_true",
        help="Browse only the configured screen pages.")
    parser.add_argument(
        "--screen", type=str, default=None, choices=_screen_choices(config_paths),
        help="Config-defined screen preset.")
    parser.add_argument(
        "--screen-layout", dest="screen_layout", type=str, default=None,
        help="Explicit layout for the screen being built.")
    parser.add_argument(
        "--screen-theme", dest="screen_theme", type=str, default=None, choices=THEME_CHOICES,
        help=f"Screen theme. Defaults to {DEFAULT_THEME} unless a screen supplies one.")
    parser.add_argument(
        "--region-widget", dest="region_widget", action="append", default=[], metavar="REGION=WIDGET",
        help="Assign a widget to a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--region-speed", dest="region_speed", action="append", default=[], metavar="REGION=N",
        help="Override speed for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--region-text", dest="region_text", action="append", default=[], metavar="REGION=TEXT",
        help="Override text for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--region-theme", dest="region_theme", action="append", default=[], metavar="REGION=THEME",
        help="Override theme for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--region-direction", dest="region_direction", action="append", default=[], metavar="REGION=VALUE",
        help=f"Override direction for a specific region or panel group. Repeatable. Recognized: {DIRECTION_HELP}.")
    parser.add_argument(
        "--region-colour", "--region-color", dest="region_colour", action="append", default=[], metavar="REGION=VALUE",
        help=f"Override colour for a specific region or panel group. Repeatable. Recognized: {COLOUR_HELP}.")
    parser.add_argument(
        "--region-image", dest="region_image", action="append", default=[], metavar="REGION=PATH",
        help="Add an image path for a specific image region. Repeatable.")
    parser.add_argument(
        "--default-colour", "--default-color", type=str, default=None, metavar="VALUE",
        help=f"Default colour for panels without a region-specific colour. Recognized: {COLOUR_HELP}.")
    parser.add_argument(
        "--default-widget", type=str, default=None, metavar="WIDGET",
        help="Default widget for panels that are not assigned explicitly.")
    parser.add_argument(
        "--life-max", type=int, default=200, metavar="N",
        help="Maximum iterations before life mode reseeds. Default 200.")
    parser.add_argument(
        "--screen-glitch", dest="screen_glitch", type=float, default=0.0, const=5.0, nargs="?", metavar="N",
        help=("Glitch interval in seconds. Every ~N seconds a rectangular region "
              "of the display is briefly corrupted then restored. "
              "0 = disabled (default). --screen-glitch alone defaults to 5s."))
    parser.add_argument(
        "--exit", type=float, default=None, metavar="N",
        help="Exit automatically after approximately N seconds.")
    return parser


def _print_list(config_paths: tuple[str, ...] | None = None) -> None:
    for line in _format_catalog_columns(config_paths or (), colourize=True):
        print(line)


def _print_layouts(config_paths: tuple[str, ...] | None = None) -> None:
    print(format_layout_diagrams(config_paths))


def _print_no_args_message() -> None:
    print("fakedata_terminal creates text screens of fake data displays for cinema backgrounds")
    print()
    print("fakedata_terminal --screens to see prebuilt screens")
    print("fakedata_terminal --widgets to see available widgets")
    print("fakedata_terminal --layouts to see available layouts")
    print("fakedata_terminal --list to list inventory of choices")
    print("fakedata_terminal --help for help")

def _showcase_widget_names(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return widget_names(config_paths)


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


def _degrade_image_area(area: dict, message: str) -> None:
    area["mode"] = "blank"
    area["image_paths"] = []
    area["unavailable_message"] = message
    area["static_lines"] = [message]
    area["static_align"] = "center"


def _degrade_runtime_image_dependencies(runtime_scene: dict, message: str) -> None:
    for area in runtime_scene.get("areas", []):
        if area.get("mode") == "image":
            _degrade_image_area(area, message)
            continue
        if area.get("mode") == "cycle" and area.get("cycle_widgets"):
            degraded_widgets = [
                "blank" if widget == "image" else widget
                for widget in area["cycle_widgets"]
            ]
            if degraded_widgets != area["cycle_widgets"]:
                area["cycle_widgets"] = degraded_widgets
                area["unavailable_message"] = message
                area["static_lines"] = [message]
                area["static_align"] = "center"
    runtime_scene["image_paths"] = []


def _widget_attribute_names(widget: str) -> list[str]:
    attrs = []
    for attr in widget_supports(widget):
        attrs.append("colour" if attr == "color" else attr)
    return attrs or ["speed"]


def _format_widget_catalog_entry(widget: str) -> str:
    attrs = ",".join(_widget_attribute_names(widget))
    return f"{widget} [{attrs}]"


def _widget_modifier_lines(widget: str, attrs: list[str]) -> list[str]:
    config_map = {
        "speed": "speed",
        "theme": "theme",
        "text": "text",
        "colour": "colour",
        "direction": "direction",
        "image": "image.paths",
        "cycle": "cycle.widgets",
    }
    cli_map = {
        "speed": "--region-speed",
        "theme": "--screen-theme, --region-theme",
        "text": "--region-text",
        "colour": "--default-colour, --region-colour",
        "direction": "--region-direction",
        "image": "--region-image",
    }
    if not attrs:
        return [
            "Modifiers (in config files): (none)",
            "Modifiers (on command line): (none)",
        ]

    config_items = [config_map.get(attr, attr) for attr in attrs]
    cli_items = [cli_map[attr] for attr in attrs if attr in cli_map]
    if widget == "image":
        config_items.append("image.glob, image.path")

    return [
        f"Modifiers (in config files): {', '.join(config_items)}",
        f"Modifiers (on command line): {', '.join(cli_items) if cli_items else '(none)'}",
    ]


def _widget_showcase_description(widget: str, attrs: list[str], unavailable: str | None) -> list[str]:
    modifier_lines = _widget_modifier_lines(widget, attrs)
    descriptions = {
        "bars": [
            "Animated vertical bars.",
            "",
            *modifier_lines,
        ],
        "blank": [
            "Empty region with optional static text.",
            "",
            *modifier_lines,
        ],
        "blocks": [
            "Random block-field activity.",
            "",
            *modifier_lines,
        ],
        "gauge": [
            "Large digital gauge display.",
            "",
            *modifier_lines,
        ],
        "cycle": [
            "Rotates a region through a configured widget list.",
            "",
            *modifier_lines,
            "cycle.widgets is an ordered widget list.",
        ],
        "image": [
            "ASCII image renderer.",
            "",
            *modifier_lines,
            "image.paths is an ordered image list.",
            "dependencies: Pillow and jp2a.",
        ],
        "life": [
            "Conway-style cellular automaton.",
            "",
            *modifier_lines,
        ],
        "matrix": [
            "Falling glyph rain.",
            "",
            *modifier_lines,
        ],
        "scope": [
            "Sweeping signal trace.",
            "",
            *modifier_lines,
            "theme selects the synthetic signal profile.",
        ],
        "readouts": [
            "Stacked telemetry readout lines.",
            "",
            *modifier_lines,
        ],
        "sparkline": [
            "Scrolling mini-chart.",
            "",
            *modifier_lines,
            "theme selects the synthetic signal profile.",
        ],
        "sweep": [
            "Single scan beam across the region.",
            "",
            *modifier_lines,
            "direction follows the host region shape.",
        ],
        "text": [
            "Dense scrolling text panel.",
            "",
            *modifier_lines,
            "direction controls forward, backward, or paused scrolling.",
        ],
        "text_scant": [
            "Sparse text panel.",
            "",
            *modifier_lines,
            "direction controls forward, backward, or paused scrolling.",
        ],
        "text_spew": [
            "Fast noisy text output.",
            "",
            *modifier_lines,
        ],
        "text_wide": [
            "Wide text panel with larger blocks.",
            "",
            *modifier_lines,
            "direction controls forward, backward, or paused scrolling.",
        ],
        "tunnel": [
            "Moving wireframe tunnel.",
            "",
            *modifier_lines,
        ],
    }
    lines = [widget, ""] + descriptions.get(widget, modifier_lines)
    if unavailable:
        lines.extend(["", f"status: {unavailable}"])
    return lines


def _pad_showcase_description(lines: list[str], header_lines: int) -> list[str]:
    # Showcase headers are drawn directly onto the screen, so reserve that space
    # in the left-hand static panel to avoid painting underneath the header box.
    return ([""] * (header_lines + 2)) + lines


def _format_catalog_columns(config_paths: tuple[str, ...], *, colourize: bool = False) -> list[str]:
    width = shutil.get_terminal_size((100, 24)).columns
    lines = []
    lines.extend(_format_catalog_section("Screens (--screens to view all the preset screens)", config_scene_names(config_paths), width))
    lines.append("")
    lines.extend(_format_catalog_section("Layouts (--layouts to see the layouts)", layout_names(config_paths), width))
    lines.append("")
    lines.extend(_format_widget_matrix_section("Widgets (--widgets to view the available widgets)", widget_names(config_paths), width))
    lines.append("")
    lines.extend(_format_modifiers_section(width, colourize=colourize))
    lines.extend(["", "Config files:"])
    lines.extend(f"  {path}" for path in config_paths)
    defaults = config_defaults(config_paths)
    default_colour = defaults.get("color")
    if colourize and default_colour:
        default_colour = ansi_colour_label(str(default_colour), is_tty=sys.stdout.isatty())
    lines.extend([
        "",
        "Configured defaults:",
        f"  speed: {defaults.get('speed', 50)}",
        f"  colour: {default_colour if default_colour is not None else '(none)'}",
        f"  direction: {defaults.get('direction', 'forward')}",
        f"  widget: {defaults.get('widget') if defaults.get('widget') is not None else '(none)'}",
    ])
    return lines


def _visible_len(text: str) -> int:
    return len(_ANSI_ESCAPE_RE.sub("", text))


def _columnize_items(items: list[str], width: int, *, gap: int = 2, columns: int | None = None) -> list[str]:
    if not items:
        return ["(none)"]
    clean_width = max(20, width)
    if columns is None:
        max_cols = len(items)
        for cols in range(max_cols, 0, -1):
            rows = math.ceil(len(items) / cols)
            col_widths = []
            fits = True
            for col in range(cols):
                column_items = items[col * rows:(col + 1) * rows]
                if not column_items:
                    continue
                col_width = max(_visible_len(item) for item in column_items)
                col_widths.append(col_width)
            total = sum(col_widths) + gap * max(0, len(col_widths) - 1)
            if total <= clean_width:
                columns = cols
                break
        if columns is None:
            columns = 1
    rows = math.ceil(len(items) / columns)
    matrix = [items[col * rows:(col + 1) * rows] for col in range(columns)]
    col_widths = [max((_visible_len(item) for item in column), default=0) for column in matrix]
    lines = []
    for row in range(rows):
        parts = []
        for col in range(columns):
            entry = matrix[col][row] if row < len(matrix[col]) else ""
            if col == columns - 1:
                parts.append(entry)
            else:
                padding = max(0, col_widths[col] - _visible_len(entry))
                parts.append(f"{entry}{' ' * (padding + gap)}")
        lines.append("".join(parts).rstrip())
    return lines


def _format_catalog_section(title: str, items: list[str], width: int) -> list[str]:
    return [title, "-" * len(title), *_columnize_items(items, width)]


def _format_widget_matrix_section(title: str, widgets: list[str], width: int) -> list[str]:
    modifier_columns = ["speed", "theme", "text", "colour", "direction", "image", "cycle"]
    check = "✓"
    widget_width = max(len("widget"), max((len(name) for name in widgets), default=0))
    col_widths = [max(len(name), 1) for name in modifier_columns]
    gap = 2
    total_width = widget_width + sum(col_widths) + gap * len(modifier_columns)
    if total_width > width:
        widget_width = max(len("widget"), widget_width - max(0, total_width - width))
    header = f"{'widget':<{widget_width}}"
    for idx, name in enumerate(modifier_columns):
        header += f"{' ' * gap}{name:<{col_widths[idx]}}"
    lines = [title, "-" * len(title), header.rstrip()]
    for widget in widgets:
        attrs = set(_widget_attribute_names(widget))
        row = f"{widget:<{widget_width}}"
        for idx, name in enumerate(modifier_columns):
            mark = check if name in attrs else ""
            row += f"{' ' * gap}{mark:<{col_widths[idx]}}"
        lines.append(row.rstrip())
    return lines


def _format_modifier_subsection(title: str, body_lines: list[str], *, note: str | None = None) -> list[str]:
    heading = f"  {title.lower()}"
    if note:
        heading = f"{heading}: {note}"
    return [heading, *[f"    {line}" if line else "" for line in body_lines]]


def _format_colour_modifier(width: int, *, colourize: bool) -> list[str]:
    display_columns = []
    for heading, values in COLOUR_CATALOG_COLUMNS:
        display_values = [ansi_colour_label(name, is_tty=sys.stdout.isatty()) for name in values] if colourize else values[:]
        display_columns.append((heading, display_values))
    gap = 2
    col_widths = []
    for heading, values in display_columns:
        col_widths.append(max([len(heading), *(_visible_len(value) for value in values)]))
    total = sum(col_widths) + gap * (len(col_widths) - 1)
    if total > max(20, width):
        # The colour block is always exactly three columns; if the terminal is narrow,
        # keep the structure and let it run wide rather than collapsing the layout.
        pass
    lines = []
    header_parts = []
    for idx, (heading, _) in enumerate(display_columns):
        if idx == len(display_columns) - 1:
            header_parts.append(heading)
        else:
            header_parts.append(f"{heading}{' ' * (col_widths[idx] - len(heading) + gap)}")
    lines.append("".join(header_parts).rstrip())
    row_count = max(len(values) for _, values in display_columns)
    for row in range(row_count):
        parts = []
        for idx, (_, values) in enumerate(display_columns):
            entry = values[row] if row < len(values) else ""
            if idx == len(display_columns) - 1:
                parts.append(entry)
            else:
                padding = max(0, col_widths[idx] - _visible_len(entry))
                parts.append(f"{entry}{' ' * (padding + gap)}")
        lines.append("".join(parts).rstrip())
    lines.append("")
    lines.append("special: multi-all, multi-dim, multi-normal, multi-bright, multi [widget-defined]")
    return lines


def _format_modifiers_section(width: int, *, colourize: bool) -> list[str]:
    lines = ["Modifiers", "---------"]
    sections = [
        _format_modifier_subsection("Colour", _format_colour_modifier(width - 4, colourize=colourize)),
        _format_modifier_subsection("Direction", _columnize_items(CANONICAL_DIRECTION_CHOICES, width - 4)),
        _format_modifier_subsection(
            "Theme",
            _columnize_items(THEME_CHOICES[:], width - 4),
            note="theme vocabulary and behavior profile",
        ),
        _format_modifier_subsection("Speed", ["1..100"], note="widget speed range"),
        _format_modifier_subsection("Text", ["use custom text in the widget"]),
        _format_modifier_subsection("Image", ["one or more image paths for image widgets"]),
        _format_modifier_subsection("Cycle", ["ordered widget list for cycle widgets"]),
    ]
    for idx, section in enumerate(sections):
        if idx:
            lines.append("")
        lines.extend(section)
    return lines

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
        parser.error("--widgets found no widgets to show")

    scenes = []
    for widget in widgets:
        attrs = _widget_attribute_names(widget)
        unavailable = _widget_unavailable_reason(widget, image_paths, image_module, image_checker)
        header_lines = [f"widget: {widget}"]
        left_cfg = _static_blank_region(
            _pad_showcase_description(
                _widget_showcase_description(widget, attrs, unavailable),
                len(header_lines),
            ),
            align="left",
        )
        if widget == "cycle" or unavailable:
            right_cfg = _static_blank_region(
                _widget_showcase_description(widget, attrs, unavailable),
                align="center",
            )
        else:
            right_cfg = {"widget": widget}
            if widget == "image":
                right_cfg["image"] = {"paths": image_paths[:]}
        runtime = resolve_runtime_layout(
            "2x2",
            {
                "L": left_cfg,
                "R": right_cfg,
            },
            parser,
            scene_name=f"<widgets:{widget}>",
            theme=theme,
            speed=speed,
            text=text,
            config_paths=config_paths,
        )
        runtime["showcase_header_lines"] = header_lines
        scenes.append(runtime)
    return scenes


def _build_screen_scenes(parser, config_paths: tuple[str, ...]) -> list[dict]:
    scenes = []
    for scene_name in config_scene_names(config_paths):
        runtime = resolve_config_scene(scene_name, parser, config_paths)
        runtime["showcase_header_lines"] = [f"screen: {scene_name}"]
        scenes.append(runtime)
    return scenes


def _build_widget_showcase(theme: str, speed: int, text: str, image_paths: list[str], parser,
                           image_module, image_checker,
                           config_paths: tuple[str, ...] | None = None) -> dict:
    resolved_paths = config_paths or ()
    scenes = _build_widget_scenes(theme, speed, text, image_paths, parser, image_module, image_checker, resolved_paths)
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


def _build_screen_showcase(parser, config_paths: tuple[str, ...] | None = None) -> dict:
    resolved_paths = config_paths or ()
    scenes = _build_screen_scenes(parser, resolved_paths)
    if not scenes:
        parser.error("--screens found no configured screens to show")
    return {
        "active": True,
        "scenes": scenes,
        "idx": 0,
        "next": float("inf"),
        "pair_duration": 10.0,
        "done": False,
        "initial": scenes[0],
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


def _validate_colour_value(value: str, parser, flag_name: str) -> str:
    normalized = normalize_colour_spec(value)
    valid_colours = {normalize_colour_spec(choice) for choice in COLOUR_CHOICES}
    if normalized not in valid_colours:
        parser.error(f"{flag_name} must be a recognized colour name")
    return normalized


def _normalize_region_key(layout_name: str, region_expr: str, parser, flag_name: str,
                          config_paths: tuple[str, ...] | None = None) -> str:
    canonical_layout = canonical_layout_name(layout_name, config_paths)
    if canonical_layout is None:
        parser.error(f"unknown layout '{layout_name}'")
    normalized = normalize_region_expr(canonical_layout, region_expr, config_paths)
    if normalized is None:
        parser.error(f"{flag_name} references unknown region or panel spec '{region_expr}'")
    return normalized


def _apply_panel_widget_overrides(base_scene: dict | None, region_widgets: list[str], region_speeds: list[str],
                            region_texts: list[str], region_themes: list[str], region_directions: list[str], region_colours: list[str], region_images: list[str],
                            parser, *, layout_name: str, scene_name: str, theme: str,
                            speed: int, text: str, glitch: float, default_widget: str | None, default_colour: str | None,
                            direction: str,
                            config_paths: tuple[str, ...] | None = None) -> dict:
    regions_cfg = {}
    if base_scene:
        base_scene_direction = base_scene.get("direction")
        for area in base_scene["areas"]:
            region_key = "+".join(area["panels"])
            entry = {"widget": area["mode"]}
            if area.get("speed") is not None:
                entry["speed"] = area["speed"]
            if area.get("text"):
                entry["text"] = area["text"]
            if area.get("theme"):
                entry["theme"] = area["theme"]
            if area.get("direction") and area.get("direction") != base_scene_direction:
                entry["direction"] = area["direction"]
            if area.get("colour"):
                entry["colour"] = area["colour"]
            if area.get("image_paths"):
                entry["image"] = {"paths": area["image_paths"][:]}
            if area.get("cycle_widgets"):
                entry["cycle"] = {"widgets": area["cycle_widgets"][:]}
            regions_cfg[region_key] = entry

    for item in region_widgets:
        target, widget = _parse_equals(item, parser, "--region-widget")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-widget", config_paths)
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
                    f"--region-widget {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
            else:
                parser.error(
                    f"--region-widget {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
        for existing_key in to_delete:
            del regions_cfg[existing_key]
        current = regions_cfg.get(normalized_target, {})
        current["widget"] = widget
        regions_cfg[normalized_target] = current

    for item in region_speeds:
        target, speed_text = _parse_equals(item, parser, "--region-speed")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-speed", config_paths)
        try:
            panel_speed = int(speed_text)
        except ValueError:
            parser.error(f"--region-speed expects an integer speed, got '{speed_text}'")
        if not 1 <= panel_speed <= 100:
            parser.error("--region-speed must be between 1 and 100")
        if normalized_target not in regions_cfg:
            parser.error(f"--region-speed target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["speed"] = panel_speed

    for item in region_texts:
        target, panel_text = _parse_equals(item, parser, "--region-text")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-text", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--region-text target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["text"] = panel_text

    for item in region_themes:
        target, theme_name = _parse_equals(item, parser, "--region-theme")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-theme", config_paths)
        if theme_name not in THEME_CHOICES:
            parser.error(f"--region-theme must be one of: {', '.join(THEME_CHOICES)}")
        if normalized_target not in regions_cfg:
            parser.error(f"--region-theme target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["theme"] = theme_name

    for item in region_directions:
        target, direction_name = _parse_equals(item, parser, "--region-direction")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-direction", config_paths)
        normalized_direction = _direction_value(direction_name)
        if normalized_direction is None:
            parser.error(f"--region-direction must be one of: {', '.join(CANONICAL_DIRECTION_CHOICES)}")
        if normalized_target not in regions_cfg:
            parser.error(f"--region-direction target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["direction"] = normalized_direction

    for item in region_colours:
        target, colour_name = _parse_equals(item, parser, "--region-colour")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-colour", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--region-colour target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["colour"] = _validate_colour_value(colour_name, parser, "--region-colour")

    for item in region_images:
        target, image_path = _parse_equals(item, parser, "--region-image")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--region-image", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--region-image target '{target}' has no matching assignment")
        if regions_cfg[normalized_target].get("widget") != "image":
            parser.error(f"--region-image target '{target}' is not assigned to widget 'image'")
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
        glitch=glitch,
        default_widget=default_widget,
        default_color=default_colour,
        direction=direction,
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
    issues.extend(validate_widget_metadata())
    if issues:
        parser.error("configuration validation failed:\n  " + "\n  ".join(issues))

    if args.list:
        _print_list(config_paths)
        raise SystemExit(0)

    if args.layouts:
        _print_layouts(config_paths)
        raise SystemExit(0)

    if not raw_argv:
        _print_no_args_message()
        raise SystemExit(0)

    glitch_explicit = any(a == "--screen-glitch" or a.startswith("--screen-glitch=") for a in raw_argv)

    if args.widgets and args.screens:
        parser.error("choose only one standalone showcase mode: --widgets or --screens")

    if (args.widgets or args.screens) and (
        args.screen is not None or
        args.screen_layout is not None or
        args.region_widget or
        args.region_speed or
        args.region_text or
        args.region_theme or
        args.region_direction or
        args.region_colour or
        args.region_image or
        args.default_colour is not None or
        args.default_widget is not None or
        args.screen_theme is not None or
        glitch_explicit
    ):
        parser.error("standalone showcase modes (--widgets, --screens) do not combine with --screen, --screen-layout, or region overrides")

    colour_explicit = any(a in {"--default-colour", "--default-color"} or a.startswith("--default-colour=") or a.startswith("--default-color=") for a in raw_argv)
    widget_explicit = any(a == "--default-widget" or a.startswith("--default-widget=") for a in raw_argv)
    theme_explicit = any(a == "--screen-theme" or a.startswith("--screen-theme=") for a in raw_argv)

    configured_defaults = config_defaults(config_paths)
    default_images = default_image_paths(config_paths)
    image_paths = default_images[:]

    runtime_speed = configured_defaults.get("speed", 50)
    runtime_text = ""
    runtime_theme = args.screen_theme or configured_defaults.get("theme", DEFAULT_THEME)
    runtime_glitch = max(0.0, configured_defaults.get("glitch", 0.0))
    runtime_default_colour = args.default_colour if colour_explicit and args.default_colour is not None else configured_defaults.get("color")
    runtime_default_widget = args.default_widget if widget_explicit and args.default_widget is not None else configured_defaults.get("widget")
    runtime_direction = configured_defaults.get("direction", "forward")
    widget_showcase = {"active": False, "scenes": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

    if args.widgets:
        widget_showcase = _build_widget_showcase(
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
    elif args.screens:
        widget_showcase = _build_screen_showcase(
            parser,
            config_paths,
        )
        config_scene_runtime = widget_showcase["initial"]
        runtime_layout_name = config_scene_runtime["layout"]
    else:
        base_runtime = resolve_config_scene(args.screen, parser, config_paths) if args.screen else None
        runtime_layout_name = args.screen_layout or (base_runtime["layout"] if base_runtime else None)
        if runtime_layout_name is not None:
            runtime_layout_name = canonical_layout_name(runtime_layout_name, config_paths)
        if not runtime_layout_name:
            parser.error("no layout available")

        runtime_theme = args.screen_theme or (base_runtime["theme"] if base_runtime else configured_defaults.get("theme", DEFAULT_THEME))
        runtime_speed = base_runtime["speed"] if base_runtime else configured_defaults.get("speed", 50)
        runtime_text = base_runtime["text"] if base_runtime else ""
        runtime_glitch = max(0.0, args.screen_glitch if glitch_explicit and args.screen_glitch is not None else (base_runtime["glitch"] if base_runtime else configured_defaults.get("glitch", 0.0)))
        runtime_direction = base_runtime["direction"] if base_runtime else configured_defaults.get("direction", "forward")

        has_cli_overrides = bool(
            args.screen_layout or args.region_widget or args.region_speed or args.region_text or args.region_theme or args.region_direction or args.region_colour or args.region_image or theme_explicit or colour_explicit or widget_explicit or glitch_explicit
        )
        if base_runtime is None or has_cli_overrides:
            config_scene_runtime = _apply_panel_widget_overrides(
                base_runtime if (base_runtime and not args.screen_layout) else None,
                args.region_widget,
                args.region_speed,
                args.region_text,
                args.region_theme,
                args.region_direction,
                args.region_colour,
                args.region_image,
                parser,
                layout_name=runtime_layout_name,
                scene_name=args.screen or f"<cli:{runtime_layout_name}>",
                theme=runtime_theme,
                speed=runtime_speed,
                text=runtime_text,
                glitch=runtime_glitch,
                default_widget=runtime_default_widget,
                default_colour=runtime_default_colour,
                direction=runtime_direction,
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

    if runtime_default_colour is not None:
        runtime_default_colour = _validate_colour_value(runtime_default_colour, parser, "--default-colour")
    if runtime_default_widget is not None and runtime_default_widget not in widget_names(config_paths):
        parser.error(f"--default-widget must be one of: {', '.join(widget_names(config_paths))}")
    if args.life_max < 1:
        parser.error("--life-max must be at least 1")
    if args.exit is not None and args.exit < 0:
        parser.error("--exit must be >= 0")

    image_sources = config_scene_runtime["image_paths"] or image_paths
    image_dependencies_met = image_module is not None and image_checker()
    image_mode_active = any(area["mode"] == "image" for area in config_scene_runtime["areas"])
    if args.widgets or args.screens:
        image_mode_active = any(
            area["mode"] == "image"
            for scene in widget_showcase["scenes"]
            for area in scene["areas"]
        )
    if image_mode_active and not image_paths and not any(area.get("image_paths") for area in config_scene_runtime["areas"]):
        parser.error("image mode requires configured default image sources or --region-image REGION=PATH")
    if image_mode_active and not image_dependencies_met:
        _degrade_runtime_image_dependencies(config_scene_runtime, IMAGE_DEPENDENCY_MESSAGE)
        if args.widgets or args.screens:
            for scene in widget_showcase["scenes"]:
                _degrade_runtime_image_dependencies(scene, IMAGE_DEPENDENCY_MESSAGE)

    return {
        "speed": runtime_speed,
        "main_speed": runtime_speed,
        "sidebar_speed": runtime_speed,
        "life_max": args.life_max,
        "text": runtime_text,
        "main_mode": None,
        "sidebar_mode": None,
        "theme": config_scene_runtime["theme"],
        "direction": config_scene_runtime.get("direction", runtime_direction),
        "scene_name": "<widgets>" if args.widgets else ("<screens>" if args.screens else (args.screen or f"<cli:{runtime_layout_name}>")),
        "themes": THEME_CHOICES[:],
        "config_scene": config_scene_runtime,
        "layout_name": config_scene_runtime["layout"],
        "area_summary": ", ".join(f"{area['name']}={area['mode']}" for area in config_scene_runtime["areas"]),
        "demo_state": {"active": False, "scenes": [], "idx": 0, "scene": None, "next": float("inf"), "done": False},
        "widget_showcase": widget_showcase,
        "glitch_interval": runtime_glitch if not (args.widgets or args.screens) else max(0.0, args.screen_glitch if glitch_explicit and args.screen_glitch is not None else 0.0),
        "exit_after": args.exit,
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
    print(f"  {bold}screen{reset} : {config['scene_name']}")
    print(f"  {bold}theme{reset}  : {config['theme']}")
    if config.get("default_colour") is not None:
        print(f"  {bold}colour{reset} : default {config['default_colour']}")
    print(f"  {bold}direction{reset}: {config.get('direction', 'forward')}")
    if config.get("default_widget") is not None:
        print(f"  {bold}widget{reset} : default {config['default_widget']}")
    if config["image_paths"]:
        label = "image" if len(config["image_paths"]) == 1 else "images"
        print(f"  {bold}{label}{reset} : {', '.join(config['image_paths'])}")
    if config["text"]:
        print(f"  {bold}text{reset}   : '{config['text']}'")
    else:
        print(f"  {bold}text{reset}   : (none)")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {bold}layout{reset} : {config['layout_name']}")
    if config["area_summary"]:
        print(f"  {bold}areas{reset}  : {config['area_summary']}")
    glitch_str = f"every ~{config['glitch_interval']:.1f}s" if config["glitch_interval"] > 0 else "off"
    print(f"  {bold}glitch{reset} : {glitch_str}")
    if config.get("exit_after") is not None:
        print(f"  {bold}exit{reset}   : after ~{config['exit_after']:.1f}s")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {dim}Press Q or Ctrl-C to quit  |  Space to pause  |  + / - to change speed live{reset}")
    print()
