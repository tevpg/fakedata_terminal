# Timing TODO

## Current Status

The shared timing framework is in place and the config split work needed for it is largely done.

Already landed:

- centralized timing helpers in `timing_support.py`
- packaged timing/behavior metadata in `data/widgets.yaml`
- overlay-aware loading for widget timing/behavior metadata
- timing/default behavior now sourced through widget metadata rather than a separate hardcoded loader

This means timing work is no longer blocked on the config split. The remaining timing work is mostly audit, tuning, and tests.

## Remaining Work

- tune actual timing values now that the shared timing framework is in place
  - cadence factors
  - motion factors
  - direction-reroll timings/probabilities
  - read-refresh/feed-scroll intervals
- audit for any remaining ad hoc tick/count-based timing behavior that should move under the shared model
- add regression coverage for:
  - timing behavior across widgets
  - pause/resume semantics
  - deadline shifting
  - direction-random behavior
  - cycle timing
- verify that runtime `+` / `-` remains the only screen-wide timing control path
- remove or compress any remaining stale timing comments/docs elsewhere once the tuned model is settled

## Timing Model To Preserve

- shared `now`/`dt` timing path
- centralized timing helpers in `timing_support.py`
- per-widget timing/behavior metadata in `widgets.yaml`
- explicit deadline-based handling for timed events
- shared speed mapping plus per-widget cadence factors
- timing configuration remains widget-level
- the only screen-wide timing control is runtime `+` / `-`

## Open Decisions

1. Which timing/behavior values still need tuning by observation?
2. Are there any widgets that still need semantic-motion treatment beyond the current ones?
3. What minimum regression coverage is enough before further timing changes?

## Next Good Steps

1. Audit remaining widget timing behavior for anything still outside the shared model.
2. Tune the current `data/widgets.yaml` values against actual runtime feel.
3. Add timing-focused regression tests or at least repeatable verification cases.
4. Remove stale timing comments that still refer to pre-split config loading.
