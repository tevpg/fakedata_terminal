"""Shared orbit math helpers for rotate/swirl-style visual widgets."""

from __future__ import annotations

import math
import random

try:
    from .runtime_support import multi_palette_specs
    from .timing_support import gauge_radians_per_second, resolve_direction_motion
except ImportError:
    from runtime_support import multi_palette_specs
    from timing_support import gauge_radians_per_second, resolve_direction_motion


def orbit_field_bounds(rows: int, width: int, *, cell_aspect_y: float = 2.0) -> tuple[float, float, int, int]:
    half_w = max(1.0, (width - 1) / 2.0)
    half_h_iso = max(1.0, ((rows - 1) / 2.0) * cell_aspect_y)
    orbit_radius = math.hypot(half_w, half_h_iso)
    max_dx = max(1.0, orbit_radius - 1.0)
    max_dy = max(1.0, (orbit_radius / cell_aspect_y) - 0.5)
    source_rows = max(rows, int(round((max_dy * 2.0) + 1.0)))
    source_width = max(width, int(round((max_dx * 2.0) + 1.0)))
    return max_dx, max_dy, source_rows, source_width


def rotate_offset(dx: float, dy: float, angle: float, *, cell_aspect_y: float = 2.0) -> tuple[float, float]:
    """Rotate a screen-space offset using isotropic math.

    Terminal character cells are typically about twice as tall as they are wide,
    so the y axis is scaled into isotropic space before rotation and scaled back
    into screen rows afterward.
    """

    iso_x = dx
    iso_y = dy * cell_aspect_y
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    rot_x = (iso_x * cos_a) - (iso_y * sin_a)
    rot_y = (iso_x * sin_a) + (iso_y * cos_a)
    return rot_x, rot_y / cell_aspect_y


