"""Oscilloscope widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import math
import random


class ScopeWidget:
    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        draw_centered_overlay,
        area_theme,
        get_gauge_config,
        resolved_direction_motion,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.draw_centered_overlay = draw_centered_overlay
        self.area_theme = area_theme
        self.get_gauge_config = get_gauge_config
        self.resolved_direction_motion = resolved_direction_motion

    def update(self, area: dict, width: int) -> None:
        motion = self.resolved_direction_motion(area)
        keep = max(12, width + 12)
        cfg = self.get_gauge_config(self.area_theme(area))
        area["scope_signal"] = cfg[1]
        if motion == 0:
            if len(area["scope_vals"]) != keep:
                raw = area["scope_signal"]()
                phase = area.get("scope_phase", 0.0)
                amplitude = 0.16 + raw * 0.18
                samples = []
                for idx in range(keep):
                    pos = idx / max(1, keep - 1)
                    base = math.sin((phase + pos * math.tau) * 1.1) * amplitude
                    harmonic = math.sin((phase * 2.7) + pos * math.tau * 2.2 + raw * 3.0) * 0.05
                    ripple = math.sin((phase * 0.7) + pos * math.tau * 5.0) * 0.018
                    sample = 0.5 + base + harmonic + ripple
                    samples.append(max(0.04, min(0.96, sample)))
                area["scope_vals"] = samples
                area["direction_motion_prev"] = 0
            return
        prev_motion = area.get("direction_motion_prev", motion)
        if prev_motion != motion:
            visible = area["scope_vals"][-width:] if prev_motion >= 0 else area["scope_vals"][:width]
            area["scope_vals"] = visible[:]
            area["direction_motion_prev"] = motion
        raw = area["scope_signal"]()
        phase = area.get("scope_phase", 0.0)
        phase += 0.22 + raw * 0.34 + random.uniform(-0.04, 0.04)
        area["scope_phase"] = phase % math.tau
        amplitude = 0.16 + raw * 0.18
        harmonic = math.sin(phase * 2.7 + raw * 3.0) * 0.05
        noise = random.gauss(0, 0.025)
        spike = 0.0
        if random.random() < 0.04:
            spike = random.choice([-1.0, 1.0]) * random.uniform(0.05, 0.16)
        nxt = 0.5 + math.sin(phase) * amplitude + harmonic + noise + spike
        sample = max(0.04, min(0.96, nxt))
        if motion < 0:
            area["scope_vals"].insert(0, sample)
        else:
            area["scope_vals"].append(sample)
        if len(area["scope_vals"]) > keep:
            if motion < 0:
                area["scope_vals"] = area["scope_vals"][:keep]
            else:
                area["scope_vals"] = area["scope_vals"][-keep:]
        area["direction_motion_prev"] = motion

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        motion = area.get("direction_motion", 1)
        if len(area["scope_vals"]) >= width:
            vals = area["scope_vals"][:width] if motion < 0 else area["scope_vals"][-width:]
        else:
            vals = area["scope_vals"]
        vals = vals or [0.5] * width
        canvas = [[" " for _ in range(width)] for _ in range(rows)]
        mid = rows // 2
        for c in range(0, width, 4):
            canvas[mid][c] = "·"
        prev_y = None
        for c, v in enumerate(vals):
            sample_y = int((1.0 - v) * max(1, rows - 1))
            sample_y = max(0, min(rows - 1, sample_y))
            canvas[sample_y][c] = "█"
            if prev_y is not None:
                low, high = sorted((prev_y, sample_y))
                for yy in range(low, high + 1):
                    if canvas[yy][c] == " ":
                        canvas[yy][c] = "│"
            prev_y = sample_y
        for r in range(rows):
            frac = r / max(1, rows - 1)
            cp = 3 if frac < 0.33 else (5 if frac > 0.66 else 6)
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, "".join(canvas[r])[:safe_w], safe_w, self.curses.color_pair(cp))
            except self.curses.error:
                pass
        self.draw_centered_overlay(area, 1 if rows > 1 else 0, y, x, width, rows=rows, anchor="top")
