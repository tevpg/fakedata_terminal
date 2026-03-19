"""Shared runtime helpers for FakeData Terminal."""

from __future__ import annotations

import collections
import math
import os
import random
import re
import traceback


PARA_THEMES = ["green"] * 60 + ["red"] * 25 + ["mixed"] * 15
BURST_SIZE = 40

HELP_TEXT_TOPICS_UNIX = [
    "bash", "sh", "ls", "find", "grep", "sed", "awk", "ps", "tar", "ssh",
    "systemd", "cron", "mount", "chmod", "chown", "printf", "make", "git",
]
HELP_TEXT_TOPICS_WIN = [
    "Get-Process", "Get-Service", "Get-ChildItem", "Get-ItemProperty",
    "Get-Command", "Get-CimClass", "Get-EventLog", "Get-NetAdapter",
    "Get-ComputerInfo", "about_Arrays", "about_Pipelines", "about_Objects",
]

COLOUR_TRIADS = {
    "red": {"dim": 88, "normal": 160, "bright": 196},
    "green": {"dim": 22, "normal": 34, "bright": 82},
    "blue": {"dim": 18, "normal": 33, "bright": 39},
    "cyan": {"dim": 23, "normal": 44, "bright": 51},
    "magenta": {"dim": 90, "normal": 165, "bright": 201},
    "yellow": {"dim": 136, "normal": 220, "bright": 226},
    "orange": {"dim": 130, "normal": 208, "bright": 214},
    "purple": {"dim": 54, "normal": 93, "bright": 141},
    "white": {"dim": 245, "normal": 252, "bright": 15},
}

COLOUR_SINGLES = {
    "black": 0,
}

COLOUR_ALIASES = {
    "grey": "dim-white",
    "gray": "dim-white",
    "pink": "bright-magenta",
    "amber": "dim-orange",
    "light green": "bright-green",
    "bright green": "bright-green",
    "brightgreen": "bright-green",
    "lime": "bright-green",
    "light blue": "bright-blue",
    "lightblue": "bright-blue",
    "brown": "dim-orange",
}

COLOUR_CHOICES = [
    "black",
    "dim-red", "red", "bright-red",
    "dim-orange", "orange", "bright-orange",
    "dim-yellow", "yellow", "bright-yellow",
    "dim-green", "green", "bright-green",
    "dim-blue", "blue", "bright-blue",
    "dim-cyan", "cyan", "bright-cyan",
    "dim-magenta", "magenta", "bright-magenta",
    "dim-purple", "purple", "bright-purple",
    "dim-white", "white", "bright-white",
    "grey", "gray", "pink", "amber",
    "multi",
    "multi-all",
    "multi-dim",
    "multi-normal",
    "multi-bright",
]

COLOUR_RAINBOW_ORDER = [
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "purple",
    "magenta",
    "white",
]

COLOUR_NORMAL_BRIGHTNESS_ORDER = [
    "white",
    "yellow",
    "cyan",
    "orange",
    "green",
    "magenta",
    "red",
    "purple",
    "blue",
]


def colour_band_specs(band: str) -> list[str]:
    if band == "dim":
        return [f"dim-{base}" for base in COLOUR_NORMAL_BRIGHTNESS_ORDER]
    if band == "bright":
        return [f"bright-{base}" for base in COLOUR_NORMAL_BRIGHTNESS_ORDER]
    if band == "all":
        return (
            [f"bright-{base}" for base in COLOUR_NORMAL_BRIGHTNESS_ORDER]
            + COLOUR_NORMAL_BRIGHTNESS_ORDER[:]
            + [f"dim-{base}" for base in COLOUR_NORMAL_BRIGHTNESS_ORDER]
        )
    return COLOUR_NORMAL_BRIGHTNESS_ORDER[:]

COLOUR_CATALOG_COLUMNS = [
    ("Dim", [f"dim-{base}" for base in COLOUR_RAINBOW_ORDER]),
    ("Normal", COLOUR_RAINBOW_ORDER[:]),
    ("Bright", [f"bright-{base}" for base in COLOUR_RAINBOW_ORDER]),
]

COLOUR_PAIR_INDICES = {
    "dim-green": 1,
    "white": 2,
    "cyan": 3,
    "yellow": 4,
    "red": 5,
    "bright-green": 6,
    "dim-cyan": 7,
    "blue": 8,
    "magenta": 9,
    "orange": 10,
    "dim-orange": 11,
    "bright-purple": 12,
    "bright-magenta": 13,
    "dim-white": 14,
    "black": 15,
    "dim-red": 16,
    "bright-red": 17,
    "bright-orange": 18,
    "dim-yellow": 19,
    "bright-yellow": 20,
    "green": 21,
    "dim-blue": 22,
    "bright-blue": 23,
    "bright-cyan": 24,
    "dim-magenta": 25,
    "dim-purple": 26,
    "purple": 27,
    "bright-white": 28,
}

