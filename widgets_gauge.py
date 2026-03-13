"""Gauge, sparkline, and readout widget helpers for FakeData Terminal."""

from __future__ import annotations

import random
import time


class GaugeWidgets:
    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        area_style,
        new_area_text_entry,
        get_gauge_config,
        normalize_colour_spec,
        colour_attr_from_spec,
        prime_values,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.area_style = area_style
        self.new_area_text_entry = new_area_text_entry
        self.get_gauge_config = get_gauge_config
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.prime_values = prime_values

    @staticmethod
    def gauge_parse_num(s: str):
        try:
            return float(s.replace(",", "").replace("+", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def readout_use_title(rows: int) -> bool:
        return rows >= 6

    def readout_line_capacity(self, rows: int) -> int:
        reserved = 1 if self.readout_use_title(rows) else 0
        return min(10, max(1, rows - reserved))

    def readout_filler_rows(self, style_name: str):
        fillers = {
            "hacker": [("LAT", lambda: f"{random.uniform(2.0, 85.0):5.1f}", "ms"), ("DISC", lambda: f"{random.randint(1, 64):2d}", "nodes"), ("TLS", lambda: f"{random.uniform(0.0, 1.0):.3f}", "err"), ("AUTH", lambda: random.choice(["PASS", "PASS", "WARN", "HOLD"]), ""), ("I/O", lambda: f"{random.randint(10, 999):3d}", "MB/s")],
            "science": [("MAG", lambda: f"{random.uniform(0.1, 8.0):4.2f}", "T"), ("PHASE", lambda: f"{random.uniform(0.0, 360.0):5.1f}", "deg"), ("VAC", lambda: f"{random.uniform(1e-9, 1e-3):.1e}", "mbar"), ("SYNC", lambda: f"{random.uniform(97.0, 100.0):4.1f}", "%"), ("BEAM", lambda: random.choice(["LOCK", "LOCK", "TUNE", "DRFT"]), "")],
            "medicine": [("RESP", lambda: f"{random.randint(8, 24):2d}", "rpm"), ("ETCO2", lambda: f"{random.uniform(28.0, 48.0):4.1f}", "mmHg"), ("MAP", lambda: f"{random.randint(60, 110):3d}", "mmHg"), ("INFUSN", lambda: f"{random.uniform(1.0, 40.0):4.1f}", "mL/h"), ("RHYTHM", lambda: random.choice(["NSR", "NSR", "PVC", "AFIB"]), "")],
            "pharmacy": [("QUEUE", lambda: f"{random.randint(0, 240):3d}", "rx"), ("FILL", lambda: f"{random.uniform(10.0, 98.0):4.1f}", "%"), ("DUR", lambda: f"{random.randint(0, 24):2d}", "flag"), ("READY", lambda: f"{random.randint(0, 180):3d}", "bags"), ("COB", lambda: random.choice(["PAID", "PAID", "REVW", "HOLD"]), "")],
            "finance": [("BID", lambda: f"{random.uniform(100.0, 9999.0):,.2f}", ""), ("ASK", lambda: f"{random.uniform(100.0, 9999.0):,.2f}", ""), ("SPD", lambda: f"{random.uniform(0.01, 1.50):.2f}", ""), ("BETA", lambda: f"{random.uniform(0.50, 2.50):.2f}", ""), ("RSI", lambda: f"{random.uniform(5.0, 95.0):4.1f}", "")],
            "space": [("ROLL", lambda: f"{random.uniform(-180.0, 180.0):6.1f}", "deg"), ("PITCH", lambda: f"{random.uniform(-90.0, 90.0):5.1f}", "deg"), ("O2", lambda: f"{random.uniform(20.0, 100.0):4.1f}", "%"), ("HULL", lambda: f"{random.uniform(65.0, 100.0):4.1f}", "%"), ("COMMS", lambda: random.choice(["CLEAR", "CLEAR", "FADE", "LOSS"]), "")],
            "military": [("IFF", lambda: random.choice(["BLUE", "BLUE", "UNK", "HOST"]), ""), ("RANGE", lambda: f"{random.uniform(0.4, 120.0):5.1f}", "km"), ("LOCK", lambda: f"{random.randint(0, 12):2d}", "trk"), ("JAM", lambda: f"{random.uniform(0.0, 100.0):4.1f}", "%"), ("RCS", lambda: f"{random.uniform(0.1, 12.0):4.1f}", "m2")],
            "navigation": [("HEAD", lambda: f"{random.randint(0, 359):3d}", "deg"), ("ALT", lambda: f"{random.randint(0, 4200):4d}", "m"), ("LANE", lambda: f"{random.randint(1, 5):1d}", ""), ("DRIFT", lambda: f"{random.uniform(0.0, 2.5):3.1f}", "m"), ("TURN", lambda: random.choice(["NONE", "LEFT", "RIGHT", "HOLD"]), "")],
            "spaceteam": [("WUMBLE", lambda: f"{random.randint(0, 88):2d}", "flux"), ("BLASTR", lambda: f"{random.uniform(0.0, 9.9):3.1f}", "zorg"), ("TWIST", lambda: f"{random.randint(0, 360):3d}", "deg"), ("GRONK", lambda: random.choice(["OK", "BZZT", "???", "YEP"]), ""), ("NOISE", lambda: f"{random.uniform(10.0, 99.0):4.1f}", "spl")],
        }
        default_rows = [("SIGMA", lambda: f"{random.uniform(0.0, 99.9):4.1f}", ""), ("DELTA", lambda: f"{random.uniform(-9.9, 9.9):+4.1f}", ""), ("STATE", lambda: random.choice(["OK", "OK", "WARN", "HOLD"]), ""), ("INDEX", lambda: f"{random.randint(0, 999):3d}", ""), ("DRIFT", lambda: f"{random.uniform(0.0, 9.9):3.1f}", "")]
        return fillers.get(style_name, default_rows)

    def next_prime_value(self, area: dict) -> str:
        idx = area["gauge_prime_idx"] % len(self.prime_values)
        value = self.prime_values[idx]
        area["gauge_prime_idx"] = (idx + 1) % len(self.prime_values)
        return value

    def refresh_readout_rows(self, area: dict, rows: int):
        target_lines = self.readout_line_capacity(rows)
        if target_lines <= 1:
            area["gauge_reads"] = [("COUNT", lambda area=area: str(area["gauge_count"]), "")]
            return
        fillers = self.readout_filler_rows(self.area_style(area))
        data_lines = list(area["gauge_base_reads"][:max(0, target_lines - 2)])
        fill_idx = 0
        while len(data_lines) < max(0, target_lines - 2):
            data_lines.append(fillers[fill_idx % len(fillers)])
            fill_idx += 1
        data_lines.append(("PRIME", lambda area=area: self.next_prime_value(area), ""))
        data_lines.append(("COUNT", lambda area=area: str(area["gauge_count"]), ""))
        area["gauge_reads"] = data_lines

    def sync_gauge_vectors(self, area: dict):
        count = len(area["gauge_reads"])
        if len(area["gauge_hist"]) != count:
            area["gauge_hist"] = [[0.0] * 4 for _ in area["gauge_reads"]]
        if len(area["gauge_arrows"]) != count:
            area["gauge_arrows"] = ["─" for _ in area["gauge_reads"]]
        if len(area["gauge_last_values"]) != count:
            vals = [val_fn() for _, val_fn, _ in area["gauge_reads"]]
            area["gauge_last_values"] = vals
            for i, val_str in enumerate(vals):
                num = self.gauge_parse_num(val_str)
                if num is not None:
                    area["gauge_hist"][i] = [num]

    def ensure_gauges(self, area: dict, rows: int, width: int, role: str, mode: str):
        cfg = self.get_gauge_config(self.area_style(area))
        area["gauge_title"], area["gauge_signal"], area["gauge_base_reads"], area["gauge_scroll_title"] = cfg
        area["gauge_reads"] = area["gauge_base_reads"]
        if mode == "readouts":
            self.refresh_readout_rows(area, rows)
        if not area["gauge_spark"]:
            area["gauge_spark"] = [0.5]
            for _ in range(max(7, width - 1)):
                area["gauge_spark"].append(self.next_gauge_spark(area))
        had_last_values = bool(area["gauge_last_values"])
        self.sync_gauge_vectors(area)
        if not had_last_values:
            if self.area_style(area) == "pharmacy" and role == "sidebar":
                area["gauge_next_reads_at"] = time.time() + 0.80
            elif role == "sidebar":
                area["gauge_next_reads_at"] = time.time() + 0.45
            else:
                area["gauge_next_reads_at"] = time.time() + 0.30
        while len(area["gauge_feed"]) < rows:
            area["gauge_feed"].append(self.new_area_text_entry("text", width, {"text": area["feed_text"], "style_override": self.area_style(area)}, role))
        while len(area["gauge_feed"]) > rows:
            area["gauge_feed"].pop(0)

    def next_gauge_spark(self, area: dict):
        if not callable(area["gauge_signal"]):
            area["gauge_title"], area["gauge_signal"], area["gauge_reads"], area["gauge_scroll_title"] = self.get_gauge_config(self.area_style(area))
        self.sync_gauge_vectors(area)
        prev = area["gauge_spark"][-1] if area["gauge_spark"] else 0.5
        raw = area["gauge_signal"]()
        target = 0.14 + raw * 0.72
        drift = area["gauge_drift"]
        drift += (target - prev) * 0.30
        drift += random.gauss(0, 0.04)
        drift *= 0.82
        drift -= (prev - 0.5) * 0.03
        floor_bias = max(0.0, (0.24 - prev) / 0.24)
        if floor_bias > 0.0:
            if drift < 0:
                drift *= max(0.20, 1.0 - floor_bias * 0.85)
            if random.random() < floor_bias:
                drift += random.uniform(0.02, 0.09) * floor_bias
        if random.random() < 0.035:
            drift += random.choice([-1, 1]) * random.uniform(0.06, 0.16)
        drift = max(-0.12, min(0.12, drift))
        nxt = prev + drift
        if nxt < 0.01:
            nxt = 0.01 + (0.01 - nxt) * 0.40
            drift = abs(drift) * 0.62 + random.uniform(0.01, 0.04)
        elif nxt > 0.99:
            nxt = 0.99 - (nxt - 0.99) * 0.40
            drift = -abs(drift) * 0.62 - random.uniform(0.01, 0.04)
        area["gauge_drift"] = drift
        return max(0.01, min(0.99, nxt))

    @staticmethod
    def gauge_rows(area: dict, rows: int):
        spark_rows = max(4, rows * 30 // 100)
        reads_rows = max(4, len(area["gauge_reads"]) + 2)
        div1 = spark_rows
        reads_start = div1 + 1
        div2 = reads_start + reads_rows
        feed_start = div2 + 1
        return spark_rows, div1, reads_start, div2, feed_start

    def draw_divider(self, y: int, row: int, x: int, width: int, label, cp=3, attr=None):
        inner = f"[ {label} ]"
        dashes = max(0, width - len(inner) - 2)
        left = dashes // 2
        right = dashes - left
        txt = "─" * left + " " + inner + " " + "─" * right
        safe_w = self.safe_row_width(y, row, x, width)
        if safe_w <= 0:
            return
        try:
            draw_attr = attr if attr is not None else (self.curses.color_pair(cp) | self.curses.A_DIM)
            self.stdscr.addnstr(y + row, x, txt[:safe_w].ljust(safe_w), safe_w, draw_attr)
        except self.curses.error:
            pass

    def repaint_gauges(self, area: dict, rows: int, y: int, x: int, width: int):
        spark_rows, div1, reads_start, div2, feed_start = self.gauge_rows(area, rows)
        spark_chars = " ▁▂▃▄▅▆▇█"
        vals = area["gauge_spark"][-width:] if len(area["gauge_spark"]) >= width else area["gauge_spark"]
        for r in range(spark_rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            chars = []
            for v in vals:
                bar_h = int(v * spark_rows)
                row_from_bottom = spark_rows - 1 - r
                if bar_h == 0:
                    chars.append(" ")
                elif row_from_bottom < bar_h - 1:
                    chars.append("█")
                elif row_from_bottom == bar_h - 1:
                    frac = (v * spark_rows) - int(v * spark_rows)
                    chars.append(spark_chars[max(1, int(frac * 8))])
                else:
                    chars.append(" ")
            cp = 3 if r / max(1, spark_rows - 1) < 0.25 else (5 if r / max(1, spark_rows - 1) > 0.75 else 6)
            try:
                self.stdscr.addnstr(y + r, x, "".join(chars)[:safe_w].ljust(safe_w), safe_w, self.curses.color_pair(cp))
            except self.curses.error:
                pass
        self.draw_divider(y, div1, x, width, area["gauge_title"])
        for i, (label, val_fn, unit) in enumerate(area["gauge_reads"]):
            row = reads_start + i
            if row >= min(rows, div2):
                break
            val_str = area["gauge_last_values"][i] if i < len(area["gauge_last_values"]) else val_fn()
            arrow = area["gauge_arrows"][i] if i < len(area["gauge_arrows"]) else " "
            line = f" {label[:10]:<10s} {val_str:>8s} {unit[:8]:<8s} {arrow}"
            safe_w = self.safe_row_width(y, row, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + row, x, line[:safe_w].ljust(safe_w), safe_w, self.curses.color_pair(2))
            except self.curses.error:
                pass
        if div2 < rows:
            self.draw_divider(y, div2, x, width, area["gauge_scroll_title"])
        blank = " " * width
        for r in range(feed_start, rows):
            idx = r - feed_start
            if idx >= len(area["gauge_feed"]):
                break
            txt, attr, vis = area["gauge_feed"][idx]
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
            except self.curses.error:
                pass
            if not txt:
                continue
            try:
                draw_w = max(0, min(vis, safe_w))
                if draw_w:
                    self.stdscr.addnstr(y + r, x, txt[:draw_w].ljust(draw_w), draw_w, attr)
            except self.curses.error:
                pass

    def repaint_sparkline(self, area: dict, rows: int, y: int, x: int, width: int):
        spark_chars = " ▁▂▃▄▅▆▇█"
        vals = area["gauge_spark"][-width:] if len(area["gauge_spark"]) >= width else area["gauge_spark"]
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            chars = []
            for v in vals:
                bar_h = int(v * rows)
                row_from_bottom = rows - 1 - r
                if bar_h == 0:
                    chars.append(" ")
                elif row_from_bottom < bar_h - 1:
                    chars.append("█")
                elif row_from_bottom == bar_h - 1:
                    frac = (v * rows) - int(v * rows)
                    chars.append(spark_chars[max(1, int(frac * 8))])
                else:
                    chars.append(" ")
            cp = 3 if r / max(1, rows - 1) < 0.25 else (5 if r / max(1, rows - 1) > 0.75 else 6)
            try:
                self.stdscr.addnstr(y + r, x, "".join(chars)[:safe_w].ljust(safe_w), safe_w, self.curses.color_pair(cp))
            except self.curses.error:
                pass

    def repaint_readouts(self, area: dict, rows: int, y: int, x: int, width: int):
        blank = " " * width
        title = area["gauge_title"]
        use_title = self.readout_use_title(rows)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "white"
        multi_attrs = [self.curses.color_pair(2), self.curses.color_pair(3), self.curses.color_pair(6), self.curses.color_pair(4), self.curses.color_pair(5), self.curses.color_pair(8), self.curses.color_pair(9)]
        single_attr = self.colour_attr_from_spec(self.curses, colour_spec, default="white")
        data_rows = min(len(area["gauge_reads"]), max(1, rows - (1 if use_title else 0)))
        content_rows = min(rows, data_rows + (1 if use_title else 0))
        top_pad = max(0, (rows - content_rows) // 2)
        start_row = top_pad + (1 if use_title else 0)
        block_width = min(width, 29)
        block_pad = max(0, (width - block_width) // 2)
        for r in range(rows):
            try:
                self.stdscr.addnstr(y + r, x, blank, width, self.curses.color_pair(1))
            except self.curses.error:
                pass
        if use_title:
            title_attr = multi_attrs[0] if colour_spec == "multi" else single_attr
            self.draw_divider(y, top_pad, x, width, title, attr=title_attr | self.curses.A_DIM)
        for i, (label, val_fn, unit) in enumerate(area["gauge_reads"]):
            row = start_row + i
            if row >= rows:
                break
            if label == "COUNT":
                val_str = str(area["gauge_count"])
            else:
                val_str = area["gauge_last_values"][i] if i < len(area["gauge_last_values"]) else val_fn()
            arrow = " " if label in {"COUNT", "PRIME"} else (area["gauge_arrows"][i] if i < len(area["gauge_arrows"]) else " ")
            line = (" " * block_pad) + f"{label[:10]:<10s} {val_str:>8s} {unit[:8]:<8s} {arrow}"
            safe_w = self.safe_row_width(y, row, x, width)
            if safe_w <= 0:
                continue
            try:
                line_attr = multi_attrs[(i + (1 if use_title else 0)) % len(multi_attrs)] if colour_spec == "multi" else single_attr
                self.stdscr.addnstr(y + row, x, line[:safe_w].ljust(safe_w), safe_w, line_attr)
            except self.curses.error:
                pass
