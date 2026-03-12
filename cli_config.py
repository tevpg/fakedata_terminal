"""CLI parsing and startup banner helpers for FakeData Terminal."""

import argparse
import math
import os
import sys

try:
    from .style_config import (
        config_style_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        resolve_config_style,
        resolve_runtime_layout,
        validate_style_catalog,
        widget_names,
    )
except ImportError:
    from style_config import (
        config_style_names,
        discover_config_paths,
        default_image_paths,
        format_layout_diagrams,
        layout_catalog,
        layout_names,
        resolve_config_style,
        resolve_runtime_layout,
        validate_style_catalog,
        widget_names,
    )


DEFAULT_VOCAB = "science"
VOCAB_CHOICES = [
    "hacker", "science", "medicine", "pharmacy", "finance",
    "space", "military", "navigation", "spaceteam",
]


def _style_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return config_style_names(config_paths)


def _layout_choices(config_paths: tuple[str, ...] | None = None) -> list[str]:
    return layout_names(config_paths)


def _build_parser(config_paths: tuple[str, ...] | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FakeData Terminal — cinematic terminal data display. "
            "Load the packaged config, then local overlays, then apply CLI overrides. "
            "Use --style for a preset, or --layout plus --assign overrides to build a screen explicitly."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s --list\n"
            "  %(prog)s --config ./lab.yaml --list\n"
            "  %(prog)s --layouts\n"
            "  %(prog)s --widgets\n"
            "  %(prog)s --style test1\n"
            "  %(prog)s --config ~/.config/fakedata-terminal/styles.yaml --style lab\n"
            "  %(prog)s --layout grid_2x2 --assign p1=life --assign p2=blank --assign p3=text --assign p4=clock\n"
            "  %(prog)s --style test1 --assign p4=matrix --panel-speed p4=80\n"
            "  %(prog)s --layout grid_3x3 --assign large_left=image --assign right=clock "
            "--panel-image large_left=geom_07_diamond_lattice.png --panel-image large_left=geom_33_torus.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List configured styles, layouts, and available widgets, then exit.")
    parser.add_argument(
        "--config", action="append", default=[], metavar="PATH",
        help=("Load an extra config overlay. Repeatable. Relative image paths inside that file are "
              "resolved relative to the file itself."))
    parser.add_argument(
        "--layouts", action="store_true",
        help="Show configured layouts as fixed-size box diagrams, with their defined regions, then exit.")
    parser.add_argument(
        "--widgets", action="store_true",
        help="Showcase available widgets in left/right pairs on a grid_2x2 layout, then exit.")
    parser.add_argument(
        "--style", type=str, default=None, choices=_style_choices(config_paths),
        help="Config-defined style preset.")
    parser.add_argument(
        "--layout", type=str, default=None, choices=_layout_choices(config_paths),
        help="Explicit layout for the generalized panel runtime.")
    parser.add_argument(
        "--vocab", type=str, default=None, choices=VOCAB_CHOICES,
        help=f"Vocabulary style. Defaults to {DEFAULT_VOCAB} unless a style supplies one.")
    parser.add_argument(
        "--assign", action="append", default=[], metavar="REGION=WIDGET",
        help="Assign a widget to a region alias or explicit panel group. Repeatable.")
    parser.add_argument(
        "--panel-speed", action="append", default=[], metavar="REGION=N",
        help="Override speed for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-vocab", action="append", default=[], metavar="REGION=STYLE",
        help="Override vocabulary style for a specific region or panel group. Repeatable.")
    parser.add_argument(
        "--panel-image", action="append", default=[], metavar="REGION=PATH",
        help="Add an image path for a specific image region. Repeatable.")
    parser.add_argument(
        "--speed", type=int, default=None, metavar="N",
        help="Global speed 1 (slowest) to 100 (no delay).")
    parser.add_argument(
        "--life-max", type=int, default=200, metavar="N",
        help="Maximum iterations before life mode reseeds. Default 200.")
    parser.add_argument(
        "--text", type=str, default=None, metavar="MSG",
        help="Message to inject into text-based widgets.")
    parser.add_argument(
        "--image", nargs="+", default=None, metavar="PATH",
        help="Global image paths fallback for image widgets lacking region-specific image sources.")
    parser.add_argument(
        "--glitch", type=float, default=0.0, const=5.0, nargs="?", metavar="N",
        help=("Glitch interval in seconds. Every ~N seconds a rectangular region "
              "of the display is briefly corrupted then restored. "
              "0 = disabled (default). --glitch alone defaults to 5s."))
    return parser


