#!/usr/bin/env python3
"""Curses runtime for FakeData Terminal."""

import math
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime

if sys.platform == "win32":
    try:
        import curses
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "windows-curses"],
            stdout=subprocess.DEVNULL,
        )
        import curses
else:
    import curses

import yaml

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_NAME = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else os.path.basename(__file__)
CONFIG_SCENE = None
_showcase_state = {"active": False, "scenes": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

try:
    from .cli_config import prepare_runtime_config
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
        centre_delay as _centre_delay,
        colour_attr_from_spec as _colour_attr_from_spec,
        life_ramp_specs as _life_ramp_specs,
        line_colour as _line_colour,
        load_prime_values,
        make_area_state as build_area_state,
        make_burst_fn,
        make_text_state as _make_text_state,
        new_paragraph as _new_paragraph,
        normalize_colour_spec as _normalize_colour_spec,
        rcol_colour as _rcol_colour,
        resize_restartable,
        scaled_speed as _scaled_speed,
        strip_overstrikes as _strip_overstrikes,
    )
    from .vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )
except ImportError:
    from cli_config import prepare_runtime_config
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
        centre_delay as _centre_delay,
        colour_attr_from_spec as _colour_attr_from_spec,
        life_ramp_specs as _life_ramp_specs,
        line_colour as _line_colour,
        load_prime_values,
        make_area_state as build_area_state,
        make_burst_fn,
        make_text_state as _make_text_state,
        new_paragraph as _new_paragraph,
        normalize_colour_spec as _normalize_colour_spec,
        rcol_colour as _rcol_colour,
        resize_restartable,
        scaled_speed as _scaled_speed,
        strip_overstrikes as _strip_overstrikes,
    )
    from vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )

