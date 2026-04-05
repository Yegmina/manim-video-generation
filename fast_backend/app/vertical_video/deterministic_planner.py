from __future__ import annotations

from typing import List

from app.services.semantic_validation import (
    FormulaSemanticContract,
    GraphSemanticContract,
    PhysicsSemanticContract,
    PhysicsVector,
    PointSample,
    SceneSemanticContract,
)

from .family_policy import get_family_policy
from .models import (
    DerivationSpec,
    DerivationStep,
    DurationBucket,
    GraphSample,
    GraphSpec,
    KinematicsSpec,
    MotionPhase,
    RenderProfile,
    SceneSpec,
    VerticalVideoPlan,
    VerticalVideoRequest,
    VisualBeat,
)


class DeterministicVerticalPlanner:
    """Builds a constrained portrait-video plan from structured input."""

    def __init__(self, render_profile: RenderProfile | None = None):
        self.render_profile = render_profile or RenderProfile()

    def build_plan(self, request: VerticalVideoRequest) -> VerticalVideoPlan:
        policy = get_family_policy(request.family)
        template_id = policy.select_template(request)
        beats = self._build_beats(request=request, template_id=template_id)
        scene_spec = self._build_scene_spec(request=request, template_id=template_id)
        semantic_contract = self._build_semantic_contract(request=request, template_id=template_id)

        return VerticalVideoPlan(
            request=request,
            render_profile=self.render_profile,
            template_id=template_id,
            hook_text=self._build_hook_text(request),
            beats=beats,
            final_cta=self._build_final_cta(request),
            safety_rules=list(policy.safety_rules),
            visual_rules=list(policy.visual_rules),
            scene_spec=scene_spec,
            metadata={
                "deterministic": True,
                "family": request.family.value,
                "duration_bucket": request.duration_bucket.value,
                "beat_count": len(beats),
                "semantic_contract": semantic_contract,
            },
        )

    def _build_hook_text(self, request: VerticalVideoRequest) -> str:
        if request.family.value == "math":
            return f"{request.topic}: the clean version in under a minute."
        return f"{request.topic}: see the physics step by step."

    def _build_final_cta(self, request: VerticalVideoRequest) -> str:
        if request.family.value == "math":
            return "Pause here and try the next step yourself."
        return "Pause here and predict the next state before replaying."

    def _build_beats(self, request: VerticalVideoRequest, template_id: str) -> List[VisualBeat]:
        if template_id == "math_derivation_stack":
            derivation = self._resolve_derivation(request)
            beats = [
                VisualBeat(
                    key=f"derivation_{index}",
                    narration=step.text,
                    visual=f"Portrait derivation card {index}: {step.text}",
                    emphasis=step.highlight or "equation",
                    duration_seconds=1.8,
                )
                for index, step in enumerate(derivation.steps, start=1)
            ]
            return beats[: self._max_beats(request.duration_bucket)]

        if template_id == "math_graph_explainer":
            graph = self._resolve_graph(request)
            samples = list(graph.samples) or [
                GraphSample(graph.x_range[0], self._graph_y(graph.expression, graph.x_range[0]), "left"),
                GraphSample(0.0, self._graph_y(graph.expression, 0.0), "center"),
                GraphSample(graph.x_range[1], self._graph_y(graph.expression, graph.x_range[1]), "right"),
            ]
            return [
                VisualBeat(
                    key=f"graph_{index}",
                    narration=f"At x = {sample.x:g}, y = {sample.y:g}.",
                    visual=f"Portrait graph marker {sample.label or index}",
                    emphasis="graph",
                    duration_seconds=1.8,
                )
                for index, sample in enumerate(samples[: self._max_beats(request.duration_bucket)], start=1)
            ]

        kinematics = self._resolve_kinematics(request)
        phases = list(kinematics.phases)[: self._max_beats(request.duration_bucket)]
        return [
            VisualBeat(
                key=f"motion_{index}",
                narration=(
                    f"{phase.label}: vx={phase.velocity_x:g}, vy={phase.velocity_y:g}"
                ),
                visual=f"Portrait motion state {index}: {phase.label}",
                emphasis="motion",
                duration_seconds=max(1.2, phase.duration_seconds),
            )
            for index, phase in enumerate(phases, start=1)
        ]

    def _build_scene_spec(self, request: VerticalVideoRequest, template_id: str) -> SceneSpec:
        if template_id == "math_derivation_stack":
            derivation = self._resolve_derivation(request)
            return SceneSpec(
                scene_id="math_derivation_scene",
                family="formula",
                template_id=template_id,
                payload={
                    "topic": request.topic,
                    "hook_text": self._build_hook_text(request),
                    "steps": [step.text for step in derivation.steps],
                    "highlights": [step.highlight or "" for step in derivation.steps],
                    "final_expression": derivation.final_expression,
                    "cta": self._build_final_cta(request),
                },
            )

        if template_id == "math_graph_explainer":
            graph = self._resolve_graph(request)
            return SceneSpec(
                scene_id="math_graph_scene",
                family="graph",
                template_id=template_id,
                payload={
                    "topic": request.topic,
                    "hook_text": self._build_hook_text(request),
                    "expression": graph.expression,
                    "x_range": list(graph.x_range),
                    "y_range": list(graph.y_range),
                    "samples": [sample.__dict__ for sample in graph.samples],
                    "highlight_label": graph.highlight_label,
                    "cta": self._build_final_cta(request),
                },
            )

        kinematics = self._resolve_kinematics(request)
        return SceneSpec(
            scene_id="physics_motion_scene",
            family="physics",
            template_id=template_id,
            payload={
                "topic": request.topic,
                "hook_text": self._build_hook_text(request),
                "equation_text": kinematics.equation_text,
                "trajectory_expression": kinematics.trajectory_expression,
                "x_range": list(kinematics.x_range),
                "y_range": list(kinematics.y_range),
                "marker_x": kinematics.marker_x,
                "phases": [phase.__dict__ for phase in kinematics.phases],
                "cta": self._build_final_cta(request),
            },
        )

    def _build_semantic_contract(self, request: VerticalVideoRequest, template_id: str) -> dict:
        if template_id == "math_derivation_stack":
            derivation = self._resolve_derivation(request)
            contract = SceneSemanticContract(
                scene_id="math-derivation",
                family="formula",
                formula=FormulaSemanticContract(
                    input_latex=derivation.input_expression,
                    expected_steps=[step.text for step in derivation.steps],
                    canonical_final_latex=derivation.final_expression,
                ),
            )
            return self._contract_to_dict(contract)

        if template_id == "math_graph_explainer":
            graph = self._resolve_graph(request)
            contract = SceneSemanticContract(
                scene_id="math-graph",
                family="graph",
                graph=GraphSemanticContract(
                    expression=graph.expression,
                    x_range=graph.x_range,
                    y_range=graph.y_range,
                    sample_points=[PointSample(sample.x, sample.y) for sample in graph.samples],
                    required_annotations=[graph.highlight_label],
                ),
            )
            return self._contract_to_dict(contract)

        kinematics = self._resolve_kinematics(request)
        marker_y = self._graph_y(kinematics.trajectory_expression, kinematics.marker_x)
        contract = SceneSemanticContract(
            scene_id="physics-motion",
            family="physics",
            physics=PhysicsSemanticContract(
                motion_type="projectile",
                trajectory_expression=kinematics.trajectory_expression,
                marker_point=PointSample(kinematics.marker_x, marker_y),
                vectors=[
                    PhysicsVector(name="velocity_x", anchor_id="projectile-dot"),
                    PhysicsVector(name="velocity_y", anchor_id="projectile-dot"),
                ],
                vectors_expected_same_anchor=["velocity_x", "velocity_y"],
            ),
        )
        return self._contract_to_dict(contract)

    def _contract_to_dict(self, contract: SceneSemanticContract) -> dict:
        return {
            "scene_id": contract.scene_id,
            "family": contract.family,
            "vertical": {
                "aspect_ratio": contract.vertical.aspect_ratio,
                "safe_margin_x": contract.vertical.safe_margin_x,
                "safe_margin_y": contract.vertical.safe_margin_y,
                "max_simultaneous_text_blocks": contract.vertical.max_simultaneous_text_blocks,
                "require_portrait": contract.vertical.require_portrait,
            },
            "formula": (
                None
                if contract.formula is None
                else {
                    "input_latex": contract.formula.input_latex,
                    "expected_steps": list(contract.formula.expected_steps),
                    "canonical_final_latex": contract.formula.canonical_final_latex,
                }
            ),
            "graph": (
                None
                if contract.graph is None
                else {
                    "expression": contract.graph.expression,
                    "x_range": list(contract.graph.x_range),
                    "y_range": list(contract.graph.y_range),
                    "sample_points": [sample.__dict__ for sample in contract.graph.sample_points],
                    "required_annotations": list(contract.graph.required_annotations),
                }
            ),
            "physics": (
                None
                if contract.physics is None
                else {
                    "motion_type": contract.physics.motion_type,
                    "trajectory_expression": contract.physics.trajectory_expression,
                    "marker_point": (
                        None
                        if contract.physics.marker_point is None
                        else contract.physics.marker_point.__dict__
                    ),
                    "vectors": [vector.__dict__ for vector in contract.physics.vectors],
                    "vectors_expected_same_anchor": list(contract.physics.vectors_expected_same_anchor),
                }
            ),
        }

    def _resolve_derivation(self, request: VerticalVideoRequest) -> DerivationSpec:
        if request.derivation is not None:
            return request.derivation

        payload = request.structured_payload.get("derivation") if request.structured_payload else None
        if payload:
            return DerivationSpec(
                input_expression=payload["input_expression"],
                steps=[
                    step if isinstance(step, DerivationStep) else DerivationStep(**step)
                    for step in payload["steps"]
                ],
                final_expression=payload["final_expression"],
            )

        steps = request.supporting_points or [
            "Start from the original expression",
            "Expand the middle term carefully",
            "Combine like terms",
        ]
        return DerivationSpec(
            input_expression=request.topic,
            steps=[DerivationStep(step) for step in steps],
            final_expression=steps[-1],
        )

    def _resolve_graph(self, request: VerticalVideoRequest) -> GraphSpec:
        if request.graph is not None:
            return request.graph

        payload = request.structured_payload.get("graph") if request.structured_payload else None
        if payload:
            return GraphSpec(
                expression=payload["expression"],
                x_range=tuple(payload.get("x_range", (-2.0, 2.0))),
                y_range=tuple(payload.get("y_range", (-1.0, 4.0))),
                samples=[
                    sample if isinstance(sample, GraphSample) else GraphSample(**sample)
                    for sample in payload.get("samples", [])
                ],
                highlight_label=payload.get("highlight_label", "shape"),
            )

        expression = "x**2"
        samples = tuple(
            GraphSample(x, self._graph_y(expression, x), label)
            for x, label in [(-1.0, "left"), (0.0, "vertex"), (1.0, "right")]
        )
        return GraphSpec(expression=expression, samples=samples, highlight_label="vertex")

    def _resolve_kinematics(self, request: VerticalVideoRequest) -> KinematicsSpec:
        if request.kinematics is not None:
            return request.kinematics

        payload = request.structured_payload.get("kinematics") if request.structured_payload else None
        if payload:
            return KinematicsSpec(
                motion_type=payload.get("motion_type", "projectile"),
                equation_text=payload.get("equation_text", "y = x - 0.12x^2"),
                trajectory_expression=payload.get("trajectory_expression", "x - 0.12*x**2"),
                x_range=tuple(payload.get("x_range", (0.0, 7.0))),
                y_range=tuple(payload.get("y_range", (0.0, 3.0))),
                marker_x=payload.get("marker_x", 3.5),
                phases=[
                    phase if isinstance(phase, MotionPhase) else MotionPhase(**phase)
                    for phase in payload.get("phases", [])
                ],
            )

        return KinematicsSpec(
            phases=(
                MotionPhase("Launch", 1.0, 3.0, 2.6),
                MotionPhase("Mid-flight", 1.0, 3.0, 0.8),
                MotionPhase("Falling", 1.0, 3.0, -1.4),
            )
        )

    def _max_beats(self, bucket: DurationBucket) -> int:
        return {
            DurationBucket.SHORT: 3,
            DurationBucket.MEDIUM: 4,
            DurationBucket.LONG: 5,
        }[bucket]

    def _graph_y(self, expression: str, x: float) -> float:
        return float(eval(expression, {"__builtins__": {}}, {"x": x}))