COLOUR_ANSI_CODES = {
    "black": "\033[30m",
    "dim-red": "\033[38;5;88m",
    "red": "\033[38;5;160m",
    "bright-red": "\033[38;5;196m",
    "dim-orange": "\033[38;5;130m",
    "orange": "\033[38;5;208m",
    "bright-orange": "\033[38;5;214m",
    "dim-yellow": "\033[38;5;136m",
    "yellow": "\033[38;5;220m",
    "bright-yellow": "\033[38;5;226m",
    "dim-green": "\033[38;5;22m",
    "green": "\033[38;5;34m",
    "bright-green": "\033[38;5;82m",
    "dim-blue": "\033[38;5;18m",
    "blue": "\033[38;5;33m",
    "bright-blue": "\033[38;5;39m",
    "dim-cyan": "\033[38;5;23m",
    "cyan": "\033[38;5;44m",
    "bright-cyan": "\033[38;5;51m",
    "dim-magenta": "\033[38;5;90m",
    "magenta": "\033[38;5;165m",
    "bright-magenta": "\033[38;5;201m",
    "dim-purple": "\033[38;5;54m",
    "purple": "\033[38;5;93m",
    "bright-purple": "\033[38;5;141m",
    "dim-white": "\033[38;5;245m",
    "white": "\033[38;5;252m",
    "bright-white": "\033[97m",
    "multi": "\033[1m",
}


def build_colour_pairs(curses_module):
    return {
        1: (22, curses_module.COLOR_BLACK),
        2: (252, curses_module.COLOR_BLACK),
        3: (44, curses_module.COLOR_BLACK),
        4: (220, curses_module.COLOR_BLACK),
        5: (160, curses_module.COLOR_BLACK),
        6: (82, curses_module.COLOR_BLACK),
        7: (23, curses_module.COLOR_BLACK),
        8: (33, curses_module.COLOR_BLACK),
        9: (165, curses_module.COLOR_BLACK),
        10: (208, curses_module.COLOR_BLACK),
        11: (130, curses_module.COLOR_BLACK),
        12: (141, curses_module.COLOR_BLACK),
        13: (201, curses_module.COLOR_BLACK),
        14: (245, curses_module.COLOR_BLACK),
        15: (curses_module.COLOR_BLACK, curses_module.COLOR_BLACK),
        16: (88, curses_module.COLOR_BLACK),
        17: (196, curses_module.COLOR_BLACK),
        18: (214, curses_module.COLOR_BLACK),
        19: (136, curses_module.COLOR_BLACK),
        20: (226, curses_module.COLOR_BLACK),
        21: (34, curses_module.COLOR_BLACK),
        22: (18, curses_module.COLOR_BLACK),
        23: (39, curses_module.COLOR_BLACK),
        24: (51, curses_module.COLOR_BLACK),
        25: (90, curses_module.COLOR_BLACK),
        26: (54, curses_module.COLOR_BLACK),
        27: (93, curses_module.COLOR_BLACK),
        28: (15, curses_module.COLOR_BLACK),
    }


def new_paragraph():
    theme = random.choice(PARA_THEMES)
    if theme == "red":
        length = random.randint(3, 10)
    elif theme == "mixed":
        length = random.randint(8, 30)
    else:
        length = random.randint(10, 40)
    return theme, length


def line_colour(line: str, theme: str) -> tuple[int, bool]:
    if theme == "red":
        use_red = True
    elif theme == "green":
        use_red = False
    else:
        use_red = random.random() < 0.25

    if use_red:
        if line.startswith("!!"):
            return 5, True
        if "FAIL" in line or "WARN" in line:
            return 4, False
        return 5, False
    if line.startswith("!!"):
        return 5, True
    if "FAIL" in line or "ERR" in line:
        return 4, False
    if line.startswith("  ["):
        return 3, False
    if line.startswith("[") and random.random() < 0.12:
        return 2, True
    if random.random() < 0.08:
        return 6, True
    return 1, False


def rcol_colour(_line: str) -> tuple[int, bool]:
    if random.random() < 0.07:
        return 6, True
    if random.random() < 0.09:
        return 3, False
    return 7, False


def normalize_colour_spec(spec: str | None) -> str | None:
    if spec is None:
        return None
    normalized = str(spec).strip().lower().replace("-", " ").replace("_", " ")
    if normalized == "multi":
        return "multi"
    if normalized == "multi all":
        return "multi-all"
    if normalized == "multi dim":
        return "multi-dim"
    if normalized == "multi normal":
        return "multi-normal"
    if normalized == "multi bright":
        return "multi-bright"
    canonical = normalized.replace(" ", "-")
    return COLOUR_ALIASES.get(normalized, canonical)


