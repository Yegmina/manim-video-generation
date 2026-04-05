from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class ContentFamily(str, Enum):
    MATH = "math"
    PHYSICS = "physics"


class DurationBucket(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


@dataclass(frozen=True)
class RenderProfile:
    aspect_ratio: str = "9:16"
    pixel_width: int = 1080
    pixel_height: int = 1920
    frame_width: int = 9
    frame_height: int = 16
    safe_margin_x: float = 0.6
    safe_margin_y: float = 0.9
    title_font_size: int = 42
    body_font_size: int = 30
    max_body_lines: int = 3


@dataclass(frozen=True)
class DerivationStep:
    text: str
    highlight: Optional[str] = None


@dataclass(frozen=True)
class DerivationSpec:
    input_expression: str
    steps: Sequence[DerivationStep]
    final_expression: str


@dataclass(frozen=True)
class GraphSample:
    x: float
    y: float
    label: str = ""


@dataclass(frozen=True)
class GraphSpec:
    expression: str
    x_range: Tuple[float, float] = (-2.0, 2.0)
    y_range: Tuple[float, float] = (-1.0, 4.0)
    samples: Sequence[GraphSample] = field(default_factory=tuple)
    highlight_label: str = "shape"


@dataclass(frozen=True)
class MotionPhase:
    label: str
    duration_seconds: float
    velocity_x: float
    velocity_y: float


@dataclass(frozen=True)
class KinematicsSpec:
    motion_type: str = "projectile"
    equation_text: str = "y = x - 0.12x^2"
    trajectory_expression: str = "x - 0.12*x**2"
    x_range: Tuple[float, float] = (0.0, 7.0)
    y_range: Tuple[float, float] = (0.0, 3.0)
    marker_x: float = 3.5
    phases: Sequence[MotionPhase] = field(default_factory=tuple)


StructuredPayload = Dict[str, Any]


@dataclass(frozen=True)
class VerticalVideoRequest:
    topic: str
    family: ContentFamily
    goal: str
    audience_age: str = "teen"
    tone: str = "clear"
    duration_bucket: DurationBucket = DurationBucket.SHORT
    visual_style: str = "clean"
    constraints: List[str] = field(default_factory=list)
    supporting_points: List[str] = field(default_factory=list)
    structured_payload: StructuredPayload = field(default_factory=dict)
    derivation: Optional[DerivationSpec] = None
    graph: Optional[GraphSpec] = None
    kinematics: Optional[KinematicsSpec] = None


@dataclass(frozen=True)
class VisualBeat:
    key: str
    narration: str
    visual: str
    emphasis: Optional[str] = None
    duration_seconds: float = 2.0


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    family: str
    template_id: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class VerticalVideoPlan:
    request: VerticalVideoRequest
    render_profile: RenderProfile
    template_id: str
    hook_text: str
    beats: List[VisualBeat]
    final_cta: str
    safety_rules: List[str]
    visual_rules: List[str]
    scene_spec: Optional[SceneSpec] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
