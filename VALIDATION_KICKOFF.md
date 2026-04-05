# Validation Kickoff for a Replacement Vertical-Video System

This repo already has the beginning of a useful **compile/render + preview-QA** story. It does **not** yet have a serious semantic-validation subsystem for StudyShorts-style math/physics scenes.

This document records:
1. what exists now,
2. where the gaps are,
3. what a replacement subsystem should validate,
4. the initial scaffold added in this kickoff.

---

## 1. Current audit: what exists now

### Existing compile / structural validation

Primary file:
- `fast_backend/app/services/llm_service.py`

What it already does well:
- validates generated code structure (`GeneratedScene`, `construct`, `manim` import)
- catches syntax and malformed keyword patterns
- emits a structured validation payload via `fast_backend/app/services/validation_report.py`
- runs static layout-risk heuristics for portrait scenes, including:
  - anchor overlap risk
  - offscreen coordinate risk
  - large-text crowding risk
  - text-density crowding risk
  - graph vertical stack crowding risk
  - graph label collision risk
  - legend/plot overlap risk
  - below-axes annotation overflow risk
  - formula transform/key-map complexity risks

Relevant tests:
- `fast_backend/tests/test_llm_validation.py`

### Existing quality / retry guidance

Primary files:
- `fast_backend/app/services/retry_policy.py`
- `fast_backend/app/services/llm_service.py`

What exists:
- preview QA failures are encoded into parseable retry signals
- subsequent generations receive stricter simplification/layout guidance
- some family-specific risk detection already exists in `analyze_quality_risks(...)`, including:
  - formula uses `Text` instead of `MathTex`
  - horizontal formula layout in portrait mode
  - weak equation alignment
  - disconnected graph annotation
  - portrait graph undercomposition
  - projectile marker off trajectory
  - detached/misaligned physics vectors

This is useful, but still mostly **prompt/code heuristic guidance**, not a validator with a contract and measurable pass/fail semantics.

### Existing preview QA

Primary file:
- `fast_backend/app/services/preview_qa_service.py`

What exists:
- low-quality preview render
- sampled frames
- frame heuristics for:
  - border crowding
  - top/bottom empty imbalance
  - dense lower horizontal label bands

Relevant tests:
- `fast_backend/tests/test_preview_qa_heuristics.py`

This is valuable for vertical-video acceptability, but it is still **generic frame hygiene**, not scene-truth verification.

### Existing benchmark helper

Primary files:
- `fast_backend/app/services/robustness_benchmark.py`
- `fast_backend/tools/run_robustness_benchmark.py`
- `fast_backend/tests/test_robustness_benchmark_cases.py`

What exists:
- four representative benchmark families:
  - `graph_formula`
  - `formula_only`
  - `graph_explanation`
  - `physics_diagram`
- helper runner for code generation + compile validation + optional preview QA

Main limitation:
- benchmark results currently answer mostly: **did it compile, and did preview frames look non-crowded?**
- they do **not** yet answer: **was the graph mathematically right, was the derivation equivalent, were the vectors attached to the right object, was the scene semantically faithful?**

---

## 2. Main gaps

The current system is strong at avoiding obvious broken code and obvious visual crowding, but weak at validating the meaning of the scene.

### Missing capabilities

#### A. Contract-based semantic truth
The generator should emit a machine-checkable scene contract, not just code.

Examples:
- Graph scene contract:
  - function/expression
  - axis ranges
  - sample points that must lie on the curve
  - required labels/annotations
- Formula scene contract:
  - input expression
  - expected intermediate steps
  - canonical final form
  - allowed transform style constraints
- Physics scene contract:
  - motion/diagram type
  - trajectory equation or sampled path
  - object anchor ids
  - vector anchors and expected relationships

Without a contract, semantic QA is forced to guess from pixels or generated code.

#### B. Scene manifest / instrumentation
A serious validator needs a lightweight manifest from the renderer, such as:
- measured aspect ratio
- text block count
- named anchors / object ids
- plotted sample coordinates
- equation strings per step
- marker coordinates
- vector start/end anchors

