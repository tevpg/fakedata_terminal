#!/usr/bin/env python3
"""Curses runtime for FakeData Terminal."""

import math
import os
import random
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import TypedDict, cast

if sys.platform == "win32":
    try:
        import curses
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "windows-curses"],
            stdout=subprocess.DEVNULL,
        )
        import curses
else:
    import curses

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
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_NAME = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else os.path.basename(__file__)
CONFIG_SCREEN = None
IGNORE_KEYBOARD = False
IMAGE_PATHS: list[str] = []
SPEED_ARG = 50
MAIN_SPEED_ARG = None
SIDEBAR_SPEED_ARG = None
LIFE_MAX_ITERATIONS = 200
INJECT_TEXT = ""
MAIN_MODE = "text"
SIDEBAR_MODE = "none"
THEME_ARG = "science"
_ALL_THEMES: list[str] = []
GLITCH_INTERVAL = 0.0
EXIT_AFTER = None
ESC_EXIT_COUNT = 3
ESC_EXIT_WINDOW_SECONDS = 1.0


class DemoScreen(TypedDict):
    theme: str
    main: str
    sidebar: str
    duration: float


class DemoState(TypedDict):
    active: bool
    screens: list[DemoScreen]
    idx: int
    screen: DemoScreen | None
    next: float
    done: bool


_demo_state: DemoState = {
    "active": False,
    "screens": [],
    "idx": 0,
    "screen": None,
    "next": float("inf"),
    "done": False,
}
_screen_showcase_state = {"active": False, "screens": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

try:
    from .cli_config import build_widget_showcase_screen, prepare_runtime_config
    from .layout_support import (
        config_area_specs as build_config_area_specs,
        cycle_widget_names as list_cycle_widget_names,
        legacy_area_specs as build_legacy_area_specs,
        sidebar_cycle_modes_for_main as list_sidebar_cycle_modes_for_main,
        sync_areas as sync_area_states,
        sync_cycle_start_modes as sync_cycle_start_modes,
    )
    from .widgets_metrics import MetricsWidgets
    from .widgets_image import ImageWidgets
    from .widgets_text import TextWidgets
    from .widgets_visual import VisualWidgets
    from .runtime_support import (
        HELP_TEXT_TOPICS_UNIX,
        HELP_TEXT_TOPICS_WIN,
        build_colour_pairs,
        clamp_density,
        colour_attr_from_spec as _colour_attr_from_spec,
        life_ramp_specs as _life_ramp_specs,
        line_colour as _line_colour,
        load_prime_values,
        make_area_state as build_area_state,
        make_text_state as _make_text_state,
        new_paragraph as _new_paragraph,
        normalize_colour_spec as _normalize_colour_spec,
        rcol_colour as _rcol_colour,
        resize_restartable,
        scaled_speed as _scaled_speed,
        strip_overstrikes as _strip_overstrikes,
    )
    from .timing_support import (
        cycle_change_interval_seconds,
        cycle_start_deadline,
        dt_clamp_seconds,
        resolve_direction_motion as resolve_shared_direction_motion,
        schedule_next,
        shift_deadline,
        widget_interval,
    )
    from .widget_metadata import widget_supports
    from .vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )
except ImportError:
    from cli_config import build_widget_showcase_screen, prepare_runtime_config
    from layout_support import (
        config_area_specs as build_config_area_specs,
        cycle_widget_names as list_cycle_widget_names,
        legacy_area_specs as build_legacy_area_specs,
        sidebar_cycle_modes_for_main as list_sidebar_cycle_modes_for_main,
        sync_areas as sync_area_states,
        sync_cycle_start_modes as sync_cycle_start_modes,
    )
    from widgets_metrics import MetricsWidgets
    from widgets_image import ImageWidgets
    from widgets_text import TextWidgets
    from widgets_visual import VisualWidgets
    from runtime_support import (
        HELP_TEXT_TOPICS_UNIX,
        HELP_TEXT_TOPICS_WIN,
        build_colour_pairs,
        clamp_density,
        colour_attr_from_spec as _colour_attr_from_spec,
        life_ramp_specs as _life_ramp_specs,
        line_colour as _line_colour,
        load_prime_values,
        make_area_state as build_area_state,
        make_text_state as _make_text_state,
        new_paragraph as _new_paragraph,
        normalize_colour_spec as _normalize_colour_spec,
        rcol_colour as _rcol_colour,
        resize_restartable,
        scaled_speed as _scaled_speed,
        strip_overstrikes as _strip_overstrikes,
    )
    from timing_support import (
        cycle_change_interval_seconds,
        cycle_start_deadline,
        dt_clamp_seconds,
        resolve_direction_motion as resolve_shared_direction_motion,
        schedule_next,
        shift_deadline,
        widget_interval,
    )
    from widget_metadata import widget_supports
    from vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )

DEMO_SCENES: list[DemoScreen] = [
    {"theme": "hacker",     "main": "text_wide",     "sidebar": "bars",         "duration": 10.0},
    {"theme": "medicine",   "main": "readouts",      "sidebar": "text_scant",   "duration": 10.0},
    {"theme": "pharmacy",   "main": "text",          "sidebar": "sparkline",    "duration": 10.0},
    {"theme": "spaceteam",  "main": "bars",          "sidebar": "text_wide",    "duration": 10.0},
    {"theme": "science",    "main": "gauge",         "sidebar": "matrix",       "duration": 10.0},
    {"theme": "finance",    "main": "scope",         "sidebar": "blocks",       "duration": 10.0},
    {"theme": "science",    "main": "sweep",         "sidebar": "none",         "duration": 10.0},
    {"theme": "navigation", "main": "readouts",      "sidebar": "none",         "duration": 10.0},
]

SIDEBAR_CYCLE_MODES = [
    "text", "text_wide", "text_spew", "bars", "text_scant",
    "gauge", "matrix", "scope", "blocks", "sweep", "tunnel",
]

# ── Colour pair indices ───────────────────────────────────────────────────────
#
#  1  Green         normal left-col
#  2  White         bright accent
#  3  Cyan          b64 / bracket lines
#  4  Yellow        warnings
#  5  Red           errors / red paragraphs
#  6  Bright green  256-colour; falls back to green
#  7  Cyan          right-column default (dim)
#  8  Blue          image mode accent
#  9  Magenta       image mode accent
# 10  Orange        256-colour; falls back to yellow
# 11  Amber         256-colour; falls back to yellow
# 12  Purple        256-colour; falls back to magenta
# 13  Pink          256-colour; falls back to magenta
# 14  Grey          256-colour; falls back to white

COLOUR_PAIRS = build_colour_pairs(curses)


def _screen_name_for_export(now: datetime | None = None) -> str:
    current = datetime.now() if now is None else now
    return f"screen_{current.strftime('%Y%m%d-%H%M%S')}"


def _shorten_export_image_path(path: str) -> str:
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    try:
        resolved_path = os.path.realpath(os.path.expanduser(path))
    except OSError:
        return path
    try:
        if os.path.commonpath([resolved_path, data_dir]) == data_dir:
            return os.path.basename(resolved_path)
    except ValueError:
        return path
    return path


def _annotate_exported_yaml(yaml_text: str, *, shortened_data_images: bool) -> str:
    if not shortened_data_images:
        return yaml_text

    lines = yaml_text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() != "paths:":
            continue
        indent = line[: len(line) - len(line.lstrip())]
        lines.insert(
            idx,
            f"{indent}# bare image filenames are assumed in the project data directory",
        )
        return "\n".join(lines) + ("\n" if yaml_text.endswith("\n") else "")
    return yaml_text


def _format_shell_command(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) <= 2:
        return " ".join(shlex.quote(part) for part in parts)

    head = " ".join(shlex.quote(part) for part in parts[:3])
    lines = [f"{head} \\" if len(parts) > 3 else head]
    idx = 3
    while idx < len(parts):
        chunk = parts[idx:idx + 2]
        rendered = " ".join(shlex.quote(part) for part in chunk)
        suffix = " \\" if idx + 2 < len(parts) else ""
        lines.append(f"  {rendered}{suffix}")
        idx += 2
    return "\n".join(lines)


