"""Title-card widget renderer."""

from __future__ import annotations

import random

try:
    import pyfiglet
except ImportError:
    pyfiglet = None

try:
    from .runtime_support import multi_palette_specs
except ImportError:
    from runtime_support import multi_palette_specs


PYFIGLET_FONTS = ("banner", "big", "standard", "small")


class TitleCardWidget:
    def __init__(self, *, curses_module, stdscr, colour_attr_from_spec, normalize_colour_spec):
        self.curses = curses_module
        self.stdscr = stdscr
        self.colour_attr_from_spec = colour_attr_from_spec
        self.normalize_colour_spec = normalize_colour_spec

    def blink_durations(self, speed: int) -> tuple[float | None, float | None]:
        clamped = max(1, min(100, int(speed)))
        if clamped <= 1:
            return None, None
        if clamped <= 50:
            progress = (clamped - 2) / 48.0
            max_on = 24.0
            min_on = 0.5
            on_seconds = max_on * ((min_on / max_on) ** max(0.0, min(1.0, progress)))
            return on_seconds, 0.5
        progress = (clamped - 51) / 49.0
        duration = 0.5 + ((0.05 - 0.5) * max(0.0, min(1.0, progress)))
        return duration, duration

    def update(self, area: dict, now: float, speed: int) -> None:
        on_seconds, off_seconds = self.blink_durations(speed)
        if on_seconds is None or off_seconds is None:
            area[self.state_key("lit")] = True
            area[self.state_key("next_toggle")] = None
            return
        lit = area.get(self.state_key("lit"))
        next_toggle = area.get(self.state_key("next_toggle"))
        if lit is None or next_toggle is None:
            area[self.state_key("lit")] = True
            area[self.state_key("next_toggle")] = now + on_seconds
            return
        lit = bool(lit)
        next_toggle = float(next_toggle)
        transitioned_on = False
        while now >= next_toggle:
            lit = not lit
            if lit:
                next_toggle += on_seconds
                transitioned_on = True
            else:
                next_toggle += off_seconds
        area[self.state_key("lit")] = lit
        area[self.state_key("next_toggle")] = next_toggle
        if transitioned_on:
            area.pop(self.state_key("render_sig"), None)
            area.pop(self.state_key("attrs"), None)

    @staticmethod
    def state_key(suffix: str) -> str:
        return f"title_card_{suffix}"

    @staticmethod
    def _resolved_text(area: dict) -> str:
        text = area.get("text_override")
        if text is None:
            return ""
        return str(text).replace("\\n", "\n").upper()

    @staticmethod
    def _rendered_size(lines: list[str]) -> tuple[int, int]:
        if not lines:
            return 0, 0
        return len(lines), max((len(line) for line in lines), default=0)

    def _render_pyfiglet_lines(self, text: str, font_name: str) -> list[str]:
        if pyfiglet is None:
            return []
        figlet = pyfiglet.Figlet(font=font_name, justify="center")
        rendered = figlet.renderText(text).rstrip("\n")
        return rendered.splitlines()

    def _best_rendered_lines(self, text: str, rows: int, width: int) -> list[str]:
        fitting: list[tuple[int, int, int, list[str]]] = []
        for font_name in PYFIGLET_FONTS:
            try:
                candidate = self._render_pyfiglet_lines(text, font_name)
            except Exception:
                continue
            render_rows, render_width = self._rendered_size(candidate)
            if render_rows <= rows and render_width <= width:
                fitting.append((render_rows * render_width, render_rows, render_width, candidate))
        if fitting:
            fitting.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
            return fitting[0][3]
        for font_name in reversed(PYFIGLET_FONTS):
            try:
                candidate = self._render_pyfiglet_lines(text, font_name)
                if candidate:
                    return candidate
            except Exception:
                continue
        return []

    def _palette(self, colour_spec: str) -> list[int]:
        multi_specs = multi_palette_specs(colour_spec, bare_multi="multi-bright")
        palette = [
            self.colour_attr_from_spec(self.curses, spec, default=spec, bold=True)
            for spec in multi_specs
        ]
        if not palette:
            palette = [self.colour_attr_from_spec(self.curses, "bright-green", default="bright-green", bold=True)]
        return palette

    def _stable_attrs(self, area: dict, rendered: list[str], palette: list[int], multi_mode: bool) -> dict[tuple[int, int], int]:
        render_sig = (tuple(rendered), tuple(palette), multi_mode)
        if area.get(self.state_key("render_sig")) == render_sig:
            cached = area.get(self.state_key("attrs"))
            if isinstance(cached, dict):
                return cached
        attrs: dict[tuple[int, int], int] = {}
        if multi_mode:
            for row_index, line in enumerate(rendered):
                for col_index, ch in enumerate(line):
                    if ch == " ":
                        continue
                    attrs[(row_index, col_index)] = random.choice(palette)
        else:
            single_attr = palette[0]
            for row_index, line in enumerate(rendered):
                for col_index, ch in enumerate(line):
                    if ch == " ":
                        continue
                    attrs[(row_index, col_index)] = single_attr
        area[self.state_key("render_sig")] = render_sig
        area[self.state_key("attrs")] = attrs
        return attrs

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        blank = " " * width
        blank_attr = self.curses.color_pair(1)
        for row in range(rows):
            try:
                self.stdscr.addnstr(y + row, x, blank, width, blank_attr)
            except self.curses.error:
                pass

        if not area.get(self.state_key("lit"), True):
            return

        text = self._resolved_text(area)
        if not text:
            return

        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "bright-green"
        palette = self._palette(colour_spec)
        multi_mode = colour_spec in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"}

        rendered = self._best_rendered_lines(text, rows, width)
        if not rendered:
            return
        attrs = self._stable_attrs(area, rendered, palette, multi_mode)
        render_rows, render_width = self._rendered_size(rendered)
        start_row = max(0, (rows - render_rows) // 2)
        start_col = max(0, (width - render_width) // 2)

        for row_index, line in enumerate(rendered):
            draw_row = start_row + row_index
            if draw_row < 0 or draw_row >= rows:
                continue
            for col_index, ch in enumerate(line):
                if ch == " ":
                    continue
                draw_col = start_col + col_index
                if draw_col < 0 or draw_col >= width:
                    continue
                attr = attrs[(row_index, col_index)]
                try:
                    self.stdscr.addch(y + draw_row, x + draw_col, ch, attr)
                except self.curses.error:
                    pass
