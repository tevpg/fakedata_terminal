"""Sweep widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import density_scale
except ImportError:
    from runtime_support import density_scale


class SweepWidget:
    def __init__(self, *, curses_module, stdscr, sweep_symbols: str):
        self.curses = curses_module
        self.stdscr = stdscr
        self.sweep_symbols = sweep_symbols

    def ensure(self, area: dict, rows: int, width: int) -> None:
        cells = area["sweep_cells"]
        density_multiplier = density_scale(area.get("density_override"), low=0.03, mid=1.0, high=2.4)
        while len(cells) < rows:
            cells.append([(" ", 1)] * width)
        if len(cells) > rows:
            del cells[rows:]
        for r in range(rows):
            row = cells[r]
            if len(row) < width:
                row.extend([(" ", 1)] * (width - len(row)))
            elif len(row) > width:
                del row[width:]
        if area["tick"] == 0:
            palette = [2, 3, 6, 7]
            for r in range(rows):
                for c in range(width):
                    if random.random() < min(0.35, 0.02 * density_multiplier):
                        cells[r][c] = (random.choice(self.sweep_symbols), random.choice(palette))

    @staticmethod
    def vertical(rows: int, width: int) -> bool:
        return width <= rows * 2

    def update(self, area: dict, rows: int, width: int) -> None:
        self.ensure(area, rows, width)
        cells = area["sweep_cells"]
        mono_density_multiplier = density_scale(area.get("density_override"), low=0.03, mid=1.0, high=2.4)
        multi_density_multiplier = density_scale(area.get("density_override"), low=0.03, mid=1.0, high=4.8)

        def drop_symbol(base_cp, spawn_prob: float):
            if random.random() >= spawn_prob:
                return (" ", 1)
            cp = random.choice(base_cp) if isinstance(base_cp, (list, tuple)) else base_cp
            return (random.choice(self.sweep_symbols), cp)

        if not self.vertical(rows, width):
            span = max(1, width)
            head_max = max(0, span - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(span, pos + 3))}
            tail_cols = [pos - 2, pos - 1] if area["sweep_dir"] > 0 else [pos + 3, pos + 4]
            wake_cp = 4 if area["sweep_dir"] > 0 else [2, 3, 6, 7]
            spawn_prob = (0.01 if area["sweep_dir"] > 0 else 0.02) * (
                mono_density_multiplier if area["sweep_dir"] > 0 else multi_density_multiplier
            )
            for r in range(rows):
                for c in head_cols:
                    cells[r][c] = (" ", 1)
                for c in tail_cols:
                    if 0 <= c < span:
                        cells[r][c] = drop_symbol(wake_cp, spawn_prob)
            next_pos = pos + area["sweep_dir"]
            if next_pos < 0 or next_pos > head_max:
                area["sweep_dir"] *= -1
                next_pos = max(0, min(head_max, pos + area["sweep_dir"]))
            area["sweep_pos"] = next_pos
        else:
            span = max(1, rows)
            pos = max(0, min(span - 1, area["sweep_pos"]))
            wake_cp = 4 if area["sweep_dir"] > 0 else [2, 3, 6, 7]
            spawn_prob = (0.01 if area["sweep_dir"] > 0 else 0.02) * (
                mono_density_multiplier if area["sweep_dir"] > 0 else multi_density_multiplier
            )
            for c in range(width):
                cells[pos][c] = (" ", 1)
            for wake_row in [r for r in range(pos - 2 * area["sweep_dir"], pos, area["sweep_dir"])]:
                if 0 <= wake_row < span:
                    for c in range(width):
                        cells[wake_row][c] = drop_symbol(wake_cp, spawn_prob)
            next_pos = pos + area["sweep_dir"]
            if next_pos < 0 or next_pos >= span:
                area["sweep_dir"] *= -1
                next_pos = max(0, min(span - 1, pos + area["sweep_dir"]))
            area["sweep_pos"] = next_pos

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        sweep_attr = self.curses.color_pair(1)
        trail_attr = self.curses.color_pair(1) | self.curses.A_DIM
        if not self.vertical(rows, width):
            head_max = max(0, width - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(width, pos + 3))}
            tail_cols = ({c for c in [pos - 2, pos - 1] if 0 <= c < width} if area["sweep_dir"] > 0 else
                         {c for c in [pos + 3, pos + 4] if 0 <= c < width})
            for r in range(rows):
                for c in range(width):
                    if c in head_cols:
                        ch, attr = "█", sweep_attr
                    elif c in tail_cols:
                        ch, attr = "█", trail_attr
                    else:
                        sym, cp = area["sweep_cells"][r][c]
                        ch, attr = (sym, self.curses.color_pair(cp) | self.curses.A_BOLD) if sym != " " else (" ", self.curses.color_pair(1))
                    try:
                        self.stdscr.addch(y + r, x + c, ch, attr)
                    except self.curses.error:
                        pass
        else:
            pos = max(0, min(rows - 1, area["sweep_pos"]))
            tail_rows = {r for r in range(pos - 2 * area["sweep_dir"], pos, area["sweep_dir"]) if 0 <= r < rows}
            for r in range(rows):
                for c in range(width):
                    if r == pos:
                        ch, attr = "█", sweep_attr
                    elif r in tail_rows:
                        ch, attr = "█", trail_attr
                    else:
                        sym, cp = area["sweep_cells"][r][c]
                        ch, attr = (sym, self.curses.color_pair(cp) | self.curses.A_BOLD) if sym != " " else (" ", self.curses.color_pair(1))
                    try:
                        self.stdscr.addch(y + r, x + c, ch, attr)
                    except self.curses.error:
                        pass