DEMO_SCENES = [
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


def _scene_name_for_export(now: datetime | None = None) -> str:
    current = datetime.now() if now is None else now
    return f"scene_{current.strftime('%Y%m%d-%H%M%S')}"


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


def _export_scene_definition(config_scene: dict, area_states: dict[str, dict], current_base_speed: int,
                             current_speed_for_role) -> str | None:
    if not config_scene:
        return None

    scene_name = _scene_name_for_export()
    shortened_data_images = False
    scene_colour = None
    scene_text = config_scene.get("text", "")
    direction_values = {
        area.get("direction")
        for area in config_scene.get("areas", [])
        if area.get("direction") is not None
    }
    scene_direction = config_scene.get("direction")
    if scene_direction is None and len(direction_values) == 1 and len(config_scene.get("areas", [])) == len([
        area for area in config_scene.get("areas", []) if area.get("direction") is not None
    ]):
        scene_direction = next(iter(direction_values))
    if scene_direction is None:
        scene_direction = "right"
    colour_values = {
        area.get("colour")
        for area in config_scene.get("areas", [])
        if area.get("colour") is not None
    }
    if colour_values and len(colour_values) == 1 and len(config_scene.get("areas", [])) == len([
        area for area in config_scene.get("areas", []) if area.get("colour") is not None
    ]):
        scene_colour = next(iter(colour_values))
    effective_regions = []
    for area in sorted(config_scene.get("areas", []), key=lambda item: (item["x"], item["y"], item["name"])):
        state = area_states.get(area["name"], {})
        role = state.get("role") or ("main" if area["x"] < 0.5 else "sidebar")
        area_speed = state.get("speed_override") or current_speed_for_role(role)
        area_theme = area.get("theme") if area.get("theme") is not None else config_scene.get("theme")
        area_text = area.get("text") if area.get("text") is not None else scene_text
        area_colour = area.get("colour") if area.get("colour") is not None else scene_colour
        area_direction = area.get("direction") if area.get("direction") is not None else scene_direction
        effective_regions.append({
            "area": area,
            "speed": area_speed,
            "theme": area_theme,
            "text": area_text,
            "colour": area_colour,
            "direction": area_direction,
            "role": role,
        })

    factored_scene_theme = _pick_factored_scene_value(
        "theme",
        "source_theme",
        [entry["theme"] for entry in effective_regions],
        config_scene.get("theme"),
    )
    factored_scene_speed = _pick_factored_scene_value(
        "speed",
        "speed",
        [entry["speed"] for entry in effective_regions],
        current_base_speed,
    )
    factored_scene_text = _pick_factored_scene_value(
        "text",
        "text",
        [entry["text"] for entry in effective_regions],
        scene_text,
    )
    factored_scene_direction = _pick_factored_scene_value(
        "direction",
        "direction",
        [entry["direction"] for entry in effective_regions],
        scene_direction,
    )
    factored_scene_colour = _pick_factored_scene_value(
        "colour",
        "colour",
        [entry["colour"] for entry in effective_regions],
        scene_colour,
    )
    scene_body = {
        "layout": config_scene["layout"],
        "glitch": max(0.0, float(config_scene.get("glitch", 0.0))),
    }
    if factored_scene_theme is not _UNFACTORED:
        scene_body["theme"] = factored_scene_theme
    if factored_scene_speed is not _UNFACTORED:
        scene_body["speed"] = factored_scene_speed
    if factored_scene_text is not _UNFACTORED:
        scene_body["text"] = _escape_export_text_modifier(factored_scene_text)
    if factored_scene_direction is not _UNFACTORED:
        scene_body["direction"] = factored_scene_direction
    if factored_scene_colour is not _UNFACTORED:
        scene_body["colour"] = factored_scene_colour
    scene_body["regions"] = {}

    for entry in effective_regions:
        area = entry["area"]
        region_body = {
            "widget": area["mode"],
        }
        if factored_scene_speed is _UNFACTORED or entry["speed"] != factored_scene_speed:
            region_body["speed"] = entry["speed"]

        if factored_scene_theme is _UNFACTORED or entry["theme"] != factored_scene_theme:
            region_body["source_theme"] = entry["theme"]

        if factored_scene_text is _UNFACTORED or entry["text"] != factored_scene_text:
            region_body["text"] = _escape_export_text_modifier(entry["text"])

        if factored_scene_colour is _UNFACTORED or entry["colour"] != factored_scene_colour:
            region_body["colour"] = entry["colour"]

        if factored_scene_direction is _UNFACTORED or entry["direction"] != factored_scene_direction:
            region_body["direction"] = entry["direction"]

        image_paths = area.get("image_paths") or []
        if image_paths:
            exported_paths = [_shorten_export_image_path(path) for path in image_paths]
            shortened_data_images = shortened_data_images or exported_paths != image_paths
            region_body["image"] = {"paths": exported_paths}

        cycle_widgets = area.get("cycle_widgets") or []
        if cycle_widgets:
            region_body["cycle"] = {"widgets": cycle_widgets[:]}

        if area.get("label") is not None:
            region_body["label"] = area["label"]
        if area.get("unavailable_message") is not None:
            region_body["unavailable_message"] = area["unavailable_message"]
        if area.get("static_lines") is not None:
            region_body["static_lines"] = area["static_lines"]
        if area.get("static_align") is not None:
            region_body["static_align"] = area["static_align"]

        scene_body["regions"][area["name"]] = region_body

    export_doc = {"scenes": {scene_name: scene_body}}
    dumped = yaml.safe_dump(export_doc, sort_keys=False, allow_unicode=False)
    return _annotate_exported_yaml(dumped, shortened_data_images=shortened_data_images)

# ── Main ──────────────────────────────────────────────────────────────────────

def main(stdscr):
    global MAIN_MODE, SIDEBAR_MODE, THEME_ARG, CONFIG_SCENE, _showcase_state, EXIT_AFTER
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
    if SIDEBAR_MODE == "cycle":
        _sidebar_cycle = {
            "modes": list_sidebar_cycle_modes_for_main(MAIN_MODE, SIDEBAR_CYCLE_MODES),
            "idx": 0,
            "next": time.time() + 15.0,
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
        new_area_text_entry=text_widgets.new_area_text_entry,
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
    main_speed_ratio = MAIN_SPEED_ARG / SPEED_ARG
    sidebar_speed_ratio = SIDEBAR_SPEED_ARG / SPEED_ARG

    def _current_speed_for_role(role: str) -> int:
        ratio = main_speed_ratio if role == "main" else sidebar_speed_ratio
        return _scaled_speed(current_base_speed, ratio)

    def _steady_mode_delay(mode: str, speed: int) -> float:
        delay = _centre_delay(speed)
        if mode in {"gauge", "blocks", "sweep", "tunnel"}:
            return delay / 1.5
        return delay

    def _resolved_area_direction_motion(area: dict, now: float) -> int:
        direction = str(area.get("direction_override") or "right").lower()
        if direction == "none":
            area["direction_motion"] = 0
            return 0
        if direction == "right":
            area["direction_motion"] = 1
            return 1
        if direction == "left":
            area["direction_motion"] = -1
            return -1
        if now >= area["gauge_next_spin_change"]:
            area["gauge_spin"] = visual_widgets.choose_gauge_spin()
            area["gauge_next_spin_change"] = now + random.uniform(0.5, 3.0)
        motion = area.get("gauge_spin", 1)
        if motion > 0:
            area["direction_motion"] = 1
            return 1
        if motion < 0:
            area["direction_motion"] = -1
            return -1
        return 0

    def _stabilize_direction_history(area: dict, width: int, motion: int, key: str) -> None:
        prev_motion = area.get("direction_motion_prev", motion)
        if prev_motion == motion:
            return
        values = area.get(key) or []
        visible = values[-width:] if prev_motion >= 0 else values[:width]
        area[key] = visible[:]
        area["direction_motion_prev"] = motion

    def _family_for_mode(mode: str):
        for family in widget_families:
            if family.handles_mode(mode):
                return family
        return None

    def _reset_area_timing(area: dict):
        role = area.get("role", "main")
        area_speed = area.get("speed_override") or _current_speed_for_role(role)
        area["next_update"] = time.time()
        if text_widgets.effective_mode(area) in STEADY_MODES:
            area["burst_fn"] = None
            area["burst_delay"] = 0.0
            area["burst_left"] = 0
        else:
            area["burst_fn"] = make_burst_fn(area_speed)
            area["burst_delay"], area["burst_left"] = area["burst_fn"]()

    def _ensure_area(area: dict, rows: int, width: int, role: str):
        if area["mode"] == "cycle":
            text_widgets.ensure_cycle(area)
        mode = text_widgets.effective_mode(area)
        area["role"] = role
        family = _family_for_mode(mode)
        if family is not None:
            family.ensure(area, rows, width, role, time.time())

    def _step_area(area: dict, rows: int, width: int, role: str, now: float):
        if area["mode"] == "cycle":
            text_widgets.ensure_cycle(area)
        mode = text_widgets.effective_mode(area)
        if now < area["next_update"]:
            return
        frozen_by_direction = (
            mode in {"gauge", "scope", "sparkline", "tunnel"}
            and str(area.get("direction_override") or "right").lower() == "none"
        )
        area_speed = area.get("speed_override") or _current_speed_for_role(role)
        if not frozen_by_direction:
            area["tick"] += 1
        _ensure_area(area, rows, width, role)
        family = _family_for_mode(mode)
        if family is text_widgets:
            family.update(area, rows, width, role, now)
        elif family is visual_widgets:
            if not (frozen_by_direction and mode in {"gauge", "scope", "tunnel"}):
                family.update(area, rows, width, role, now)
        elif family is gauge_widgets:
            family.update(
                area,
                rows,
                width,
                role,
                now,
                resolved_direction_motion=_resolved_area_direction_motion,
                stabilize_direction_history=_stabilize_direction_history,
            )
        elif family is image_widgets:
            family.update(area, rows, width, role, now)

        if mode in STEADY_MODES:
            area["next_update"] = now + _steady_mode_delay(mode, area_speed)
        else:
            area["burst_left"] -= 1
            if area["burst_left"] <= 0:
                area["burst_delay"], area["burst_left"] = area["burst_fn"]()
            area["next_update"] = now + area["burst_delay"]
            if mode == "text_wide":
                if area["textwall_pause_until"] > now:
                    area["next_update"] = area["textwall_pause_until"]
                elif area["textwall_reverse_left"] > 0:
                    area["next_update"] = now
            elif mode == "text_spew":
                area["next_update"] = now

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
        line4 = f" --theme {vocab_val} "
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
        if not _showcase_state["active"] or not CONFIG_SCENE:
            return
        header_lines = CONFIG_SCENE.get("showcase_header_lines") or []
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
        if not _showcase_state["active"] or rows < 1:
            return
        label = f"[Left/h] back  [Right/l] forward  [+/-] faster/slower  [Q] exit   Speed: {current_base_speed}"
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

    def _set_showcase_scene(next_idx: int) -> None:
        global CONFIG_SCENE, THEME_ARG
        nonlocal area_specs, area_states
        scenes = _showcase_state.get("scenes", [])
        if not scenes:
            return
        next_idx %= len(scenes)
        _showcase_state["idx"] = next_idx
        _showcase_state["done"] = False
        CONFIG_SCENE = scenes[next_idx]
        THEME_ARG = CONFIG_SCENE.get("theme", THEME_ARG)
        GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)
        area_specs = _current_area_specs(rows, cols)
        area_states = _sync_areas(area_specs)
        _sync_cycle_start_modes(area_specs, area_states, time.time())
        for spec in area_specs:
            _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"])

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
        return build_config_area_specs(CONFIG_SCENE, rows, cols)

    def _current_area_specs(rows: int, cols: int):
        if CONFIG_SCENE and not _demo_state["active"]:
            return _config_area_specs(rows, cols)
        return _legacy_area_specs(cols)

    def _sync_areas(area_specs: list[dict]):
        return sync_area_states(area_specs, area_states, _make_area, _reset_area_timing)

    area_states = {}
    area_specs = _current_area_specs(rows, cols)
    area_states = _sync_areas(area_specs)
    _sync_cycle_start_modes(area_specs, area_states, time.time())
    for spec in area_specs:
        _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"])

    _GLITCH_CHARS = "!@#$%^&*?><|/\\~`[]{}abcdefXYZ0123456789XOXOX##!!??@@$$%%^^&&**"
    _glitch_next = time.time() + GLITCH_INTERVAL if GLITCH_INTERVAL > 0 else float("inf")
    _glitch_active = False
    _glitch_restore_at = 0.0
    _glitch_r0 = _glitch_c0 = _glitch_rh = _glitch_cw = 0
    _paused = False
    _paused_at = 0.0
    _exit_at = time.time() + EXIT_AFTER if EXIT_AFTER is not None else float("inf")

    if _showcase_state["active"] and _showcase_state["next"] == float("inf"):
        _showcase_state["next"] = time.time() + _showcase_state["pair_duration"]

    def _shift_pause_timers(delta: float) -> None:
        nonlocal _glitch_next, _glitch_restore_at
        if delta <= 0.0:
            return
        if _sidebar_cycle:
            _sidebar_cycle["next"] += delta
        for area in area_states.values():
            area["next_update"] += delta
            if area.get("cycle_next_change", 0.0):
                area["cycle_next_change"] += delta
            if area.get("gauge_next_reads_at", 0.0):
                area["gauge_next_reads_at"] += delta
            if area.get("textwall_next_reverse_at", 0.0):
                area["textwall_next_reverse_at"] += delta
            if area.get("textwall_pause_until", 0.0):
                area["textwall_pause_until"] += delta
        if _showcase_state["active"] and _showcase_state["next"] != float("inf"):
            _showcase_state["next"] += delta
        if _demo_state["active"] and _demo_state["next"] != float("inf"):
            _demo_state["next"] += delta
        if _glitch_active and _glitch_restore_at:
            _glitch_restore_at += delta
        elif _glitch_next != float("inf"):
            _glitch_next += delta

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
        _glitch_restore_at = time.time() + random.uniform(0.12, 0.44)

    def _restore_glitch(current_specs):
        nonlocal _glitch_active
        for spec in current_specs:
            area = area_states.get(spec["name"])
            if area:
                _paint_area(area, spec["height"], spec["y"], spec["x"], spec["width"], spec["role"])
        _glitch_active = False

    while True:
        rows, cols = stdscr.getmaxyx()
        now = time.time()
        if now >= _exit_at:
            break
        if _sidebar_cycle and not _paused:
            new_modes = list_sidebar_cycle_modes_for_main(MAIN_MODE, SIDEBAR_CYCLE_MODES)
            if new_modes != _sidebar_cycle["modes"]:
                _sidebar_cycle["modes"] = new_modes
                _sidebar_cycle["idx"] = 0
                _sidebar_cycle["next"] = now + 15.0
        if _sidebar_cycle and not _paused and now >= _sidebar_cycle["next"]:
            _sidebar_cycle["idx"] = (_sidebar_cycle["idx"] + 1) % len(_sidebar_cycle["modes"])
            _sidebar_cycle["next"] = now + 15.0
        area_specs = _current_area_specs(rows, cols)
        area_states = _sync_areas(area_specs)
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
                text_widgets.advance_cycle(area, forbidden)
        for spec in area_specs:
            area = area_states[spec["name"]]
            if not _paused:
                if text_widgets.effective_mode(area) == "readouts":
                    area["gauge_count"] += 1
                _step_area(area, spec["height"], spec["width"], spec["role"], now)
            if spec.get("separator_after"):
                _draw_separator(rows, spec["width"])
            _paint_area(area, spec["height"], spec["y"], spec["x"], spec["width"], spec["role"])
            _draw_area_label(spec["y"], spec["x"], spec["width"], area.get("label"))
        if CONFIG_SCENE and not _demo_state["active"]:
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
            now = time.time()
            if _glitch_active:
                if now >= _glitch_restore_at:
                    _restore_glitch(area_specs)
            elif now >= _glitch_next:
                _fire_glitch()
                _glitch_next = now + GLITCH_INTERVAL * random.uniform(0.70, 1.30)

        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27):
            if CONFIG_SCENE and not _demo_state["active"] and not _showcase_state["active"]:
                return _export_scene_definition(
                    CONFIG_SCENE,
                    area_states,
                    current_base_speed,
                    _current_speed_for_role,
                )
            break
        if _showcase_state["active"] and key in (curses.KEY_LEFT, ord('h'), ord('H')):
            _set_showcase_scene(_showcase_state["idx"] - 1)
            continue
        if _showcase_state["active"] and key in (curses.KEY_RIGHT, ord('l'), ord('L')):
            _set_showcase_scene(_showcase_state["idx"] + 1)
            continue
        if key == ord(' '):
            if _paused:
                _shift_pause_timers(time.time() - _paused_at)
                _paused = False
            else:
                _paused = True
                _paused_at = time.time()
        elif key in (ord('+'), ord('=')):
            current_base_speed = min(100, current_base_speed + 1)
            for area in area_states.values():
                _reset_area_timing(area)
        elif key == ord('-'):
            current_base_speed = max(1, current_base_speed - 1)
            for area in area_states.values():
                _reset_area_timing(area)

        if (not _paused and _demo_state["active"]
                and not _demo_state["done"]
                and time.time() >= _demo_state["next"]):
            next_idx = _demo_state["idx"] + 1
            if next_idx >= len(_demo_state["scenes"]):
                _demo_state["done"] = True
                break
            _demo_state["idx"] = next_idx
            _demo_state["scene"] = _demo_state["scenes"][next_idx]
            THEME_ARG = _demo_state["scene"]["theme"]
            MAIN_MODE = _demo_state["scene"]["main"]
            SIDEBAR_MODE = _demo_state["scene"]["sidebar"]
            GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)
            area_specs = _current_area_specs(rows, cols)
            area_states = _sync_areas(area_specs)
            _sync_cycle_start_modes(area_specs, area_states, time.time())
            for spec in area_specs:
                _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"])
            _demo_state["next"] = time.time() + _demo_state["scene"]["duration"]
        time.sleep(0.01)


# ── Entry point ───────────────────────────────────────────────────────────────



def run(argv=None) -> int:
    global IMAGE_PATHS, SPEED_ARG, MAIN_SPEED_ARG, SIDEBAR_SPEED_ARG
    global LIFE_MAX_ITERATIONS, INJECT_TEXT, MAIN_MODE, _ALL_THEMES
    global THEME_ARG, SIDEBAR_MODE, _demo_state, GLITCH_INTERVAL, CONFIG_SCENE, _showcase_state, EXIT_AFTER

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
    CONFIG_SCENE = config["config_scene"]
    SIDEBAR_MODE = config["sidebar_mode"]
    _demo_state = config["demo_state"]
    _showcase_state = config["widget_showcase"]
    GLITCH_INTERVAL = config["glitch_interval"]
    EXIT_AFTER = config["exit_after"]

    GEN_POOL[:], RCOL_POOL[:] = _build_pools(THEME_ARG)

    while True:
        exported_scene_yaml = None
        try:
            exported_scene_yaml = curses.wrapper(main)
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
    if exported_scene_yaml:
        print(exported_scene_yaml, end="" if exported_scene_yaml.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
