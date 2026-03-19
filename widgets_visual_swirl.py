"""Swirl widget renderer."""

from __future__ import annotations

try:
    from .widgets_visual_orbit import OrbitalFieldWidget
except ImportError:
    from widgets_visual_orbit import OrbitalFieldWidget


class SwirlWidget(OrbitalFieldWidget):
    # Inward spiral: differential orbit plus steady radial decay toward centre.
    ORBIT_FACTOR = 1.0
    FALLOFF_EXPONENT = 0.45
    DIFFERENTIAL_BASE = 0.60
    DIFFERENTIAL_SPREAD = 2.40
    RADIAL_DECAY_PER_SECOND = -100

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        super().__init__(
            curses_module=curses_module,
            stdscr=stdscr,
            colour_attr_from_spec=colour_attr_from_spec,
            normalize_colour_spec=normalize_colour_spec,
            widget_name="swirl",
            state_prefix="swirl",
        )
