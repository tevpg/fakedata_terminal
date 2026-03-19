# Config Cleanup TODO

This document is the implementation backlog for bringing the codebase into the target model defined in `configuration_model.md`.

It is intentionally execution-oriented:

- the target model is already decided unless explicitly called out below
- tasks should be implemented in chunks that leave the codebase runnable
- startup validation should catch every avoidable error before rendering begins

## Target State

- `data/layouts.yaml`: geometry only
- `data/widgets.yaml`: widget metadata, widget defaults, widget behavior, widget timing
- `data/screens.yaml`: app defaults and named screens
- user/project/`--config` overlays participate in the same merge model for layouts, widgets, screens, and defaults
- runtime terminology is `screen`, not `scene`, in user-facing config and CLI
- the CLI builds one resolved screen per invocation
- the CLI has exactly one layout selector per invocation: `--screen-layout`
- the runtime validates the fully resolved screen after parsing and before rendering

## Naming Rules To Preserve

- `theme` is the only theme key in config
- internal normalized key: `color`
- public/user-facing canonical spelling: `colour`
- public/user-facing supported alias: `color`

Apart from `colour`/`color` and supported colour-name aliases, the cleanup work should not preserve old public names as compatibility aliases.

## Validation Principle

- detect errors at startup rather than while running, whenever possible

That includes:

- bad YAML structure
- missing files or bad file paths
- unsupported widget/modifier combinations that can be known before rendering
- screen/layout incompatibilities
- disabled widgets still referenced by resolved config
- missing image dependencies or unreadable image inputs

## Execution Chunks

### Chunk 1: Rename the user-facing model

Status: largely complete

- replace user-facing `scene` terminology with `screen`
- adopt `data/screens.yaml` and `screens.<name>.*` terminology consistently
- update CLI/help/docs/examples to use:
  - `--screen`
  - `--screen-layout`
  - `--screen-theme`
  - `--screen-glitch`
- remove the no-args implicit default-layout path
- replace no-args behavior with the short orientation message described in `configuration_model.md`

Exit condition:

- help text, packaged YAML, examples, and docs all speak the target vocabulary

### Chunk 2: Lock the target CLI surface

Status: largely complete

- rename `--layout` to `--screen-layout`
- rename `--theme` to `--screen-theme`
- rename `--glitch` to `--screen-glitch`
- remove `--text`
- remove `--direction` and `--screen-direction`
- remove `--image` once `--region-image` can cover the intended use cases
- remove `--default-speed` and `--screen-speed`
- keep `--default-widget`
- keep `--default-colour`
- keep region-scoped overrides as the narrow patch layer

Exit condition:

- the supported CLI surface matches `configuration_model.md`

### Chunk 3: Finish the config split and overlay model

Status: mostly complete

- make `widgets.yaml` a first-class packaged base file
- merge widget overlays from user/project/`--config` sources the same way as layouts and screens
- remove the remaining compatibility path that sources widget defaults from screen catalogs
- ensure widget metadata, defaults, and timing are resolved from widget config rather than scattered fallback code

Exit condition:

- widget metadata/defaults/timing are sourced through the same overlay model as the rest of config

### Chunk 4: Implement resolved-screen startup validation

Status: in progress

- add a post-parse, pre-render lint pass for the final resolved screen
- validate screen/layout compatibility
- validate resolved widget/modifier compatibility
- validate disabled-widget references in defaults, screens, regions, and cycle lists
- validate image files exist and are readable
- eagerly exercise the image-to-ASCII path to surface missing `jp2a`, missing Pillow support, or decode failures
- validate cycle widget lists contain real supported widgets only
- allow inert leftover modifiers when a region widget is overridden and the leftover modifier is merely unused baggage
- reject direct CLI region overrides when the target widget does not support the requested modifier

Examples that should fail before rendering:

- a screen references region aliases not present in the resolved layout
- a cycle widget names an unsupported or disabled widget
- a default widget is disabled
- an image path does not exist

Exit condition:

- avoidable invocation/config errors are rejected before curses initialization

### Chunk 5: Lock precedence and resolution behavior

Status: partially complete, but not closed

- align code paths with the precedence model in `configuration_model.md`
- ensure defaults resolve before structure and modifiers
- ensure `screens.<name>.*` provides screen-wide runtime values, not hidden per-region fallback
- ensure widget defaults are the main per-region fallback layer
- ensure region overrides are the narrowest and strongest config layer
- ensure `--default-colour` behaves as the remaining broad late fallback only if that is still the intended model

Exit condition:

- runtime behavior matches the target mental model and precedence document

### Chunk 6: Finish docs and tests

Status: not started in earnest

- update packaged configs and examples to express only the target model
- remove stale comments and transitional docs
- add focused tests for:
  - precedence resolution
  - screen/layout compatibility validation
  - resolved widget/modifier validation
  - disabled-widget validation
  - image validation and dependency failures
  - `colour`/`color` alias handling
  - CLI naming and no-args behavior

Exit condition:

- no stale user-facing model remains in docs/examples/tests

## Resolved Decisions

1. Do not add `screens.<name>.defaults`.
   Screen-wide values remain direct screen fields.
2. Leave `enabled` runtime enforcement undecided for now.
   Do not block current cleanup work on that choice.
3. `--region-image` should support regular glob patterns.
   Advise users to quote glob patterns when they want the application to resolve them rather than the shell.
4. Timing configuration remains widget-level.
   The only screen-wide timing control is runtime `+` / `-`.

## Immediate Next Steps

1. Finish Chunk 4 by broadening resolved-screen validation.
   Priorities:
   - eager image decode / ASCII conversion validation
   - any remaining safe widget/modifier checks on the resolved active model
   - preserve the inert-leftover-modifier exception
2. Close the remaining Chunk 5 gaps.
   Priorities:
   - audit the remaining precedence paths for agreement with `configuration_model.md`
   - trim any remaining `scene_*` wrappers or local naming that still obscures the target model
3. Start Chunk 6 with focused tests before more feature work.
   Priorities:
   - CLI naming and no-args behavior
   - screen/layout incompatibility validation
   - direct CLI modifier/widget validation
   - disabled-widget and cycle validation
   - image validation/dependency failures

## Current State Summary

Implemented already:

- user-facing `screen` terminology and `data/screens.yaml`
- `--screen`, `--screens`, `--screen-layout`, `--screen-theme`, `--screen-glitch`
- no-args orientation output
- `data/widgets.yaml` as packaged widget config
- merged widget overlay loading for metadata/defaults/timing/behavior
- removal of `defaults.layout` from the active packaged/default config model
- startup validation for:
  - disabled widgets in defaults, screens, regions, cycle lists, and resolved runtime screens
  - invalid/disabled cycle members
  - empty cycle widgets
  - image areas with no image sources
  - missing image files
  - missing image dependencies before rendering
  - invalid direct CLI region modifier/widget combinations

Still outstanding:

- broader resolved-screen semantic validation beyond the current checks
- focused regression tests
- final cleanup of leftover internal `scene_*` names and stale comments/docs
- eliminate internal-only widget ids from the model entirely
  - every runtime/config widget id should either be a real public widget or not exist as a widget id at all -- in fact the very concept of internal widget should be removed (wiget_metadata.py and perhaps elsewhere)
  - current cleanup target: remove the internal widget name `gauges`
  - rationale: internal widget ids violate the intended model and confuse config/runtime semantics
  - `gauges` is also redundant with composing screens from multiple regions/layouts
- deferred design item:
  - decide whether `cycle.widgets` should support a magic value such as `all`
  - open question: if `all` exists, should it mean all enabled widgets in principle, or only widgets usable on the current platform/dependency set?
