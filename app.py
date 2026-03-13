#!/usr/bin/env python3
"""Curses runtime for FakeData Terminal."""

import collections
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
import traceback

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

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_NAME = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else os.path.basename(__file__)
CONFIG_STYLE = None
_showcase_state = {"active": False, "scenes": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

try:
    from .cli_config import prepare_runtime_config, show_startup_banner
    from .vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )
except ImportError:
    from cli_config import prepare_runtime_config, show_startup_banner
    from vocab import (
        GEN_POOL, RCOL_POOL, _P_MAIN_GEN_POOL, _P_MAIN_RCOL_POOL, _P_SIDEBAR_SPIKE_POOL,
        HEX_WORD, _build_pools, get_bar_config, get_gauge_config, random_line, random_rcol_line,
    )

DEMO_SCENES = [
    {"style": "hacker",     "main": "text_wide",     "sidebar": "bars",         "duration": 10.0},
    {"style": "medicine",   "main": "readouts",      "sidebar": "text_scant",   "duration": 10.0},
    {"style": "pharmacy",   "main": "text",          "sidebar": "sparkline",    "duration": 10.0},
    {"style": "spaceteam",  "main": "bars",          "sidebar": "text_wide",    "duration": 10.0},
    {"style": "science",    "main": "clock",         "sidebar": "matrix",       "duration": 10.0},
    {"style": "finance",    "main": "oscilloscope",  "sidebar": "blocks",       "duration": 10.0},
    {"style": "science",    "main": "sweep",         "sidebar": "none",         "duration": 10.0},
    {"style": "navigation", "main": "readouts",      "sidebar": "none",         "duration": 10.0},
]

