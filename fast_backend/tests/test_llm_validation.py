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


def test_validate_code_compilation_flags_graph_vertical_stack_crowding():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Quadratic", font_size=44).to_edge(UP)
        axes = Axes(x_range=[-3, 3], y_range=[-1, 9]).next_to(title, DOWN, buff=0.5)
        graph = axes.plot(lambda x: x**2, color=BLUE)
        formula = MathTex("f(x)=x^2").next_to(axes, DOWN, buff=0.4)
        explanation = Text("Parabola opens upward", font_size=26).next_to(formula, DOWN, buff=0.3)
        self.add(title, axes, graph, formula, explanation)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}
    assert "graph_vertical_stack_crowding_risk" in risk_codes


def test_validate_code_compilation_flags_graph_label_collision_risk():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Velocity Graph", font_size=40).to_edge(UP)
        axes = Axes(x_range=[0, 10], y_range=[0, 10]).next_to(title, DOWN, buff=0.5)
        x_label = axes.get_x_axis_label("t")
        y_label = axes.get_y_axis_label("v")
        graph = axes.plot(lambda x: x, color=YELLOW)
        graph_label = axes.get_graph_label(graph, label="v=t", x_val=8, direction=UR)
        formula = MathTex("v=t").next_to(axes, DOWN, buff=0.4)
        self.add(title, axes, x_label, y_label, graph, graph_label, formula)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}
    assert "graph_label_collision_risk" in risk_codes


def test_validate_code_compilation_flags_legend_plot_overlap_risk():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        axes = Axes(x_range=[0, 6], y_range=[-1, 1])
        graph = axes.plot(lambda x: np.sin(x), color=BLUE)
        legend = VGroup(Text("sin(x)", font_size=22))
        legend.to_corner(UR)
        self.add(axes, graph, legend)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}
    assert "legend_plot_overlap_risk" in risk_codes


def test_validate_code_compilation_flags_vertical_chain_crowding_risk():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Topic").to_edge(UP)
        block1 = Text("A").next_to(title, DOWN, buff=0.3)
        block2 = Text("B").next_to(block1, DOWN, buff=0.3)
        block3 = Text("C").next_to(block2, DOWN, buff=0.3)
        block4 = Text("D").next_to(block3, DOWN, buff=0.3)
        self.add(title, block1, block2, block3, block4)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}
    assert "vertical_chain_crowding_risk" in risk_codes


def test_validate_code_compilation_flags_below_axes_annotation_overflow_risk():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Linear Growth", font_size=42).to_edge(UP)
        axes = Axes(x_range=[0, 8], y_range=[0, 8]).next_to(title, DOWN, buff=0.4)
        graph = axes.plot(lambda x: 0.8 * x + 1, color=GREEN)
        formula = MathTex("y=0.8x+1").next_to(axes, DOWN, buff=0.3)
        description = Text("Slope is constant", font_size=26).next_to(formula, DOWN, buff=0.3)
        self.add(title, axes, graph, formula, description)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}
    assert "below_axes_annotation_overflow_risk" in risk_codes


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


def test_model_map_includes_new_gemini_preview_and_latest_aliases():
    llm_service = LLMService()

    expected_keys = {
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-latest",
        "gemini-pro-latest",
    }

    assert expected_keys.issubset(set(llm_service._MODEL_MAP.keys()))


def test_build_generation_prompt_adds_portrait_graph_guardrails():
    llm_service = LLMService()
    user_prompt = (
        "Create a portrait 9:16 educational lesson for students explaining a sine graph "
        "with axes and labels."
    )

    full_prompt = llm_service._build_generation_prompt(
        llm_service._SYSTEM_PROMPTS["gemini-3-flash-preview"],
        user_prompt,
    )

    assert "Portrait graph scene guardrails" in full_prompt
    assert "avoid dense tick labels" in full_prompt
    assert "no duplicate pi labels" in full_prompt
    assert f"User request: {user_prompt}" in full_prompt


def test_build_generation_prompt_skips_portrait_graph_guardrails_for_general_prompt():
    llm_service = LLMService()
    user_prompt = "Create a short intro animation with a title and subtitle."

    full_prompt = llm_service._build_generation_prompt(
        llm_service._SYSTEM_PROMPTS["gemini-3-flash-preview"],
        user_prompt,
    )

    assert "Portrait graph scene guardrails" not in full_prompt


