#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from cli_config import prepare_runtime_config
from fakedata_terminal import _export_screen_definition


ROOT_DIR = Path(__file__).resolve().parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "fakedata_terminal", *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
    )


class StartupValidationTests(unittest.TestCase):
    def test_speed_precedence_widget_defaults_region_and_cli(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "widgets:\n"
                "  text:\n"
                "    defaults:\n"
                "      speed: 11\n"
                "screens:\n"
                "  localtest:\n"
                "    layout: 2x2\n"
                "    regions:\n"
                "      P1:\n"
                "        widget: text\n"
                "      P2:\n"
                "        widget: text\n"
                "        speed: 33\n"
                "      P3:\n"
                "        widget: text\n"
                "      P4:\n"
                "        widget: text\n"
            )
            config_path = Path(handle.name)
        try:
            runtime = prepare_runtime_config(
                ["--config", str(config_path), "--screen", "localtest", "--region-speed", "P1=44"],
                image_module=None,
                image_checker=lambda: False,
                demo_scenes=[],
            )
        finally:
            config_path.unlink(missing_ok=True)
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["speed"], 44)
        self.assertEqual(areas["P2"]["speed"], 33)
        self.assertEqual(areas["P3"]["speed"], 11)
        self.assertEqual(areas["P4"]["speed"], 11)

    def test_colour_precedence_config_default_cli_default_and_region(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "defaults:\n"
                "  colour: yellow\n"
                "screens:\n"
                "  localtest:\n"
                "    layout: 2x2\n"
                "    regions:\n"
                "      P1:\n"
                "        widget: blank\n"
                "        colour: green\n"
                "      P2:\n"
                "        widget: blank\n"
                "      P3:\n"
                "        widget: blank\n"
                "      P4:\n"
                "        widget: blank\n"
            )
            config_path = Path(handle.name)
        try:
            runtime = prepare_runtime_config(
                [
                    "--config", str(config_path),
                    "--screen", "localtest",
                    "--default-colour", "bright-cyan",
                    "--region-colour", "P2=red",
                ],
                image_module=None,
                image_checker=lambda: False,
                demo_scenes=[],
            )
        finally:
            config_path.unlink(missing_ok=True)
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["colour"], "green")
        self.assertEqual(areas["P2"]["colour"], "red")
        self.assertEqual(areas["P3"]["colour"], "bright-cyan")
        self.assertEqual(areas["P4"]["colour"], "bright-cyan")

    def test_prepare_runtime_allows_inert_leftover_modifiers_after_widget_override(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "screens:\n"
                "  localtest:\n"
                "    layout: 2x2\n"
                "    regions:\n"
                "      P1:\n"
                "        widget: gauge\n"
                "        direction: backward\n"
                "      P2:\n"
                "        widget: text\n"
                "      P3:\n"
                "        widget: text\n"
                "      P4:\n"
                "        widget: text\n"
            )
            config_path = Path(handle.name)
        try:
            runtime = prepare_runtime_config(
                ["--config", str(config_path), "--screen", "localtest", "--region-widget", "P1=life"],
                image_module=None,
                image_checker=lambda: False,
                demo_scenes=[],
            )
        finally:
            config_path.unlink(missing_ok=True)
        p1 = next(area for area in runtime["config_screen"]["areas"] if area["name"] == "P1")
        self.assertEqual(p1["mode"], "life")

    def test_no_args_shows_orientation_message(self) -> None:
        result = run_cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("creates text screens of fake data displays for cinema backgrounds", result.stdout)
        self.assertIn("--screens", result.stdout)
        self.assertIn("--widgets", result.stdout)

    def test_list_succeeds(self) -> None:
        result = run_cli("--list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Screens (--screens to view all the preset screens)", result.stdout)
        self.assertIn("Config files:", result.stdout)
        self.assertIn("1x3", result.stdout)
        self.assertIn("2x4", result.stdout)
        self.assertIn("crash", result.stdout)
        self.assertIn("whorl", result.stdout)
        self.assertIn("orbit", result.stdout)
        self.assertIn("rotate", result.stdout)
        self.assertIn("spiral", result.stdout)
        self.assertIn("title_card", result.stdout)

    def test_crash_widget_resolves_with_metadata_default_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=crash",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-theme", "P1=finance",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "crash")
        self.assertEqual(areas["P1"]["theme"], "finance")
        self.assertEqual(areas["P1"]["colour"], "multi-all")

    def test_rotate_widget_resolves_with_direction_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=rotate",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-direction", "P1=backward",
                "--region-colour", "P1=bright-cyan",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "rotate")
        self.assertEqual(areas["P1"]["direction"], "backward")
        self.assertEqual(areas["P1"]["colour"], "bright-cyan")

    def test_rotate_widget_resolves_with_density(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=rotate",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-density", "P1=72",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "rotate")
        self.assertEqual(areas["P1"]["density"], 72)

    def test_exported_screen_yaml_includes_density(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=rotate",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-density", "P1=72",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        exported = _export_screen_definition(
            runtime["config_screen"],
            area_states={},
            current_base_speed=runtime["speed"],
            current_speed_for_area=lambda _state, _role: runtime["speed"],
        )
        self.assertIsNotNone(exported)
        parsed = yaml.safe_load(exported)
        screens = parsed["screens"]
        self.assertEqual(len(screens), 1)
        screen_body = next(iter(screens.values()))
        self.assertEqual(screen_body["regions"]["P1"]["density"], 72)

    def test_exported_screen_yaml_includes_implicit_default_density(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=spiral",
                "--region-widget", "P2=whorl",
                "--region-widget", "P3=orbit",
                "--region-widget", "P4=crash",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        exported = _export_screen_definition(
            runtime["config_screen"],
            area_states={},
            current_base_speed=runtime["speed"],
            current_speed_for_area=lambda _state, _role: runtime["speed"],
        )
        self.assertIsNotNone(exported)
        parsed = yaml.safe_load(exported)
        screen_body = next(iter(parsed["screens"].values()))
        self.assertEqual(screen_body["regions"]["P1"]["density"], 50)
        self.assertEqual(screen_body["regions"]["P2"]["density"], 50)
        self.assertEqual(screen_body["regions"]["P3"]["density"], 50)
        self.assertNotIn("density", screen_body["regions"]["P4"])

    def test_orbit_widget_resolves_with_direction_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=orbit",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-direction", "P1=backward",
                "--region-colour", "P1=bright-magenta",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "orbit")
        self.assertEqual(areas["P1"]["direction"], "backward")
        self.assertEqual(areas["P1"]["colour"], "bright-magenta")

    def test_whorl_widget_resolves_with_direction_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=whorl",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-direction", "P1=forward",
                "--region-colour", "P1=bright-magenta",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "whorl")
        self.assertEqual(areas["P1"]["direction"], "forward")
        self.assertEqual(areas["P1"]["colour"], "bright-magenta")

    def test_spiral_widget_resolves_with_direction_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=spiral",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-direction", "P1=backward",
                "--region-colour", "P1=bright-blue",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "spiral")
        self.assertEqual(areas["P1"]["direction"], "backward")
        self.assertEqual(areas["P1"]["colour"], "bright-blue")

    def test_title_card_widget_resolves_with_text_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=title_card",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-text", "P1=ALERT",
                "--region-colour", "P1=multi",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "title_card")
        self.assertEqual(areas["P1"]["text"], "ALERT")
        self.assertEqual(areas["P1"]["colour"], "multi-bright")

    def test_title_card_widget_defaults_to_bright_green(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=title_card",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-text", "P1=ALERT",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["colour"], "bright-green")

    def test_layouts_succeeds(self) -> None:
        result = run_cli("--layouts")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Layout: 1x3", result.stdout)
        self.assertIn("Layout: 2x4", result.stdout)

    def test_region_text_rejected_for_life_widget(self) -> None:
        result = run_cli(
            "--screen-layout", "2x2",
            "--region-widget", "P1=life",
            "--region-widget", "P2=blank",
            "--region-widget", "P3=text",
            "--region-widget", "P4=gauge",
            "--region-text", "P1=hello",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-text is not valid for widget 'life' in region 'P1'", result.stderr)

    def test_region_modifier_target_requires_matching_assignment(self) -> None:
        result = run_cli(
            "--screen-layout", "2x2",
            "--region-widget", "P1=text",
            "--region-text", "P2=hello",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-text target 'P2' has no matching assignment", result.stderr)

    def test_region_density_rejected_for_text_widget(self) -> None:
        result = run_cli(
            "--screen-layout", "2x2",
            "--region-widget", "P1=text",
            "--region-widget", "P2=blank",
            "--region-widget", "P3=blank",
            "--region-widget", "P4=blank",
            "--region-density", "P1=75",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-density is not valid for widget 'text' in region 'P1'", result.stderr)

    def test_region_widget_partial_overlap_is_rejected(self) -> None:
        result = run_cli(
            "--screen-layout", "3x3",
            "--region-widget", "L2=text",
            "--region-widget", "P1=gauge",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-widget P1=gauge partially overlaps existing region", result.stderr)

    def test_region_override_unknown_panel_is_rejected(self) -> None:
        result = run_cli(
            "--screen-layout", "2x2",
            "--region-widget", "P9=text",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-widget references unknown region or panel spec 'P9'", result.stderr)

    def test_removed_gauges_widget_rejected(self) -> None:
        result = run_cli(
            "--screen-layout", "2x2",
            "--region-widget", "P1=gauges",
            "--region-widget", "P2=blank",
            "--region-widget", "P3=text",
            "--region-widget", "P4=gauge",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("uses unsupported widget 'gauges'", result.stderr)

    def test_region_image_glob_must_match_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fdt-emptyglob-") as tmpdir:
            result = run_cli(
                "--screen-layout", "2x2",
                "--region-widget", "P1=image",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-image", f"P1={tmpdir}/*.png",
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--region-image glob for region 'P1' matched no files", result.stderr)

    def test_unreadable_image_fails_before_rendering(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("not an image\n")
            temp_path = Path(handle.name)
        try:
            result = run_cli(
                "--screen-layout", "2x2",
                "--region-widget", "P1=image",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-image", f"P1={temp_path}",
            )
        finally:
            temp_path.unlink(missing_ok=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("image file is unreadable", result.stderr)

    def test_image_widget_dependency_failure_happens_before_render(self) -> None:
        image_path = ROOT_DIR / "data" / "geom_33_torus.png"
        with self.assertRaises(SystemExit) as ctx:
            prepare_runtime_config(
                [
                    "--screen-layout", "2x2",
                    "--region-widget", "P1=image",
                    "--region-widget", "P2=blank",
                    "--region-widget", "P3=text",
                    "--region-widget", "P4=gauge",
                    "--region-image", f"P1={image_path}",
                ],
                image_module=None,
                image_checker=lambda: False,
                demo_scenes=[],
            )
        self.assertEqual(ctx.exception.code, 2)

    def test_disabled_widget_overlay_fails_validation(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "widgets:\n"
                "  blank:\n"
                "    enabled: false\n"
                "defaults:\n"
                "  widget: blank\n"
                "screens:\n"
                "  localtest:\n"
                "    layout: 2x2\n"
                "    regions:\n"
                "      P1:\n"
                "        widget: blank\n"
                "      P2:\n"
                "        widget: text\n"
                "      P3:\n"
                "        widget: text\n"
                "      P4:\n"
                "        widget: text\n"
            )
            config_path = Path(handle.name)
        try:
            result = run_cli("--config", str(config_path), "--list")
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("configuration validation failed:", result.stderr)
        self.assertIn("defaults.widget references disabled widget 'blank'", result.stderr)

    def test_duplicate_cycle_widgets_fail_resolved_screen_validation(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "screens:\n"
                "  localtest:\n"
                "    layout: 2x2\n"
                "    regions:\n"
                "      P1:\n"
                "        widget: cycle\n"
                "        cycle:\n"
                "          widgets: [gauge, gauge]\n"
                "      P2:\n"
                "        widget: text\n"
                "      P3:\n"
                "        widget: text\n"
                "      P4:\n"
                "        widget: text\n"
            )
            config_path = Path(handle.name)
        try:
            result = run_cli("--config", str(config_path), "--screen", "localtest")
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("repeats cycle widget 'gauge'", result.stderr)

    def test_screen_layout_without_default_widget_rejects_unassigned_panels(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(
                "defaults:\n"
                "  widget: null\n"
            )
            config_path = Path(handle.name)
        try:
            result = run_cli(
                "--config", str(config_path),
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
            )
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("leaves panels unassigned (P2, P3, P4) and no default widget is configured", result.stderr)


if __name__ == "__main__":
    unittest.main()
