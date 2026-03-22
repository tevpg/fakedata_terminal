#!/usr/bin/env python3

from __future__ import annotations

import unittest
from unittest import mock

from runtime_support import colour_attr_from_spec, make_area_state, normalize_colour_spec
from widgets_image import ImageWidgets


class _FakeCurses:
    A_BOLD = 1
    error = RuntimeError

    @staticmethod
    def color_pair(value: int) -> int:
        return value << 8


class _FakeStdScr:
    def getmaxyx(self) -> tuple[int, int]:
        return (24, 80)

    def addnstr(self, *_args, **_kwargs) -> None:
        return None

    def addch(self, *_args, **_kwargs) -> None:
        return None


class BlankWidgetTests(unittest.TestCase):
    def make_widget(self) -> ImageWidgets:
        return ImageWidgets(
            curses_module=_FakeCurses,
            stdscr=_FakeStdScr(),
            safe_row_width=lambda _y, _r, _x, width: width,
            image_module=None,
            image_paths_getter=lambda: [],
            inject_text_getter=lambda: "",
            life_max_getter=lambda: 50,
            normalize_colour_spec=normalize_colour_spec,
            colour_attr_from_spec=colour_attr_from_spec,
            life_ramp_specs=lambda _spec: ["bright-white", "white", "dim-white"],
            image_colour_cycle=[1, 2, 3],
            image_trail_attrs=[_FakeCurses.color_pair(1)],
        )

    def make_area(self) -> dict:
        area = make_area_state(None, "science", lambda _theme: ([], []))
        area["mode"] = "blank"
        area["text_override"] = "ABCD"
        area["colour_override"] = "multi"
        return area

    def test_blank_multicolour_forward_rotates_visible_character_colours(self) -> None:
        widget = self.make_widget()
        area = self.make_area()
        counter = {"value": 0}

        def cycle_choice(seq):
            picked = seq[counter["value"] % len(seq)]
            counter["value"] += 1
            return picked

        with mock.patch("widgets_image.random.choice", side_effect=cycle_choice):
            widget.update(area, rows=3, width=4, role="main", now=0.0)

        before = area["blank_line_colours"][0][:]
        area["direction_override"] = "forward"
        widget.update(area, rows=3, width=4, role="main", now=1.0)
        after = area["blank_line_colours"][0]
        self.assertEqual(after, [before[-1], *before[:-1]])

    def test_blank_multicolour_none_keeps_visible_character_colours_static(self) -> None:
        widget = self.make_widget()
        area = self.make_area()
        area["direction_override"] = "none"
        widget.update(area, rows=3, width=4, role="main", now=0.0)
        before = area["blank_line_colours"][0][:]
        widget.update(area, rows=3, width=4, role="main", now=1.0)
        self.assertEqual(area["blank_line_colours"][0], before)


if __name__ == "__main__":
    unittest.main()
