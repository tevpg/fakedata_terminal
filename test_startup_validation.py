#!/usr/bin/env python3

from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

from cli_config import prepare_runtime_config
import fakedata_terminal
from fakedata_terminal import _export_screen_definition
from scene_config import widget_showcase_pages
from widget_metadata import widget_description


ROOT_DIR = Path(__file__).resolve().parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "fakedata_terminal", *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
    )


class StartupValidationTests(unittest.TestCase):
    def test_widget_metadata_descriptions_are_available(self) -> None:
        self.assertEqual(
            widget_description("gauge"),
            "Large gauge-style instrumentation with dial motion and text.",
        )

    def test_widget_showcase_pages_follow_packaged_order(self) -> None:
        pages = widget_showcase_pages()
        self.assertGreaterEqual(len(pages), 5)
        self.assertEqual([page["widget"] for page in pages[:5]], ["blank", "title_card", "text", "text_scant", "text_wide"])

    def test_prepare_runtime_builds_interactive_widget_showcase_state(self) -> None:
        runtime = prepare_runtime_config(
            ["--widgets"],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        showcase = runtime["screen_showcase"]
        self.assertTrue(showcase["active"])
        self.assertEqual(showcase["mode"], "widgets")
        self.assertIn(str((ROOT_DIR / "data" / "widget_showcase.yaml").resolve()), showcase["config_paths"])
        self.assertEqual(runtime["config_screen"]["showcase_widget"], "blank")
        self.assertEqual(showcase["states"]["blank"]["text_values"], ["", "STATUS HOLD", "Stand by"])
        self.assertEqual(showcase["states"]["gauge"]["colour_values"], ["cyan", "yellow", "multi"])
        self.assertEqual(showcase["states"]["gauge"]["direction"], "random")
        self.assertTrue(showcase["states"]["image"]["image_paths"][0].endswith("/data/geom_33_torus.png"))

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

    def test_blank_widget_resolves_with_speed_direction_and_colour(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=blank",
                "--region-widget", "P2=text",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-speed", "P1=50",
                "--region-direction", "P1=random",
                "--region-colour", "P1=multi",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["mode"], "blank")
        self.assertEqual(areas["P1"]["speed"], 50)
        self.assertEqual(areas["P1"]["direction"], "random")
        self.assertEqual(areas["P1"]["colour"], "multi")

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
        parsed = yaml.safe_load(exported["yaml"])
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
        parsed = yaml.safe_load(exported["yaml"])
        screen_body = next(iter(parsed["screens"].values()))
        self.assertEqual(screen_body["regions"]["P1"]["density"], 50)
        self.assertEqual(screen_body["regions"]["P2"]["density"], 50)
        self.assertEqual(screen_body["regions"]["P3"]["density"], 50)
        self.assertNotIn("density", screen_body["regions"]["P4"])

    def test_exported_screen_report_includes_replay_command(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=gauge",
                "--region-widget", "P4=matrix",
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
        parsed = yaml.safe_load(exported["yaml"])
        self.assertEqual(len(parsed["screens"]), 1)
        self.assertIn("python3 -m fakedata_terminal \\", exported["command"])
        self.assertIn("--screen-layout 2x2 \\", exported["command"])
        self.assertIn("--region-widget P1=text", exported["command"])
        self.assertIn("--region-widget P4=matrix", exported["command"])

    def test_exported_screen_report_marks_cli_limitations(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=cycle",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        runtime["config_screen"]["areas"][0]["cycle_widgets"] = ["text", "matrix"]
        runtime["config_screen"]["areas"][0].setdefault("modifier_sources", {})["cycle"] = "region"
        exported = _export_screen_definition(
            runtime["config_screen"],
            area_states={},
            current_base_speed=runtime["speed"],
            current_speed_for_area=lambda _state, _role: runtime["speed"],
        )
        self.assertIsNotNone(exported)
        self.assertIn("Closest command line recreation only", exported["command"])
        self.assertIn("P1 cycle.widgets", exported["command"])

    def test_exported_screen_report_omits_default_cycle_widgets(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=cycle",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
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
        parsed = yaml.safe_load(exported["yaml"])
        screen_body = next(iter(parsed["screens"].values()))
        self.assertNotIn("cycle", screen_body["regions"]["P1"])
        self.assertIn("default cycle list", exported["command"])
        self.assertNotIn("P1 cycle.widgets", exported["command"])
        self.assertIn("--region-widget P1=cycle", exported["command"])

    def test_exported_screen_report_shortens_data_image_paths_in_cli(self) -> None:
        exported = _export_screen_definition(
            {
                "layout": "2x2",
                "glitch": 0.0,
                "theme": "science",
                "text": "",
                "speed": 55,
                "direction": "forward",
                "areas": [
                    {
                        "name": "P1",
                        "panels": ["P1"],
                        "x": 0.0,
                        "y": 0.0,
                        "mode": "image",
                        "theme": "science",
                        "direction": "forward",
                        "image_paths": [str(ROOT_DIR / "data" / "geom_33_torus.png")],
                    },
                ],
            },
            area_states={},
            current_base_speed=55,
            current_speed_for_area=lambda _state, _role: 55,
        )
        self.assertIsNotNone(exported)
        self.assertIn("--region-image P1=geom_33_torus.png", exported["command"])
        self.assertNotIn("--region-image P1=data/geom_33_torus.png", exported["command"])

    def test_save_screen_flags_default_to_stdout_when_present_without_file(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=gauge",
                "--region-widget", "P4=matrix",
                "--save-screen-yaml",
                "--save-screen-command",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        self.assertEqual(runtime["save_screen_yaml"], "-")
        self.assertEqual(runtime["save_screen_command"], "-")

    def test_save_screen_flags_accept_output_paths(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=gauge",
                "--region-widget", "P4=matrix",
                "--save-screen-yaml", "saved.yaml",
                "--save-screen-command", "saved.sh",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        self.assertEqual(runtime["save_screen_yaml"], "saved.yaml")
        self.assertEqual(runtime["save_screen_command"], "saved.sh")

    def test_ignore_keyboard_flag_enables_runtime_keyboard_lock(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=gauge",
                "--region-widget", "P4=matrix",
                "--ignore-keyboard",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        self.assertTrue(runtime["ignore_keyboard"])

    def test_performance_flag_alias_enables_runtime_keyboard_lock(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=text",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=gauge",
                "--region-widget", "P4=matrix",
                "--performance",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        self.assertTrue(runtime["ignore_keyboard"])

    def test_run_only_writes_requested_exit_artifacts(self) -> None:
        export_payload = {
            "yaml": "screens:\n  sample:\n    layout: 2x2\n",
            "command": "python3 -m fakedata_terminal --screen-layout 2x2\n",
        }
        with tempfile.NamedTemporaryFile("r+", suffix=".yaml", delete=False) as yaml_handle:
            yaml_path = yaml_handle.name
        try:
            with mock.patch.object(fakedata_terminal.curses, "wrapper", return_value=export_payload):
                stdout_buffer = io.StringIO()
                with redirect_stdout(stdout_buffer):
                    result = fakedata_terminal.run(
                        [
                            "--screen-layout", "2x2",
                            "--region-widget", "P1=text",
                            "--region-widget", "P2=blank",
                            "--region-widget", "P3=gauge",
                            "--region-widget", "P4=matrix",
                            "--save-screen-yaml", yaml_path,
                        ]
                    )
            self.assertEqual(result, 0)
            self.assertNotIn("screens:\n  sample", stdout_buffer.getvalue())
            self.assertIn("python3 -m fakedata_terminal --screen-layout 2x2", stdout_buffer.getvalue())
            self.assertIn("terminated.", stdout_buffer.getvalue())
            self.assertEqual(Path(yaml_path).read_text(encoding="utf-8"), export_payload["yaml"])
        finally:
            Path(yaml_path).unlink(missing_ok=True)

    def test_append_text_file_separates_saved_yaml_blocks(self) -> None:
        with tempfile.NamedTemporaryFile("r+", suffix=".yaml", delete=False) as handle:
            path = Path(handle.name)
        try:
            fakedata_terminal._append_text_file(str(path), "screens:\n  first:\n    layout: 2x2\n")
            fakedata_terminal._append_text_file(str(path), "screens:\n  second:\n    layout: 3x2\n")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "screens:\n  first:\n    layout: 2x2\n\nscreens:\n  second:\n    layout: 3x2\n",
            )
        finally:
            path.unlink(missing_ok=True)

    def test_file_already_ends_with_block_detects_duplicate_yaml(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("screens:\n  first:\n    layout: 2x2\n\nscreens:\n  second:\n    layout: 3x2\n")
            path = Path(handle.name)
        try:
            self.assertTrue(
                fakedata_terminal._file_already_ends_with_block(
                    str(path),
                    "screens:\n  second:\n    layout: 3x2\n",
                )
            )
            self.assertFalse(
                fakedata_terminal._file_already_ends_with_block(
                    str(path),
                    "screens:\n  third:\n    layout: 4x2\n",
                )
            )
        finally:
            path.unlink(missing_ok=True)

    def test_run_shows_performance_mode_warning_before_startup(self) -> None:
        with mock.patch.object(fakedata_terminal.time, "sleep") as mock_sleep:
            with mock.patch.object(fakedata_terminal.curses, "wrapper", return_value=None):
                stdout_buffer = io.StringIO()
                with redirect_stdout(stdout_buffer):
                    result = fakedata_terminal.run(
                        [
                            "--screen-layout", "2x2",
                            "--region-widget", "P1=text",
                            "--region-widget", "P2=blank",
                            "--region-widget", "P3=gauge",
                            "--region-widget", "P4=matrix",
                            "--performance",
                        ]
                    )
        self.assertEqual(result, 0)
        self.assertIn("\n\nPerformance mode: press/hold Esc to exit\n\n", stdout_buffer.getvalue())
        mock_sleep.assert_any_call(2.0)

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

    def test_title_card_widget_resolves_with_speed(self) -> None:
        runtime = prepare_runtime_config(
            [
                "--screen-layout", "2x2",
                "--region-widget", "P1=title_card",
                "--region-widget", "P2=blank",
                "--region-widget", "P3=text",
                "--region-widget", "P4=gauge",
                "--region-text", "P1=ALERT",
                "--region-speed", "P1=50",
            ],
            image_module=None,
            image_checker=lambda: False,
            demo_scenes=[],
        )
        areas = {area["name"]: area for area in runtime["config_screen"]["areas"]}
        self.assertEqual(areas["P1"]["speed"], 50)

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
