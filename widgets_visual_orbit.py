"""Physics-based orbit widget renderer."""

from __future__ import annotations

import math
import random

try:
    from .runtime_support import clamp_density, density_scale, multi_palette_specs
    from .timing_support import gauge_radians_per_second, resolve_direction_motion
    from .widgets_visual_rotation import rotation_field_bounds
except ImportError:
    from runtime_support import clamp_density, density_scale, multi_palette_specs
    from timing_support import gauge_radians_per_second, resolve_direction_motion
    from widgets_visual_rotation import rotation_field_bounds


class OrbitWidget:
    GLYPHS = "αβγδεζηθλμξπρστυφχψωΔΘΛΞΠΣΦΨΩ∂∇∞∑∏∫√≈≠≤≥⊕⊗⊙⊛⊜⊝⊞⊟⊠⊡☉☌☍☿♀♁♂♃♄♅♆♇⚝✦✧·∘"
    CELL_ASPECT_Y = 2.0
    SEED_DIVISOR = 12
    MIN_SEED_COUNT = 12
    MAX_SEED_COUNT = 420
    MUTATION_PROBABILITY = 0.08
    DENSITY_LOW_SCALE = 0.05
    DENSITY_HIGH_SCALE = 1.60
    DIRECTION_EASE_SECONDS = 0.9
    REFERENCE_RADIUS_NORM = 0.34
    SOFTENING_RADIUS_ABS = 1.2
    TURN_STEER_PER_SECOND = 0.40
    RADIAL_DAMPING_PER_SECOND = 0.08
    SPEED_JITTER = 0.10
    INITIAL_RADIUS_MIN_NORM = 0.12
    INITIAL_RADIUS_MAX_NORM = 0.92
    INITIAL_SPEED_MIN_SCALE = 0.35
    INITIAL_SPEED_MAX_SCALE = 1.10
    INITIAL_RADIAL_SPEED_MAX_SCALE = 0.85
    RESPAWN_INNER_RADIUS_ABS = 1.8
    RESPAWN_OUTER_MIN_RADIUS_NORM = 0.72
    RESPAWN_OUTER_MAX_RADIUS_NORM = 0.96
    RADIAL_SPEED_LIMIT_FACTOR = 1.6

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        self.curses = curses_module
        self.stdscr = stdscr
        self.colour_attr_from_spec = colour_attr_from_spec
        self.normalize_colour_spec = normalize_colour_spec

    @staticmethod
    def state_key(suffix: str) -> str:
        return f"orbit_{suffix}"

    def orbit_geometry(self, rows: int, width: int) -> tuple[float, float, int, int, float]:
        max_dx, max_dy, source_rows, source_width = rotation_field_bounds(rows, width, cell_aspect_y=self.CELL_ASPECT_Y)
        max_radius = math.hypot(max_dx, max_dy * self.CELL_ASPECT_Y)
        return max_dx, max_dy, source_rows, source_width, max_radius

    def random_position(
        self,
        max_dx: float,
        max_iso_y: float,
        *,
        radius_norm_min: float,
        radius_norm_max: float,
    ) -> tuple[float, float]:
        lo = max(0.0, min(1.0, radius_norm_min))
        hi = max(lo, min(1.0, radius_norm_max))
        theta = random.uniform(0.0, math.tau)
        radius_norm = random.uniform(lo ** 2, hi ** 2) ** 0.5
        x = math.cos(theta) * max_dx * radius_norm
        y = math.sin(theta) * max_iso_y * radius_norm
        return x, y

    def ensure(self, area: dict, rows: int, width: int) -> None:
        sig = (rows, width, clamp_density(area.get("density_override")))
        if area.get(self.state_key("sig")) == sig and area.get(self.state_key("cells")):
            return
        area[self.state_key("sig")] = sig
        area[self.state_key("cells")] = self.seed_cells(area, rows, width)
        area[self.state_key("motion")] = 1.0
        area[self.state_key("target_motion")] = 1.0

    def circular_speed(self, radius: float, base_omega: float, max_radius: float) -> float:
        reference_radius = max(2.5, max_radius * self.REFERENCE_RADIUS_NORM)
        mu = self.gravity_mu(base_omega, max_radius)
        return math.sqrt(max(0.0, mu) / max(0.5, radius))

    def gravity_mu(self, base_omega: float, max_radius: float) -> float:
        reference_radius = max(2.5, max_radius * self.REFERENCE_RADIUS_NORM)
        return (base_omega ** 2) * (reference_radius ** 3)

    def build_cell(
        self,
        idx: int,
        max_dx: float,
        max_iso_y: float,
        max_radius: float,
        base_omega: float,
        *,
        radius_norm_min: float,
        radius_norm_max: float,
        speed_scale_min: float,
        speed_scale_max: float,
        motion_sign: float = 1.0,
    ) -> tuple[float, float, float, float, str, int]:
        x, y = self.random_position(
            max_dx,
            max_iso_y,
            radius_norm_min=radius_norm_min,
            radius_norm_max=radius_norm_max,
        )
        radius = math.hypot(x, y)
        radial_x = x / max(radius, 0.001)
        radial_y = y / max(radius, 0.001)
        tangent_x = -radial_y
        tangent_y = radial_x
        circular_speed = self.circular_speed(radius, base_omega, max_radius)
        speed_scale = random.uniform(speed_scale_min, speed_scale_max)
        tangential_speed = circular_speed * speed_scale * (1.0 if motion_sign >= 0.0 else -1.0)
        radial_speed = circular_speed * random.uniform(-self.INITIAL_RADIAL_SPEED_MAX_SCALE, self.INITIAL_RADIAL_SPEED_MAX_SCALE)
        vx = (tangent_x * tangential_speed) + (radial_x * radial_speed)
        vy = (tangent_y * tangential_speed) + (radial_y * radial_speed)
        return (x, y, vx, vy, random.choice(self.GLYPHS), idx)

    def seed_cells(self, area: dict, rows: int, width: int) -> list[tuple[float, float, float, float, str, int]]:
        max_dx, max_dy, source_rows, source_width, max_radius = self.orbit_geometry(rows, width)
        max_iso_y = max_dy * self.CELL_ASPECT_Y
        density_multiplier = density_scale(
            area.get("density_override"),
            low=self.DENSITY_LOW_SCALE,
            mid=1.0,
            high=self.DENSITY_HIGH_SCALE,
        )
        count = max(self.MIN_SEED_COUNT, min(self.MAX_SEED_COUNT, int(((source_rows * source_width) // self.SEED_DIVISOR) * density_multiplier)))
        base_omega = gauge_radians_per_second(50, widget="orbit")
        cells = []
        for idx in range(count):
            motion_sign = random.choice((-1.0, 1.0))
            cells.append(
                self.build_cell(
                    idx,
                    max_dx,
                    max_iso_y,
                    max_radius,
                    base_omega,
                    radius_norm_min=self.INITIAL_RADIUS_MIN_NORM,
                    radius_norm_max=self.INITIAL_RADIUS_MAX_NORM,
                    speed_scale_min=self.INITIAL_SPEED_MIN_SCALE,
                    speed_scale_max=self.INITIAL_SPEED_MAX_SCALE,
                    motion_sign=motion_sign,
                )
            )
        return cells

    def respawn_cell(
        self,
        idx: int,
        max_dx: float,
        max_iso_y: float,
        max_radius: float,
        base_omega: float,
        motion_sign: float,
    ) -> tuple[float, float, float, float, str, int]:
        return self.build_cell(
            idx,
            max_dx,
            max_iso_y,
            max_radius,
            base_omega,
            radius_norm_min=self.RESPAWN_OUTER_MIN_RADIUS_NORM,
            radius_norm_max=self.RESPAWN_OUTER_MAX_RADIUS_NORM,
            speed_scale_min=1.0 - self.SPEED_JITTER,
            speed_scale_max=1.0 + self.SPEED_JITTER,
            motion_sign=motion_sign,
        )

    def update(self, area: dict, rows: int, width: int, now: float, dt: float, speed: int) -> None:
        self.ensure(area, rows, width)
        target_motion = float(resolve_direction_motion(area, "orbit", now))
        area[self.state_key("target_motion")] = target_motion
        motion = float(area.get(self.state_key("motion"), target_motion))
        ease_seconds = max(0.001, float(self.DIRECTION_EASE_SECONDS))
        max_step = dt / ease_seconds if dt > 0.0 else 1.0
        delta = target_motion - motion
        if abs(delta) <= max_step:
            motion = target_motion
        else:
            motion += max_step if delta > 0.0 else -max_step
        area[self.state_key("motion")] = motion

        cells = area.get(self.state_key("cells")) or []
        if not cells:
            return

        max_dx, max_dy, _source_rows, _source_width, max_radius = self.orbit_geometry(rows, width)
        max_iso_y = max_dy * self.CELL_ASPECT_Y
        base_omega = gauge_radians_per_second(speed, widget="orbit")
        mu = self.gravity_mu(base_omega, max_radius)
        activity = abs(motion)
        softening = max(0.25, float(self.SOFTENING_RADIUS_ABS))
        softening_sq = softening * softening
        dt_step = dt * activity
        desired_sign = 0.0 if abs(motion) < 0.001 else (1.0 if motion > 0.0 else -1.0)
        inner_limit = max(0.5, float(self.RESPAWN_INNER_RADIUS_ABS))
        outer_limit = max_radius * 1.08
        outer_x_limit = max_dx + 1.0
        outer_y_limit = max_iso_y + self.CELL_ASPECT_Y
        updated = []

        for x, y, vx, vy, glyph, palette_idx in cells:
            radius_sq = (x * x) + (y * y)
            radius = math.sqrt(radius_sq)
            if (
                not math.isfinite(radius)
                or radius < inner_limit
                or radius > outer_limit
                or abs(x) > outer_x_limit
                or abs(y) > outer_y_limit
            ):
                updated.append(self.respawn_cell(palette_idx, max_dx, max_iso_y, max_radius, base_omega, desired_sign or 1.0))
                continue

            if dt_step > 0.0:
                inv_r3 = 1.0 / ((radius_sq + softening_sq) * math.sqrt(radius_sq + softening_sq))
                ax = -x * mu * inv_r3
                ay = -y * mu * inv_r3

                radial_x = x / max(radius, 0.001)
                radial_y = y / max(radius, 0.001)
                tangent_x = -radial_y
                tangent_y = radial_x
                tangential_speed = (vx * tangent_x) + (vy * tangent_y)
                radial_speed = (vx * radial_x) + (vy * radial_y)
                target_tangential_speed = desired_sign * self.circular_speed(radius, base_omega, max_radius)
                steer_strength = min(1.0, dt_step * self.TURN_STEER_PER_SECOND)
                tangential_speed += (target_tangential_speed - tangential_speed) * steer_strength
                radial_speed *= max(0.0, 1.0 - (dt_step * self.RADIAL_DAMPING_PER_SECOND))
                radial_limit = target_tangential_speed if target_tangential_speed > 0.0 else self.circular_speed(radius, base_omega, max_radius)
                radial_speed = max(-radial_limit * self.RADIAL_SPEED_LIMIT_FACTOR, min(radial_limit * self.RADIAL_SPEED_LIMIT_FACTOR, radial_speed))
                vx = (tangent_x * tangential_speed) + (radial_x * radial_speed)
                vy = (tangent_y * tangential_speed) + (radial_y * radial_speed)
                vx += ax * dt_step
                vy += ay * dt_step
                x += vx * dt_step
                y += vy * dt_step

            next_radius = math.hypot(x, y)
            if (
                not math.isfinite(next_radius)
                or next_radius < inner_limit
                or next_radius > outer_limit
                or abs(x) > outer_x_limit
                or abs(y) > outer_y_limit
            ):
                updated.append(self.respawn_cell(palette_idx, max_dx, max_iso_y, max_radius, base_omega, desired_sign or 1.0))
                continue
            updated.append((x, y, vx, vy, glyph, palette_idx))

        area[self.state_key("cells")] = updated
        if updated and random.random() < self.MUTATION_PROBABILITY:
            idx = random.randrange(len(updated))
            x, y, vx, vy, _old_glyph, palette_idx = updated[idx]
            updated[idx] = (x, y, vx, vy, random.choice(self.GLYPHS), palette_idx)

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
        for row in range(rows):
            try:
                self.stdscr.addnstr(y + row, x, " " * width, width, blank_attr)
            except self.curses.error:
                pass

        cx = (width - 1) / 2.0
        cy = (rows - 1) / 2.0
        occupied: set[tuple[int, int]] = set()
        for iso_x, iso_y, _vx, _vy, glyph, palette_idx in area.get(self.state_key("cells")) or []:
            col = int(round(cx + iso_x))
            row = int(round(cy + (iso_y / self.CELL_ASPECT_Y)))
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
