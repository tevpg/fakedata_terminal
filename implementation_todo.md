# Implementation TODO

This is the single execution backlog for remaining work.

Persistent reference material lives elsewhere:

- [README.md](/home/tags/fakedata_terminal/README.md): user-facing usage and config overview
- [configuration_model.md](/home/tags/fakedata_terminal/configuration_model.md): target mental model, precedence, validation principles

## Current Priorities

### 1. Finish precedence and internal cleanup

- close any remaining precedence mismatches with `configuration_model.md`
- trim leftover internal `scene_*` wrappers and naming where practical
- remove stale comments/docs that still describe the old model

### 2. Finish hardening

- add focused regression tests for:
  - any remaining screen/layout incompatibility validation gaps
  - any remaining direct CLI modifier/widget validation gaps
  - any remaining disabled-widget and cycle validation gaps
  - any remaining image validation and dependency-failure gaps
- clean tests/examples/docs around the implemented model

### 3. Finish timing work

- tune widget timing/behavior values in `data/widgets.yaml`
- decide whether any remaining widget-local tick/motion details should stay as implementation details or be promoted into the timing model
- expand timing-focused regression coverage if more timing behavior becomes declarative

### 4. New feature ideas

- 'spiral' widget
- gauge multi-all coloured, the sweep arm changes colour to match the colour of current portion of rim
- flash on/off chaotic disruptive, as though screen is basically going haywire and breaking down
- new object class `sequence`: a series of scenes (or scene definitions?) advanced by keypress or possibly by timer.  Keypress seems more useful, if it goes to something like a dramatic change when actor initiates something....  a timer might loop through a series of scenes, like 'cycle' is for widgets.

## Future Refactors

### Telemetry provider / widget split

- stop treating `sparkline` + `readouts` as a special shared widget family
- split `sparkline` and `readouts` into independent widget implementations
- extract the current shared fake telemetry generation into a separate helper/provider layer
- make telemetry consumption optional per widget rather than implied by widget family
- keep synchronized/shared telemetry streams possible, but not architecturally required
- assess whether `scope`, `gauge`, or later widgets should be able to consume telemetry providers

## Open Questions

### `cycle.widgets: all`

- should `cycle.widgets` gain a magic value such as `all`?
- if yes, should `all` mean:
  - all enabled widgets in principle
  - or only widgets usable on the current platform/dependency set?

## Recently Completed

- removed the internal widget id `gauges` and the separate `INTERNAL_WIDGETS` concept
- kept the public `gauge` widget intact while rejecting the removed `gauges` id at startup
- broadened resolved-screen startup validation without breaking the inert-leftover-modifier exception
- added startup validation coverage for duplicate `cycle.widgets` members and stale-widget rejection
- added portrait-oriented layouts `1x3` and `2x4`
- changed `--layouts` preview rendering to derive row/column spans from layout geometry so equal-sized panels consume equal preview space
- assessed the role and boundary of `MetricsWidgets`; current direction is toward independent widgets plus an optional telemetry-provider layer rather than expanding the shared widget-family abstraction
- renamed the remaining metrics-specific `gauge*` / `ensure_gauges` internals to metrics-oriented names and removed stale metrics-only state from the shared area model
- added focused precedence tests for widget-default, region, CLI, and default-colour resolution, and fixed `--default-colour` so it overrides colours inherited only from config defaults
- added hardening coverage for direct CLI target/overlap failures, unknown region references, image dependency failures, and unassigned-panel rejection when no default widget is configured
- audited timing paths, fixed cycle-start jitter to use the shared timing helper, and added targeted timing tests for scheduler/deadline behavior
- updated timing comments in `data/widgets.yaml` to describe the current shared scheduler model rather than the older burst/steady bucket terminology

## Working Rules

- do not introduce `screens.<name>.defaults`
- keep `configuration_model.md` as the source of truth for precedence and scope
- direct CLI modifier overrides must be valid for the target widget
- inert inherited leftovers from replaced region assignments are allowed
- do not preserve a separate class of internal-only widget ids in config/runtime
- treat emitted `exit` YAML as a lossless scene serialization: if pasted into `scenes.yaml`, it should recreate the same resolved scene except where later layout/widget definition changes make that impossible