def _uses_default_cycle_widgets(area: dict) -> bool:
    sources = area.get("modifier_sources") or {}
    return bool(area.get("cycle_widgets")) and sources.get("cycle") == "widget_default"


def _build_cli_recreation_command(config_screen: dict, effective_regions: list[dict]) -> tuple[str, list[str], list[str]]:
    command_parts = [
        "python3",
        "-m",
        "fakedata_terminal",
        "--screen-layout",
        str(config_screen["layout"]),
        "--screen-theme",
        str(config_screen.get("theme", "science")),
        "--screen-glitch",
        str(max(0.0, float(config_screen.get("glitch", 0.0)))),
    ]
    unsupported: list[str] = []
    default_cycle_regions: list[str] = []

    for entry in effective_regions:
        area = entry["area"]
        region_key = "+".join(area["panels"])
        widget = str(area["mode"])
        supports = set(widget_supports(widget))

        command_parts.extend(["--region-widget", f"{region_key}={widget}"])

        if _uses_default_cycle_widgets(area):
            default_cycle_regions.append(region_key)
        elif area.get("cycle_widgets"):
            unsupported.append(f"{region_key} cycle.widgets")
        if area.get("label") is not None:
            unsupported.append(f"{region_key} label")
        if area.get("unavailable_message") is not None:
            unsupported.append(f"{region_key} unavailable_message")
        if area.get("static_lines") is not None:
            unsupported.append(f"{region_key} static_lines")
        if area.get("static_align") is not None:
            unsupported.append(f"{region_key} static_align")

        if "speed" in supports and entry["speed"] is not None:
            command_parts.extend(["--region-speed", f"{region_key}={entry['speed']}"])
        if "density" in supports and entry["density"] is not None:
            command_parts.extend(["--region-density", f"{region_key}={entry['density']}"])
        if "text" in supports and entry["text"]:
            command_parts.extend(["--region-text", f"{region_key}={entry['text']}"])
        if "theme" in supports and entry["theme"] is not None and entry["theme"] != config_screen.get("theme"):
            command_parts.extend(["--region-theme", f"{region_key}={entry['theme']}"])
        if "direction" in supports and entry["direction"] is not None:
            command_parts.extend(["--region-direction", f"{region_key}={entry['direction']}"])
        if "color" in supports and entry["colour"] is not None:
            command_parts.extend(["--region-colour", f"{region_key}={entry['colour']}"])
        if "image" in supports:
            for path in area.get("image_paths") or []:
                command_parts.extend(["--region-image", f"{region_key}={_shorten_export_image_path(path)}"])

    return _format_shell_command(command_parts), sorted(set(unsupported)), default_cycle_regions


def _build_cli_export_text(cli_command: str, cli_limitations: list[str], default_cycle_regions: list[str]) -> str:
    parts: list[str] = []
    if default_cycle_regions:
        regions = ", ".join(default_cycle_regions)
        parts.append(
            f"# Note: cycle widgets for {regions} are using the default cycle list, so that list is omitted here."
        )
    if cli_limitations:
        parts.append(
            "# Closest command line recreation only; the current CLI cannot encode: "
            + ", ".join(cli_limitations)
            + "."
        )
    parts.append(cli_command)
    return "\n".join(parts) + "\n"


def _append_text_file(path: str, content: str) -> None:
    needs_separator = False
    ends_with_newline = False
    try:
        needs_separator = os.path.exists(path) and os.path.getsize(path) > 0
        if needs_separator:
            with open(path, "rb") as handle:
                handle.seek(-1, os.SEEK_END)
                ends_with_newline = handle.read(1) == b"\n"
    except OSError:
        needs_separator = False
        ends_with_newline = False
    with open(path, "a", encoding="utf-8") as handle:
        if needs_separator:
            separator = "\n" if ends_with_newline else "\n\n"
            if content.startswith("\n"):
                separator = ""
            handle.write(separator)
        if content:
            handle.write(content if content.endswith("\n") else f"{content}\n")