def _print_list(config_paths: tuple[str, ...] | None = None) -> None:
    print("Styles:")
    for name in _style_choices(config_paths):
        print(f"  {name}")
    print()
    print("Layouts:")
    for name in _layout_choices(config_paths):
        print(f"  {name}")
    print()
    print("Widgets:")
    for name in widget_names(config_paths):
        print(f"  {name}")


def _print_layouts(config_paths: tuple[str, ...] | None = None) -> None:
    print(format_layout_diagrams(config_paths))

def _showcase_widget_names(include_image: bool, config_paths: tuple[str, ...] | None = None) -> list[str]:
    names = [name for name in widget_names(config_paths) if name not in {"blank", "cycle"}]
    if not include_image:
        names = [name for name in names if name != "image"]
    return names


def _build_widget_showcase(vocab: str, speed: int, text: str, image_paths: list[str], parser,
                           config_paths: tuple[str, ...] | None = None) -> dict:
    all_widgets = [name for name in widget_names(config_paths) if name != "blank"]
    widgets = _showcase_widget_names(bool(image_paths), config_paths)
    if not widgets:
        parser.error("--widgets found no widgets to show")

    scenes = []
    idx = 0
    while idx < len(widgets):
        left_widget = widgets[idx]
        right_widget = widgets[idx + 1] if idx + 1 < len(widgets) else widgets[0]
        regions_cfg = {
            "left": {"widget": left_widget},
            "right": {"widget": right_widget},
        }
        if left_widget == "image":
            regions_cfg["left"]["image"] = {"paths": image_paths[:]}
        if right_widget == "image":
            regions_cfg["right"]["image"] = {"paths": image_paths[:]}
        runtime = resolve_runtime_layout(
            "grid_2x2",
            regions_cfg,
            parser,
            style_name="<widgets>",
            vocab=vocab,
            speed=speed,
            text=text,
            config_paths=config_paths,
        )
        for area in runtime["areas"]:
            area["label"] = area["mode"]
        scenes.append(runtime)
        idx += 2
    initial = scenes[0]
    return {
        "active": True,
        "scenes": scenes,
        "idx": 0,
        "next": float("inf"),
        "pair_duration": 10.0,
        "done": False,
        "initial": initial,
        "all_widgets": all_widgets,
        "displayed_widgets": widgets,
    }


