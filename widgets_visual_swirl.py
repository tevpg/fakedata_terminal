"""Spiral widget renderer."""

from __future__ import annotations

try:
    from .widgets_visual_rotation import RotationFieldWidget
except ImportError:
    from widgets_visual_rotation import RotationFieldWidget


class SpiralWidget(RotationFieldWidget):
    # Inward spiral: differential rotation plus steady radial decay toward centre.
    ROTATION_FACTOR = 1.0
    FALLOFF_EXPONENT = 0.45
    DIFFERENTIAL_BASE = 0.60
    DIFFERENTIAL_SPREAD = 2.40
    RADIAL_DECAY_PER_RADIAN = -80
    RADIAL_DECAY_USES_TARGET_MOTION = True
    RESPAWN_INNER_RADIUS_ABS = 1.8

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        super().__init__(
            curses_module=curses_module,
            stdscr=stdscr,
            colour_attr_from_spec=colour_attr_from_spec,
            normalize_colour_spec=normalize_colour_spec,
            widget_name="spiral",
            state_prefix="spiral",
        )
