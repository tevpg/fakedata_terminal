"""Crash widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import multi_palette_specs
except ImportError:
    from runtime_support import multi_palette_specs


class CrashWidget:
    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        area_theme,
        build_pools,
        normalize_colour_spec,
        colour_attr_from_spec,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.area_theme = area_theme
        self.build_pools = build_pools
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.theme_pool_cache = {}

    def theme_pools(self, theme_name: str):
        pools = self.theme_pool_cache.get(theme_name)
        if pools is None:
            pools = self.build_pools(theme_name)
            self.theme_pool_cache[theme_name] = pools
        return pools

    def random_theme_line(self, area: dict) -> str:
        theme_name = self.area_theme(area)
        gen_pool, _ = self.theme_pools(theme_name)
        if not gen_pool:
            return "SYSTEM FAULT"
        return str(random.choice(gen_pool)())

    def ensure(self, area: dict, rows: int, width: int) -> None:
        lines = area["crash_lines"]
        while len(lines) < rows:
            lines.append("")
        if len(lines) > rows:
            del lines[rows:]
        for idx in range(rows):
            current = lines[idx]
            if len(current) < width:
                current = current.ljust(width)
            elif len(current) > width:
                current = current[:width]
            lines[idx] = current

    def inject_fragment(self, line: str, fragment: str, width: int) -> str:
        base = line[:width].ljust(width)
        draw = fragment[:width]
        if not draw:
            return base
        start = random.randint(0, max(0, width - len(draw)))
        merged = list(base)
        for idx, ch in enumerate(draw):
            if start + idx >= width:
                break
            merged[start + idx] = ch
        return "".join(merged)

    def scramble_line(self, line: str, width: int) -> str:
        chars = list(line[:width].ljust(width))
        noise = "#$%@!&*+/\\[]{}<>?=|:;"
        flips = random.randint(1, max(1, width // 6))
        for _ in range(flips):
            pos = random.randint(0, max(0, width - 1))
            chars[pos] = random.choice(noise)
        return "".join(chars)

    def update(self, area: dict, rows: int, width: int) -> None:
        self.ensure(area, rows, width)
        area["crash_phase"] += 1

        if area["crash_flash_frames"] > 0:
            area["crash_flash_frames"] -= 1
        elif random.random() < 0.08:
            area["crash_flash_frames"] = random.randint(1, 2)

        if area["crash_blank_frames"] > 0:
            area["crash_blank_frames"] -= 1
        elif random.random() < 0.06:
            area["crash_blank_frames"] = random.randint(1, 3)

        for idx in range(rows):
            line = area["crash_lines"][idx]
            if not line.strip() or random.random() < 0.30:
                line = self.random_theme_line(area)
            if random.random() < 0.75:
                line = self.inject_fragment(line, self.random_theme_line(area), width)
            if random.random() < 0.45:
                line = self.scramble_line(line, width)
            if random.random() < 0.18:
                line = " " * width
            area["crash_lines"][idx] = line[:width].ljust(width)

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "multi-all"
        multi_specs = multi_palette_specs(colour_spec, bare_multi="multi-all")
        palette = [
            self.colour_attr_from_spec(self.curses, spec, default=spec, bold=True)
            for spec in multi_specs
        ]
        if not palette:
            palette = [self.colour_attr_from_spec(self.curses, "white", default="white", bold=True)]
        blank = " " * width

        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            if area["crash_flash_frames"] > 0:
                flash_line = "".join(random.choice(" █▓▒") for _ in range(width))
                attr = self.curses.color_pair(28) | self.curses.A_BOLD
                draw = flash_line[:safe_w].ljust(safe_w)
            elif area["crash_blank_frames"] > 0:
                if random.random() < 0.20:
                    residue = self.scramble_line(blank, width)
                    attr = self.curses.color_pair(2) | self.curses.A_DIM
                    draw = residue[:safe_w].ljust(safe_w)
                else:
                    attr = self.curses.color_pair(1)
                    draw = blank[:safe_w]
            else:
                line = area["crash_lines"][r]
                if random.random() < 0.10:
                    line = self.scramble_line(line, width)
                attr = palette[(r + area["crash_phase"]) % len(palette)]
                if random.random() < 0.18:
                    attr |= self.curses.A_REVERSE
                draw = line[:safe_w].ljust(safe_w)
            try:
                self.stdscr.addnstr(y + r, x, draw, safe_w, attr)
            except self.curses.error:
                pass
