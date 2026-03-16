# Timing TODO

This file captures the current timing-design direction for FakeData Terminal. It is intended to evolve as the design and implementation plan become more concrete.

## Goals

The primary goals are non-functional:

- maintainability
- reliability
- consistency
- easier reasoning about widget behavior
- easier future refactoring and widget additions

There are also functional timing goals:

- widgets at the same `speed` setting may still animate at different real-world rates
- those differences should be intentional and centrally understandable
- true time-based events should be modeled explicitly
- the `speed` scale remains `1..100`
- the timing model should ideally be clock-based rather than loop-count-based

## Desired Model

### 1. Shared Clock-Based Timing

Use one real-time clock source for the application.

The runtime should compute `now` once per main-loop iteration and pass it into widget update logic. Widget modules should not call `time.time()` directly.

Benefits:

- more consistent behavior across hardware
- clearer pause/resume behavior
- simpler implementation of deadlines like `--exit`
- more deterministic reasoning and testing

### 2. Separate Animation Cadence From Timed Events

There are two different timing concerns:

#### Animation cadence

This is how often a widget advances one animation step.

Examples:

- `blocks` changes one or more cells
- `matrix` advances rain columns
- `life` computes the next generation
- `scope` advances the signal trace
- `gauge` advances its display state

#### Timed events

These are explicit deadlines and durations that are not simply "advance one animation step now".

Examples:

- `cycle_next_change`
- `exit_at`
- `gauge_next_spin_change`
- `textwall_next_reverse_at`
- `textwall_pause_until`
- showcase/demo/glitch timers

These should remain deadline-based, using `now` and explicit stored timestamps.

### 3. Shared Speed Mapping

Keep `speed` on a scale of `1..100`, but make it map to a shared base interval.

Possible shape:

- `speed 1` = about 1 animation step per second for a widget with multiplier `1.0`
- `speed 100` = some chosen maximum "super fast" rate for a widget with multiplier `1.0`

The exact endpoints still need to be chosen.

### 4. Per-Widget Relative Rate Factors

Widgets animated at the same speed may still need different real-world cadences.

That should be defined intentionally, either:

- by constants near the top of each widget module, or
- in a centralized table

The intended framing is:

- there is some shared maximum or reference cadence
- each widget uses a proportion of that cadence

So the factors would normally be in the range `(0, 1]`.

Examples:

- `blocks`: `1.0x`
- `scope`: `0.75`
- `matrix`: `0.90`
- `life`: `0.60`

Then:

- `base_rate = f(speed)`
- `effective_widget_rate = base_rate * widget_rate_factor`

Equivalent interval form:

- `base_interval = g(speed)`
- `effective_widget_interval = base_interval / widget_rate_factor`

The rate form may be the clearer mental model:

- `1.0` means the widget uses the full reference cadence
- `0.75` means the widget runs at 75% of that cadence
- `0.5` means the widget runs at half of that cadence

This provides consistency without forcing all widgets to feel identical.

## Hardware Considerations

If the timing system is clock-based, then hardware may limit achievable speeds.

One possible future idea:

- detect if a machine cannot sustain the requested maximum cadence
- warn at startup
- optionally cap effective speed

Example concept:

- on an older machine, perhaps practical speed tops out around `80`
- higher requested speeds could be truncated with a warning

This is only a future possibility. It is not a required first step.

## Text Timing

The current text timing model has special burst/variable-rate behavior.

That behavior may no longer be necessary and may be a source of complexity.

Working assumption:

- remove the special variable burst timing for text
- make text use the same cadence framework as other widgets

If some irregularity is still desired later, reintroduce it as a small jitter layered on top of the shared timing model, not as a separate framework.

## Gauge Timing Requirement

The `gauge` widget has an additional timing requirement:

- perceived speed should be based on rotational speed, not on character or cell changes

That means:

- at the same `speed` setting, a large gauge and a small gauge should rotate at the same angular rate
- size should not make a larger gauge appear slower

Current problem:

- a larger gauge currently takes longer to complete a full rotation because its visible motion effectively depends on more incremental character changes

Desired outcome:

- gauge timing should be expressed in terms of angular velocity, such as "radians per second" or "rotations per second"
- rendering size should affect only how that motion is drawn, not how quickly the widget rotates

This is a useful example of the difference between:

- animation cadence
- semantic motion rate

For most widgets, those may be close enough to treat together. For `gauge`, they should be separated:

- cadence determines how often the widget updates
- angular velocity determines how far the indicator rotates per update based on elapsed time

This may also be a good pattern for any future widgets whose motion should be expressed in physical or semantic terms rather than just "advance one step".

## Current Problems In The Codebase

The code currently has a partial timing framework, but it is inconsistent.

Observed issues:

- the runtime owns `next_update`, but widgets still call `time.time()` directly
- pause/resume works by manually shifting many separate deadline fields
- `speed` means different things in different widgets
- some widgets are mostly tick-driven, some are wall-clock-driven, and some are mixed
- text timing uses a different model from other widgets

This increases cognitive load and makes future refactors harder.

## Proposed Refactor Direction

### Phase 1: Centralize Clock Access

First, make `now` the only clock source.

Tasks:

- remove internal `time.time()` calls from widget modules and timing helpers
- pass `now` into all timing-sensitive helper methods
- keep existing behavior as much as possible while centralizing the clock

This is intended as the lowest-risk first step.

### Phase 2: Standardize Timing Vocabulary

Use explicit area-state deadlines for true timed events.

Examples:

- `next_update`
- `cycle_next_change`
- `gauge_next_reads_at`
- `gauge_next_spin_change`
- `textwall_next_reverse_at`
- `textwall_pause_until`

All such fields should be updated only from the passed-in `now`, not from ad hoc calls to the system clock.

### Phase 3: Replace Special Text Burst Timing

Remove the separate burst model for text widgets and put text on the same cadence model as the rest of the system.

### Phase 4: Introduce Shared Speed + Widget Rate Factors

Add a shared timing helper or timing table with:

- a speed-to-base-interval mapping
- per-widget relative rate factors

Then make animation cadence consistent across widget families.

### Phase 5: Tune Behavior

After the framework is in place:

- choose the actual `speed 1` and `speed 100` intervals
- tune per-widget multipliers
- decide whether any widgets need small timing jitter for aesthetic reasons

## Candidate API Shape

Possible shared helpers:

- `base_interval(speed) -> seconds`
- `widget_interval(widget, speed) -> seconds`
- `schedule_next(area, now, interval)`
- `deadline_passed(now, deadline)`

Possible contract:

- runtime owns the master `now`
- runtime decides whether an area is due for update
- widgets may own explicit named deadlines in area state
- widgets may inspect and advance those deadlines using `now`
- widgets do not call the system clock directly

## Working Design Principles

- prefer one coherent model over many widget-specific timing schemes
- keep widget-specific feel through rate multipliers, not bespoke frameworks
- keep true deadlines explicit
- make pause/resume simpler by reducing hidden timing state
- optimize first for clarity and maintainability, then for tuning and polish

## Open Questions

- What should `speed 1` mean in real time?
- What should `speed 100` mean in real time?
- Should widget rate factors live in each module or in a central table?
- Should hardware-aware speed capping ever be implemented?
- Should text timing retain any jitter or become fully regular?
- Which timed events should remain fully wall-clock-based, and which should be expressed as multiples of the base widget cadence?
- Which widgets, like `gauge`, should express motion in semantic units such as rotations-per-second rather than simple per-update steps?

## Immediate Next Step

The most useful first implementation step is:

1. centralize clock access
2. pass `now` through timing-sensitive helpers
3. keep behavior the same for now

That creates a safer base for the later timing redesign.

## Rebuild Strategy For This Repo

Assumption:

- a separate production copy of the app will remain available for normal use
- this repository can therefore be used for a less-constrained timing rebuild
- intermediate states in this repository do not have to remain fully runnable

This changes the preferred approach.

Instead of optimizing for continuous compatibility during every step, the timing work here should optimize for:

- conceptual clarity
- removal of mixed timing models
- deletion of obsolete timing code
- coherent end-state design over temporary compatibility

The separate production copy becomes:

- the stable reference implementation
- the comparison target for behavior and feel
- the fallback when this repository is temporarily broken during the timing rewrite

## Recommended Rewrite Plan

This is a subsystem rewrite, not just an incremental cleanup.

### Stage 0: Freeze The Target Design

Before changing runtime code further, finalize a few design choices:

- one shared runtime clock
- one shared speed-to-base-rate mapping
- one central table of widget cadence factors
- explicit deadline fields for real timed events
- semantic motion rates for widgets that need them, starting with `gauge`
- removal of the current text burst timing model

Decisions still to make:

- exact real-time meaning of `speed 1`
- exact real-time meaning of `speed 100`
- initial widget cadence factors
- whether `update()` should receive `now` only, or both `now` and `dt`

