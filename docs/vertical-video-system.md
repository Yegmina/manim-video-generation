# Vertical Video Generation System: Kickoff Design

## Goal

Build a **separate, deterministic 9:16 video-generation subsystem** for StudyShorts-style math and physics explainers inside this repo, without mutating StudyShorts itself and without relying only on prompt tweaks.

This subsystem is meant to sit alongside the current generic `text2video` pipeline, not replace it.

## Repo Audit

### Current structure

- `manim_video_generator.py`
  - low-level Manim render wrapper
- `fast_backend/app/services/llm_service.py`
  - prompt-heavy generic code generation and retry logic
- `fast_backend/app/services/video_service.py`
  - persistence + render execution
- `fast_backend/app/api/v1/endpoints/text2video.py`
  - generic prompt-to-video endpoint
- `fast_backend/app/models/video.py`
  - generic video job model

### Key observation

The existing system is optimized around:
- free-form prompt -> LLM code generation
- retry-on-failure
- compatibility fixes after generation

That is useful, but it is **not yet a strong architecture** for a deterministic family-aware vertical video engine.

## Where the new subsystem should live

Recommended home:

- `fast_backend/app/vertical_video/`

Why here:
- keeps the new architecture isolated from the current generic `services/llm_service.py`
- stays inside the backend app where future API integration is natural
- allows a dedicated domain model for vertical Shorts/Reels/TikTok-style explainers
- cleanly separates **planning/spec generation** from **render execution**

## Architectural direction

### Core principle

Instead of generating arbitrary Manim code directly from raw prompts, the vertical system should use a stricter pipeline:

1. **User intent normalization**
2. **Family classification** (`math`, `physics`, later `chemistry`, etc.)
3. **Deterministic plan assembly** into a constrained intermediate representation
4. **Family-aware scene template selection**
5. **Manim script emission from structured plan**
6. **Portrait-safe validation** before render
7. **Render execution** through the existing renderer layer

This gives us:
- deterministic outputs
- stronger style consistency
- safer portrait layout behavior
- easier testing
- smaller surface area for LLM hallucination

## Mandatory product assumptions

- Target format is always **vertical 9:16**
- Family-aware output is mandatory
- Architecture should prefer **templates + structured plans** over unconstrained code generation
- LLM usage, if kept, should be optional and bounded to specific subproblems like wording or enrichment

## Proposed subsystem boundaries

### New package

`fast_backend/app/vertical_video/`

Planned responsibilities:

- `models.py`
  - dataclasses/enums for the intermediate representation
- `family_policy.py`
  - deterministic rules per content family
- `deterministic_planner.py`
  - converts a structured request into a constrained plan
- `manim_builder.py`
  - emits portrait-safe Manim code from the plan
- `service.py`
  - orchestration entrypoint for future API/background integration

## Initial domain model

### Input

A future request object should contain explicit fields, not just one prompt:

- `topic`
- `family` (`math` / `physics`)
- `goal`
- `tone`
- `audience_age`
- `duration_bucket`
- `visual_style`
- `constraints`

### Internal plan

The intermediate representation should contain:

- `render_profile`
  - portrait dimensions, margins, typography limits
- `family`
- `template_id`
- `hook_text`
- `beats[]`
  - ordered explain steps
- `safety_rules[]`
- `visual_rules[]`
- `final_cta`

### Output

Generated Manim should be:
- portrait-configured at the top of the file
- based on a selected scene family/template
- emitted from code, not inferred ad hoc during render time

## Family-aware policy examples

### Math family

Prefer:
- equation-first composition
- derivation stacks
- graph-with-caption layouts
- short symbolic steps

Avoid:
- decorative clutter
- excessive prose blocks
- long horizontal formulas spanning the frame width

### Physics family

Prefer:
- quantity/state progression
- object + vector relationships
- labeled motion diagrams
- compact graphs tied directly to phenomena

Avoid:
- detached annotations
- hard-coded vector anchors inconsistent with motion state
- overly dense multi-panel layouts in portrait mode

## Determinism strategy

The first version should be deterministic by default:

- template choice from family + goal + duration bucket
- beat count bounded by duration bucket
- typography limits encoded in render profile
- family-specific rules enforced before code emission
- no random placements
- no free-form direct LLM code generation in the core planner

Later, optional LLM helpers can enrich text copy only after the structural plan is fixed.

## Integration plan

### Phase 0 (this kickoff)

- create the new package
- define plan models
- implement deterministic planner
- scaffold Manim emitter
- add focused unit tests

### Phase 1

- add `VerticalVideoService`
- wire into existing `video_service` render path
- add a new API endpoint such as `/api/v1/vertical-video/plan` and `/api/v1/vertical-video/render`

### Phase 2

- add scene templates per family
- add portrait-specific QA rules for final plans before render
- add request persistence for structured vertical jobs

### Phase 3

- allow bounded LLM enrichment for hook/caption phrasing only
- add more families and template variants

## First implementation decision

For this repo, the safest kickoff is:

- keep the current generic pipeline unchanged
- introduce a **parallel vertical subsystem** under `fast_backend/app/vertical_video/`
- make the first version able to:
  - accept a structured request
  - select a family policy and template
  - create a deterministic plan
  - emit a portrait-safe starter Manim script

## Next recommended step

Implement a first end-to-end happy path for two canonical templates:

- `math_derivation_stack`
- `physics_motion_explainer`

Then expose a plan-preview API before connecting it to full render jobs.
