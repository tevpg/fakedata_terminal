# Timing TODO

This file captures the current timing-design direction for FakeData Terminal. It is intended to evolve as the design and implementation plan become more concrete.

## Goals


Functional timing goals:

- widgets at the same `speed` setting may still animate at different real-world rates
- those differences should be intentional and centrally understandable
- true time-based events should be modeled explicitly
- the `speed` scale remains `1..100`
- the timing model should ideally be clock-based rather than loop-count-based

The functional goals are shaped by these non-functional goals:

- maintainability
- reliability
- consistency
- easier reasoning about widget behavior
- easier future refactoring and widget additions
- able to run on newer or older hardware
- able to run on linux or Windows (some functions may not be available in Windows)


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

Current provisional shape:

- `speed 1` = about 1 animation step per second for a widget with cadence factor `1.0`
- `speed 100` = about 50 animation iterations per second for a widget with cadence factor `1.0`
- the speed curve should be linear in the first implementation unless there is a strong reason to revise it

These values are currently the intended first-pass defaults.

### 4. Per-Widget Relative Rate Factors

Widgets animated at the same speed may still need different real-world cadences.

That should be defined intentionally, either:

- by constants near the top of each widget module, or
- in a centralized table

Current provisional decision:

- use a centralized table in `widgets.yaml`

The intended framing is:

- there is some shared maximum or reference cadence
- each widget uses a proportion of that cadence

So the factors would normally be in the range `(0, 1]`.

Example factors:

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

Current provisional thinking:

- `gauge` definitely belongs in this category
- `sweep` may also be a candidate
- most other widgets should remain cadence-driven for now

The implementation of `speed` meaning rotation speed in the gauge widget can be deferred, as long as the timing model supports it.

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

Some design questions now have provisional answers. The list below focuses on what still needs to be decided before or during implementation.

### Provisional Decisions Already Made

- `speed 1` should mean about 1 second per animation iteration for a widget with cadence factor `1.0`
- `speed 100` should mean about 50 iterations per second for a widget with cadence factor `1.0`
- the speed curve should be linear for the first implementation unless there is a strong reason to revise it
- widget cadence factors should live in `widgets.yaml`
- hardware-aware speed capping is a later enhancement, not part of the first rewrite
- text timing may become fully regular for now; jitter can be reconsidered later
- `gauge` is currently the only widget that clearly needs semantic motion units
- `sweep` is a possible later candidate for semantic motion units
- timing values and factors should be documented as tunable defaults
- all text widgets should share the same cadence model
- cycle timing should use a fixed default first, with scene configurability as a possible later enhancement
- random-direction rerolls should stay wall-clock-based
- textwall forward/pause/reverse behavior should use the same general direction-modifier and reroll model as other `direction`-aware widgets
- the rewrite should prioritize simpler code over exact behavioral matching
- provisional timing values chosen by Codex are acceptable if documented
- `dt` should be clamped at `0.5s`
- `sweep` should remain cadence-driven in the first rewrite
- pause/resume should use the simpler monotonic/deadline model:
  shift deadlines forward by the paused duration and reset per-area update timestamps so `dt` does not jump
- `cycle_next_change` should remain one absolute timestamp per region, at least initially
- direction-aware widgets should share one reroll helper/model with per-widget settings in `widgets.yaml`
- textwall should use that same general reroll model rather than its own separate forward/pause/reverse timing scheme
- image colour cycling should remain tied to image/frame replacement, as it is now
- metrics/readouts refresh timing may be simplified even if that changes the exact current `COUNT` behavior

### Remaining Open Questions

- What exact per-widget direction-reroll settings should be the first defaults in `widgets.yaml`?
- Should metrics/readouts refresh continue using a dedicated deadline, or should it be folded into ordinary cadence for some modes?
- Does the current image/frame transition model need any redesign beyond preserving its colour-change-on-frame-replacement behavior?

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
- one central table of widget cadence factors in `widgets.yaml`
- explicit deadline fields for real timed events
- semantic motion rates for widgets that need them, starting with `gauge`
- removal of the current text burst timing model

