"""Shared timing configuration and scheduling helpers."""

from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
import random
import subprocess
import sys

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


PACKAGE_DIR = Path(__file__).resolve().parent
TIMING_CONFIG_PATH = PACKAGE_DIR / "widgets.yaml"


@lru_cache(maxsize=1)
def load_timing_config() -> dict:
    try:
        with TIMING_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError:
        data = {}
    if not isinstance(data, dict):
        return {}
    return data


def _timing_defaults() -> dict:
    config = load_timing_config()
    defaults = config.get("defaults")
    if not isinstance(defaults, dict):
        return {}
    timing = defaults.get("timing")
    return timing if isinstance(timing, dict) else {}


def _speed_defaults() -> dict:
    timing = _timing_defaults()
    speed = timing.get("speed")
    return speed if isinstance(speed, dict) else {}


def dt_clamp_seconds() -> float:
    value = _speed_defaults().get("dt_clamp_seconds", 0.5)
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.5


def clamp_speed(speed: int) -> int:
    return max(1, min(100, int(speed)))


def base_iterations_per_second(speed: int) -> float:
    config = _speed_defaults()
    lo = float(config.get("min_iterations_per_second", 1.0))
    hi = float(config.get("max_iterations_per_second", 50.0))
    speed = clamp_speed(speed)
    if speed <= 1:
        return lo
    if speed >= 100:
        return hi
    t = (speed - 1) / 99.0
    curve = str(config.get("curve", "linear")).lower()
    if curve == "linear":
        return lo + ((hi - lo) * t)
    # Fallback to linear until a different curve is intentionally introduced.
    return lo + ((hi - lo) * t)


def widget_settings(widget: str) -> dict:
    config = load_timing_config()
    widgets = config.get("widgets")
    if not isinstance(widgets, dict):
        return {}
    entry = widgets.get(widget)
    return entry if isinstance(entry, dict) else {}


def _timing_section(widget: str) -> dict:
    timing = widget_settings(widget).get("timing")
    return timing if isinstance(timing, dict) else {}


def widget_cadence_factor(widget: str) -> float:
    value = _timing_section(widget).get("cadence_factor", 1.0)
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 1.0


def widget_interval(widget: str, speed: int) -> float:
    factor = widget_cadence_factor(widget)
    if factor <= 0.0:
        return math.inf
    rate = base_iterations_per_second(speed) * factor
    if rate <= 0.0:
        return math.inf
    return 1.0 / rate


def schedule_next(next_update: float, now: float, interval: float) -> float:
    if math.isinf(interval):
        return math.inf
    if interval <= 0.0:
        return now
    if next_update <= 0.0:
        return now + interval
    candidate = next_update + interval
    if candidate < now - interval:
        return now + interval
    return candidate


def shift_deadline(deadline: float, delta: float) -> float:
    if deadline <= 0.0 or math.isinf(deadline):
        return deadline
    return deadline + delta


def _behavior_section(widget: str) -> dict:
    behavior = widget_settings(widget).get("behavior")
    return behavior if isinstance(behavior, dict) else {}


def cycle_change_interval_seconds() -> float:
    controller = _behavior_section("cycle").get("controller")
    if isinstance(controller, dict):
        value = controller.get("change_interval_seconds", 10.0)
        try:
            return max(0.01, float(value))
        except (TypeError, ValueError):
            pass
    return 10.0


def cycle_start_jitter_range_seconds() -> tuple[float, float]:
    controller = _behavior_section("cycle").get("controller")
    if isinstance(controller, dict):
        values = controller.get("start_jitter_range_seconds")
        if isinstance(values, (list, tuple)) and len(values) == 2:
            try:
                lo = float(values[0])
                hi = float(values[1])
                return (min(lo, hi), max(lo, hi))
            except (TypeError, ValueError):
                pass
    return (0.0, 10.0)


def cycle_start_deadline(now: float) -> float:
    lo, hi = cycle_start_jitter_range_seconds()
    return now + random.uniform(lo, hi)


def next_cycle_deadline(now: float) -> float:
    return now + cycle_change_interval_seconds()


def direction_random_settings(widget: str) -> dict:
    behavior = _behavior_section(widget)
    direction = behavior.get("direction_random")
    return direction if isinstance(direction, dict) else {}


def read_refresh_interval(widget: str, role: str, theme_name: str | None) -> float | None:
    settings = _behavior_section(widget).get("read_refresh")
    if not isinstance(settings, dict):
        return None
    if theme_name == "pharmacy" and role == "sidebar":
        key = "pharmacy_sidebar_interval_seconds"
    elif role == "sidebar":
        key = "sidebar_interval_seconds"
    else:
        key = "main_interval_seconds"
    value = settings.get(key)
    try:
        return max(0.01, float(value))
    except (TypeError, ValueError):
        return None


def feed_scroll_interval(widget: str) -> float | None:
    settings = _behavior_section(widget).get("feed_scroll")
    if not isinstance(settings, dict):
        return None
    value = settings.get("interval_seconds")
    try:
        return max(0.01, float(value))
    except (TypeError, ValueError):
        return None


def motion_factor(widget: str) -> float:
    motion = _timing_section(widget).get("motion")
    if not isinstance(motion, dict):
        return 1.0
    value = motion.get("factor", 1.0)
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 1.0


def gauge_radians_per_second(speed: int, *, widget: str = "gauge") -> float:
    # First-pass semantic motion mapping:
    # speed 1 -> about 6 RPM; speed 100 -> about 300 RPM.
    rpm = (6.0 * base_iterations_per_second(speed)) * motion_factor(widget)
    return (rpm / 60.0) * math.tau


def resolve_direction_motion(area: dict, widget: str, now: float) -> int:
    direction = str(area.get("direction_override") or "forward").lower()
    if direction == "none":
        area["direction_motion"] = 0
        return 0
    if direction == "forward":
        area["direction_motion"] = 1
        return 1
    if direction == "backward":
        area["direction_motion"] = -1
        return -1

    settings = direction_random_settings(widget)
    if not settings:
        area["direction_motion"] = 1
        return 1

    next_change = float(area.get("direction_next_change", 0.0) or 0.0)
    if next_change > now:
        return int(area.get("direction_motion", 1))

    choices = [
        ("backward", float(settings.get("backward_probability", 0.0))),
        ("none", float(settings.get("none_probability", 0.0))),
        ("forward", float(settings.get("forward_probability", 1.0))),
    ]
    total = sum(max(0.0, weight) for _, weight in choices)
    if total <= 0.0:
        picked = "forward"
    else:
        roll = random.uniform(0.0, total)
        running = 0.0
        picked = "forward"
        for name, weight in choices:
            running += max(0.0, weight)
            if roll <= running:
                picked = name
                break

    area["direction_motion"] = {"backward": -1, "none": 0, "forward": 1}[picked]
    duration_key = f"{picked}_duration_range_seconds"
    values = settings.get(duration_key, [0.5, 3.0])
    try:
        lo = float(values[0])
        hi = float(values[1])
    except (TypeError, ValueError, IndexError):
        lo, hi = 0.5, 3.0
    area["direction_next_change"] = now + random.uniform(min(lo, hi), max(lo, hi))
    return area["direction_motion"]