def colour_attr_from_spec(curses_module, spec: str | None, *, default: str, bold: bool = False):
    resolved = normalize_colour_spec(spec) or normalize_colour_spec(default)
    if resolved in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"}:
        return None
    default_name = normalize_colour_spec(default) or "white"
    fallback_pair = COLOUR_PAIR_INDICES.get(default_name, COLOUR_PAIR_INDICES["white"])
    pair_index = COLOUR_PAIR_INDICES.get(resolved, fallback_pair)
    attr = curses_module.color_pair(pair_index)
    if resolved in {"yellow", "bright-yellow", "bright-white"}:
        attr |= curses_module.A_BOLD
    if bold:
        attr |= curses_module.A_BOLD
    return attr


def colour_family_name(spec: str | None, *, default: str = "green") -> str:
    resolved = normalize_colour_spec(spec) or normalize_colour_spec(default) or "green"
    if resolved in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"}:
        return "multi"
    if resolved in COLOUR_SINGLES:
        fallback = normalize_colour_spec(default) or "green"
        if fallback in COLOUR_TRIADS:
            return fallback
        if "-" in fallback:
            tone, base = fallback.split("-", 1)
            if tone in {"dim", "bright"} and base in COLOUR_TRIADS:
                return base
        return "green"
    if resolved in COLOUR_TRIADS:
        return resolved
    if "-" in resolved:
        tone, base = resolved.split("-", 1)
        if tone in {"dim", "bright"} and base in COLOUR_TRIADS:
            return base
    return normalize_colour_spec(default) or "green"


def life_ramp_specs(spec: str | None) -> list[str]:
    resolved = normalize_colour_spec(spec) or "green"
    if resolved in {"multi", "multi-normal"}:
        return colour_band_specs("normal")
    if resolved == "multi-dim":
        return colour_band_specs("dim")
    if resolved == "multi-bright":
        return colour_band_specs("bright")
    if resolved == "multi-all":
        return colour_band_specs("all")
    family = colour_family_name(resolved, default="green")
    if family == "multi":
        return colour_band_specs("normal")
    return ["bright-white", f"bright-{family}", family, f"dim-{family}", "dim-white"]


def multi_palette_specs(spec: str | None, *, bare_multi: str = "multi-normal") -> list[str]:
    resolved = normalize_colour_spec(spec) or bare_multi
    if resolved == "multi":
        resolved = bare_multi
    if resolved == "multi-all":
        return colour_band_specs("all")
    if resolved == "multi-dim":
        return colour_band_specs("dim")
    if resolved == "multi-normal":
        return colour_band_specs("normal")
    if resolved == "multi-bright":
        return colour_band_specs("bright")
    return [resolved]


def blocks_palette_specs(spec: str | None) -> list[str]:
    resolved = normalize_colour_spec(spec) or "multi-all"
    if resolved == "multi":
        resolved = "multi-all"
    if resolved == "multi-all":
        return [colour_name for colour_name in COLOUR_PAIR_INDICES if colour_name != "black"]
    if resolved == "multi-dim":
        return [f"dim-{base}" for base in COLOUR_RAINBOW_ORDER]
    if resolved == "multi-normal":
        return COLOUR_RAINBOW_ORDER[:]
    if resolved == "multi-bright":
        return [f"bright-{base}" for base in COLOUR_RAINBOW_ORDER]
    if resolved == "black":
        return []
    return [resolved]


def tunnel_palette_specs(spec: str | None) -> list[str]:
    resolved = normalize_colour_spec(spec) or "multi"
    if resolved == "multi":
        resolved = "multi-bright"
    if resolved == "multi-all":
        return [colour_name for colour_name in COLOUR_PAIR_INDICES if colour_name != "black"]
    if resolved == "multi-dim":
        return [f"dim-{base}" for base in COLOUR_RAINBOW_ORDER]
    if resolved == "multi-normal":
        return COLOUR_RAINBOW_ORDER[:]
    if resolved == "multi-bright":
        return [f"bright-{base}" for base in COLOUR_RAINBOW_ORDER]
    if resolved == "black":
        return []
    return [resolved]


def ansi_colour_label(name: str, *, is_tty: bool) -> str:
    if not is_tty:
        return name
    resolved = normalize_colour_spec(name) or name
    code = COLOUR_ANSI_CODES.get(resolved, "")
    if not code:
        return name
    return f"{code}{name}\033[0m"


def centre_delay(speed: int) -> float:
    if speed >= 100:
        return 0.0
    lo, hi = math.log(0.004), math.log(1.0)
    t = (speed - 1) / 98
    return math.exp(hi + t * (lo - hi))


