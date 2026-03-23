#!/usr/bin/env python3

from __future__ import annotations

import unittest
from unittest import mock

import widgets_visual_title_card
from widgets_visual_title_card import TitleCardWidget


class _DummyCurses:
    COLOR_BLACK = 0
    A_BOLD = 0

    @staticmethod
    def color_pair(_index: int) -> int:
        return 0


class _DummyStdScr:
    pass


def _make_widget() -> TitleCardWidget:
    return TitleCardWidget(
        curses_module=_DummyCurses(),
        stdscr=_DummyStdScr(),
        colour_attr_from_spec=lambda *args, **kwargs: 0,
        normalize_colour_spec=lambda value: value,
    )


class TitleCardWidgetTests(unittest.TestCase):
    def test_render_pyfiglet_lines_trims_shared_left_padding(self) -> None:
        class _FakeFiglet:
            def __init__(self, font: str, justify: str):
                self.font = font
                self.justify = justify

            def renderText(self, text: str) -> str:
                self.last_text = text
                return "   ABC\n   DEF\n"

        fake_module = type("FakePyfiglet", (), {"Figlet": _FakeFiglet})
        widget = _make_widget()
        with mock.patch.object(widgets_visual_title_card, "pyfiglet", fake_module):
            self.assertEqual(widget._render_pyfiglet_lines("HELLO", "standard"), ["ABC", "DEF"])

    def test_best_rendered_lines_prefers_unsplit_direct_render_when_it_fits(self) -> None:
        widget = _make_widget()
        with mock.patch.object(widget, "_render_pyfiglet_lines", side_effect=lambda text, _font: [text]):
            with mock.patch.object(widget, "_render_wrapped_pyfiglet", return_value=["MISSIO", "N"]):
                rendered = widget._best_rendered_lines("MISSION", rows=5, width=7)
        self.assertEqual(rendered, ["MISSION"])


if __name__ == "__main__":
    unittest.main()
