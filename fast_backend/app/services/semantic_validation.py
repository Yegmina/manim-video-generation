"""Semantic validation scaffolding for a replacement vertical-video generation system.

This module is intentionally separate from compile/render validation. It defines a
contract-driven path for checking whether a generated scene is *about the right
thing* and whether it is acceptable in a 9:16 educational format.

The expected long-term flow is:
1. Planner/generator emits a structured semantic contract per scene.
2. Renderer/instrumentation emits a lightweight scene manifest with measured
   geometry/anchors/text and optional sampled semantic data.
3. Validators compare contract vs manifest before/after preview rendering.

Current implementation is a starter scaffold with deterministic checks that can
already validate:
- portrait-safe vertical framing metadata
- graph formula/sample consistency
- formula derivation step hygiene
- physics vector anchor consistency and trajectory marker consistency
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple


SceneFamily = Literal["graph", "formula", "physics"]
Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class SemanticIssue:
    code: str
    message: str
    severity: Severity = "error"
    evidence: Optional[str] = None


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: List[SemanticIssue] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalLayoutContract:
    aspect_ratio: str = "9:16"
    safe_margin_x: float = 0.08
    safe_margin_y: float = 0.08
    max_simultaneous_text_blocks: int = 3
    require_portrait: bool = True


@dataclass(frozen=True)
class PointSample:
    x: float
    y: float


@dataclass(frozen=True)
class GraphSemanticContract:
    expression: str
    x_range: Tuple[float, float]
    y_range: Tuple[float, float]
    sample_points: Sequence[PointSample]
    required_annotations: Sequence[str] = field(default_factory=tuple)
    max_labels_near_plot: int = 2


@dataclass(frozen=True)
class FormulaSemanticContract:
    input_latex: str
    expected_steps: Sequence[str]
    canonical_final_latex: str
    require_mathtex: bool = True
    max_steps: int = 6


@dataclass(frozen=True)
class PhysicsVector:
    name: str
    anchor_id: str


@dataclass(frozen=True)
class PhysicsSemanticContract:
    motion_type: Literal["projectile", "kinematics", "forces"]
    trajectory_expression: Optional[str] = None
    trajectory_samples: Sequence[PointSample] = field(default_factory=tuple)
    marker_point: Optional[PointSample] = None
    vectors: Sequence[PhysicsVector] = field(default_factory=tuple)
    vectors_expected_same_anchor: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class SceneSemanticContract:
    scene_id: str
    family: SceneFamily
    vertical: VerticalLayoutContract = field(default_factory=VerticalLayoutContract)
    graph: Optional[GraphSemanticContract] = None
    formula: Optional[FormulaSemanticContract] = None
    physics: Optional[PhysicsSemanticContract] = None
    measured_aspect_ratio: Optional[str] = None
    measured_text_blocks: Optional[int] = None
    measured_annotations: Sequence[str] = field(default_factory=tuple)


_ALLOWED_MATH_NAMES: Dict[str, object] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "sqrt": math.sqrt,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
    "abs": abs,
}


def _normalize_latex(text: str) -> str:
    text = text.strip()
    text = text.replace(" ", "")
    text = text.replace("\\left", "").replace("\\right", "")
    return text


def _safe_eval_expression(expression: str, x: float) -> float:
    normalized = expression.replace("^", "**")
    normalized = normalized.replace("\\cdot", "*")
    normalized = normalized.replace("{", "(").replace("}", ")")
    normalized = re.sub(r"\\frac\((.+?)\)\((.+?)\)", r"((\1)/(\2))", normalized)
    return float(eval(normalized, {"__builtins__": {}}, {**_ALLOWED_MATH_NAMES, "x": x}))


def _make_result(issues: Iterable[SemanticIssue]) -> ValidationResult:
    issue_list = list(issues)
    return ValidationResult(ok=not any(issue.severity == "error" for issue in issue_list), issues=issue_list)


def validate_vertical_layout(contract: SceneSemanticContract) -> ValidationResult:
    issues: List[SemanticIssue] = []
    vertical = contract.vertical

    measured_aspect = contract.measured_aspect_ratio or vertical.aspect_ratio
    if vertical.require_portrait and measured_aspect != "9:16":
        issues.append(
            SemanticIssue(
                code="vertical_aspect_ratio_mismatch",
                message="Scene is not explicitly measured as 9:16 portrait.",
                evidence=f"measured={measured_aspect}",
            )
        )

    if contract.measured_text_blocks is not None and contract.measured_text_blocks > vertical.max_simultaneous_text_blocks:
        issues.append(
            SemanticIssue(
                code="vertical_text_block_overload",
                message="Too many simultaneous text blocks for a Shorts-style portrait scene.",
                severity="warning",
                evidence=(
                    f"measured={contract.measured_text_blocks}, "
                    f"allowed={vertical.max_simultaneous_text_blocks}"
                ),
            )
        )

    return _make_result(issues)


def validate_graph_semantics(contract: SceneSemanticContract) -> ValidationResult:
    issues: List[SemanticIssue] = []
    graph = contract.graph
    if graph is None:
        return _make_result([SemanticIssue(code="missing_graph_contract", message="Graph scene is missing graph semantic contract.")])

    if graph.x_range[0] >= graph.x_range[1]:
        issues.append(SemanticIssue(code="graph_invalid_x_range", message="Graph x_range must be strictly increasing."))
    if graph.y_range[0] >= graph.y_range[1]:
        issues.append(SemanticIssue(code="graph_invalid_y_range", message="Graph y_range must be strictly increasing."))
    if len(graph.sample_points) < 3:
        issues.append(
            SemanticIssue(
                code="graph_insufficient_samples",
                message="Graph contract should include at least three semantic sample points.",
            )
        )

    for sample in graph.sample_points:
        try:
            expected_y = _safe_eval_expression(graph.expression, sample.x)
        except Exception as exc:  # pragma: no cover - defensive fallback
            issues.append(
                SemanticIssue(
                    code="graph_expression_unreadable",
                    message="Graph expression could not be evaluated safely.",
                    evidence=str(exc),
                )
            )
            break
        if abs(expected_y - sample.y) > 1e-6:
            issues.append(
                SemanticIssue(
                    code="graph_sample_mismatch",
                    message="Graph sample does not match declared expression.",
                    evidence=f"x={sample.x}, expected={expected_y}, actual={sample.y}",
                )
            )
            break

    measured_annotations = {item.strip().lower() for item in contract.measured_annotations}
    for annotation in graph.required_annotations:
        if annotation.strip().lower() not in measured_annotations:
            issues.append(
                SemanticIssue(
                    code="graph_required_annotation_missing",
                    message="Required graph annotation is missing from measured scene metadata.",
                    severity="warning",
                    evidence=annotation,
                )
            )

    return _make_result(issues)


def validate_formula_semantics(contract: SceneSemanticContract) -> ValidationResult:
    issues: List[SemanticIssue] = []
    formula = contract.formula
    if formula is None:
        return _make_result([SemanticIssue(code="missing_formula_contract", message="Formula scene is missing formula semantic contract.")])

    if not formula.expected_steps:
        issues.append(SemanticIssue(code="formula_missing_steps", message="Formula contract must declare at least one derivation step."))
        return _make_result(issues)

    if len(formula.expected_steps) > formula.max_steps:
        issues.append(
            SemanticIssue(
                code="formula_step_overload",
                message="Formula derivation contains too many visible steps for a vertical short.",
                severity="warning",
                evidence=f"steps={len(formula.expected_steps)}, max={formula.max_steps}",
            )
        )

    normalized_steps = [_normalize_latex(step) for step in formula.expected_steps]
    if any(not step for step in normalized_steps):
        issues.append(SemanticIssue(code="formula_empty_step", message="Formula contract contains an empty derivation step."))

    for previous, current in zip(normalized_steps, normalized_steps[1:]):
        if previous == current:
            issues.append(
                SemanticIssue(
                    code="formula_duplicate_consecutive_step",
                    message="Consecutive formula steps are identical, suggesting a redundant animation beat.",
                    severity="warning",
                    evidence=current,
                )
            )
            break

    if normalized_steps[-1] != _normalize_latex(formula.canonical_final_latex):
        issues.append(
            SemanticIssue(
                code="formula_final_form_mismatch",
                message="Last derivation step does not match canonical final formula.",
                evidence=f"last={normalized_steps[-1]}, canonical={_normalize_latex(formula.canonical_final_latex)}",
            )
        )

    if formula.require_mathtex:
        non_mathtex_like = [step for step in formula.expected_steps if "\\" not in step and "^" not in step and "=" not in step]
        if non_mathtex_like:
            issues.append(
                SemanticIssue(
                    code="formula_steps_not_mathtex_like",
                    message="Formula steps do not look like explicit math content suitable for MathTex.",
                    severity="warning",
                    evidence=non_mathtex_like[0],
                )
            )

    return _make_result(issues)


def validate_physics_semantics(contract: SceneSemanticContract) -> ValidationResult:
    issues: List[SemanticIssue] = []
    physics = contract.physics
    if physics is None:
        return _make_result([SemanticIssue(code="missing_physics_contract", message="Physics scene is missing physics semantic contract.")])

    vector_anchor_map = {vector.name: vector.anchor_id for vector in physics.vectors}
    if physics.vectors_expected_same_anchor:
        anchors = {vector_anchor_map.get(name) for name in physics.vectors_expected_same_anchor if name in vector_anchor_map}
        if len(anchors) > 1:
            issues.append(
                SemanticIssue(
                    code="physics_vector_anchor_mismatch",
                    message="Physics vectors expected to share one anchor do not.",
                    evidence=", ".join(f"{name}:{vector_anchor_map.get(name)}" for name in physics.vectors_expected_same_anchor),
                )
            )

    if physics.trajectory_expression and physics.marker_point is not None:
        try:
            expected_y = _safe_eval_expression(physics.trajectory_expression, physics.marker_point.x)
            if abs(expected_y - physics.marker_point.y) > 1e-6:
                issues.append(
                    SemanticIssue(
                        code="projectile_marker_off_trajectory",
                        message="Physics marker point does not lie on the declared trajectory.",
                        evidence=(
                            f"x={physics.marker_point.x}, expected={expected_y}, actual={physics.marker_point.y}"
                        ),
                    )
                )
        except Exception as exc:  # pragma: no cover - defensive fallback
            issues.append(
                SemanticIssue(
                    code="physics_expression_unreadable",
                    message="Physics trajectory expression could not be evaluated safely.",
                    evidence=str(exc),
                )
            )

    if physics.trajectory_expression and len(physics.trajectory_samples) >= 2:
        for sample in physics.trajectory_samples:
            expected_y = _safe_eval_expression(physics.trajectory_expression, sample.x)
            if abs(expected_y - sample.y) > 1e-6:
                issues.append(
                    SemanticIssue(
                        code="physics_trajectory_sample_mismatch",
                        message="Physics trajectory samples do not match declared trajectory expression.",
                        evidence=f"x={sample.x}, expected={expected_y}, actual={sample.y}",
                    )
                )
                break

    return _make_result(issues)


def validate_scene_contract(contract: SceneSemanticContract) -> ValidationResult:
    """Run all relevant validators for a scene contract."""
    issues: List[SemanticIssue] = []

    issues.extend(validate_vertical_layout(contract).issues)
    if contract.family == "graph":
        issues.extend(validate_graph_semantics(contract).issues)
    elif contract.family == "formula":
        issues.extend(validate_formula_semantics(contract).issues)
    elif contract.family == "physics":
        issues.extend(validate_physics_semantics(contract).issues)
    else:  # pragma: no cover - Literal should prevent this
        issues.append(SemanticIssue(code="unsupported_scene_family", message=f"Unsupported scene family: {contract.family}"))

    return _make_result(issues)
