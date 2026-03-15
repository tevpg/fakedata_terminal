"""Tunnel widget renderer extracted from VisualWidgets."""

from __future__ import annotations


class TunnelWidget:
    def __init__(
        self,
        *,
        curses_module,
        normalize_colour_spec,
        colour_attr_from_spec,
        resolved_direction_motion,
        repaint_nested_layers,
        draw_centered_overlay,
        build_tunnel_layers,
    ):
        self.curses = curses_module
        self.normalize_colour_spec = normalize_colour_spec
        self.colour_attr_from_spec = colour_attr_from_spec
        self.resolved_direction_motion = resolved_direction_motion
        self.repaint_nested_layers = repaint_nested_layers
        self.draw_centered_overlay = draw_centered_overlay
        self.build_tunnel_layers = build_tunnel_layers

    def ensure(self, area: dict, rows: int, width: int) -> None:
        sig = (rows, width)
        if area["tunnel_sig"] == sig:
            return
        area["tunnel_sig"] = sig
        area["tunnel_layers"] = self.build_tunnel_layers(rows, width)

    def update(self, area: dict, rows: int, width: int) -> None:
        self.ensure(area, rows, width)

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "multi"
        motion = self.resolved_direction_motion(area)
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
            outward=(motion >= 0),
        )
        self.draw_centered_overlay(area, max(0, rows // 2), y, x, width, rows=rows, anchor="center")
