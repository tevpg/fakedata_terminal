"""Area layout and synchronization helpers for FakeData Terminal."""

from __future__ import annotations

import random

try:
    from .timing_support import cycle_start_deadline
except ImportError:
    from timing_support import cycle_start_deadline


def sidebar_cycle_modes_for_main(main_mode: str, sidebar_cycle_modes: list[str]) -> list[str]:
    if main_mode in ("text", "text_wide"):
        blocked = {"text", "text_wide", main_mode}
    else:
        blocked = {main_mode}
    modes = [mode for mode in sidebar_cycle_modes if mode not in blocked]
    return modes if modes else ["readouts"]


def cycle_widget_names(include_image: bool) -> list[str]:
    names = [
        "bars", "blocks", "crash", "gauge", "image", "life", "matrix",
        "rotate", "scope", "readouts", "sparkline", "spiral", "sweep", "tunnel", "whorl",
        "text", "text_scant", "text_spew", "text_wide",
    ]
    if not include_image:
        names = [name for name in names if name != "image"]
    return names


def role_for_area(spec: dict) -> str:
    if spec.get("role"):
        return spec["role"]
    return "main" if spec["x"] < 0.5 else "sidebar"


def scaled_rect(spec: dict, rows: int, cols: int) -> dict:
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
        "role": role_for_area(spec),
    }


def config_area_specs(config_style: dict, rows: int, cols: int) -> list[dict]:
    specs = []
    for area_spec in sorted(config_style["areas"], key=lambda item: (item["x"], item["y"], item["name"])):
        rect = scaled_rect(area_spec, rows, cols)
        if rect.get("theme") is None and config_style.get("theme") is not None:
            rect["theme"] = config_style["theme"]
        if rect.get("direction") is None and config_style.get("direction") is not None:
            rect["direction"] = config_style["direction"]
        specs.append(rect)
    return specs


def legacy_area_specs(*, cols: int, rows: int, main_mode: str, sidebar_mode: str, effective_sidebar_mode, layout) -> list[dict]:
    main_w, side_w, side_x = layout(cols)
    specs = [{
        "name": "main",
        "mode": main_mode,
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
            "mode": effective_sidebar_mode(),
            "x": side_x,
            "y": 0,
            "width": side_w,
            "height": rows,
            "role": "sidebar",
            "separator_after": False,
        })
    return specs


def sync_areas(area_specs: list[dict], area_states: dict[str, dict], make_area, reset_area_timing) -> dict[str, dict]:
    synced = {}
    for spec in area_specs:
        area = area_states.get(spec["name"])
        if area is None or area["mode"] != spec["mode"] or area.get("theme_override") != spec.get("theme"):
            area = make_area(spec["mode"], spec.get("theme"))
            area["mode"] = spec["mode"]
            area["name"] = spec["name"]
            area["text_override"] = spec.get("text")
            area["label"] = spec.get("label")
            area["speed_override"] = spec.get("speed")
            area["density_override"] = spec.get("density")
            area["colour_override"] = spec.get("colour")
            area["direction_override"] = spec.get("direction")
            area["role"] = spec["role"]
            area["theme_override"] = spec.get("theme")
            area["image_paths"] = spec.get("image_paths") or []
            area["cycle_widgets"] = spec.get("cycle_widgets") or []
            area["unavailable_message"] = spec.get("unavailable_message")
            area["static_lines"] = spec.get("static_lines") or []
            area["static_align"] = spec.get("static_align") or "top"
            reset_area_timing(area)
        else:
            area["text_override"] = spec.get("text")
            area["label"] = spec.get("label")
            area["speed_override"] = spec.get("speed")
            area["density_override"] = spec.get("density")
            area["colour_override"] = spec.get("colour")
            area["direction_override"] = spec.get("direction")
            area["role"] = spec["role"]
            area["theme_override"] = spec.get("theme")
            area["image_paths"] = spec.get("image_paths") or []
            area["cycle_widgets"] = spec.get("cycle_widgets") or []
            area["unavailable_message"] = spec.get("unavailable_message")
            area["static_lines"] = spec.get("static_lines") or []
            area["static_align"] = spec.get("static_align") or "top"
        synced[spec["name"]] = area
    return synced


def sync_cycle_start_modes(area_specs: list[dict], area_states: dict[str, dict], ensure_cycle, now: float | None = None):
    now = 0.0 if now is None else now
    used = set()
    for spec in area_specs:
        area = area_states[spec["name"]]
        if area["mode"] != "cycle":
            continue
        ensure_cycle(area, now)
        current = area.get("cycle_current")
        if current and current not in used:
            used.add(current)
            continue
        candidates = [name for name in area["cycle_catalog"] if name not in used]
        if not candidates:
            candidates = area["cycle_catalog"][:]
        current = "text" if not candidates else random.choice(candidates)
        area["cycle_current"] = current
        area["label"] = current
        if current in area["cycle_order"]:
            area["cycle_idx"] = area["cycle_order"].index(current)
        area["cycle_next_change"] = cycle_start_deadline(now)
        area["next_update"] = 0.0
        used.add(current)