def test_build_generation_prompt_adds_formula_only_guardrails():
    llm_service = LLMService()
    user_prompt = "Create a formula-only derivation of (a+b)^2 with no graph."

    full_prompt = llm_service._build_generation_prompt(
        llm_service._SYSTEM_PROMPTS["gemini-3-flash-preview"],
        user_prompt,
    )

    assert "Formula-only derivation guardrails" in full_prompt
    assert "Avoid decorative backgrounds" in full_prompt
    assert "Prefer reliable animations: Write/FadeIn" in full_prompt
    assert "avoid key_map-heavy transforms" in full_prompt


def test_build_generation_prompt_adds_portrait_formula_requirements():
    llm_service = LLMService()
    user_prompt = "Create a portrait formula-only derivation of (a+b)^2 with no graph for Shorts."

    full_prompt = llm_service._build_generation_prompt(
        llm_service._SYSTEM_PROMPTS["gemini-3-flash-preview"],
        user_prompt,
    )

    assert "config.pixel_width = 1080" in full_prompt
    assert "Portrait formula layout requirement" in full_prompt
    assert "Do not spread derivation terms across the width of the frame" in full_prompt


def test_create_structured_code_repair_prompt_mentions_modify_existing_code():
    llm_service = LLMService()
    prompt = llm_service._create_structured_code_repair_prompt(
        original_prompt="Derive (a+b)^2",
        broken_code="from manim import *\n\nclass GeneratedScene(Scene):\n    pass\n",
        issue_text="Missing construct method",
    )

    assert "modify the existing code" in prompt
    assert "Do NOT start from scratch unless the code is unusable" in prompt
    assert "Code to repair:" in prompt
    assert "Missing construct method" in prompt


def test_create_structured_code_repair_prompt_adds_layout_style_rules():
    llm_service = LLMService()
    prompt = llm_service._create_structured_code_repair_prompt(
        original_prompt="Create a portrait formula-only derivation of (a+b)^2 with no graph.",
        broken_code="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass\n",
        issue_text="portrait layout issue with horizontal alignment and decorative rectangle highlight",
    )

    assert "Additional layout/style repair requirements" in prompt
    assert "avoid wide horizontal composition" in prompt
    assert "Do not add decorative highlight rectangles" in prompt


def test_summarize_layout_style_failures_includes_preview_and_alignment_guidance():
    llm_service = LLMService()
    summary = llm_service._summarize_layout_style_failures(
        "Create a portrait formula-only derivation of (a+b)^2 with no graph.",
        [
            "preview_qa_failed attempt=1; preview_qa_codes=dense_horizontal_label_band; frames=dense_horizontal_label_band:2",
            "bad alignment and decorative rectangle highlight",
        ],
    )

    assert "Portrait requirement" in summary
    assert "MathTex" in summary
    assert "Reduce dense lower-band/horizontal clutter" in summary
    assert "Fix alignment" in summary
    assert "Remove decorative highlight shapes" in summary


def test_validate_code_compilation_flags_formula_transform_matching_chain_risks():
    llm_service = LLMService()
    code = r"""
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        step1 = MathTex(r"(a+b)^2")
        step2 = MathTex(r"(a+b)(a+b)")
        step3 = MathTex(r"a^2 + ab + ba + b^2")
        step4 = MathTex(r"a^2 + 2ab + b^2")
        self.play(Write(step1))
        self.play(TransformMatchingTex(step1, step2))
        self.play(TransformMatchingTex(step2, step3))
        self.play(TransformMatchingTex(step3, step4))
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}

    assert "formula_transform_matching_chain_risk" in risk_codes
    assert "formula_complex_step_morph_risk" in risk_codes


def test_validate_code_compilation_flags_formula_key_map_transform_risk():
    llm_service = LLMService()
    code = r"""
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        step1 = MathTex(r"x^2+2x+1")
        step2 = MathTex(r"(x+1)^2")
        self.play(Write(step1))
        self.play(
            TransformMatchingTex(
                step1,
                step2,
                key_map={"x^2": "(x+1)^2", "2x": "x+1", "1": "x+1"},
            )
        )
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))
    risk_codes = {risk["code"] for risk in result["report"]["layout_risks"]}

    assert "formula_key_map_transform_risk" in risk_codes


def test_validate_code_compilation_flags_malformed_repeated_kwarg_assignment():
    llm_service = LLMService()
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Test", color= color= BLUE)
        self.add(title)
"""
    result = asyncio.run(llm_service._validate_code_compilation(code))

    assert result["success"] is False
    error_codes = {issue["code"] for issue in result["report"]["errors"]}
    assert "malformed_repeated_kwarg_assignment" in error_codes
    assert "syntax_error" in error_codes
