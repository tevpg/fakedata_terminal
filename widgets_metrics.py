"""Shared telemetry-driven helpers for sparkline and readout widgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import multi_palette_specs
    from .timing_support import read_refresh_interval, schedule_next
except ImportError:
    from runtime_support import multi_palette_specs
    from timing_support import read_refresh_interval, schedule_next


class MetricsWidgets:
    METRICS_MODES = {"sparkline", "readouts"}

    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        area_theme,
        inject_text_getter,
        get_gauge_config,
        normalize_colour_spec,
        colour_attr_from_spec,
        prime_values,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.area_theme = area_theme
        self.inject_text_getter = inject_text_getter
        self.get_gauge_config = get_gauge_config
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.prime_values = prime_values

    def overlay_text(self, area: dict) -> str:
        text = area.get("text_override") or self.inject_text_getter()
        if not text:
            return ""
        return str(text).replace("\\n", "\n")

    def draw_centered_overlay(self, overlay: str, row: int, y: int, x: int, width: int, rows: int, *,
                              anchor: str = "center", pad: bool = False):
        lines = overlay.splitlines() or [overlay]
        if pad:
            lines = [f" {line} " for line in lines]
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

    @staticmethod
    def parse_metric_num(s: str):
        try:
            return float(s.replace(",", "").replace("+", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def readout_use_title(rows: int) -> bool:
        return rows >= 6

    def readout_line_capacity(self, rows: int) -> int:
        reserved = 2 if self.readout_use_title(rows) else 0
        return min(10, max(1, rows - reserved))

    def readout_filler_rows(self, theme_name: str):
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
        return fillers.get(theme_name, default_rows)

    def next_prime_value(self, area: dict) -> str:
        idx = area["metrics_prime_idx"] % len(self.prime_values)
        value = self.prime_values[idx]
        area["metrics_prime_idx"] = (idx + 1) % len(self.prime_values)
        return value

    def refresh_readout_rows(self, area: dict, rows: int):
        target_lines = self.readout_line_capacity(rows)
        if target_lines <= 1:
            area["metrics_reads"] = [("COUNT", lambda area=area: str(area["metrics_count"]), "")]
            return
        fillers = self.readout_filler_rows(self.area_theme(area))
        data_lines = list(area["metrics_base_reads"][:max(0, target_lines - 2)])
        fill_idx = 0
        while len(data_lines) < max(0, target_lines - 2):
            data_lines.append(fillers[fill_idx % len(fillers)])
            fill_idx += 1
        data_lines.append(("PRIME", lambda area=area: self.next_prime_value(area), ""))
        data_lines.append(("COUNT", lambda area=area: str(area["metrics_count"]), ""))
        area["metrics_reads"] = data_lines

    def sync_metric_vectors(self, area: dict):
        count = len(area["metrics_reads"])
        if len(area["metrics_hist"]) != count:
            area["metrics_hist"] = [[0.0] * 4 for _ in area["metrics_reads"]]
        if len(area["metrics_arrows"]) != count:
            area["metrics_arrows"] = ["─" for _ in area["metrics_reads"]]
        if len(area["metrics_last_values"]) != count:
            vals = [val_fn() for _, val_fn, _ in area["metrics_reads"]]
            area["metrics_last_values"] = vals
            for i, val_str in enumerate(vals):
                num = self.parse_metric_num(val_str)
                if num is not None:
                    area["metrics_hist"][i] = [num]

    def ensure_metrics_state(self, area: dict, rows: int, width: int, role: str, mode: str, now: float):
        cfg = self.get_gauge_config(self.area_theme(area))
        area["metrics_title"], area["metrics_signal"], area["metrics_base_reads"], _unused_scroll_title = cfg
        area["metrics_reads"] = area["metrics_base_reads"]
        if mode == "readouts":
            self.refresh_readout_rows(area, rows)
        had_last_values = bool(area["metrics_last_values"])
        if not area["metrics_spark"]:
            area["metrics_spark"] = [0.5]
            for _ in range(max(7, width - 1)):
                area["metrics_spark"].append(self.next_metrics_spark(area))
        self.sync_metric_vectors(area)
        if not had_last_values or area["metrics_next_reads_at"] <= 0.0:
            interval = read_refresh_interval(mode, role, self.area_theme(area))
            area["metrics_next_reads_at"] = (now + interval) if interval is not None else 0.0

    def next_metrics_spark(self, area: dict):
        if not callable(area["metrics_signal"]):
            title, signal, base_reads, _unused_scroll_title = self.get_gauge_config(self.area_theme(area))
            area["metrics_title"] = title
            area["metrics_signal"] = signal
            area["metrics_base_reads"] = base_reads
            area["metrics_reads"] = base_reads
        self.sync_metric_vectors(area)
        prev = area["metrics_spark"][-1] if area["metrics_spark"] else 0.5
        raw = area["metrics_signal"]()
        target = 0.14 + raw * 0.72
        drift = area["metrics_drift"]
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
        area["metrics_drift"] = drift
        return max(0.01, min(0.99, nxt))

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

    def repaint_sparkline(self, area: dict, rows: int, y: int, x: int, width: int):
        spark_chars = " ▁▂▃▄▅▆▇█"
        motion = area.get("direction_motion", 1)
        if len(area["metrics_spark"]) >= width:
            vals = area["metrics_spark"][:width] if motion < 0 else area["metrics_spark"][-width:]
        else:
            vals = area["metrics_spark"]
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
        overlay = self.overlay_text(area)
        if overlay:
            self.draw_centered_overlay(overlay, max(0, rows - 2), y, x, width, rows, anchor="bottom", pad=True)

    def repaint_readouts(self, area: dict, rows: int, y: int, x: int, width: int):
        blank = " " * width
        title = area["metrics_title"]
        use_title = self.readout_use_title(rows)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "white"
        multi_specs = multi_palette_specs(colour_spec, bare_multi="multi-normal")
        multi_attrs = [
            self.colour_attr_from_spec(self.curses, spec, default=spec)
            for spec in multi_specs
        ]
        single_attr = self.colour_attr_from_spec(self.curses, colour_spec, default="white")
        data_rows = min(len(area["metrics_reads"]), max(1, rows - (1 if use_title else 0)))
        content_rows = min(rows, data_rows + (1 if use_title else 0))
        top_pad = max(0, (rows - content_rows) // 2)
        start_row = top_pad + (2 if use_title else 0)
        block_width = min(width, 29)
        block_pad = max(0, (width - block_width) // 2)
        for r in range(rows):
            try:
                self.stdscr.addnstr(y + r, x, blank, width, self.curses.color_pair(1))
            except self.curses.error:
                pass
        if use_title:
            title_attr = multi_attrs[0] if colour_spec in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"} and multi_attrs else single_attr
            self.draw_divider(y, top_pad, x, width, title, attr=title_attr | self.curses.A_DIM)
        for i, (label, val_fn, unit) in enumerate(area["metrics_reads"]):
            row = start_row + i
            if row >= rows:
                break
            if label == "COUNT":
                val_str = str(area["metrics_count"])
            else:
                val_str = area["metrics_last_values"][i] if i < len(area["metrics_last_values"]) else val_fn()
            arrow = " " if label in {"COUNT", "PRIME"} else (area["metrics_arrows"][i] if i < len(area["metrics_arrows"]) else " ")
            line = (" " * block_pad) + f"{label[:10]:<10s} {val_str:>8s} {unit[:8]:<8s} {arrow}"
            safe_w = self.safe_row_width(y, row, x, width)
            if safe_w <= 0:
                continue
            try:
                line_attr = (
                    multi_attrs[(i + (1 if use_title else 0)) % len(multi_attrs)]
                    if colour_spec in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"} and multi_attrs
                    else single_attr
                )
                self.stdscr.addnstr(y + row, x, line[:safe_w].ljust(safe_w), safe_w, line_attr)
            except self.curses.error:
                pass

    def handles_mode(self, mode: str) -> bool:
        return mode in self.METRICS_MODES

    def ensure(self, area: dict, rows: int, width: int, role: str, now: float | None = None) -> None:
        now = 0.0 if now is None else now
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode in self.METRICS_MODES:
            self.ensure_metrics_state(area, rows, width, role, mode, now)
            if area.get("text_override"):
                if mode == "readouts":
                    area["metrics_title"] = area["text_override"]

    def update(self, area: dict, rows: int, width: int, role: str, now: float, dt: float, *,
               resolved_direction_motion, stabilize_direction_history) -> None:
        del dt
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode not in self.METRICS_MODES:
            return
        if mode == "sparkline":
            motion = resolved_direction_motion(area, now)
            if motion != 0:
                stabilize_direction_history(area, width, motion, "metrics_spark")
                sample = self.next_metrics_spark(area)
                if motion < 0:
                    area["metrics_spark"].insert(0, sample)
                else:
                    area["metrics_spark"].append(sample)
                if len(area["metrics_spark"]) > width + 20:
                    if motion < 0:
                        area["metrics_spark"].pop()
                    else:
                        area["metrics_spark"].pop(0)
                area["direction_motion_prev"] = motion
        else:
            area["metrics_spark"].append(self.next_metrics_spark(area))
            if len(area["metrics_spark"]) > width + 20:
                area["metrics_spark"].pop(0)
        if area["metrics_next_reads_at"] > 0.0 and now >= area["metrics_next_reads_at"]:
            vals = [val_fn() for _, val_fn, _ in area["metrics_reads"]]
            for i, val_str in enumerate(vals):
                label = area["metrics_reads"][i][0] if i < len(area["metrics_reads"]) else ""
                if label in {"COUNT", "PRIME"}:
                    continue
                num = self.parse_metric_num(val_str)
                if num is None:
                    continue
                hist = area["metrics_hist"][i]
                prev_num = hist[-1] if hist else None
                if prev_num is not None:
                    eps = max(0.005, 0.005 * max(1.0, abs(prev_num)))
                    if num > prev_num + eps:
                        area["metrics_arrows"][i] = "▲"
                    elif num < prev_num - eps:
                        area["metrics_arrows"][i] = "▼"
                hist.append(num)
                if len(hist) > 4:
                    hist.pop(0)
            area["metrics_last_values"] = vals
            interval = read_refresh_interval(mode, role, self.area_theme(area))
            if interval is not None:
                area["metrics_next_reads_at"] = schedule_next(area["metrics_next_reads_at"], now, interval)

    def render(self, area: dict, rows: int, y: int, x: int, width: int, role: str) -> None:
        del role
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "sparkline":
            self.repaint_sparkline(area, rows, y, x, width)
        elif mode == "readouts":
            self.repaint_readouts(area, rows, y, x, width)
