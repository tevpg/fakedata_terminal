# Implementation TODO

This is the single execution backlog for remaining work.

Persistent reference material lives elsewhere:

- [README.md](/home/tags/fakedata_terminal/README.md): user-facing usage and config overview
- [configuration_model.md](/home/tags/fakedata_terminal/configuration_model.md): target mental model, precedence, validation principles

## Current Priorities

### 1. Finish startup validation

- broaden resolved-screen semantic validation where it is safe
- preserve the inert-leftover-modifier exception
- keep all avoidable failures pre-render
- decide whether any remaining `cycle` validation rules are still missing

### 2. Finish precedence and internal cleanup

- close any remaining precedence mismatches with `configuration_model.md`
- trim leftover internal `scene_*` wrappers and naming where practical
- eliminate internal-only widget ids from the model entirely
- rename leftover `MetricsWidgets` `gauge*` / `ensure_gauges` naming that now refers to `sparkline` + `readouts`
- assess the role and boundary of `MetricsWidgets` itself:
  - is it still the right abstraction for `sparkline` + `readouts`
  - which remaining `gauge_*` state is still semantically correct vs stale
  - whether any state should move, split, or be removed entirely
- remove stale comments/docs that still describe the old model

### 3. Finish hardening

- add focused regression tests for:
  - precedence resolution
  - screen/layout incompatibility validation
  - direct CLI modifier/widget validation
  - disabled-widget and cycle validation
  - image validation and dependency failures
  - `colour` / `color` handling
- clean tests/examples/docs around the implemented model

### 4. Finish timing work

- audit for any remaining ad hoc timing paths
- tune widget timing/behavior values in `data/widgets.yaml`
- add timing-focused regression coverage

### 5. New feature ideas

- 'swirl' widget
- gauge multi-all coloured, the sweep arm changes colour to match the colour of current portion of rim
- flash on/off chaotic disruptive, as though screen is basically going haywire and breaking down

## Open Questions

### `cycle.widgets: all`

- should `cycle.widgets` gain a magic value such as `all`?
- if yes, should `all` mean:
  - all enabled widgets in principle
  - or only widgets usable on the current platform/dependency set?

## Working Rules

- do not introduce `screens.<name>.defaults`
- keep `configuration_model.md` as the source of truth for precedence and scope
- direct CLI modifier overrides must be valid for the target widget
- inert inherited leftovers from replaced region assignments are allowed
- do not preserve a separate class of internal-only widget ids in config/runtime