class OrbitalFieldWidget:
    GLYPHS = "αβγδεζηθλμξπρστυφχψωΔΘΛΞΠΣΦΨΩ∂∇∞∑∏∫√≈≠≤≥⊕⊗⊙⊛⊜⊝⊞⊟⊠⊡☉☌☍☿♀♁♂♃♄♅♆♇⚝✦✧·∘"
    CELL_ASPECT_Y = 2.0
    SEED_DIVISOR = 7
    MIN_SEED_COUNT = 24
    MAX_SEED_COUNT = 420
    MUTATION_PROBABILITY = 0.08
    RANDOM_INITIAL_PHASE = True
    RIGID_SPEED_MULTIPLIER = 1.0
    ORBIT_FACTOR = 0.0
    DIFFERENTIAL_BASE = 0.55
    DIFFERENTIAL_SPREAD = 2.10
    FALLOFF_EXPONENT = 1.0
    RADIAL_DECAY_PER_SECOND = 0.0
    RESPAWN_INNER_RADIUS_NORM = 0.08
    RESPAWN_OUTER_MIN_RADIUS_NORM = 0.88
    RESPAWN_OUTER_MAX_RADIUS_NORM = 0.98
    RESPAWN_INNER_MIN_RADIUS_NORM = 0.04
    RESPAWN_INNER_MAX_RADIUS_NORM = 0.18

    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        colour_attr_from_spec,
        normalize_colour_spec,
        widget_name: str,
        state_prefix: str,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.colour_attr_from_spec = colour_attr_from_spec
        self.normalize_colour_spec = normalize_colour_spec
        self.widget_name = widget_name
        self.state_prefix = state_prefix

    def state_key(self, suffix: str) -> str:
        return f"{self.state_prefix}_{suffix}"

    def ensure(self, area: dict, rows: int, width: int) -> None:
        sig = (rows, width)
        if area.get(self.state_key("sig")) == sig and area.get(self.state_key("cells")):
            return
        area[self.state_key("sig")] = sig
        area[self.state_key("cells")] = self.seed_cells(rows, width)

    def velocity_multiplier(self, radius_norm: float) -> float:
        shaped_falloff = (1.0 - radius_norm) ** self.FALLOFF_EXPONENT
        differential = self.DIFFERENTIAL_BASE + (shaped_falloff * self.DIFFERENTIAL_SPREAD)
        return (
            ((1.0 - self.ORBIT_FACTOR) * self.RIGID_SPEED_MULTIPLIER)
            + (self.ORBIT_FACTOR * differential)
        )

    def orbit_geometry(self, rows: int, width: int) -> tuple[float, float, int, int, float]:
        max_dx, max_dy, source_rows, source_width = orbit_field_bounds(rows, width, cell_aspect_y=self.CELL_ASPECT_Y)
        max_radius = math.hypot(max_dx, max_dy * self.CELL_ASPECT_Y)
        return max_dx, max_dy, source_rows, source_width, max_radius

    def random_offset(
        self,
        max_dx: float,
        max_dy: float,
        *,
        radius_norm_min: float = 0.0,
        radius_norm_max: float = 1.0,
    ) -> tuple[float, float]:
        radius_norm_min = max(0.0, min(1.0, radius_norm_min))
        radius_norm_max = max(radius_norm_min, min(1.0, radius_norm_max))
        theta = random.uniform(0.0, math.tau)
        radius_norm = random.uniform(radius_norm_min ** 2, radius_norm_max ** 2) ** 0.5
        dx = math.cos(theta) * max_dx * radius_norm
        dy = math.sin(theta) * max_dy * radius_norm
        return dx, dy

    def build_cell(
        self,
        idx: int,
        dx: float,
        dy: float,
        max_radius: float,
        *,
        phase: float | None = None,
    ) -> tuple[float, float, float, str, int, float]:
        radius_norm = min(1.0, math.hypot(dx, dy * self.CELL_ASPECT_Y) / max(1.0, max_radius))
        velocity = self.velocity_multiplier(radius_norm)
        cell_phase = random.uniform(0.0, math.tau) if phase is None and self.RANDOM_INITIAL_PHASE else (phase or 0.0)
        return (dx, dy, cell_phase, random.choice(self.GLYPHS), idx, velocity)

    def respawn_cell(
        self,
        idx: int,
        max_dx: float,
        max_dy: float,
        max_radius: float,
        *,
        outward: bool,
        phase: float | None = None,
    ) -> tuple[float, float, float, str, int, float]:
        if outward:
            dx, dy = self.random_offset(
                max_dx,
                max_dy,
                radius_norm_min=self.RESPAWN_INNER_MIN_RADIUS_NORM,
                radius_norm_max=self.RESPAWN_INNER_MAX_RADIUS_NORM,
            )
        else:
            dx, dy = self.random_offset(
                max_dx,
                max_dy,
                radius_norm_min=self.RESPAWN_OUTER_MIN_RADIUS_NORM,
                radius_norm_max=self.RESPAWN_OUTER_MAX_RADIUS_NORM,
            )
        return self.build_cell(idx, dx, dy, max_radius, phase=phase)

    def seed_cells(self, rows: int, width: int) -> list[tuple[float, float, float, str, int, float]]:
        max_dx, max_dy, source_rows, source_width, max_radius = self.orbit_geometry(rows, width)
        count = max(self.MIN_SEED_COUNT, min(self.MAX_SEED_COUNT, (source_rows * source_width) // self.SEED_DIVISOR))
        cells: list[tuple[float, float, float, str, int, float]] = []
        for idx in range(count):
            dx, dy = self.random_offset(max_dx, max_dy, radius_norm_min=0.10, radius_norm_max=0.98)
            cells.append(self.build_cell(idx, dx, dy, max_radius))
        return cells

    def update(self, area: dict, rows: int, width: int, now: float, dt: float, speed: int) -> None:
        self.ensure(area, rows, width)
        motion = resolve_direction_motion(area, self.widget_name, now)
        cells = area.get(self.state_key("cells")) or []
        if not cells or motion == 0:
            return
        max_dx, max_dy, _source_rows, _source_width, max_radius = self.orbit_geometry(rows, width)
        base_rate = gauge_radians_per_second(speed, widget=self.widget_name) * dt * motion
        updated = []
        radial_step = self.RADIAL_DECAY_PER_SECOND * dt
        outward = radial_step > 0.0
        for dx, dy, phase, glyph, palette_idx, velocity in cells:
            next_phase = (phase + (base_rate * velocity)) % math.tau
            next_dx = dx
            next_dy = dy
            if radial_step != 0.0:
                radius = math.hypot(dx, dy * self.CELL_ASPECT_Y)
                if radius > 0.0:
                    scale = max(0.0, (radius + radial_step) / radius)
                    next_dx = dx * scale
                    next_dy = dy * scale
                else:
                    next_dx, next_dy = self.random_offset(max_dx, max_dy, radius_norm_min=0.10, radius_norm_max=0.18)
            radius_norm = min(1.5, math.hypot(next_dx, next_dy * self.CELL_ASPECT_Y) / max(1.0, max_radius))
            if radius_norm < self.RESPAWN_INNER_RADIUS_NORM or radius_norm > 1.02:
                updated.append(
                    self.respawn_cell(
                        palette_idx,
                        max_dx,
                        max_dy,
                        max_radius,
                        outward=outward,
                        phase=next_phase,
                    )
                )
                continue
            next_velocity = self.velocity_multiplier(min(1.0, radius_norm))
            updated.append((next_dx, next_dy, next_phase, glyph, palette_idx, next_velocity))
        area[self.state_key("cells")] = updated
        if random.random() < self.MUTATION_PROBABILITY:
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
        for dx, dy, phase, glyph, palette_idx, _velocity in area.get(self.state_key("cells")) or []:
            rot_x, rot_y = rotate_offset(dx, dy, phase, cell_aspect_y=self.CELL_ASPECT_Y)
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
