#!/usr/bin/env python3

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from layout_support import sync_cycle_start_modes
from timing_support import (
    schedule_next,
    shift_deadline,
    widget_interval,
)
from widget_metadata import set_widget_config_paths


ROOT_DIR = Path(__file__).resolve().parent


class TimingSupportTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_widget_config_paths(None)

    def test_widget_interval_increases_with_lower_speed(self) -> None:
        fast = widget_interval("gauge", 100)
        slow = widget_interval("gauge", 1)
        self.assertGreater(slow, fast)

    def test_widget_interval_for_blank_is_infinite(self) -> None:
        self.assertAlmostEqual(widget_interval("blank", 1), 15.0)
        self.assertAlmostEqual(widget_interval("blank", 50), 0.1, places=2)
        self.assertLess(widget_interval("blank", 100), 0.03)

    def test_schedule_next_catches_up_after_far_miss(self) -> None:
        interval = 0.5
        self.assertEqual(schedule_next(0.0, 10.0, interval), 10.5)
        self.assertEqual(schedule_next(1.0, 10.0, interval), 10.5)
        self.assertEqual(schedule_next(9.8, 10.0, interval), 10.3)

    def test_shift_deadline_preserves_nonpositive_and_infinite(self) -> None:
        self.assertEqual(shift_deadline(0.0, 5.0), 0.0)
        self.assertEqual(shift_deadline(-3.0, 5.0), -3.0)
        self.assertTrue(math.isinf(shift_deadline(math.inf, 5.0)))
        self.assertEqual(shift_deadline(10.0, 2.5), 12.5)

    def test_sync_cycle_start_modes_uses_configured_cycle_jitter(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "widgets:\n"
                "  cycle:\n"
                "    behavior:\n"
                "      controller:\n"
                "        start_jitter_range_seconds: [2.5, 2.5]\n"
            )
            config_path = Path(handle.name)
        try:
            set_widget_config_paths((str(ROOT_DIR / "data" / "widgets.yaml"), str(config_path)))
            area_specs = [{"name": "P1"}, {"name": "P2"}]
            area_states = {
                "P1": {
                    "mode": "cycle",
                    "cycle_catalog": ["text", "matrix"],
                    "cycle_order": ["text", "matrix"],
                    "cycle_current": "text",
                    "cycle_idx": 0,
                    "cycle_next_change": 0.0,
                    "next_update": 1.0,
                    "label": None,
                }
                ,
                "P2": {
                    "mode": "cycle",
                    "cycle_catalog": ["text", "matrix"],
                    "cycle_order": ["text", "matrix"],
                    "cycle_current": "text",
                    "cycle_idx": 0,
                    "cycle_next_change": 0.0,
                    "next_update": 1.0,
                    "label": None,
                },
            }

            def ensure_cycle(area: dict, now: float) -> None:
                del now
                area["cycle_catalog"] = ["text", "matrix"]
                area["cycle_order"] = ["text", "matrix"]
                area["cycle_current"] = area.get("cycle_current") or "text"

            sync_cycle_start_modes(area_specs, area_states, ensure_cycle, now=100.0)
            self.assertEqual(area_states["P2"]["cycle_current"], "matrix")
            self.assertEqual(area_states["P2"]["cycle_next_change"], 102.5)
            self.assertEqual(area_states["P2"]["next_update"], 0.0)
        finally:
            config_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