Decisions still to make:

- initial widget cadence factors
- initial per-widget direction-reroll defaults in `widgets.yaml`
- exact handling of metrics/readouts refresh timing
- whether image/frame transition timing needs any redesign beyond the current frame-replacement-driven model

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

Implementation note:

- timing values and cadence factors should be documented as tunable defaults
- those defaults should live in `widgets.yaml`

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
- direction-aware widgets should share one reroll helper/model, with per-widget values from `widgets.yaml`

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

Specific note:

- textwall should stop using its own unique forward/pause/reverse timing concept and instead participate in the same general direction-reroll model as other `direction`-aware widgets

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

Possible extension:

- consider whether `sweep` should also be expressed in semantic motion terms
- this is deferred until after `gauge`

Implementation decision:

- express `gauge` motion internally in RPM

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

## Deferred Items

These items have come up during design discussion but are intentionally deferred so they do not complicate the first timing rewrite.

- hardware-aware speed capping and startup warnings for slow machines
- reintroducing jitter or irregular cadence for text widgets
- semantic motion for `sweep`
- scene-configurable cycle timing
- deciding whether any widgets besides `gauge` should later use semantic motion units
- tuning the exact widget cadence factors after the framework is in place
- any deeper redesign of image timing beyond the current frame-replacement-driven colour changes

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

## Questions For Design Input

This section is intended for upfront design questions that can be answered before the main timing rewrite begins.

The goal is to reduce interruptions once implementation starts.

Where exact answers are not yet known, "provisional default chosen by Codex" is an acceptable answer.

### A. Speed Scale

1. What should `speed 1` mean for a widget with cadence factor `1.0`?

Possible ways to answer:

- approximately 1 update per second
- slower than that
- faster than that

2. What should `speed 100` mean for a widget with cadence factor `1.0`?

Possible ways to answer:

- a target updates-per-second value
- a minimum interval in seconds or milliseconds
- "as fast as is still visually meaningful"

3. Should the speed curve feel:

- linear
- exponential
- logarithmic / perceptual
- similar to the current feel, but cleaner

4. Should speed `100` be treated as:

- a real finite maximum cadence
- effectively unthrottled

Recommendation:

- use a real finite maximum cadence

Reason:

- easier reasoning
- better consistency
- simpler tuning

### B. Cadence Factors

5. Should cadence factors be documented in one central table first?

Decision:

- yes

6. Should the default assumption be that all widgets start at `1.0` and are tuned downward only where needed?

Decision:

- yes

7. Are cadence factors intended to be:

- user-facing tunables later
- internal implementation constants only

Decision:

- internal documented tunables for now in a widgets.yaml

### C. Motion Semantics

8. Should `gauge` be the only widget initially using semantic motion units, such as rotations-per-second?

Decision:

- yes

9. For `gauge`, should speed correspond more naturally to:

- rotations per second
- rotations per minute
- some other angular-rate measure

Provisional decision, for comment:

- Don't care as long as it's consistent, based on speed.  In code, I would think RPM is a reasonable measure, if you need one

10. Should any other widgets be treated similarly, where speed should describe semantic motion rather than simple update cadence?

Candidates to consider:

- `scope` - no
- `tunnel` - no
- `sweep` - yes
- `life` - no

### D. Text Behavior

11. Confirm that the old burst timing model for text should be removed entirely.

Decision:

- yes

12. After burst timing is removed, should text movement be:

- fully regular
- slightly jittered

Decision:

- fully regular first, without closing the door on jitter

13. Should all text widgets (`text`, `text_scant`, `text_wide`, `text_spew`) share the same cadence model, differing only in rendering/update behavior?

Decision:

- yes.  They would all receive their cadence from speed, direction, and the per-widget cadence tuning factor

### E. Timed Events

14. Should the following remain explicit wall-clock deadlines?

- `exit_at`
- `cycle_next_change`
- showcase/demo next-scene changes
- glitch timers
- textwall reverse/pause deadlines
- gauge spin-direction re-roll deadlines
- metrics/readouts refresh deadlines
- image colour-cycle deadlines, if they remain time-based

