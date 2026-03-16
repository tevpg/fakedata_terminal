"""Text-oriented widget helpers for FakeData Terminal."""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys

try:
    from .timing_support import cycle_start_deadline, next_cycle_deadline, resolve_direction_motion
except ImportError:
    from timing_support import cycle_start_deadline, next_cycle_deadline, resolve_direction_motion


class TextWidgets:
    TEXT_MODES = {"text", "text_wide", "text_scant", "text_spew"}

    def __init__(
        self,
        *,
        curses_module,
        stdscr,
        theme_arg_getter,
        build_pools,
        build_area_state,
        get_bar_config,
        random_line,
        HEX_WORD,
        p_main_gen_pool,
        p_main_rcol_pool,
        p_sidebar_spike_pool,
        line_colour,
        rcol_colour,
        new_paragraph,
        strip_overstrikes,
        inject_text_getter,
        image_paths_getter,
        list_cycle_widget_names,
        help_text_topics_unix,
        help_text_topics_win,
    ):
        self.curses = curses_module
        self.stdscr = stdscr
        self.theme_arg_getter = theme_arg_getter
        self.build_pools = build_pools
        self.build_area_state = build_area_state
        self.get_bar_config = get_bar_config
        self.random_line = random_line
        self.HEX_WORD = HEX_WORD
        self.p_main_gen_pool = p_main_gen_pool
        self.p_main_rcol_pool = p_main_rcol_pool
        self.p_sidebar_spike_pool = p_sidebar_spike_pool
        self.line_colour = line_colour
        self.rcol_colour = rcol_colour
        self.new_paragraph = new_paragraph
        self.strip_overstrikes = strip_overstrikes
        self.inject_text_getter = inject_text_getter
        self.image_paths_getter = image_paths_getter
        self.list_cycle_widget_names = list_cycle_widget_names
        self.help_text_topics_unix = help_text_topics_unix
        self.help_text_topics_win = help_text_topics_win
        self.theme_pool_cache = {}

    def area_theme(self, area: dict) -> str:
        return area.get("theme_override") or self.theme_arg_getter()

    def theme_pools(self, theme_name: str):
        pools = self.theme_pool_cache.get(theme_name)
        if pools is None:
            pools = self.build_pools(theme_name)
            self.theme_pool_cache[theme_name] = pools
        return pools

    def make_area_state(self, theme_name: str | None = None):
        return self.build_area_state(theme_name, self.theme_arg_getter(), self.get_bar_config)

    def splice_text(self, base_line: str, msg: str, col_width: int) -> str:
        msg_len = len(msg)
        if msg_len >= len(base_line):
            start = random.randint(0, max(0, col_width - msg_len))
            return (base_line[:start] + msg)[:col_width].ljust(col_width)
        max_insert = max(0, len(base_line) - msg_len)
        insert_at = random.randint(0, max_insert)
        removal_options = []
        if insert_at > msg_len:
            removal_options.append((0, insert_at - msg_len))
        tail_start = insert_at + msg_len
        if tail_start + msg_len <= len(base_line):
            removal_options.append((tail_start, len(base_line) - msg_len))
        if removal_options:
            low, high = random.choice(removal_options)
            remove_at = random.randint(low, high)
            chopped = base_line[:remove_at] + base_line[remove_at + msg_len:]
        else:
            chopped = base_line
        spliced = chopped[:insert_at] + msg + chopped[insert_at:]
        return spliced[:col_width].ljust(col_width)

    def leading_blank(self, txt: str, width: int) -> str:
        if width <= 0:
            return ""
        return (" " + txt)[:width].ljust(width)

    def rand_line_len(self, width: int) -> int:
        t = random.betavariate(2, 3)
        frac = 0.30 + t * 0.70
        return max(10, int(frac * width))

    def dense_line(self, width: int, line_fn=None) -> str:
        if line_fn is None:
            line_fn = self.random_line
        mode = random.random()
        if mode < 0.12:
            label = random.choice([
                "MEMORY MAP", "ACTIVE LINKS", "WORK QUEUE", "STATUS BUS",
                "CHECKPOINT", "ANALYSIS GRID", "SIGNAL PATH", "ARCHIVE INDEX",
            ])
            return (f"[ {label} ] ".ljust(min(width, len(label) + 4), "═"))[:width]
        if mode < 0.28:
            left_w = max(12, width // 2 - 2)
            left = line_fn()[:left_w].ljust(left_w)
            right = line_fn()[:max(8, width - left_w - 3)]
            return f"{left} │ {right}"[:width]
        if mode < 0.42:
            cols = max(2, min(6, width // 14))
            return "  ".join(f"{self.HEX_WORD(4)} {random.randint(0,9999):04d}" for _ in range(cols))[:width]
        if mode < 0.58:
            chars = " .:-=+*#%@"
            span = max(8, width - 4)
            graph = "".join(chars[min(len(chars) - 1, int(random.random() * (len(chars) - 1)))] for _ in range(span))
            return f"SIG {graph}"[:width]
        return line_fn()[:width]

    def new_area_text_entry(self, mode: str, width: int, state: dict, role: str):
        txt_state = state["text"]
        area_theme = self.area_theme(state)
        is_pharm = area_theme == "pharmacy"
        gen_pool, rcol_pool = self.theme_pools(area_theme)
        if is_pharm and role == "main":
            line_fn = lambda: random.choice(self.p_main_gen_pool)()
            rcol_fn = lambda: random.choice(self.p_main_rcol_pool)()
        else:
            line_fn = lambda: random.choice(gen_pool)()
            rcol_fn = lambda: random.choice(rcol_pool)()

        if mode == "text_scant":
            if is_pharm and role == "sidebar":
                blank_prob = 0.0
            else:
                blank_prob = 0.55 if role == "sidebar" else 0.20
            if random.random() < blank_prob:
                return "", self.curses.color_pair(1), width
            if is_pharm and role == "sidebar":
                txt = random.choice(self.p_sidebar_spike_pool)()
            else:
                txt = rcol_fn()
            cp, bold = self.rcol_colour(txt)
            attr = self.curses.color_pair(cp) | (self.curses.A_BOLD if bold else 0)
            vis = width
        else:
            txt = self.dense_line(width, line_fn=line_fn) if mode == "text_wide" else line_fn()
            cp, bold = self.line_colour(txt, txt_state["theme"])
            attr = self.curses.color_pair(cp) | (self.curses.A_BOLD if bold else 0)
            txt_state["left"] -= 1
            if txt_state["left"] <= 0:
                txt_state["theme"], txt_state["left"] = self.new_paragraph()
            vis = width if mode == "text_wide" else self.rand_line_len(width)

        inject_text = state.get("text_override") or self.inject_text_getter()
        if inject_text:
            txt_state["countdown"] -= 1
            if txt_state["countdown"] <= 0:
                txt_state["countdown"] = random.randint(35, 50)
                txt = self.splice_text(txt, inject_text, width)
        if mode in {"text", "text_scant", "text_wide"}:
            txt = self.leading_blank(txt, width)
            vis = min(width, vis + 1)
        return txt[:width], attr, min(vis, width)

    def load_helptext_lines(self, area: dict):
        if sys.platform == "win32":
            shell_cmd = shutil.which("pwsh") or shutil.which("powershell")
            topics = self.help_text_topics_win
            if shell_cmd is None:
                lines = ["[text_spew] PowerShell not found on PATH."]
                topic = "powershell-missing"
            else:
                topic = topics[area["helptext_topic_idx"] % len(topics)]
                area["helptext_topic_idx"] += 1
                cmd = [
                    shell_cmd,
                    "-NoProfile",
                    "-Command",
                    f"Get-Help {topic} -Full | Out-String -Width 500",
                ]
                try:
                    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    lines = proc.stdout.splitlines()
                except subprocess.CalledProcessError:
                    lines = [f"[text_spew] failed to load PowerShell help for {topic}."]
        else:
            topic = self.help_text_topics_unix[area["helptext_topic_idx"] % len(self.help_text_topics_unix)]
            area["helptext_topic_idx"] += 1
            env = os.environ.copy()
            env["MANPAGER"] = "cat"
            env["PAGER"] = "cat"
            env["MANWIDTH"] = "500"
            try:
                proc = subprocess.run(["man", topic], check=True, capture_output=True, text=True, env=env)
                lines = self.strip_overstrikes(proc.stdout).splitlines()
            except subprocess.CalledProcessError:
                lines = [f"[text_spew] failed to load man page for {topic}."]
        area["helptext_topic"] = topic
        if not lines:
            lines = [f"[text_spew] empty output for {topic}."]
        header = f"[ text_spew :: {topic} ]"
        area["helptext_lines"].extend([header, "", *lines, "", ""])

    def next_helptext_entry(self, width: int, area: dict):
        while len(area["helptext_lines"]) < 40:
            self.load_helptext_lines(area)
        txt = area["helptext_lines"].popleft()
        if not txt:
            return "", self.curses.color_pair(1), width
        cp, bold = 2, False
        if txt.startswith("[ text_spew ::"):
            cp, bold = 2, True
        elif txt.lstrip().startswith(("NAME", "SYNOPSIS", "DESCRIPTION", "PARAMETERS", "INPUTS", "OUTPUTS", "NOTES")):
            cp, bold = 2, False
        attr = self.curses.color_pair(cp) | (self.curses.A_BOLD if bold else 0)
        return txt[:width], attr, width

    @staticmethod
    def effective_mode(area: dict) -> str:
        if area["mode"] == "cycle":
            return area.get("cycle_current") or "text"
        return area["mode"]

    def ensure_cycle(self, area: dict, now: float):
        include_image = bool(area.get("image_paths") or self.image_paths_getter())
        desired = area.get("cycle_widgets") or self.list_cycle_widget_names(include_image)
        if not include_image:
            desired = [name for name in desired if name != "image"]
        desired = [name for name in desired if name not in {"cycle", "blank"}]
        seen = set()
        desired = [name for name in desired if not (name in seen or seen.add(name))]
        if not desired:
            desired = self.list_cycle_widget_names(include_image)
        if desired != area["cycle_catalog"]:
            area["cycle_catalog"] = desired[:]
            area["cycle_order"] = desired[:]
            random.shuffle(area["cycle_order"])
            area["cycle_idx"] = 0
            area["cycle_current"] = area["cycle_order"][0] if area["cycle_order"] else "text"
            area["cycle_next_change"] = cycle_start_deadline(now)
            area["label"] = area["cycle_current"]
            area["next_update"] = 0.0

    def advance_cycle(self, area: dict, now: float, forbidden: set[str] | None = None):
        self.ensure_cycle(area, now)
        forbidden = forbidden or set()
        if not area["cycle_order"]:
            area["cycle_current"] = "text"
            area["label"] = "text"
            area["cycle_next_change"] = next_cycle_deadline(now)
            return
        candidates = [name for name in area["cycle_catalog"] if name not in forbidden and name != area.get("cycle_current")]
        if not candidates:
            candidates = [name for name in area["cycle_catalog"] if name != area.get("cycle_current")]
        if not candidates:
            candidates = area["cycle_catalog"][:]
        next_widget = random.choice(candidates) if candidates else "text"
        area["cycle_current"] = next_widget
        if next_widget in area["cycle_order"]:
            area["cycle_idx"] = area["cycle_order"].index(next_widget)
        area["label"] = area["cycle_current"]
        area["cycle_next_change"] = next_cycle_deadline(now)
        area["next_update"] = 0.0

    def ensure_text_buffer(self, area: dict, rows: int, mode: str, width: int, role: str, now: float):
        buf = area["buf"]
        while len(buf) < rows:
            if mode == "text_spew":
                buf.append(self.next_helptext_entry(width, area))
            else:
                buf.append(self.new_area_text_entry(mode, width, area, role))
        while len(buf) > rows:
            buf.pop(0)
        if mode == "text_wide":
            resolve_direction_motion(area, "text_wide", now)

    def scroll_text_buffer(self, area: dict, mode: str, width: int, role: str, direction: str):
        if not area["buf"]:
            return
        next_entry = self.next_helptext_entry(width, area) if mode == "text_spew" else self.new_area_text_entry(mode, width, area, role)
        if direction == "up":
            area["buf"].pop(0)
            area["buf"].append(next_entry)
        else:
            area["buf"].pop()
            area["buf"].insert(0, next_entry)

    def safe_row_width(self, y: int, r: int, x: int, width: int) -> int:
        max_rows, max_cols = self.stdscr.getmaxyx()
        abs_row = y + r
        if width <= 0 or x >= max_cols or abs_row < 0 or abs_row >= max_rows:
            return 0
        clipped = min(width, max_cols - x)
        if abs_row == max_rows - 1 and x + clipped >= max_cols:
            clipped = max(0, max_cols - x - 1)
        return clipped

    def repaint_text_buffer(self, buf, nrows, y, x, width):
        blank = " " * width
        for r in range(nrows):
            safe_w = self.safe_row_width(y, r, x, width)
            if safe_w <= 0:
                continue
            txt, attr, vis = buf[r]
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

    def handles_mode(self, mode: str) -> bool:
        return mode in self.TEXT_MODES

    def ensure(self, area: dict, rows: int, width: int, role: str, now: float | None = None) -> None:
        now = 0.0 if now is None else now
        mode = self.effective_mode(area)
        if mode in self.TEXT_MODES:
            self.ensure_text_buffer(area, rows, mode, width, role, now)

    def update(self, area: dict, rows: int, width: int, role: str, now: float, dt: float) -> None:
        del rows, dt
        mode = self.effective_mode(area)
        if mode not in self.TEXT_MODES:
            return
        if mode == "text_spew":
            self.scroll_text_buffer(area, mode, width, role, "up")
        elif mode == "text_wide":
            motion = resolve_direction_motion(area, "text_wide", now)
            if motion < 0:
                self.scroll_text_buffer(area, mode, width, role, "down")
            elif motion > 0:
                self.scroll_text_buffer(area, mode, width, role, "up")
        else:
            self.scroll_text_buffer(area, mode, width, role, "up")

    def render(self, area: dict, rows: int, y: int, x: int, width: int, role: str) -> None:
        del role
        mode = self.effective_mode(area)
        if mode in self.TEXT_MODES:
            self.repaint_text_buffer(area["buf"], rows, y, x, width)
