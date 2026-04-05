from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import ContentFamily, DurationBucket, VerticalVideoRequest


@dataclass(frozen=True)
class FamilyPolicy:
    family: ContentFamily
    default_template: str
    allowed_templates: List[str]
    safety_rules: List[str]
    visual_rules: List[str]

    def select_template(self, request: VerticalVideoRequest) -> str:
        if self.family == ContentFamily.MATH:
            if request.duration_bucket == DurationBucket.LONG:
                return "math_graph_explainer"
            return "math_derivation_stack"
        if self.family == ContentFamily.PHYSICS:
            return "physics_motion_explainer"
        return self.default_template


POLICIES = {
    ContentFamily.MATH: FamilyPolicy(
        family=ContentFamily.MATH,
        default_template="math_derivation_stack",
        allowed_templates=["math_derivation_stack", "math_graph_explainer"],
        safety_rules=[
            "Always render in vertical 9:16.",
            "Prefer MathTex for equations and symbols.",
            "Do not build wide horizontal equation chains.",
            "Keep at most one major idea on screen at a time.",
        ],
        visual_rules=[
            "Use vertically stacked derivation steps.",
            "Keep strong side margins for portrait readability.",
            "Avoid decorative boxes unless explicitly requested.",
        ],
    ),
    ContentFamily.PHYSICS: FamilyPolicy(
        family=ContentFamily.PHYSICS,
        default_template="physics_motion_explainer",
        allowed_templates=["physics_motion_explainer"],
        safety_rules=[
            "Always render in vertical 9:16.",
            "Anchor vectors and labels to the same physical object/state.",
            "Avoid detached annotations that float away from the phenomenon.",
            "Prefer one phenomenon per scene flow.",
        ],
        visual_rules=[
            "Use compact labeled diagrams.",
            "Show cause-and-effect progression across beats.",
            "Keep graph usage secondary to the main phenomenon unless graph is the lesson.",
        ],
    ),
}


def get_family_policy(family: ContentFamily) -> FamilyPolicy:
    return POLICIES[family]
