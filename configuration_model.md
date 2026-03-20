# Configuration Model and Precedence

This document defines the target mental model for FakeData Terminal configuration and how YAML and CLI options should interact.

It is intentionally more explicit than the `README`. The goal is to make it easy to answer questions like:

- Where should a setting live?
- What overrides what?
- When should I use screen config versus widget defaults versus CLI flags?
- How should overlapping defaults be interpreted?

## Why This Exists

The project has several configuration scopes:

- packaged defaults
- local YAML overlays
- widget-level defaults
- screen-level values
- region-level assignments
- CLI defaults
- CLI per-region overrides

Without a clear model, small changes become hard to reason about. The target model is:

- broad configuration defines reusable defaults
- narrower configuration specializes those defaults
- CLI acts as the final runtime patch layer for one invocation

In short: start broad, then get more specific.

## Target Mental Model

Think of the system as four layers of responsibility.

### 1. Layouts define geometry

Layouts answer only one question:

- Where are the panels, and which named regions map to which panels?

Target rule:

- `layouts.yaml` should contain geometry only.

Layouts should not decide widget behavior, themes, speeds, or screen composition.

### 2. Widgets define widget-type behavior and fallback defaults

Widgets answer questions like:

- What modifiers does this widget support?
- Is it enabled?
- What timing or behavior metadata does it use?
- What fallback attributes should apply whenever this widget type is used?

Target rule:

- `widgets.yaml` should own widget metadata, widget defaults, and widget behavior/timing.

Examples of widget-level fallback defaults:

- all `sweep` widgets default to `colour: cyan`
- all `readouts` widgets default to `theme: finance`
- all `image` widgets default to a packaged image glob

These are defaults for a widget type, not a particular screen.

### 3. Screens compose a screen

Screens answer questions like:

- Which layout should be used?
- Which widget goes in each region?
- What screen-wide theme/speed/text/glitch/direction should apply?
- Which regions override those broader defaults?

Target rule:

- `screens.yaml` should contain app defaults and named screen compositions.

A screen is where the user says "build this screen", not where widget metadata is defined.

Terminology note:

- `screen` is the preferred term for the current composed-display concept
- if the project later adds sequencing, timeline, or storytelling semantics, those would more naturally be modeled as scenes composed from screens

### 4. CLI patches one run

The CLI should be understood as an invocation-time override layer:

- choose a screen, or construct an ad hoc screen
- replace screen-wide values for this run
- replace region assignments or region attributes for this run

The CLI should not introduce a second configuration model. It should expose the same concepts already present in YAML, just with command-line syntax.

## Core Resolution Model

The clearest way to reason about the system is as a two-phase process:

1. resolve defaults
2. resolve concrete runtime structure and per-region specifics

That means the runtime should not be thought of as one long flat precedence stack. It is better understood as:

- first, build the effective fallback values from every relevant source
- then, resolve the actual layout, widget assignments, and region-specific overrides
- whenever a specific scope omits a modifier, fill it from the already-resolved defaults

This is the target mental model.

The most important rule inside that model is still:

- narrower scope wins over broader scope

But it applies within each phase, not as one undifferentiated global ordering.

## Two Different Kinds of Precedence

There are two separate precedence problems, and they should not be confused.

### 1. Config file merge order

This decides how multiple YAML files combine into one merged catalog.

Target merge order:

1. packaged base files
2. user config
3. project config
4. extra `--config PATH` files, in command-line order

Current automatic discovery order is:

1. packaged `data/layouts.yaml`
2. packaged `data/screens.yaml`
3. user `~/.config/fakedata-terminal/screens.yaml` or `$XDG_CONFIG_HOME/fakedata-terminal/screens.yaml`
4. project `./.fakedata-terminal.yaml` or `./.fakedata-terminal.yml`

Target end state:

1. packaged `data/layouts.yaml`
2. packaged `data/widgets.yaml`
3. packaged `data/screens.yaml`
4. user overlays
5. project overlays
6. explicit `--config` overlays

Merge semantics:

- mappings merge recursively
- scalar values replace earlier values
- lists replace earlier lists

This means overlays are patches, not append-only fragments.

### 2. Runtime resolution order

This decides which value wins after the merged catalog exists and the CLI is applied.

The target runtime model is:

1. resolve effective defaults
2. resolve structure
3. resolve per-area modifiers from the defaults plus specific overrides

Expanded:

1. resolve app-wide defaults from `defaults.*`
2. resolve widget-type defaults from `widgets.<widget>.*`
3. resolve screen-wide defaults or screen-wide runtime values from `screens.<name>.*`
4. choose the layout
5. resolve region-to-widget assignments
6. for each resolved area, start from the applicable defaults and overlay region-specific values
7. apply CLI region overrides
8. use built-in runtime fallback only if something is still unset

This is the main precedence rule users care about.

## Serialization Principle

The `exit` YAML should be treated as a lossless scene serialization.

Target rule:

- if the emitted `exit` YAML is pasted into `scenes.yaml`, it should recreate the same resolved scene

The intended exceptions are only changes outside the serialized scene itself, such as:

- later changes to layout definitions
- later changes to widget metadata or widget implementations

Practical implication:

- `exit` output should include every resolved, user-visible region or screen value needed to reconstruct the scene faithfully
- it should not rely on hidden defaults when omitting those values would change the recreated scene

## What Each Scope Should Be Used For

### `defaults.*`

Use `defaults` for cross-screen application defaults such as:

- default theme
- default speed
- default widget for uncovered panels
- default colour
- default glitch interval
- default direction
- default image sources

These values answer: "What should happen if nothing more specific says otherwise?"

### `widgets.<widget>.*`

Use widget defaults for reusable widget-type behavior, not for screen composition.

Good fits:

- `widgets.sweep.colour`
- `widgets.readouts.theme`
- `widgets.image.image`
- `widgets.cycle.cycle.widgets`

Bad fits:

- assigning a widget to a specific screen region
- choosing the layout for a screen
- putting screen-specific copy in widget defaults unless that text is truly reusable for every use of that widget

### `screens.<name>.*`

Use screen-wide keys for values that describe the whole screen:

- `layout`
- `theme`
- `speed`
- `text`
- `glitch`
- `direction`

Screen-wide values should mean "for this screen as a whole", not "fallback for every region modifier".

Target behavior:

- screen-wide `theme`, `speed`, `text`, `glitch`, and `direction` are runtime screen values
- per-region modifier fallback is handled by widget defaults plus region values
- screen-wide values should not silently act as per-area fallback unless the model explicitly says so

### `screens.<name>.regions.<region>.*`

Use region values for actual area assignments and per-area specialization:

- `widget`
- `speed`
- `text`
- `theme`
- `colour`
- `direction`
- `image`
- `cycle`

This is the most specific YAML layer in normal config use.

### CLI screen/default flags

These are one-run overrides of broad screen/default behavior.

Examples:

- `--screen`
- `--screen-layout`
- `--screen-theme`
- `--screen-glitch`
- `--default-widget`
- `--default-colour`

Use them when you want to patch the current run without editing YAML.

### CLI region flags

These are the narrowest, strongest overrides.

Examples:

- `--region-widget`
- `--region-speed`
- `--region-text`
- `--region-theme`
- `--region-direction`
- `--region-colour`
- `--region-image`

Use them for one-off changes to specific regions.

Planning note:

- `--region-image` should accept a glob, not only a single path
- this needs to be designed with shell wildcard expansion in mind so quoted and unquoted forms behave predictably

## Resolution Passes

### Pass 1: Resolve defaults

In the first pass, collect the fallback values that may later be used to fill gaps.

The intended order is:

1. packaged base config
2. local YAML overlays
3. app-wide `defaults.*`
4. widget-type defaults from `widgets.<widget>.*`
5. CLI broad/default flags such as `--screen-theme`, `--screen-glitch`, `--default-colour`, and `--default-widget`