def make_burst_fn(speed: int):
    centre = centre_delay(speed)
    if centre == 0.0:
        def new_burst():
            return 0.0, BURST_SIZE

        return new_burst

    tiers = [
        (centre * 0.40, centre * 0.75, 30),
        (centre * 0.80, centre * 1.30, 45),
        (centre * 1.50, centre * 3.00, 25),
    ]
    pool = [tier for tier in tiers for _ in range(tier[2])]

    def new_burst():
        low, high, _ = random.choice(pool)
        delay = random.uniform(low, high)
        count = BURST_SIZE + random.randint(-12, 12)
        return delay, count

    return new_burst


def clamp_speed(speed: int) -> int:
    return max(1, min(100, int(speed)))


def scaled_speed(base_speed: int, ratio: float) -> int:
    return clamp_speed(round(base_speed * ratio))


def strip_overstrikes(text: str) -> str:
    return re.sub(r".\x08", "", text)


def load_prime_values(base_dir: str) -> list[str]:
    primes_path = os.path.join(base_dir, "data", "primes.txt")
    try:
        with open(primes_path, "r", encoding="utf-8") as prime_file:
            values = [line.strip() for line in prime_file if line.strip()]
    except OSError:
        values = ["2", "3", "5", "7", "11"]
    return values or ["2", "3", "5", "7", "11"]


def make_text_state():
    theme, left = new_paragraph()
    return {"theme": theme, "left": left, "countdown": random.randint(35, 50)}


def make_area_state(theme_name: str | None, default_theme: str, get_bar_config) -> dict:
    area_theme = theme_name or default_theme
    bar_headers, bar_labels = get_bar_config(area_theme)
    return {
        "buf": [],
        "tick": 0,
        "text": make_text_state(),
        "feed_text": make_text_state(),
        "bars_headers": bar_headers[:],
        "bars_labels": bar_labels[:],
        "bars_values": [random.uniform(0.08, 0.92) for _ in bar_labels],
        "bars_drift": [random.gauss(0, 0.02) for _ in bar_labels],
        "crash_lines": [],
        "crash_phase": 0,
        "crash_flash_frames": 0,
        "crash_blank_frames": 0,
        "crash_invert_frames": 0,
        "crash_static_frames": 0,
        "scope_vals": [],
        "scope_drift": 0.0,
        "scope_phase": random.uniform(0.0, math.tau),
        "scope_warmed": False,
        "matrix_cols": [],
        "matrix_warmed": False,
        "orbit_sig": None,
        "orbit_cells": [],
        "rotate_sig": None,
        "rotate_cells": [],
        "rotate_angle": 0.0,
        "sweep_warmed": False,
        "cycle_catalog": [],
        "cycle_widgets": [],
        "cycle_order": [],
        "cycle_idx": 0,
        "cycle_next_change": 0.0,
        "cycle_current": None,
        "gauge_angle": random.uniform(0.0, math.tau),
        "gauge_blips": [],
        "gauge_tick": 0,
        "gauge_spin": 1,
        "gauge_next_spin_change": 0.0,
        "direction_next_change": 0.0,
        "direction_motion": 1,
        "direction_motion_prev": 1,
        "metrics_signal": None,
        "metrics_title": "",
        "colour_override": None,
        "metrics_base_reads": [],
        "metrics_reads": [],
        "metrics_spark": [],
        "metrics_drift": 0.0,
        "metrics_hist": [],
        "metrics_arrows": [],
        "metrics_last_values": [],
        "metrics_next_reads_at": 0.0,
        "metrics_count": 0,
        "metrics_prime_idx": 0,
        "blocks_bg": random.choice([1, 3, 7]),
        "blocks_cells": [],
        "blocks_warmed": False,
        "sweep_cells": [],
        "sweep_pos": 0,
        "sweep_dir": 1,
        "tunnel_sig": None,
        "tunnel_layers": [],
        "tunnel_colour_sig": None,
        "tunnel_band_attrs": [],
        "tunnel_phase": random.random(),
        "tunnel_palette_idx": random.randrange(6),
        "tunnel_drift_phase": random.uniform(0.0, math.tau),
        "next_update": 0.0,
        "last_update_at": 0.0,
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
        "configured_speed": 0,
        "current_speed": 0,
        "theme_override": theme_name,
        "text_override": None,
        "direction_override": None,
        "unavailable_message": None,
        "static_lines": [],
        "static_align": "top",
    }


def resize_restartable(exc: Exception, *, curses_module, app_path: str, helper_names: set[str]) -> bool:
    if isinstance(exc, curses_module.error):
        return True
    if not isinstance(exc, IndexError):
        return False
    tb = traceback.extract_tb(exc.__traceback__)
    app_path = os.path.abspath(app_path)
    for frame in tb:
        if os.path.abspath(frame.filename) != app_path:
            continue
        if frame.name in helper_names:
            return True
    return False
