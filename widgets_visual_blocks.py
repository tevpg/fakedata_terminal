"""Blocks widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

BLACK_BLOCK_PROBABILITY = 0.65
BLOCK_COLOUR_INDICES = tuple(range(1, 15))


class BlocksWidget:
    def __init__(self, *, curses_module, stdscr):
        self.curses = curses_module
        self.stdscr = stdscr

    def ensure(self, area: dict, rows: int, width: int) -> None:
        bg = area["blocks_bg"]
        cells = area["blocks_cells"]
        while len(cells) < rows:
            cells.append([bg] * width)
        if len(cells) > rows:
            del cells[rows:]
        for r in range(rows):
            row = cells[r]
            if len(row) < width:
                row.extend([bg] * (width - len(row)))
            elif len(row) > width:
                del row[width:]

    def update(self, area: dict, rows: int, width: int) -> None:
        self.ensure(area, rows, width)
        cells = area["blocks_cells"]
        rect_count = random.randint(1, 3)
        palette = [cp for cp in BLOCK_COLOUR_INDICES if cp != area["blocks_bg"]]
        for _ in range(rect_count):
            rh = random.randint(1, max(1, rows // 3))
            rw = random.randint(2, max(2, width // 3))
            r0 = random.randint(0, max(0, rows - rh))
            c0 = random.randint(0, max(0, width - rw))
            cp = 0 if random.random() < BLACK_BLOCK_PROBABILITY else random.choice(palette)
            for r in range(r0, r0 + rh):
                cells[r][c0:c0 + rw] = [cp] * rw

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        for r in range(rows):
            for c in range(width):
                cp = area["blocks_cells"][r][c]
                ch = " " if cp == 0 else "█"
                try:
                    self.stdscr.addch(y + r, x + c, ch, self.curses.color_pair(cp))
                except self.curses.error:
                    pass
