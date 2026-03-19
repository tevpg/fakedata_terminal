"""Visual widget helpers for FakeData Terminal."""

from __future__ import annotations

import math
import random

try:
    from .runtime_support import COLOUR_PAIR_INDICES, blocks_palette_specs
    from .timing_support import resolve_direction_motion as resolve_shared_direction_motion
    from .widgets_visual_blocks import BlocksWidget
    from .widgets_visual_crash import CrashWidget
    from .widgets_visual_gauge import GaugeWidget
    from .widgets_visual_matrix import MatrixWidget
    from .widgets_visual_scope import ScopeWidget
    from .widgets_visual_sweep import SweepWidget
    from .widgets_visual_tunnel import TunnelWidget
    from .vocab import _build_pools
except ImportError:
    from runtime_support import COLOUR_PAIR_INDICES, blocks_palette_specs
    from timing_support import resolve_direction_motion as resolve_shared_direction_motion
    from widgets_visual_blocks import BlocksWidget
    from widgets_visual_crash import CrashWidget
    from widgets_visual_gauge import GaugeWidget
    from widgets_visual_matrix import MatrixWidget
    from widgets_visual_scope import ScopeWidget
    from widgets_visual_sweep import SweepWidget
    from widgets_visual_tunnel import TunnelWidget
    from vocab import _build_pools


