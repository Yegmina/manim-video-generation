import asyncio

from fast_backend.app.services.llm_service import LLMService
from fast_backend.app.models.video import VideoGenerationCreate


def test_validate_code_compilation_reports_static_layout_risks():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Big Title", font_size=96).to_edge(UP)
        subtitle = Text("Subtitle", font_size=84).to_edge(UP)
        note = Text("Far note", font_size=32)
        note.move_to([10, 0, 0])
        self.play(Write(title))
        self.play(Write(subtitle))
        self.play(Write(note))
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))

    assert result["success"] is True
    report = result["report"]
    risk_codes = {risk["code"] for risk in report["layout_risks"]}
    assert "anchor_overlap_risk" in risk_codes
    assert "offscreen_coordinate_risk" in risk_codes
    assert "large_text_crowding_risk" in risk_codes


def test_validate_code_compilation_includes_structured_errors():
    llm_service = LLMService()
    code = """
from manim import *

class NotGeneratedScene(Scene):
    def construct(self):
        pass
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))

    assert result["success"] is False
    report = result["report"]
    assert result["error"] is not None
    assert any(issue["code"] == "missing_generated_scene" for issue in report["errors"])


def test_video_generation_create_accepts_metadata_alias():
    payload = {
        "title": "Alias check",
        "description": "metadata alias support",
        "script_content": "from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        self.wait(1)\n",
        "scene_name": "GeneratedScene",
        "quality": "low_quality",
        "format": "mp4",
        "metadata": {"validation_report": {"success": True}},
    }
    model = VideoGenerationCreate(**payload)
    assert model.video_metadata == {"validation_report": {"success": True}}
