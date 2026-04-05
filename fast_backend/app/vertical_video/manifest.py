from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from .models import VerticalVideoPlan


def build_scene_manifest(plan: VerticalVideoPlan) -> Dict[str, Any]:
    """Emit machine-readable scene metadata for semantic validation/reporting."""
    scene = plan.scene_spec
    if scene is None:
        raise ValueError("VerticalVideoPlan has no scene_spec; cannot emit manifest")

    manifest: Dict[str, Any] = {
        "scene_id": scene.scene_id,
        "family": scene.family,
        "template_id": scene.template_id,
        "aspect_ratio": plan.render_profile.aspect_ratio,
        "render_profile": {
            "pixel_width": plan.render_profile.pixel_width,
            "pixel_height": plan.render_profile.pixel_height,
            "frame_width": plan.render_profile.frame_width,
            "frame_height": plan.render_profile.frame_height,
            "safe_margin_x": plan.render_profile.safe_margin_x,
            "safe_margin_y": plan.render_profile.safe_margin_y,
        },
        "hook_text": plan.hook_text,
        "cta": plan.final_cta,
        "beats": [asdict(beat) for beat in plan.beats],
        "payload": scene.payload,
    }

    annotations: List[str] = []
    payload = scene.payload
    if scene.family == "graph":
        annotations.extend([payload.get("highlight_label", "")])
        annotations.extend([sample.get("label", "") for sample in payload.get("samples", [])])
    elif scene.family == "physics":
        annotations.extend([phase.get("label", "") for phase in payload.get("phases", [])])
        annotations.extend(["v_x", "v_y", "horizontal", "vertical"])
    elif scene.family == "formula":
        annotations.extend([payload.get("final_expression", "")])
        annotations.extend(payload.get("steps", []))

    manifest["measured_annotations"] = [item for item in annotations if item]
    manifest["measured_text_blocks"] = min(3, max(1, len(manifest["measured_annotations"]) // 2 + 1))
    manifest["semantic"] = _build_family_semantic_snapshot(plan)
    return manifest


def _build_family_semantic_snapshot(plan: VerticalVideoPlan) -> Dict[str, Any]:
    scene = plan.scene_spec
    assert scene is not None
    payload = scene.payload

    if scene.family == "formula":
        return {
            "input_expression": payload.get("input_expression"),
            "steps": payload.get("steps", []),
            "final_expression": payload.get("final_expression"),
            "math_mode": "text-cards-for-now",
        }
    if scene.family == "graph":
        return {
            "expression": payload.get("expression"),
            "samples": payload.get("samples", []),
            "highlight_label": payload.get("highlight_label"),
        }
    if scene.family == "physics":
        marker_x = payload.get("marker_x")
        trajectory_expression = payload.get("trajectory_expression")
        return {
            "motion_type": payload.get("motion_type", "projectile"),
            "trajectory_expression": trajectory_expression,
            "marker_x": marker_x,
            "vector_anchor_id": "projectile-dot",
            "vectors": ["velocity_x", "velocity_y"],
            "phases": payload.get("phases", []),
        }
    return {}