Recommendation:

- standardize on `update(..., now, dt)`

Reason:

- `now` is useful for deadlines
- `dt` is useful for semantic motion such as rotations-per-second

### Stage 1: Build A New Timing Core

Create a new timing subsystem, likely in a dedicated module.

Responsibilities:

- define the shared speed mapping
- define widget cadence factors
- define optional widget motion-rate factors
- compute effective animation cadence for a widget at a given speed
- provide helpers for deadlines and scheduling

Candidate contents:

- `base_rate(speed)` or `base_interval(speed)`
- `widget_cadence(widget, speed)`
- `widget_motion_rate(widget, speed)` where needed
- `schedule_next(now, interval)`
- `deadline_due(now, deadline)`

This stage should be implemented cleanly without worrying yet about preserving the old runtime paths.

### Stage 2: Redefine The Runtime Timing Contract

Change the expected contract between the runtime and widget families.

Target contract:

- runtime computes `now`
- runtime computes `dt`
- runtime checks `area["next_update"]`
- runtime calls `family.ensure(...)`
- runtime calls `family.update(..., now, dt)`
- runtime calls `family.render(...)`

Rules:

- widgets do not call the system clock directly
- widgets may maintain explicit deadlines in area state
- widgets do not invent independent timing frameworks

This stage may temporarily break widget behavior while the families are being rewritten.

### Stage 3: Convert Widgets By Family

Convert whole families to the new timing model, one family at a time.

Recommended order:

1. `TextWidgets`
2. `MetricsWidgets`
3. `VisualWidgets`
4. `ImageWidgets`

Reasoning:

- `TextWidgets` currently contain the burst timing and cycle-related timing complexity
- `MetricsWidgets` have their own internal readout timers
- `VisualWidgets` include `gauge`, `scope`, `sweep`, `matrix`, `blocks`, `tunnel`
- `ImageWidgets` are comparatively simpler once the shared model exists

Within each family:

- remove direct `time.time()` usage
- remove family-specific cadence models
- move to shared cadence scheduling
- keep only true deadlines as explicit deadline fields

### Stage 4: Rewrite Gauge Timing Semantics

Treat `gauge` as the first widget with explicit semantic motion.

Design target:

- speed controls angular velocity, not character-step count
- large and small gauges rotate at the same real-world rate
- update cadence and angular motion are separated

Possible model:

- `gauge_angle += angular_velocity * dt`

Where:

- `angular_velocity` is derived from speed and the widget's motion-rate factor
- rendering size affects only how the angle is drawn, not how quickly it changes

This stage is important enough that it should be handled explicitly, not as a side effect of the general timing rewrite.

### Stage 5: Remove The Old Timing System

Once all families use the new timing core:

- delete text burst timing helpers
- delete obsolete ad hoc timing code
- remove compatibility scaffolding
- simplify pause/resume logic around the smaller set of real deadlines

This stage should aim to leave:

- one shared cadence model
- a small set of explicit deadline fields
- a smaller and clearer main loop

### Stage 6: Tune And Compare

Once the rewrite is functionally complete:

- compare behavior against the production copy
- tune speed endpoints
- tune widget cadence factors
- tune motion-rate behavior, especially for `gauge`
- decide whether any widget needs intentional jitter or irregularity

At this point, smoke testing and visual comparison become more useful than line-by-line code comparison.

## Rewrite Principles

For this less-constrained rebuild, prefer:

- replacing over adapting
- deleting over bridging
- a coherent end state over temporary compatibility layers

Avoid:

- preserving old timing semantics just because they already exist
- keeping parallel timing systems alive longer than necessary
- introducing adapters whose only purpose is to support transitional code

## Role Of The Production Copy

The separate runnable production copy should be treated as:

- the safety net
- the visual/behavioral comparison point
- a source of examples when behavior must be checked

That means this repository can tolerate:

- temporarily broken runs
- temporarily incomplete widget family conversions
- larger, more coherent timing changes in fewer steps

## Suggested Immediate Next Action

The next useful design action is to tighten this plan into explicit implementation tasks:

1. create the new timing module
2. define the new runtime/widget timing contract
3. choose `now` + `dt` as the update signature
4. list the old timing code that will be deleted
5. pick the first family to convert

Recommendation:

- start with the new timing module and contract definition
- then rewrite `TextWidgets` first, because removing text burst timing will simplify the rest of the system
