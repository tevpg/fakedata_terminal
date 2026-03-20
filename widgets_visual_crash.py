"""Crash widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import multi_palette_specs
    from .timing_support import widget_interval
except ImportError:
    from runtime_support import multi_palette_specs
    from timing_support import widget_interval


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
        self.noise_chars = "#$%@!&*+/\\[]{}<>?=|:;"

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
        if not any(line.strip() for line in lines) and rows > 0 and width > 0:
            seed_count = max(1, rows // 5)
            for _ in range(seed_count):
                idx = random.randrange(rows)
                lines[idx] = self.inject_fragment(" " * width, self.random_theme_line(area), width)

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
        flips = random.randint(1, max(1, width // 6))
        for _ in range(flips):
            pos = random.randint(0, max(0, width - 1))
            chars[pos] = random.choice(self.noise_chars)
        return "".join(chars)

    def static_line(self, width: int, density: float = 0.16) -> str:
        chars = []
        for _ in range(width):
            if random.random() < density:
                chars.append(random.choice(self.noise_chars + ".:"))
            else:
                chars.append(" ")
        return "".join(chars)

    def decay_line(self, line: str, width: int) -> str:
        chars = list(line[:width].ljust(width))
        for idx, ch in enumerate(chars):
            if ch != " " and random.random() < 0.08:
                chars[idx] = " "
        return "".join(chars)

    @staticmethod
    def frames_for_seconds(seconds: float, speed: int) -> int:
        interval = widget_interval("crash", speed)
        if interval <= 0.0 or interval == float("inf"):
            return 1
        return max(1, int(round(seconds / interval)))

    def update(self, area: dict, rows: int, width: int, speed: int) -> None:
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

        if area["crash_invert_frames"] > 0:
            area["crash_invert_frames"] -= 1
        elif random.random() < 0.10:
            area["crash_invert_frames"] = random.randint(1, 3)

        if area["crash_static_frames"] > 0:
            area["crash_static_frames"] -= 1
        elif random.random() < 0.08:
            jitter = random.uniform(0.40, 0.60)
            area["crash_static_frames"] = self.frames_for_seconds(jitter, speed)

        if area["crash_flash_frames"] > 0 or area["crash_blank_frames"] > 0:
            return

        if area["crash_static_frames"] > 0:
            lines = area["crash_lines"]
            for idx in range(rows):
                if random.random() < 0.80:
                    lines[idx] = self.static_line(width, density=random.uniform(0.12, 0.28))
                elif random.random() < 0.30:
                    lines[idx] = self.scramble_line(lines[idx], width)
            return

        lines = area["crash_lines"]
        for idx in range(rows):
            if random.random() < 0.22:
                lines[idx] = self.decay_line(lines[idx], width)

        event_count = random.randint(1, max(2, rows // 4))
        for _ in range(event_count):
            idx = random.randrange(rows)
            line = lines[idx]
            roll = random.random()
            if not line.strip() or roll < 0.22:
                line = self.inject_fragment(" " * width, self.random_theme_line(area), width)
            elif roll < 0.55:
                line = self.inject_fragment(line, self.random_theme_line(area), width)
            elif roll < 0.78:
                line = self.scramble_line(line, width)
            elif roll < 0.90:
                line = self.static_line(width, density=0.22)
            else:
                line = " " * width
            lines[idx] = line[:width].ljust(width)

        if rows > 2 and random.random() < 0.12:
            band_height = random.randint(1, max(1, rows // 5))
            start = random.randint(0, rows - band_height)
            for idx in range(start, start + band_height):
                lines[idx] = self.scramble_line(lines[idx], width)

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
        frame_attr = palette[area["crash_phase"] % len(palette)]
        if random.random() < 0.10:
            frame_attr |= self.curses.A_DIM
        frame_inverted = area.get("crash_invert_frames", 0) > 0
        frame_static = area.get("crash_static_frames", 0) > 0
        if frame_inverted:
            frame_attr |= self.curses.A_REVERSE

        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            if area["crash_flash_frames"] > 0:
                if random.random() < 0.75:
                    flash_line = " " * width
                else:
                    flash_line = "".join(random.choice(" █▓▒") for _ in range(width))
                attr = self.curses.color_pair(28) | self.curses.A_BOLD
                if random.random() < 0.35:
                    attr |= self.curses.A_REVERSE
                draw = flash_line[:safe_w].ljust(safe_w)
            elif area["crash_blank_frames"] > 0:
                if random.random() < 0.12:
                    residue = self.static_line(width, density=0.10)
                    attr = self.curses.color_pair(2) | self.curses.A_DIM
                    if frame_inverted:
                        attr |= self.curses.A_REVERSE
                    draw = residue[:safe_w].ljust(safe_w)
                else:
                    attr = self.curses.color_pair(1)
                    if frame_inverted:
                        attr |= self.curses.A_REVERSE
                    draw = blank[:safe_w]
            elif frame_static:
                line = area["crash_lines"][r]
                attr = self.curses.color_pair(2) | self.curses.A_DIM
                if random.random() < 0.35:
                    attr = frame_attr | self.curses.A_DIM
                draw = line[:safe_w].ljust(safe_w)
            else:
                line = area["crash_lines"][r]
                if random.random() < 0.04:
                    line = self.scramble_line(line, width)
                attr = frame_attr
                draw = line[:safe_w].ljust(safe_w)
            try:
                self.stdscr.addnstr(y + r, x, draw, safe_w, attr)
            except self.curses.error:
                pass
