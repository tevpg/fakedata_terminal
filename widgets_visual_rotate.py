"""Rotate widget renderer."""

from __future__ import annotations

try:
    from .widgets_visual_rotation import RotationFieldWidget
except ImportError:
    from widgets_visual_rotation import RotationFieldWidget


class RotateWidget(RotationFieldWidget):
    # Rigid rotating plate: no radius-based speed variation, no random phase.
    ROTATION_FACTOR = 0.0
    RANDOM_INITIAL_PHASE = False
    RIGID_SPEED_MULTIPLIER = 1.0

    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        super().__init__(
            curses_module=curses_module,
            stdscr=stdscr,
            colour_attr_from_spec=colour_attr_from_spec,
            normalize_colour_spec=normalize_colour_spec,
            widget_name="rotate",
            state_prefix="rotate",
        )
