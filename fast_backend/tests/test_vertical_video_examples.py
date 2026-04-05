from app.services.semantic_validation import validate_scene_contract
from app.vertical_video import VerticalVideoService, builtin_vertical_examples, get_example


def test_builtin_examples_include_projectile_kinematics_case():
    example_ids = {spec.example_id for spec in builtin_vertical_examples()}
    assert "physics_kinematics_projectile" in example_ids


def test_projectile_example_produces_expected_template_and_semantic_contract():
    spec = get_example("physics_kinematics_projectile")
    service = VerticalVideoService()

    plan = service.plan_video(spec.request)

    assert plan.template_id == "physics_motion_explainer"
    assert plan.scene_spec is not None
    assert plan.scene_spec.family == "physics"
    assert plan.scene_spec.payload["trajectory_expression"] == "0.95*x - 0.09*x**2"

    semantic = validate_scene_contract(spec.contract)
    assert semantic.ok is True
    assert semantic.issues == []


def test_projectile_example_script_is_portrait_and_compiles():
    spec = get_example("physics_kinematics_projectile")
    service = VerticalVideoService()

    script = service.build_script(spec.request)

    assert "config.pixel_width = 1080" in script
    assert "config.pixel_height = 1920" in script
    assert 'TEMPLATE_ID = "physics_motion_explainer"' in script or "TEMPLATE_ID = 'physics_motion_explainer'" in script
    assert "0.95*x - 0.09*x**2" in script
    compile(script, "<vertical-example>", "exec")
