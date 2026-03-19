# FakeData Terminal

FakeData Terminal renders animated, fake telemetry screens in the terminal. It combines configurable layouts, widget assignments, named themes, and optional image-to-ASCII rendering to produce cinematic dashboard displays.

## Docs

- [README.md](/home/tags/fakedata_terminal/README.md): user-facing usage and configuration overview
- [configuration_model.md](/home/tags/fakedata_terminal/configuration_model.md): mental model, precedence, and validation rules
- [implementation_todo.md](/home/tags/fakedata_terminal/implementation_todo.md): remaining implementation backlog

## What It Does

- Renders multi-panel terminal screens using `curses`
- Drives text widgets from named theme pools such as `science`, `hacker`, `medicine`, and `finance`
- Loads packaged layouts from [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and screen presets from [`data/screens.yaml`](/home/tags/fakedata_terminal/data/screens.yaml)
- Supports widget types including `text`, `gauge`, `matrix`, `bars`, `crash`, `rotate`, `orbit`, `life`, `scope`, `sparkline`, `readouts`, `sweep`, `tunnel`, and `image`
- Lets you start from a preset screen or build a screen explicitly with `--screen-layout`, `--region-widget`, and supported default/region overrides
- Supports widget-level fallback defaults in YAML via the top-level `widgets:` section

## Requirements

- Python 3.10+
- `PyYAML`
- `Pillow` for the `image` widget
- `jp2a` for the `image` widget
- A terminal with curses support

On Windows, the app attempts to install `windows-curses` automatically if it is missing.

## Running

This repository does not include packaging metadata, so the most direct entrypoint is the source file:

```bash
python3 fakedata_terminal.py --list
python3 fakedata_terminal.py --screen science
python3 fakedata_terminal.py --layouts
python3 fakedata_terminal.py --screen-layout 2x2 --default-widget tunnel
```

If you want image widgets, install the extra dependencies first:

```bash
python3 -m pip install PyYAML Pillow
# install jp2a with your system package manager
```

## Common Commands

List available screens, layouts, and widgets:

```bash
python3 fakedata_terminal.py --list
```

Show layout diagrams:

```bash
python3 fakedata_terminal.py --layouts
```

`--layouts` renders geometry-driven ASCII previews. Panels with the same configured width or height consume the same number of preview columns or rows.

Run a preset screen:

```bash
python3 fakedata_terminal.py --screen science
python3 fakedata_terminal.py --screen clocks
```

Browse the widget showcase:

```bash
python3 fakedata_terminal.py --widgets
python3 fakedata_terminal.py --screens
```

Build a screen manually:

```bash
  python3 fakedata_terminal.py \
  --screen-layout 2x2 \
  --region-widget P1=life \
  --region-widget P2=gauge \
  --region-widget P3=text \
  --region-widget P4=matrix
```

Override per-region behavior:

```bash
  python3 fakedata_terminal.py \
  --screen test1 \
  --region-widget P4=matrix \
  --region-speed P4=80 \
  --region-theme P4=hacker \
  --region-text P2=SIGNAL
```

Run an image panel:

```bash
  python3 fakedata_terminal.py \
  --screen-layout 3x2 \
  --region-widget P3+P4=image \
  --region-widget P5=gauge \
  --region-widget P6=text \
  --region-image P3+P4=data/geom_33_torus.png
```

Set defaults for unassigned panels:

```bash
python3 fakedata_terminal.py \
  --screen-layout 3x3 \
  --default-widget cycle \
  --default-colour cyan \
  --region-widget L2=image \
  --region-image L2=data/geom_33_torus.png
```

If no arguments are provided, the program prints a short orientation message instead of launching a screen.

Enable periodic glitch effects:

```bash
python3 fakedata_terminal.py --screen science --screen-glitch 5
```

`glitch` can also be set in config at `defaults.glitch` or `screens.<name>.glitch`. An explicit `--screen-glitch` overrides config.

## Controls

During runtime:

- `q` or `Ctrl-C` quits
- `Space` pauses
- `+` and `-` adjust speed live

## Configuration Model

The runtime is config-first:

- Layouts define panel geometry
- Regions alias one or more panels
- Screens bind widgets and options to regions
- Config precedence is: packaged config, then local overlays, then CLI flags
- Widget defaults can supply fallback `speed`, `text`, `colour`, `theme`, `image`, and `cycle` settings per widget type. `color` is also accepted as an alias.

The packaged base config lives in [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/screens.yaml`](/home/tags/fakedata_terminal/data/screens.yaml). Validation, overlay merging, and runtime adaptation are handled in [`scene_config.py`](/home/tags/fakedata_terminal/scene_config.py) and [`cli_config.py`](/home/tags/fakedata_terminal/cli_config.py).

Automatic config search order:

- packaged base: [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/screens.yaml`](/home/tags/fakedata_terminal/data/screens.yaml)
- user overlay: `~/.config/fakedata-terminal/screens.yaml` (or `$XDG_CONFIG_HOME/fakedata-terminal/screens.yaml`)
- project overlay: `./.fakedata-terminal.yaml` or `./.fakedata-terminal.yml`

You can also add one or more explicit overlays with `--config PATH`. Those are applied after the automatic files, in the order given on the command line.

Overlay semantics:

- mappings merge recursively, so local config can redefine only the keys it needs
- scalar values replace earlier values
- lists replace earlier lists rather than appending
- image references with path components are resolved relative to the current working directory unless absolute
- bare image names are resolved in this order: current working directory, the YAML file's directory, then the packaged `data/` directory

### Widget Defaults

The top-level `widgets:` section can define fallback attributes for a widget type. These defaults apply whenever that widget is used and the region does not specify the same attribute.

```yaml
widgets:
  sweep:
    colour: cyan
    speed: 65

  readouts:
    theme: finance

  image:
    image:
      glob: "./images/geom*.png"

  cycle:
    cycle:
      widgets: [text, bars, matrix, tunnel]
```

Supported widget-default keys are:

- `speed`
- `text`
- `theme`
- `colour` (`color` also accepted)
- `image`
- `cycle`

`text` is context-sensitive but still consistent:

- screen-level `text` is the global text override for that screen
- screen-level `glitch` is the glitch interval in seconds for that screen
- region-level `text` is the per-region override used by `blank`, `readouts`, and text-heavy widgets

### Core Terms

These pieces fit together in a specific order:

- `Panel`: a single rectangular tile in a layout, usually named `P1`, `P2`, and so on.
- `Layout`: the panel geometry for the whole screen. Layouts define panel positions and optional named region aliases. Use `python3 fakedata_terminal.py --layouts` to inspect the available layouts and region names.
- `Region`: a rectangular area made of one or more contiguous panels. A region is referenced either by its component panel ids such as `P2` or `P1+P2+P3`, or by an alias defined in the layout such as `L`, `R`, `C`, or `L2`. Each region is assigned exactly one widget.
- `Widget`: the renderer/behavior assigned to a region, such as `text`, `matrix`, `gauge`, `image`, `sweep`, or `cycle`. Use `python3 fakedata_terminal.py --list` to see the available widget names.
- `Region attributes`: options attached to one region assignment, such as `speed`, `text`, `theme`, `colour`, `image`, and `cycle`. `color` is also accepted as an alias.
- `Widget defaults`: fallback attributes for all uses of a widget type, defined under top-level `widgets:`.
- `Screen`: a named screen configuration. A screen picks one layout, assigns widgets to regions in that layout, and can also supply screen-wide theme/speed/text plus per-region attributes. Use `python3 fakedata_terminal.py --screen NAME` to run one, `python3 fakedata_terminal.py --list` to list them, `python3 fakedata_terminal.py --screens` to browse just the configured screen pages, and `python3 fakedata_terminal.py --widgets` to browse the widget showcase.

In short:

- layouts define panels and region aliases
- regions group panels into usable rectangular areas
- widgets render inside regions
- screens combine a layout with widget assignments and attributes

### Precedence

There are two layers of precedence to keep in mind.

Config file merge order:

- packaged base config in [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/screens.yaml`](/home/tags/fakedata_terminal/data/screens.yaml)
- user config in `~/.config/fakedata-terminal/screens.yaml`
- project config in `./.fakedata-terminal.yaml` or `./.fakedata-terminal.yml`
- extra `--config PATH` files, in the order given

Within the merged config, area attributes resolve in this order:

- global `defaults.*`
- widget-specific defaults from `widgets.<widget>.*`
- screen region settings in `screens.<screen>.regions.*`
- CLI defaults such as `--default-colour` and `--default-widget` for values still not set by the config/screen layer
- CLI per-region overrides such as `--region-colour`, `--region-speed`, `--region-theme`, `--region-image`, and `--region-widget`
- built-in code fallback inside the widget implementation if an attribute is still unset

## Project Structure

- [`fakedata_terminal.py`](/home/tags/fakedata_terminal/fakedata_terminal.py): curses runtime and widget rendering
- [`cli.py`](/home/tags/fakedata_terminal/cli.py): launcher wrapper
- [`cli_config.py`](/home/tags/fakedata_terminal/cli_config.py): argument parsing and runtime config assembly
- [`scene_config.py`](/home/tags/fakedata_terminal/scene_config.py): YAML loading, overlay merging, and validation
- [`vocab.py`](/home/tags/fakedata_terminal/vocab.py): theme data generators
- [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml): packaged layout geometry and region aliases
- [`data/screens.yaml`](/home/tags/fakedata_terminal/data/screens.yaml): packaged defaults and screen presets
- [`data/widgets.yaml`](/home/tags/fakedata_terminal/data/widgets.yaml): widget metadata, defaults, and timing/behavior tunables
- [`data/`](/home/tags/fakedata_terminal/data): image assets used by image panels

## Notes

- Running `python3 fakedata_terminal.py` with no arguments prints the short orientation message and exits.
- Image mode fails fast if `Pillow` or `jp2a` is unavailable.
- Startup validation runs before rendering and catches unsupported widgets, invalid resolved modifier/widget combinations, duplicate `cycle.widgets` entries, unreadable images, and missing image dependencies.
- `--config PATH` is repeatable and can add site, user, or project-specific overlays.
- CLI defaults are `--default-colour` and `--default-widget`.
- Packaged layouts currently include `full`, `1x3`, `2x2`, `2x4`, `3x2`, `3x3`, `4x3`, `L2x2_R3`, `L3_R2x2`, `L2_R3x3`, `L3_M3_R2`, and `L3x3_R2`.
- Preset names currently include `clocks`, `cycle9`, `cycle4`, `science`, `science2`, `geometries`, `tunnel`, `test1` through `test7`, and `gauges`.
