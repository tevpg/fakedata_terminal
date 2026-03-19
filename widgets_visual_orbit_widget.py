"""Orbit widget renderer."""

from __future__ import annotations

import math
import random

try:
    from .runtime_support import multi_palette_specs
    from .timing_support import gauge_radians_per_second, resolve_direction_motion
    from .widgets_visual_orbit import orbit_field_bounds, rotate_offset
except ImportError:
    from runtime_support import multi_palette_specs
    from timing_support import gauge_radians_per_second, resolve_direction_motion
    from widgets_visual_orbit import orbit_field_bounds, rotate_offset


class OrbitWidget:
    GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&+=?<>[]{}/*-:."

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        self.curses = curses_module
        self.stdscr = stdscr
        self.colour_attr_from_spec = colour_attr_from_spec
        self.normalize_colour_spec = normalize_colour_spec

    def ensure(self, area: dict, rows: int, width: int) -> None:
        sig = (rows, width)
        if area.get("orbit_sig") == sig and area.get("orbit_cells"):
            return
        area["orbit_sig"] = sig
        area["orbit_cells"] = self.seed_cells(rows, width)

    def seed_cells(self, rows: int, width: int) -> list[tuple[float, float, float, str, int, float]]:
        max_dx, max_dy, source_rows, source_width = orbit_field_bounds(rows, width, cell_aspect_y=2.0)
        max_radius = math.hypot(max_dx, max_dy * 2.0)
        count = max(24, min(420, (source_rows * source_width) // 7))
        cells: list[tuple[float, float, float, str, int, float]] = []
        for idx in range(count):
            dx = random.uniform(-max_dx, max_dx)
            dy = random.uniform(-max_dy, max_dy)
            if ((dx / max_dx) ** 2) + ((dy / max_dy) ** 2) > 1.0:
                scale = random.uniform(0.10, 0.98)
                theta = random.uniform(0.0, math.tau)
                dx = math.cos(theta) * max_dx * scale
                dy = math.sin(theta) * max_dy * scale
            radius_norm = min(1.0, math.hypot(dx, dy * 2.0) / max(1.0, max_radius))
            # Fudgy heuristic: the closer to the centre, the faster the orbit.
            velocity = 0.55 + ((1.0 - radius_norm) * 2.10)
            phase = random.uniform(0.0, math.tau)
            cells.append((dx, dy, phase, random.choice(self.GLYPHS), idx, velocity))
        return cells

    def update(self, area: dict, rows: int, width: int, now: float, dt: float, speed: int) -> None:
        self.ensure(area, rows, width)
        motion = resolve_direction_motion(area, "orbit", now)
        cells = area.get("orbit_cells") or []
        if not cells:
            return
        if motion == 0:
            return
        base_rate = gauge_radians_per_second(speed, widget="orbit") * dt * motion
        updated = []
        for dx, dy, phase, glyph, palette_idx, velocity in cells:
            updated.append((dx, dy, (phase + (base_rate * velocity)) % math.tau, glyph, palette_idx, velocity))
        area["orbit_cells"] = updated
        if random.random() < 0.08:
            idx = random.randrange(len(updated))
            dx, dy, phase, _old_glyph, palette_idx, velocity = updated[idx]
            updated[idx] = (dx, dy, phase, random.choice(self.GLYPHS), palette_idx, velocity)

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "green"
        multi_specs = multi_palette_specs(colour_spec, bare_multi="multi-normal")
        palette = [
            self.colour_attr_from_spec(self.curses, spec, default=spec, bold=True)
            for spec in multi_specs
        ]
        if not palette:
            palette = [self.colour_attr_from_spec(self.curses, "green", default="green", bold=True)]

        blank_attr = self.curses.color_pair(1)
        for r in range(rows):
            try:
                self.stdscr.addnstr(y + r, x, " " * width, width, blank_attr)
            except self.curses.error:
                pass

        cx = (width - 1) / 2.0
        cy = (rows - 1) / 2.0
        occupied: set[tuple[int, int]] = set()
        for dx, dy, phase, glyph, palette_idx, _velocity in area.get("orbit_cells") or []:
            rot_x, rot_y = rotate_offset(dx, dy, phase, cell_aspect_y=2.0)
            col = int(round(cx + rot_x))
            row = int(round(cy + rot_y))
            if not (0 <= row < rows and 0 <= col < width):
                continue
            if (row, col) in occupied:
                continue
            occupied.add((row, col))
            attr = palette[palette_idx % len(palette)]
            try:
                self.stdscr.addch(y + row, x + col, glyph, attr)
            except self.curses.error:
                pass