def _parse_equals(expr: str, parser, flag_name: str) -> tuple[str, str]:
    if "=" not in expr:
        parser.error(f"{flag_name} expects NAME=VALUE, got '{expr}'")
    left, right = expr.split("=", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        parser.error(f"{flag_name} expects NAME=VALUE, got '{expr}'")
    return left, right


def _normalize_region_key(layout_name: str, region_expr: str, parser, flag_name: str,
                          config_paths: tuple[str, ...] | None = None) -> str:
    layouts = layout_catalog(config_paths)
    layout_cfg = layouts.get(layout_name)
    if not isinstance(layout_cfg, dict):
        parser.error(f"unknown layout '{layout_name}'")
    panels = layout_cfg.get("panels", {})
    aliases = layout_cfg.get("regions", {})

    spec = aliases.get(region_expr, region_expr)
    panel_names = [part.strip() for part in str(spec).split("+") if part.strip()]
    if not panel_names:
        parser.error(f"{flag_name} references an empty region '{region_expr}'")
    for panel_name in panel_names:
        if panel_name not in panels:
            parser.error(f"{flag_name} references unknown panel '{panel_name}' in region '{region_expr}'")
    return "+".join(panel_names)


def _apply_assign_overrides(base_style: dict | None, assignments: list[str], panel_speeds: list[str],
                            panel_vocabs: list[str], panel_images: list[str],
                            parser, *, layout_name: str, style_name: str, vocab: str,
                            speed: int, text: str, config_paths: tuple[str, ...] | None = None) -> dict:
    regions_cfg = {}
    if base_style:
        for area in base_style["areas"]:
            region_key = "+".join(area["panels"])
            entry = {"widget": area["mode"]}
            if area.get("speed") is not None:
                entry["speed"] = area["speed"]
            if area.get("title"):
                entry["title"] = area["title"]
            if area.get("vocab"):
                entry["source_vocab"] = area["vocab"]
            if area.get("image_paths"):
                entry["image"] = {"paths": area["image_paths"][:]}
            if area.get("cycle_widgets"):
                entry["cycle"] = {"widgets": area["cycle_widgets"][:]}
            regions_cfg[region_key] = entry

    for item in assignments:
        target, widget = _parse_equals(item, parser, "--assign")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--assign", config_paths)
        target_panels = set(normalized_target.split("+"))
        to_delete = []
        for existing_key in list(regions_cfg):
            existing_panels = set(existing_key.split("+"))
            overlap = existing_panels & target_panels
            if not overlap:
                continue
            if existing_panels == target_panels:
                to_delete.append(existing_key)
                continue
            if existing_panels < target_panels:
                to_delete.append(existing_key)
                continue
            if target_panels < existing_panels:
                parser.error(
                    f"--assign {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
            else:
                parser.error(
                    f"--assign {target}={widget} partially overlaps existing region '{existing_key}'. "
                    "Overrides may replace whole regions or fully cover smaller ones."
                )
        for existing_key in to_delete:
            del regions_cfg[existing_key]
        current = regions_cfg.get(normalized_target, {})
        current["widget"] = widget
        regions_cfg[normalized_target] = current

    for item in panel_speeds:
        target, speed_text = _parse_equals(item, parser, "--panel-speed")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-speed", config_paths)
        try:
            panel_speed = int(speed_text)
        except ValueError:
            parser.error(f"--panel-speed expects an integer speed, got '{speed_text}'")
        if not 1 <= panel_speed <= 100:
            parser.error("--panel-speed must be between 1 and 100")
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-speed target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["speed"] = panel_speed

    for item in panel_vocabs:
        target, vocab_name = _parse_equals(item, parser, "--panel-vocab")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-vocab", config_paths)
        if vocab_name not in VOCAB_CHOICES:
            parser.error(f"--panel-vocab style must be one of: {', '.join(VOCAB_CHOICES)}")
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-vocab target '{target}' has no matching assignment")
        regions_cfg[normalized_target]["source_vocab"] = vocab_name

    for item in panel_images:
        target, image_path = _parse_equals(item, parser, "--panel-image")
        normalized_target = _normalize_region_key(layout_name, target, parser, "--panel-image", config_paths)
        if normalized_target not in regions_cfg:
            parser.error(f"--panel-image target '{target}' has no matching assignment")
        if regions_cfg[normalized_target].get("widget") != "image":
            parser.error(f"--panel-image target '{target}' is not assigned to widget 'image'")
        image_cfg = regions_cfg[normalized_target].setdefault("image", {})
        image_cfg.setdefault("paths", []).append(image_path)

    if not regions_cfg:
        parser.error("generalized layouts require at least one assignment")

    return resolve_runtime_layout(
        layout_name,
        regions_cfg,
        parser,
        style_name=style_name,
        vocab=vocab,
        speed=speed,
        text=text,
        config_paths=config_paths,
    )


def _resolve_config_paths(raw_argv: list[str]) -> tuple[str, ...]:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", action="append", default=[], metavar="PATH")
    config_args, _ = config_parser.parse_known_args(raw_argv)
    ordered_paths = [str(path) for path in discover_config_paths()] + config_args.config
    deduped = []
    seen = set()
    for path in ordered_paths:
        expanded = os.path.abspath(os.path.expanduser(path))
        if expanded in seen:
            continue
        seen.add(expanded)
        deduped.append(expanded)
    return tuple(deduped)


def prepare_runtime_config(argv, image_module, image_checker, demo_scenes):
    del demo_scenes
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    config_paths = _resolve_config_paths(raw_argv)
    parser = _build_parser(config_paths)

    if not raw_argv:
        parser.print_help()
        print()
        raise SystemExit(0)

    args = parser.parse_args(raw_argv)

    issues = validate_style_catalog(config_paths)
    if issues:
        parser.error("styles.yaml validation failed:\n  " + "\n  ".join(issues))

    if args.list:
        _print_list(config_paths)
        raise SystemExit(0)

    if args.layouts:
        _print_layouts(config_paths)
        raise SystemExit(0)

    if args.widgets and (args.style is not None or args.layout is not None or args.assign or args.panel_speed or args.panel_vocab or args.panel_image):
        parser.error("--widgets is a standalone showcase mode; do not combine it with --style, --layout, or panel overrides")

    if not args.widgets and args.style is None and args.layout is None:
        parser.error("specify either --style, --layout, or --widgets")

    speed_explicit = any(a == "--speed" or a.startswith("--speed=") for a in raw_argv)
    text_explicit = any(a == "--text" or a.startswith("--text=") for a in raw_argv)
    image_explicit = any(a == "--image" or a.startswith("--image=") for a in raw_argv)

    default_images = default_image_paths(config_paths)
    image_paths = []
    if args.image is not None and len(args.image) < 1:
        parser.error("--image expects at least one file path")
    if image_explicit and args.image:
        for raw_path in args.image:
            path = os.path.abspath(os.path.expanduser(raw_path))
            if not os.path.isfile(path):
                parser.error(f"image file not found: {raw_path}")
            image_paths.append(path)

    runtime_speed = args.speed if speed_explicit and args.speed is not None else 30
    runtime_text = args.text.strip() if text_explicit and args.text is not None else ""
    runtime_vocab = args.vocab or DEFAULT_VOCAB
    widget_showcase = {"active": False, "scenes": [], "idx": 0, "next": float("inf"), "pair_duration": 10.0, "done": False}

    if not image_explicit:
        image_paths = default_images[:]

    if args.widgets:
        widget_showcase = _build_widget_showcase(runtime_vocab, runtime_speed, runtime_text, image_paths, parser, config_paths)
        config_style_runtime = widget_showcase["initial"]
        runtime_layout_name = config_style_runtime["layout"]
    else:
        base_runtime = resolve_config_style(args.style, parser, config_paths) if args.style else None
        runtime_layout_name = args.layout or (base_runtime["layout"] if base_runtime else None)
        if not runtime_layout_name:
            parser.error("no layout available")

        runtime_vocab = args.vocab or (base_runtime["vocab"] if base_runtime else DEFAULT_VOCAB)
        runtime_speed = args.speed if speed_explicit and args.speed is not None else (base_runtime["speed"] if base_runtime else 30)
        runtime_text = args.text.strip() if text_explicit and args.text is not None else (base_runtime["text"] if base_runtime else "")

        has_cli_overrides = bool(
            args.layout or args.assign or args.panel_speed or args.panel_vocab or args.panel_image or args.vocab
        )
        if base_runtime is None or has_cli_overrides:
            config_style_runtime = _apply_assign_overrides(
                base_runtime if (base_runtime and not args.layout) else None,
                args.assign,
                args.panel_speed,
                args.panel_vocab,
                args.panel_image,
                parser,
                layout_name=runtime_layout_name,
                style_name=args.style or f"<cli:{runtime_layout_name}>",
                vocab=runtime_vocab,
                speed=runtime_speed,
                text=runtime_text,
                config_paths=config_paths,
            )
        else:
            config_style_runtime = base_runtime

    if runtime_speed is None:
        runtime_speed = config_style_runtime["speed"]

    if not 1 <= runtime_speed <= 100:
        parser.error("--speed must be between 1 and 100")
    if args.life_max < 1:
        parser.error("--life-max must be at least 1")

    image_sources = config_style_runtime["image_paths"] if not image_explicit else image_paths
    image_mode_active = any(area["mode"] == "image" for area in config_style_runtime["areas"])
    if args.widgets:
        image_mode_active = any(
            area["mode"] == "image"
            for scene in widget_showcase["scenes"]
            for area in scene["areas"]
        )
    if image_mode_active and not image_paths and not any(area.get("image_paths") for area in config_style_runtime["areas"]):
        parser.error("image mode requires --image PATH [PATH ...] or --panel-image REGION=PATH")
    if image_mode_active and image_module is None:
        parser.error("image mode requires Pillow to be installed")
    if image_mode_active and not image_checker():
        parser.error("image mode requires jp2a to be installed")

    return {
        "speed": runtime_speed,
        "main_speed": runtime_speed,
        "sidebar_speed": runtime_speed,
        "life_max": args.life_max,
        "inject_text": runtime_text,
        "main_mode": None,
        "sidebar_mode": None,
        "style": config_style_runtime["vocab"],
        "style_name": "<widgets>" if args.widgets else (args.style or f"<cli:{runtime_layout_name}>"),
        "styles": VOCAB_CHOICES[:],
        "config_style": config_style_runtime,
        "layout_name": config_style_runtime["layout"],
        "area_summary": ", ".join(f"{area['name']}={area['mode']}" for area in config_style_runtime["areas"]),
        "demo_state": {"active": False, "scenes": [], "idx": 0, "scene": None, "next": float("inf"), "done": False},
        "widget_showcase": widget_showcase,
        "glitch_interval": max(0.0, args.glitch if args.glitch is not None else 0.0),
        "image_paths": image_sources,
    }


def _show_delay(speed: int) -> str:
    if speed >= 100:
        return "no delay (flat-out)"
    lo, hi = math.log(0.004), math.log(1.0)
    delay = math.exp(hi + (speed - 1) / 98 * (lo - hi))
    return f"~{delay:.3f} s/line centre"


def show_startup_banner(script_name: str, config: dict) -> None:
    bold = "\033[1m"
    cyan = "\033[36m"
    dim = "\033[2m"
    reset = "\033[0m"

    print(reset)
    print(f"  {cyan}{script_name}{reset}  —  FakeData Terminal")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {bold}speed{reset}  : global {config['speed']}/100", end="")
    print(f"  ({_show_delay(config['speed'])})")
    print(f"  {bold}style{reset}  : {config['style_name']}")
    print(f"  {bold}vocab{reset}  : {config['style']}")
    if config["image_paths"]:
        label = "image" if len(config["image_paths"]) == 1 else "images"
        print(f"  {bold}{label}{reset} : {', '.join(config['image_paths'])}")
    if config["inject_text"]:
        print(f"  {bold}text{reset}   : '{config['inject_text']}'")
    else:
        print(f"  {bold}text{reset}   : (none)")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {bold}layout{reset} : {config['layout_name']}")
    if config["area_summary"]:
        print(f"  {bold}areas{reset}  : {config['area_summary']}")
    glitch_str = f"every ~{config['glitch_interval']:.1f}s" if config["glitch_interval"] > 0 else "off"
    print(f"  {bold}glitch{reset} : {glitch_str}")
    print(f"  {dim}{'─' * 54}{reset}")
    print(f"  {dim}Press Q or Ctrl-C to quit  |  Space to pause  |  + / - to change speed live{reset}")
    print()
