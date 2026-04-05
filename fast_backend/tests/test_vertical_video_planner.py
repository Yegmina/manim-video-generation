from app.vertical_video import (
    ContentFamily,
    DeterministicVerticalPlanner,
    DurationBucket,
    VerticalVideoRequest,
    VerticalVideoService,
)


def test_math_request_uses_derivation_template_and_portrait_profile():
    planner = DeterministicVerticalPlanner()
    request = VerticalVideoRequest(
        topic="Quadratic formula",
        family=ContentFamily.MATH,
        goal="show how the formula is used",
        duration_bucket=DurationBucket.SHORT,
        supporting_points=[
            "Ask what the coefficients mean",
            "Substitute a, b, and c carefully",
            "Interpret the two roots",
        ],
    )

    plan = planner.build_plan(request)

    assert plan.template_id == "math_derivation_stack"
    assert plan.render_profile.aspect_ratio == "9:16"
    assert plan.metadata["deterministic"] is True
    assert len(plan.beats) == 3


def test_physics_request_uses_motion_template():
    planner = DeterministicVerticalPlanner()
    request = VerticalVideoRequest(
        topic="Projectile motion",
        family=ContentFamily.PHYSICS,
        goal="explain horizontal and vertical velocity",
        duration_bucket=DurationBucket.MEDIUM,
    )

    plan = planner.build_plan(request)

    assert plan.template_id == "physics_motion_explainer"
    assert any("Anchor vectors" in rule for rule in plan.safety_rules)


def test_service_builds_portrait_script():
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
