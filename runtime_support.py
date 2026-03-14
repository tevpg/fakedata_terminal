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


def build_colour_pairs(curses_module):
    return {
        1: (curses_module.COLOR_GREEN, curses_module.COLOR_BLACK),
        2: (curses_module.COLOR_WHITE, curses_module.COLOR_BLACK),
        3: (curses_module.COLOR_CYAN, curses_module.COLOR_BLACK),
        4: (curses_module.COLOR_YELLOW, curses_module.COLOR_BLACK),
        5: (curses_module.COLOR_RED, curses_module.COLOR_BLACK),
        6: (82, curses_module.COLOR_BLACK),
        7: (curses_module.COLOR_CYAN, curses_module.COLOR_BLACK),
        8: (curses_module.COLOR_BLUE, curses_module.COLOR_BLACK),
        9: (curses_module.COLOR_MAGENTA, curses_module.COLOR_BLACK),
        10: (208, curses_module.COLOR_BLACK),
        11: (172, curses_module.COLOR_BLACK),
        12: (141, curses_module.COLOR_BLACK),
        13: (213, curses_module.COLOR_BLACK),
        14: (245, curses_module.COLOR_BLACK),
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
    aliases = {
        "brightgreen": "lime",
        "bright green": "lime",
        "light green": "lime",
        "lightblue": "cyan",
        "light blue": "cyan",
        "gray": "grey",
        "brown": "amber",
    }
    return aliases.get(normalized, normalized)


def colour_attr_from_spec(curses_module, spec: str | None, *, default: str, bold: bool = False):
    resolved = normalize_colour_spec(spec) or normalize_colour_spec(default)
    if resolved == "multi":
        return None
    mapping = {
        "green": curses_module.color_pair(1),
        "lime": curses_module.color_pair(6),
        "red": curses_module.color_pair(5),
        "yellow": curses_module.color_pair(4),
        "orange": curses_module.color_pair(10),
        "amber": curses_module.color_pair(11),
        "cyan": curses_module.color_pair(3),
        "blue": curses_module.color_pair(8),
        "magenta": curses_module.color_pair(9),
        "purple": curses_module.color_pair(12),
        "pink": curses_module.color_pair(13),
        "white": curses_module.color_pair(2),
        "grey": curses_module.color_pair(14),
        "gray": curses_module.color_pair(14),
    }
    attr = mapping.get(resolved, mapping[normalize_colour_spec(default) or "white"])
    if bold:
        attr |= curses_module.A_BOLD
    return attr


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


def make_area_state(vocab_name: str | None, default_vocab: str, get_bar_config) -> dict:
    area_vocab = vocab_name or default_vocab
    bar_headers, bar_labels = get_bar_config(area_vocab)
    return {
        "buf": [],
        "tick": 0,
        "text": make_text_state(),
        "feed_text": make_text_state(),
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
        "colour_override": None,
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
        "vocab_override": vocab_name,
        "text_override": None,
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