The result of this pass should be a set of effective defaults, not yet a fully resolved screen.

Those defaults include things like:

- default theme
- default speed
- default colour
- default direction
- default widget
- default image sources
- widget-specific fallback modifiers

### Pass 2: Resolve structure

In the second pass, determine the actual screen structure.

The intended order is:

1. choose the layout
2. resolve region expressions and panel coverage
3. resolve explicit widget assignments from the screen
4. apply CLI `--region-widget` overrides
5. fill any uncovered panels with the default widget, if configured

This phase answers:

- what areas exist?
- which panels do they cover?
- which widget is assigned to each area?

### Pass 3: Resolve area modifiers

Once the structure exists, resolve modifiers for each area.

For each area, the intended reasoning order is:

1. start from the already-resolved defaults that apply to that area
2. apply screen-wide values if that modifier has screen-wide meaning
3. apply screen region values
4. apply CLI broad/default overrides if they are meant to replace screen-wide values for this run
5. apply CLI region overrides
6. use built-in runtime fallback only if something is still unset

This yields the working rule:

- resolve defaults first, then structure, then modifiers

Structure means:

- layout
- region coverage
- widget assignment

Modifiers mean:

- speed
- text
- theme
- colour
- direction
- image
- cycle

## Structural Precedence

Layout selection should be understood as:

1. screen layout from `screens.<name>.layout`
2. explicit CLI `--screen-layout`

Region/widget selection should be understood as:

1. screen region assignments
2. CLI `--region-widget` overrides
3. default widget fills any uncovered panels

Important detail:

- the default widget is not a competing region assignment
- it only fills panels left unassigned after explicit screen and CLI region assignments are resolved

Planning note:

- remove the concept of a configured default layout
- a default layout is only useful for the special case of running `fakedata_terminal` with no arguments
- that no-args case should be handled by a short usage/inventory message instead of implicit layout selection

## Modifier Precedence by Area

For a specific area modifier such as `speed`, `theme`, `colour`, `direction`, `text`, `image`, or `cycle`, the target order is:

1. effective defaults already resolved in the defaults pass
2. screen-wide value, if that modifier has screen-wide meaning
3. screen region value
4. CLI broad/default override, if it replaces the screen-wide value for this run
5. CLI region override
6. runtime hardcoded fallback

The target compact summary is:

- widget defaults are the main YAML fallback for per-area modifiers
- screen region values override widget defaults
- CLI region flags override screen region values
- default widget fills uncovered panels
- `--default-colour` is applied late to any area still missing a colour

## CLI Principles

The target CLI model should follow these rules:

- CLI names should map cleanly to config concepts
- broad flags should affect broad scope
- region flags should affect one region only
- the CLI should not silently invent extra precedence layers

In practice that means:

- `--screen` selects a named composition
- `--screen-layout` replaces the layout field of the screen being built for this invocation
- `--screen-theme` and `--screen-glitch` replace screen-wide runtime values for this invocation
- `--default-*` flags describe broad fallback behavior
- `--region-*` flags are always more specific than non-region flags

Structural rule:

- there should be at most one layout selection per invocation
- `--screen-layout` is that one invocation-scoped layout selector
- if no `--screen` is supplied, `--screen-layout` creates an ad hoc screen using that layout plus any region/default overrides
- if `--screen` is supplied, `--screen-layout` overrides that screen's `layout` field for this invocation

### No-args behavior

Running `fakedata_terminal` with no arguments should print a short orientation message rather than trying to infer a default layout or default screen.

Target output:

```text
fakedata_terminal creates text screens of fake data displays for cinema backgrounds

fakedata_terminal --screens to see prebuilt screens
fakedata_terminal --widgets to see available widgets
fakedata_terminal --layouts to see available layouts
fakedata_terminal --list to list inventory of choices
fakedata_terminal --help for help
```

## CLI Naming Review

The CLI cleanup work is mostly about removing or renaming older broad runtime flags that mixed together three different jobs:

- selecting structure
- overriding screen-wide values
- defining fallback defaults

