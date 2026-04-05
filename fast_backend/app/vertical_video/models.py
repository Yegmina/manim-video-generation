from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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


@dataclass(frozen=True)
class VisualBeat:
    key: str
    narration: str
    visual: str
    emphasis: Optional[str] = None
    duration_seconds: float = 2.0


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
    metadata: Dict[str, Any] = field(default_factory=dict)
