# Config Cleanup Proposal

## Goal

Clean up how layouts, scenes, widget defaults, widget behavior, and CLI overrides are specified so the system is easier to understand, document, validate, and extend.

The current system works, but it has three structural problems:

1. Responsibility is split unevenly across `data/layouts.yaml`, `data/scenes.yaml`, and `widgets.yaml`.
2. Modifier names and capabilities drift across YAML, CLI, docs, and runtime code.
3. CLI/global/default semantics are not uniform across modifiers.


## Proposed End State

Use three config layers with clear roles:

1. `data/layouts.yaml`
   Owns geometry only.
   Contains panel definitions and named region aliases.
   Contains no widget behavior, no themes, no defaults, and no scene content.

2. `data/widgets.yaml`
   Owns widget definitions.
   Contains:
   - widget capability metadata
   - widget-level default modifiers
   - widget behavior/timing tunables
   - optional widget grouping metadata for docs/showcase

3. `data/scenes.yaml`
   Owns runnable scenes only.
   Contains:
   - global app defaults
   - named scenes
   - scene-level defaults
   - region assignments per scene

This separates:
   layout structure
   widget specification
   scene composition


## Naming Rules

Standardize on one term per concept.

- Use `theme`, not `source_theme`.
- Use `color`, not mixed `colour`/`color`, internally.
- Maintain `colour` as a fully supported input alias in YAML and CLI.
- Normalize both `color` and `colour` to internal `color`.
- Use `widget`, `layout`, `scene`, `region` consistently in docs and CLI.
- Use `modifiers` as the umbrella term for configurable per-widget/per-region options.

Recommended modifier names:

- `speed`
- `theme`
- `text`
- `color`
- `direction`
- `image`
- `cycle`

Nested modifier keys should also be consistent:

- `image.paths`
- `image.path`
- `image.glob`
- `cycle.widgets`
- `cycle.change_interval_seconds`
- `cycle.start_jitter_range_seconds`


## Config Structure Proposal

### `data/layouts.yaml`

Keep the current basic shape:

```yaml
layouts:
  3x3:
    panels:
      P1: {x: 0.00, y: 0.00, w: 0.3333, h: 0.3333}
    regions:
      L: P1+P2+P3
```

Rules:

- No widget assignments here.
- No scene defaults here.
- No widget metadata here.
- Region aliases remain layout-local.


### `data/widgets.yaml`

Move all widget-owned config here.

Proposed shape:

```yaml
widgets:
  text:
    enabled: true
    supports: [speed, theme, text, direction]
    defaults:
      speed: 55
      direction: forward
    behavior:
      timing:
        cadence_factor: 0.55
      direction_random:
        backward_probability: 0.12
        none_probability: 0.10
        forward_probability: 0.78

  image:
    enabled: true
    supports: [speed, image]
    defaults:
      image:
        glob: "geom*.png"
    behavior:
      timing:
        cadence_factor: 0.67
```

Rules:

- `enabled` is a per-widget availability flag reserved for future use.
- `enabled` should be parsed and validated now, even if runtime behavior does not change yet.
- `supports` is the source of truth for docs, validation, and CLI help.
- `defaults` contains widget-level fallback modifiers.
- `behavior` contains internal tunables not meant to be scene-specific unless explicitly exposed.
- Widget behavior may include widget-owned characteristics that are not region modifiers, such as `life.behavior.restart.max_iterations`.


### `data/scenes.yaml`

Limit this file to defaults and composed scenes.

Proposed shape:

```yaml
defaults:
  layout: 2x2
  theme: science
  speed: 55
  widget: blank

scenes:
  science:
    layout: 3x3
    defaults:
      theme: science
      speed: 27
      direction: forward
    regions:
      L2:
        widget: text_wide
        direction: random
      P7:
        widget: readouts
        text: TIMEFLUX REDUCTIONS
        color: multi-normal
```

Rules:

- Top-level `defaults` are app/runtime defaults.
- `scenes.<name>.defaults` are scene-wide defaults that apply to the scene.
- `scenes.<name>.regions.<region>` only contains region/widget assignment and region overrides.
- Remove top-level `widgets:` from this file entirely.


## Modifier Model

### Principle

A modifier should mean the same thing in all three places:

- widget definition
- scene config
- CLI

If a modifier is valid for a widget, that should be declared once and reused everywhere.


### Proposed Capability Table

Use one central registry, ideally generated from `data/widgets.yaml`.

Example:

```yaml
widgets:
  gauge:
    enabled: true
    supports: [speed, color, text, direction]
  scope:
    enabled: true
    supports: [speed, theme, text, direction]
  sweep:
    enabled: true
    supports: [speed]
  cycle:
    enabled: true
    supports: [speed, theme, color, cycle]
```

