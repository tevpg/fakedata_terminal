#!/usr/bin/env python3
"""Preview candidate FakeData Terminal colour palettes in a plain terminal."""

from __future__ import annotations

import argparse
import sys


RESET = "\033[0m"
BOLD = "\033[1m"

CURRENT_PALETTE = [
    ("black", 0),
    ("red", 160),
    ("orange", 208),
    ("amber", 172),
    ("yellow", 226),
    ("green", 34),
    ("lime", 82),
    ("cyan", 51),
    ("blue", 39),
    ("magenta", 201),
    ("purple", 141),
    ("pink", 213),
    ("white", 15),
    ("grey", 245),
]

PROPOSED_SINGLES = {
    "black": 0,
}

PROPOSED_TRIADS = {
    "red": {"dim": 88, "normal": 160, "bright": 196},
    "green": {"dim": 22, "normal": 34, "bright": 82},
    "blue": {"dim": 18, "normal": 33, "bright": 39},
    "cyan": {"dim": 23, "normal": 44, "bright": 51},
    "magenta": {"dim": 90, "normal": 165, "bright": 201},
    "yellow": {"dim": 136, "normal": 220, "bright": 226},
    "orange": {"dim": 130, "normal": 208, "bright": 214},
    "purple": {"dim": 54, "normal": 93, "bright": 141},
    "white": {"dim": 245, "normal": 252, "bright": 15},
}

PROPOSED_ALIASES = {
    "grey": "dim-white",
    "gray": "dim-white",
    "pink": "bright-magenta",
    "amber": "dim-orange",
    "black": "black",
}


def fg(code: int) -> str:
    return f"\033[38;5;{code}m"


def bg(code: int) -> str:
    return f"\033[48;5;{code}m"


def sample(label: str, code: int, *, bold: bool = False) -> str:
    weight = BOLD if bold else ""
    swatch_fg = 15 if code in {0, 16} else 0
    swatch = f"{bg(code)}{fg(swatch_fg)} .. {RESET}"
    return f"{swatch} {weight}{fg(code)}{label}{RESET} ({code})"


def show_current() -> None:
    print("Current palette")
    print("--------------")
    for name, code in CURRENT_PALETTE:
        print(sample(name, code, bold=(name in {"yellow", "white"})))
    print()


def show_proposed() -> None:
    print("Proposed triads")
    print("---------------")
    print("RGB, CMY, orange, purple, and white")
    print()
    print("Singles")
    print("-------")
    for name, code in PROPOSED_SINGLES.items():
        print(f"{name}:")
        print(f"  {sample(name, code)}")
    print()
    for base_name, variants in PROPOSED_TRIADS.items():
        print(f"{base_name}:")
        print(f"  {sample(f'dim-{base_name}', variants['dim'])}")
        print(f"  {sample(base_name, variants['normal'])}")
        print(f"  {sample(f'bright-{base_name}', variants['bright'], bold=(base_name in {'yellow', 'white'}))}")
    print()

    print("Proposed aliases")
    print("----------------")
    for alias, target in PROPOSED_ALIASES.items():
        if "-" in target:
            target_name, target_base = target.split("-", 1)
            code = PROPOSED_TRIADS[target_base][target_name]
        elif target in PROPOSED_SINGLES:
            code = PROPOSED_SINGLES[target]
        else:
            code = PROPOSED_TRIADS[target]["normal"]
        print(f"{alias:<8} -> {sample(target, code, bold=target in {'bright-yellow', 'bright-white'})}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview candidate dim/normal/bright colour mappings."
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Show the current palette used by FakeData Terminal.",
    )
    parser.add_argument(
        "--proposed",
        action="store_true",
        help="Show the proposed dim/normal/bright palette.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not sys.stdout.isatty():
        print("Run this script in a terminal to see ANSI colour samples.")
        return 1

    render_current = args.current or not args.proposed
    render_proposed = args.proposed or not args.current

    if render_current:
        show_current()
    if render_proposed:
        show_proposed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
