"""Matrix widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import density_scale
except ImportError:
    from runtime_support import density_scale


class MatrixWidget:
    def __init__(self, *, curses_module, stdscr, matrix_chars: str):
        self.curses = curses_module
        self.stdscr = stdscr
        self.matrix_chars = matrix_chars

    def update(self, area: dict, rows: int, width: int) -> None:
        density = area.get("density_override")
        baseline = density_scale(density, low=0.02, mid=1.0, high=3.2)
        cols = area["matrix_cols"]
        while len(cols) < width:
            cols.append({
                "head": random.randint(-rows, 0),
                "tail": random.randint(4, max(6, rows // 3)),
                "speed": random.choice([1, 1, 1, 2]),
                "active": random.random() < min(0.92, 0.25 * baseline),
            })
        if len(cols) > width:
            del cols[width:]
        for col in cols:
            if not col["active"]:
                if random.random() < min(0.35, 0.035 * baseline):
                    col["active"] = True
                    col["head"] = random.randint(-rows, 0)
                    col["tail"] = random.randint(4, max(6, rows // 3))
                    col["speed"] = random.choice([1, 1, 2])
                continue
            col["head"] += col["speed"]
            if col["head"] - col["tail"] > rows + random.randint(0, 6):
                col["active"] = False

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        canvas = [[" " for _ in range(width)] for _ in range(rows)]
        attr_map = [[self.curses.color_pair(1) for _ in range(width)] for _ in range(rows)]
        for c, col in enumerate(area["matrix_cols"][:width]):
            if not col["active"]:
                continue
            for r in range(max(0, col["head"] - col["tail"]), min(rows, col["head"] + 1)):
                age = col["head"] - r
                ch = random.choice(self.matrix_chars)
                if age == 0:
                    attr = self.curses.color_pair(2) | self.curses.A_BOLD
                elif age < 3:
                    attr = self.curses.color_pair(6)
                else:
                    attr = self.curses.color_pair(1)
                canvas[r][c] = ch
                attr_map[r][c] = attr
        for r in range(rows):
            for c in range(width):
                try:
                    self.stdscr.addch(y + r, x + c, canvas[r][c], attr_map[r][c])
                except self.curses.error:
                    pass
