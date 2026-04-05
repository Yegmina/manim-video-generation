from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from manim_video_generator import ManimVideoGenerator

from ..services.preview_qa_service import PreviewQAService
from .repair_client import VerticalRepairClient
from .service import VerticalVideoService
from .models import VerticalVideoRequest


class VerticalVideoRepairLoop:
    """Preview-QA-driven repair loop for the deterministic vertical video subsystem."""

    def __init__(
        self,
        video_service: Optional[VerticalVideoService] = None,
        repair_client: Optional[VerticalRepairClient] = None,
        preview_service: Optional[PreviewQAService] = None,
    ):
        self.video_service = video_service or VerticalVideoService()
        self.repair_client = repair_client or VerticalRepairClient()
        self.preview_service = preview_service or PreviewQAService(
            manim_generator=ManimVideoGenerator(
                output_dir="fast_backend/generated_videos",
                manim_path="/home/openclaw/workspace/manim-video-generation/.venv/bin/python",
            )
        )

    async def render_with_repair(
        self,
        request: VerticalVideoRequest,
        output_dir: str | Path,
        output_name: str,
        max_repairs: int = 1,
    ) -> Dict[str, Any]:
        plan = self.video_service.plan_video(request)
        current_code = self.video_service.build_script_from_plan(plan)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = self.video_service.emit_manifest(plan, output_dir / f"{output_name}_manifest.json")

        attempts = []
        for attempt in range(max_repairs + 1):
            preview_report = self.preview_service.run_preview_qa(current_code, scene_name="GeneratedScene")
            attempt_payload = {
                "attempt": attempt + 1,
                "preview_ok": preview_report.get("ok", False),
                "preview_summary": preview_report.get("summary", {}),
            }
            attempts.append(attempt_payload)

            if preview_report.get("ok", False):
                video_path = self._render_code_to_video(current_code, output_dir, output_name)
                (output_dir / f"{output_name}_repair_report.json").write_text(
                    json.dumps({"attempts": attempts, "manifest": manifest}, indent=2),
                    encoding="utf-8",
                )
                return {
                    "ok": True,
                    "video_path": str(video_path),
                    "manifest_path": str(output_dir / f"{output_name}_manifest.json"),
                    "attempts": attempts,
                }

            if attempt >= max_repairs:
                break

            issue_text = self._preview_issue_text(preview_report)
            attempt_payload["repair_issue_text"] = issue_text
            try:
                repaired_code = self.repair_client.repair_code(
                    original_prompt=request.goal,
                    broken_code=current_code,
                    issue_text=issue_text,
                )
                attempt_payload["repair_ok"] = True
                attempt_payload["repair_error"] = ""
                current_code = repaired_code
            except Exception as exc:
                attempt_payload["repair_ok"] = False
                attempt_payload["repair_error"] = str(exc)
                break

        (output_dir / f"{output_name}_repair_report.json").write_text(
            json.dumps({"attempts": attempts, "manifest": manifest}, indent=2),
            encoding="utf-8",
        )
        return {
            "ok": False,
            "attempts": attempts,
            "manifest_path": str(output_dir / f"{output_name}_manifest.json"),
        }

    def _preview_issue_text(self, preview_report: Dict[str, Any]) -> str:
        issues = preview_report.get("summary", {}).get("aggregate_issues", [])
        if not issues:
            return "preview_qa_failed: preview did not pass but no aggregate issue codes were available"
        parts = []
        for issue in issues:
            parts.append(
                f"{issue.get('code')} frames={issue.get('frames')} peak_score={issue.get('peak_score')}"
            )
        return "preview_qa_failed: " + "; ".join(parts)

    def _render_code_to_video(self, script_content: str, output_dir: Path, output_name: str) -> Path:
        script_dir = output_dir / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / f"{output_name}.py"
        script_path.write_text(script_content, encoding="utf-8")

        generator = ManimVideoGenerator(
            output_dir=str(output_dir / "media"),
            manim_path="/home/openclaw/workspace/manim-video-generation/.venv/bin/python",
        )
        video_path = generator.generate_video(
            script_path=str(script_path),
            scene_name="GeneratedScene",
            quality="low_quality",
            output_name=output_name,
        )
        if not video_path:
            raise RuntimeError("Render failed after preview repair loop")
        return Path(video_path)
