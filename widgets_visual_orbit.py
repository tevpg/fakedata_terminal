"""Shared orbit math helpers for rotate/swirl-style visual widgets."""

from __future__ import annotations

import math


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
