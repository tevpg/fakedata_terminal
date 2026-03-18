# Timing TODO

## Remaining Work

- tune actual timing values now that the shared timing framework is in place
  - cadence factors
  - motion factors
  - direction-reroll timings/probabilities
  - read-refresh/feed-scroll intervals
- audit for any remaining ad hoc tick/count-based timing behavior that should move under the shared model
- decide which timing controls, if any, should ever become scene-configurable instead of remaining widget-level behavior
- add regression coverage for:
  - timing behavior across widgets
  - pause/resume semantics
  - deadline shifting
  - direction-random behavior
  - cycle timing
- remove or compress any remaining stale timing comments/docs elsewhere once the tuned model is settled

## Timing Model To Preserve

- shared `now`/`dt` timing path
- centralized timing helpers in `timing_support.py`
- per-widget timing/behavior metadata in `widgets.yaml`
- explicit deadline-based handling for timed events
- shared speed mapping plus per-widget cadence factors

## Open Decisions

1. Which timing/behavior values still need tuning by observation?
2. Should any timing controls become scene-configurable, or should they remain widget-level only?
3. Are there any widgets that still need semantic-motion treatment beyond the current ones?
4. What minimum regression coverage is enough before further timing changes?

## Next Good Steps

1. Audit remaining widget timing behavior for anything still outside the shared model.
2. Tune the current `widgets.yaml` values against actual runtime feel.
3. Add timing-focused regression tests or at least repeatable verification cases.
