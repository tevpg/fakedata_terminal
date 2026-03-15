"""Image and life widget helpers for FakeData Terminal."""

from __future__ import annotations

import collections
import random
import subprocess
import textwrap


class ImageWidgets:
    IMAGE_MODES = {"image", "life", "blank"}

    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        safe_row_width,
        image_module,
        image_paths_getter,
        inject_text_getter,
        life_max_getter,
        normalize_colour_spec,
        colour_attr_from_spec,
        image_colour_cycle,
        image_trail_attrs,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.safe_row_width = safe_row_width
        self.Image = image_module
        self.image_paths_getter = image_paths_getter
        self.inject_text_getter = inject_text_getter
        self.life_max_getter = life_max_getter
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.image_colour_cycle = image_colour_cycle
        self.image_trail_attrs = image_trail_attrs
        self.jp2a_cache = {}

    def overlay_text(self, area: dict) -> str:
        text = area.get("text_override") or self.inject_text_getter()
        if not text:
            return ""
        return str(text).replace("\\n", "\n")

    @staticmethod
    def image_message(rows: int, width: int, text: str):
        lines = ["" for _ in range(rows)]
        msg = text[:width]
        if rows > 0:
            lines[rows // 2] = msg.center(width)
        return lines

    def jp2a_background(self, path: str) -> str:
        try:
            with self.Image.open(path) as img:
                img = img.convert("RGBA")
                sample_w = max(1, min(8, img.width))
                sample_h = max(1, min(8, img.height))
                total = 0.0
                count = 0
                for y in range(sample_h):
                    for x in range(sample_w):
                        r, g, b, a = img.getpixel((x, y))
                        alpha = a / 255.0
                        r *= alpha
                        g *= alpha
                        b *= alpha
                        total += 0.2126 * r + 0.7152 * g + 0.0722 * b
                        count += 1
        except Exception:
            return "dark"
        avg = total / max(1, count)
        return "light" if avg >= 128 else "dark"

    def fit_ascii_to_panel(self, lines, width: int, rows: int):
        lines = [line.replace("\t", "    ").rstrip("\n") for line in lines]
        if not lines:
            return [" " * width for _ in range(rows)]
        src_h = len(lines)
        if src_h > rows:
            top = (src_h - rows) // 2
            lines = lines[top:top + rows]
        elif src_h < rows:
            pad_top = (rows - src_h) // 2
            pad_bot = rows - src_h - pad_top
            lines = ([""] * pad_top) + lines + ([""] * pad_bot)
        fitted = []
        for line in lines[:rows]:
            src_w = len(line)
            if src_w > width:
                left = (src_w - width) // 2
                fitted.append(line[left:left + width])
            else:
                pad_left = (width - src_w) // 2
                pad_right = width - src_w - pad_left
                fitted.append((" " * pad_left) + line + (" " * pad_right))
        if len(fitted) < rows:
            fitted.extend([" " * width for _ in range(rows - len(fitted))])
        return [line[:width].ljust(width) for line in fitted]

    def render_image(self, path: str, width: int, rows: int, invert: bool = False):
        background = self.jp2a_background(path)
        key = (path, width, rows, invert, background)
        cached = self.jp2a_cache.get(key)
        if cached is not None:
            return cached

        def run_jp2a(dim_flag: str):
            cmd = ["jp2a", dim_flag, f"--background={background}"]
            if invert:
                cmd.append("--invert")
            cmd.append(path)
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return proc.stdout.replace("\r", "").splitlines()

        try:
            lines_w = run_jp2a(f"--width={width}")
            if len(lines_w) >= rows:
                lines = lines_w
            else:
                lines_h = run_jp2a(f"--height={rows}")
                lines = lines_h if lines_h else lines_w
        except FileNotFoundError:
            lines = self.image_message(rows, width, "jp2a not found")
        except subprocess.CalledProcessError as exc:
            err = exc.stderr.strip().splitlines()
            detail = err[0] if err else "jp2a failed"
            lines = self.image_message(rows, width, detail)
        lines = self.fit_ascii_to_panel(lines, width, rows)
        self.jp2a_cache[key] = lines
        return lines

    def ensure_image(self, area: dict, rows: int, width: int):
        area_image_paths = area.get("image_paths") or self.image_paths_getter()
        sig = (tuple(area_image_paths), rows, width)
        if area["image_sig"] == sig:
            return
        if not area_image_paths:
            frames = []
        elif len(area_image_paths) == 1:
            frames = [self.render_image(area_image_paths[0], width, rows, invert=False), self.render_image(area_image_paths[0], width, rows, invert=True)]
        else:
            frames = [self.render_image(path, width, rows, invert=False) for path in area_image_paths]
        area["image_sig"] = sig
        area["image_frames"] = frames
        area["image_from"] = 0
        area["image_to"] = 1 % len(frames) if frames else 0
        area["image_wipe_row"] = -1
        area["image_colour_idx"] = 0

    def update_image(self, area: dict, rows: int, width: int):
        self.ensure_image(area, rows, width)
        area["image_wipe_row"] += 1
        if area["image_wipe_row"] > rows:
            frame_count = len(area["image_frames"])
            area["image_from"] = area["image_to"]
            area["image_to"] = (area["image_to"] + 1) % frame_count if frame_count else 0
            area["image_wipe_row"] = -1
            area["image_colour_idx"] = (area["image_colour_idx"] + 1) % len(self.image_colour_cycle)

    @staticmethod
    def life_hash(cells):
        return tuple("".join("1" if cell else "0" for cell in row) for row in cells)

    def seed_life(self, area: dict, rows: int, width: int, sig=None):
        density = 0.22 if rows * width <= 1200 else 0.16
        cells = []
        ages = []
        for _ in range(rows):
            row = []
            age_row = []
            for _ in range(width):
                alive = 1 if random.random() < density else 0
                row.append(alive)
                age_row.append(alive)
            cells.append(row)
            ages.append(age_row)
        area["life_sig"] = sig if sig is not None else (rows, width)
        area["life_cells"] = cells
        area["life_ages"] = ages
        area["life_iteration"] = 0
        area["life_hashes"] = collections.deque([self.life_hash(cells)], maxlen=8)

    def ensure_life(self, area: dict, rows: int, width: int):
        sig = (rows, width)
        if area["life_sig"] == sig:
            return
        self.seed_life(area, rows, width, sig=sig)

    def update_life(self, area: dict, rows: int, width: int):
        self.ensure_life(area, rows, width)
        src = area["life_cells"]
        src_ages = area["life_ages"]
        nxt = [[0] * width for _ in range(rows)]
        nxt_ages = [[0] * width for _ in range(rows)]
        births = 0
        deaths = 0
        for r in range(rows):
            for c in range(width):
                neighbours = 0
                for dr in (-1, 0, 1):
                    rr = r + dr
                    if rr < 0 or rr >= rows:
                        continue
                    for dc in (-1, 0, 1):
                        cc = c + dc
                        if dc == 0 and dr == 0:
                            continue
                        if 0 <= cc < width:
                            neighbours += src[rr][cc]
                alive = src[r][c] == 1
                if alive and neighbours in (2, 3):
                    nxt[r][c] = 1
                    nxt_ages[r][c] = src_ages[r][c] + 1
                elif (not alive) and neighbours == 3:
                    nxt[r][c] = 1
                    nxt_ages[r][c] = 1
                    births += 1
                elif alive:
                    deaths += 1
        area["life_iteration"] += 1
        next_hash = self.life_hash(nxt)
        if area["life_iteration"] >= self.life_max_getter() or births == 0 or deaths == 0 or next_hash in area["life_hashes"]:
            self.seed_life(area, rows, width)
            return
        area["life_cells"] = nxt
        area["life_ages"] = nxt_ages
        area["life_hashes"].append(next_hash)

    def repaint_life(self, area: dict, rows: int, y: int, x: int, width: int):
        self.ensure_life(area, rows, width)
        dead_attr = self.curses.color_pair(1)
        cells = area["life_cells"]
        ages = area["life_ages"]
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            for c in range(safe_w):
                if cells[r][c]:
                    age = ages[r][c]
                    if age <= 1:
                        attr = self.curses.color_pair(9) | self.curses.A_BOLD
                    elif age <= 3:
                        attr = self.curses.color_pair(3) | self.curses.A_BOLD
                    elif age <= 6:
                        attr = self.curses.color_pair(2) | self.curses.A_BOLD
                    else:
                        attr = self.curses.color_pair(7) | self.curses.A_DIM
                    ch = "◉"
                else:
                    ch = " "
                    attr = dead_attr
                try:
                    self.stdscr.addch(y + r, x + c, ch, attr)
                except self.curses.error:
                    pass

    def repaint_image(self, area: dict, rows: int, y: int, x: int, width: int):
        self.ensure_image(area, rows, width)
        if not area["image_frames"]:
            return
        src = area["image_frames"][area["image_from"]]
        dst = area["image_frames"][area["image_to"]]
        wipe_row = area["image_wipe_row"]
        src_cp = self.image_colour_cycle[area["image_colour_idx"] % len(self.image_colour_cycle)]
        dst_cp = self.image_colour_cycle[(area["image_colour_idx"] + 1) % len(self.image_colour_cycle)]
        src_attr = self.curses.color_pair(src_cp)
        dst_attr = self.curses.color_pair(dst_cp)
        bar_attr = self.curses.color_pair(1) | self.curses.A_DIM
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            if 0 <= wipe_row < rows and r == wipe_row:
                line = "▄" * width
                attr = bar_attr
            elif wipe_row - len(self.image_trail_attrs) <= r < wipe_row:
                line = dst[r]
                attr = self.image_trail_attrs[wipe_row - r - 1]
            elif r < wipe_row:
                line = dst[r]
                attr = dst_attr
            else:
                line = src[r]
                attr = src_attr
            try:
                self.stdscr.addnstr(y + r, x, line[:safe_w], safe_w, attr)
            except self.curses.error:
                pass

    def repaint_unavailable(self, area: dict, rows: int, y: int, x: int, width: int):
        lines = self.image_message(rows, width, area.get("unavailable_message") or "")
        blank = " " * width
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
                line = lines[r][:safe_w].ljust(safe_w)
                attr = self.curses.color_pair(4) | self.curses.A_BOLD if line.strip() else self.curses.color_pair(1)
                self.stdscr.addnstr(y + r, x, line, safe_w, attr)
            except self.curses.error:
                pass

    def repaint_static_lines(self, area: dict, rows: int, y: int, x: int, width: int):
        blank = " " * width
        lines = area.get("static_lines") or []
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "white"
        base_attr = self.colour_attr_from_spec(self.curses, colour_spec, default="white")
        text_only = False
        overlay = self.overlay_text(area)
        if not lines and overlay:
            lines = overlay.splitlines() or [overlay]
            text_only = True
        wrapped_lines = []
        wrap_width = max(1, width)
        for source_line in lines:
            if not source_line:
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(textwrap.wrap(
                source_line,
                width=wrap_width,
                break_long_words=True,
                break_on_hyphens=False,
            ) or [""])
        lines = wrapped_lines
        align = area.get("static_align") or "top"
        if text_only and align == "top":
            align = "center"
        top = max(0, (rows - len(lines)) // 2) if align == "center" else (1 if rows > 2 else 0)
        for r in range(rows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            try:
                self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
                line_idx = r - top
                if 0 <= line_idx < len(lines):
                    source_line = lines[line_idx][:safe_w]
                    if align == "center":
                        start = max(0, (safe_w - len(source_line)) // 2)
                        line = (" " * start + source_line).ljust(safe_w)
                    else:
                        line = source_line.ljust(safe_w)
                    attr = base_attr if not source_line.endswith(":") else base_attr | self.curses.A_BOLD
                    self.stdscr.addnstr(y + r, x, line, safe_w, attr)
            except self.curses.error:
                pass

    def handles_mode(self, mode: str) -> bool:
        return mode in self.IMAGE_MODES

    def ensure(self, area: dict, rows: int, width: int, role: str, now: float | None = None) -> None:
        del role, now
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "image":
            self.ensure_image(area, rows, width)
        elif mode == "life":
            self.ensure_life(area, rows, width)

    def update(self, area: dict, rows: int, width: int, role: str, now: float | None = None) -> None:
        del role, now
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "image":
            self.update_image(area, rows, width)
        elif mode == "life":
            self.update_life(area, rows, width)

    def render(self, area: dict, rows: int, y: int, x: int, width: int, role: str) -> None:
        del role
        mode = area["mode"] if area["mode"] != "cycle" else area.get("cycle_current") or "text"
        if mode == "image":
            self.repaint_image(area, rows, y, x, width)
        elif mode == "life":
            self.repaint_life(area, rows, y, x, width)
        elif mode == "blank":
            if area.get("static_lines") or area.get("text_override") or self.inject_text_getter():
                self.repaint_static_lines(area, rows, y, x, width)
            elif area.get("unavailable_message"):
                self.repaint_unavailable(area, rows, y, x, width)
            else:
                blank = " " * width
                for r in range(rows):
                    safe_w = self.safe_row_width(y, r, x, width)
                    if safe_w <= 0:
                        continue
                    try:
                        self.stdscr.addnstr(y + r, x, blank, safe_w, self.curses.color_pair(1))
                    except self.curses.error:
                        pass
