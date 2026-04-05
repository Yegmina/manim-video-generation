from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import json
import os

from .deterministic_planner import DeterministicVerticalPlanner
from .manim_builder import VerticalManimScriptBuilder
from .manifest import build_scene_manifest
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

    def build_script_from_plan(self, plan: VerticalVideoPlan) -> str:
        return self.builder.build_script(plan)

    def emit_manifest(self, plan: VerticalVideoPlan, output_path: str | Path | None = None) -> dict:
        manifest = build_scene_manifest(plan)
        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

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
        self.emit_manifest(plan, output_dir / f"{output_name}_manifest.json")
        scripts_dir = output_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script_path = scripts_dir / f"{output_name}.py"
        script_path.write_text(script, encoding="utf-8")

        media_dir = output_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        python_bin = os.environ.get("VERTICAL_VIDEO_PYTHON")
        if not python_bin:
            repo_root = Path(__file__).resolve().parents[3]
            venv_python = repo_root / ".venv" / "bin" / "python"
            python_bin = str(venv_python if venv_python.exists() else Path(sys.executable))

        command = [
            python_bin,
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