SIDEBAR_CYCLE_MODES = [
    "text", "text_wide", "text_spew", "bars", "text_scant",
    "clock", "matrix", "oscilloscope", "blocks", "sweep", "tunnel", "boxes",
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

COLOUR_PAIRS = {
    1: (curses.COLOR_GREEN,  curses.COLOR_BLACK),
    2: (curses.COLOR_WHITE,  curses.COLOR_BLACK),
    3: (curses.COLOR_CYAN,   curses.COLOR_BLACK),
    4: (curses.COLOR_YELLOW, curses.COLOR_BLACK),
    5: (curses.COLOR_RED,    curses.COLOR_BLACK),
    6: (82,                  curses.COLOR_BLACK),
    7: (curses.COLOR_CYAN,   curses.COLOR_BLACK),
    8: (curses.COLOR_BLUE,   curses.COLOR_BLACK),
    9: (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
}

# ── Paragraph colour state machine (left column) ──────────────────────────────
#
# "green"  (~60%) – lines use green / bright-green family
# "red"    (~25%) – lines use red
# "mixed"  (~15%) – each line independently 75% green / 25% red

PARA_THEMES = ["green"] * 60 + ["red"] * 25 + ["mixed"] * 15

def _new_paragraph():
    """Return (theme, remaining_lines)."""
    theme = random.choice(PARA_THEMES)
    if theme == "red":
        length = random.randint(3, 10)   # red runs are short and punchy
    elif theme == "mixed":
        length = random.randint(8, 30)
    else:
        length = random.randint(10, 40)
    return theme, length

def _line_colour(line: str, theme: str) -> tuple:
    """Return (pair_index, bold) for *line* under *theme*."""
    if theme == "red":
        use_red = True
    elif theme == "green":
        use_red = False
    else:  # mixed
        use_red = random.random() < 0.25

    if use_red:
        if line.startswith("!!"):          return 5, True
        if "FAIL" in line or "WARN" in line: return 4, False
        return 5, False
    else:
        if line.startswith("!!"):          return 5, True
        if "FAIL" in line or "ERR" in line: return 4, False
        if line.startswith("  ["):         return 3, False
        if line.startswith("["):
            if random.random() < 0.12:     return 2, True
        if random.random() < 0.08:        return 6, True
        return 1, False

# ── Right-column colour ───────────────────────────────────────────────────────

def _rcol_colour(_line: str) -> tuple:
    if random.random() < 0.07: return 6, True
    if random.random() < 0.09: return 3, False
    return 7, False

# ── Speed helpers (1-100 scale) ───────────────────────────────────────────────
#
# speed 1   → centre ~1.000 s/line
# speed 50  → centre ~0.022 s/line
# speed 100 → 0 s (no sleep)
#
# We use exponential interpolation over speed 1-99, then treat 100 specially.

BURST_SIZE = 40

def _centre_delay(speed: int) -> float:
    if speed >= 100:
        return 0.0
    # speed 1 → 1.0 s,  speed 99 → 0.004 s
    lo, hi = math.log(0.004), math.log(1.0)
    t = (speed - 1) / 98          # 0.0 … 1.0
    return math.exp(hi + t * (lo - hi))

def make_burst_fn(speed: int):
    centre = _centre_delay(speed)
    if centre == 0.0:
        # Speed 100: constant zero delay, fixed burst length
        def new_burst():
            return 0.0, BURST_SIZE
        return new_burst

    tiers = [
        (centre * 0.40, centre * 0.75,  30),   # fast burst
        (centre * 0.80, centre * 1.30,  45),   # normal
        (centre * 1.50, centre * 3.00,  25),   # slow / dramatic
    ]
    pool = [t for t in tiers for _ in range(t[2])]

    def new_burst():
        lo, hi, _ = random.choice(pool)
        delay = random.uniform(lo, hi)
        count = BURST_SIZE + random.randint(-12, 12)
        return delay, count

    return new_burst

def _clamp_speed(speed: int) -> int:
    return max(1, min(100, int(speed)))

def _scaled_speed(base_speed: int, ratio: float) -> int:
    return _clamp_speed(round(base_speed * ratio))

def _strip_overstrikes(text: str) -> str:
    # man output can include overstrike sequences like "x\b x".
    return re.sub(r".\x08", "", text)

# ── Main ──────────────────────────────────────────────────────────────────────

def main(stdscr):
    global MAIN_MODE, SIDEBAR_MODE, STYLE_ARG, CONFIG_STYLE, _showcase_state
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
    STEADY_MODES = {"blocks", "clock", "oscilloscope", "sweep", "image", "life", "tunnel", "boxes"}
    STYLE_VOCAB_MODES = {"text", "text_wide", "text_scant", "bars"}
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
    jp2a_cache = {}
    helptext_topics_unix = [
        "bash", "sh", "ls", "find", "grep", "sed", "awk", "ps", "tar", "ssh",
        "systemd", "cron", "mount", "chmod", "chown", "printf", "make", "git",
    ]
    helptext_topics_win = [
        "Get-Process", "Get-Service", "Get-ChildItem", "Get-ItemProperty",
        "Get-Command", "Get-CimClass", "Get-EventLog", "Get-NetAdapter",
        "Get-ComputerInfo", "about_Arrays", "about_Pipelines", "about_Objects",
    ]
    primes_path = os.path.join(os.path.dirname(__file__), "data", "primes.txt")
    try:
        with open(primes_path, "r", encoding="utf-8") as prime_file:
            prime_values = [line.strip() for line in prime_file if line.strip()]
    except OSError:
        prime_values = ["2", "3", "5", "7", "11"]
    if not prime_values:
        prime_values = ["2", "3", "5", "7", "11"]

    def layout(cols):
        side_mode = _effective_sidebar_mode()
        if side_mode == "none":
            return cols, 0, None
        sw = max(28, cols // 3)
        mw = cols - sw - 1
        if mw < 28:
            return cols, 0, None
        return mw, sw, mw + 1

    def _sidebar_cycle_modes_for_main(main_mode: str):
        if main_mode in ("text", "text_wide"):
            blocked = {"text", "text_wide", main_mode}
        else:
            blocked = {main_mode}
        modes = [m for m in SIDEBAR_CYCLE_MODES if m not in blocked]
        return modes if modes else ["readouts"]

    def _cycle_widget_names(include_image: bool) -> list[str]:
        names = [
            "bars", "blocks", "clock", "image", "life", "matrix",
            "oscilloscope", "readouts", "sparkline", "sweep", "tunnel", "boxes",
            "text", "text_scant", "text_spew", "text_wide",
        ]
        if not include_image:
            names = [name for name in names if name != "image"]
        return names

    _sidebar_cycle = None
    if SIDEBAR_MODE == "cycle":
        _sidebar_cycle = {
            "modes": _sidebar_cycle_modes_for_main(MAIN_MODE),
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

    style_pool_cache = {}

    def _area_style(area: dict) -> str:
        return area.get("style_override") or STYLE_ARG

    def _style_pools(style_name: str):
        pools = style_pool_cache.get(style_name)
        if pools is None:
            pools = _build_pools(style_name)
            style_pool_cache[style_name] = pools
        return pools

    def _make_text_state():
        theme, left = _new_paragraph()
        return {"theme": theme, "left": left, "countdown": random.randint(35, 50)}

    def _make_area_state(style_name: str | None = None):
        area_style = style_name or STYLE_ARG
        bar_headers, bar_labels = get_bar_config(area_style)
        return {
            "buf": [],
            "tick": 0,
            "text": _make_text_state(),
            "feed_text": _make_text_state(),
            "bars_headers": bar_headers[:],
            "bars_labels": bar_labels[:],
            "bars_values": [random.uniform(0.08, 0.92) for _ in bar_labels],
            "bars_drift": [random.gauss(0, 0.02) for _ in bar_labels],
            "scope_vals": [],
            "scope_drift": 0.0,
            "scope_phase": random.uniform(0.0, math.tau),
            "scope_warmed": False,
            "matrix_cols": [],
            "matrix_warmed": False,
            "sweep_warmed": False,
            "cycle_catalog": [],
            "cycle_widgets": [],
            "cycle_order": [],
            "cycle_idx": 0,
            "cycle_next_change": 0.0,
            "cycle_current": None,
            "radar_angle": 0.0,
            "radar_blips": [],
            "radar_tick": 0,
            "radar_spin": 1,
            "radar_next_spin_change": 0.0,
            "gauge_tick": 0,
            "gauge_signal": None,
            "gauge_title": "",
            "gauge_base_reads": [],
            "gauge_reads": [],
            "gauge_scroll_title": "",
            "gauge_spark": [],
            "gauge_drift": 0.0,
            "gauge_feed": [],
            "gauge_hist": [],
            "gauge_arrows": [],
            "gauge_last_values": [],
            "gauge_next_reads_at": 0.0,
            "gauge_count": 0,
            "gauge_prime_idx": 0,
            "blocks_bg": random.choice([1, 3, 7]),
            "blocks_cells": [],
            "sweep_cells": [],
            "sweep_pos": 0,
            "sweep_dir": 1,
            "boxes_sig": None,
            "boxes_layers": [],
            "tunnel_sig": None,
            "tunnel_layers": [],
            "tunnel_phase": random.random(),
            "tunnel_palette_idx": random.randrange(6),
            "tunnel_drift_phase": random.uniform(0.0, math.tau),
            "next_update": 0.0,
            "burst_fn": None,
            "burst_delay": 0.0,
            "burst_left": 0,
            "image_sig": None,
            "image_frames": [],
            "image_from": 0,
            "image_to": 1,
            "image_wipe_row": 0,
            "image_colour_idx": 0,
            "image_paths": [],
            "life_sig": None,
            "life_cells": [],
            "life_ages": [],
            "life_iteration": 0,
            "life_hashes": collections.deque(maxlen=8),
            "helptext_lines": collections.deque(),
            "helptext_topic": "",
            "helptext_topic_idx": 0,
            "textwall_next_reverse_at": 0.0,
            "textwall_pause_until": 0.0,
            "textwall_reverse_left": 0,
            "style_override": style_name,
            "unavailable_message": None,
            "static_lines": [],
        }

    def _dense_line(width: int, line_fn=None) -> str:
        if line_fn is None:
            line_fn = random_line
        mode = random.random()
        if mode < 0.12:
            label = random.choice([
                "MEMORY MAP", "ACTIVE LINKS", "WORK QUEUE", "STATUS BUS",
                "CHECKPOINT", "ANALYSIS GRID", "SIGNAL PATH", "ARCHIVE INDEX",
            ])
            return (f"[ {label} ] ".ljust(min(width, len(label) + 4), "═"))[:width]
        if mode < 0.28:
            left_w = max(12, width // 2 - 2)
            left = line_fn()[:left_w].ljust(left_w)
            right = line_fn()[:max(8, width - left_w - 3)]
            return f"{left} │ {right}"[:width]
        if mode < 0.42:
            cols = max(2, min(6, width // 14))
            return "  ".join(f"{HEX_WORD(4)} {random.randint(0,9999):04d}" for _ in range(cols))[:width]
        if mode < 0.58:
            chars = " .:-=+*#%@"
            span = max(8, width - 4)
            graph = "".join(chars[min(len(chars) - 1, int(random.random() * (len(chars) - 1)))]
                            for _ in range(span))
            return f"SIG {graph}"[:width]
        return line_fn()[:width]

    def _new_area_text_entry(mode: str, width: int, state: dict, role: str):
        txt_state = state["text"]
        area_style = _area_style(state)
        is_pharm = (area_style == "pharmacy")
        gen_pool, rcol_pool = _style_pools(area_style)
        if is_pharm and role == "main":
            line_fn = lambda: random.choice(_P_MAIN_GEN_POOL)()
            rcol_fn = lambda: random.choice(_P_MAIN_RCOL_POOL)()
        else:
            line_fn = lambda: random.choice(gen_pool)()
            rcol_fn = lambda: random.choice(rcol_pool)()

        if mode == "text_scant":
            if is_pharm and role == "sidebar":
                blank_prob = 0.0
            else:
                blank_prob = 0.55 if role == "sidebar" else 0.20
            if random.random() < blank_prob:
                return "", curses.color_pair(1), width
            if is_pharm and role == "sidebar":
                txt = random.choice(_P_SIDEBAR_SPIKE_POOL)()
            else:
                txt = rcol_fn()
            cp, bold = _rcol_colour(txt)
            a = curses.color_pair(cp) | (curses.A_BOLD if bold else 0)
            vis = width
        else:
            txt = _dense_line(width, line_fn=line_fn) if mode == "text_wide" else line_fn()
            cp, bold = _line_colour(txt, txt_state["theme"])
            a = curses.color_pair(cp) | (curses.A_BOLD if bold else 0)
            txt_state["left"] -= 1
            if txt_state["left"] <= 0:
                txt_state["theme"], txt_state["left"] = _new_paragraph()
            vis = width if mode == "text_wide" else _rand_line_len(width)

        if INJECT_TEXT:
            txt_state["countdown"] -= 1
            if txt_state["countdown"] <= 0:
                txt_state["countdown"] = random.randint(35, 50)
                txt = _splice_text(txt, INJECT_TEXT, width)
        if mode in {"text", "text_scant", "text_wide"}:
            txt = _leading_blank(txt, width)
            vis = min(width, vis + 1)
        return txt[:width], a, min(vis, width)

    def _load_helptext_lines(area: dict):
        if sys.platform == "win32":
            shell_cmd = shutil.which("pwsh") or shutil.which("powershell")
            topics = helptext_topics_win
            if shell_cmd is None:
                lines = ["[text_spew] PowerShell not found on PATH."]
                topic = "powershell-missing"
            else:
                topic = topics[area["helptext_topic_idx"] % len(topics)]
                area["helptext_topic_idx"] += 1
                cmd = [
                    shell_cmd,
                    "-NoProfile",
                    "-Command",
                    f"Get-Help {topic} -Full | Out-String -Width 500",
                ]
                try:
                    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    lines = proc.stdout.splitlines()
                except subprocess.CalledProcessError:
                    lines = [f"[text_spew] failed to load PowerShell help for {topic}."]
        else:
            topic = helptext_topics_unix[area["helptext_topic_idx"] % len(helptext_topics_unix)]
            area["helptext_topic_idx"] += 1
            env = os.environ.copy()
            env["MANPAGER"] = "cat"
            env["PAGER"] = "cat"
            env["MANWIDTH"] = "500"
            try:
                proc = subprocess.run(
                    ["man", topic],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                lines = _strip_overstrikes(proc.stdout).splitlines()
            except subprocess.CalledProcessError:
                lines = [f"[text_spew] failed to load man page for {topic}."]
        area["helptext_topic"] = topic
        if not lines:
            lines = [f"[text_spew] empty output for {topic}."]
        header = f"[ text_spew :: {topic} ]"
        area["helptext_lines"].extend([
            header,
            "",
            *lines,
            "",
            "",
        ])

    def _next_helptext_entry(width: int, area: dict):
        while len(area["helptext_lines"]) < 40:
            _load_helptext_lines(area)
        txt = area["helptext_lines"].popleft()
        if not txt:
            return "", curses.color_pair(1), width
        cp, bold = 2, False
        if txt.startswith("[ text_spew ::"):
            cp, bold = 2, True
        elif txt.lstrip().startswith(("NAME", "SYNOPSIS", "DESCRIPTION", "PARAMETERS", "INPUTS", "OUTPUTS", "NOTES")):
            cp, bold = 2, False
        attr = curses.color_pair(cp) | (curses.A_BOLD if bold else 0)
        return txt[:width], attr, width

    def _effective_mode(area: dict) -> str:
        if area["mode"] == "cycle":
            return area.get("cycle_current") or "text"
        return area["mode"]

    def _ensure_cycle(area: dict):
        include_image = bool(area.get("image_paths") or IMAGE_PATHS)
        desired = area.get("cycle_widgets") or _cycle_widget_names(include_image)
        if not include_image:
            desired = [name for name in desired if name != "image"]
        desired = [name for name in desired if name not in {"cycle", "blank"}]
        seen = set()
        desired = [name for name in desired if not (name in seen or seen.add(name))]
        if not desired:
            desired = _cycle_widget_names(include_image)
        if desired != area["cycle_catalog"]:
            area["cycle_catalog"] = desired[:]
            area["cycle_order"] = desired[:]
            random.shuffle(area["cycle_order"])
            area["cycle_idx"] = 0
            area["cycle_current"] = area["cycle_order"][0] if area["cycle_order"] else "text"
            area["cycle_next_change"] = time.time() + random.uniform(0.0, 10.0)
            area["label"] = area["cycle_current"]
            area["next_update"] = 0.0

    def _advance_cycle(area: dict, forbidden: set[str] | None = None):
        _ensure_cycle(area)
        forbidden = forbidden or set()
        if not area["cycle_order"]:
            area["cycle_current"] = "text"
            area["label"] = "text"
            area["cycle_next_change"] = time.time() + 10.0
            return
        candidates = [name for name in area["cycle_catalog"] if name not in forbidden and name != area.get("cycle_current")]
        if not candidates:
            candidates = [name for name in area["cycle_catalog"] if name != area.get("cycle_current")]
        if not candidates:
            candidates = area["cycle_catalog"][:]
        next_widget = random.choice(candidates) if candidates else "text"
        area["cycle_current"] = next_widget
        if next_widget in area["cycle_order"]:
            area["cycle_idx"] = area["cycle_order"].index(next_widget)
        area["label"] = area["cycle_current"]
        area["cycle_next_change"] = time.time() + 10.0
        area["next_update"] = 0.0

    def _sync_cycle_start_modes(area_specs: list[dict], area_states: dict[str, dict], now: float):
        used = set()
        for spec in area_specs:
            area = area_states[spec["name"]]
            if area["mode"] != "cycle":
                continue
            _ensure_cycle(area)
            current = area.get("cycle_current")
            if current and current not in used:
                used.add(current)
                continue
            candidates = [name for name in area["cycle_catalog"] if name not in used]
            if not candidates:
                candidates = area["cycle_catalog"][:]
            if not candidates:
                current = "text"
            else:
                current = random.choice(candidates)
            area["cycle_current"] = current
            area["label"] = current
            if current in area["cycle_order"]:
                area["cycle_idx"] = area["cycle_order"].index(current)
            area["cycle_next_change"] = now + random.uniform(0.0, 10.0)
            area["next_update"] = 0.0
            used.add(current)

    def _ensure_text_buffer(area: dict, rows: int, mode: str, width: int, role: str):
        buf = area["buf"]
        while len(buf) < rows:
            if mode == "text_spew":
                buf.append(_next_helptext_entry(width, area))
            else:
                buf.append(_new_area_text_entry(mode, width, area, role))
        while len(buf) > rows:
            buf.pop(0)
        if mode == "text_wide" and area["textwall_next_reverse_at"] <= 0.0:
            area["textwall_next_reverse_at"] = time.time() + random.uniform(5.0, 15.0)

    def _scroll_text_buffer(area: dict, mode: str, width: int, role: str, direction: str):
        if not area["buf"]:
            return
        next_entry = _next_helptext_entry(width, area) if mode == "text_spew" else _new_area_text_entry(mode, width, area, role)
        if direction == "up":
            area["buf"].pop(0)
            area["buf"].append(next_entry)
        else:
            area["buf"].pop()
            area["buf"].insert(0, next_entry)

    def _safe_row_width(y: int, r: int, x: int, width: int) -> int:
        """Width clipped to viewport, avoiding terminal lower-right write."""
        max_rows, max_cols = stdscr.getmaxyx()
        abs_row = y + r
        if width <= 0 or x >= max_cols or abs_row < 0 or abs_row >= max_rows:
            return 0
        w = min(width, max_cols - x)
        # Writing into lower-right can trigger terminal wrap/scroll artifacts.
        if abs_row == max_rows - 1 and x + w >= max_cols:
            w = max(0, max_cols - x - 1)
        return w

    def _repaint_text_buffer(buf, nrows, y, x, width):
        blank = " " * width
        for r in range(nrows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            txt, attr, vis = buf[r]
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
            except curses.error:
                pass
            if not txt:
                continue
            try:
                draw_w = max(0, min(vis, safe_w))
                if draw_w:
                    stdscr.addnstr(y + r, x, txt[:draw_w].ljust(draw_w), draw_w, attr)
            except curses.error:
                pass

    def _update_scope(area: dict, width: int):
        cfg = get_gauge_config(_area_style(area))
        area["scope_signal"] = cfg[1]
        raw = area["scope_signal"]()
        phase = area.get("scope_phase", 0.0)
        phase += 0.22 + raw * 0.34 + random.uniform(-0.04, 0.04)
        area["scope_phase"] = phase % math.tau

        # Keep the scope centered on a stable midline and vary amplitude/texture instead.
        amplitude = 0.16 + raw * 0.18
        harmonic = math.sin(phase * 2.7 + raw * 3.0) * 0.05
        noise = random.gauss(0, 0.025)
        spike = 0.0
        if random.random() < 0.04:
            spike = random.choice([-1.0, 1.0]) * random.uniform(0.05, 0.16)
        nxt = 0.5 + math.sin(phase) * amplitude + harmonic + noise + spike
        area["scope_vals"].append(max(0.04, min(0.96, nxt)))
        keep = max(12, width + 12)
        if len(area["scope_vals"]) > keep:
            area["scope_vals"] = area["scope_vals"][-keep:]

    def _repaint_scope(area: dict, nrows: int, y: int, x: int, width: int):
        vals = area["scope_vals"][-width:] or [0.5] * width
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        mid = nrows // 2
        for c in range(0, width, 4):
            canvas[mid][c] = "·"
        prev_y = None
        for c, v in enumerate(vals):
            sample_y = int((1.0 - v) * max(1, nrows - 1))
            sample_y = max(0, min(nrows - 1, sample_y))
            canvas[sample_y][c] = "█"
            if prev_y is not None:
                lo, hi = sorted((prev_y, sample_y))
                for yy in range(lo, hi + 1):
                    if canvas[yy][c] == " ":
                        canvas[yy][c] = "│"
            prev_y = sample_y
        for r in range(nrows):
            frac = r / max(1, nrows - 1)
            cp = 3 if frac < 0.33 else (5 if frac > 0.66 else 6)
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, "".join(canvas[r])[:safe_w], safe_w, curses.color_pair(cp))
            except curses.error:
                pass

    def _update_bars(area: dict):
        for i in range(len(area["bars_values"])):
            area["bars_drift"][i] += random.gauss(0, 0.035)
            area["bars_drift"][i] *= 0.72
            if random.random() < 0.08:
                area["bars_drift"][i] += random.choice([-1, 1]) * random.uniform(0.10, 0.22)
            area["bars_values"][i] = max(0.02, min(0.99, area["bars_values"][i] + area["bars_drift"][i]))

    def _repaint_bars(area: dict, nrows: int, y: int, x: int, width: int):
        blank = " " * width
        meter_w = max(8, width - 18)
        for r in range(nrows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
            except curses.error:
                pass
            if r % 5 == 0:
                label = random.choice(area["bars_headers"])
                line = f"[ {label} ]".center(width, "─")
                attr = curses.color_pair(3) | curses.A_DIM
            else:
                idx = (r - (area["tick"] // 2)) % len(area["bars_labels"])
                value = area["bars_values"][idx]
                filled = int(value * meter_w)
                bar = "█" * filled + "·" * (meter_w - filled)
                line = f"{area['bars_labels'][idx]:<7s} [{bar}] {int(value * 100):3d}%"
                attr = (curses.color_pair(5) | curses.A_BOLD) if value > 0.78 else (
                    curses.color_pair(3) if value > 0.48 else curses.color_pair(6))
            line = _leading_blank(line, width)
            try:
                stdscr.addnstr(y + r, x, line[:safe_w].ljust(safe_w), safe_w, attr)
            except curses.error:
                pass

    def _update_matrix(area: dict, nrows: int, width: int):
        cols = area["matrix_cols"]
        while len(cols) < width:
            cols.append({
                "head": random.randint(-nrows, 0),
                "tail": random.randint(4, max(6, nrows // 3)),
                "speed": random.choice([1, 1, 1, 2]),
                "active": random.random() < 0.25,
            })
        if len(cols) > width:
            del cols[width:]
        for col in cols:
            if not col["active"]:
                if random.random() < 0.035:
                    col["active"] = True
                    col["head"] = random.randint(-nrows, 0)
                    col["tail"] = random.randint(4, max(6, nrows // 3))
                    col["speed"] = random.choice([1, 1, 2])
                continue
            col["head"] += col["speed"]
            if col["head"] - col["tail"] > nrows + random.randint(0, 6):
                col["active"] = False

    def _repaint_matrix(area: dict, nrows: int, y: int, x: int, width: int):
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        attr_map = [[curses.color_pair(1) for _ in range(width)] for _ in range(nrows)]
        for c, col in enumerate(area["matrix_cols"][:width]):
            if not col["active"]:
                continue
            for r in range(max(0, col["head"] - col["tail"]), min(nrows, col["head"] + 1)):
                age = col["head"] - r
                ch = random.choice(MATRIX_CHARS)
                if age == 0:
                    attr = curses.color_pair(2) | curses.A_BOLD
                elif age < 3:
                    attr = curses.color_pair(6)
                else:
                    attr = curses.color_pair(1)
                canvas[r][c] = ch
                attr_map[r][c] = attr
        for r in range(nrows):
            for c in range(width):
                try:
                    stdscr.addch(y + r, x + c, canvas[r][c], attr_map[r][c])
                except curses.error:
                    pass

    def _choose_radar_spin() -> int:
        roll = random.random()
        if roll < 0.5:
            return 1
        if roll < 0.9:
            return -1
        return 0

    def _update_radar(area: dict):
        now = time.time()
        if now >= area["radar_next_spin_change"]:
            area["radar_spin"] = _choose_radar_spin()
            area["radar_next_spin_change"] = now + random.uniform(0.5, 3.0)
        area["radar_angle"] = (area["radar_angle"] + (0.12 * area["radar_spin"])) % (math.pi * 2)
        area["radar_tick"] += 1
        fresh = []
        for ang, dist, ttl in area["radar_blips"]:
            ttl -= 1
            if ttl > 0:
                fresh.append((ang, dist, ttl))
        area["radar_blips"] = fresh
        if random.random() < 0.18:
            area["radar_blips"].append((
                random.uniform(0, math.pi * 2),
                random.uniform(0.15, 0.95),
                random.randint(10, 24),
            ))

    def _repaint_radar(area: dict, nrows: int, y: int, x: int, width: int):
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        attrs = [[curses.color_pair(1) for _ in range(width)] for _ in range(nrows)]
        cx = (width - 1) / 2.0
        cy = (nrows - 1) / 2.0
        # Assume conventional terminal cells are roughly twice as tall as they are wide.
        # Keep this face ratio constant across layouts instead of stretching to the panel.
        face_aspect = 2.0  # horizontal radius / vertical radius in character cells
        xroom = max(0.0, cx - 1.0)
        yroom = max(0.0, cy - 1.0)
        if xroom <= 0.0 or yroom <= 0.0:
            return
        xrad = min(xroom, yroom * face_aspect)
        yrad = xrad / face_aspect
        c_mid = int(round(cx))
        r_mid = int(round(cy))
        for r in range(nrows):
            for c in range(width):
                dx = (c - cx) / max(1.0, xrad)
                dy = (r - cy) / max(1.0, yrad)
                dist = math.sqrt(dx * dx + dy * dy)
                if abs(dist - 1.0) < 0.08:
                    canvas[r][c] = "•"
                    attrs[r][c] = curses.color_pair(3)
                ang = math.atan2(dy, dx)
                delta = abs((ang - area["radar_angle"] + math.pi) % (math.pi * 2) - math.pi)
                if dist <= 1.0 and delta < 0.08:
                    if delta < 0.02:
                        canvas[r][c] = "█"
                    else:
                        canvas[r][c] = "▓"
                    attrs[r][c] = curses.color_pair(2)

        markers = [
            (int(round(cy - yrad)), c_mid, "▲"),
            (r_mid, int(round(cx + xrad)), "▶"),
            (int(round(cy + yrad)), c_mid, "▼"),
            (r_mid, int(round(cx - xrad)), "◀"),
        ]
        for mr, mc, ch in markers:
            if 0 <= mr < nrows and 0 <= mc < width:
                canvas[mr][mc] = ch
                attrs[mr][mc] = curses.color_pair(2) | curses.A_BOLD

        if 0 <= r_mid < nrows and 0 <= c_mid < width:
            canvas[r_mid][c_mid] = "◉"
            attrs[r_mid][c_mid] = curses.color_pair(2) | curses.A_BOLD

        for ang, dist, ttl in area["radar_blips"]:
            px = int(round(cx + math.cos(ang) * xrad * dist))
            py = int(round(cy + math.sin(ang) * yrad * dist))
            if 0 <= py < nrows and 0 <= px < width:
                canvas[py][px] = "◆" if ttl > 16 else "◉"
                attrs[py][px] = curses.color_pair(5)
                # Add a faint halo so contacts stand out from the sweep.
                for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                    if 0 <= ny < nrows and 0 <= nx < width and canvas[ny][nx] == " ":
                        canvas[ny][nx] = "·"
                        attrs[ny][nx] = curses.color_pair(2)
        for r in range(nrows):
            for c in range(width):
                try:
                    stdscr.addch(y + r, x + c, canvas[r][c], attrs[r][c])
                except curses.error:
                    pass

    def _ensure_blocks(area: dict, rows: int, width: int):
        bg = area["blocks_bg"]
        cells = area["blocks_cells"]
        while len(cells) < rows:
            cells.append([bg] * width)
        if len(cells) > rows:
            del cells[rows:]
        for r in range(rows):
            row = cells[r]
            if len(row) < width:
                row.extend([bg] * (width - len(row)))
            elif len(row) > width:
                del row[width:]

    def _update_blocks(area: dict, rows: int, width: int):
        _ensure_blocks(area, rows, width)
        cells = area["blocks_cells"]
        rect_count = random.randint(1, 3)
        palette = [cp for cp in [0, 1, 2, 3, 4, 5, 6, 7] if cp != area["blocks_bg"]]
        for _ in range(rect_count):
            rh = random.randint(1, max(1, rows // 3))
            rw = random.randint(2, max(2, width // 3))
            r0 = random.randint(0, max(0, rows - rh))
            c0 = random.randint(0, max(0, width - rw))
            cp = random.choice(palette)
            for r in range(r0, r0 + rh):
                cells[r][c0:c0 + rw] = [cp] * rw

    def _repaint_blocks(area: dict, nrows: int, y: int, x: int, width: int):
        _ensure_blocks(area, nrows, width)
        for r in range(nrows):
            for c in range(width):
                cp = area["blocks_cells"][r][c]
                ch = " " if cp == 0 else "█"
                try:
                    stdscr.addch(y + r, x + c, ch, curses.color_pair(cp))
                except curses.error:
                    pass

    def _build_nested_box_layers(rows: int, width: int, side_border_width: int = 1):
        layers = []
        inset_y = 0
        inset_x = 0
        step_x = max(1, side_border_width)
        while True:
            top = inset_y
            left = inset_x
            bottom = rows - 1 - inset_y
            right = width - 1 - inset_x
            if top > bottom or left > right:
                break
            cells = []
            for c in range(left + 1, right):
                cells.append((top, c, "─"))
            for r in range(top + 1, bottom):
                cells.append((r, right, "│"))
            if bottom > top:
                for c in range(right - 1, left, -1):
                    cells.append((bottom, c, "─"))
            if right > left:
                for r in range(bottom - 1, top, -1):
                    cells.append((r, left, "│"))
            if top == bottom and left == right:
                cells.append((top, left, "•"))
            elif top == bottom:
                for c in range(left, right + 1):
                    cells.append((top, c, "─"))
            elif left == right:
                for r in range(top, bottom + 1):
                    cells.append((r, left, "│"))
            else:
                cells.extend([
                    (top, left, "┌"),
                    (top, right, "┐"),
                    (bottom, left, "└"),
                    (bottom, right, "┘"),
                ])
            layers.append(cells)
            inset_y += 1
            inset_x += step_x
        return layers

    def _build_boxes_layers(rows: int, width: int):
        return _build_nested_box_layers(rows, width, side_border_width=1)

    def _build_tunnel_layers(rows: int, width: int):
        return _build_nested_box_layers(rows, width, side_border_width=2)

    def _ensure_boxes(area: dict, rows: int, width: int):
        sig = (rows, width)
        if area["boxes_sig"] == sig:
            return
        area["boxes_sig"] = sig
        area["boxes_layers"] = _build_boxes_layers(rows, width)

    def _update_boxes(area: dict, rows: int, width: int):
        _ensure_boxes(area, rows, width)

    def _ensure_tunnel(area: dict, rows: int, width: int):
        sig = (rows, width)
        if area["tunnel_sig"] == sig:
            return
        area["tunnel_sig"] = sig
        area["tunnel_layers"] = _build_tunnel_layers(rows, width)

    def _repaint_nested_layers(layers, area: dict, rows: int, y: int, x: int, width: int, attr_for_band=None):
        blank = " " * width
        for r in range(rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
            except curses.error:
                pass
        if not layers:
            return
        cadence = 4
        cycle_step = area["tick"] // cadence
        phase = cycle_step % cadence
        for inner_offset, layer in enumerate(reversed(layers)):
            if (inner_offset - phase) % cadence != 0:
                continue
            band_idx = (inner_offset - cycle_step) // cadence
            attr = attr_for_band(band_idx) if attr_for_band is not None else (curses.color_pair(6) | curses.A_BOLD)
            for rr, cc, ch in layer:
                if 0 <= rr < rows and 0 <= cc < width:
                    try:
                        stdscr.addch(y + rr, x + cc, ch, attr)
                    except curses.error:
                        pass

    def _repaint_boxes(area: dict, rows: int, y: int, x: int, width: int):
        _ensure_boxes(area, rows, width)
        _repaint_nested_layers(area.get("boxes_layers") or [], area, rows, y, x, width)

    def _ensure_sweep(area: dict, rows: int, width: int):
        cells = area["sweep_cells"]
        while len(cells) < rows:
            cells.append([(" ", 1)] * width)
        if len(cells) > rows:
            del cells[rows:]
        for r in range(rows):
            row = cells[r]
            if len(row) < width:
                row.extend([(" ", 1)] * (width - len(row)))
            elif len(row) > width:
                del row[width:]
        if area["tick"] == 0:
            palette = [2, 3, 6, 7]
            for r in range(rows):
                for c in range(width):
                    if random.random() < 0.02:
                        cells[r][c] = (random.choice(SWEEP_SYMBOLS), random.choice(palette))

    def _update_sweep(area: dict, rows: int, width: int, role: str):
        _ensure_sweep(area, rows, width)
        cells = area["sweep_cells"]
        def _drop_symbol(base_cp, spawn_prob: float, allow_red=False):
            if random.random() >= spawn_prob:
                return (" ", 1)
            cp = random.choice(base_cp) if isinstance(base_cp, (list, tuple)) else base_cp
            if allow_red and random.randint(1, 50) == 1:
                cp = 5
            return (random.choice(SWEEP_SYMBOLS), cp)
        if role == "main":
            span = max(1, width)
            head_max = max(0, span - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(span, pos + 3))}
            if area["sweep_dir"] > 0:
                tail_cols = [pos - 2, pos - 1]
            else:
                tail_cols = [pos + 3, pos + 4]
            wake_cp = 4 if area["sweep_dir"] > 0 else [2, 3, 6, 7]
            spawn_prob = 0.01 if area["sweep_dir"] > 0 else 0.02
            for r in range(rows):
                for c in head_cols:
                    cells[r][c] = (" ", 1)
                for c in tail_cols:
                    if 0 <= c < span:
                        cells[r][c] = (" ", 1)
                        cells[r][c] = _drop_symbol(wake_cp, spawn_prob, allow_red=False)
            next_pos = pos + area["sweep_dir"]
            if next_pos < 0 or next_pos > head_max:
                area["sweep_dir"] *= -1
                next_pos = max(0, min(head_max, pos + area["sweep_dir"]))
            area["sweep_pos"] = next_pos
        else:
            span = max(1, rows)
            pos = max(0, min(span - 1, area["sweep_pos"]))
            wake_cp = 4 if area["sweep_dir"] > 0 else [2, 3, 6, 7]
            spawn_prob = 0.01 if area["sweep_dir"] > 0 else 0.02
            for c in range(width):
                cells[pos][c] = (" ", 1)
            tail_rows = [r for r in range(pos - 2 * area["sweep_dir"], pos, area["sweep_dir"])]
            for wake_row in tail_rows:
                if 0 <= wake_row < span:
                    for c in range(width):
                        cells[wake_row][c] = _drop_symbol(wake_cp, spawn_prob, allow_red=False)
            next_pos = pos + area["sweep_dir"]
            if next_pos < 0 or next_pos >= span:
                area["sweep_dir"] *= -1
                next_pos = max(0, min(span - 1, pos + area["sweep_dir"]))
            area["sweep_pos"] = next_pos

    def _repaint_sweep(area: dict, nrows: int, y: int, x: int, width: int, role: str):
        _ensure_sweep(area, nrows, width)
        sweep_attr = curses.color_pair(1)
        trail_attr = curses.color_pair(1) | curses.A_DIM
        if role == "main":
            head_max = max(0, width - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(width, pos + 3))}
            if area["sweep_dir"] > 0:
                tail_cols = {c for c in [pos - 2, pos - 1] if 0 <= c < width}
            else:
                tail_cols = {c for c in [pos + 3, pos + 4] if 0 <= c < width}
            for r in range(nrows):
                for c in range(width):
                    if c in head_cols:
                        ch, attr = "█", sweep_attr
                    elif c in tail_cols:
                        ch, attr = "█", trail_attr
                    else:
                        sym, cp = area["sweep_cells"][r][c]
                        ch, attr = (sym, curses.color_pair(cp) | curses.A_BOLD) if sym != " " else (" ", curses.color_pair(1))
                    try:
                        stdscr.addch(y + r, x + c, ch, attr)
                    except curses.error:
                        pass
        else:
            pos = max(0, min(nrows - 1, area["sweep_pos"]))
            tail_rows = {r for r in range(pos - 2 * area["sweep_dir"], pos, area["sweep_dir"]) if 0 <= r < nrows}
            for r in range(nrows):
                for c in range(width):
                    if r == pos:
                        ch, attr = "█", sweep_attr
                    elif r in tail_rows:
                        ch, attr = "█", trail_attr
                    else:
                        sym, cp = area["sweep_cells"][r][c]
                        ch, attr = (sym, curses.color_pair(cp) | curses.A_BOLD) if sym != " " else (" ", curses.color_pair(1))
                    try:
                        stdscr.addch(y + r, x + c, ch, attr)
                    except curses.error:
                        pass

    def _update_tunnel(area: dict, rows: int, width: int):
        _ensure_tunnel(area, rows, width)

    def _repaint_tunnel(area: dict, rows: int, y: int, x: int, width: int):
        _ensure_tunnel(area, rows, width)
        tunnel_attrs = [
            curses.color_pair(5) | curses.A_BOLD,
            curses.color_pair(4) | curses.A_BOLD,
            curses.color_pair(6) | curses.A_BOLD,
            curses.color_pair(3) | curses.A_BOLD,
            curses.color_pair(8) | curses.A_BOLD,
            curses.color_pair(9) | curses.A_BOLD,
            curses.color_pair(2) | curses.A_BOLD,
        ]
        _repaint_nested_layers(
            area.get("tunnel_layers") or [],
            area,
            rows,
            y,
            x,
            width,
            attr_for_band=lambda band_idx: tunnel_attrs[band_idx % len(tunnel_attrs)],
        )

    def _gauge_parse_num(s: str):
        try:
            return float(s.replace(",", "").replace("+", ""))
        except (ValueError, TypeError):
            return None

    def _readout_use_title(rows: int) -> bool:
        return rows >= 6

    def _readout_line_capacity(rows: int) -> int:
        reserved = 1 if _readout_use_title(rows) else 0
        return min(10, max(1, rows - reserved))

    def _readout_filler_rows(style_name: str):
        fillers = {
            "hacker": [
                ("LAT", lambda: f"{random.uniform(2.0, 85.0):5.1f}", "ms"),
                ("DISC", lambda: f"{random.randint(1, 64):2d}", "nodes"),
                ("TLS", lambda: f"{random.uniform(0.0, 1.0):.3f}", "err"),
                ("AUTH", lambda: random.choice(["PASS", "PASS", "WARN", "HOLD"]), ""),
                ("I/O", lambda: f"{random.randint(10, 999):3d}", "MB/s"),
            ],
            "science": [
                ("MAG", lambda: f"{random.uniform(0.1, 8.0):4.2f}", "T"),
                ("PHASE", lambda: f"{random.uniform(0.0, 360.0):5.1f}", "deg"),
                ("VAC", lambda: f"{random.uniform(1e-9, 1e-3):.1e}", "mbar"),
                ("SYNC", lambda: f"{random.uniform(97.0, 100.0):4.1f}", "%"),
                ("BEAM", lambda: random.choice(["LOCK", "LOCK", "TUNE", "DRFT"]), ""),
            ],
            "medicine": [
                ("RESP", lambda: f"{random.randint(8, 24):2d}", "rpm"),
                ("ETCO2", lambda: f"{random.uniform(28.0, 48.0):4.1f}", "mmHg"),
                ("MAP", lambda: f"{random.randint(60, 110):3d}", "mmHg"),
                ("INFUSN", lambda: f"{random.uniform(1.0, 40.0):4.1f}", "mL/h"),
                ("RHYTHM", lambda: random.choice(["NSR", "NSR", "PVC", "AFIB"]), ""),
            ],
            "pharmacy": [
                ("QUEUE", lambda: f"{random.randint(0, 240):3d}", "rx"),
                ("FILL", lambda: f"{random.uniform(10.0, 98.0):4.1f}", "%"),
                ("DUR", lambda: f"{random.randint(0, 24):2d}", "flag"),
                ("READY", lambda: f"{random.randint(0, 180):3d}", "bags"),
                ("COB", lambda: random.choice(["PAID", "PAID", "REVW", "HOLD"]), ""),
            ],
            "finance": [
                ("BID", lambda: f"{random.uniform(100.0, 9999.0):,.2f}", ""),
                ("ASK", lambda: f"{random.uniform(100.0, 9999.0):,.2f}", ""),
                ("SPD", lambda: f"{random.uniform(0.01, 1.50):.2f}", ""),
                ("BETA", lambda: f"{random.uniform(0.50, 2.50):.2f}", ""),
                ("RSI", lambda: f"{random.uniform(5.0, 95.0):4.1f}", ""),
            ],
            "space": [
                ("ROLL", lambda: f"{random.uniform(-180.0, 180.0):6.1f}", "deg"),
                ("PITCH", lambda: f"{random.uniform(-90.0, 90.0):5.1f}", "deg"),
                ("O2", lambda: f"{random.uniform(20.0, 100.0):4.1f}", "%"),
                ("HULL", lambda: f"{random.uniform(65.0, 100.0):4.1f}", "%"),
                ("COMMS", lambda: random.choice(["CLEAR", "CLEAR", "FADE", "LOSS"]), ""),
            ],
            "military": [
                ("IFF", lambda: random.choice(["BLUE", "BLUE", "UNK", "HOST"]), ""),
                ("RANGE", lambda: f"{random.uniform(0.4, 120.0):5.1f}", "km"),
                ("LOCK", lambda: f"{random.randint(0, 12):2d}", "trk"),
                ("JAM", lambda: f"{random.uniform(0.0, 100.0):4.1f}", "%"),
                ("RCS", lambda: f"{random.uniform(0.1, 12.0):4.1f}", "m2"),
            ],
            "navigation": [
                ("HEAD", lambda: f"{random.randint(0, 359):3d}", "deg"),
                ("ALT", lambda: f"{random.randint(0, 4200):4d}", "m"),
                ("LANE", lambda: f"{random.randint(1, 5):1d}", ""),
                ("DRIFT", lambda: f"{random.uniform(0.0, 2.5):3.1f}", "m"),
                ("TURN", lambda: random.choice(["NONE", "LEFT", "RIGHT", "HOLD"]), ""),
            ],
            "spaceteam": [
                ("WUMBLE", lambda: f"{random.randint(0, 88):2d}", "flux"),
                ("BLASTR", lambda: f"{random.uniform(0.0, 9.9):3.1f}", "zorg"),
                ("TWIST", lambda: f"{random.randint(0, 360):3d}", "deg"),
                ("GRONK", lambda: random.choice(["OK", "BZZT", "???", "YEP"]), ""),
                ("NOISE", lambda: f"{random.uniform(10.0, 99.0):4.1f}", "spl"),
            ],
        }
        default_rows = [
            ("SIGMA", lambda: f"{random.uniform(0.0, 99.9):4.1f}", ""),
            ("DELTA", lambda: f"{random.uniform(-9.9, 9.9):+4.1f}", ""),
            ("STATE", lambda: random.choice(["OK", "OK", "WARN", "HOLD"]), ""),
            ("INDEX", lambda: f"{random.randint(0, 999):3d}", ""),
            ("DRIFT", lambda: f"{random.uniform(0.0, 9.9):3.1f}", ""),
        ]
        return fillers.get(style_name, default_rows)

    def _next_prime_value(area: dict) -> str:
        idx = area["gauge_prime_idx"] % len(prime_values)
        value = prime_values[idx]
        area["gauge_prime_idx"] = (idx + 1) % len(prime_values)
        return value

    def _refresh_readout_rows(area: dict, rows: int):
        target_lines = _readout_line_capacity(rows)
        if target_lines <= 1:
            area["gauge_reads"] = [("COUNT", lambda area=area: str(area["gauge_count"]), "")]
            return
        fillers = _readout_filler_rows(_area_style(area))
        data_lines = list(area["gauge_base_reads"][:max(0, target_lines - 2)])
        fill_idx = 0
        while len(data_lines) < max(0, target_lines - 2):
            data_lines.append(fillers[fill_idx % len(fillers)])
            fill_idx += 1
        data_lines.append(("PRIME", lambda area=area: _next_prime_value(area), ""))
        data_lines.append(("COUNT", lambda area=area: str(area["gauge_count"]), ""))
        area["gauge_reads"] = data_lines

    def _sync_gauge_vectors(area: dict):
        count = len(area["gauge_reads"])
        if len(area["gauge_hist"]) != count:
            area["gauge_hist"] = [[0.0] * 4 for _ in area["gauge_reads"]]
        if len(area["gauge_arrows"]) != count:
            area["gauge_arrows"] = ["─" for _ in area["gauge_reads"]]
        if len(area["gauge_last_values"]) != count:
            vals = [val_fn() for _, val_fn, _ in area["gauge_reads"]]
            area["gauge_last_values"] = vals
            for i, val_str in enumerate(vals):
                num = _gauge_parse_num(val_str)
                if num is not None:
                    area["gauge_hist"][i] = [num]

    def _ensure_gauges(area: dict, rows: int, width: int, role: str, mode: str):
        cfg = get_gauge_config(_area_style(area))
        area["gauge_title"], area["gauge_signal"], area["gauge_base_reads"], area["gauge_scroll_title"] = cfg
        area["gauge_reads"] = area["gauge_base_reads"]
        if mode == "readouts":
            _refresh_readout_rows(area, rows)
        if not area["gauge_spark"]:
            area["gauge_spark"] = [0.5]
            for _ in range(max(7, width - 1)):
                area["gauge_spark"].append(_next_gauge_spark(area))
        had_last_values = bool(area["gauge_last_values"])
        _sync_gauge_vectors(area)
        if not had_last_values:
            if _area_style(area) == "pharmacy" and role == "sidebar":
                area["gauge_next_reads_at"] = time.time() + 0.80
            elif role == "sidebar":
                area["gauge_next_reads_at"] = time.time() + 0.45
            else:
                area["gauge_next_reads_at"] = time.time() + 0.30
        while len(area["gauge_feed"]) < rows:
            area["gauge_feed"].append(
                _new_area_text_entry("text", width, {"text": area["feed_text"], "style_override": _area_style(area)}, role)
            )
        while len(area["gauge_feed"]) > rows:
            area["gauge_feed"].pop(0)

    def _next_gauge_spark(area: dict):
        if not callable(area["gauge_signal"]):
            area["gauge_title"], area["gauge_signal"], area["gauge_reads"], area["gauge_scroll_title"] = get_gauge_config(_area_style(area))
        _sync_gauge_vectors(area)
        prev = area["gauge_spark"][-1] if area["gauge_spark"] else 0.5
        raw = area["gauge_signal"]()
        target = 0.14 + raw * 0.72
        drift = area["gauge_drift"]
        drift += (target - prev) * 0.30
        drift += random.gauss(0, 0.04)
        drift *= 0.82
        drift -= (prev - 0.5) * 0.03
        floor_bias = max(0.0, (0.24 - prev) / 0.24)
        if floor_bias > 0.0:
            if drift < 0:
                drift *= max(0.20, 1.0 - floor_bias * 0.85)
            if random.random() < floor_bias:
                drift += random.uniform(0.02, 0.09) * floor_bias
        if random.random() < 0.035:
            drift += random.choice([-1, 1]) * random.uniform(0.06, 0.16)
        drift = max(-0.12, min(0.12, drift))
        nxt = prev + drift
        if nxt < 0.01:
            nxt = 0.01 + (0.01 - nxt) * 0.40
            drift = abs(drift) * 0.62 + random.uniform(0.01, 0.04)
        elif nxt > 0.99:
            nxt = 0.99 - (nxt - 0.99) * 0.40
            drift = -abs(drift) * 0.62 - random.uniform(0.01, 0.04)
        area["gauge_drift"] = drift
        return max(0.01, min(0.99, nxt))

    def _gauge_rows(area: dict, rows: int):
        spark_rows = max(4, rows * 30 // 100)
        reads_rows = max(4, len(area["gauge_reads"]) + 2)
        div1 = spark_rows
        reads_start = div1 + 1
        div2 = reads_start + reads_rows
        feed_start = div2 + 1
        return spark_rows, div1, reads_start, div2, feed_start

    def _draw_divider(y: int, row: int, x: int, width: int, label, cp=3):
        inner = f"[ {label} ]"
        dashes = max(0, width - len(inner) - 2)
        left = dashes // 2
        right = dashes - left
        txt = "─" * left + " " + inner + " " + "─" * right
        safe_w = _safe_row_width(y, row, x, width)
        if safe_w <= 0:
            return
        try:
            stdscr.addnstr(y + row, x, txt[:safe_w].ljust(safe_w), safe_w, curses.color_pair(cp) | curses.A_DIM)
        except curses.error:
            pass

    def _repaint_gauges(area: dict, rows: int, y: int, x: int, width: int):
        spark_rows, div1, reads_start, div2, feed_start = _gauge_rows(area, rows)
        spark_chars = " ▁▂▃▄▅▆▇█"
        vals = area["gauge_spark"][-width:] if len(area["gauge_spark"]) >= width else area["gauge_spark"]
        for r in range(spark_rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            chars = []
            for v in vals:
                bar_h = int(v * spark_rows)
                row_from_bottom = spark_rows - 1 - r
                if bar_h == 0:
                    chars.append(" ")
                elif row_from_bottom < bar_h - 1:
                    chars.append("█")
                elif row_from_bottom == bar_h - 1:
                    frac = (v * spark_rows) - int(v * spark_rows)
                    chars.append(spark_chars[max(1, int(frac * 8))])
                else:
                    chars.append(" ")
            cp = 3 if r / max(1, spark_rows - 1) < 0.25 else (5 if r / max(1, spark_rows - 1) > 0.75 else 6)
            try:
                stdscr.addnstr(y + r, x, "".join(chars)[:safe_w].ljust(safe_w), safe_w, curses.color_pair(cp))
            except curses.error:
                pass
        _draw_divider(y, div1, x, width, area["gauge_title"])
        for i, (label, val_fn, unit) in enumerate(area["gauge_reads"]):
            row = reads_start + i
            if row >= min(rows, div2):
                break
            if i < len(area["gauge_last_values"]):
                val_str = area["gauge_last_values"][i]
            else:
                val_str = val_fn()
            arrow = area["gauge_arrows"][i] if i < len(area["gauge_arrows"]) else " "
            line = f" {label[:10]:<10s} {val_str:>8s} {unit[:8]:<8s} {arrow}"
            safe_w = _safe_row_width(y, row, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + row, x, line[:safe_w].ljust(safe_w), safe_w, curses.color_pair(2))
            except curses.error:
                pass
        if div2 < rows:
            _draw_divider(y, div2, x, width, area["gauge_scroll_title"])
        blank = " " * width
        for r in range(feed_start, rows):
            idx = r - feed_start
            if idx >= len(area["gauge_feed"]):
                break
            txt, attr, vis = area["gauge_feed"][idx]
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
            except curses.error:
                pass
            if not txt:
                continue
            try:
                draw_w = max(0, min(vis, safe_w))
                if draw_w:
                    stdscr.addnstr(y + r, x, txt[:draw_w].ljust(draw_w), draw_w, attr)
            except curses.error:
                pass

    def _repaint_sparkline(area: dict, rows: int, y: int, x: int, width: int):
        spark_rows = rows
        spark_chars = " ▁▂▃▄▅▆▇█"
        vals = area["gauge_spark"][-width:] if len(area["gauge_spark"]) >= width else area["gauge_spark"]
        for r in range(spark_rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            chars = []
            for v in vals:
                bar_h = int(v * spark_rows)
                row_from_bottom = spark_rows - 1 - r
                if bar_h == 0:
                    chars.append(" ")
                elif row_from_bottom < bar_h - 1:
                    chars.append("█")
                elif row_from_bottom == bar_h - 1:
                    frac = (v * spark_rows) - int(v * spark_rows)
                    chars.append(spark_chars[max(1, int(frac * 8))])
                else:
                    chars.append(" ")
            cp = 3 if r / max(1, spark_rows - 1) < 0.25 else (5 if r / max(1, spark_rows - 1) > 0.75 else 6)
            try:
                stdscr.addnstr(y + r, x, "".join(chars)[:safe_w].ljust(safe_w), safe_w, curses.color_pair(cp))
            except curses.error:
                pass

    def _repaint_readouts(area: dict, rows: int, y: int, x: int, width: int):
        blank = " " * width
        title = area["gauge_title"]
        use_title = _readout_use_title(rows)
        data_rows = min(len(area["gauge_reads"]), max(1, rows - (1 if use_title else 0)))
        content_rows = min(rows, data_rows + (1 if use_title else 0))
        top_pad = max(0, (rows - content_rows) // 2)
        start_row = top_pad + (1 if use_title else 0)
        block_width = min(width, 29)
        block_pad = max(0, (width - block_width) // 2)
        for r in range(rows):
            try:
                stdscr.addnstr(y + r, x, blank, width, curses.color_pair(1))
            except curses.error:
                pass
        if use_title:
            _draw_divider(y, top_pad, x, width, title)
        for i, (label, val_fn, unit) in enumerate(area["gauge_reads"]):
            row = start_row + i
            if row >= rows:
                break
            if label == "COUNT":
                val_str = str(area["gauge_count"])
            elif label == "PRIME":
                val_str = area["gauge_last_values"][i] if i < len(area["gauge_last_values"]) else val_fn()
            else:
                val_str = area["gauge_last_values"][i] if i < len(area["gauge_last_values"]) else val_fn()
            arrow = " " if label in {"COUNT", "PRIME"} else (area["gauge_arrows"][i] if i < len(area["gauge_arrows"]) else " ")
            line = (" " * block_pad) + f"{label[:10]:<10s} {val_str:>8s} {unit[:8]:<8s} {arrow}"
            safe_w = _safe_row_width(y, row, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + row, x, line[:safe_w].ljust(safe_w), safe_w, curses.color_pair(2))
            except curses.error:
                pass

    def _image_message(rows: int, width: int, text: str):
        lines = ["" for _ in range(rows)]
        msg = text[:width]
        if rows > 0:
            lines[rows // 2] = msg.center(width)
        return lines

    def _jp2a_background(path: str) -> str:
        try:
            with Image.open(path) as img:
                img = img.convert("RGBA")
                sample_w = max(1, min(8, img.width))
                sample_h = max(1, min(8, img.height))
                total = 0.0
                count = 0
                for y in range(sample_h):
                    for x in range(sample_w):
                        r, g, b, a = img.getpixel((x, y))
                        alpha = a / 255.0
                        # Blend transparency against black, which matches the curses canvas.
                        r *= alpha
                        g *= alpha
                        b *= alpha
                        total += 0.2126 * r + 0.7152 * g + 0.0722 * b
                        count += 1
        except Exception:
            return "dark"
        avg = total / max(1, count)
        return "light" if avg >= 128 else "dark"

    def _fit_ascii_to_panel(lines, width: int, rows: int):
        lines = [line.replace("\t", "    ").rstrip("\n") for line in lines]
        if not lines:
            return [" " * width for _ in range(rows)]

        src_h = len(lines)
        if src_h > rows:
            top = (src_h - rows) // 2
            lines = lines[top:top + rows]
        elif src_h < rows:
            pad_top = (rows - src_h) // 2
            pad_bot = rows - src_h - pad_top
            lines = ([""] * pad_top) + lines + ([""] * pad_bot)

        fitted = []
        for line in lines[:rows]:
            src_w = len(line)
            if src_w > width:
                left = (src_w - width) // 2
                fitted.append(line[left:left + width])
            else:
                pad_left = (width - src_w) // 2
                pad_right = width - src_w - pad_left
                fitted.append((" " * pad_left) + line + (" " * pad_right))

        if len(fitted) < rows:
            fitted.extend([" " * width for _ in range(rows - len(fitted))])
        return [line[:width].ljust(width) for line in fitted]

    def _render_image(path: str, width: int, rows: int, invert: bool = False):
        background = _jp2a_background(path)
        key = (path, width, rows, invert, background)
        cached = jp2a_cache.get(key)
        if cached is not None:
            return cached

        def _run_jp2a(dim_flag: str):
            cmd = ["jp2a", dim_flag, f"--background={background}"]
            if invert:
                cmd.append("--invert")
            cmd.append(path)
            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            return proc.stdout.replace("\r", "").splitlines()

        try:
            lines_w = _run_jp2a(f"--width={width}")
            if len(lines_w) >= rows:
                lines = lines_w
            else:
                lines_h = _run_jp2a(f"--height={rows}")
                lines = lines_h if lines_h else lines_w
        except FileNotFoundError:
            lines = _image_message(rows, width, "jp2a not found")
        except subprocess.CalledProcessError as exc:
            err = exc.stderr.strip().splitlines()
            detail = err[0] if err else "jp2a failed"
            lines = _image_message(rows, width, detail)
        lines = _fit_ascii_to_panel(lines, width, rows)
        jp2a_cache[key] = lines
        return lines

    def _ensure_image(area: dict, rows: int, width: int):
        area_image_paths = area.get("image_paths") or IMAGE_PATHS
        sig = (tuple(area_image_paths), rows, width)
        if area["image_sig"] == sig:
            return
        if not area_image_paths:
            frames = []
        elif len(area_image_paths) == 1:
            frames = [
                _render_image(area_image_paths[0], width, rows, invert=False),
                _render_image(area_image_paths[0], width, rows, invert=True),
            ]
        else:
            frames = [_render_image(path, width, rows, invert=False) for path in area_image_paths]
        area["image_sig"] = sig
        area["image_frames"] = frames
        area["image_from"] = 0
        area["image_to"] = 1 % len(frames) if frames else 0
        area["image_wipe_row"] = -1
        area["image_colour_idx"] = 0

    def _update_image(area: dict, rows: int, width: int):
        _ensure_image(area, rows, width)
        area["image_wipe_row"] += 1
        if area["image_wipe_row"] > rows:
            frame_count = len(area["image_frames"])
            area["image_from"] = area["image_to"]
            area["image_to"] = (area["image_to"] + 1) % frame_count if frame_count else 0
            area["image_wipe_row"] = -1
            area["image_colour_idx"] = (area["image_colour_idx"] + 1) % len(IMAGE_COLOUR_CYCLE)

    def _life_hash(cells):
        return tuple("".join("1" if cell else "0" for cell in row) for row in cells)

    def _seed_life(area: dict, rows: int, width: int, sig=None):
        density = 0.22 if rows * width <= 1200 else 0.16
        cells = []
        ages = []
        for _ in range(rows):
            row = []
            age_row = []
            for _ in range(width):
                alive = 1 if random.random() < density else 0
                row.append(alive)
                age_row.append(alive)
            cells.append(row)
            ages.append(age_row)
        area["life_sig"] = sig if sig is not None else (rows, width)
        area["life_cells"] = cells
        area["life_ages"] = ages
        area["life_iteration"] = 0
        area["life_hashes"] = collections.deque([_life_hash(cells)], maxlen=8)

    def _ensure_life(area: dict, rows: int, width: int):
        sig = (rows, width)
        if area["life_sig"] == sig:
            return
        _seed_life(area, rows, width, sig=sig)

    def _update_life(area: dict, rows: int, width: int):
        _ensure_life(area, rows, width)
        src = area["life_cells"]
        src_ages = area["life_ages"]
        nxt = [[0] * width for _ in range(rows)]
        nxt_ages = [[0] * width for _ in range(rows)]
        live_count = 0
        births = 0
        deaths = 0
        for r in range(rows):
            for c in range(width):
                neighbours = 0
                for dr in (-1, 0, 1):
                    rr = r + dr
                    if rr < 0 or rr >= rows:
                        continue
                    for dc in (-1, 0, 1):
                        cc = c + dc
                        if dc == 0 and dr == 0:
                            continue
                        if 0 <= cc < width:
                            neighbours += src[rr][cc]
                alive = src[r][c] == 1
                if alive and neighbours in (2, 3):
                    nxt[r][c] = 1
                    nxt_ages[r][c] = src_ages[r][c] + 1
                elif (not alive) and neighbours == 3:
                    nxt[r][c] = 1
                    nxt_ages[r][c] = 1
                    births += 1
                elif alive:
                    deaths += 1
                if nxt[r][c]:
                    live_count += 1
        area["life_iteration"] += 1
        next_hash = _life_hash(nxt)
        if (area["life_iteration"] >= LIFE_MAX_ITERATIONS
                or births == 0 or deaths == 0
                or next_hash in area["life_hashes"]):
            _seed_life(area, rows, width)
            return
        area["life_cells"] = nxt
        area["life_ages"] = nxt_ages
        area["life_hashes"].append(next_hash)

    def _repaint_life(area: dict, rows: int, y: int, x: int, width: int):
        _ensure_life(area, rows, width)
        dead_attr = curses.color_pair(1)
        cells = area["life_cells"]
        ages = area["life_ages"]
        for r in range(rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            for c in range(safe_w):
                if cells[r][c]:
                    age = ages[r][c]
                    if age <= 1:
                        attr = curses.color_pair(9) | curses.A_BOLD
                    elif age <= 3:
                        attr = curses.color_pair(3) | curses.A_BOLD
                    elif age <= 6:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(7) | curses.A_DIM
                    ch = "◉"
                else:
                    ch = " "
                    attr = dead_attr
                try:
                    stdscr.addch(y + r, x + c, ch, attr)
                except curses.error:
                    pass

    def _repaint_image(area: dict, rows: int, y: int, x: int, width: int):
        _ensure_image(area, rows, width)
        if not area["image_frames"]:
            return
        src = area["image_frames"][area["image_from"]]
        dst = area["image_frames"][area["image_to"]]
        wipe_row = area["image_wipe_row"]
        src_cp = IMAGE_COLOUR_CYCLE[area["image_colour_idx"] % len(IMAGE_COLOUR_CYCLE)]
        dst_cp = IMAGE_COLOUR_CYCLE[(area["image_colour_idx"] + 1) % len(IMAGE_COLOUR_CYCLE)]
        src_attr = curses.color_pair(src_cp)
        dst_attr = curses.color_pair(dst_cp)
        bar_attr = curses.color_pair(1) | curses.A_DIM
        for r in range(rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            if 0 <= wipe_row < rows and r == wipe_row:
                line = "▄" * width
                attr = bar_attr
            elif wipe_row - len(IMAGE_TRAIL_ATTRS) <= r < wipe_row:
                line = dst[r]
                attr = IMAGE_TRAIL_ATTRS[wipe_row - r - 1]
            elif r < wipe_row:
                line = dst[r]
                attr = dst_attr
            else:
                line = src[r]
                attr = src_attr
            try:
                stdscr.addnstr(y + r, x, line[:safe_w], safe_w, attr)
            except curses.error:
                pass

    def _repaint_unavailable(area: dict, rows: int, y: int, x: int, width: int):
        lines = _image_message(rows, width, area.get("unavailable_message") or "")
        blank = " " * width
        for r in range(rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
                line = lines[r][:safe_w].ljust(safe_w)
                attr = curses.color_pair(4) | curses.A_BOLD if line.strip() else curses.color_pair(1)
                stdscr.addnstr(y + r, x, line, safe_w, attr)
            except curses.error:
                pass

    def _repaint_static_lines(area: dict, rows: int, y: int, x: int, width: int):
        blank = " " * width
        lines = area.get("static_lines") or []
        top = 1 if rows > 2 else 0
        for r in range(rows):
            safe_w = _safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                stdscr.addnstr(y + r, x, blank, safe_w, curses.color_pair(1))
                line_idx = r - top
                if 0 <= line_idx < len(lines):
                    line = lines[line_idx][:safe_w].ljust(safe_w)
                    attr = curses.color_pair(2) if not line.endswith(":") else curses.color_pair(2) | curses.A_BOLD
                    stdscr.addnstr(y + r, x, line, safe_w, attr)
            except curses.error:
                pass

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

    def _make_area(mode, style_name: str | None = None):
        area = _make_area_state(style_name)
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
        if mode in {"clock", "blocks", "sweep", "tunnel", "boxes"}:
            return delay / 1.5
        return delay

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
        elif mode == "boxes":
            _ensure_boxes(area, rows, width)
        elif mode == "sweep":
            _ensure_sweep(area, rows, width)
        elif mode == "tunnel":
            return
        elif mode in {"gauges", "sparkline", "readouts"}:
            _ensure_gauges(area, rows, width, role, mode)
            if area.get("title"):
                if mode == "sparkline":
                    area["gauge_title"] = area["title"]
                elif mode == "readouts":
                    area["gauge_title"] = area["title"]
                else:
                    area["gauge_scroll_title"] = area["title"]
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
        elif mode == "boxes":
            _update_boxes(area, rows, width)
        elif mode == "sweep":
            _update_sweep(area, rows, width, role)
        elif mode == "tunnel":
            _update_tunnel(area, rows, width)
        elif mode == "oscilloscope":
            _update_scope(area, width)
        elif mode in {"gauges", "sparkline", "readouts"}:
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
                if _area_style(area) == "pharmacy" and role == "sidebar":
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
                    _new_area_text_entry("text", width, {"text": area["feed_text"], "style_override": _area_style(area)}, role)
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
        elif mode == "boxes":
            _repaint_boxes(area, rows, y, x, width)
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
            if area.get("static_lines"):
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
        style_val = STYLE_ARG if (MAIN_MODE in STYLE_VOCAB_MODES or side_mode in STYLE_VOCAB_MODES) else "-"
        line1 = " demo "
        line2 = f" --main {MAIN_MODE} "
        if SIDEBAR_MODE == "cycle" and side_mode != "none":
            side_label = f"cycle({side_mode})"
        else:
            side_label = side_mode if side_mode != "none" else "(none)"
        line3 = f" --sidebar {side_label} "
        line4 = f" --style {style_val} "
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
        if not _showcase_state["active"] or not CONFIG_STYLE:
            return
        header_lines = CONFIG_STYLE.get("showcase_header_lines") or []
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
        global CONFIG_STYLE, STYLE_ARG
        nonlocal area_specs, area_states
        scenes = _showcase_state.get("scenes", [])
        if not scenes:
            return
        next_idx %= len(scenes)
        _showcase_state["idx"] = next_idx
        _showcase_state["done"] = False
        CONFIG_STYLE = scenes[next_idx]
        STYLE_ARG = CONFIG_STYLE.get("vocab", STYLE_ARG)
        GEN_POOL[:], RCOL_POOL[:] = _build_pools(STYLE_ARG)
        area_specs = _current_area_specs(rows, cols)
        area_states = _sync_areas(area_specs)
        _sync_cycle_start_modes(area_specs, area_states, time.time())
        for spec in area_specs:
            _ensure_area(area_states[spec["name"]], spec["height"], spec["width"], spec["role"])

    def _role_for_area(spec: dict) -> str:
        if spec.get("role"):
            return spec["role"]
        return "main" if spec["x"] < 0.5 else "sidebar"

    def _scaled_rect(spec: dict, rows: int, cols: int) -> dict:
        x0 = max(0, min(cols - 1, int(round(cols * spec["x"])))) if cols > 0 else 0
        y0 = max(0, min(rows - 1, int(round(rows * spec["y"])))) if rows > 0 else 0
        x1 = max(x0 + 1, min(cols, int(round(cols * (spec["x"] + spec["w"]))))) if cols > 0 else 0
        y1 = max(y0 + 1, min(rows, int(round(rows * (spec["y"] + spec["h"]))))) if rows > 0 else 0
        return {
            **spec,
            "x": x0,
            "y": y0,
            "width": max(1, x1 - x0) if cols > 0 else 0,
            "height": max(1, y1 - y0) if rows > 0 else 0,
            "role": _role_for_area(spec),
        }

    def _legacy_area_specs(cols: int):
        main_w, side_w, side_x = layout(cols)
        specs = [{
            "name": "main",
            "mode": MAIN_MODE,
            "x": 0,
            "y": 0,
            "width": main_w,
            "height": rows,
            "role": "main",
            "separator_after": side_w > 0,
        }]
        if side_w:
            specs.append({
                "name": "sidebar",
                "mode": _effective_sidebar_mode(),
                "x": side_x,
                "y": 0,
                "width": side_w,
                "height": rows,
                "role": "sidebar",
                "separator_after": False,
            })
        return specs

    def _config_area_specs(rows: int, cols: int):
        specs = []
        for area_spec in sorted(CONFIG_STYLE["areas"], key=lambda item: (item["x"], item["y"], item["name"])):
            rect = _scaled_rect(area_spec, rows, cols)
            if rect.get("vocab") is None and CONFIG_STYLE.get("vocab") is not None:
                rect["vocab"] = CONFIG_STYLE["vocab"]
            specs.append(rect)
        return specs

    def _current_area_specs(rows: int, cols: int):
        if CONFIG_STYLE and not _demo_state["active"]:
            return _config_area_specs(rows, cols)
        return _legacy_area_specs(cols)

    def _sync_areas(area_specs: list[dict]):
        synced = {}
        for spec in area_specs:
            area = area_states.get(spec["name"])
            if (area is None or area["mode"] != spec["mode"]
                    or area.get("style_override") != spec.get("vocab")):
                area = _make_area(spec["mode"], spec.get("vocab"))
                area["mode"] = spec["mode"]
                area["name"] = spec["name"]
                area["title"] = spec.get("title")
                area["label"] = spec.get("label")
                area["speed_override"] = spec.get("speed")
                area["role"] = spec["role"]
                area["style_override"] = spec.get("vocab")
                area["image_paths"] = spec.get("image_paths") or []
                area["cycle_widgets"] = spec.get("cycle_widgets") or []
                area["unavailable_message"] = spec.get("unavailable_message")
                area["static_lines"] = spec.get("static_lines") or []
                _reset_area_timing(area)
            else:
                area["title"] = spec.get("title")
                area["label"] = spec.get("label")
                area["speed_override"] = spec.get("speed")
                area["role"] = spec["role"]
                area["style_override"] = spec.get("vocab")
                area["image_paths"] = spec.get("image_paths") or []
                area["cycle_widgets"] = spec.get("cycle_widgets") or []
                area["unavailable_message"] = spec.get("unavailable_message")
                area["static_lines"] = spec.get("static_lines") or []
            synced[spec["name"]] = area
        return synced

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
        current_specs = _current_area_specs(cur_rows, cur_cols)
        main_specs = [spec for spec in current_specs if spec["role"] == "main"]
        target = main_specs[0] if main_specs else current_specs[0]
        cur_main_w = target["width"]
        base_x = target["x"]
        base_y = target["y"]
        rh = random.randint(3, min(12, max(3, cur_rows - 1)))
        cw = random.randint(8, min(40, max(8, cur_main_w - 1)))
        _glitch_rh, _glitch_cw = rh, cw
        _glitch_r0 = base_y + random.randint(0, max(0, target["height"] - rh - 1))
        _glitch_c0 = base_x + random.randint(0, max(0, cur_main_w - cw - 1))
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
                        sc = max(0, min(cur_main_w - 1, c + random.randint(-5, 5)))
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
            new_modes = _sidebar_cycle_modes_for_main(MAIN_MODE)
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
        if CONFIG_STYLE and not _demo_state["active"]:
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
            STYLE_ARG = _demo_state["scene"]["style"]
            MAIN_MODE = _demo_state["scene"]["main"]
            SIDEBAR_MODE = _demo_state["scene"]["sidebar"]
            GEN_POOL[:], RCOL_POOL[:] = _build_pools(STYLE_ARG)
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
    global LIFE_MAX_ITERATIONS, INJECT_TEXT, MAIN_MODE, _ALL_STYLES
    global STYLE_ARG, SIDEBAR_MODE, _demo_state, GLITCH_INTERVAL, CONFIG_STYLE, _showcase_state

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
    INJECT_TEXT = config["inject_text"]
    MAIN_MODE = config["main_mode"]
    _ALL_STYLES = config["styles"]
    STYLE_ARG = config["style"]
    CONFIG_STYLE = config["config_style"]
    SIDEBAR_MODE = config["sidebar_mode"]
    _demo_state = config["demo_state"]
    _showcase_state = config["widget_showcase"]
    GLITCH_INTERVAL = config["glitch_interval"]

    GEN_POOL[:], RCOL_POOL[:] = _build_pools(STYLE_ARG)
    if not _showcase_state["active"]:
        show_startup_banner(SCRIPT_NAME, config)

        for countdown in (2, 1):
            print(f"  Starting in {countdown}...", end="\r", flush=True)
            time.sleep(1)
        print(" " * 30, end="\r")

    def _is_resize_restartable(exc: Exception) -> bool:
        if isinstance(exc, curses.error):
            return True
        if not isinstance(exc, IndexError):
            return False
        tb = traceback.extract_tb(exc.__traceback__)
        for frame in tb:
            if os.path.abspath(frame.filename) != os.path.abspath(__file__):
                continue
            if frame.name in {
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
            }:
                return True
        return False

    while True:
        try:
            curses.wrapper(main)
            break
        except KeyboardInterrupt:
            break
        except Exception as exc:
            if not _is_resize_restartable(exc):
                raise
            time.sleep(0.05)
    print(f"\n[{SCRIPT_NAME}] terminated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
