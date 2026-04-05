from __future__ import annotations

from typing import List

from .family_policy import get_family_policy
from .models import DurationBucket, VerticalVideoPlan, VerticalVideoRequest, VisualBeat, RenderProfile


class DeterministicVerticalPlanner:
    """Builds a constrained portrait-video plan from structured input."""

    def __init__(self, render_profile: RenderProfile | None = None):
        self.render_profile = render_profile or RenderProfile()

    def build_plan(self, request: VerticalVideoRequest) -> VerticalVideoPlan:
        policy = get_family_policy(request.family)
        template_id = policy.select_template(request)
        beats = self._build_beats(request=request, template_id=template_id)

        return VerticalVideoPlan(
            request=request,
            render_profile=self.render_profile,
            template_id=template_id,
            hook_text=self._build_hook_text(request),
            beats=beats,
            final_cta=self._build_final_cta(request),
            safety_rules=list(policy.safety_rules),
            visual_rules=list(policy.visual_rules),
            metadata={
                "deterministic": True,
                "family": request.family.value,
                "duration_bucket": request.duration_bucket.value,
                "beat_count": len(beats),
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
        max_beats = {
            DurationBucket.SHORT: 3,
            DurationBucket.MEDIUM: 4,
            DurationBucket.LONG: 5,
        }[request.duration_bucket]

        base_points = [point.strip() for point in request.supporting_points if point.strip()]
        if not base_points:
            base_points = [
                f"Introduce {request.topic}",
                f"Explain the main idea behind {request.goal}",
                "Land the key takeaway clearly",
            ]

        selected_points = base_points[:max_beats]
        beats: List[VisualBeat] = []
        for index, point in enumerate(selected_points, start=1):
            beats.append(
                VisualBeat(
                    key=f"beat_{index}",
                    narration=point,
                    visual=self._build_visual_description(template_id=template_id, point=point, index=index),
                    emphasis=self._build_emphasis(template_id=template_id, index=index),
                    duration_seconds=2.2 if request.duration_bucket == DurationBucket.SHORT else 2.8,
                )
            )
        return beats

    def _build_visual_description(self, template_id: str, point: str, index: int) -> str:
        if template_id == "math_derivation_stack":
            return f"Portrait equation stack step {index}: {point}"
        if template_id == "math_graph_explainer":
            return f"Portrait graph explainer step {index}: {point}"
        return f"Portrait physics diagram step {index}: {point}"

    def _build_emphasis(self, template_id: str, index: int) -> str:
        if template_id.startswith("math"):
            return "equation" if index > 1 else "question"
        return "motion" if index > 1 else "setup"
