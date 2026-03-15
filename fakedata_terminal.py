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
    from .widgets_gauge import GaugeWidgets
    from .widgets_image import ImageWidgets
    from .widgets_text import TextWidgets
    from .widgets_visual import VisualWidgets
    from .runtime_support import (
        HELP_TEXT_TOPICS_UNIX,
        HELP_TEXT_TOPICS_WIN,
        build_colour_pairs,
        centre_delay as _centre_delay,
        colour_attr_from_spec as _colour_attr_from_spec,
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
    from widgets_gauge import GaugeWidgets
    from widgets_image import ImageWidgets
    from widgets_text import TextWidgets
    from widgets_visual import VisualWidgets
    from runtime_support import (
        HELP_TEXT_TOPICS_UNIX,
        HELP_TEXT_TOPICS_WIN,
        build_colour_pairs,
        centre_delay as _centre_delay,
        colour_attr_from_spec as _colour_attr_from_spec,
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
    {"theme": "science",    "main": "clock",         "sidebar": "matrix",       "duration": 10.0},
    {"theme": "finance",    "main": "oscilloscope",  "sidebar": "blocks",       "duration": 10.0},
    {"theme": "science",    "main": "sweep",         "sidebar": "none",         "duration": 10.0},
    {"theme": "navigation", "main": "readouts",      "sidebar": "none",         "duration": 10.0},
]

SIDEBAR_CYCLE_MODES = [
    "text", "text_wide", "text_spew", "bars", "text_scant",
    "clock", "matrix", "oscilloscope", "blocks", "sweep", "tunnel",
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


def _export_scene_definition(config_scene: dict, area_states: dict[str, dict], current_base_speed: int,
                             current_speed_for_role) -> str | None:
    if not config_scene:
        return None

    scene_name = _scene_name_for_export()
    shortened_data_images = False
    scene_colour = None
    scene_text = config_scene.get("text", "")
    scene_direction = config_scene.get("direction", "right")
    colour_values = {
        area.get("colour")
        for area in config_scene.get("areas", [])
        if area.get("colour") is not None
    }
    if colour_values and len(colour_values) == 1 and len(config_scene.get("areas", [])) == len([
        area for area in config_scene.get("areas", []) if area.get("colour") is not None
    ]):
        scene_colour = next(iter(colour_values))
    scene_body = {
        "layout": config_scene["layout"],
        "theme": config_scene.get("theme"),
        "speed": current_base_speed,
        "text": _escape_export_text_modifier(scene_text),
    }
    if scene_direction != "right":
        scene_body["direction"] = scene_direction
    if scene_colour is not None:
        scene_body["colour"] = scene_colour
    if config_scene.get("glitch", 0.0) > 0:
        scene_body["glitch"] = config_scene["glitch"]
    scene_body["regions"] = {}

    for area in sorted(config_scene.get("areas", []), key=lambda item: (item["x"], item["y"], item["name"])):
        state = area_states.get(area["name"], {})
        role = state.get("role") or ("main" if area["x"] < 0.5 else "sidebar")
        area_speed = state.get("speed_override") or current_speed_for_role(role)
        region_body = {
            "widget": area["mode"],
        }
        if area_speed != scene_body["speed"]:
            region_body["speed"] = area_speed

        area_theme = area.get("theme")
        if area_theme is not None and area_theme != scene_body.get("theme"):
            region_body["source_theme"] = area_theme

        area_text = area.get("text")
        if area_text is not None and area_text != scene_text:
            region_body["text"] = _escape_export_text_modifier(area_text)

        area_colour = area.get("colour")
        if area_colour is not None and area_colour != scene_body.get("colour"):
            region_body["colour"] = area_colour

        area_direction = area.get("direction")
        if area_direction is not None and area_direction != scene_direction:
            region_body["direction"] = area_direction

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
    global MAIN_MODE, SIDEBAR_MODE, THEME_ARG, CONFIG_SCENE, _showcase_state
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
    STEADY_MODES = {"blocks", "clock", "oscilloscope", "sweep", "image", "life", "tunnel"}
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
        vocab_arg_getter=lambda: THEME_ARG,
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

    _area_vocab = text_widgets.area_vocab
    _vocab_pools = text_widgets.vocab_pools
    _make_area_state = text_widgets.make_area_state
    _dense_line = text_widgets.dense_line
    _new_area_text_entry = text_widgets.new_area_text_entry
    _load_helptext_lines = text_widgets.load_helptext_lines
    _next_helptext_entry = text_widgets.next_helptext_entry
    _effective_mode = text_widgets.effective_mode
    _ensure_cycle = text_widgets.ensure_cycle
    _advance_cycle = text_widgets.advance_cycle

    def _sync_cycle_start_modes(area_specs: list[dict], area_states: dict[str, dict], now: float):
        sync_cycle_start_modes(area_specs, area_states, _ensure_cycle, now)

    _ensure_text_buffer = text_widgets.ensure_text_buffer
    _scroll_text_buffer = text_widgets.scroll_text_buffer
    _safe_row_width = text_widgets.safe_row_width
    _repaint_text_buffer = text_widgets.repaint_text_buffer

    visual_widgets = VisualWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        leading_blank=_leading_blank,
        inject_text_getter=lambda: INJECT_TEXT,
        area_vocab=_area_vocab,
        get_gauge_config=get_gauge_config,
        normalize_colour_spec=_normalize_colour_spec,
        colour_attr_from_spec=_colour_attr_from_spec,
        matrix_chars=MATRIX_CHARS,
        sweep_symbols=SWEEP_SYMBOLS,
    )
    _update_scope = visual_widgets.update_scope
    _repaint_scope = visual_widgets.repaint_scope
    _update_bars = visual_widgets.update_bars
    _repaint_bars = visual_widgets.repaint_bars
    _update_matrix = visual_widgets.update_matrix
    _repaint_matrix = visual_widgets.repaint_matrix
    _choose_radar_spin = visual_widgets.choose_radar_spin
    _update_radar = visual_widgets.update_radar
    _repaint_radar = visual_widgets.repaint_radar
    _ensure_blocks = visual_widgets.ensure_blocks
    _update_blocks = visual_widgets.update_blocks
    _repaint_blocks = visual_widgets.repaint_blocks
    _build_nested_box_layers = visual_widgets.build_nested_box_layers
    _build_tunnel_layers = visual_widgets.build_tunnel_layers
    _ensure_tunnel = visual_widgets.ensure_tunnel
    _repaint_nested_layers = visual_widgets.repaint_nested_layers
    _ensure_sweep = visual_widgets.ensure_sweep
    _update_sweep = visual_widgets.update_sweep
    _repaint_sweep = visual_widgets.repaint_sweep
    _update_tunnel = visual_widgets.update_tunnel
    _repaint_tunnel = visual_widgets.repaint_tunnel

    gauge_widgets = GaugeWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        area_vocab=_area_vocab,
        new_area_text_entry=_new_area_text_entry,
        inject_text_getter=lambda: INJECT_TEXT,
        get_gauge_config=get_gauge_config,
        normalize_colour_spec=_normalize_colour_spec,
        colour_attr_from_spec=_colour_attr_from_spec,
        prime_values=prime_values,
    )
    _gauge_parse_num = gauge_widgets.gauge_parse_num
    _readout_use_title = gauge_widgets.readout_use_title
    _readout_line_capacity = gauge_widgets.readout_line_capacity
    _readout_filler_rows = gauge_widgets.readout_filler_rows
    _next_prime_value = gauge_widgets.next_prime_value
    _refresh_readout_rows = gauge_widgets.refresh_readout_rows
    _sync_gauge_vectors = gauge_widgets.sync_gauge_vectors
    _ensure_gauges = gauge_widgets.ensure_gauges
    _next_gauge_spark = gauge_widgets.next_gauge_spark
    _gauge_rows = gauge_widgets.gauge_rows
    _draw_divider = gauge_widgets.draw_divider
    _repaint_gauges = gauge_widgets.repaint_gauges
    _repaint_sparkline = gauge_widgets.repaint_sparkline
    _repaint_readouts = gauge_widgets.repaint_readouts

    image_widgets = ImageWidgets(
        curses_module=curses,
        stdscr=stdscr,
        safe_row_width=_safe_row_width,
        image_module=Image,
        image_paths_getter=lambda: IMAGE_PATHS,
        inject_text_getter=lambda: INJECT_TEXT,
        life_max_getter=lambda: LIFE_MAX_ITERATIONS,
        image_colour_cycle=IMAGE_COLOUR_CYCLE,
        image_trail_attrs=IMAGE_TRAIL_ATTRS,
    )
    _image_message = image_widgets.image_message
    _jp2a_background = image_widgets.jp2a_background
    _fit_ascii_to_panel = image_widgets.fit_ascii_to_panel
    _render_image = image_widgets.render_image
    _ensure_image = image_widgets.ensure_image
    _update_image = image_widgets.update_image
    _life_hash = image_widgets.life_hash
    _seed_life = image_widgets.seed_life
    _ensure_life = image_widgets.ensure_life
    _update_life = image_widgets.update_life
    _repaint_life = image_widgets.repaint_life
    _repaint_image = image_widgets.repaint_image
    _repaint_unavailable = image_widgets.repaint_unavailable
    _repaint_static_lines = image_widgets.repaint_static_lines

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

    def _make_area(mode, vocab_name: str | None = None):
        area = _make_area_state(vocab_name)
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
        if mode in {"clock", "blocks", "sweep", "tunnel"}:
            return delay / 1.5
        return delay

    def _resolved_area_direction_motion(area: dict, now: float) -> int:
        direction = str(area.get("direction_override") or "right").lower()
        if direction == "right":
            area["direction_motion"] = 1
            return 1
        if direction == "left":
            area["direction_motion"] = -1
            return -1
        if now >= area["radar_next_spin_change"]:
            area["radar_spin"] = _choose_radar_spin()
            area["radar_next_spin_change"] = now + random.uniform(0.5, 3.0)
        motion = area.get("radar_spin", 1)
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

    def _reset_area_timing(area: dict):
        role = area.get("role", "main")
        area_speed = area.get("speed_override") or _current_speed_for_role(role)
        area["next_update"] = time.time()
        if _effective_mode(area) in STEADY_MODES:
            area["burst_fn"] = None
            area["burst_delay"] = 0.0
            area["burst_left"] = 0
        else:
            area["burst_fn"] = make_burst_fn(area_speed)
            area["burst_delay"], area["burst_left"] = area["burst_fn"]()

    def _ensure_area(area: dict, rows: int, width: int, role: str):
        if area["mode"] == "cycle":
            _ensure_cycle(area)
        mode = _effective_mode(area)
        area["role"] = role
        if mode in TEXT_MODES:
            _ensure_text_buffer(area, rows, mode, width, role)
        elif mode == "blocks":
            _ensure_blocks(area, rows, width)
        elif mode == "sweep":
            _ensure_sweep(area, rows, width)
        elif mode == "tunnel":
            return
        elif mode in {"gauges", "sparkline", "readouts"}:
            _ensure_gauges(area, rows, width, role, mode)
            if area.get("text_override"):
                if mode == "readouts":
                    area["gauge_title"] = area["text_override"]
                else:
                    area["gauge_scroll_title"] = area["text_override"]
        elif mode == "image":
            _ensure_image(area, rows, width)
        elif mode == "blank":
            return
        elif mode == "life":
            _ensure_life(area, rows, width)
        if mode == "oscilloscope" and not area["scope_warmed"]:
            for _ in range(max(24, width + 24)):
                _update_scope(area, width)
            area["scope_warmed"] = True
        elif mode == "matrix" and not area["matrix_warmed"]:
            for _ in range(max(18, rows * 3)):
                _update_matrix(area, rows, width)
            area["matrix_warmed"] = True
        elif mode == "sweep" and not area["sweep_warmed"]:
            _update_sweep(area, rows, width, role)
            area["sweep_warmed"] = True

    def _step_area(area: dict, rows: int, width: int, role: str, now: float):
        if area["mode"] == "cycle":
            _ensure_cycle(area)
        mode = _effective_mode(area)
        if now < area["next_update"]:
            return
        area_speed = area.get("speed_override") or _current_speed_for_role(role)
        area["tick"] += 1
        _ensure_area(area, rows, width, role)
        if mode in TEXT_MODES:
            if mode == "text_spew":
                _scroll_text_buffer(area, mode, width, role, "up")
            elif mode == "text_wide":
                if area["textwall_reverse_left"] > 0:
                    _scroll_text_buffer(area, mode, width, role, "down")
                    area["textwall_reverse_left"] -= 1
                    if area["textwall_reverse_left"] <= 0:
                        area["textwall_next_reverse_at"] = now + random.uniform(5.0, 15.0)
                elif now >= area["textwall_next_reverse_at"]:
                    if area["textwall_pause_until"] <= 0.0:
                        area["textwall_pause_until"] = now + 1.0
                    elif now >= area["textwall_pause_until"]:
                        area["textwall_pause_until"] = 0.0
                        area["textwall_reverse_left"] = random.randint(10, 80)
                        _scroll_text_buffer(area, mode, width, role, "down")
                        area["textwall_reverse_left"] -= 1
                else:
                    _scroll_text_buffer(area, mode, width, role, "up")
            else:
                interval = 1 if mode == "text" else (5 if role == "sidebar" else 2)
                if area["tick"] % interval == 0:
                    _scroll_text_buffer(area, mode, width, role, "up")
        elif mode == "bars":
            _update_bars(area)
        elif mode == "clock":
            _update_radar(area)
        elif mode == "matrix":
            _update_matrix(area, rows, width)
        elif mode == "blocks":
            _update_blocks(area, rows, width)
        elif mode == "sweep":
            _update_sweep(area, rows, width, role)
        elif mode == "tunnel":
            _update_tunnel(area, rows, width)
        elif mode == "oscilloscope":
            _update_scope(area, width)
        elif mode in {"gauges", "sparkline", "readouts"}:
            if mode == "sparkline":
                motion = _resolved_area_direction_motion(area, now)
                if motion != 0:
                    _stabilize_direction_history(area, width, motion, "gauge_spark")
                    sample = _next_gauge_spark(area)
                    if motion < 0:
                        area["gauge_spark"].insert(0, sample)
                    else:
                        area["gauge_spark"].append(sample)
                    if len(area["gauge_spark"]) > width + 20:
                        if motion < 0:
                            area["gauge_spark"].pop()
                        else:
                            area["gauge_spark"].pop(0)
                    area["direction_motion_prev"] = motion
            else:
                area["gauge_spark"].append(_next_gauge_spark(area))
                if len(area["gauge_spark"]) > width + 20:
                    area["gauge_spark"].pop(0)
            if now >= area["gauge_next_reads_at"]:
                vals = [val_fn() for _, val_fn, _ in area["gauge_reads"]]
                for i, val_str in enumerate(vals):
                    label = area["gauge_reads"][i][0] if i < len(area["gauge_reads"]) else ""
                    if label in {"COUNT", "PRIME"}:
                        continue
                    num = _gauge_parse_num(val_str)
                    if num is None:
                        continue
                    hist = area["gauge_hist"][i]
                    prev_num = hist[-1] if hist else None
                    if prev_num is not None:
                        eps = max(0.005, 0.005 * max(1.0, abs(prev_num)))
                        if num > prev_num + eps:
                            area["gauge_arrows"][i] = "▲"
                        elif num < prev_num - eps:
                            area["gauge_arrows"][i] = "▼"
                        # Otherwise keep the last non-flat direction.
                    hist.append(num)
                    if len(hist) > 4:
                        hist.pop(0)
                area["gauge_last_values"] = vals
                if _area_vocab(area) == "pharmacy" and role == "sidebar":
                    area["gauge_next_reads_at"] = now + 0.80
                elif role == "sidebar":
                    area["gauge_next_reads_at"] = now + 0.45
                else:
                    area["gauge_next_reads_at"] = now + 0.30
            area["gauge_tick"] += 1
            if mode == "gauges" and area["gauge_tick"] >= 5:
                area["gauge_tick"] = 0
                area["gauge_feed"].pop(0)
                area["gauge_feed"].append(
                    _new_area_text_entry("text", width, {"text": area["feed_text"], "vocab_override": _area_vocab(area)}, role)
                )
        elif mode == "image":
            _update_image(area, rows, width)
        elif mode == "life":
            _update_life(area, rows, width)
        elif mode == "blank":
            pass

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
        mode = _effective_mode(area)
        if mode in TEXT_MODES:
            _repaint_text_buffer(area["buf"], rows, y, x, width)
        elif mode == "bars":
            _repaint_bars(area, rows, y, x, width)
        elif mode == "clock":
            _repaint_radar(area, rows, y, x, width)
        elif mode == "matrix":
            _repaint_matrix(area, rows, y, x, width)
        elif mode == "blocks":
            _repaint_blocks(area, rows, y, x, width)
        elif mode == "sweep":
            _repaint_sweep(area, rows, y, x, width, role)
        elif mode == "tunnel":
            _repaint_tunnel(area, rows, y, x, width)
        elif mode == "oscilloscope":
            _repaint_scope(area, rows, y, x, width)
        elif mode == "gauges":
            _repaint_gauges(area, rows, y, x, width)
        elif mode == "sparkline":
            _repaint_sparkline(area, rows, y, x, width)
        elif mode == "readouts":
            _repaint_readouts(area, rows, y, x, width)
        elif mode == "image":
            _repaint_image(area, rows, y, x, width)
        elif mode == "life":
            _repaint_life(area, rows, y, x, width)
        elif mode == "blank":
            if area.get("static_lines") or area.get("text_override") or INJECT_TEXT:
                _repaint_static_lines(area, rows, y, x, width)
            elif area.get("unavailable_message"):
                _repaint_unavailable(area, rows, y, x, width)
            else:
                blank = " " * width
                for r in range(rows):
                    try:
                        stdscr.addnstr(y + r, x, blank, width, curses.color_pair(1))
                    except curses.error:
                        pass

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
                    _effective_mode(other)
                    for other_name, other in area_states.items()
                    if other_name != spec["name"] and other["mode"] == "cycle"
                }
                _advance_cycle(area, forbidden)
        for spec in area_specs:
            area = area_states[spec["name"]]
            if not _paused:
                if _effective_mode(area) == "readouts":
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
    global THEME_ARG, SIDEBAR_MODE, _demo_state, GLITCH_INTERVAL, CONFIG_SCENE, _showcase_state

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
                    "_repaint_text_buffer",
                    "_repaint_readouts",
                    "_repaint_bars",
                    "_repaint_scope",
                    "_repaint_sparkline",
                    "_repaint_blocks",
                    "_repaint_sweep",
                    "_repaint_life",
                    "_ensure_area",
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