def _file_already_ends_with_block(path: str, content: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            existing = handle.read()
    except OSError:
        return False
    trimmed_existing = existing.rstrip()
    if not trimmed_existing:
        return False
    return trimmed_existing.endswith(content.rstrip())


def _escape_export_text_modifier(value):
    if not isinstance(value, str) or "\n" not in value:
        return value
    return value.replace("\n", r"\n")


def _yaml_field_cost(key: str, value) -> int:
    dumped = yaml.safe_dump({key: value}, sort_keys=False, allow_unicode=False).strip()
    return len(dumped)


_UNFACTORED = object()


def _pick_factored_scene_value(scene_key: str, region_key: str, region_values: list, current_value):
    candidates = []
    seen = set()
    for value in [current_value, *region_values]:
        marker = (type(value), value)
        if marker in seen:
            continue
        seen.add(marker)
        candidates.append(value)

    occurrences = {}
    for value in region_values:
        marker = (type(value), value)
        occurrences[marker] = occurrences.get(marker, 0) + 1

    eligible_candidates = [
        value for value in candidates
        if occurrences.get((type(value), value), 0) > 1
    ]
    if not eligible_candidates:
        return _UNFACTORED

    best_value = eligible_candidates[0]
    best_cost = None
    best_matches = -1
    for candidate in eligible_candidates:
        scene_cost = _yaml_field_cost(scene_key, candidate)
        region_cost = 0
        matches = 0
        for value in region_values:
            if value == candidate:
                matches += 1
                continue
            region_cost += _yaml_field_cost(region_key, value)
        total_cost = scene_cost + region_cost
        if (
            best_cost is None
            or total_cost < best_cost
            or (total_cost == best_cost and matches > best_matches)
            or (total_cost == best_cost and matches == best_matches and candidate == current_value)
        ):
            best_value = candidate
            best_cost = total_cost
            best_matches = matches
    return best_value


def _export_screen_definition(config_screen: dict, area_states: dict[str, dict], current_base_speed: int,
                              current_speed_for_area) -> dict[str, str] | None:
    if not config_screen:
        return None

    screen_name = _screen_name_for_export()
    shortened_data_images = False
    screen_colour = None
    screen_text = config_screen.get("text", "")
    screen_density = config_screen.get("density")
    direction_values = {
        area.get("direction")
        for area in config_screen.get("areas", [])
        if area.get("direction") is not None
    }
    screen_direction = config_screen.get("direction")
    if screen_direction is None and len(direction_values) == 1 and len(config_screen.get("areas", [])) == len([
        area for area in config_screen.get("areas", []) if area.get("direction") is not None
    ]):
        screen_direction = next(iter(direction_values))
    if screen_direction is None:
        screen_direction = "forward"
    colour_values = {
        area.get("colour")
        for area in config_screen.get("areas", [])
        if area.get("colour") is not None
    }
    if colour_values and len(colour_values) == 1 and len(config_screen.get("areas", [])) == len([
        area for area in config_screen.get("areas", []) if area.get("colour") is not None
    ]):
        screen_colour = next(iter(colour_values))
    effective_regions = []
    for area in sorted(config_screen.get("areas", []), key=lambda item: (item["x"], item["y"], item["name"])):
        state = area_states.get(area["name"], {})
        role = state.get("role") or ("main" if area["x"] < 0.5 else "sidebar")
        area_speed = current_speed_for_area(state, role)
        area_theme = area.get("theme") if area.get("theme") is not None else config_screen.get("theme")
        area_text = area.get("text") if area.get("text") is not None else screen_text
        area_colour = area.get("colour") if area.get("colour") is not None else screen_colour
        area_direction = area.get("direction") if area.get("direction") is not None else screen_direction
        area_density = area.get("density") if area.get("density") is not None else screen_density
        effective_regions.append({
            "area": area,
            "speed": area_speed,
            "density": area_density,
            "theme": area_theme,
            "text": area_text,
            "colour": area_colour,
            "direction": area_direction,
            "role": role,
        })

    factored_screen_theme = _pick_factored_scene_value(
        "theme",
        "theme",
        [entry["theme"] for entry in effective_regions],
        config_screen.get("theme"),
    )
    factored_screen_speed = _pick_factored_scene_value(
        "speed",
        "speed",
        [entry["speed"] for entry in effective_regions],
        current_base_speed,
    )
    factored_screen_density = _pick_factored_scene_value(
        "density",
        "density",
        [entry["density"] for entry in effective_regions if "density" in widget_supports(entry["area"]["mode"])],
        screen_density,
    )
    factored_screen_text = _pick_factored_scene_value(
        "text",
        "text",
        [entry["text"] for entry in effective_regions],
        screen_text,
    )
    factored_screen_direction = _pick_factored_scene_value(
        "direction",
        "direction",
        [entry["direction"] for entry in effective_regions],
        screen_direction,
    )
    factored_screen_colour = _pick_factored_scene_value(
        "colour",
        "colour",
        [entry["colour"] for entry in effective_regions],
        screen_colour,
    )
    screen_body = {
        "layout": config_screen["layout"],
        "glitch": max(0.0, float(config_screen.get("glitch", 0.0))),
    }
    if factored_screen_theme is not _UNFACTORED:
        screen_body["theme"] = factored_screen_theme
    if factored_screen_speed is not _UNFACTORED:
        screen_body["speed"] = factored_screen_speed
    if factored_screen_density is not _UNFACTORED and factored_screen_density is not None:
        screen_body["density"] = factored_screen_density
    if factored_screen_text is not _UNFACTORED:
        screen_body["text"] = _escape_export_text_modifier(factored_screen_text)
    if factored_screen_direction is not _UNFACTORED:
        screen_body["direction"] = factored_screen_direction
    if factored_screen_colour is not _UNFACTORED:
        screen_body["colour"] = factored_screen_colour
    screen_body["regions"] = {}

    for entry in effective_regions:
        area = entry["area"]
        region_body = {
            "widget": area["mode"],
        }
        if "density" in widget_supports(area["mode"]):
            density_source = (area.get("modifier_sources") or {}).get("density")
            if density_source in {None, "widget_default"}:
                region_body["density"] = 50
            else:
                region_body["density"] = clamp_density(entry["density"])

        if factored_screen_speed is _UNFACTORED or entry["speed"] != factored_screen_speed:
            region_body["speed"] = entry["speed"]

        if factored_screen_theme is _UNFACTORED or entry["theme"] != factored_screen_theme:
            region_body["theme"] = entry["theme"]

        if factored_screen_text is _UNFACTORED or entry["text"] != factored_screen_text:
            region_body["text"] = _escape_export_text_modifier(entry["text"])

        if factored_screen_colour is _UNFACTORED or entry["colour"] != factored_screen_colour:
            region_body["colour"] = entry["colour"]

        if factored_screen_direction is _UNFACTORED or entry["direction"] != factored_screen_direction:
            region_body["direction"] = entry["direction"]

        image_paths = area.get("image_paths") or []
        if image_paths:
            exported_paths = [_shorten_export_image_path(path) for path in image_paths]
            shortened_data_images = shortened_data_images or exported_paths != image_paths
            region_body["image"] = {"paths": exported_paths}

        cycle_widgets = area.get("cycle_widgets") or []
        if cycle_widgets and not _uses_default_cycle_widgets(area):
            region_body["cycle"] = {"widgets": cycle_widgets[:]}

        if area.get("label") is not None:
            region_body["label"] = area["label"]
        if area.get("unavailable_message") is not None:
            region_body["unavailable_message"] = area["unavailable_message"]
        if area.get("static_lines") is not None:
            region_body["static_lines"] = area["static_lines"]
        if area.get("static_align") is not None:
            region_body["static_align"] = area["static_align"]

        screen_body["regions"][area["name"]] = region_body

    export_doc = {"screens": {screen_name: screen_body}}
    dumped = yaml.safe_dump(export_doc, sort_keys=False, allow_unicode=False)
    yaml_text = _annotate_exported_yaml(dumped, shortened_data_images=shortened_data_images)
    cli_command, cli_limitations, default_cycle_regions = _build_cli_recreation_command(config_screen, effective_regions)
    cli_text = _build_cli_export_text(cli_command, cli_limitations, default_cycle_regions)
    return {
        "screen_name": screen_name,
        "yaml": yaml_text,
        "command": cli_text,
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main(stdscr):
    global MAIN_MODE, SIDEBAR_MODE, THEME_ARG, CONFIG_SCREEN, _screen_showcase_state, EXIT_AFTER, IGNORE_KEYBOARD
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    try:
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        if curses.has_colors():
            for idx, (fg, bg) in COLOUR_PAIRS.items():
                try:
                    curses.init_pair(idx, fg, bg)
                except Exception:
                    try:
                        curses.init_pair(idx, curses.COLOR_GREEN, curses.COLOR_BLACK)
                    except Exception:
                        pass
    except curses.error:
        pass

    rows, cols = stdscr.getmaxyx()
    stdscr.bkgd(' ', curses.color_pair(1))
    try:
        stdscr.scrollok(False)
        stdscr.idlok(False)
    except (curses.error, AttributeError):
        pass

    TEXT_MODES = {"text", "text_wide", "text_scant", "text_spew"}
    STEADY_MODES = {"blocks", "gauge", "scope", "sweep", "image", "life", "tunnel"}
    THEME_MODES = {"text", "text_wide", "text_scant", "bars"}
    MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>[]{}/*+-=."
    SWEEP_SYMBOLS = "∑∏∫∮√∞≈≠≤≥∂∇∈∉∩∪⊂⊃⊆⊇⊕⊗⊥∥∀∃∝∠∅∴∵≜≙⊢⊨"
    IMAGE_COLOUR_CYCLE = [1, 3, 2, 9, 8, 4]
    IMAGE_TRAIL_ATTRS = [
        curses.color_pair(5),
        curses.color_pair(5),
        curses.color_pair(5),
        curses.color_pair(5),
        curses.color_pair(4) | curses.A_DIM,
        curses.color_pair(4) | curses.A_DIM,
        curses.color_pair(4) | curses.A_DIM,
        curses.color_pair(4) | curses.A_DIM,
    ]
    prime_values = load_prime_values(os.path.dirname(__file__))
    text_widgets = TextWidgets(
        curses_module=curses,
        stdscr=stdscr,
        theme_arg_getter=lambda: THEME_ARG,
        build_pools=_build_pools,
        build_area_state=build_area_state,
        get_bar_config=get_bar_config,
        random_line=random_line,
        HEX_WORD=HEX_WORD,
        p_main_gen_pool=_P_MAIN_GEN_POOL,
        p_main_rcol_pool=_P_MAIN_RCOL_POOL,
        p_sidebar_spike_pool=_P_SIDEBAR_SPIKE_POOL,
        line_colour=_line_colour,
        rcol_colour=_rcol_colour,
        new_paragraph=_new_paragraph,
        strip_overstrikes=_strip_overstrikes,
        inject_text_getter=lambda: INJECT_TEXT,
        image_paths_getter=lambda: IMAGE_PATHS,
        list_cycle_widget_names=list_cycle_widget_names,
        help_text_topics_unix=HELP_TEXT_TOPICS_UNIX,
        help_text_topics_win=HELP_TEXT_TOPICS_WIN,
    )

    def layout(cols):
        side_mode = _effective_sidebar_mode()
        if side_mode == "none":
            return cols, 0, None
        sw = max(28, cols // 3)
        mw = cols - sw - 1
        if mw < 28:
            return cols, 0, None
        return mw, sw, mw + 1

    _sidebar_cycle = None
    _clock_now = time.monotonic()
    if SIDEBAR_MODE == "cycle":
        _sidebar_cycle = {
            "modes": list_sidebar_cycle_modes_for_main(MAIN_MODE, SIDEBAR_CYCLE_MODES),
            "idx": 0,
            "next": _clock_now + cycle_change_interval_seconds(),
        }

    def _effective_sidebar_mode():
        if _sidebar_cycle:
            return _sidebar_cycle["modes"][_sidebar_cycle["idx"]]
        return SIDEBAR_MODE

    def _splice_text(base_line: str, msg: str, col_width: int) -> str:
        msg_len = len(msg)
        if msg_len >= len(base_line):
            start = random.randint(0, max(0, col_width - msg_len))
            return (base_line[:start] + msg)[:col_width].ljust(col_width)
        max_insert = max(0, len(base_line) - msg_len)
        insert_at = random.randint(0, max_insert)
        removal_options = []
        if insert_at > msg_len:
            removal_options.append((0, insert_at - msg_len))
        tail_start = insert_at + msg_len
        if tail_start + msg_len <= len(base_line):
            removal_options.append((tail_start, len(base_line) - msg_len))
        if removal_options:
            lo, hi = random.choice(removal_options)
            remove_at = random.randint(lo, hi)
            chopped = base_line[:remove_at] + base_line[remove_at + msg_len:]
        else:
            chopped = base_line
        spliced = chopped[:insert_at] + msg + chopped[insert_at:]
        return spliced[:col_width].ljust(col_width)

    def _leading_blank(txt: str, width: int) -> str:
        if width <= 0:
            return ""
        return (" " + txt)[:width].ljust(width)

    def _rand_line_len(width: int) -> int:
        t = random.betavariate(2, 3)
        frac = 0.30 + t * 0.70
        return max(10, int(frac * width))

    _area_theme = text_widgets.area_theme

    def _sync_cycle_start_modes(area_specs: list[dict], area_states: dict[str, dict], now: float):
        sync_cycle_start_modes(area_specs, area_states, text_widgets.ensure_cycle, now)

    _scroll_text_buffer = text_widgets.scroll_text_buffer
    _safe_row_width = text_widgets.safe_row_width

    visual_widgets = VisualWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        leading_blank=_leading_blank,
        inject_text_getter=lambda: INJECT_TEXT,
        area_theme=_area_theme,
        get_gauge_config=get_gauge_config,
        normalize_colour_spec=_normalize_colour_spec,
        colour_attr_from_spec=_colour_attr_from_spec,
        matrix_chars=MATRIX_CHARS,
        sweep_symbols=SWEEP_SYMBOLS,
    )

    metrics_widgets = MetricsWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        area_theme=_area_theme,
        inject_text_getter=lambda: INJECT_TEXT,
        get_gauge_config=get_gauge_config,
        normalize_colour_spec=_normalize_colour_spec,
        colour_attr_from_spec=_colour_attr_from_spec,
        prime_values=prime_values,
    )
    image_widgets = ImageWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        image_module=Image,
        image_paths_getter=lambda: IMAGE_PATHS,
        inject_text_getter=lambda: INJECT_TEXT,
        life_max_getter=lambda: LIFE_MAX_ITERATIONS,
        normalize_colour_spec=_normalize_colour_spec,
        colour_attr_from_spec=_colour_attr_from_spec,
        life_ramp_specs=_life_ramp_specs,
        image_colour_cycle=IMAGE_COLOUR_CYCLE,
        image_trail_attrs=IMAGE_TRAIL_ATTRS,
    )
    widget_families = [
        text_widgets,
        visual_widgets,
        metrics_widgets,
        image_widgets,
    ]

    def _family_for_mode(mode: str):
        for family in widget_families:
            if family.handles_mode(mode):
                return family
        return None

    def _draw_separator(nrows, left_w):
        if _effective_sidebar_mode() == "none":
            return
        sep_attr = curses.color_pair(1) | curses.A_DIM
        for r in range(nrows):
            try:
                stdscr.addch(r, left_w, '|', sep_attr)
            except curses.error:
                pass

    def _draw_config_separators(area_specs: list[dict]):
        sep_attr = curses.color_pair(1) | curses.A_DIM
        left = 1
        right = 2
        up = 4
        down = 8
        glyphs = {
            left: "─",
            right: "─",
            up: "│",
            down: "│",
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
        masks = {}

        def _add_h_segment(y: int, x0: int, x1: int):
            for x in range(x0, x1 + 1):
                mask = masks.get((y, x), 0)
                if x > x0:
                    mask |= left
                if x < x1:
                    mask |= right
                masks[(y, x)] = mask

        def _add_v_segment(x: int, y0: int, y1: int):
            for y in range(y0, y1 + 1):
                mask = masks.get((y, x), 0)
                if y > y0:
                    mask |= up
                if y < y1:
                    mask |= down
                masks[(y, x)] = mask

        for idx, a in enumerate(area_specs):
            ax0, ay0 = a["x"], a["y"]
            ax1, ay1 = a["x"] + a["width"], a["y"] + a["height"]
            for b in area_specs[idx + 1:]:
                bx0, by0 = b["x"], b["y"]
                bx1, by1 = b["x"] + b["width"], b["y"] + b["height"]

                if ax1 == bx0 or bx1 == ax0:
                    sx = ax1 if ax1 == bx0 else bx1
                    oy0 = max(ay0, by0)
                    oy1 = min(ay1, by1)
                    if 0 < sx < cols and oy1 - oy0 > 0:
                        _add_v_segment(sx, max(0, oy0), min(rows - 1, oy1))

                if ay1 == by0 or by1 == ay0:
                    sy = ay1 if ay1 == by0 else by1
                    ox0 = max(ax0, bx0)
                    ox1 = min(ax1, bx1)
                    if 0 < sy < rows and ox1 - ox0 > 0:
                        _add_h_segment(sy, max(0, ox0), min(cols - 1, ox1))

        for (py, px), mask in masks.items():
            ch = glyphs.get(mask, " ")
            if ch == " ":
                continue
            try:
                stdscr.addch(py, px, ch, sep_attr)
            except curses.error:
                pass

    def _make_area(mode, theme_name: str | None = None):
        area = text_widgets.make_area_state(theme_name)
        area["mode"] = mode
        return area

    current_base_speed = SPEED_ARG
    def _configured_speed_for_role(role: str) -> int:
        return MAIN_SPEED_ARG if role == "main" else SIDEBAR_SPEED_ARG

    def _configured_speed_for_area(area: dict, role: str) -> int:
        return int(area.get("speed_override") or _configured_speed_for_role(role))

    def _current_speed_for_area(area: dict, role: str) -> int:
        current = int(area.get("current_speed") or 0)
        if current:
            return current
        configured = _configured_speed_for_area(area, role)
        area["configured_speed"] = configured
        area["current_speed"] = configured
        return configured

    def _sync_area_speed_state(area: dict, role: str) -> None:
        configured = _configured_speed_for_area(area, role)
        previous = int(area.get("configured_speed") or 0)
        if previous != configured or not area.get("current_speed"):
            area["configured_speed"] = configured
            area["current_speed"] = configured

    def _effective_widget_name(area: dict) -> str:
        return text_widgets.effective_mode(area)

    def _resolved_area_direction_motion(area: dict, now: float) -> int:
        return resolve_shared_direction_motion(area, _effective_widget_name(area), now)

    def _stabilize_direction_history(area: dict, width: int, motion: int, key: str) -> None:
        prev_motion = area.get("direction_motion_prev", motion)
        if prev_motion == motion:
            return
        values = area.get(key) or []
        visible = values[-width:] if prev_motion >= 0 else values[:width]
        area[key] = visible[:]
        area["direction_motion_prev"] = motion

    def _reset_area_timing(area: dict, now: float):
        role = area.get("role", "main")
        _sync_area_speed_state(area, role)
        area_speed = _current_speed_for_area(area, role)
        widget_name = _effective_widget_name(area)
        interval = widget_interval(widget_name, area_speed)
        area["next_update"] = schedule_next(0.0, now, interval)
        area["last_update_at"] = now
        area["burst_fn"] = None
        area["burst_delay"] = 0.0
        area["burst_left"] = 0

    def _ensure_area(area: dict, rows: int, width: int, role: str, now: float):
        if area["mode"] == "cycle":
            text_widgets.ensure_cycle(area, now)
        mode = text_widgets.effective_mode(area)
        area["role"] = role
        _sync_area_speed_state(area, role)
        for family in widget_families:
            if family.handles_mode(mode):
                family.ensure(area, rows, width, role, now)
                break

    def _step_area(area: dict, rows: int, width: int, role: str, now: float, dt: float):
        if area["mode"] == "cycle":
            text_widgets.ensure_cycle(area, now)
        mode = text_widgets.effective_mode(area)
        if now < area["next_update"]:
            return
        frozen_by_direction = (
            mode in {"gauge", "scope", "sparkline", "tunnel"}
            and str(area.get("direction_override") or "forward").lower() == "none"
        )
        area_speed = _current_speed_for_area(area, role)
        if not frozen_by_direction:
            area["tick"] += 1
        _ensure_area(area, rows, width, role, now)
        if text_widgets.handles_mode(mode):
            text_widgets.update(area, rows, width, role, now, dt)
        elif visual_widgets.handles_mode(mode):
            if not (frozen_by_direction and mode in {"gauge", "scope", "tunnel"}):
                visual_widgets.update(area, rows, width, role, now, dt, area_speed)
        elif metrics_widgets.handles_mode(mode):
            # Pylint sometimes loses the concrete MetricsWidgets type here and
            # misreads the keyword-only tail of MetricsWidgets.update(...).
            # pylint: disable=too-many-function-args,unexpected-keyword-arg
            metrics_widgets.update(
                area,
                rows,
                width,
                role,
                now,
                dt,
                resolved_direction_motion=_resolved_area_direction_motion,
                stabilize_direction_history=_stabilize_direction_history,
            )
        elif image_widgets.handles_mode(mode):
            image_widgets.update(area, rows, width, role, now, dt)

        interval = widget_interval(mode, area_speed)
        area["next_update"] = schedule_next(area["next_update"], now, interval)
        area["last_update_at"] = now

    def _paint_area(area: dict, rows: int, y: int, x: int, width: int, role: str):
        mode = text_widgets.effective_mode(area)
        family = _family_for_mode(mode)
        if family is not None:
            family.render(area, rows, y, x, width, role)

    def _draw_area_label(y: int, x: int, width: int, label: str | None):
        if not label or width < 6:
            return
        txt = f"[{label}]"
        draw = txt[:max(0, width - 1)]
        if not draw:
            return
        try:
            stdscr.addnstr(y, x + 1, draw, min(len(draw), max(0, width - 1)), curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

    def _draw_info_box():
        if not _demo_state["active"]:
            return
        side_mode = _effective_sidebar_mode()
        vocab_val = THEME_ARG if (MAIN_MODE in THEME_MODES or side_mode in THEME_MODES) else "-"
        line1 = " demo "
        line2 = f" --main {MAIN_MODE} "
        if SIDEBAR_MODE == "cycle" and side_mode != "none":
            side_label = f"cycle({side_mode})"
        else:
            side_label = side_mode if side_mode != "none" else "(none)"
        line3 = f" --sidebar {side_label} "
        line4 = f" --screen-theme {vocab_val} "
        width = max(len(line1), len(line2), len(line3), len(line4)) + 1
        border_top = "┌" + "─" * (width - 1) + "┐"
        border_bot = "└" + "─" * (width - 1) + "┘"
        try:
            stdscr.addnstr(0, 1, border_top[:width+2], width+2, curses.color_pair(2))
            stdscr.addnstr(1, 1, f"│{line1:<{width-1}s}│", width+2, curses.color_pair(2) | curses.A_BOLD)
            stdscr.addnstr(2, 1, f"│{line2:<{width-1}s}│", width+2, curses.color_pair(2))
            stdscr.addnstr(3, 1, f"│{line3:<{width-1}s}│", width+2, curses.color_pair(2))
            stdscr.addnstr(4, 1, f"│{line4:<{width-1}s}│", width+2, curses.color_pair(2))
            stdscr.addnstr(5, 1, border_bot[:width+2], width+2, curses.color_pair(2))
        except curses.error:
            pass

    def _draw_pause_label():
        if not _paused:
            return
        label = "[paused]"
        try:
            stdscr.addnstr(0, max(1, cols - len(label) - 1), label, len(label), curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass

    def _draw_showcase_header():
        if not _screen_showcase_state["active"] or not CONFIG_SCREEN:
            return
        if _screen_showcase_state.get("mode") == "widgets":
            return
        header_lines = CONFIG_SCREEN.get("showcase_header_lines") or []
        if not header_lines:
            return
        width = max(len(line) for line in header_lines) + 1
        border_top = "┌" + "─" * (width - 1) + "┐"
        border_bot = "└" + "─" * (width - 1) + "┘"
        try:
            stdscr.addnstr(0, 1, border_top[:width + 2], width + 2, curses.color_pair(2))
            for idx, line in enumerate(header_lines, start=1):
                attr = curses.color_pair(2) | (curses.A_BOLD if idx == 1 else 0)
                stdscr.addnstr(idx, 1, f"│{line:<{width-1}s}│", width + 2, attr)
            stdscr.addnstr(len(header_lines) + 1, 1, border_bot[:width + 2], width + 2, curses.color_pair(2))
        except curses.error:
            pass

    def _draw_showcase_footer():
        if not _screen_showcase_state["active"] or rows < 1:
            return
        if _screen_showcase_state.get("mode") == "widgets":
            return
        label = f"[PgUp/Dn] browse  [←/→] speed  [Space] pause  [Q] exit  Speed: {current_base_speed}%"
        try:
            stdscr.addnstr(
                rows - 1,
                max(0, (cols - len(label)) // 2),
                label,
                min(len(label), cols),
                curses.color_pair(2) | curses.A_BOLD,
            )
        except curses.error:
            pass

    _speed_overlay_until = 0.0

    def _show_speed_overlay(now: float) -> None:
        nonlocal _speed_overlay_until
        _speed_overlay_until = now + 1.0

    def _draw_blocking_message(message: str) -> None:
        banner = f"[{message}]"
        draw_w = min(len(banner), max(0, cols - 1))
        if draw_w <= 0 or rows <= 0:
            return
        try:
            stdscr.addnstr(
                rows - 1,
                max(0, (cols - draw_w) // 2),
                banner[:draw_w],
                draw_w,
                curses.color_pair(4) | curses.A_BOLD,
            )
        except curses.error:
            pass

    def _pause_for_confirmation(message: str, seconds: float = 2.0) -> None:
        _draw_blocking_message(message)
        stdscr.refresh()
        time.sleep(seconds)

    def _prompt_for_yaml_save_path(current_path: str | None) -> str | None:
        prompt = "Append YAML to file"
        default_hint = f" [{current_path}]" if current_path else ""
        cwd_line = f"cwd: {os.getcwd()}"
        input_prefix = "> "
        prompt_row = max(0, rows - 2)
        input_row = max(0, rows - 1)
        max_input = max(1, cols - len(input_prefix) - 1)
        buffer = []
        try:
            stdscr.nodelay(False)
            try:
                curses.curs_set(1)
            except curses.error:
                pass
            while True:
                stdscr.move(prompt_row, 0)
                stdscr.clrtoeol()
                prompt_text = f"{prompt}{default_hint} ({cwd_line}, Esc cancels)"
                stdscr.addnstr(prompt_row, 0, prompt_text, max(0, cols - 1), curses.A_BOLD)
                stdscr.move(input_row, 0)
                stdscr.clrtoeol()
                entered = "".join(buffer)[-max_input:]
                stdscr.addnstr(input_row, 0, input_prefix + entered, max(0, cols - 1), curses.A_BOLD)
                stdscr.move(input_row, min(len(input_prefix) + len(entered), max(0, cols - 1)))
                stdscr.refresh()
                key = stdscr.getch()
                if key in (10, 13, curses.KEY_ENTER):
                    text = "".join(buffer).strip()
                    if text:
                        return os.path.expanduser(text)
                    return current_path
                if key == 27:
                    return None
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    if buffer:
                        buffer.pop()
                    continue
                if 32 <= key <= 126 and len(buffer) < max_input:
                    buffer.append(chr(key))
        finally:
            stdscr.nodelay(True)
            try:
                curses.curs_set(0)
            except curses.error:
                pass
            try:
                stdscr.move(prompt_row, 0)
                stdscr.clrtoeol()
                stdscr.move(input_row, 0)
                stdscr.clrtoeol()
            except curses.error:
                pass

    def _save_current_screen_yaml() -> None:
        nonlocal last_yaml_save_path
        if not CONFIG_SCREEN or _demo_state["active"] or _screen_showcase_state["active"]:
            _pause_for_confirmation("save only available for configured screens", 1.5)
            return
        export_payload = _export_screen_definition(
            CONFIG_SCREEN,
            area_states,
            current_base_speed,
            _current_speed_for_area,
        )
        if not export_payload:
            _pause_for_confirmation("nothing to save", 1.5)
            return
        target_path = _prompt_for_yaml_save_path(last_yaml_save_path)
        if not target_path:
            _pause_for_confirmation("save cancelled", 1.0)
            return
        if _file_already_ends_with_block(target_path, export_payload["yaml"]):
            last_yaml_save_path = target_path
            _pause_for_confirmation("No change since last save", 2.0)
            return
        try:
            _append_text_file(target_path, export_payload["yaml"])
        except OSError as exc:
            message = exc.strerror or str(exc)
            _pause_for_confirmation(f"save failed: {message}", 2.0)
            return
        last_yaml_save_path = target_path
        _pause_for_confirmation(f"saved yaml -> {target_path}", 2.0)

    def _adjust_runtime_speeds(delta: int, now: float) -> None:
        speeds = [int(area.get("current_speed") or 0) for area in area_states.values()]
        speeds = [speed for speed in speeds if speed > 0]
        if not speeds:
            return
        ordered = sorted(speeds)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            median = float(ordered[mid])
        else:
            median = (ordered[mid - 1] + ordered[mid]) / 2.0
        if median <= 0.0:
            return
        target_median = max(1.0, min(100.0, median + delta))
        scale = target_median / median
        original = {
            name: int(area.get("current_speed") or 0)
            for name, area in area_states.items()
            if int(area.get("current_speed") or 0) > 0
        }
        use_floor_collapse = delta < 0 and target_median <= 1.0
        for area in area_states.values():
            current = int(area.get("current_speed") or 0)
            if current <= 0:
                continue
            if use_floor_collapse:
                area["current_speed"] = max(1, current - 1)
            else:
                updated = max(1, min(100, round(current * scale)))
                if delta > 0 and updated == current and current < 100:
                    updated = current + 1
                elif delta < 0 and updated == current and current > 1:
                    updated = current - 1
                area["current_speed"] = max(1, min(100, updated))
        if delta < 0 and not use_floor_collapse:
            changed = any(
                int(area_states[name].get("current_speed") or 0) != speed
                for name, speed in original.items()
            )
            if not changed:
                for name, speed in original.items():
                    area_states[name]["current_speed"] = max(1, speed - 1)
        for area in area_states.values():
            _reset_area_timing(area, now)
        nonlocal current_base_speed
        refreshed = sorted(int(area.get("current_speed") or 0) for area in area_states.values() if int(area.get("current_speed") or 0) > 0)
        if refreshed:
            mid = len(refreshed) // 2
            if len(refreshed) % 2:
                current_base_speed = refreshed[mid]
            else:
                current_base_speed = round((refreshed[mid - 1] + refreshed[mid]) / 2.0)

    def _draw_area_speed_overlay(area: dict, area_rows: int, y: int, x: int, width: int, role: str, now: float):
        if _screen_showcase_state["active"] or rows < 1:
            return
        if now >= _speed_overlay_until:
            return
        if area_rows <= 0 or width < 8:
            return
        label = f"[{_current_speed_for_area(area, role)}]"
        draw_w = min(len(label), max(0, cols - 1))
        if draw_w <= 0:
            return
        try:
            stdscr.addnstr(
                y + area_rows - 1,
                max(x, x + width - draw_w - 1),
                label[:draw_w],
                draw_w,
                curses.color_pair(2) | curses.A_BOLD,
            )
        except curses.error:
            pass

    def _apply_showcase_runtime(runtime_screen: dict, next_idx: int) -> None:
        global CONFIG_SCREEN, THEME_ARG
        nonlocal area_specs, area_states, current_base_speed
        now = time.monotonic()
        _screen_showcase_state["idx"] = next_idx
        _screen_showcase_state["done"] = False
        CONFIG_SCREEN = runtime_screen
        THEME_ARG = CONFIG_SCREEN.get("theme", THEME_ARG)
        current_base_speed = int(CONFIG_SCREEN.get("speed") or current_base_speed)
        GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)
        area_specs = _current_area_specs(rows, cols)
        area_states = _sync_areas(area_specs, now)
        _sync_cycle_start_modes(area_specs, area_states, now)
        for spec in area_specs:
            _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"], now)

    def _set_showcase_scene(next_idx: int) -> None:
        screens = _screen_showcase_state.get("screens", [])
        if not screens:
            return
        next_idx %= len(screens)
        if _screen_showcase_state.get("mode") == "widgets":
            try:
                runtime_screen = build_widget_showcase_screen(
                    _screen_showcase_state,
                    next_idx,
                    image_module=Image,
                    image_checker=lambda: shutil.which("jp2a") is not None,
                )
            except ValueError:
                return
            _screen_showcase_state["screens"][next_idx] = runtime_screen
            _apply_showcase_runtime(runtime_screen, next_idx)
            return
        _apply_showcase_runtime(screens[next_idx], next_idx)

    def _current_widget_showcase_state() -> tuple[str, dict] | tuple[None, None]:
        if _screen_showcase_state.get("mode") != "widgets":
            return None, None
        pages = _screen_showcase_state.get("pages") or []
        if not isinstance(pages, list) or not pages:
            return None, None
        page_cfg = pages[_screen_showcase_state["idx"] % len(pages)]
        if not isinstance(page_cfg, dict):
            return None, None
        widget = str(page_cfg.get("widget") or "")
        states = _screen_showcase_state.get("states") or {}
        state = states.get(widget) if isinstance(states, dict) else None
        if not widget or not isinstance(state, dict):
            return None, None
        return widget, state

    def _cycle_widget_showcase_list(key_name: str) -> None:
        widget, state = _current_widget_showcase_state()
        if not widget or not state:
            return
        values = list(state.get(key_name) or [])
        if len(values) < 2:
            return
        current_key = "color" if key_name == "colour_values" else key_name[:-7]
        current_value = state.get(current_key)
        try:
            current_idx = values.index(str(current_value))
        except ValueError:
            current_idx = -1
        state[current_key] = values[(current_idx + 1) % len(values)]
        _set_showcase_scene(_screen_showcase_state["idx"])

    def _cycle_widget_showcase_theme() -> None:
        widget, state = _current_widget_showcase_state()
        if not widget or not state or "theme" not in widget_supports(widget):
            return
        if not _ALL_THEMES:
            return
        current = str(state.get("theme") or _ALL_THEMES[0])
        try:
            current_idx = _ALL_THEMES.index(current)
        except ValueError:
            current_idx = -1
        state["theme"] = _ALL_THEMES[(current_idx + 1) % len(_ALL_THEMES)]
        _set_showcase_scene(_screen_showcase_state["idx"])

    def _cycle_widget_showcase_direction() -> None:
        widget, state = _current_widget_showcase_state()
        if not widget or not state or "direction" not in widget_supports(widget):
            return
        choices = ["forward", "backward", "random", "none"]
        current = str(state.get("direction") or choices[0])
        try:
            current_idx = choices.index(current)
        except ValueError:
            current_idx = -1
        state["direction"] = choices[(current_idx + 1) % len(choices)]
        _set_showcase_scene(_screen_showcase_state["idx"])

    def _adjust_widget_showcase_numeric(modifier: str, delta: int) -> None:
        widget, state = _current_widget_showcase_state()
        if not widget or not state or modifier not in widget_supports(widget):
            return
        current = int(state.get(modifier) or 50)
        state[modifier] = max(1, min(100, current + delta))
        _set_showcase_scene(_screen_showcase_state["idx"])

    def _legacy_area_specs(cols: int):
        return build_legacy_area_specs(
            cols=cols,
            rows=rows,
            main_mode=MAIN_MODE,
            sidebar_mode=SIDEBAR_MODE,
            effective_sidebar_mode=_effective_sidebar_mode,
            layout=layout,
        )

    def _config_area_specs(rows: int, cols: int):
        return build_config_area_specs(CONFIG_SCREEN, rows, cols)

    def _current_area_specs(rows: int, cols: int):
        if CONFIG_SCREEN and not _demo_state["active"]:
            return _config_area_specs(rows, cols)
        return _legacy_area_specs(cols)

    def _sync_areas(area_specs: list[dict], now: float):
        return sync_area_states(area_specs, area_states, _make_area, lambda area: _reset_area_timing(area, now))

    area_states = {}
    area_specs = _current_area_specs(rows, cols)
    start_now = time.monotonic()
    area_states = _sync_areas(area_specs, start_now)
    _sync_cycle_start_modes(area_specs, area_states, start_now)
    for spec in area_specs:
        _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"], start_now)

    _GLITCH_CHARS = "!@#$%^&*?><|/\\~`[]{}abcdefXYZ0123456789XOXOX##!!??@@$$%%^^&&**"
    _glitch_next = start_now + GLITCH_INTERVAL if GLITCH_INTERVAL > 0 else float("inf")
    _glitch_active = False
    _glitch_restore_at = 0.0
    _glitch_r0 = _glitch_c0 = _glitch_rh = _glitch_cw = 0
    _paused = False
    _paused_at = 0.0
    esc_sequence_times: list[float] = []
    last_yaml_save_path = None
    _exit_at = start_now + EXIT_AFTER if EXIT_AFTER is not None else float("inf")
    _last_loop_now = start_now

    if _screen_showcase_state["active"] and _screen_showcase_state["next"] == float("inf"):
        _screen_showcase_state["next"] = start_now + _screen_showcase_state["pair_duration"]

    def _shift_pause_timers(delta: float, resumed_at: float) -> None:
        nonlocal _glitch_next, _glitch_restore_at, _last_loop_now
        if delta <= 0.0:
            return
        if _sidebar_cycle:
            _sidebar_cycle["next"] = shift_deadline(_sidebar_cycle["next"], delta)
        for area in area_states.values():
            area["next_update"] = shift_deadline(area.get("next_update", 0.0), delta)
            area["cycle_next_change"] = shift_deadline(area.get("cycle_next_change", 0.0), delta)
            area["metrics_next_reads_at"] = shift_deadline(area.get("metrics_next_reads_at", 0.0), delta)
            area["textwall_next_reverse_at"] = shift_deadline(area.get("textwall_next_reverse_at", 0.0), delta)
            area["textwall_pause_until"] = shift_deadline(area.get("textwall_pause_until", 0.0), delta)
            area["direction_next_change"] = shift_deadline(area.get("direction_next_change", 0.0), delta)
            area["last_update_at"] = resumed_at
        if _screen_showcase_state["active"] and _screen_showcase_state["next"] != float("inf"):
            _screen_showcase_state["next"] += delta
        if _demo_state["active"] and _demo_state["next"] != float("inf"):
            _demo_state["next"] += delta
        if _glitch_active and _glitch_restore_at:
            _glitch_restore_at = shift_deadline(_glitch_restore_at, delta)
        elif _glitch_next != float("inf"):
            _glitch_next = shift_deadline(_glitch_next, delta)
        _last_loop_now = resumed_at

    def _fire_glitch():
        nonlocal _glitch_active, _glitch_restore_at, _glitch_r0, _glitch_c0, _glitch_rh, _glitch_cw
        cur_rows, cur_cols = stdscr.getmaxyx()
        rh = random.randint(3, min(12, max(3, cur_rows)))
        cw = random.randint(8, min(40, max(8, cur_cols)))
        _glitch_rh, _glitch_cw = rh, cw
        _glitch_r0 = random.randint(0, max(0, cur_rows - rh))
        _glitch_c0 = random.randint(0, max(0, cur_cols - cw))
        flavour = random.choice(["noise", "shift", "invert", "blank"])
        for r in range(_glitch_r0, _glitch_r0 + rh):
            for c in range(_glitch_c0, _glitch_c0 + cw):
                try:
                    if flavour == "blank":
                        ch, attr = ord(" "), curses.color_pair(1)
                    elif flavour == "invert":
                        cell = stdscr.inch(r, c)
                        ch, attr = (cell & 0xFF or ord(" ")), curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD
                    elif flavour == "shift":
                        sr = max(0, min(cur_rows - 1, r + random.randint(-3, 3)))
                        sc = max(0, min(cur_cols - 1, c + random.randint(-5, 5)))
                        cell = stdscr.inch(sr, sc)
                        ch, attr = (cell & 0xFF or ord(" ")), curses.color_pair(random.choice([5, 4, 3])) | curses.A_BOLD
                    else:
                        ch, attr = ord(random.choice(_GLITCH_CHARS)), curses.color_pair(random.choice([5, 4, 2, 3, 6])) | curses.A_BOLD
                    stdscr.addch(r, c, ch, attr)
                except curses.error:
                    pass
        _glitch_active = True
        _glitch_restore_at = time.monotonic() + random.uniform(0.12, 0.44)

    def _restore_glitch(current_specs):
        nonlocal _glitch_active
        for spec in current_specs:
            area = area_states.get(spec["name"])
            if area:
                _paint_area(area, spec["height"], spec["y"], spec["x"], spec["width"], spec["role"])
        _glitch_active = False

    while True:
        rows, cols = stdscr.getmaxyx()
        now = time.monotonic()
        dt = max(0.0, min(now - _last_loop_now, dt_clamp_seconds()))
        _last_loop_now = now
        if now >= _exit_at:
            break
        if _sidebar_cycle and not _paused:
            new_modes = list_sidebar_cycle_modes_for_main(MAIN_MODE, SIDEBAR_CYCLE_MODES)
            if new_modes != _sidebar_cycle["modes"]:
                _sidebar_cycle["modes"] = new_modes
                _sidebar_cycle["idx"] = 0
                _sidebar_cycle["next"] = now + cycle_change_interval_seconds()
        if _sidebar_cycle and not _paused and now >= _sidebar_cycle["next"]:
            _sidebar_cycle["idx"] = (_sidebar_cycle["idx"] + 1) % len(_sidebar_cycle["modes"])
            _sidebar_cycle["next"] = now + cycle_change_interval_seconds()
        area_specs = _current_area_specs(rows, cols)
        area_states = _sync_areas(area_specs, now)
        if not _paused:
            _sync_cycle_start_modes(area_specs, area_states, now)
            for spec in area_specs:
                area = area_states[spec["name"]]
                if area["mode"] != "cycle" or now < area["cycle_next_change"]:
                    continue
                forbidden = {
                    text_widgets.effective_mode(other)
                    for other_name, other in area_states.items()
                    if other_name != spec["name"] and other["mode"] == "cycle"
                }
                text_widgets.advance_cycle(area, now, forbidden)
        for spec in area_specs:
            area = area_states[spec["name"]]
            if not _paused:
                if text_widgets.effective_mode(area) == "readouts":
                    area["metrics_count"] += 1
                _step_area(area, spec["height"], spec["width"], spec["role"], now, dt)
            if spec.get("separator_after"):
                _draw_separator(rows, spec["width"])
            _paint_area(area, spec["height"], spec["y"], spec["x"], spec["width"], spec["role"])
            _draw_area_speed_overlay(area, spec["height"], spec["y"], spec["x"], spec["width"], spec["role"], now)
            _draw_area_label(spec["y"], spec["x"], spec["width"], area.get("label"))
        if CONFIG_SCREEN and not _demo_state["active"]:
            _draw_config_separators(area_specs)

        primary_main = next((spec for spec in area_specs if spec["role"] == "main"), area_specs[0])
        if primary_main["mode"] in TEXT_MODES and random.random() < 0.18:
            r = random.randint(primary_main["y"], max(primary_main["y"], primary_main["y"] + primary_main["height"] - 2))
            c = random.randint(primary_main["x"], primary_main["x"] + primary_main["width"] - 1)
            try:
                ch = stdscr.inch(r, c) & 0xFF
                if ch not in (0, 32):
                    stdscr.addch(r, c, ch, curses.color_pair(6) | curses.A_BOLD)
            except curses.error:
                pass

        _draw_info_box()
        _draw_pause_label()
        _draw_showcase_header()
        _draw_showcase_footer()

        if GLITCH_INTERVAL > 0 and not _paused:
            glitch_now = time.monotonic()
            if _glitch_active:
                if glitch_now >= _glitch_restore_at:
                    _restore_glitch(area_specs)
            elif glitch_now >= _glitch_next:
                _fire_glitch()
                _glitch_next = glitch_now + GLITCH_INTERVAL * random.uniform(0.70, 1.30)

        stdscr.refresh()

        key = stdscr.getch()
        if IGNORE_KEYBOARD:
            if key == 27:
                esc_sequence_times.append(time.monotonic())
                cutoff = esc_sequence_times[-1] - ESC_EXIT_WINDOW_SECONDS
                esc_sequence_times = [timestamp for timestamp in esc_sequence_times if timestamp >= cutoff]
                if len(esc_sequence_times) >= ESC_EXIT_COUNT:
                    if CONFIG_SCREEN and not _demo_state["active"] and not _screen_showcase_state["active"]:
                        return _export_screen_definition(
                            CONFIG_SCREEN,
                            area_states,
                            current_base_speed,
                            _current_speed_for_area,
                        )
                    break
            continue
        if key == ord('s'):
            _save_current_screen_yaml()
            continue
        if key in (ord('q'), ord('Q'), 27):
            if CONFIG_SCREEN and not _demo_state["active"] and not _screen_showcase_state["active"]:
                return _export_screen_definition(
                    CONFIG_SCREEN,
                    area_states,
                    current_base_speed,
                    _current_speed_for_area,
                )
            break
        if _screen_showcase_state["active"] and key in (curses.KEY_LEFT, ord('h'), ord('H')):
            if _screen_showcase_state.get("mode") == "widgets":
                _adjust_widget_showcase_numeric("speed", -1)
            else:
                speed_now = time.monotonic()
                _adjust_runtime_speeds(-1, speed_now)
                _show_speed_overlay(speed_now)
            continue
        if _screen_showcase_state["active"] and key in (curses.KEY_RIGHT, ord('l'), ord('L')):
            if _screen_showcase_state.get("mode") == "widgets":
                _adjust_widget_showcase_numeric("speed", 1)
            else:
                speed_now = time.monotonic()
                _adjust_runtime_speeds(1, speed_now)
                _show_speed_overlay(speed_now)
            continue
        if _screen_showcase_state["active"] and key == curses.KEY_PPAGE:
            _set_showcase_scene(_screen_showcase_state["idx"] - 1)
            continue
        if _screen_showcase_state["active"] and key == curses.KEY_NPAGE:
            _set_showcase_scene(_screen_showcase_state["idx"] + 1)
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key == curses.KEY_UP:
            _adjust_widget_showcase_numeric("density", 1)
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key == curses.KEY_DOWN:
            _adjust_widget_showcase_numeric("density", -1)
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key in (ord('t'), ord('T')):
            _cycle_widget_showcase_list("text_values")
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key in (ord('c'), ord('C')):
            _cycle_widget_showcase_list("colour_values")
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key in (ord('d'), ord('D')):
            _cycle_widget_showcase_direction()
            continue
        if _screen_showcase_state["active"] and _screen_showcase_state.get("mode") == "widgets" and key in (ord('v'), ord('V')):
            _cycle_widget_showcase_theme()
            continue
        if key == ord(' '):
            if _paused:
                resumed_at = time.monotonic()
                _shift_pause_timers(resumed_at - _paused_at, resumed_at)
                _paused = False
            else:
                _paused = True
                _paused_at = time.monotonic()
        elif key in (ord('+'), ord('=')) and _screen_showcase_state.get("mode") != "widgets":
            speed_now = time.monotonic()
            _adjust_runtime_speeds(1, speed_now)
            _show_speed_overlay(speed_now)
        elif key == ord('-') and _screen_showcase_state.get("mode") != "widgets":
            speed_now = time.monotonic()
            _adjust_runtime_speeds(-1, speed_now)
            _show_speed_overlay(speed_now)

        if (not _paused and _demo_state["active"]
                and not _demo_state["done"]
                and time.monotonic() >= _demo_state["next"]):
            next_idx = _demo_state["idx"] + 1
            if next_idx >= len(_demo_state["screens"]):
                _demo_state["done"] = True
                break
            _demo_state["idx"] = next_idx
            _demo_state["screen"] = _demo_state["screens"][next_idx]
            current_demo_screen = _demo_state["screen"]
            if current_demo_screen is None:
                _demo_state["done"] = True
                break
            THEME_ARG = current_demo_screen["theme"]  # pylint: disable=unsubscriptable-object
            MAIN_MODE = current_demo_screen["main"]  # pylint: disable=unsubscriptable-object
            SIDEBAR_MODE = current_demo_screen["sidebar"]  # pylint: disable=unsubscriptable-object
            GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)
            area_specs = _current_area_specs(rows, cols)
            scene_now = time.monotonic()
            area_states = _sync_areas(area_specs, scene_now)
            _sync_cycle_start_modes(area_specs, area_states, scene_now)
            for spec in area_specs:
                _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"], scene_now)
            _demo_state["next"] = scene_now + current_demo_screen["duration"]  # pylint: disable=unsubscriptable-object
        time.sleep(0.01)


# ── Entry point ───────────────────────────────────────────────────────────────



def run(argv=None) -> int:
    global IMAGE_PATHS, SPEED_ARG, MAIN_SPEED_ARG, SIDEBAR_SPEED_ARG
    global LIFE_MAX_ITERATIONS, INJECT_TEXT, MAIN_MODE, _ALL_THEMES
    global THEME_ARG, SIDEBAR_MODE, _demo_state, GLITCH_INTERVAL, CONFIG_SCREEN, _screen_showcase_state, EXIT_AFTER
    global IGNORE_KEYBOARD

    config = prepare_runtime_config(
        argv=argv,
        image_module=Image,
        image_checker=lambda: shutil.which("jp2a") is not None,
        demo_scenes=DEMO_SCENES,
    )

    IMAGE_PATHS = config["image_paths"]
    SPEED_ARG = config["speed"]
    MAIN_SPEED_ARG = config["main_speed"]
    SIDEBAR_SPEED_ARG = config["sidebar_speed"]
    LIFE_MAX_ITERATIONS = config["life_max"]
    INJECT_TEXT = config["text"]
    MAIN_MODE = config["main_mode"]
    _ALL_THEMES = config["themes"]
    THEME_ARG = config["theme"]
    CONFIG_SCREEN = config["config_screen"]
    SIDEBAR_MODE = config["sidebar_mode"]
    _demo_state = cast(DemoState, config["demo_state"])
    _screen_showcase_state = config["screen_showcase"]
    GLITCH_INTERVAL = config["glitch_interval"]
    EXIT_AFTER = config["exit_after"]
    IGNORE_KEYBOARD = config["ignore_keyboard"]
    save_screen_yaml = config["save_screen_yaml"]
    save_screen_command = config["save_screen_command"]

    GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)

    if IGNORE_KEYBOARD:
        print("\n\nPerformance mode: press/hold Esc to exit\n\n", end="", flush=True)
        time.sleep(2.0)

    while True:
        exported_screen = None
        try:
            exported_screen = curses.wrapper(main)
            break
        except KeyboardInterrupt:
            break
        except Exception as exc:
            if not resize_restartable(
                exc,
                curses_module=curses,
                app_path=__file__,
                helper_names={
                    "main",
                    "_paint_area",
                    "_ensure_area",
                    "_step_area",
                    "_draw_config_separators",
                    "_sync_areas",
                },
            ):
                raise
            time.sleep(0.05)
    print(f"\n[{SCRIPT_NAME}] terminated.")
    if exported_screen:
        print(exported_screen["command"], end="" if exported_screen["command"].endswith("\n") else "\n")
        if save_screen_yaml == "-":
            print(exported_screen["yaml"], end="" if exported_screen["yaml"].endswith("\n") else "\n")
        elif save_screen_yaml:
            _append_text_file(save_screen_yaml, exported_screen["yaml"])
        if save_screen_command and save_screen_command != "-":
            _append_text_file(save_screen_command, exported_screen["command"])
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
