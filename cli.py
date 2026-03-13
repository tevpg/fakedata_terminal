"""CLI launcher for package and script entrypoints."""

import runpy
import sys


def main(prog_name: str | None = None) -> int:
    original_argv0 = sys.argv[0]
    if prog_name:
        sys.argv[0] = prog_name
    try:
        runpy.run_module("fakedata_terminal.fakedata_terminal", run_name="__main__")
    finally:
        sys.argv[0] = original_argv0
    return 0