That naming was harder to read than it should be. The table below captures the required cleanup to reach the target model.

| Current name | Current behavior | Proposed name |
| --- | --- | --- |
| `--layout` | structural override | `--screen-layout` |
| `--theme` | screen-wide override | `--screen-theme` |
| `--default-speed` | screen-wide override, despite the name | remove |
| `--text` | screen-wide override | remove |
| `--glitch` | screen-wide override | `--screen-glitch` |
| `--direction` | screen-wide override, despite the name | remove |
| `--default-widget` | true default/fallback for uncovered panels | `--default-widget` |
| `--default-colour` | true default/fallback for areas still missing colour | `--default-colour` |
| `--image` | broad image source override | remove in favor of `--region-image` |

### Recommended changes

The target broad CLI follows one rule:

- flags that replace screen-wide values should be named `--screen-*`
- flags that provide fallback values should be named `--default-*`
- structural selectors should keep structural names

That leads to the following required changes.

### Retain in the target model

- `--layout` -> `--screen-layout`
  - Every normal invocation builds a screen.
  - The flag should read as overriding the layout field of that screen.
  - It should remain the single layout selector for the invocation.

- `--default-widget`
  - This is a real default.
  - It fills uncovered panels rather than replacing explicit assignments.

- `--default-colour`
  - This is also a real default.
  - It is applied only when an area still has no colour.

- `--theme` -> `--screen-theme`
  - It overrides the screen/runtime theme for the current run.
  - It is not a fallback default once a screen is selected.

- `--glitch` -> `--screen-glitch`
  - It overrides the screen-level glitch interval.
  - The proposed name makes that scope explicit.

### Remove instead of rename

- remove `--text`
  - Text is better expressed per region.
  - If screen-global text is still useful, it should live in YAML screen globals rather than as a broad CLI flag.

- remove `--direction`
- remove `--screen-direction`
  - Direction should live in YAML defaults or region specifications.
  - A broad direction flag is too coarse and duplicates more precise config surfaces.

- remove `--image`
  - Image selection should use `--region-image` for targeted overrides.
  - Broad image input is too ambiguous once multiple image-capable regions exist.

- remove `--default-speed`
- remove `--screen-speed`
  - A single numeric speed for a whole screen is not a meaningful abstraction.
  - Speed should be carried by widget defaults or region-level configuration instead.

### Region-image follow-up

If `--image` is removed in favor of `--region-image`, the region-scoped flag should become more flexible:

- allow `--region-image` to accept a glob as well as a single path
- document that shell wildcard expansion applies before the application sees arguments
- treat quoted patterns such as `--region-image 'assets/*.png'` as regular globs to be resolved by the application
- advise users to quote glob patterns when they want the application, not the shell, to resolve them
- keep YAML and CLI glob semantics aligned as closely as practical

### Rename and removal policy

This planning model does not require backward-compatible CLI or YAML aliases during the rename work.

Assume the rename is applied consistently across:

- code
- packaged YAML
- example YAML
- tests
- docs

Anything outside that scope can adopt the new names when it is next updated.

The intended cleanup is therefore direct:

- rename `--layout` to `--screen-layout`
- rename `--theme` to `--screen-theme`
- rename `--glitch` to `--screen-glitch`
- remove `--text`
- remove `--direction` and `--screen-direction`
- remove `--image` once `--region-image` covers the required glob use cases
- remove `--default-speed` and `--screen-speed`

The implementation work should:

1. rename the supported public flags and config keys in-tree
2. update help text, docs, examples, and packaged YAML to use only the new names
3. expand `--region-image` to cover glob inputs with clearly documented wildcard semantics
4. add the post-parse resolved-screen validation pass described below
5. remove references to the old names rather than preserving compatibility shims

That includes:

- keep only one layout selector per invocation
- reject incompatible `--screen` and `--screen-layout` combinations before rendering starts
- reject invalid resolved widget/modifier combinations before rendering starts
- eagerly validate image inputs and image dependencies before rendering starts

### What should not be introduced

