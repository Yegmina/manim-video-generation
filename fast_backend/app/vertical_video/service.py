from __future__ import annotations

from .deterministic_planner import DeterministicVerticalPlanner
from .manim_builder import VerticalManimScriptBuilder
from .models import VerticalVideoPlan, VerticalVideoRequest


class VerticalVideoService:
    """Facade for the deterministic vertical-video subsystem."""

    def __init__(self, planner: DeterministicVerticalPlanner | None = None, builder: VerticalManimScriptBuilder | None = None):
        self.planner = planner or DeterministicVerticalPlanner()
        self.builder = builder or VerticalManimScriptBuilder()

    def plan_video(self, request: VerticalVideoRequest) -> VerticalVideoPlan:
        return self.planner.build_plan(request)

    def build_script(self, request: VerticalVideoRequest) -> str:
        plan = self.plan_video(request)
        return self.builder.build_script(plan)