Usage:

- Scene validation checks region modifiers against `supports`.
- Widget showcase/docs render supported modifiers from `supports`.
- CLI help text is generated from the same data.
- Runtime resolution uses the same data to decide what is legal.

Non-modifier widget characteristics should remain in widget behavior, not in scene or CLI config.

Example:

```yaml
widgets:
  life:
    enabled: true
    supports: [speed, color]
    defaults: {}
    behavior:
      restart:
        on_stable_or_loop: true
        on_max_iterations: true
        max_iterations: 200
```

In this model:

- `speed` and `color` are region modifiers
- `max_iterations` is a widget characteristic

Other widget-owned behavior properties that should remain widget-level only:

- `blocks` blackout/dark-block bias
- `gauge` blip spawn probability
- `gauge` blip lifetime range
- `sweep` wake/trail spawn probabilities
- `image` transition mode and related transition behavior

These should live in `widgets.yaml` behavior sections or remain in code until they are intentionally made configurable.
They should not be exposed in scenes, regions, or CLI flags by default.


### Application Order

Define one explicit precedence model:

1. built-in widget defaults from `data/widgets.yaml`
2. app defaults from `scenes.yaml: defaults`
3. scene defaults from `scenes.<name>.defaults`
4. region config from `scenes.<name>.regions.<region>`
5. CLI scene-wide overrides
6. CLI region overrides

Notes:

- Widget defaults should be the lowest layer because they are widget-owned fallback behavior.
- Scene defaults should apply uniformly to all modifiers that support scene-wide use.
- Region overrides should always win over scene defaults.
- CLI region overrides should always be the final layer.


### Scene-Wide vs Region-Only Modifiers

Decide this explicitly.

Recommended rule:

- `speed`, `theme`, `text`, `color`, `direction` may be scene-wide and region-specific.
- `image` may be scene-wide as a fallback and region-specific.
- `cycle` may be scene-wide only if every cycle widget should inherit it; otherwise region-only.

If `cycle.change_interval_seconds` is intentionally global for all cycle widgets, keep it in widget behavior only.
If scenes should tune cycle cadence, expose it as a supported scene/region modifier.


## CLI Proposal

### Current Problem

CLI naming mixes three models:

- `--default-speed`, `--default-color`, `--default-widget`
- `--theme`, `--text`, `--image`, `--direction`
- `--region-*`

That makes it unclear which flags are:

- app defaults
- scene-wide overrides
- fallback-only values


### Proposed CLI Model

Use parallel naming:

- `--scene`
- `--layout`
- `--scene-speed`
- `--scene-theme`
- `--scene-text`
- `--scene-color`
- `--scene-direction`
- `--scene-image`
- `--default-widget`
- `--region-widget`
- `--region-speed`
- `--region-theme`
- `--region-text`
- `--region-color`
- `--region-direction`
- `--region-image`

Optional later additions:

- `--region-cycle-widgets`
- `--region-cycle-change-interval`

Compatibility plan:

- Keep existing flags temporarily as aliases.
- Map:
  - `--theme` -> `--scene-theme`
  - `--text` -> `--scene-text`
  - `--direction` -> `--scene-direction`
  - `--image` -> `--scene-image`
  - `--default-colour` -> `--scene-color` or `--default-color`, depending on final meaning
- Emit deprecation warnings before removing old names.


### CLI Semantics Recommendation

Choose one of these and apply it consistently:

Option A:
   `--scene-*` means scene-wide override.
   `--default-widget` only fills unassigned panels.

Option B:
   all non-region modifiers are `--default-*` fallback values.

Option A is clearer and closer to current behavior.

Do not expose widget-internal behavior tunables such as `life` max iterations, `blocks` blackout bias, `gauge` blip behavior, `sweep` wake probabilities, or image transition behavior on the CLI unless there is a demonstrated need for scene/runtime tuning.


## Validation Changes

Add schema-level checks so unsupported modifier use is rejected early.

Examples:

- reject `theme` on widgets that do not support it
- reject `direction` on `sweep` unless support is intentionally added
- reject `cycle.*` on non-`cycle` widgets
- reject undocumented keys in widget defaults and scene regions
- reject doc/help entries for modifiers not actually supported

Implementation direction:

- replace hard-coded `_widget_attribute_names()` with generated data
- validate scene region keys against `widgets.<name>.supports`
- validate CLI region override flags against target widget capability


## Documentation Changes

Update docs to match the normalized model.

Tasks:

