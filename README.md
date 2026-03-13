# FakeData Terminal

FakeData Terminal is a curses-based Python app that renders animated, fake telemetry screens in the terminal. It combines configurable layouts, widget assignments, themed vocabularies, and optional image-to-ASCII rendering to produce cinematic dashboard displays.

## What It Does

- Renders multi-panel terminal scenes using `curses`
- Drives text widgets from themed vocab pools such as `science`, `hacker`, `medicine`, and `finance`
- Loads packaged layouts from [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and style presets from [`data/styles.yaml`](/home/tags/fakedata_terminal/data/styles.yaml)
- Supports widget types including `text`, `clock`, `matrix`, `bars`, `life`, `oscilloscope`, `readouts`, `sweep`, `tunnel`, and `image`
- Lets you start from a preset style or build a screen explicitly with `--layout`, `--panel-widget`, and `--default-*`
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
python3 app.py --list
python3 app.py --style science
python3 app.py --layouts
python3 app.py --layout grid_2x2 --default-widget tunnel
```

If you want image widgets, install the extra dependencies first:

```bash
python3 -m pip install PyYAML Pillow
# install jp2a with your system package manager
```

## Common Commands

List available presets, layouts, and widgets:

```bash
python3 app.py --list
```

Show layout diagrams:

```bash
python3 app.py --layouts
```

Run a preset style:

```bash
python3 app.py --style science
python3 app.py --style clocks
```

Browse the interactive demo pages:

```bash
python3 app.py --demo
```

Build a layout manually:

```bash
  python3 app.py \
  --layout grid_2x2 \
  --panel-widget p1=life \
  --panel-widget p2=clock \
  --panel-widget p3=text \
  --panel-widget p4=matrix
```

Override per-region behavior:

```bash
  python3 app.py \
  --style test1 \
  --panel-widget p4=matrix \
  --panel-speed p4=80 \
  --panel-vocab p4=hacker
```

Run an image panel:

```bash
  python3 app.py \
  --layout grid_3x2 \
  --panel-widget p3+p4=image \
  --panel-widget p5=clock \
  --panel-widget p6=text \
  --panel-image p3+p4=data/geom_33_torus.png
```

Set layout-wide defaults for unassigned panels:

```bash
python3 app.py \
  --layout grid_3x3 \
  --default-widget cycle \
  --default-speed 70 \
  --default-colour cyan \
  --panel-widget large_left=image \
  --panel-image large_left=data/geom_33_torus.png
```

If no `--style` or `--layout` is provided, the configured `defaults.layout` is used.

Enable periodic glitch effects:

```bash
python3 app.py --style science --glitch 5
```

## Controls

During runtime:

- `q` or `Ctrl-C` quits
- `Space` pauses
- `+` and `-` adjust speed live

## Configuration Model

The runtime is config-first:

- Layouts define panel geometry
- Regions alias one or more panels
- Styles bind widgets and options to regions
- Config precedence is: packaged config, then local overlays, then CLI flags
- Widget defaults can supply fallback `speed`, `colour`, `source_vocab`, `image`, and `cycle` settings per widget type

The packaged base config lives in [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/styles.yaml`](/home/tags/fakedata_terminal/data/styles.yaml). Validation, overlay merging, and runtime adaptation are handled in [`style_config.py`](/home/tags/fakedata_terminal/style_config.py) and [`cli_config.py`](/home/tags/fakedata_terminal/cli_config.py).

Automatic config search order:

- packaged base: [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/styles.yaml`](/home/tags/fakedata_terminal/data/styles.yaml)
- user overlay: `~/.config/fakedata-terminal/styles.yaml` (or `$XDG_CONFIG_HOME/fakedata-terminal/styles.yaml`)
- project overlay: `./.fakedata-terminal.yaml` or `./.fakedata-terminal.yml`

You can also add one or more explicit overlays with `--config PATH`. Those are applied after the automatic files, in the order given on the command line.

Overlay semantics:

- mappings merge recursively, so local config can redefine only the keys it needs
- scalar values replace earlier values
- lists replace earlier lists rather than appending
- relative image paths inside a config file are resolved relative to that file

### Widget Defaults

The top-level `widgets:` section can define fallback attributes for a widget type. These defaults apply whenever that widget is used and the region does not specify the same attribute.

```yaml
widgets:
  sweep:
    colour: cyan
    speed: 65

  readouts:
    source_vocab: finance

  image:
    image:
      glob: "./images/geom*.png"

  cycle:
    cycle:
      widgets: [text, bars, matrix, tunnel]
```

Supported widget-default keys are:

- `speed`
- `title`
- `source_vocab`
- `colour` or `color`
- `image`
- `cycle`

### Precedence

There are two layers of precedence to keep in mind.

Config file merge order:

- packaged base config in [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml) and [`data/styles.yaml`](/home/tags/fakedata_terminal/data/styles.yaml)
- user config in `~/.config/fakedata-terminal/styles.yaml`
- project config in `./.fakedata-terminal.yaml` or `./.fakedata-terminal.yml`
- extra `--config PATH` files, in the order given

Within the merged config, area attributes resolve in this order:

- global `defaults.*`
- widget-specific defaults from `widgets.<widget>.*`
- style region settings in `styles.<style>.regions.*`
- CLI defaults such as `--default-colour`, `--default-speed`, and `--default-widget` for values still not set by the config/style layer
- CLI per-panel overrides such as `--panel-colour`, `--panel-speed`, `--panel-vocab`, `--panel-image`, and `--panel-widget`
- built-in code fallback inside the widget implementation if an attribute is still unset

## Project Structure

- [`app.py`](/home/tags/fakedata_terminal/app.py): curses runtime and widget rendering
- [`cli.py`](/home/tags/fakedata_terminal/cli.py): launcher wrapper
- [`cli_config.py`](/home/tags/fakedata_terminal/cli_config.py): argument parsing and runtime config assembly
- [`style_config.py`](/home/tags/fakedata_terminal/style_config.py): YAML loading, overlay merging, and validation
- [`vocab.py`](/home/tags/fakedata_terminal/vocab.py): themed fake-data generators
- [`data/layouts.yaml`](/home/tags/fakedata_terminal/data/layouts.yaml): packaged layout geometry and region aliases
- [`data/styles.yaml`](/home/tags/fakedata_terminal/data/styles.yaml): defaults, widget fallbacks, and style presets
- [`data/`](/home/tags/fakedata_terminal/data): image assets used by image panels

## Notes

- Running `python3 app.py` with no arguments uses the configured `defaults.layout`.
- Image mode fails fast if `Pillow` or `jp2a` is unavailable.
- `--config PATH` is repeatable and can add site, user, or project-specific overlays.
- CLI defaults are `--default-speed`, `--default-colour`, and `--default-widget`.
- Preset names currently include `clocks`, `cycle9`, `cycle4`, `science`, `science2`, `geometries`, `tunnel`, `test1` through `test7`, and `gauges`.
