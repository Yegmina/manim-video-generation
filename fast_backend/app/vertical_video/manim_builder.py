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
                if not text:
                    footer = Dot(radius=0.001, fill_opacity=0.0, stroke_opacity=0.0)
                    footer.move_to([0, -100, 0])
                    return footer
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


            def build_motion_scene_objects(payload, title):
                x_range = payload["x_range"]
                y_range = payload["y_range"]
                equation = MathTex(payload["equation_text"], font_size=24, color=WHITE)
                phase_text = Text(payload["phases"][1]["label"] if payload.get("phases") else "Motion state", font_size=16, color="#CBD5E1")
                info = VGroup(equation, phase_text).arrange(DOWN, aligned_edge=LEFT, buff=0.04)
                info.scale_to_fit_width(2.4)
                info_box = RoundedRectangle(corner_radius=0.12, width=info.width + 0.22, height=info.height + 0.18, color="#334155")
                info_box.set_fill("#0F172A", opacity=0.88)
                info.move_to(info_box.get_center())
                info_card = VGroup(info_box, info)

                top_anchor_y = title.get_bottom()[1] - 0.14
                graph_center_y = 0.15
                graph_height = 4.55

                axes = Axes(
                    x_range=[x_range[0], x_range[1], 1],
                    y_range=[y_range[0], y_range[1], 1],
                    x_length=4.8,
                    y_length=graph_height,
                    axis_config={"color": GREY_B, "include_numbers": False},
                    tips=False,
                )
                axes.move_to([-0.25, graph_center_y, 0])
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
                vx = Arrow(projectile.get_center(), projectile.get_center() + RIGHT * 1.0, buff=0.0, color="#22C55E", stroke_width=8)
                vy = Arrow(projectile.get_center(), projectile.get_center() + UP * 0.8, buff=0.0, color="#A78BFA", stroke_width=8)
                vx_label = Text("v_x", font_size=20, color="#22C55E").next_to(vx, UP, buff=0.05)
                vy_label = Text("v_y", font_size=20, color="#A78BFA").next_to(vy, LEFT, buff=0.05)
                x_axis_label = Text(payload.get("x_axis_label", "horizontal distance"), font_size=18, color="#CBD5E1")
                y_axis_label = Text(payload.get("y_axis_label", "height"), font_size=18, color="#CBD5E1")
                x_axis_label.next_to(axes.x_axis, DOWN, buff=0.02)
                y_axis_label.rotate(PI / 2)
                y_axis_label.next_to(axes.y_axis, LEFT, buff=0.06)

                info_card.next_to(title, DOWN, buff=0.18)
                info_card.to_edge(RIGHT, buff=SAFE_X + 0.15)
                return axes, graph, projectile, vx, vy, vx_label, vy_label, info_card, x_axis_label, y_axis_label


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
                        fade_targets = [axes, graph, markers, labels, note, footer, title]
                        self.play(*[FadeOut(mob) for mob in fade_targets], run_time=0.8)
                        return

                    axes, graph, projectile, vx, vy, vx_label, vy_label, info, x_axis_label, y_axis_label = build_motion_scene_objects(SCENE_PAYLOAD, title)
                    self.play(Create(axes), FadeIn(x_axis_label), FadeIn(y_axis_label), run_time=0.7)
                    self.play(Create(graph), run_time=1.0)
                    self.play(FadeIn(projectile, scale=0.7), run_time=0.3)
                    self.play(GrowArrow(vx), GrowArrow(vy), FadeIn(vx_label), FadeIn(vy_label), run_time=0.7)
                    self.play(Write(info), FadeIn(footer, shift=UP * 0.15), run_time=0.6)
                    self.wait(0.8)
                    fade_targets = [axes, graph, projectile, vx, vy, vx_label, vy_label, info, x_axis_label, y_axis_label, footer, title]
                    self.play(*[FadeOut(mob) for mob in fade_targets], run_time=0.8)
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