- document `theme`, not `source_theme`
- document `color`, with `colour` as compatibility alias if retained
- remove references to nonexistent `cycle.duration`
- document whether cycle timing is widget behavior or scene modifier
- document exact precedence order once finalized
- document which modifiers are supported by each widget from generated metadata


## Migration Plan

### Status

Completed:

- Added per-widget `enabled`, `supports`, and `defaults` placeholders in `widgets.yaml`.
- Added a shared widget metadata loader/validator.
- Switched CLI widget showcase/help to read supported modifiers from shared metadata.
- Added metadata validation at startup.
- Added compatibility-safe support checks in scene/widget-default validation.
- Removed the stale `cycle.duration` help reference.
- Removed packaged non-scene widget metadata from `data/scenes.yaml`.
- Switched widget names/defaults to resolve through shared widget metadata.
- Added internal `theme` alias support alongside `source_theme`.
- Consolidated runtime area/scene precedence resolution in `scene_config.py` through shared helpers, without changing behavior.

Not completed:

- Runtime enforcement of `enabled`
- Canonical key renames (`theme`, `color`)
- CLI renaming
- Full precedence/schema cleanup

### Stage 1: Naming Cleanup

- Add `theme` as the canonical YAML key.
- Accept `source_theme` as a legacy alias.
- Add `color` as the canonical YAML/CLI/docs spelling.
- Keep `colour` as a fully supported input alias during and after migration.
- Update README and showcase text.


### Stage 2: Centralize Capability Metadata

- Extend the shared widget metadata beyond capability/help validation.
- Make widget-default resolution read canonical defaults from shared metadata.
- Remove the remaining compatibility dependency on scene-config widget defaults if no external overlays still need it.
- Add tests around metadata loading and validation.


### Stage 3: Move Widget Defaults Out of `scenes.yaml`

- Remove any remaining fallback assumptions that widget defaults may come from scene catalogs.
- Update docs and overlays to treat `data/widgets.yaml` as the canonical widget-default location.


### Stage 4: Normalize Scene Defaults

- Introduce `scenes.<name>.defaults`.
- Make scene-wide modifier resolution uniform.
- Remove remaining ad hoc post-processing like special default-color passes if no longer needed.


### Stage 5: CLI Rename and Alias Period

- Add canonical `--scene-*` flags.
- Keep old flags as aliases.
- Print warnings for deprecated forms.
- Remove old forms after docs/tests are updated.


## Concrete Code Tasks

1. Split `scene_config.py` responsibilities:
   - layout catalog loading
   - scene catalog loading
   - widget metadata loading
   - runtime merge/resolution

2. Remove non-scene metadata from `data/scenes.yaml`.

3. Introduce normalized key aliases:
   - `source_theme` -> `theme`
   - `colour` -> `color`

4. Make precedence resolution explicit in one helper instead of spreading it across:
   - scene config resolution
   - runtime layout resolution
   - CLI post-processing

5. Add tests for:
   - precedence
   - unsupported modifiers
   - disabled-widget placeholder parsing
   - alias handling
   - CLI backward compatibility
   - generated widget capability docs


## Recommended First Implementation

Status: completed.

Start with capability centralization only. Do not rename CLI flags or move config files yet.

Scope:

1. Define per-widget metadata in `data/widgets.yaml`:
   - `enabled`
   - `supports`
   - `defaults`

2. Add a loader/helper that exposes that metadata to:
   - CLI widget showcase/help
   - scene validation
   - widget capability documentation

3. Keep runtime behavior unchanged:
   - `enabled` is accepted and validated, but not enforced yet
   - existing CLI names stay as they are
   - existing precedence stays as it is
   - existing file locations stay as they are

Why this is the right first slice:

- it is low risk
- it removes duplicated hard-coded modifier tables
- it immediately improves consistency between docs, validation, and CLI help
- it creates the schema foundation needed for later cleanup
- it introduces `enabled` early without forcing behavior changes yet


## Open Decisions

1. Should cycle timing be scene-configurable, or remain widget behavior only?
2. Should image source selection support the same full structure on CLI as YAML?
3. Should `color` become the only public spelling, or should both stay first-class?
4. Should scene-wide defaults live under `scenes.<name>.defaults`, or continue as direct scene fields?


## Recommended Direction

Use this combination:

- `layouts.yaml` for layout geometry only
- `widgets.yaml` for widget metadata/defaults/behavior
- `scenes.yaml` for app defaults and composed scenes
- `theme` and `color` as canonical names
- `--scene-*` plus `--region-*` as canonical CLI naming
- one generated widget capability registry as the source of truth

That gives the cleanest long-term model and removes the current drift between code, YAML, CLI, and docs.
