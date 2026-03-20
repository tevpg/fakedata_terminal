"""Whorl widget renderer."""

from __future__ import annotations

try:
    from .widgets_visual_rotation import RotationFieldWidget
except ImportError:
    from widgets_visual_rotation import RotationFieldWidget


class WhorlWidget(RotationFieldWidget):
    # Stable rotating cloud: strong radius-based speed variation, no radial drift.
    ROTATION_FACTOR = 1.0
    FALLOFF_EXPONENT = 3.8
    DIFFERENTIAL_BASE = 0.03
    DIFFERENTIAL_SPREAD = 4.20

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        super().__init__(
            curses_module=curses_module,
            stdscr=stdscr,
            colour_attr_from_spec=colour_attr_from_spec,
            normalize_colour_spec=normalize_colour_spec,
            widget_name="whorl",
            state_prefix="whorl",
        )