Decision for comment:

- yes but also note:  the direction changes in textwall , the gauge direction changes, and the direction changes for other widgets that observe the `direction=random` modifier can presumably all follow the same model, with probabilities and timings in `widgets.yaml`. This is a bit of a departure for textwall, but likely good enough, and config management should be simpler if they all use the same model. Thus, textwall would take a `direction` modifier in the same general sense as `scope`, etc.

15. Should cycle timing eventually be:

- a fixed default duration
- speed-influenced
- scene-configurable

Decision:

- fixed default first, scene-configurable later if needed

16. Should random-direction re-roll timing stay:

- wall-clock-based
- tied to widget cadence

Decision:

- wall-clock-based

### F. Runtime Contract

17. Confirm the new update contract:

- `ensure(area, rows, width, role, now)`
- `update(area, rows, width, role, now, dt)`
- `render(area, rows, y, x, width, role)`

Comment:

- I don't have an informed opinion on this.

18. Should `dt` be:

- actual elapsed time since the widget's last update
- clamped to a maximum to avoid giant jumps after stalls

Decision:

- actual elapsed time, but clamped to a reasonable maximum

Reason:

- avoids huge jumps after resize stalls, terminal pauses, or debugger stops

19. Should each area maintain its own previous-update timestamp for `dt` calculation?

Decision:

- yes, but I don't think I care that much

### G. Pause / Resume

20. On pause/resume, should semantic motion pick up exactly where it would have been if time had stopped?

Decision:

- this is my preference, yes

21. Should pause continue to work by shifting deadlines forward, or should paused duration be subtracted from a monotonic timing model?

Decision:

- whatever simplifies the runtime, this is not a mission-critical feature

### H. Hardware / Performance

22. Should hardware-aware speed capping be deferred completely for now?

Decision:

- yes

23. Should the rewrite initially prioritize correctness and clarity over matching the previous maximum achievable apparent speed?

Decision:

- yes

### I. Tuning Workflow

24. Is it acceptable for Codex to choose provisional timing values and cadence factors, document them, and treat them as tunable defaults rather than final decisions?

Decision:

- yes, preferably in widgets.yaml

25. Should those defaults be documented directly in the timing module as code comments and also summarized in this file?

Decision:

- yes

26. When comparing the rewritten timing system to the production copy, what matters most?

Priorities, in order:

1 - simpler code over exact behavioral matching
2 - visual feel
3 - rough relative speeds between widgets
4 - identical scene pacing

### J. Optional Notes / Decisions

Use this space for your direct answers, overrides, or preferences.

- Q1 `speed 1`: 1 iteration per second
- Q2 `speed 100`: as fast as is still visually meaningful
- Q3 speed curve: linear
- Q5 cadence-factor storage: `widgets.yaml`
- Q9 `gauge` motion unit:
- Q10 other semantic-motion widgets:
- Q14/Q16 wall-clock timed events: as recommended, but also note:
  the textwall direction changes, the gauge direction changes, and the direction changes for other widgets that observe the `direction=random` modifier can presumably all follow the same model, with probabilities and timings in `widgets.yaml`. This is a bit of a departure for textwall, but likely good enough, and config management should be simpler if they all use the same model. Thus, textwall would take a `direction` modifier in the same general sense as `scope`, etc.
- Q14/Q16 cadence-based timed events:
- Q18 `dt` clamp: as recommended
- Q21 pause model:
- Q26 production-comparison priority:
- Q11 remove text burst timing:
- Q12 text jitter later?:
- Q15 cycle timing policy:
- Q20 pause/resume expectation:
- Q24 provisional defaults acceptable:

You can answer either way:

- preferred: put concise answers here in section `J. Optional Notes / Decisions`
- also acceptable: answer inline by editing sections `A` through `I`

If you answer inline in `A` through `I`, keep the question number and add your answer immediately below the question or recommendation so it is easy to fold back into the summary sections later.