The CLI should not try to support both a broad screen override and a separate broad fallback default for the same modifier unless there is a strong real use case.

For example, adding both:

- `--screen-speed`
- `--default-speed`

would reinforce a concept that is not actually meaningful if speed should be region-specific.

The cleaner model is to avoid broad speed flags entirely and keep speed in YAML defaults, widget defaults, and region-level overrides.

Screen-wide timing control should not be expanded beyond the existing runtime `+` / `-` adjustment behavior.

Timing configuration should otherwise remain widget-level rather than screen-configurable.

## Post-Parse Validation

The runtime should perform a full resolved-screen lint pass after parsing CLI arguments and applying overrides, but before any rendering begins.

This is a startup validation step for the requested invocation, not a late runtime check.

The goal is to catch every possible error before curses setup, animation startup, or partial rendering.

The validation target is the final screen spec that would be rendered for this invocation.

That pass should check at least:

- do the resolved region assignments fit the resolved layout
- if a screen is invoked with `--screen-layout`, are its region assignments compatible with that layout
- are widget modifiers valid for the resolved widget assigned to each region
- are image files present and readable
- can image inputs be converted to ASCII with the currently available dependencies
- does every `cycle.widgets` entry name a real supported widget
- do cycle definitions avoid invalid members such as recursive or disallowed widget choices

Modifier validation should follow these special rules:

- modifiers supplied only through defaults are not errors just because a particular resolved widget does not use them
- stale modifiers left attached to a region whose widget was overridden are not errors if they are merely inert leftovers

Example:

- if YAML assigns region `P1` to widget `gauge` with `direction: backward`
- and the CLI changes that region to `life`
- then `direction: backward` should not be treated as a fatal error for that invocation if it is only an inherited unused appendage

Image validation should be eager:

- verify that referenced files exist during the pre-render lint pass
- attempt the ASCII conversion path during that pass as well
- this should surface missing `jp2a`, missing Pillow support, unreadable files, or decode failures before rendering starts

Error reporting should describe the resolved invocation context, for example:

- screen/layout incompatibility
- invalid modifier for resolved widget
- missing image dependency
- unreadable image file
- unknown cycle widget

## Naming Rules

User-facing naming should stay stable:

- canonical public spelling: `colour`
- accepted public alias: `color`
- normalized internal key: `color`
- `theme` is the only theme key

This keeps the user-facing model readable while preserving a single normalized internal representation.

Apart from the existing `colour`/`color` handling and supported colour-name aliases, the planning model does not require preserving old names as aliases during terminology cleanup.

## Recommended User Mental Shortcut

Users should be able to reason about the system with one short rule:

- config resolves defaults first, then screens and CLI resolve the actual screen; narrower scope wins when two values compete

And one slightly longer version:

1. layouts define shape
2. widgets define widget-type defaults and behavior
3. defaults are resolved before concrete areas are built
4. screens compose a screen
5. CLI overrides the chosen screen for one execution

## Transition Work

The codebase should be brought into this model by making the remaining structural changes explicit:

- adopt `data/screens.yaml` and `screens.<name>.*` terminology everywhere user-facing
- finish extracting widget metadata and widget defaults into `widgets.yaml`
- rename CLI flags to the target spellings used in this document
- remove broad flags that do not fit the model
- implement the resolved-screen validation pass before any rendering begins
- update packaged configs, examples, tests, and docs so they express only the target model

Resolved decisions that should now be treated as fixed during implementation:

- do not add `screens.<name>.defaults`; screen-wide values remain direct screen fields
- leave `enabled` runtime enforcement undecided for now; do not block current cleanup work on it
- `--region-image` should accept ordinary glob patterns, with quoted CLI patterns resolved by the application
- keep timing configuration widget-level; the only screen-wide timing control is runtime `+` / `-`

## Non-Goals

This document does not try to settle every schema question. In particular, it does not require a final answer yet on:

- whether `enabled` is validation-only or also enforced at runtime

Those decisions should be made in a way that preserves the model above, not replaces it.
