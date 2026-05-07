"""Package entrypoints and runtime re-exports for FakeData Terminal."""

from importlib import import_module

from .cli import main

_RUNTIME_EXPORTS = {
    "curses",
    "time",
    "run",
    "_append_text_file",
    "_export_screen_definition",
    "_file_already_ends_with_block",
}

__all__ = ["main", *sorted(_RUNTIME_EXPORTS)]


def __getattr__(name: str):
    if name not in _RUNTIME_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    runtime = import_module(".fakedata_terminal", __name__)
    value = getattr(runtime, name)
    globals()[name] = value
    return value
