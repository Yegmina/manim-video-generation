from __future__ import annotations

from textwrap import dedent

from .models import VerticalVideoPlan


class VerticalManimScriptBuilder:
    """Emit family-aware Manim scripts from structured vertical video plans."""

    def build_script(self, plan: VerticalVideoPlan) -> str:
        if plan.scene_spec is None:
            raise ValueError("Vertical plan is missing scene_spec; cannot build script.")

        template = dedent(
            """
            from manim import *
            import math

            config.pixel_width = __PIXEL_WIDTH__
            config.pixel_height = __PIXEL_HEIGHT__
            config.frame_width = __FRAME_WIDTH__
            config.frame_height = __FRAME_HEIGHT__
            config.background_color = "#0F172A"

            TITLE_FONT = __TITLE_FONT__
            BODY_FONT = __BODY_FONT__
            SAFE_X = __SAFE_X__
            SAFE_Y = __SAFE_Y__
            TEMPLATE_ID = __TEMPLATE_ID__
            SCENE_PAYLOAD = __SCENE_PAYLOAD__


            def fit_to_portrait(mobject, extra_margin=0.0):
                max_width = config.frame_width - (2 * SAFE_X) - extra_margin
                max_height = config.frame_height - (2 * SAFE_Y) - extra_margin
                mobject.scale_to_fit_width(max_width)
                if mobject.height > max_height:
                    mobject.scale_to_fit_height(max_height)
                return mobject


            def make_title(text):
                title = Text(text, font_size=TITLE_FONT, color=WHITE, weight=BOLD)
                fit_to_portrait(title, extra_margin=0.2)
                title.to_edge(UP, buff=SAFE_Y)
                return title


            def make_footer(text):
                footer = Text(text, font_size=24, color="#CBD5E1")
                fit_to_portrait(footer, extra_margin=0.6)
                footer.to_edge(DOWN, buff=SAFE_Y)
                return footer


            def build_derivation_cards(payload):
                cards = []
                colors = ["#38BDF8", "#A78BFA", "#34D399", "#F59E0B", "#F472B6"]
                for index, step in enumerate(payload["steps"]):
                    color = colors[index % len(colors)]
                    text = Text(step, font_size=BODY_FONT, color=WHITE)
                    fit_to_portrait(text, extra_margin=1.1)
                    box = RoundedRectangle(corner_radius=0.25, width=text.width + 0.6, height=text.height + 0.5, color=color)
                    box.set_fill(color, opacity=0.18)
                    label = VGroup(box, text)
                    text.move_to(box.get_center())
                    cards.append(label)
                stack = VGroup(*cards).arrange(DOWN, buff=0.32)
                fit_to_portrait(stack, extra_margin=0.3)
                return stack


            def build_graph_scene_objects(payload):
                x_range = payload["x_range"]
                y_range = payload["y_range"]
                axes = Axes(
                    x_range=[x_range[0], x_range[1], 1],
                    y_range=[y_range[0], y_range[1], 1],
                    x_length=6.0,
                    y_length=7.4,
                    axis_config={"color": GREY_B, "include_numbers": False},
                    tips=False,
                )
                axes.shift(DOWN * 0.6)
                expression = payload["expression"]
                graph = axes.plot(
                    lambda x: eval(expression, {"__builtins__": {}}, {"x": x, "math": math}),
                    color=YELLOW,
                    stroke_width=6,
                )

                markers = VGroup()
                labels = VGroup()
                for sample in payload["samples"]:
                    dot = Dot(axes.c2p(sample["x"], sample["y"]), color="#38BDF8", radius=0.08)
                    label_text = sample["label"] or f"({sample['x']}, {sample['y']})"
                    label = Text(label_text, font_size=22, color=WHITE).next_to(dot, RIGHT, buff=0.15)
                    markers.add(dot)
                    labels.add(label)
                note = Text(payload["highlight_label"], font_size=26, color="#F8FAFC")
                note.next_to(axes, DOWN, buff=0.25)
                return axes, graph, markers, labels, note


            def build_motion_scene_objects(payload):
                x_range = payload["x_range"]
                y_range = payload["y_range"]
                axes = Axes(
                    x_range=[x_range[0], x_range[1], 1],
                    y_range=[y_range[0], y_range[1], 1],
                    x_length=6.0,
                    y_length=7.2,
                    axis_config={"color": GREY_B, "include_numbers": False},
                    tips=False,
                )
                axes.shift(DOWN * 0.4)
                trajectory_expression = payload["trajectory_expression"]
                graph = axes.plot(
                    lambda x: eval(trajectory_expression, {"__builtins__": {}}, {"x": x, "math": math}),
                    x_range=[x_range[0], x_range[1]],
                    color="#F59E0B",
                    stroke_width=6,
                )
                marker_x = payload["marker_x"]
                marker_y = eval(trajectory_expression, {"__builtins__": {}}, {"x": marker_x, "math": math})
                projectile = Dot(axes.c2p(marker_x, marker_y), color="#38BDF8", radius=0.11)
                vx = Arrow(projectile.get_center(), projectile.get_center() + RIGHT * 1.1, buff=0.0, color="#22C55E", stroke_width=8)
                vy = Arrow(projectile.get_center(), projectile.get_center() + UP * 0.9, buff=0.0, color="#A78BFA", stroke_width=8)
                vx_label = Text("vx", font_size=24, color="#22C55E").next_to(vx, UP, buff=0.08)
                vy_label = Text("vy", font_size=24, color="#A78BFA").next_to(vy, LEFT, buff=0.08)
                equation = Text(payload["equation_text"], font_size=28, color=WHITE)
                equation.next_to(axes, DOWN, buff=0.25)
                return axes, graph, projectile, vx, vy, vx_label, vy_label, equation


            class GeneratedScene(Scene):
                def construct(self):
                    title = make_title(SCENE_PAYLOAD["hook_text"])
                    footer = make_footer(SCENE_PAYLOAD["cta"])
                    self.play(FadeIn(title, shift=DOWN * 0.15), run_time=0.5)

                    if TEMPLATE_ID == "math_derivation_stack":
                        stack = build_derivation_cards(SCENE_PAYLOAD)
                        stack.next_to(title, DOWN, buff=0.55)
                        self.play(LaggedStart(*[FadeIn(card, shift=UP * 0.15) for card in stack], lag_ratio=0.2), run_time=1.8)
                        final_text = Text(SCENE_PAYLOAD["final_expression"], font_size=BODY_FONT + 2, color="#F8FAFC", weight=BOLD)
                        fit_to_portrait(final_text, extra_margin=1.0)
                        final_text.next_to(stack, DOWN, buff=0.4)
                        self.play(Write(final_text), run_time=0.7)
                        self.play(FadeIn(footer, shift=UP * 0.15), run_time=0.5)
                        self.wait(0.8)
                        self.play(FadeOut(stack, final_text, footer, title), run_time=0.7)
                        return

                    if TEMPLATE_ID == "math_graph_explainer":
                        axes, graph, markers, labels, note = build_graph_scene_objects(SCENE_PAYLOAD)
                        self.play(Create(axes), run_time=0.7)
                        self.play(Create(graph), run_time=1.1)
                        self.play(LaggedStart(*[FadeIn(dot, scale=0.7) for dot in markers], lag_ratio=0.2), run_time=0.8)
                        self.play(LaggedStart(*[Write(label) for label in labels], lag_ratio=0.2), run_time=0.9)
                        self.play(FadeIn(note, shift=UP * 0.1), FadeIn(footer, shift=UP * 0.15), run_time=0.5)
                        self.wait(0.8)
                        self.play(FadeOut(axes, graph, markers, labels, note, footer, title), run_time=0.8)
                        return

                    axes, graph, projectile, vx, vy, vx_label, vy_label, equation = build_motion_scene_objects(SCENE_PAYLOAD)
                    self.play(Create(axes), run_time=0.7)
                    self.play(Create(graph), run_time=1.0)
                    self.play(FadeIn(projectile, scale=0.7), run_time=0.3)
                    self.play(GrowArrow(vx), GrowArrow(vy), FadeIn(vx_label), FadeIn(vy_label), run_time=0.7)
                    self.play(Write(equation), FadeIn(footer, shift=UP * 0.15), run_time=0.6)
                    self.wait(0.8)
                    self.play(FadeOut(axes, graph, projectile, vx, vy, vx_label, vy_label, equation, footer, title), run_time=0.8)
            """
        )

        replacements = {
            "__PIXEL_WIDTH__": str(plan.render_profile.pixel_width),
            "__PIXEL_HEIGHT__": str(plan.render_profile.pixel_height),
            "__FRAME_WIDTH__": str(plan.render_profile.frame_width),
            "__FRAME_HEIGHT__": str(plan.render_profile.frame_height),
            "__TITLE_FONT__": str(plan.render_profile.title_font_size),
            "__BODY_FONT__": str(plan.render_profile.body_font_size),
            "__SAFE_X__": str(plan.render_profile.safe_margin_x),
            "__SAFE_Y__": str(plan.render_profile.safe_margin_y),
            "__TEMPLATE_ID__": repr(plan.template_id),
            "__SCENE_PAYLOAD__": repr(plan.scene_spec.payload),
        }

        for key, value in replacements.items():
            template = template.replace(key, value)
        return template
