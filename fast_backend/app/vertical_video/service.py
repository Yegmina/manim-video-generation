from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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

    def render_video(
        self,
        request: VerticalVideoRequest,
        output_dir: str | Path,
        output_name: str = "vertical_video",
        quality: str = "l",
    ) -> Path:
        plan = self.plan_video(request)
        script = self.builder.build_script(plan)

        output_dir = Path(output_dir)
        scripts_dir = output_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script_path = scripts_dir / f"{output_name}.py"
        script_path.write_text(script, encoding="utf-8")

        media_dir = output_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "manim",
            "render",
            str(script_path),
            "GeneratedScene",
            f"-q{quality}",
            "--media_dir",
            str(media_dir),
            "-o",
            output_name,
            "--format",
            "mp4",
        ]
        subprocess.run(command, check=True)

        matches = sorted(media_dir.glob(f"**/{output_name}.mp4"))
        if not matches:
            raise FileNotFoundError(f"Manim finished but no output MP4 was found for {output_name}")
        return matches[-1]
