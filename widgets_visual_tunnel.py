"""Tunnel widget renderer extracted from VisualWidgets."""

from __future__ import annotations

import random

try:
    from .runtime_support import tunnel_palette_specs, COLOUR_PAIR_INDICES
except ImportError:
    from runtime_support import tunnel_palette_specs, COLOUR_PAIR_INDICES


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

    def ensure_multi_attrs(self, area: dict, colour_spec: str, palette_specs: list[str]) -> list[int]:
        layers = area.get("tunnel_layers") or []
        colour_sig = (colour_spec, len(layers), tuple(palette_specs))
        if area.get("tunnel_colour_sig") == colour_sig and area.get("tunnel_band_attrs"):
            return area["tunnel_band_attrs"]
        multi_attrs = [
            self.colour_attr_from_spec(self.curses, spec, default=spec, bold=True)
            for spec in palette_specs
            if spec in COLOUR_PAIR_INDICES
        ]
        if not multi_attrs:
            area["tunnel_colour_sig"] = colour_sig
            area["tunnel_band_attrs"] = []
            return []
        band_attrs = [random.choice(multi_attrs) for _ in range(max(1, len(layers)))]
        area["tunnel_colour_sig"] = colour_sig
        area["tunnel_band_attrs"] = band_attrs
        return band_attrs

    def ensure(self, area: dict, rows: int, width: int) -> None:
        sig = (rows, width)
        if area["tunnel_sig"] == sig:
            return
        area["tunnel_sig"] = sig
        area["tunnel_layers"] = self.build_tunnel_layers(rows, width)
        area["tunnel_colour_sig"] = None
        area["tunnel_band_attrs"] = []

    def update(self, area: dict, rows: int, width: int) -> None:
        self.ensure(area, rows, width)

    def render(self, area: dict, rows: int, y: int, x: int, width: int) -> None:
        self.ensure(area, rows, width)
        colour_spec = self.normalize_colour_spec(area.get("colour_override")) or "multi"
        motion = self.resolved_direction_motion(area)
        single_attr = self.colour_attr_from_spec(self.curses, colour_spec, default="green", bold=True)
        palette_specs = tunnel_palette_specs(colour_spec)
        band_attrs = self.ensure_multi_attrs(area, colour_spec, palette_specs)
        self.repaint_nested_layers(
            area.get("tunnel_layers") or [],
            area,
            rows,
            y,
            x,
            width,
            attr_for_band=(
                (lambda _band_idx: single_attr)
                if colour_spec not in {"multi", "multi-all", "multi-dim", "multi-normal", "multi-bright"} or not band_attrs
                else (lambda band_idx: band_attrs[band_idx % len(band_attrs)])
            ),
            outward=(motion >= 0),
        )
        self.draw_centered_overlay(area, max(0, rows // 2), y, x, width, rows=rows, anchor="center")
