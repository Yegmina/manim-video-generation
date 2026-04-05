from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..services.semantic_validation import (
    PhysicsSemanticContract,
    PhysicsVector,
    PointSample,
    SceneSemanticContract,
)
from .models import ContentFamily, DurationBucket, KinematicsSpec, MotionPhase, VerticalVideoRequest


@dataclass(frozen=True)
class VerticalExampleSpec:
    example_id: str
    request: VerticalVideoRequest
    contract: SceneSemanticContract
    expected_template: str
    output_name: str


def builtin_vertical_examples() -> List[VerticalExampleSpec]:
    projectile_request = VerticalVideoRequest(
        topic="Projectile motion",
        family=ContentFamily.PHYSICS,
        goal="explain how horizontal and vertical velocity create a curved path",
        duration_bucket=DurationBucket.SHORT,
        constraints=[
            "portrait 9:16 only",
            "show a single projectile arc",
            "keep labels compact",
        ],
        supporting_points=[
            "Horizontal velocity keeps pushing the ball forward.",
            "Gravity changes the vertical part, so the path bends.",
            "Both arrows stay attached to the same moving object.",
        ],
        kinematics=KinematicsSpec(
            motion_type="projectile",
            equation_text="y = 0.95x - 0.09x^2",
            trajectory_expression="0.95*x - 0.09*x**2",
            x_range=(0.0, 8.0),
            y_range=(0.0, 5.0),
            marker_x=4.0,
            phases=(
                MotionPhase("Launch", 1.2, 3.8, 2.8),
                MotionPhase("Apex approach", 1.2, 3.8, 1.0),
                MotionPhase("Falling", 1.2, 3.8, -1.4),
            ),
        ),
    )
    projectile_contract = SceneSemanticContract(
        scene_id="projectile_motion_portrait_example",
        family="physics",
        measured_aspect_ratio="9:16",
        measured_text_blocks=3,
        measured_annotations=("horizontal", "vertical", "v_x", "v_y"),
        physics=PhysicsSemanticContract(
            motion_type="projectile",
            trajectory_expression="0.95*x - 0.09*x^2",
            trajectory_samples=(
                PointSample(0, 0),
                PointSample(4, 2.36),
                PointSample(8, 1.84),
            ),
            marker_point=PointSample(4, 2.36),
            vectors=(
                PhysicsVector(name="velocity_x", anchor_id="projectile-dot"),
                PhysicsVector(name="velocity_y", anchor_id="projectile-dot"),
            ),
            vectors_expected_same_anchor=("velocity_x", "velocity_y"),
        ),
    )

    return [
        VerticalExampleSpec(
            example_id="physics_kinematics_projectile",
            request=projectile_request,
            contract=projectile_contract,
            expected_template="physics_motion_explainer",
            output_name="physics_kinematics_projectile",
        )
    ]


def get_example(example_id: str) -> VerticalExampleSpec:
    for spec in builtin_vertical_examples():
        if spec.example_id == example_id:
            return spec
    raise KeyError(f"Unknown vertical example: {example_id}")
