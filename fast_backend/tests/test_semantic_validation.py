from fast_backend.app.services.semantic_validation import (
    FormulaSemanticContract,
    GraphSemanticContract,
    PhysicsSemanticContract,
    PhysicsVector,
    PointSample,
    SceneSemanticContract,
    VerticalLayoutContract,
    validate_formula_semantics,
    validate_graph_semantics,
    validate_physics_semantics,
    validate_scene_contract,
)


def test_validate_graph_semantics_accepts_consistent_samples_and_annotations():
    contract = SceneSemanticContract(
        scene_id="graph-ok",
        family="graph",
        measured_aspect_ratio="9:16",
        measured_annotations=("vertex", "y=x^2"),
        graph=GraphSemanticContract(
            expression="x^2",
            x_range=(-2, 2),
            y_range=(0, 4),
            sample_points=[PointSample(-1, 1), PointSample(0, 0), PointSample(2, 4)],
            required_annotations=["vertex"],
        ),
    )

    result = validate_graph_semantics(contract)
    assert result.ok is True
    assert result.issues == []


def test_validate_graph_semantics_flags_sample_mismatch():
    contract = SceneSemanticContract(
        scene_id="graph-bad",
        family="graph",
        graph=GraphSemanticContract(
            expression="x^2",
            x_range=(-2, 2),
            y_range=(0, 5),
            sample_points=[PointSample(-1, 1), PointSample(1, 3), PointSample(2, 4)],
        ),
    )

    result = validate_graph_semantics(contract)
    codes = {issue.code for issue in result.issues}
    assert "graph_sample_mismatch" in codes


def test_validate_formula_semantics_flags_bad_final_form_and_duplicates():
    contract = SceneSemanticContract(
        scene_id="formula-bad",
        family="formula",
        formula=FormulaSemanticContract(
            input_latex=r"(a+b)^2",
            expected_steps=[r"(a+b)^2", r"(a+b)^2", r"a^2 + ab + ba + b^2"],
            canonical_final_latex=r"a^2 + 2ab + b^2",
        ),
    )

    result = validate_formula_semantics(contract)
    codes = {issue.code for issue in result.issues}
    assert "formula_duplicate_consecutive_step" in codes
    assert "formula_final_form_mismatch" in codes


def test_validate_physics_semantics_flags_anchor_mismatch_and_marker_off_curve():
    contract = SceneSemanticContract(
        scene_id="physics-bad",
        family="physics",
        physics=PhysicsSemanticContract(
            motion_type="projectile",
            trajectory_expression="0.5*x - 0.05*x^2",
            marker_point=PointSample(5, 3.0),
            vectors=[
                PhysicsVector(name="velocity_x", anchor_id="dot-base"),
                PhysicsVector(name="velocity_y", anchor_id="dot-center"),
            ],
            vectors_expected_same_anchor=["velocity_x", "velocity_y"],
        ),
    )

    result = validate_physics_semantics(contract)
    codes = {issue.code for issue in result.issues}
    assert "physics_vector_anchor_mismatch" in codes
    assert "projectile_marker_off_trajectory" in codes


def test_validate_scene_contract_combines_vertical_and_family_checks():
    contract = SceneSemanticContract(
        scene_id="scene-combined",
        family="formula",
        measured_aspect_ratio="16:9",
        measured_text_blocks=5,
        vertical=VerticalLayoutContract(max_simultaneous_text_blocks=3),
        formula=FormulaSemanticContract(
            input_latex=r"x^2+2x+1",
            expected_steps=[r"x^2 + 2x + 1", r"(x+1)^2"],
            canonical_final_latex=r"(x+1)^2",
        ),
    )

    result = validate_scene_contract(contract)
    codes = {issue.code for issue in result.issues}
    assert "vertical_aspect_ratio_mismatch" in codes
    assert "vertical_text_block_overload" in codes
