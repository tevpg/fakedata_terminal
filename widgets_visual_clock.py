"""Clock widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import math
import random
import time


class ClockWidget:
    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        normalize_colour_spec,
        colour_attr_from_spec,
        draw_centered_overlay_to_canvas,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.draw_centered_overlay_to_canvas = draw_centered_overlay_to_canvas

    @staticmethod
    def choose_spin() -> int:
        roll = random.random()
        if roll < 0.5:
            return 1
        if roll < 0.9:
            return -1
        return 0

    @staticmethod
    def spin_for_direction(direction: str | None) -> int:
        if direction == "right":
            return 1
        if direction == "left":
            return -1
        return 0

    def update(self, area: dict) -> None:
        now = time.time()
        direction = str(area.get("direction_override") or "right").lower()
        if direction == "none":
            area["direction_motion"] = 0
            return
        forced_spin = self.spin_for_direction(direction)
        if forced_spin:
            area["clock_spin"] = forced_spin
            area["direction_motion"] = forced_spin
        elif now >= area["clock_next_spin_change"]:
            area["clock_spin"] = self.choose_spin()
            area["clock_next_spin_change"] = now + random.uniform(0.5, 3.0)
            if area["clock_spin"] > 0:
                area["direction_motion"] = 1
            elif area["clock_spin"] < 0:
                area["direction_motion"] = -1
        area["clock_angle"] = (area["clock_angle"] + (0.12 * area["clock_spin"])) % (math.pi * 2)
        area["clock_tick"] += 1
        fresh = []
        for ang, dist, ttl in area["clock_blips"]:
            ttl -= 1
            if ttl > 0:
                fresh.append((ang, dist, ttl))
        area["clock_blips"] = fresh
        if random.random() < 0.18:
            area["clock_blips"].append((random.uniform(0, math.pi * 2), random.uniform(0.15, 0.95), random.randint(10, 24)))

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        canvas = [[" " for _ in range(width)] for _ in range(rows)]
        attrs = [[self.curses.color_pair(1) for _ in range(width)] for _ in range(rows)]
        face_spec = self.normalize_colour_spec(area.get("colour_override")) or "cyan"
        face_attr = self.colour_attr_from_spec(self.curses, face_spec, default="cyan")
        face_multi_attrs = [
            self.curses.color_pair(5) | self.curses.A_BOLD,
            self.curses.color_pair(4) | self.curses.A_BOLD,
            self.curses.color_pair(6) | self.curses.A_BOLD,
            self.curses.color_pair(3) | self.curses.A_BOLD,
            self.curses.color_pair(8) | self.curses.A_BOLD,
            self.curses.color_pair(9) | self.curses.A_BOLD,
            self.curses.color_pair(2) | self.curses.A_BOLD,
        ]
        cx = (width - 1) / 2.0
        cy = (rows - 1) / 2.0
        face_aspect = 2.0
        xroom = max(0.0, cx - 1.0)
        yroom = max(0.0, cy - 1.0)
        if xroom <= 0.0 or yroom <= 0.0:
            return
        xrad = min(xroom, yroom * face_aspect)
        yrad = xrad / face_aspect
        c_mid = int(round(cx))
        r_mid = int(round(cy))
        for r in range(rows):
            for c in range(width):
                dx = (c - cx) / max(1.0, xrad)
                dy = (r - cy) / max(1.0, yrad)
                dist = math.sqrt(dx * dx + dy * dy)
                ang = math.atan2(dy, dx)
                if abs(dist - 1.0) < 0.08:
                    canvas[r][c] = "•"
                    if face_spec == "multi":
                        sector = int((((ang + math.pi) / (math.pi * 2)) * len(face_multi_attrs)))
                        attrs[r][c] = face_multi_attrs[sector % len(face_multi_attrs)]
                    else:
                        attrs[r][c] = face_attr
        for mr, mc, ch in [
            (int(round(cy - yrad)), c_mid, "▲"),
            (r_mid, int(round(cx + xrad)), "▶"),
            (int(round(cy + yrad)), c_mid, "▼"),
            (r_mid, int(round(cx - xrad)), "◀"),
        ]:
            if 0 <= mr < rows and 0 <= mc < width:
                canvas[mr][mc] = ch
                attrs[mr][mc] = self.curses.color_pair(2) | self.curses.A_BOLD
        if 0 <= r_mid < rows and 0 <= c_mid < width:
            canvas[r_mid][c_mid] = "◉"
            attrs[r_mid][c_mid] = self.curses.color_pair(2) | self.curses.A_BOLD
        for ang, dist, ttl in area["clock_blips"]:
            px = int(round(cx + math.cos(ang) * xrad * dist))
            py = int(round(cy + math.sin(ang) * yrad * dist))
            if 0 <= py < rows and 0 <= px < width:
                canvas[py][px] = "◆" if ttl > 16 else "◉"
                attrs[py][px] = self.curses.color_pair(5)
                for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                    if 0 <= ny < rows and 0 <= nx < width and canvas[ny][nx] == " ":
                        canvas[ny][nx] = "·"
                        attrs[ny][nx] = self.curses.color_pair(2)
        clock_text_row = min(rows - 1, max(0, int(round(cy + max(1.0, yrad * 0.72)))))
        self.draw_centered_overlay_to_canvas(area, clock_text_row, width, canvas, attrs, rows=rows, anchor="center")
        for r in range(rows):
            for c in range(width):
                dx = (c - cx) / max(1.0, xrad)
                dy = (r - cy) / max(1.0, yrad)
                dist = math.sqrt(dx * dx + dy * dy)
                ang = math.atan2(dy, dx)
                delta = abs((ang - area["clock_angle"] + math.pi) % (math.pi * 2) - math.pi)
                if dist <= 1.0 and delta < 0.08:
                    canvas[r][c] = "█" if delta < 0.02 else "▓"
                    attrs[r][c] = self.curses.color_pair(2)
        for r in range(rows):
            for c in range(width):
                try:
                    self.stdscr.addch(y + r, x + c, canvas[r][c], attrs[r][c])
                except self.curses.error:
                    pass
