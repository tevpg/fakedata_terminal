# Config Cleanup TODO

## Remaining Work

- decide and implement the final scene schema
  - specifically whether to add `scenes.<name>.defaults`
- make `widgets.yaml` fully participate in the overlay model
  - packaged widget config as base
  - user/project/`--config` widget config layered over it
- remove the remaining compatibility path for widget defaults from scene catalogs after widget overlays are in place
- add startup validation for disabled-widget references
  - scene uses a widget that merged widget config marks `enabled: false`
  - cycle widget lists include disabled widgets
  - default widget is disabled
- add startup validation for mutual compatibility across YAML and CLI options
  - reject modifier/widget mismatches that can be known before runtime
  - example: `--region-image` on a region whose widget is neither `image` nor `cycle`
  - example: region/scene config requests a modifier the selected widget does not support
- decide whether `enabled` should affect runtime behavior or remain metadata-only
- clean up CLI naming and semantics
- go carefully over precedence and sequencing of:
  - packaged YAML
  - user/project/`--config` YAML overlays
  - scene defaults
  - region overrides
  - CLI defaults and CLI region overrides
- finish public docs/examples cleanup so `colour` is treated as canonical everywhere user-facing
- add focused tests for:
  - precedence resolution
  - metadata-driven validation
  - `colour`/`color` alias handling
  - CLI/config backward-compatibility where still intended

## Target Model

- `data/layouts.yaml`: geometry only
- `data/widgets.yaml`: widget metadata, widget defaults, widget behavior/timing
- `data/scenes.yaml`: app defaults and composed scenes
- widget metadata/defaults/behavior remain overrideable via YAML overlays

## Naming Rules To Preserve

- `theme` is the only theme key in config
- internal normalized key: `color`
- public/user-facing canonical spelling: `colour`
- public/user-facing supported alias: `color`

## Validation Principle

- detect errors at startup rather than while running, whenever possible

Justification:

- this is intended to run in the background of a film scene
- it is undesirable to discover an avoidable error during a take if it could have been detected and fixed at startup

Startup validation should catch as much as practical, including:

- dependency problems
- missing files or bad file paths
- disabled widgets still referenced by scenes/defaults/cycle lists
- unsupported modifier/widget combinations
- invalid region/widget/config interactions that can be known before runtime

## Open Decisions

1. Should `scenes.<name>.defaults` exist, or should scene-wide values remain direct scene fields?
2. Should `enabled` be enforced at runtime in addition to startup validation?
3. Exactly how should widget YAML overlays be discovered and merged?
4. What should the final precedence order be across YAML layers and CLI overrides?
5. What should the final CLI naming model be:
   - keep current names
   - move to `--scene-*` plus `--region-*`
   - some hybrid

## Next Good Steps

1. Decide the scene schema.
2. Make widget metadata/behavior overlayable and validate disabled-widget references at startup.
3. Remove the scene-catalog widget-default compatibility path.
4. Review and lock down precedence/sequence rules across YAML and CLI.
5. Clean up CLI naming after the scene schema is settled.
6. Add tests before any further user-facing schema/CLI changes.
