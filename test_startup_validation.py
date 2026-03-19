#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "fakedata_terminal", *args],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
    )


class StartupValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
