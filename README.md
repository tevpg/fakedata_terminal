# FakeData Terminal

FakeData Terminal is a curses-based Python app that renders animated, fake telemetry screens in the terminal. It combines configurable layouts, widget assignments, themed vocabularies, and optional image-to-ASCII rendering to produce cinematic dashboard displays.

## What It Does

- Renders multi-panel terminal scenes using `curses`
- Drives text widgets from themed vocab pools such as `science`, `hacker`, `medicine`, and `finance`
- Loads layouts and style presets from [`data/styles.yaml`](/fs/sysbits/fakedata_terminal/data/styles.yaml)
- Supports widget types including `text`, `clock`, `matrix`, `bars`, `life`, `oscilloscope`, `readouts`, `sweep`, and `image`
- Lets you start from a preset style or build a screen explicitly with `--layout` and `--assign`

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

Showcase all widgets:

```bash
python3 app.py --widgets
```

Build a layout manually:

```bash
python3 app.py \
  --layout grid_2x2 \
  --assign p1=life \
  --assign p2=clock \
  --assign p3=text \
  --assign p4=matrix
```

Override per-region behavior:

```bash
python3 app.py \
  --style test1 \
  --assign p4=matrix \
  --panel-speed p4=80 \
  --panel-vocab p4=hacker
```

Run an image panel:

```bash
python3 app.py \
  --layout grid_3x2 \
  --assign p3+p4=image \
  --assign p5=clock \
  --assign p6=text \
  --panel-image p3+p4=data/geom_33_torus.png
```

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
- CLI flags can override style defaults

The main config lives in [`data/styles.yaml`](/fs/sysbits/fakedata_terminal/data/styles.yaml). Validation and runtime adaptation are handled in [`style_config.py`](/fs/sysbits/fakedata_terminal/style_config.py) and [`cli_config.py`](/fs/sysbits/fakedata_terminal/cli_config.py).

## Project Structure

- [`app.py`](/fs/sysbits/fakedata_terminal/app.py): curses runtime and widget rendering
- [`cli.py`](/fs/sysbits/fakedata_terminal/cli.py): launcher wrapper
- [`cli_config.py`](/fs/sysbits/fakedata_terminal/cli_config.py): argument parsing and runtime config assembly
- [`style_config.py`](/fs/sysbits/fakedata_terminal/style_config.py): YAML style loading and validation
- [`vocab.py`](/fs/sysbits/fakedata_terminal/vocab.py): themed fake-data generators
- [`data/styles.yaml`](/fs/sysbits/fakedata_terminal/data/styles.yaml): layouts, regions, and style presets
- [`data/`](/fs/sysbits/fakedata_terminal/data): image assets used by image panels

## Notes

- Running `python3 app.py` with no arguments prints the CLI help and exits.
- Image mode fails fast if `Pillow` or `jp2a` is unavailable.
- Preset names currently include `clocks`, `cycle9`, `cycle4`, `science`, `science2`, `geometries`, `test1` through `test7`, and `gauges`.
