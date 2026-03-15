"""Visual widget helpers for FakeData Terminal."""

from __future__ import annotations

import math
import random
import time


class VisualWidgets:
    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        leading_blank,
        inject_text_getter,
        area_vocab,
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
        self.area_vocab = area_vocab
        self.get_gauge_config = get_gauge_config
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.matrix_chars = matrix_chars
        self.sweep_symbols = sweep_symbols

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

    def update_scope(self, area: dict, width: int):
        cfg = self.get_gauge_config(self.area_vocab(area))
        area["scope_signal"] = cfg[1]
        raw = area["scope_signal"]()
        phase = area.get("scope_phase", 0.0)
        phase += 0.22 + raw * 0.34 + random.uniform(-0.04, 0.04)
        area["scope_phase"] = phase % math.tau
        amplitude = 0.16 + raw * 0.18
        harmonic = math.sin(phase * 2.7 + raw * 3.0) * 0.05
        noise = random.gauss(0, 0.025)
        spike = 0.0
        if random.random() < 0.04:
            spike = random.choice([-1.0, 1.0]) * random.uniform(0.05, 0.16)
        nxt = 0.5 + math.sin(phase) * amplitude + harmonic + noise + spike
        area["scope_vals"].append(max(0.04, min(0.96, nxt)))
        keep = max(12, width + 12)
        if len(area["scope_vals"]) > keep:
            area["scope_vals"] = area["scope_vals"][-keep:]

    def repaint_scope(self, area: dict, nrows: int, y: int, x: int, width: int):
        vals = area["scope_vals"][-width:] or [0.5] * width
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        mid = nrows // 2
        for c in range(0, width, 4):
            canvas[mid][c] = "·"
        prev_y = None
        for c, v in enumerate(vals):
            sample_y = int((1.0 - v) * max(1, nrows - 1))
            sample_y = max(0, min(nrows - 1, sample_y))
            canvas[sample_y][c] = "█"
            if prev_y is not None:
                low, high = sorted((prev_y, sample_y))
                for yy in range(low, high + 1):
                    if canvas[yy][c] == " ":
                        canvas[yy][c] = "│"
            prev_y = sample_y
        for r in range(nrows):
            frac = r / max(1, nrows - 1)
            cp = 3 if frac < 0.33 else (5 if frac > 0.66 else 6)
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, "".join(canvas[r])[:safe_w], safe_w, self.curses.color_pair(cp))
            except self.curses.error:
                pass
        self.draw_centered_overlay(area, 1 if nrows > 1 else 0, y, x, width, rows=nrows, anchor="top")

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
        cols = area["matrix_cols"]
        while len(cols) < width:
            cols.append({
                "head": random.randint(-nrows, 0),
                "tail": random.randint(4, max(6, nrows // 3)),
                "speed": random.choice([1, 1, 1, 2]),
                "active": random.random() < 0.25,
            })
        if len(cols) > width:
            del cols[width:]
        for col in cols:
            if not col["active"]:
                if random.random() < 0.035:
                    col["active"] = True
                    col["head"] = random.randint(-nrows, 0)
                    col["tail"] = random.randint(4, max(6, nrows // 3))
                    col["speed"] = random.choice([1, 1, 2])
                continue
            col["head"] += col["speed"]
            if col["head"] - col["tail"] > nrows + random.randint(0, 6):
                col["active"] = False

    def repaint_matrix(self, area: dict, nrows: int, y: int, x: int, width: int):
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        attr_map = [[self.curses.color_pair(1) for _ in range(width)] for _ in range(nrows)]
        for c, col in enumerate(area["matrix_cols"][:width]):
            if not col["active"]:
                continue
            for r in range(max(0, col["head"] - col["tail"]), min(nrows, col["head"] + 1)):
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
        for r in range(nrows):
            for c in range(width):
                try:
                    self.stdscr.addch(y + r, x + c, canvas[r][c], attr_map[r][c])
                except self.curses.error:
                    pass

    @staticmethod
    def choose_radar_spin() -> int:
        roll = random.random()
        if roll < 0.5:
            return 1
        if roll < 0.9:
            return -1
        return 0

    def update_radar(self, area: dict):
        now = time.time()
        if now >= area["radar_next_spin_change"]:
            area["radar_spin"] = self.choose_radar_spin()
            area["radar_next_spin_change"] = now + random.uniform(0.5, 3.0)
        area["radar_angle"] = (area["radar_angle"] + (0.12 * area["radar_spin"])) % (math.pi * 2)
        area["radar_tick"] += 1
        fresh = []
        for ang, dist, ttl in area["radar_blips"]:
            ttl -= 1
            if ttl > 0:
                fresh.append((ang, dist, ttl))
        area["radar_blips"] = fresh
        if random.random() < 0.18:
            area["radar_blips"].append((random.uniform(0, math.pi * 2), random.uniform(0.15, 0.95), random.randint(10, 24)))

    def repaint_radar(self, area: dict, nrows: int, y: int, x: int, width: int):
        canvas = [[" " for _ in range(width)] for _ in range(nrows)]
        attrs = [[self.curses.color_pair(1) for _ in range(width)] for _ in range(nrows)]
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
        cy = (nrows - 1) / 2.0
        face_aspect = 2.0
        xroom = max(0.0, cx - 1.0)
        yroom = max(0.0, cy - 1.0)
        if xroom <= 0.0 or yroom <= 0.0:
            return
        xrad = min(xroom, yroom * face_aspect)
        yrad = xrad / face_aspect
        c_mid = int(round(cx))
        r_mid = int(round(cy))
        for r in range(nrows):
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
            if 0 <= mr < nrows and 0 <= mc < width:
                canvas[mr][mc] = ch
                attrs[mr][mc] = self.curses.color_pair(2) | self.curses.A_BOLD
        if 0 <= r_mid < nrows and 0 <= c_mid < width:
            canvas[r_mid][c_mid] = "◉"
            attrs[r_mid][c_mid] = self.curses.color_pair(2) | self.curses.A_BOLD
        for ang, dist, ttl in area["radar_blips"]:
            px = int(round(cx + math.cos(ang) * xrad * dist))
            py = int(round(cy + math.sin(ang) * yrad * dist))
            if 0 <= py < nrows and 0 <= px < width:
                canvas[py][px] = "◆" if ttl > 16 else "◉"
                attrs[py][px] = self.curses.color_pair(5)
                for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
                    if 0 <= ny < nrows and 0 <= nx < width and canvas[ny][nx] == " ":
                        canvas[ny][nx] = "·"
                        attrs[ny][nx] = self.curses.color_pair(2)
        clock_text_row = min(nrows - 1, max(0, int(round(cy + max(1.0, yrad * 0.72)))))
        self.draw_centered_overlay_to_canvas(area, clock_text_row, width, canvas, attrs, rows=nrows, anchor="center")
        for r in range(nrows):
            for c in range(width):
                dx = (c - cx) / max(1.0, xrad)
                dy = (r - cy) / max(1.0, yrad)
                dist = math.sqrt(dx * dx + dy * dy)
                ang = math.atan2(dy, dx)
                delta = abs((ang - area["radar_angle"] + math.pi) % (math.pi * 2) - math.pi)
                if dist <= 1.0 and delta < 0.08:
                    canvas[r][c] = "█" if delta < 0.02 else "▓"
                    attrs[r][c] = self.curses.color_pair(2)
        for r in range(nrows):
            for c in range(width):
                try:
                    self.stdscr.addch(y + r, x + c, canvas[r][c], attrs[r][c])
                except self.curses.error:
                    pass

    def ensure_blocks(self, area: dict, rows: int, width: int):
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

    def update_blocks(self, area: dict, rows: int, width: int):
        self.ensure_blocks(area, rows, width)
        cells = area["blocks_cells"]
        rect_count = random.randint(1, 3)
        palette = [cp for cp in [0, 1, 2, 3, 4, 5, 6, 7] if cp != area["blocks_bg"]]
        for _ in range(rect_count):
            rh = random.randint(1, max(1, rows // 3))
            rw = random.randint(2, max(2, width // 3))
            r0 = random.randint(0, max(0, rows - rh))
            c0 = random.randint(0, max(0, width - rw))
            cp = random.choice(palette)
            for r in range(r0, r0 + rh):
                cells[r][c0:c0 + rw] = [cp] * rw

    def repaint_blocks(self, area: dict, nrows: int, y: int, x: int, width: int):
        self.ensure_blocks(area, nrows, width)
        for r in range(nrows):
            for c in range(width):
                cp = area["blocks_cells"][r][c]
                ch = " " if cp == 0 else "█"
                try:
                    self.stdscr.addch(y + r, x + c, ch, self.curses.color_pair(cp))
                except self.curses.error:
                    pass

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
        sig = (rows, width)
        if area["tunnel_sig"] == sig:
            return
        area["tunnel_sig"] = sig
        area["tunnel_layers"] = self.build_tunnel_layers(rows, width)

    def repaint_nested_layers(self, layers, area: dict, rows: int, y: int, x: int, width: int, attr_for_band=None):
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
        for inner_offset, layer in enumerate(reversed(layers)):
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
        cells = area["sweep_cells"]
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
                    if random.random() < 0.02:
                        cells[r][c] = (random.choice(self.sweep_symbols), random.choice(palette))

    @staticmethod
    def sweep_vertical(rows: int, width: int) -> bool:
        # Terminal cells are typically about twice as tall as they are wide, so a
        # panel looks roughly square around a 2:1 width:height ratio.
        return width <= rows * 2

    def update_sweep(self, area: dict, rows: int, width: int, role: str):
        self.ensure_sweep(area, rows, width)
        cells = area["sweep_cells"]

        def drop_symbol(base_cp, spawn_prob: float):
            if random.random() >= spawn_prob:
                return (" ", 1)
            cp = random.choice(base_cp) if isinstance(base_cp, (list, tuple)) else base_cp
            return (random.choice(self.sweep_symbols), cp)

        if not self.sweep_vertical(rows, width):
            span = max(1, width)
            head_max = max(0, span - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(span, pos + 3))}
            tail_cols = [pos - 2, pos - 1] if area["sweep_dir"] > 0 else [pos + 3, pos + 4]
            wake_cp = 4 if area["sweep_dir"] > 0 else [2, 3, 6, 7]
            spawn_prob = 0.01 if area["sweep_dir"] > 0 else 0.02
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
            spawn_prob = 0.01 if area["sweep_dir"] > 0 else 0.02
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

    def repaint_sweep(self, area: dict, nrows: int, y: int, x: int, width: int, role: str):
        self.ensure_sweep(area, nrows, width)
        sweep_attr = self.curses.color_pair(1)
        trail_attr = self.curses.color_pair(1) | self.curses.A_DIM
        if not self.sweep_vertical(nrows, width):
            head_max = max(0, width - 3)
            pos = max(0, min(head_max, area["sweep_pos"]))
            head_cols = {c for c in range(pos, min(width, pos + 3))}
            tail_cols = ({c for c in [pos - 2, pos - 1] if 0 <= c < width} if area["sweep_dir"] > 0 else
                         {c for c in [pos + 3, pos + 4] if 0 <= c < width})
            for r in range(nrows):
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
            pos = max(0, min(nrows - 1, area["sweep_pos"]))
            tail_rows = {r for r in range(pos - 2 * area["sweep_dir"], pos, area["sweep_dir"]) if 0 <= r < nrows}
            for r in range(nrows):
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

    def update_tunnel(self, area: dict, rows: int, width: int):
        self.ensure_tunnel(area, rows, width)

    def repaint_tunnel(self, area: dict, rows: int, y: int, x: int, width: int):
        self.ensure_tunnel(area, rows, width)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "multi"
        tunnel_attrs = [
            self.curses.color_pair(5) | self.curses.A_BOLD,
            self.curses.color_pair(4) | self.curses.A_BOLD,
            self.curses.color_pair(6) | self.curses.A_BOLD,
            self.curses.color_pair(3) | self.curses.A_BOLD,
            self.curses.color_pair(8) | self.curses.A_BOLD,
            self.curses.color_pair(9) | self.curses.A_BOLD,
            self.curses.color_pair(2) | self.curses.A_BOLD,
        ]
        single_attr = self.colour_attr_from_spec(self.curses, colour_spec, default="green", bold=True)
        self.repaint_nested_layers(
            area.get("tunnel_layers") or [],
            area,
            rows,
            y,
            x,
            width,
            attr_for_band=(lambda _band_idx: single_attr) if colour_spec != "multi" else (lambda band_idx: tunnel_attrs[band_idx % len(tunnel_attrs)]),
        )
        self.draw_centered_overlay(area, max(0, rows // 2), y, x, width, rows=rows, anchor="center")
