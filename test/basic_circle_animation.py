"""
Basic Circle Animation Example

This script demonstrates a simple Manim animation featuring a circle
that appears, grows, and then fades out.
"""

from manim import *


class BasicCircleAnimation(Scene):
    """
    A basic scene demonstrating circle creation and transformation.
    
    This scene shows a circle appearing, growing in size, and then
    fading out with smooth transitions.
    """
    
    def construct(self):
        # Create a circle
        circle = Circle(
            radius=1,
            color=BLUE,
            fill_opacity=0.5
        )
        
        # Position the circle at the center
        circle.move_to(ORIGIN)
        
        # Animation sequence
        # 1. Create the circle
        self.play(Create(circle), run_time=2)
        
        # 2. Wait a moment
        self.wait(1)
        
        # 3. Scale the circle up
        self.play(circle.animate.scale(1.5), run_time=1.5)
        
        # 4. Wait again
        self.wait(1)
        
        # 5. Fade out the circle
        self.play(FadeOut(circle), run_time=1.5)
        
        # Final wait
        self.wait(1)


class CircleWithText(Scene):
    """
    A scene showing a circle with accompanying text.
    
    This demonstrates how to combine geometric shapes with text
    in a single animation sequence.
    """
    
    def construct(self):
        # Create a circle
        circle = Circle(
            radius=1.2,
            color=RED,
            fill_opacity=0.3,
            stroke_width=4
        )
        
        # Create text
        text = Text(
            "Hello Manim!",
            font_size=48,
            color=WHITE
        ).next_to(circle, DOWN, buff=0.5)
        
        # Animation sequence
        # Show circle first
        self.play(Create(circle), run_time=2)
        
        # Show text
        self.play(Write(text), run_time=1.5)
        
        # Wait
        self.wait(2)
        
        # Fade everything out
        self.play(
            FadeOut(circle),
            FadeOut(text),
            run_time=1.5
        )
        
        self.wait(1)
