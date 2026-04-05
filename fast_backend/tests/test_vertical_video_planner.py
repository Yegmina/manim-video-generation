from app.vertical_video import (
    ContentFamily,
    DerivationSpec,
    DerivationStep,
    DeterministicVerticalPlanner,
    DurationBucket,
    GraphSample,
    GraphSpec,
    KinematicsSpec,
    MotionPhase,
    VerticalVideoRequest,
    VerticalVideoService,
)


def test_math_request_uses_derivation_template_and_portrait_profile():
    planner = DeterministicVerticalPlanner()
    request = VerticalVideoRequest(
        topic="Expand (a+b)^2",
        family=ContentFamily.MATH,
        goal="show the clean derivation",
        duration_bucket=DurationBucket.SHORT,
        derivation=DerivationSpec(
            input_expression="(a+b)^2",
            steps=[
                DerivationStep("(a+b)^2"),
                DerivationStep("(a+b)(a+b)"),
                DerivationStep("a^2 + 2ab + b^2", highlight="result"),
            ],
            final_expression="a^2 + 2ab + b^2",
        ),
    )

    plan = planner.build_plan(request)

    assert plan.template_id == "math_derivation_stack"
    assert plan.render_profile.aspect_ratio == "9:16"
    assert plan.metadata["deterministic"] is True
    assert len(plan.beats) == 3
    assert plan.scene_spec is not None
    assert plan.scene_spec.family == "formula"
    assert plan.metadata["semantic_contract"]["formula"]["canonical_final_latex"] == "a^2 + 2ab + b^2"


def test_long_math_request_uses_graph_template_with_structured_samples():
    planner = DeterministicVerticalPlanner()
    request = VerticalVideoRequest(
        topic="Parabola shape",
        family=ContentFamily.MATH,
        goal="explain how y changes with x",
        duration_bucket=DurationBucket.LONG,
        graph=GraphSpec(
            expression="x**2",
            x_range=(-2.0, 2.0),
            y_range=(0.0, 4.0),
            samples=(
                GraphSample(-1.0, 1.0, "left"),
                GraphSample(0.0, 0.0, "vertex"),
                GraphSample(2.0, 4.0, "right"),
            ),
            highlight_label="vertex",
        ),
    )

    plan = planner.build_plan(request)

    assert plan.template_id == "math_graph_explainer"
    assert plan.scene_spec is not None
    assert plan.scene_spec.family == "graph"
    assert plan.scene_spec.payload["samples"][1]["label"] == "vertex"
    assert plan.metadata["semantic_contract"]["graph"]["required_annotations"] == ["vertex"]


def test_physics_request_uses_motion_template_and_keeps_vectors_anchored():
    planner = DeterministicVerticalPlanner()
    request = VerticalVideoRequest(
        topic="Projectile motion",
        family=ContentFamily.PHYSICS,
        goal="explain horizontal and vertical velocity",
        duration_bucket=DurationBucket.MEDIUM,
        kinematics=KinematicsSpec(
            equation_text="y = x - 0.12x^2",
            trajectory_expression="x - 0.12*x**2",
            phases=(
                MotionPhase("Launch", 1.0, 3.2, 2.4),
                MotionPhase("Mid-flight", 1.0, 3.2, 0.4),
                MotionPhase("Falling", 1.0, 3.2, -1.2),
            ),
        ),
    )

    plan = planner.build_plan(request)

    assert plan.template_id == "physics_motion_explainer"
    assert any("Anchor vectors" in rule for rule in plan.safety_rules)
    assert plan.scene_spec is not None
    assert plan.scene_spec.family == "physics"
    vectors = plan.metadata["semantic_contract"]["physics"]["vectors"]
    assert {vector["anchor_id"] for vector in vectors} == {"projectile-dot"}


def test_service_builds_family_specific_script():
    service = VerticalVideoService()
    request = VerticalVideoRequest(
        topic="Newton's second law",
        family=ContentFamily.PHYSICS,
        goal="explain force equals mass times acceleration",
    )

    script = service.build_script(request)

    assert "config.pixel_width = 1080" in script
    assert "config.pixel_height = 1920" in script
    assert "class GeneratedScene(Scene):" in script
    assert "build_motion_scene_objects" in script