This can be generated before or during render from the scene graph.

#### C. Benchmark scoring beyond compile/render
Benchmarks should score multiple dimensions separately:
- compile correctness
- visual acceptability in 9:16
- semantic correctness
- pedagogical compactness
- repair stability across retries

#### D. Family-specific failure codes
Replacement-quality validation should emit stable issue codes such as:
- `graph_sample_mismatch`
- `graph_required_annotation_missing`
- `formula_final_form_mismatch`
- `formula_duplicate_consecutive_step`
- `physics_vector_anchor_mismatch`
- `projectile_marker_off_trajectory`
- `vertical_text_block_overload`

These are much more useful than generic "QA failed" messages.

---

## 3. Proposed replacement subsystem

### Architecture

Use a **three-layer validation stack**:

#### Layer 1 — Code/scene-graph validation
Purpose: reject broken or obviously unsafe scene programs.

Checks:
- syntax/AST validity
- required scene structure
- disallowed asset dependencies
- dangerous or unsupported Manim patterns
- static crowding/layout heuristics

This layer mostly already exists.

#### Layer 2 — Semantic contract validation
Purpose: verify that the scene content is mathematically/physically faithful.

Checks by family:

##### Graph scenes
- expression parses safely
- sample points satisfy the declared function
- axis ranges are sane and monotonic
- required annotation tokens exist
- number of labels near the plot stays below a vertical-video threshold

##### Formula scenes
- derivation steps are present and ordered
- no duplicate consecutive steps
- final step matches canonical final form
- steps are MathTex-friendly, not prose disguised as equations
- step count stays compact enough for a short vertical video

##### Physics scenes
- declared vectors that should share one anchor actually do
- marker lies on declared trajectory
- trajectory sample points match the stated law/equation
- vector/marker naming stays consistent across the manifest

#### Layer 3 — Preview/video acceptability validation
Purpose: ensure the scene still works as a short-form portrait video.

Checks:
- border crowding
- empty-band imbalance
- dense lower label band
- total simultaneous text blocks
- safe-area occupancy
- time-windowed density spikes (future)
- subtitle/overlay collision zones (future)

---

## 4. What was added in this kickoff

### New scaffold
Added:
- `fast_backend/app/services/semantic_validation.py`
- `fast_backend/tests/test_semantic_validation.py`

The scaffold introduces deterministic, contract-driven validators for:
- vertical layout metadata
- graph semantic sample checking
- formula step/final-form validation
- physics anchor/trajectory consistency

### What it already validates

#### Vertical
- explicit portrait aspect ratio expectation
- maximum simultaneous text block budget

#### Graph
- increasing x/y ranges
- at least 3 sample points
- declared sample points satisfy the declared expression
- required annotations can be checked against measured metadata

#### Formula
- derivation steps exist
- step count can be capped for Shorts
- duplicate consecutive steps are flagged
- last step must match a canonical final form

#### Physics
- vectors expected to share an anchor are checked
- marker point can be tested against a declared trajectory expression
- sampled trajectory points can also be checked

### Why this scaffold matters

This moves the repo toward a system where semantic correctness is a first-class artifact instead of a side-effect of prompt heuristics.

---

## 5. Recommended next step

Implement **scene manifest emission** from generated scenes so these validators can run on real measured data instead of hand-authored contracts.

Concretely:
1. emit a JSON manifest per generated scene with named objects, anchors, formula steps, and sampled graph/trajectory coordinates;
2. connect `semantic_validation.py` into benchmark runs;
3. expand benchmark cases from 4 broad prompts into a curated corpus with expected contracts and scoring thresholds;
4. only then add optional vision-model checks for final rendered frames/video.

The key opinion here: **semantic validation should be contract-first, vision-assisted second**. Pixels alone are too weak and too noisy for replacement-quality math/physics QA.
