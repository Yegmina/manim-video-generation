from __future__ import annotations

from .models import VerticalVideoPlan


class VerticalManimScriptBuilder:
    """Emit starter Manim scripts from structured vertical video plans."""

    def build_script(self, plan: VerticalVideoPlan) -> str:
        beat_lines = []
        for beat in plan.beats:
            beat_lines.append(
                f"        steps.append(Paragraph({beat.narration!r}, line_spacing=0.65).scale(0.55))"
            )

        steps_block = "\n".join(beat_lines) or "        steps.append(Paragraph('No steps supplied').scale(0.55))"

        family_comment = f"# family={plan.request.family.value} template={plan.template_id}"
        return f'''from manim import *

config.pixel_width = {plan.render_profile.pixel_width}
config.pixel_height = {plan.render_profile.pixel_height}
config.frame_width = {plan.render_profile.frame_width}
config.frame_height = {plan.render_profile.frame_height}


class GeneratedScene(Scene):
    def construct(self):
        {family_comment}
        title = Text({plan.hook_text!r}, font_size={plan.render_profile.title_font_size})
        title.to_edge(UP, buff={plan.render_profile.safe_margin_y})

        steps = []
{steps_block}
        stack = VGroup(*steps).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        stack.scale_to_fit_width(config.frame_width - {2 * plan.render_profile.safe_margin_x})
        stack.next_to(title, DOWN, buff=0.9)

        footer = Text({plan.final_cta!r}, font_size=24)
        footer.to_edge(DOWN, buff={plan.render_profile.safe_margin_y})

        self.play(FadeIn(title, shift=DOWN * 0.2), run_time=0.6)
        self.wait(0.2)
        for item in stack:
            self.play(Write(item), run_time=0.7)
            self.wait(0.15)
        self.play(FadeIn(footer, shift=UP * 0.2), run_time=0.5)
        self.wait(0.8)
'''
