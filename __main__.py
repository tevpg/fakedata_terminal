"""Allow `python -m fakedata_terminal`."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main("python3 -m fakedata_terminal"))