class VisualWidgets:
    VISUAL_MODES = {"bars", "crash", "gauge", "matrix", "blocks", "sweep", "tunnel", "scope"}

    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        leading_blank,
        inject_text_getter,
        area_theme,
        get_gauge_config,
        normalize_colour_spec,
        colour_attr_from_spec,
        matrix_chars: str,
        sweep_symbols: str,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.leading_blank = leading_blank
        self.inject_text_getter = inject_text_getter
        self.area_theme = area_theme
        self.get_gauge_config = get_gauge_config
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.matrix_chars = matrix_chars
        self.sweep_symbols = sweep_symbols
        self.blocks_widget = BlocksWidget(
            curses_module=curses_module,
            stdscr=stdscr,
            normalize_colour_spec=normalize_colour_spec,
            blocks_palette_specs=blocks_palette_specs,
            colour_pair_indices=COLOUR_PAIR_INDICES,
        )
        self.crash_widget = CrashWidget(
            curses_module=curses_module,
            stdscr=stdscr,
            safe_row_width=safe_row_width,
            area_theme=area_theme,
            build_pools=_build_pools,
            normalize_colour_spec=normalize_colour_spec,
            colour_attr_from_spec=colour_attr_from_spec,
        )
        self.gauge_widget = GaugeWidget(
            curses_module=curses_module,
            stdscr=stdscr,
            normalize_colour_spec=normalize_colour_spec,
            colour_attr_from_spec=colour_attr_from_spec,
            draw_centered_overlay_to_canvas=self.draw_centered_overlay_to_canvas,
        )
        self.matrix_widget = MatrixWidget(curses_module=curses_module, stdscr=stdscr, matrix_chars=matrix_chars)
        self.scope_widget = ScopeWidget(
            curses_module=curses_module,
            stdscr=stdscr,
            safe_row_width=safe_row_width,
            draw_centered_overlay=self.draw_centered_overlay,
            area_theme=area_theme,
            get_gauge_config=get_gauge_config,
            resolved_direction_motion=self.resolved_direction_motion,
        )
        self.sweep_widget = SweepWidget(curses_module=curses_module, stdscr=stdscr, sweep_symbols=sweep_symbols)
        self.tunnel_widget = TunnelWidget(
            curses_module=curses_module,
            normalize_colour_spec=normalize_colour_spec,
            colour_attr_from_spec=colour_attr_from_spec,
            resolved_direction_motion=self.resolved_direction_motion,
            repaint_nested_layers=self.repaint_nested_layers,
            draw_centered_overlay=self.draw_centered_overlay,
            build_tunnel_layers=self.build_tunnel_layers,
        )

    def overlay_text(self, area: dict) -> str:
        text = area.get("text_override") or self.inject_text_getter()
        if not text:
            return ""
        return str(text).replace("\\n", "\n")

    def draw_centered_overlay(self, area: dict, row: int, y: int, x: int, width: int, *,
                              rows: int | None = None, anchor: str = "center"):
        overlay = self.overlay_text(area)
        if not overlay:
            return
        if row < 0:
            return
        lines = overlay.splitlines() or [overlay]
        if rows is None:
            rows = row + len(lines)
        if anchor == "top":
            start_row = row
        elif anchor == "bottom":
            start_row = row - len(lines) + 1
        else:
            start_row = row - ((len(lines) - 1) // 2)
        start_row = max(0, min(start_row, max(0, rows - len(lines))))
        for idx, source in enumerate(lines):
            draw_row = start_row + idx
            if draw_row < 0 or draw_row >= rows:
                continue
            safe_w = self.safe_row_width(y, draw_row, x, width)
            if safe_w <= 0:
                continue
            draw = source[:safe_w]
            start_x = x + max(0, (safe_w - len(draw)) // 2)
            try:
                self.stdscr.addnstr(
                    y + draw_row,
                    start_x,
                    draw,
                    min(len(draw), safe_w),
                    self.curses.color_pair(2) | self.curses.A_BOLD,
                )
            except self.curses.error:
                pass

    def draw_centered_overlay_to_canvas(self, area: dict, row: int, width: int, canvas, attrs, *,
                                        rows: int | None = None, anchor: str = "center"):
        overlay = self.overlay_text(area)
        if not overlay or row < 0:
            return
        lines = overlay.splitlines() or [overlay]
        if rows is None:
            rows = row + len(lines)
        if anchor == "top":
            start_row = row
        elif anchor == "bottom":
            start_row = row - len(lines) + 1
        else:
            start_row = row - ((len(lines) - 1) // 2)
        start_row = max(0, min(start_row, max(0, rows - len(lines))))
        overlay_attr = self.curses.color_pair(2) | self.curses.A_BOLD
        for idx, source in enumerate(lines):
            draw_row = start_row + idx
            if draw_row < 0 or draw_row >= rows:
                continue
            safe_w = min(width, len(canvas[draw_row]), len(attrs[draw_row]))
            if safe_w <= 0:
                continue
            draw = source[:safe_w]
            start_col = max(0, (safe_w - len(draw)) // 2)
            for offset, ch in enumerate(draw):
                col = start_col + offset
                if col >= safe_w:
                    break
                canvas[draw_row][col] = ch
                attrs[draw_row][col] = overlay_attr

    def update_scope(self, area: dict, width: int, now: float):
        self.scope_widget.update(area, width, now)

    def resolved_direction_motion(self, area: dict, *, now: float | None = None) -> int:
        current = 0.0 if now is None else now
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        return resolve_shared_direction_motion(area, mode, current)

    def repaint_scope(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.scope_widget.render(area, nrows, y, x, width)

    def update_bars(self, area: dict):
        for i in range(len(area["bars_values"])):
            area["bars_drift"][i] += random.gauss(0, 0.035)
            area["bars_drift"][i] *= 0.72
            if random.random() < 0.08:
                area["bars_drift"][i] += random.choice([-1, 1]) * random.uniform(0.10, 0.22)
            area["bars_values"][i] = max(0.02, min(0.99, area["bars_values"][i] + area["bars_drift"][i]))

    def repaint_bars(self, area: dict, nrows: int, y: int, x: int, width: int):
        blank = " " * width
        meter_w = max(8, width - 18)
        for r in range(nrows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
            except self.curses.error:
                pass
            if r % 5 == 0:
                label = random.choice(area["bars_headers"])
                line = f"[ {label} ]".center(width, "─")
                attr = self.curses.color_pair(3) | self.curses.A_DIM
            else:
                idx = (r - (area["tick"] // 2)) % len(area["bars_labels"])
                value = area["bars_values"][idx]
                filled = int(value * meter_w)
                bar = "█" * filled + "·" * (meter_w - filled)
                line = f"{area['bars_labels'][idx]:<7s} [{bar}] {int(value * 100):3d}%"
                attr = (self.curses.color_pair(5) | self.curses.A_BOLD) if value > 0.78 else (
                    self.curses.color_pair(3) if value > 0.48 else self.curses.color_pair(6)
                )
            line = self.leading_blank(line, width)
            try:
                self.stdscr.addnstr(y + r, x, line[:safe_w].ljust(safe_w), safe_w, attr)
            except self.curses.error:
                pass

    def update_matrix(self, area: dict, nrows: int, width: int):
        self.matrix_widget.update(area, nrows, width)

    def repaint_matrix(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.matrix_widget.render(area, nrows, y, x, width)

    def update_gauge(self, area: dict, now: float, dt: float, speed: int):
        self.gauge_widget.update(area, now, dt, speed)

    def repaint_gauge(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.gauge_widget.render(area, nrows, y, x, width)

    def ensure_crash(self, area: dict, rows: int, width: int):
        self.crash_widget.ensure(area, rows, width)

    def update_crash(self, area: dict, rows: int, width: int):
        self.crash_widget.update(area, rows, width)

    def repaint_crash(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.crash_widget.render(area, nrows, y, x, width)

    def ensure_blocks(self, area: dict, rows: int, width: int):
        self.blocks_widget.ensure(area, rows, width)

    def update_blocks(self, area: dict, rows: int, width: int):
        self.blocks_widget.update(area, rows, width)

    def repaint_blocks(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.blocks_widget.render(area, nrows, y, x, width)

    @staticmethod
    def build_nested_box_layers(rows: int, width: int, side_border_width: int = 1):
        layers = []
        inset_y = 0
        inset_x = 0
        step_x = max(1, side_border_width)
        while True:
            top = inset_y
            left = inset_x
            bottom = rows - 1 - inset_y
            right = width - 1 - inset_x
            if top > bottom or left > right:
                break
            cells = []
            for c in range(left + 1, right):
                cells.append((top, c, "─"))
            for r in range(top + 1, bottom):
                cells.append((r, right, "│"))
            if bottom > top:
                for c in range(right - 1, left, -1):
                    cells.append((bottom, c, "─"))
            if right > left:
                for r in range(bottom - 1, top, -1):
                    cells.append((r, left, "│"))
            if top == bottom and left == right:
                cells.append((top, left, "•"))
            elif top == bottom:
                for c in range(left, right + 1):
                    cells.append((top, c, "─"))
            elif left == right:
                for r in range(top, bottom + 1):
                    cells.append((r, left, "│"))
            else:
                cells.extend([(top, left, "┌"), (top, right, "┐"), (bottom, left, "└"), (bottom, right, "┘")])
            layers.append(cells)
            inset_y += 1
            inset_x += step_x
        return layers

    def build_tunnel_layers(self, rows: int, width: int):
        return self.build_nested_box_layers(rows, width, side_border_width=2)

    def ensure_tunnel(self, area: dict, rows: int, width: int):
        self.tunnel_widget.ensure(area, rows, width)

    def repaint_nested_layers(self, layers, area: dict, rows: int, y: int, x: int, width: int, attr_for_band=None,
                              outward: bool = True):
        blank = " " * width
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
            except self.curses.error:
                pass
        if not layers:
            return
        cadence = 4
        cycle_step = area["tick"] // cadence
        phase = cycle_step % cadence
        ordered_layers = list(reversed(layers)) if outward else list(layers)
        for inner_offset, layer in enumerate(ordered_layers):
            if (inner_offset - phase) % cadence != 0:
                continue
            band_idx = (inner_offset - cycle_step) // cadence
            attr = attr_for_band(band_idx) if attr_for_band is not None else (self.curses.color_pair(6) | self.curses.A_BOLD)
            for rr, cc, ch in layer:
                if 0 <= rr < rows and 0 <= cc < width:
                    try:
                        self.stdscr.addch(y + rr, x + cc, ch, attr)
                    except self.curses.error:
                        pass

    def ensure_sweep(self, area: dict, rows: int, width: int):
        self.sweep_widget.ensure(area, rows, width)

    @staticmethod
    def sweep_vertical(rows: int, width: int) -> bool:
        # Terminal cells are typically about twice as tall as they are wide, so a
        # panel looks roughly square around a 2:1 width:height ratio.
        return SweepWidget.vertical(rows, width)

    def update_sweep(self, area: dict, rows: int, width: int, role: str):
        del role
        self.sweep_widget.update(area, rows, width)

    def repaint_sweep(self, area: dict, nrows: int, y: int, x: int, width: int, role: str):
        del role
        self.sweep_widget.render(area, nrows, y, x, width)

    def update_tunnel(self, area: dict, rows: int, width: int, now: float):
        self.tunnel_widget.update(area, rows, width, now)

    def repaint_tunnel(self, area: dict, rows: int, y: int, x: int, width: int):
        self.tunnel_widget.render(area, rows, y, x, width)

    def handles_mode(self, mode: str) -> bool:
        return mode in self.VISUAL_MODES

    def ensure(self, area: dict, rows: int, width: int, role: str, now: float | None = None) -> None:
        del role
        now = 0.0 if now is None else now
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "blocks":
            self.ensure_blocks(area, rows, width)
            if not area["blocks_warmed"]:
                for _ in range(max(12, min(36, rows * 3))):
                    self.update_blocks(area, rows, width)
                area["blocks_warmed"] = True
        elif mode == "crash":
            self.ensure_crash(area, rows, width)
        elif mode == "sweep":
            self.ensure_sweep(area, rows, width)
        elif mode == "tunnel":
            self.ensure_tunnel(area, rows, width)
        elif mode == "scope" and not area["scope_warmed"]:
            for _ in range(max(24, width + 24)):
                self.update_scope(area, width, now)
            area["scope_warmed"] = True
        elif mode == "matrix" and not area["matrix_warmed"]:
            for _ in range(max(18, rows * 3)):
                self.update_matrix(area, rows, width)
            area["matrix_warmed"] = True
        elif mode == "sweep" and not area["sweep_warmed"]:
            self.update_sweep(area, rows, width, area.get("role", "main"))
            area["sweep_warmed"] = True

    def update(self, area: dict, rows: int, width: int, role: str, now: float, dt: float, speed: int) -> None:
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "bars":
            self.update_bars(area)
        elif mode == "crash":
            self.update_crash(area, rows, width)
        elif mode == "gauge":
            self.update_gauge(area, now, dt, speed)
        elif mode == "matrix":
            self.update_matrix(area, rows, width)
        elif mode == "blocks":
            self.update_blocks(area, rows, width)
        elif mode == "sweep":
            self.update_sweep(area, rows, width, role)
        elif mode == "tunnel":
            self.update_tunnel(area, rows, width, now)
        elif mode == "scope":
            self.update_scope(area, width, now)

    def render(self, area: dict, rows: int, y: int, x: int, width: int, role: str) -> None:
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "bars":
            self.repaint_bars(area, rows, y, x, width)
        elif mode == "crash":
            self.repaint_crash(area, rows, y, x, width)
        elif mode == "gauge":
            self.repaint_gauge(area, rows, y, x, width)
        elif mode == "matrix":
            self.repaint_matrix(area, rows, y, x, width)
        elif mode == "blocks":
            self.repaint_blocks(area, rows, y, x, width)
        elif mode == "sweep":
            self.repaint_sweep(area, rows, y, x, width, role)
        elif mode == "tunnel":
            self.repaint_tunnel(area, rows, y, x, width)
        elif mode == "scope":
            self.repaint_scope(area, rows, y, x, width)
